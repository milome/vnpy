"""
多周期叠加绘制 Widget

- 支持在同一张图上叠加显示 1m / 5m / 1H / 4H K 线
- 使用跨索引绘制（所有大周期都按 1 分钟时间轴对齐）
- 线型颜色、粗细、阴线填充透明度、是否显示等通过参数对象配置
- 仅绘制K线部分，不包含成交量（保持功能专一）
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from vnpy.trader.ui import QtCore, QtWidgets, QtGui, create_qapp
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.database import get_database
from vnpy.trader.object import BarData, TickData
from vnpy.trader.utility import BarGenerator
from vnpy.trader.hkfe_bar_generator import HKFEBarGenerator
from vnpy.trader.period_utils import (
    get_period_start,
    get_hkfe_4hour_period,
    aggregate_to_1hour_from_minutes
)

from vnpy.chart import ChartWidget, CandleItem
from vnpy.chart.manager import BarManager
from vnpy.chart.base import PEN_WIDTH, UP_COLOR, DOWN_COLOR
from vnpy.chart.cross_index_candle_item import CrossIndexCandleItem
from vnpy.chart.multi_timeframe_settings_dialog import (
    MultiTimeframeSettings,
    show_settings_dialog
)

logger = logging.getLogger(__name__)


@dataclass
class TimeframeStyle:
    """
    多周期绘制样式配置。

    所有字段都可选，如果为 None/缺省则使用该周期的默认样式。
    """

    bullish_color: QtGui.QColor | None = None      # 阳线颜色
    bearish_color: QtGui.QColor | None = None      # 阴线轮廓颜色
    pen_width: int | None = None                   # 线宽
    bearish_fill_opacity: float = 0.05                # 阴线实体填充不透明度（0.0-1.0）
    visible: bool = True                              # 是否显示该周期


class MultiTimeframeWidget(QtWidgets.QWidget):
    """
    可复用的多周期叠加绘制组件。

    - 内含一个 `ChartWidget`，仅绘制K线图表（不包含成交量）
    - 通过 TimeframeStyle 配置 5m / 1H / 4H 的样式与显示
    - 使用数据库中的历史 K 线数据（1m/5m/1H/4H）
    """

    def __init__(
        self,
        vt_symbol: str,
        exchange: Exchange,
        start: datetime,
        end: datetime,
        style_5m: TimeframeStyle | None = None,
        style_1h: TimeframeStyle | None = None,
        style_4h: TimeframeStyle | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._vt_symbol: str = vt_symbol
        self._exchange: Exchange = exchange
        self._start: datetime = start
        self._end: datetime = end

        # 样式对象：如未传入，则使用默认配置
        self._style_5m: TimeframeStyle = style_5m or TimeframeStyle(
            bullish_color=QtGui.QColor(*UP_COLOR),
            bearish_color=QtGui.QColor(*DOWN_COLOR),
            pen_width=PEN_WIDTH,
            bearish_fill_opacity=0.10,
            visible=True,
        )
        self._style_1h: TimeframeStyle = style_1h or TimeframeStyle(
            bullish_color=QtGui.QColor(*UP_COLOR),
            bearish_color=QtGui.QColor(*DOWN_COLOR),
            pen_width=PEN_WIDTH + 1,
            bearish_fill_opacity=0.10,
            visible=True,
        )
        self._style_4h: TimeframeStyle = style_4h or TimeframeStyle(
            bullish_color=QtGui.QColor(*UP_COLOR),
            bearish_color=QtGui.QColor(*DOWN_COLOR),
            pen_width=PEN_WIDTH + 2,
            bearish_fill_opacity=0.05,
            visible=True,
        )

        # 图表及管理器
        self._chart: ChartWidget
        self._main_manager: BarManager
        self._manager_5m: BarManager | None = None
        self._manager_1h: BarManager | None = None
        self._manager_4h: BarManager | None = None

        # 绘制项
        self._item_5m: CrossIndexCandleItem | None = None
        self._item_1h: CrossIndexCandleItem | None = None
        self._item_4h: CrossIndexCandleItem | None = None

        # 控件
        self._slider_5m: QtWidgets.QSlider | None = None
        self._slider_1h: QtWidgets.QSlider | None = None
        self._slider_4h: QtWidgets.QSlider | None = None

        self._checkbox_5m: QtWidgets.QCheckBox | None = None
        self._checkbox_1h: QtWidgets.QCheckBox | None = None
        self._checkbox_4h: QtWidgets.QCheckBox | None = None

        # BarGenerator实例（用于实时更新）
        self._bg_1m: BarGenerator | None = None
        self._bg_5m: HKFEBarGenerator | None = None
        self._bg_1h: HKFEBarGenerator | None = None
        self._bg_4h: HKFEBarGenerator | None = None

        # 是否启用实时更新
        self._realtime_enabled: bool = False

        self._init_ui()
        self._load_data_and_build_items()

    # ---------------------------------------------------------------------
    # UI 构建
    def _init_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # ChartWidget（仅K线图表，不包含成交量）
        chart = ChartWidget()
        chart.add_plot("candle", hide_x_axis=False)

        chart.add_item(CandleItem, "candle", "candle")
        chart.add_cursor()

        layout.addWidget(chart, stretch=1)

        self._chart = chart
        self._main_manager = chart._manager  # 1m 时间轴基准

        # 控制面板：透明度 + 显示开关
        control_layout = QtWidgets.QHBoxLayout()
        control_layout.setContentsMargins(0, 0, 0, 0)

        def add_opacity_control(
            label_text: str,
            init_opacity: float,
        ) -> tuple[QtWidgets.QSlider, QtWidgets.QLabel, QtWidgets.QLabel]:
            label = QtWidgets.QLabel(label_text)
            label.setMinimumWidth(130)

            slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(int(init_opacity * 100))
            slider.setTickInterval(5)
            slider.setSingleStep(1)

            value_label = QtWidgets.QLabel(f"{int(init_opacity * 100)}%")
            value_label.setMinimumWidth(40)

            control_layout.addWidget(label)
            control_layout.addWidget(slider, stretch=1)
            control_layout.addWidget(value_label)

            return label, slider, value_label

        # 4H / 1H / 5m 透明度控件
        _, self._slider_4h, label_val_4h = add_opacity_control(
            "4H 阴线填充透明度", self._style_4h.bearish_fill_opacity
        )

        control_layout.addSpacing(15)

        _, self._slider_1h, label_val_1h = add_opacity_control(
            "1H 阴线填充透明度", self._style_1h.bearish_fill_opacity
        )

        control_layout.addSpacing(15)

        _, self._slider_5m, label_val_5m = add_opacity_control(
            "5m 阴线填充透明度", self._style_5m.bearish_fill_opacity
        )

        # 显示开关
        control_layout.addSpacing(15)

        self._checkbox_4h = QtWidgets.QCheckBox("显示 4H")
        self._checkbox_4h.setChecked(self._style_4h.visible)

        self._checkbox_1h = QtWidgets.QCheckBox("显示 1H")
        self._checkbox_1h.setChecked(self._style_1h.visible)

        self._checkbox_5m = QtWidgets.QCheckBox("显示 5m")
        self._checkbox_5m.setChecked(self._style_5m.visible)

        control_layout.addWidget(self._checkbox_4h)
        control_layout.addWidget(self._checkbox_1h)
        control_layout.addWidget(self._checkbox_5m)

        layout.addLayout(control_layout)

        # 把 value_label 保存下来（用于更新显示数值）
        self._label_val_4h = label_val_4h
        self._label_val_1h = label_val_1h
        self._label_val_5m = label_val_5m

    # ---------------------------------------------------------------------
    # 辅助方法：起始时间优化
    def _check_data_completeness(
        self, 
        database, 
        existing_bars: list,
        user_start: datetime,
        user_end: datetime
    ) -> tuple:
        """
        检查数据完整性，决定是否需要从FUTU下载
        
        策略（与单周期相同）：
        1. 如果数据库无数据 → 下载最近7天
        2. 如果数据库最新数据 < 1小时前 → 下载最近7天
        3. 如果用户起始时间 < 数据库最早时间 → 全量下载
        4. 如果数据库数据较新 → 跳过下载
        
        Returns:
            (download_start, need_download): 下载起始时间和是否需要下载
        """
        from datetime import timedelta
        import pytz
        from vnpy.trader.setting import SETTINGS
        
        try:
            # 策略1：数据库无数据 → 下载最近7天
            if not existing_bars:
                download_start = user_end - timedelta(days=7)
                logger.info(f"[多周期] 数据库无数据，下载最近7天: {download_start} ~ {user_end}")
                return download_start, True
            
            # 查询数据库中的最早和最新数据
            existing_bars.sort(key=lambda x: x.datetime)
            db_earliest_raw = existing_bars[0].datetime
            db_latest_raw = existing_bars[-1].datetime
            
            # 打印原始时间戳（转换前）
            logger.info(f"[时区调试] === 原始时间戳（转换前） ===")
            logger.info(f"[时区调试] 数据库最早原始: {db_earliest_raw} (tzinfo={db_earliest_raw.tzinfo})")
            logger.info(f"[时区调试] 数据库最新原始: {db_latest_raw} (tzinfo={db_latest_raw.tzinfo})")
            logger.info(f"[时区调试] 用户起始原始: {user_start} (tzinfo={user_start.tzinfo})")
            logger.info(f"[时区调试] 用户结束原始: {user_end} (tzinfo={user_end.tzinfo})")
            
            # ✅ 时区统一处理：统一使用数据库配置的时区进行比较
            # 获取数据库时区配置，根据 database.py 的 convert_tz()，
            # 数据库保存的是 naive datetime，实际表示数据库时区的时间
            db_tz_name = SETTINGS.get("database.timezone", "Asia/Shanghai")
            database_tz = pytz.timezone(db_tz_name)
            
            logger.info(f"[时区调试] 数据库时区配置: {db_tz_name}")
            
            # 将所有 datetime 统一转换到数据库时区
            db_earliest = db_earliest_raw
            db_latest = db_latest_raw
            
            if db_earliest.tzinfo is None:
                db_earliest = database_tz.localize(db_earliest)
            else:
                db_earliest = db_earliest.astimezone(database_tz)
            
            if db_latest.tzinfo is None:
                db_latest = database_tz.localize(db_latest)
            else:
                db_latest = db_latest.astimezone(database_tz)
            
            if user_start.tzinfo is None:
                user_start = database_tz.localize(user_start)
            else:
                user_start = user_start.astimezone(database_tz)
            
            if user_end.tzinfo is None:
                user_end = database_tz.localize(user_end)
            else:
                user_end = user_end.astimezone(database_tz)
            
            # 打印转换后的时间戳
            logger.info(f"[时区调试] === 转换后时间戳（统一到{db_tz_name}） ===")
            logger.info(f"[时区调试] 数据库最早: {db_earliest}")
            logger.info(f"[时区调试] 数据库最新: {db_latest}")
            logger.info(f"[时区调试] 用户起始: {user_start}")
            logger.info(f"[时区调试] 用户结束: {user_end}")
            
            # 打印时间差
            data_age = user_end - db_latest
            time_gap = user_start - db_earliest
            logger.info(f"[时区调试] === 时间差分析 ===")
            logger.info(f"[时区调试] 数据年龄 (user_end - db_latest): {data_age} ({data_age.total_seconds()/3600:.2f} 小时)")
            logger.info(f"[时区调试] 时间间隙 (user_start - db_earliest): {time_gap}")
            
            logger.info(f"[多周期] 数据库时区: {db_tz_name}")
            logger.info(f"[多周期] 数据库范围: {db_earliest} ~ {db_latest}")
            logger.info(f"[多周期] 用户选择范围: {user_start} ~ {user_end}")
            
            # 策略2：数据库最新数据 < 1小时前 → 下载最近7天
            data_age = user_end - db_latest
            if data_age.total_seconds() > 3600:  # 1小时
                download_start = user_end - timedelta(days=7)
                logger.info(
                    f"[多周期] 数据库数据较旧（最新数据距今 {data_age.total_seconds()/3600:.1f} 小时），"
                    f"下载最近7天: {download_start} ~ {user_end}"
                )
                return download_start, True
            
            # 策略3：用户起始时间 < 数据库最早时间 → 全量下载
            if user_start < db_earliest:
                logger.info(
                    f"[多周期] 用户选择时间 {user_start} 早于数据库最早时间 {db_earliest}，"
                    f"全量下载: {user_start} ~ {user_end}"
                )
                return user_start, True
            
            # 策略4：数据库数据较新 → 跳过下载
            logger.info(f"[多周期] 数据库数据足够新（< 1小时），跳过下载")
            return user_start, False
            
        except Exception as e:
            logger.warning(f"[多周期] 检查数据完整性失败: {e}，跳过下载")
            return user_start, False
    
    def _download_from_futu(
        self,
        symbol: str,
        exchange: Exchange,
        start: datetime,
        end: datetime
    ) -> list:
        """
        从FUTU API下载1分钟数据（复用 DataManager 的下载逻辑）
        
        Args:
            symbol: 合约代码
            exchange: 交易所
            start: 起始时间
            end: 结束时间
            
        Returns:
            下载的K线数据列表，如果失败返回 None
        """
        try:
            # 检查是否有 MainEngine
            if not hasattr(self, '_main_engine') or not self._main_engine:
                logger.warning("[多周期] 未设置 MainEngine，无法从 FUTU API 下载数据")
                return None
            
            # 使用 DataManager 的下载功能（DRY原则，不重复造轮子）
            datamanager_engine = self._main_engine.engines.get("DataManager")
            
            if not datamanager_engine:
                logger.warning("[多周期] DataManager 不可用")
                return None
            
            if not hasattr(datamanager_engine, 'download_bar_data'):
                logger.warning("[多周期] DataManager 没有 download_bar_data 方法")
                return None
            
            logger.info(f"[多周期] 使用 DataManager 下载数据: {start} 至今")
            
            # 调用 DataManager 的下载方法
            # 注意：DataManager.download_bar_data 只需要 start，会下载到当前时间
            # 参数：symbol, exchange, interval, start, output（回调函数）
            success = datamanager_engine.download_bar_data(
                symbol=symbol,
                exchange=exchange,
                interval=Interval.MINUTE,
                start=start,
                output=lambda msg: logger.info(f"[DataManager] {msg}")
            )
            
            if success:
                logger.info(f"[多周期] DataManager 下载成功，数据已保存到数据库")
                # 从数据库重新加载
                from vnpy.trader.database import get_database
                database = get_database()
                bars = database.load_bar_data(
                    symbol=symbol,
                    exchange=exchange,
                    interval=Interval.MINUTE,
                    start=start,
                    end=end
                )
                return bars
            else:
                logger.warning("[多周期] DataManager 下载失败")
                return None
            
        except Exception as e:
            logger.error(f"[多周期] 从FUTU下载失败: {e}", exc_info=True)
            return None
    
    def _get_optimized_start_time(self, database) -> tuple:
        """
        优化起始时间和数据下载策略
        
        策略：
        1. 查询数据库中最早的1分钟数据时间
        2. 如果用户选择时间早于数据库最早时间 → 数据库不全，从FUTU API全量补齐
        3. 如果用户选择时间晚于数据库最早时间 → 数据库已有，为保险重新下载最近7天
        
        Returns:
            (optimized_start, need_download_from_futu): 优化后的起始时间和是否需要从FUTU下载
        """
        from datetime import timedelta
        
        try:
            # 查询数据库最早数据（查询最近90天内的数据来确定最早时间）
            query_start = datetime.now() - timedelta(days=90)
            existing_bars = database.load_bar_data(
                symbol=self._vt_symbol,
                exchange=self._exchange,
                interval=Interval.MINUTE,
                start=query_start,
                end=self._end
            )
            
            if existing_bars and len(existing_bars) > 0:
                # 找到最早的数据时间
                existing_bars.sort(key=lambda x: x.datetime)
                db_earliest = existing_bars[0].datetime
                
                logger.info(f"[多周期] 数据库最早1分钟数据: {db_earliest}")
                logger.info(f"[多周期] 用户选择起始时间: {self._start}")
                
                if self._start < db_earliest:
                    # 情况1：用户选择时间早于数据库最早时间
                    # → 数据库数据不全，需要从 FUTU API 全量补齐
                    logger.info(
                        f"[多周期] 数据库数据不全：用户选择 {self._start} 早于数据库最早数据 {db_earliest}"
                    )
                    logger.info(f"[多周期] 策略：从 FUTU API 全量下载历史数据")
                    return self._start, True  # 使用用户时间，需要从FUTU下载
                else:
                    # 情况2：用户选择时间晚于数据库最早时间
                    # → 数据库已有数据，为保险重新下载最近7天
                    optimized_start = datetime.now() - timedelta(days=7)
                    logger.info(
                        f"[多周期] 数据库已有数据：用户选择 {self._start} 晚于数据库最早数据 {db_earliest}"
                    )
                    logger.info(f"[多周期] 策略：为保险起见，重新下载最近7天数据（{optimized_start} ~ {self._end}）")
                    return optimized_start, True  # 使用最近7天，需要从FUTU下载
            else:
                # 数据库没有数据，从FUTU API下载最近7天
                optimized_start = datetime.now() - timedelta(days=7)
                logger.info(f"[多周期] 数据库无数据，从 FUTU API 下载最近7天: {optimized_start}")
                return optimized_start, True
                
        except Exception as e:
            logger.warning(f"[多周期] 查询数据库最早时间失败: {e}，使用用户选择时间")
            return self._start, False  # 失败时不强制下载
    
    def _download_minute_bars_from_futu(
        self,
        start: datetime,
        end: datetime,
        progress_callback=None
    ) -> list:
        """
        从 FUTU API 下载1分钟历史数据（复用 ChartWindow 的下载逻辑）
        
        Args:
            start: 起始时间
            end: 结束时间
            progress_callback: 进度回调
            
        Returns:
            下载的1分钟K线数据
        """
        from vnpy.trader.object import HistoryRequest
        
        if progress_callback:
            progress_callback(f"正在从 FUTU API 下载数据 ({start.strftime('%Y-%m-%d')} ~ {end.strftime('%Y-%m-%d')})...", 10)
        
        try:
            # 检查是否有 MainEngine
            if not hasattr(self, '_main_engine') or not self._main_engine:
                if progress_callback:
                    progress_callback("未设置 MainEngine，无法下载", 0)
                return None
            
            # 使用 DataManager 的下载功能（DRY原则，不重复造轮子）
            datamanager_engine = self._main_engine.engines.get("DataManager")
            
            if not datamanager_engine:
                logger.warning("[多周期] DataManager 不可用")
                if progress_callback:
                    progress_callback("DataManager 不可用", 0)
                return None
            
            if not hasattr(datamanager_engine, 'download_history_data'):
                logger.warning("[多周期] DataManager 没有 download_history_data 方法")
                if progress_callback:
                    progress_callback("DataManager 方法不可用", 0)
                return None
            
            logger.info("[多周期] 使用 DataManager 下载数据")
            
            if progress_callback:
                progress_callback("使用 DataManager 下载数据...", 12)
            
            # 调用 DataManager 的 download_history_data 方法
            datamanager_engine.download_history_data(
                symbol=self._vt_symbol,
                exchange=self._exchange,
                interval=Interval.MINUTE,
                start=start,
                end=end
            )
            
            if progress_callback:
                progress_callback("DataManager 下载完成，正在从数据库加载...", 20)
            
            # 从数据库重新加载
            database = get_database()
            bars = database.load_bar_data(
                symbol=self._vt_symbol,
                exchange=self._exchange,
                interval=Interval.MINUTE,
                start=start,
                end=end
            )
            
            if bars:
                logger.info(f"[多周期] DataManager 下载并保存成功: {len(bars)} 条")
                if progress_callback:
                    progress_callback(f"下载完成: {len(bars)} 条", 25)
                return bars
            else:
                logger.warning("[多周期] DataManager 下载后数据库仍为空")
                if progress_callback:
                    progress_callback("下载后数据库仍为空", 0)
                return None
            
        except Exception as e:
            logger.error(f"[多周期] 从 FUTU API 下载数据失败: {e}", exc_info=True)
            if progress_callback:
                progress_callback(f"FUTU 下载失败: {e}", 0)
            return None
    
    # ---------------------------------------------------------------------
    # 数据加载与绘制项创建
    def _load_data_and_build_items(self, progress_callback=None) -> None:
        """
        加载数据并创建绘制项
        
        策略：先加载1分钟数据（必需），然后并行加载其他大周期数据
        
        Args:
            progress_callback: 进度回调函数，接受 (message: str, progress: int) 参数
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        database = get_database()

        # 添加详细的调试信息
        logger.info("[多周期] _load_data_and_build_items 开始执行（分步并行加载）")
        logger.info(f"[多周期] 当前合约: {self._vt_symbol}")
        logger.info(f"[多周期] 当前交易所: {self._exchange}")
        logger.info(f"[多周期] 用户选择时间范围: {self._start} ~ {self._end}")
        logger.info(f"[多周期] 重要：所有周期都使用用户选择的完整时间范围")

        # ============================================================
        # 第一步：先加载1分钟数据（必需，其他周期依赖于它）
        # ============================================================
        if progress_callback:
            progress_callback("正在分析数据库状态...", 5)
        
        # ============================================================
        # 第一步：加载1分钟数据（使用智能下载策略确保数据完整）
        # 关键：最终加载的数据必须严格符合用户指定的时间范围
        # ============================================================
        if progress_callback:
            progress_callback("正在加载1分钟K线数据...", 5)
        
        logger.info("[多周期] 开始加载1分钟K线数据")
        logger.info(f"[多周期] 用户指定范围: {self._start} ~ {self._end}")
        
        try:
            # 步骤1：从数据库加载用户指定的完整范围
            one_minute_bars = database.load_bar_data(
                symbol=self._vt_symbol,
                exchange=self._exchange,
                interval=Interval.MINUTE,
                start=self._start,
                end=self._end,
            )
            logger.info(f"[多周期] 从数据库加载: {len(one_minute_bars) if one_minute_bars else 0} 条")
            
            # 步骤2：分析数据库状态，决定是否需要从FUTU下载
            download_start, need_download = self._check_data_completeness(
                database, one_minute_bars, self._start, self._end
            )
            
            if need_download:
                if progress_callback:
                    progress_callback(f"数据不完整，正在从FUTU下载 ({download_start} ~ {self._end})...", 10)
                
                logger.info(f"[多周期] 需要从FUTU下载: {download_start} ~ {self._end}")
                
                # 步骤3：从FUTU下载并保存到数据库
                downloaded_bars = self._download_from_futu(
                    self._vt_symbol, self._exchange, download_start, self._end
                )
                
                if downloaded_bars:
                    database.save_bar_data(downloaded_bars)
                    logger.info(f"[多周期] 已下载并保存 {len(downloaded_bars)} 条数据")
                    
                    # 步骤4：重新从数据库加载用户指定的完整范围
                    one_minute_bars = database.load_bar_data(
                        symbol=self._vt_symbol,
                        exchange=self._exchange,
                        interval=Interval.MINUTE,
                        start=self._start,  # ✅ 重新加载完整范围
                        end=self._end,
                    )
                    logger.info(f"[多周期] 重新加载完整范围: {len(one_minute_bars) if one_minute_bars else 0} 条")
            
            if progress_callback:
                progress_callback(f"1分钟数据加载完成: {len(one_minute_bars) if one_minute_bars else 0} 条", 25)
                
        except Exception as e:
            logger.error(f"[多周期] 加载1分钟K线数据出错: {e}", exc_info=True)
            if progress_callback:
                progress_callback(f"加载1分钟数据失败: {e}", 0)
            return

        if not one_minute_bars:
            logger.warning("[多周期] 未找到1分钟K线数据")
            if progress_callback:
                progress_callback("未找到1分钟数据", 0)
            return

        # ============================================================
        # 第二步：从1分钟数据聚合所有大周期数据（5m/1H/4H）
        # 重要：不使用数据库中的大周期数据，全部从1分钟重新聚合
        # 使用 period_utils.py 中的港期时间划分方法
        # ============================================================
        if progress_callback:
            progress_callback("正在从1分钟数据聚合大周期 (5m/1H/4H)...", 35)
        
        logger.info(f"[多周期] 开始从1分钟数据聚合大周期（使用港期时间划分）")
        logger.info(f"[多周期] 1分钟数据数量: {len(one_minute_bars)}")
        
        # 定义聚合函数（在后台线程中执行）
        def aggregate_5min_bars(source_bars: list):
            """从1分钟聚合5分钟（使用港期时间划分）"""
            try:
                logger.info(f"[多周期] 开始聚合5分钟数据...")
                
                # 按5分钟周期分组
                period_groups = {}
                for bar in source_bars:
                    period_start = get_period_start(bar.datetime, Interval.MINUTE_5, self._exchange)
                    if period_start is None:
                        continue
                    if period_start not in period_groups:
                        period_groups[period_start] = []
                    period_groups[period_start].append(bar)
                
                # 聚合每个周期
                aggregated_bars = []
                for period_start in sorted(period_groups.keys()):
                    bars = period_groups[period_start]
                    if not bars:
                        continue
                    
                    bars.sort(key=lambda x: x.datetime)
                    
                    # 创建5分钟K线
                    bar_5m = BarData(
                        symbol=bars[0].symbol,
                        exchange=bars[0].exchange,
                        datetime=period_start,
                        interval=Interval.MINUTE_5,
                        open_price=bars[0].open_price,
                        high_price=max(b.high_price for b in bars),
                        low_price=min(b.low_price for b in bars),
                        close_price=bars[-1].close_price,
                        volume=sum(b.volume for b in bars),
                        turnover=sum(b.turnover for b in bars if hasattr(b, 'turnover') and b.turnover),
                        open_interest=bars[-1].open_interest if hasattr(bars[-1], 'open_interest') else 0,
                        gateway_name=bars[0].gateway_name,
                    )
                    aggregated_bars.append(bar_5m)
                
                logger.info(f"[多周期] 5分钟聚合完成: {len(aggregated_bars)} 条")
                return 'five_minute', aggregated_bars, None
            except Exception as e:
                logger.error(f"[多周期] 5分钟聚合失败: {e}", exc_info=True)
                return 'five_minute', None, e
        
        def aggregate_1hour_bars(source_bars: list):
            """从1分钟聚合1小时（使用港期时间划分）"""
            try:
                logger.info(f"[多周期] 开始聚合1小时数据...")
                
                # 使用 period_utils 中的方法
                aggregated_bars = aggregate_to_1hour_from_minutes(
                    source_bars,
                    symbol=self._vt_symbol,
                    exchange=self._exchange
                )
                
                logger.info(f"[多周期] 1小时聚合完成: {len(aggregated_bars)} 条")
                return 'one_hour', aggregated_bars, None
            except Exception as e:
                logger.error(f"[多周期] 1小时聚合失败: {e}", exc_info=True)
                return 'one_hour', None, e
        
        def aggregate_4hour_bars(source_bars: list):
            """从1分钟聚合4小时（使用港期时间划分）"""
            try:
                logger.info(f"[多周期] 开始聚合4小时数据...")
                
                # 按4小时周期分组
                period_groups = {}
                for bar in source_bars:
                    period_start, period_index = get_hkfe_4hour_period(bar.datetime)
                    if period_start is None:
                        continue
                    if period_start not in period_groups:
                        period_groups[period_start] = []
                    period_groups[period_start].append(bar)
                
                # 聚合每个周期
                aggregated_bars = []
                for period_start in sorted(period_groups.keys()):
                    bars = period_groups[period_start]
                    if not bars:
                        continue
                    
                    bars.sort(key=lambda x: x.datetime)
                    
                    # 创建4小时K线
                    bar_4h = BarData(
                        symbol=bars[0].symbol,
                        exchange=bars[0].exchange,
                        datetime=period_start,
                        interval=Interval.HOUR_4,
                        open_price=bars[0].open_price,
                        high_price=max(b.high_price for b in bars),
                        low_price=min(b.low_price for b in bars),
                        close_price=bars[-1].close_price,
                        volume=sum(b.volume for b in bars),
                        turnover=sum(b.turnover for b in bars if hasattr(b, 'turnover') and b.turnover),
                        open_interest=bars[-1].open_interest if hasattr(bars[-1], 'open_interest') else 0,
                        gateway_name=bars[0].gateway_name,
                    )
                    aggregated_bars.append(bar_4h)
                
                logger.info(f"[多周期] 4小时聚合完成: {len(aggregated_bars)} 条")
                return 'four_hour', aggregated_bars, None
            except Exception as e:
                logger.error(f"[多周期] 4小时聚合失败: {e}", exc_info=True)
                return 'four_hour', None, e
        
        # 并行聚合大周期数据
        tasks = [
            (aggregate_5min_bars, '5分钟'),
            (aggregate_1hour_bars, '1小时'),
            (aggregate_4hour_bars, '4小时'),
        ]
        
        results = {}
        
        # 使用线程池并行聚合
        with ThreadPoolExecutor(max_workers=3) as executor:
            # 提交所有聚合任务
            futures = {
                executor.submit(func, one_minute_bars): display_name
                for func, display_name in tasks
            }
            
            # 按完成顺序获取结果
            completed_count = 0
            for future in as_completed(futures):
                display_name = futures[future]
                interval_name, bars, error = future.result()
                
                if not error:
                    results[interval_name] = bars
                
                completed_count += 1
                progress = 35 + (completed_count * 15)  # 50%, 65%, 80%
                
                if progress_callback:
                    if error:
                        progress_callback(f"{display_name} 聚合失败: {error}", progress)
                    else:
                        bar_count = len(bars) if bars else 0
                        progress_callback(f"{display_name} 聚合完成: {bar_count} 条", progress)
        
        # 提取结果
        five_minute_bars = results.get('five_minute')
        one_hour_bars = results.get('one_hour')
        four_hour_bars = results.get('four_hour')

        if progress_callback:
            progress_callback("正在创建图表项...", 85)
        
        if progress_callback:
            progress_callback("正在创建图表项...", 88)
        
        logger.info(
            f"加载完成: 1m={len(one_minute_bars)}, "
            f"5m={len(five_minute_bars) if five_minute_bars else 0}, "
            f"1H={len(one_hour_bars) if one_hour_bars else 0}, "
            f"4H={len(four_hour_bars) if four_hour_bars else 0}"
        )

        # 主图 1m 数据
        if progress_callback:
            progress_callback("正在更新1分钟图表...", 90)
        
        self._chart.update_history(one_minute_bars)

        # 各周期 BarManager
        if progress_callback:
            progress_callback("正在创建5分钟图表管理器...", 91)
        
        if five_minute_bars:
            self._manager_5m = BarManager()
            self._manager_5m.update_history(five_minute_bars)

        if progress_callback:
            progress_callback("正在创建1小时图表管理器...", 92)
        
        if one_hour_bars:
            self._manager_1h = BarManager()
            self._manager_1h.update_history(one_hour_bars)

        if progress_callback:
            progress_callback("正在创建4小时图表管理器...", 93)
        
        if four_hour_bars:
            self._manager_4h = BarManager()
            self._manager_4h.update_history(four_hour_bars)

        if progress_callback:
            progress_callback("正在创建图表绘制项...", 94)
        
        candle_plot = self._chart.get_plot("candle")

        # 4H 绘制项
        if self._manager_4h:
            self._item_4h = CrossIndexCandleItem(
                manager=self._manager_4h,
                base_manager=self._main_manager,
                bearish_fill_opacity=self._style_4h.bearish_fill_opacity,
                bullish_color=self._style_4h.bullish_color,
                bearish_color=self._style_4h.bearish_color,
                interval=Interval.HOUR_4,
                pen_width=self._style_4h.pen_width,
            )
            self._item_4h.setVisible(self._style_4h.visible)
            candle_plot.addItem(self._item_4h)
            self._item_4h.update_history(self._manager_4h.get_all_bars())

        # 1H 绘制项
        if self._manager_1h:
            self._item_1h = CrossIndexCandleItem(
                manager=self._manager_1h,
                base_manager=self._main_manager,
                bearish_fill_opacity=self._style_1h.bearish_fill_opacity,
                bullish_color=self._style_1h.bullish_color,
                bearish_color=self._style_1h.bearish_color,
                interval=Interval.HOUR,
                pen_width=self._style_1h.pen_width,
            )
            self._item_1h.setVisible(self._style_1h.visible)
            candle_plot.addItem(self._item_1h)
            self._item_1h.update_history(self._manager_1h.get_all_bars())

        # 5m 绘制项
        if self._manager_5m:
            self._item_5m = CrossIndexCandleItem(
                manager=self._manager_5m,
                base_manager=self._main_manager,
                bearish_fill_opacity=self._style_5m.bearish_fill_opacity,
                bullish_color=self._style_5m.bullish_color,
                bearish_color=self._style_5m.bearish_color,
                interval=Interval.MINUTE_5,
                pen_width=self._style_5m.pen_width,
            )
            self._item_5m.setVisible(self._style_5m.visible)
            candle_plot.addItem(self._item_5m)
            self._item_5m.update_history(self._manager_5m.get_all_bars())

        # 连接透明度和显示开关信号
        self._connect_signals()

    # ---------------------------------------------------------------------
    def _connect_signals(self) -> None:
        candle_plot = self._chart.get_plot("candle")

        # 4H 透明度
        if self._slider_4h and self._item_4h:
            def on_4h_opacity_changed(value: int) -> None:
                opacity = max(0.0, min(1.0, value / 100.0))
                self._item_4h.set_bearish_fill_opacity(opacity)
                self._label_val_4h.setText(f"{int(opacity * 100)}%")
                self._item_4h.update()
                candle_plot.update()
                self._chart.update()
                self._chart.repaint()

            self._slider_4h.valueChanged.connect(on_4h_opacity_changed)

        # 1H 透明度
        if self._slider_1h and self._item_1h:
            def on_1h_opacity_changed(value: int) -> None:
                opacity = max(0.0, min(1.0, value / 100.0))
                self._item_1h.set_bearish_fill_opacity(opacity)
                self._label_val_1h.setText(f"{int(opacity * 100)}%")
                self._item_1h.update()
                candle_plot.update()
                self._chart.update()
                self._chart.repaint()

            self._slider_1h.valueChanged.connect(on_1h_opacity_changed)

        # 5m 透明度
        if self._slider_5m and self._item_5m:
            def on_5m_opacity_changed(value: int) -> None:
                opacity = max(0.0, min(1.0, value / 100.0))
                self._item_5m.set_bearish_fill_opacity(opacity)
                self._label_val_5m.setText(f"{int(opacity * 100)}%")
                self._item_5m.update()
                candle_plot.update()
                self._chart.update()
                self._chart.repaint()

            self._slider_5m.valueChanged.connect(on_5m_opacity_changed)

        # 显示开关
        if self._checkbox_4h and self._item_4h:
            def on_4h_toggled(checked: bool) -> None:
                self._item_4h.setVisible(checked)
                candle_plot.update()
                self._chart.update()
                self._chart.repaint()

            self._checkbox_4h.toggled.connect(on_4h_toggled)

        if self._checkbox_1h and self._item_1h:
            def on_1h_toggled(checked: bool) -> None:
                self._item_1h.setVisible(checked)
                candle_plot.update()
                self._chart.update()
                self._chart.repaint()

            self._checkbox_1h.toggled.connect(on_1h_toggled)

        if self._checkbox_5m and self._item_5m:
            def on_5m_toggled(checked: bool) -> None:
                self._item_5m.setVisible(checked)
                candle_plot.update()
                self._chart.update()
                self._chart.repaint()

            self._checkbox_5m.toggled.connect(on_5m_toggled)

    # ---------------------------------------------------------------------
    # 合约切换功能
    def switch_symbol(
        self,
        vt_symbol: str,
        exchange: Exchange,
        start: datetime,
        end: datetime,
        progress_callback=None
    ) -> None:
        """
        切换合约（T030）

        清理现有数据，重新加载新合约的数据，并重新初始化BarGenerator

        Args:
            vt_symbol: 新的合约代码
            exchange: 交易所
            start: 开始时间
            end: 结束时间
            progress_callback: 进度回调函数，接受 (message: str, progress: int) 参数
        """
        # 更新合约信息
        self._vt_symbol = vt_symbol
        self._exchange = exchange
        self._start = start
        self._end = end

        # 清理现有数据（T031）
        if progress_callback:
            progress_callback("正在清理旧数据...", 5)
        self._cleanup_data()

        # 重新加载数据（传递进度回调）
        self._load_data_and_build_items(progress_callback)

        # 重新初始化BarGenerator（T032）
        if self._realtime_enabled:
            if progress_callback:
                progress_callback("正在重新初始化实时更新...", 98)
            self._reinitialize_bar_generators()
        
        if progress_callback:
            progress_callback("加载完成！", 100)

    def _cleanup_data(self) -> None:
        """
        清理现有数据（T031）

        清理所有周期的BarManager、ChartItem、BarGenerator和价格线
        """
        # 清理BarManager数据
        if self._main_manager:
            self._main_manager.clear_all()
        if self._manager_5m:
            self._manager_5m.clear_all()
        if self._manager_1h:
            self._manager_1h.clear_all()
        if self._manager_4h:
            self._manager_4h.clear_all()

        # 清理ChartItem数据
        candle_plot = self._chart.get_plot("candle")
        if self._item_5m:
            candle_plot.removeItem(self._item_5m)
            self._item_5m = None
        if self._item_1h:
            candle_plot.removeItem(self._item_1h)
            self._item_1h = None
        if self._item_4h:
            candle_plot.removeItem(self._item_4h)
            self._item_4h = None

        # 清理BarGenerator实例
        self._bg_1m = None
        self._bg_5m = None
        self._bg_1h = None
        self._bg_4h = None
        self._realtime_enabled = False

        # 清理图表
        self._chart.clear_all()

        # 清理价格线（如果已启用画线交易功能）
        if hasattr(self._chart, 'get_price_line_manager'):
            price_line_manager = self._chart.get_price_line_manager()
            if price_line_manager:
                price_line_manager.clear_all()

    def _reinitialize_bar_generators(self) -> None:
        """
        重新初始化BarGenerator（T032）

        在切换合约后重新创建BarGenerator实例
        """
        # 重置实时更新标志
        self._realtime_enabled = False

        # 重新启用实时更新（会创建新的BarGenerator）
        self.enable_realtime()

    # ---------------------------------------------------------------------
    # 实时更新功能
    def enable_realtime(self) -> None:
        """
        启用实时更新功能

        创建多级BarGenerator，用于从Tick数据实时合成各周期K线
        """
        if self._realtime_enabled:
            return

        # 创建1分钟BarGenerator
        self._bg_1m = BarGenerator(
            on_bar=self._on_1m_bar,
            interval=Interval.MINUTE
        )

        # 创建5分钟BarGenerator
        # 注意：on_bar是1分钟K线回调（这里不需要），on_window_bar是合成K线回调
        if self._manager_5m:
            self._bg_5m = HKFEBarGenerator(
                on_bar=lambda bar: None,  # 1分钟K线回调（不需要）
                on_window_bar=self._on_5m_bar,  # 合成5分钟K线回调
                interval=Interval.MINUTE_5,
                exchange=self._exchange,
                symbol=self._vt_symbol
            )

        # 创建1小时BarGenerator
        if self._manager_1h:
            self._bg_1h = HKFEBarGenerator(
                on_bar=lambda bar: None,  # 1分钟K线回调（不需要）
                on_window_bar=self._on_1h_bar,  # 合成1小时K线回调
                interval=Interval.HOUR,
                exchange=self._exchange,
                symbol=self._vt_symbol
            )

        # 创建4小时BarGenerator
        if self._manager_4h:
            self._bg_4h = HKFEBarGenerator(
                on_bar=lambda bar: None,  # 1分钟K线回调（不需要）
                on_window_bar=self._on_4h_bar,  # 合成4小时K线回调
                interval=Interval.HOUR_4,
                exchange=self._exchange,
                symbol=self._vt_symbol
            )

        self._realtime_enabled = True
        logger.info("[多周期] 实时更新功能已启用")

    def update_tick(self, tick: TickData) -> None:
        """
        接收Tick数据并更新所有周期

        Args:
            tick: Tick数据
        """
        if not self._realtime_enabled or not self._bg_1m:
            return

        # 传递给1分钟BarGenerator，触发级联更新
        self._bg_1m.update_tick(tick)

        # 确保 tick 数据传递给价格突破监控（T055, T056）
        if self._chart and hasattr(self._chart, '_breakthrough_monitor') and self._chart._breakthrough_monitor:
            # 价格突破监控会自动从 ChartWidget 的内部机制获取 tick
            # 这里确保 tick 被传递（通过 ChartWidget 的 update_tick 或类似机制）
            # 注意：ChartWidget 的价格突破监控通常通过 process_tick_event 或 update_tick 触发
            # 由于 MultiTimeframeWidget 使用自己的 update_tick，需要确保 ChartWidget 也能接收到 tick
            if hasattr(self._chart, 'update_tick'):
                self._chart.update_tick(tick)

    def _on_1m_bar(self, bar: BarData) -> None:
        """
        1分钟K线更新回调

        更新主图（1分钟K线），并传递给大周期BarGenerator
        同时检查并更新正在构建的大周期K线（实时更新）
        """
        # 更新主图（1分钟K线）
        self._chart.update_bar(bar)

        # 传递给大周期BarGenerator
        if self._bg_5m:
            self._bg_5m.update_bar(bar)
            # 检查是否有正在构建的5分钟K线，如果有则实时更新
            # 注意：HKFEBarGenerator在周期开始时就会创建window_bar
            if self._bg_5m.window_bar and self._manager_5m and self._item_5m:
                # 确保window_bar的interval正确设置
                if not self._bg_5m.window_bar.interval:
                    self._bg_5m.window_bar.interval = Interval.MINUTE_5
                # 保护开盘价：从BarManager中获取已存在的bar，保留其开盘价
                existing_bar = self._manager_5m._bars.get(self._bg_5m.window_bar.datetime)
                if existing_bar:
                    # 如果bar已存在，保留其开盘价
                    preserved_open_price = existing_bar.open_price
                else:
                    # 如果bar不存在，使用window_bar的开盘价（新周期）
                    preserved_open_price = self._bg_5m.window_bar.open_price

                # 更新BarManager
                self._manager_5m.update_bar(self._bg_5m.window_bar)

                # 恢复开盘价：更新BarManager中的bar和window_bar
                if self._bg_5m.window_bar.datetime in self._manager_5m._bars:
                    self._manager_5m._bars[self._bg_5m.window_bar.datetime].open_price = preserved_open_price
                self._bg_5m.window_bar.open_price = preserved_open_price
                # 清除索引范围缓存（因为最后一根K线的范围会不断变化）
                if self._item_5m._bar_range_cache:
                    all_bars = self._manager_5m.get_all_bars()
                    if all_bars and all_bars[-1].datetime == self._bg_5m.window_bar.datetime:
                        # 如果是最后一根K线，清除其缓存
                        if self._bg_5m.window_bar.datetime in self._item_5m._bar_range_cache:
                            del self._item_5m._bar_range_cache[self._bg_5m.window_bar.datetime]
                # 再更新绘制项（BarManager.update_bar已经建立了索引）
                ix = self._manager_5m.get_index(self._bg_5m.window_bar.datetime)
                if ix is not None:
                    self._item_5m.update_bar(self._bg_5m.window_bar)
                    # 触发图表更新
                    candle_plot = self._chart.get_plot("candle")
                    candle_plot.update()
                    self._chart.update()

        if self._bg_1h:
            self._bg_1h.update_bar(bar)
            # 检查是否有正在构建的1小时K线，如果有则实时更新
            if self._bg_1h.hour_bar and self._manager_1h and self._item_1h:
                # 保护开盘价：从BarManager中获取已存在的bar，保留其开盘价
                existing_bar = self._manager_1h._bars.get(self._bg_1h.hour_bar.datetime)
                if existing_bar:
                    # 如果bar已存在，保留其开盘价
                    preserved_open_price = existing_bar.open_price
                else:
                    # 如果bar不存在，使用hour_bar的开盘价（新周期）
                    preserved_open_price = self._bg_1h.hour_bar.open_price

                # 更新BarManager
                self._manager_1h.update_bar(self._bg_1h.hour_bar)

                # 恢复开盘价：更新BarManager中的bar和hour_bar
                if self._bg_1h.hour_bar.datetime in self._manager_1h._bars:
                    self._manager_1h._bars[self._bg_1h.hour_bar.datetime].open_price = preserved_open_price
                self._bg_1h.hour_bar.open_price = preserved_open_price
                # 清除索引范围缓存（因为最后一根K线的范围会不断变化）
                if self._item_1h._bar_range_cache:
                    all_bars = self._manager_1h.get_all_bars()
                    if all_bars and all_bars[-1].datetime == self._bg_1h.hour_bar.datetime:
                        if self._bg_1h.hour_bar.datetime in self._item_1h._bar_range_cache:
                            del self._item_1h._bar_range_cache[self._bg_1h.hour_bar.datetime]
                self._item_1h.update_bar(self._bg_1h.hour_bar)
                candle_plot = self._chart.get_plot("candle")
                candle_plot.update()
                self._chart.update()

        if self._bg_4h:
            self._bg_4h.update_bar(bar)
            # 检查是否有正在构建的4小时K线，如果有则实时更新
            if self._bg_4h.window_bar and self._manager_4h and self._item_4h:
                # 保护开盘价：从BarManager中获取已存在的bar，保留其开盘价
                existing_bar = self._manager_4h._bars.get(self._bg_4h.window_bar.datetime)
                if existing_bar:
                    # 如果bar已存在，保留其开盘价
                    preserved_open_price = existing_bar.open_price
                else:
                    # 如果bar不存在，使用window_bar的开盘价（新周期）
                    preserved_open_price = self._bg_4h.window_bar.open_price

                # 更新BarManager
                self._manager_4h.update_bar(self._bg_4h.window_bar)

                # 恢复开盘价：更新BarManager中的bar和window_bar
                if self._bg_4h.window_bar.datetime in self._manager_4h._bars:
                    self._manager_4h._bars[self._bg_4h.window_bar.datetime].open_price = preserved_open_price
                self._bg_4h.window_bar.open_price = preserved_open_price
                # 清除索引范围缓存（因为最后一根K线的范围会不断变化）
                if self._item_4h._bar_range_cache:
                    all_bars = self._manager_4h.get_all_bars()
                    if all_bars and all_bars[-1].datetime == self._bg_4h.window_bar.datetime:
                        if self._bg_4h.window_bar.datetime in self._item_4h._bar_range_cache:
                            del self._item_4h._bar_range_cache[self._bg_4h.window_bar.datetime]
                self._item_4h.update_bar(self._bg_4h.window_bar)
                candle_plot = self._chart.get_plot("candle")
                candle_plot.update()
                self._chart.update()

    def _on_5m_bar(self, bar: BarData) -> None:
        """
        5分钟K线更新回调

        更新5分钟BarManager和绘制项
        """
        if self._manager_5m and self._item_5m:
            self._manager_5m.update_bar(bar)
            self._item_5m.update_bar(bar)
            # 触发图表更新
            candle_plot = self._chart.get_plot("candle")
            candle_plot.update()

    def _on_1h_bar(self, bar: BarData) -> None:
        """
        1小时K线更新回调

        更新1小时BarManager和绘制项
        """
        if self._manager_1h and self._item_1h:
            self._manager_1h.update_bar(bar)
            self._item_1h.update_bar(bar)
            # 触发图表更新
            candle_plot = self._chart.get_plot("candle")
            candle_plot.update()

    def _on_4h_bar(self, bar: BarData) -> None:
        """
        4小时K线更新回调

        更新4小时BarManager和绘制项
        """
        if self._manager_4h and self._item_4h:
            self._manager_4h.update_bar(bar)
            self._item_4h.update_bar(bar)
            # 触发图表更新
            candle_plot = self._chart.get_plot("candle")
            candle_plot.update()

    def get_last_bar(self) -> BarData | None:
        """
        获取最后的历史K线数据（用于模拟数据连续性）

        Returns:
            最后一根1分钟K线，如果没有数据则返回None
        """
        all_bars = self._main_manager.get_all_bars()
        if not all_bars:
            return None
        return all_bars[-1]

    # ---------------------------------------------------------------------
    # 画线交易功能
    def enable_drawing_order(
        self,
        main_engine: object,
        vt_symbol: str,
        on_drawing_click: callable | None = None
    ) -> None:
        """
        启用画线交易功能（T049）

        Args:
            main_engine: MainEngine 实例
            vt_symbol: 合约代码（完整的vt_symbol，如 "MHImain.HKFE"）
            on_drawing_click: 画线点击回调函数（可选，如果不提供则使用默认回调）
        """
        logger.info("[多周期] enable_drawing_order 被调用")
        logger.info(f"[多周期] vt_symbol: {vt_symbol}")

        if not self._chart:
            logger.error("[多周期] _chart 未初始化")
            return

        # 保存 MainEngine 引用（用于数据下载）
        self._main_engine = main_engine
        logger.info("[多周期] 已保存 MainEngine 引用")

        # 设置 main_engine 和 vt_symbol（T051）
        logger.info("[多周期] 设置 ChartWidget 的 main_engine 和 vt_symbol")
        self._chart.set_main_engine(main_engine)
        self._chart.set_vt_symbol(vt_symbol)

        # 设置画线点击回调（T052）
        if on_drawing_click:
            logger.info("[多周期] 设置画线点击回调")
            self._chart.set_drawing_click_callback(on_drawing_click)

        # 确保 DrawingOrderController 已初始化（T050）
        # 注意：ChartWidget 的 get_drawing_order_controller 会自动初始化
        controller = self._chart.get_drawing_order_controller()
        if controller:
            logger.info("[多周期] DrawingOrderController 已初始化")
            # 设置 main_engine 和 vt_symbol 到 controller
            if hasattr(controller, 'set_main_engine'):
                controller.set_main_engine(main_engine)
                logger.info("[多周期] 已设置 controller.main_engine")
            if hasattr(controller, 'set_vt_symbol'):
                controller.set_vt_symbol(vt_symbol)
                logger.info(f"[多周期] 已设置 controller.vt_symbol: {vt_symbol}")

            # 验证设置是否成功
            logger.debug(f"[多周期] controller._vt_symbol: {getattr(controller, '_vt_symbol', 'NOT SET')}")
            logger.debug(f"[多周期] controller._main_engine: {getattr(controller, '_main_engine', 'NOT SET')}")
        else:
            logger.error("[多周期] DrawingOrderController 未初始化")

        # 设置画线模式状态变化回调（用于ESC键退出等功能）
        # 注意：这里需要从外部传入回调，因为 MultiTimeframeWidget 不知道 ChartWindow 的 _on_drawing_mode_changed 方法
        # 这个回调会在 enable_drawing_order 时由 ChartWindow 设置

    def get_drawing_order_controller(self):
        """
        获取画线交易控制器

        Returns:
            DrawingOrderController 实例或 None
        """
        if not self._chart:
            return None
        return self._chart.get_drawing_order_controller()

    # ---------------------------------------------------------------------
    # 设置对话框功能
    def show_settings_dialog(self) -> None:
        """
        显示设置对话框

        用于从外部调用（例如从 ChartWindow）
        """
        self._show_settings_dialog()

    def _show_settings_dialog(self) -> None:
        """显示设置对话框"""
        # 获取当前设置
        current_settings = MultiTimeframeSettings(
            opacity_4h=self._style_4h.bearish_fill_opacity,
            visible_4h=self._style_4h.visible,
            opacity_1h=self._style_1h.bearish_fill_opacity,
            visible_1h=self._style_1h.visible,
            opacity_5m=self._style_5m.bearish_fill_opacity,
            visible_5m=self._style_5m.visible,
        )

        # 显示对话框，支持实时预览
        new_settings = show_settings_dialog(
            current_settings=current_settings,
            parent=self,
            on_apply=self._apply_settings,  # 确定时应用（用于保存设置）
            on_preview=self._apply_settings  # 实时预览（设置变化时立即应用）
        )

        # 如果用户点击取消，设置已经通过on_preview恢复到原始值了
        # 如果用户点击确定，设置已经通过on_apply应用了
        if new_settings:
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    "[MultiTimeframeWidget] 显示设置已更新",
                    "MultiTimeframeWidget"
                )

    def _apply_settings(self, settings: MultiTimeframeSettings) -> None:
        """
        应用新的显示设置

        Args:
            settings: 新的设置
        """
        # 更新4H设置
        if self._item_4h:
            self._item_4h.set_bearish_fill_opacity(settings.opacity_4h)
            self._item_4h.setVisible(settings.visible_4h)
            self._style_4h.bearish_fill_opacity = settings.opacity_4h
            self._style_4h.visible = settings.visible_4h
            # 更新UI控件
            if self._slider_4h:
                self._slider_4h.setValue(int(settings.opacity_4h * 100))
            if self._label_val_4h:
                self._label_val_4h.setText(f"{int(settings.opacity_4h * 100)}%")
            if self._checkbox_4h:
                self._checkbox_4h.setChecked(settings.visible_4h)

        # 更新1H设置
        if self._item_1h:
            self._item_1h.set_bearish_fill_opacity(settings.opacity_1h)
            self._item_1h.setVisible(settings.visible_1h)
            self._style_1h.bearish_fill_opacity = settings.opacity_1h
            self._style_1h.visible = settings.visible_1h
            # 更新UI控件
            if self._slider_1h:
                self._slider_1h.setValue(int(settings.opacity_1h * 100))
            if self._label_val_1h:
                self._label_val_1h.setText(f"{int(settings.opacity_1h * 100)}%")
            if self._checkbox_1h:
                self._checkbox_1h.setChecked(settings.visible_1h)

        # 更新5m设置
        if self._item_5m:
            self._item_5m.set_bearish_fill_opacity(settings.opacity_5m)
            self._item_5m.setVisible(settings.visible_5m)
            self._style_5m.bearish_fill_opacity = settings.opacity_5m
            self._style_5m.visible = settings.visible_5m
            # 更新UI控件
            if self._slider_5m:
                self._slider_5m.setValue(int(settings.opacity_5m * 100))
            if self._label_val_5m:
                self._label_val_5m.setText(f"{int(settings.opacity_5m * 100)}%")
            if self._checkbox_5m:
                self._checkbox_5m.setChecked(settings.visible_5m)

        # 触发图表更新
        candle_plot = self._chart.get_plot("candle")
        candle_plot.update()
        self._chart.update()
        self._chart.repaint()

    def get_current_settings(self) -> MultiTimeframeSettings:
        """
        获取当前显示设置

        Returns:
            当前设置
        """
        return MultiTimeframeSettings(
            opacity_4h=self._style_4h.bearish_fill_opacity,
            visible_4h=self._style_4h.visible,
            opacity_1h=self._style_1h.bearish_fill_opacity,
            visible_1h=self._style_1h.visible,
            opacity_5m=self._style_5m.bearish_fill_opacity,
            visible_5m=self._style_5m.visible,
        )


def create_demo_widget() -> MultiTimeframeWidget:
    """
    示例工厂函数：供 `run_multi_timeframe.py` 或其他模块直接复用。
    """
    start = datetime(2024, 11, 14)
    end = datetime(2024, 11, 18)

    widget = MultiTimeframeWidget(
        vt_symbol="MHImain",
        exchange=Exchange.HKFE,
        start=start,
        end=end,
    )
    return widget


def main() -> None:
    """
    独立运行示例入口（方便直接测试这个 widget）。
    """
    app = create_qapp()
    w = create_demo_widget()
    w.setWindowTitle("多周期K线叠加示例（1m + 5m + 1H + 4H）")
    w.resize(1400, 800)
    w.show()
    app.exec()


if __name__ == "__main__":
    main()


