"""ChartWidget 图表更新模块 Mixin

处理图表数据更新和显示功能。
"""

from typing import TYPE_CHECKING

import pyqtgraph as pg      # type: ignore

from vnpy.trader.ui import QtGui, QtCore
from vnpy.trader.object import BarData

from .widget_mixin_base import ChartWidgetMixinBase

if TYPE_CHECKING:
    pass


class ChartWidgetChartMixin(ChartWidgetMixinBase):
    """图表更新和显示相关功能 Mixin"""
    
    def update_history(self, history: list[BarData]) -> None:
        """
        Update a list of bar data.
        """
        self._manager.update_history(history)

        for item in self._items.values():
            item.update_history(history)

        self._update_plot_limits()

        self.move_to_right()
    
    def update_bar(self, bar: BarData) -> None:
        """
        Update single bar data.
        """
        self._manager.update_bar(bar)

        for item in self._items.values():
            item.update_bar(bar)

        self._update_plot_limits()

        # 只有当视图在数据范围内且接近末尾时才自动跟随
        # 如果用户已将视图移到未来空间，则不自动移动
        data_count = self._manager.get_count()
        if self._right_ix <= data_count and self._right_ix >= (data_count - self._bar_count / 2):
            self.move_to_right()
        
        # Update breakthrough monitor with bar data
        if self._breakthrough_monitor:
            all_lines = self._price_line_manager.get_all_lines()
            self._breakthrough_monitor.update_bar(bar, all_lines)
    
    def _update_plot_limits(self) -> None:
        """
        Update the limit of plots.
        """
        for item, plot in self._item_plot_map.items():
            min_value, max_value = item.get_y_range()

            plot.setLimits(
                xMin=-1,
                xMax=self._manager.get_count() + self._future_bars,
                yMin=min_value,
                yMax=max_value
            )
    
    def _update_x_range(self) -> None:
        """
        Update the x-axis range of plots.
        """
        max_ix: int = self._right_ix
        min_ix: int = self._right_ix - self._bar_count

        for plot in self._plots.values():
            plot.setRange(xRange=(min_ix, max_ix), padding=0)
    
    def _update_y_range(self) -> None:
        """
        Update the y-axis range of plots.
        """
        if not self._first_plot:
            return

        view: pg.ViewBox = self._first_plot.getViewBox()
        view_range: list = view.viewRange()

        min_ix: int = max(0, int(view_range[0][0]))
        max_ix: int = min(self._manager.get_count(), int(view_range[0][1]))

        # Update limit for y-axis
        for item, plot in self._item_plot_map.items():
            y_range: tuple = item.get_y_range(min_ix, max_ix)
            plot.setRange(yRange=y_range)
    
    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        """
        Reimplement this method of parent to update current max_ix value.
        """
        if not self._first_plot:
            return

        view: pg.ViewBox = self._first_plot.getViewBox()
        view_range: list = view.viewRange()
        self._right_ix = max(0, view_range[0][1])

        super().paintEvent(event)
    
    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        """
        Reimplement this method of parent to zoom in/out.
        """
        delta: QtCore.QPoint = event.angleDelta()

        if delta.y() > 0:
            self._on_key_up()
        elif delta.y() < 0:
            self._on_key_down()
    
    def _on_key_left(self) -> None:
        """
        Move chart to left.
        """
        self._right_ix -= 1
        self._right_ix = max(self._right_ix, self._bar_count)

        self._update_x_range()

        if self._cursor:
            self._cursor.move_left()
            self._cursor.update_info()
    
    def _on_key_right(self) -> None:
        """
        Move chart to right.
        """
        self._right_ix += 1
        self._right_ix = min(self._right_ix, self._manager.get_count())

        self._update_x_range()

        if self._cursor:
            self._cursor.move_right()
            self._cursor.update_info()
    
    def _on_key_up(self) -> None:
        """
        Zoom in the chart.
        """
        self._bar_count = int(self._bar_count / 1.2)
        self._bar_count = max(int(self._bar_count), self.MIN_BAR_COUNT)

        self._update_x_range()

        if self._cursor:
            self._cursor.update_info()
    
    def _on_key_down(self) -> None:
        """
        Zoom out the chart.
        """
        self._bar_count = int(self._bar_count * 1.2)
        self._bar_count = min(int(self._bar_count), self._manager.get_count())

        self._update_x_range()

        if self._cursor:
            self._cursor.update_info()
    
    def move_to_right(self) -> None:
        """
        Move chart to the most right.
        """
        self._right_ix = self._manager.get_count()
        self._update_x_range()

        if self._cursor:
            self._cursor.update_info()

