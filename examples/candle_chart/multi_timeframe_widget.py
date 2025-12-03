"""
多周期叠加绘制 Widget

- 支持在同一张图上叠加显示 1m / 5m / 1H / 4H K 线
- 使用跨索引绘制（所有大周期都按 1 分钟时间轴对齐）
- 线型颜色、粗细、阴线填充透明度、是否显示等通过参数对象配置
- 仅绘制K线部分，不包含成交量（保持功能专一）
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

from vnpy.trader.ui import QtCore, QtWidgets, QtGui, create_qapp
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.database import get_database

from vnpy.chart import ChartWidget, CandleItem
from vnpy.chart.manager import BarManager
from vnpy.chart.base import PEN_WIDTH, UP_COLOR, DOWN_COLOR

try:
    from .cross_index_candle_item import CrossIndexCandleItem
    # from .one_hour_aggregator import aggregate_to_1hour  # 暂时注释：改为从数据库加载
except ImportError:
    # 如果相对导入失败（直接运行脚本时），使用绝对导入
    from cross_index_candle_item import CrossIndexCandleItem
    # from one_hour_aggregator import aggregate_to_1hour  # 暂时注释：改为从数据库加载


@dataclass
class TimeframeStyle:
    """
    多周期绘制样式配置。

    所有字段都可选，如果为 None/缺省则使用该周期的默认样式。
    """

    bullish_color: Optional[QtGui.QColor] = None      # 阳线颜色
    bearish_color: Optional[QtGui.QColor] = None      # 阴线轮廓颜色
    pen_width: Optional[int] = None                   # 线宽
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
        style_5m: Optional[TimeframeStyle] = None,
        style_1h: Optional[TimeframeStyle] = None,
        style_4h: Optional[TimeframeStyle] = None,
        parent: Optional[QtWidgets.QWidget] = None,
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
        self._manager_5m: Optional[BarManager] = None
        self._manager_1h: Optional[BarManager] = None
        self._manager_4h: Optional[BarManager] = None

        # 绘制项
        self._item_5m: Optional[CrossIndexCandleItem] = None
        self._item_1h: Optional[CrossIndexCandleItem] = None
        self._item_4h: Optional[CrossIndexCandleItem] = None

        # 控件
        self._slider_5m: Optional[QtWidgets.QSlider] = None
        self._slider_1h: Optional[QtWidgets.QSlider] = None
        self._slider_4h: Optional[QtWidgets.QSlider] = None

        self._checkbox_5m: Optional[QtWidgets.QCheckBox] = None
        self._checkbox_1h: Optional[QtWidgets.QCheckBox] = None
        self._checkbox_4h: Optional[QtWidgets.QCheckBox] = None

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
    # 数据加载与绘制项创建
    def _load_data_and_build_items(self) -> None:
        database = get_database()

        # 加载 1m / 5m / 1H / 4H
        one_minute_bars = database.load_bar_data(
            self._vt_symbol,
            self._exchange,
            interval=Interval.MINUTE,
            start=self._start,
            end=self._end,
        )

        if not one_minute_bars:
            print("未找到1分钟K线数据")
            return

        five_minute_bars = database.load_bar_data(
            self._vt_symbol,
            self._exchange,
            interval=Interval.MINUTE_5,
            start=self._start,
            end=self._end,
        )

        # 1小时K线：从数据库加载
        # 暂时注释掉聚合计算，改为直接从数据库加载
        # one_hour_bars = aggregate_to_1hour(one_minute_bars)
        one_hour_bars = database.load_bar_data(
            self._vt_symbol,
            self._exchange,
            interval=Interval.HOUR,
            start=self._start,
            end=self._end,
        )

        four_hour_bars = database.load_bar_data(
            self._vt_symbol,
            self._exchange,
            interval=Interval.HOUR_4,
            start=self._start,
            end=self._end,
        )

        print(
            f"加载完成: 1m={len(one_minute_bars)}, "
            f"5m={len(five_minute_bars)}, "
            f"1H={len(one_hour_bars)}, "
            f"4H={len(four_hour_bars)}"
        )

        # 主图 1m 数据
        self._chart.update_history(one_minute_bars)

        # 各周期 BarManager
        if five_minute_bars:
            self._manager_5m = BarManager()
            self._manager_5m.update_history(five_minute_bars)

        if one_hour_bars:
            self._manager_1h = BarManager()
            self._manager_1h.update_history(one_hour_bars)

        if four_hour_bars:
            self._manager_4h = BarManager()
            self._manager_4h.update_history(four_hour_bars)

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


