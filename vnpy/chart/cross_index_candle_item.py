"""
扩展的CandleItem，支持大周期K线的跨索引绘制

特点：
1. 支持跨多个索引位置绘制（大周期K线）
2. 颜色：阳线红色空心，阴线青色填充（95%透明）
3. 上下影线位于时间范围中点，不穿过实体
"""

from datetime import datetime, timedelta

import pyqtgraph as pg  # type: ignore

from vnpy.trader.ui import QtGui, QtCore
from vnpy.trader.object import BarData
from vnpy.trader.constant import Interval
from vnpy.trader.period_utils import (
    get_hkfe_4hour_period,
    get_hkfe_hour_period_start,
    get_period_start,
)

from vnpy.chart.manager import BarManager
from vnpy.chart.item import ChartItem
from vnpy.chart.base import UP_COLOR, DOWN_COLOR, PEN_WIDTH


class CrossIndexCandleItem(ChartItem):
    """
    支持跨索引绘制的CandleItem

    用于绘制大周期K线（如4小时），可以跨越多个1分钟索引位置
    """

    def __init__(
        self,
        manager: BarManager,
        base_manager: BarManager | None = None,
        bearish_fill_opacity: float = 0.05,
        bullish_color: QtGui.QColor | None = None,
        bearish_color: QtGui.QColor | None = None,
        interval: Interval = Interval.HOUR_4,
        pen_width: int | None = None,
    ) -> None:
        """
        Initialize cross-index candle item.

        Args:
            manager: BarManager for current timeframe bars
            base_manager: BarManager for 1-minute bars (used for index mapping)
            bearish_fill_opacity: 填充透明度（阳线阴线共享）
            bullish_color: 阳线颜色
            bearish_color: 阴线颜色
            interval: 时间周期
            pen_width: 线宽
        """
        super().__init__(manager)

        # Store reference to base manager (1-minute bars)
        self._base_manager: BarManager | None = base_manager

        # 当前时间周期（1小时或4小时），用于索引映射
        self._interval: Interval = interval

        # 填充透明度（阳线阴线共享）
        self._fill_opacity: float = max(0.0, min(1.0, bearish_fill_opacity))

        # 颜色和线宽设置
        # 阳线：默认红色，带填充
        if bullish_color is None:
            bullish_color = QtGui.QColor(*UP_COLOR)

        # 如果未指定，则4H/1H默认线宽 = PEN_WIDTH+1
        if pen_width is None:
            pen_width = PEN_WIDTH + 1

        self._bullish_pen: QtGui.QPen = pg.mkPen(
            color=bullish_color, width=pen_width
        )

        # 阳线画刷（带填充，与阴线共享透明度）
        self._bullish_color = bullish_color
        self._update_bullish_brush()

        # 阴线：默认青色
        # 要求：引线和实体边界完全显示（不透明），只有填充区域高透明度（可调）
        if bearish_color is None:
            bearish_pen_color = QtGui.QColor(*DOWN_COLOR)  # 不透明，用于边框和影线
        else:
            bearish_pen_color = bearish_color

        self._bearish_pen: QtGui.QPen = pg.mkPen(
            color=bearish_pen_color, width=pen_width
        )

        self._bearish_color = bearish_pen_color
        self._update_bearish_brush()

        # Cache for bar index ranges
        # Format: bar_datetime -> (start_index, end_index)
        self._bar_range_cache: dict[datetime, tuple[int, int]] = {}

    def _update_bullish_brush(self) -> None:
        """
        根据当前的不透明度设置更新阳线填充画刷。
        """
        bullish_brush_color = QtGui.QColor(self._bullish_color)
        # setAlphaF 接受 0.0-1.0 之间的不透明度（1.0 为完全不透明）
        bullish_brush_color.setAlphaF(self._fill_opacity)
        self._bullish_brush = pg.mkBrush(color=bullish_brush_color)

    def _update_bearish_brush(self) -> None:
        """
        根据当前的不透明度设置更新阴线填充画刷。
        """
        bearish_brush_color = QtGui.QColor(self._bearish_color)
        # setAlphaF 接受 0.0-1.0 之间的不透明度（1.0 为完全不透明）
        bearish_brush_color.setAlphaF(self._fill_opacity)
        self._bearish_brush = pg.mkBrush(color=bearish_brush_color)

    def set_bearish_fill_opacity(self, opacity: float) -> None:
        """
        设置填充透明度（阳线阴线共享）。

        Args:
            opacity: 0.0-1.0 之间的浮点数，0.0=完全透明，1.0=完全不透明
        """
        self._fill_opacity = max(0.0, min(1.0, opacity))
        self._update_bullish_brush()  # 同时更新阳线
        self._update_bearish_brush()  # 和阴线

        # 清空已缓存的bar图片，确保使用新的画刷重新绘制
        for ix in list(self._bar_picutures.keys()):
            pic = self._bar_picutures[ix]
            if pic is not None:
                del pic
            self._bar_picutures[ix] = None

        # 整体图像也需要重建
        if self._item_picuture is not None:
            del self._item_picuture
        self._item_picuture = None

        # 触发重绘
        self.update()

    def _calculate_4h_period_end(self, start_datetime: datetime) -> datetime:
        """
        计算4小时周期的结束时间（HKFE交易时段）

        4小时周期规则：
        1. 17:15-21:14 (第一根4H)
        2. 21:15-01:14 (第二根4H，跨午夜)
        3. 01:15-11:29 (第三根4H，跨休市：01:15-03:00 + 09:15-11:29)
        4. 11:30-16:29 (第四根4H，跨午休：11:30-12:00 + 13:00-16:29)

        Args:
            start_datetime: 4小时周期开始时间

        Returns:
            4小时周期结束时间（下一个周期的开始时间）
        """
        hour = start_datetime.hour
        minute = start_datetime.minute

        # 根据开始时间判断是哪个4小时周期
        if hour == 17 and minute == 15:
            # 第一根：17:15 -> 21:15
            end_datetime = start_datetime.replace(hour=21, minute=15)
        elif hour == 21 and minute == 15:
            # 第二根：21:15 -> 次日01:15
            end_datetime = start_datetime + timedelta(days=1)
            end_datetime = end_datetime.replace(hour=1, minute=15)
        elif hour == 1 and minute == 15:
            # 第三根：01:15 -> 当日11:30
            end_datetime = start_datetime.replace(hour=11, minute=30)
        elif hour == 11 and minute == 30:
            # 第四根：11:30 -> 当日16:30（11:30-16:29 为第四根4小时K线）
            end_datetime = start_datetime.replace(hour=16, minute=30)
        else:
            # 默认：4小时后（简化处理）
            end_datetime = start_datetime + timedelta(hours=4)

        return end_datetime

    def _get_bar_index_range(self, bar: BarData) -> tuple[int, int]:
        """
        获取大周期K线在1分钟时间轴上的索引范围

        Args:
            bar: 大周期K线数据

        Returns:
            (start_index, end_index) 索引范围
        """
        # 检查缓存
        if bar.datetime in self._bar_range_cache:
            return self._bar_range_cache[bar.datetime]

        if not self._base_manager:
            # 如果没有基准管理器，使用默认值（单索引位置）
            ix = self._manager.get_index(bar.datetime)
            if ix is None:
                ix = 0
            return (ix, ix)

        # 使用全局HKFE/period_utils规则：扫描所有1分钟K线，找到属于当前周期(bar.datetime)的连续区间
        base_bars = self._base_manager.get_all_bars()
        start_ix: int | None = None
        end_ix: int | None = None

        for i, base_bar in enumerate(base_bars):
            if self._interval == Interval.HOUR_4:
                period_start, _ = get_hkfe_4hour_period(base_bar.datetime)
            elif self._interval == Interval.HOUR:
                period_start = get_hkfe_hour_period_start(base_bar.datetime)
            elif self._interval == Interval.MINUTE_5:
                # 5分钟周期：使用period_utils中现有规则
                period_start = get_period_start(
                    base_bar.datetime, Interval.MINUTE_5, base_bar.exchange
                )
            else:
                period_start = None

            if period_start == bar.datetime:
                if start_ix is None:
                    start_ix = i
                end_ix = i
            elif start_ix is not None:
                # 一旦走出该周期区间就可以停止
                break

        if start_ix is None or end_ix is None:
            # 找不到匹配的1分钟K线时，退回到bar自身索引
            ix = self._manager.get_index(bar.datetime)
            if ix is None:
                ix = 0
            start_ix = end_ix = ix

        # 缓存结果
        self._bar_range_cache[bar.datetime] = (start_ix, end_ix)
        return (start_ix, end_ix)

    def _find_closest_index(self, target_datetime: datetime, before: bool = True) -> int:
        """
        查找最接近目标时间的索引

        Args:
            target_datetime: 目标时间
            before: 如果为True，查找目标时间之前的最近索引

        Returns:
            索引位置
        """
        if not self._base_manager:
            return 0

        # 精确匹配
        exact_ix = self._base_manager.get_index(target_datetime)
        if exact_ix is not None:
            return exact_ix

        # 查找最接近的索引
        all_bars = self._base_manager.get_all_bars()
        if not all_bars:
            return 0

        closest_ix = 0
        min_diff = float('inf')

        for i, base_bar in enumerate(all_bars):
            diff = abs((base_bar.datetime - target_datetime).total_seconds())
            if diff < min_diff:
                min_diff = diff
                closest_ix = i

        return closest_ix

    def _draw_bar_picture(self, ix: int, bar: BarData) -> QtGui.QPicture:
        """
        按“画线方式”绘制4小时K线（跨索引），而不是矩形实体：

        - 起点X：第一根1分钟K线(如17:15)的索引
        - 终点X：最后一根1分钟K线(如21:14)的索引
        - 实体：
          - 在起点和终点分别画竖线，连接开盘价和收盘价
          - 从终点向起点各画一条开盘价/收盘价的水平线
        - 影线：在时间范围中点画竖线，上下端按最高价/最低价并且不穿过实体

        Args:
            ix: Starting index position (from current manager)
            bar: Bar data
        """
        # Create objects
        candle_picture: QtGui.QPicture = QtGui.QPicture()
        painter: QtGui.QPainter = QtGui.QPainter(candle_picture)

        # 获取K线在1分钟时间轴上的索引范围
        start_ix, end_ix = self._get_bar_index_range(bar)

        # 计算中心位置（用于影线）
        center_ix = (start_ix + end_ix) / 2.0

        open_price = bar.open_price
        close_price = bar.close_price
        high_price = bar.high_price
        low_price = bar.low_price

        # 实体上下边界
        body_top = max(open_price, close_price)
        body_bottom = min(open_price, close_price)

        # ---------- K线填充矩形（阳线阴线都填充，共享透明度） ----------
        # 先画填充矩形（只影响实体内部），使用高透明度画刷
        fill_rect = QtCore.QRectF(
            start_ix,
            body_bottom,
            max(1.0, end_ix - start_ix),  # 至少保证有一点宽度
            body_top - body_bottom
        )
        painter.setPen(QtCore.Qt.NoPen)

        if close_price < open_price:
            # 阴线：使用阴线画刷填充
            painter.setBrush(self._bearish_brush)
        else:
            # 阳线：也使用画刷填充（不再是空心）
            painter.setBrush(self._bullish_brush)

        painter.drawRect(fill_rect)

        # 接下来画边框和影线：始终使用不透明画笔 + 无填充
        if close_price >= open_price:
            painter.setPen(self._bullish_pen)
        else:
            painter.setPen(self._bearish_pen)
        painter.setBrush(QtGui.QBrush(QtCore.Qt.NoBrush))

        # ---------- 实体：两条水平线 + 两条竖线 ----------
        # 水平线：从终点画到起点（视觉上等价）
        # 开盘价水平线
        painter.drawLine(
            QtCore.QPointF(start_ix, open_price),
            QtCore.QPointF(end_ix, open_price),
        )
        # 收盘价水平线
        painter.drawLine(
            QtCore.QPointF(start_ix, close_price),
            QtCore.QPointF(end_ix, close_price),
        )

        # 竖线：起点和终点各一根，连接开盘价和收盘价
        painter.drawLine(
            QtCore.QPointF(start_ix, open_price),
            QtCore.QPointF(start_ix, close_price),
        )
        painter.drawLine(
            QtCore.QPointF(end_ix, open_price),
            QtCore.QPointF(end_ix, close_price),
        )

        # ---------- 影线：数量中点位置，不穿过实体 ----------
        # 上影线
        if high_price > body_top:
            upper_from = body_top
            painter.drawLine(
                QtCore.QPointF(center_ix, upper_from),
                QtCore.QPointF(center_ix, high_price),
            )

        # 下影线
        if low_price < body_bottom:
            lower_from = body_bottom
            painter.drawLine(
                QtCore.QPointF(center_ix, lower_from),
                QtCore.QPointF(center_ix, low_price),
            )

        # Finish
        painter.end()
        return candle_picture

    # ----------------------------------------------------------------------
    # 覆盖父类的 paint：对于4小时K线数量很少，直接绘制全部K线，
    # 避免使用视图的 min_ix/max_ix 导致在放大后索引范围超出4小时数量而不绘制的问题。
    def paint(
        self,
        painter: QtGui.QPainter,
        opt,
        w
    ) -> None:
        """
        Reimplement paint: always draw all 4H bars regardless of current X index range.
        """
        min_ix = 0
        max_ix = self._manager.get_count()

        rect_area: tuple = (min_ix, max_ix)
        if (
            self._to_update
            or rect_area != self._rect_area
            or not self._item_picuture
        ):
            self._to_update = False
            self._rect_area = rect_area
            self._draw_item_picture(min_ix, max_ix)

        if self._item_picuture:
            self._item_picuture.play(painter)

    def boundingRect(self) -> QtCore.QRectF:
        """
        Get bounding rectangle.

        对于跨索引绘制的大周期K线，X 轴应该覆盖完整的1分钟时间轴范围，
        否则在放大到右侧时，4小时K线会因为boundingRect太窄而被裁剪掉。
        """
        min_price, max_price = self._manager.get_price_range()

        # 如果有1分钟基准管理器，则使用1分钟数据的数量作为宽度
        if self._base_manager:
            x_max = self._base_manager.get_count()
        else:
            x_max = len(self._bar_picutures)

        rect: QtCore.QRectF = QtCore.QRectF(
            0,
            min_price,
            x_max,
            max_price - min_price
        )
        return rect

    def get_y_range(self, min_ix: int | None = None, max_ix: int | None = None) -> tuple[float, float]:
        """Get Y-axis range."""
        return self._manager.get_price_range()

    def get_info_text(self, ix: int) -> str:
        """Get info text for cursor."""
        bar = self._manager.get_bar(ix)
        if bar is None:
            return ""

        return f"4H: O:{bar.open_price:.2f} H:{bar.high_price:.2f} L:{bar.low_price:.2f} C:{bar.close_price:.2f}"

