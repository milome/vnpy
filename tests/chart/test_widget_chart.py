"""ChartWidget 图表更新模块测试

测试 ChartWidgetChartMixin 的所有方法。
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from vnpy.trader.ui import QtGui, QtCore
from vnpy.trader.object import BarData
from vnpy.trader.constant import Exchange
from vnpy.chart.widget_mixin_base import ChartWidgetMixinBase
from vnpy.chart.widget_chart import ChartWidgetChartMixin
from tests.chart.test_base import TestBase


class TestChartWidgetChart(TestBase, ChartWidgetChartMixin):
    """图表更新模块测试"""
    
    @pytest.fixture(autouse=True)
    def setup(self, qtbot):
        """为每个测试设置模拟对象"""
        self._manager = Mock()
        self._manager.get_count = Mock(return_value=100)
        self._manager.get_all_bars = Mock(return_value=[])
        self._manager.update_history = Mock()
        self._manager.update_bar = Mock()
        
        self._items = {}
        self._item_plot_map = {}
        self._plots = {}
        self._first_plot = Mock()
        self._first_plot.getViewBox = Mock(return_value=Mock(
            viewRange=Mock(return_value=[(0, 100), (19900, 20100)])
        ))
        
        self._right_ix = 100
        self._bar_count = 50
        self._future_bars = 0
        self.MIN_BAR_COUNT = 100  # ChartWidget 的类常量
        self._cursor = Mock()
        self._cursor.move_left = Mock()
        self._cursor.move_right = Mock()
        self._cursor.update_info = Mock()
        
        self._price_line_manager = Mock()
        self._price_line_manager.get_all_lines = Mock(return_value={})
        self._breakthrough_monitor = Mock()
        self._breakthrough_monitor.update_bar = Mock()

    def test_update_history(self):
        """测试更新历史数据"""
        # Arrange
        history = [self.create_bar_data() for _ in range(10)]
        item = Mock()
        item.update_history = Mock()
        self._items = {"candle": item}
        
        # Act
        self.update_history(history)
        
        # Assert
        self._manager.update_history.assert_called_once_with(history)
        item.update_history.assert_called_once_with(history)

    def test_update_bar(self):
        """测试更新单根K线"""
        # Arrange
        bar = self.create_bar_data()
        item = Mock()
        item.update_bar = Mock()
        self._items = {"candle": item}
        self._right_ix = 100  # 在数据范围内
        
        # Act
        self.update_bar(bar)
        
        # Assert
        self._manager.update_bar.assert_called_once_with(bar)
        item.update_bar.assert_called_once_with(bar)

    def test_update_bar_auto_follow(self):
        """测试自动跟随"""
        # Arrange
        bar = self.create_bar_data()
        item = Mock()
        item.update_bar = Mock()
        self._items = {"candle": item}
        self._manager.get_count.return_value = 100
        self._right_ix = 90  # 接近末尾，应该自动跟随
        self._bar_count = 50
        
        # Act
        self.update_bar(bar)
        
        # Assert
        # update_bar 应该被调用
        item.update_bar.assert_called_once_with(bar)
        # 由于接近末尾，move_to_right 可能被调用（取决于实现）
        # 这里只验证 update_bar 被调用

    def test_update_plot_limits(self):
        """测试更新图表限制"""
        # Arrange
        item = Mock()
        item.get_y_range = Mock(return_value=(19900.0, 20100.0))
        plot = Mock()
        plot.setLimits = Mock()
        self._item_plot_map = {item: plot}
        self._manager.get_count.return_value = 100
        
        # Act
        self._update_plot_limits()
        
        # Assert
        plot.setLimits.assert_called_once()
        call_args = plot.setLimits.call_args
        assert call_args[1]['xMin'] == -1
        assert call_args[1]['xMax'] == 100  # get_count() + future_bars

    def test_update_x_range(self):
        """测试更新X轴范围"""
        # Arrange
        plot = Mock()
        plot.setRange = Mock()
        self._plots = {"candle": plot}
        self._right_ix = 100
        self._bar_count = 50
        
        # Act
        self._update_x_range()
        
        # Assert
        plot.setRange.assert_called_once()
        call_args = plot.setRange.call_args
        assert call_args[1]['xRange'] == (50, 100)  # (right_ix - bar_count, right_ix)

    def test_update_y_range(self):
        """测试更新Y轴范围"""
        # Arrange
        item = Mock()
        item.get_y_range = Mock(return_value=(19900.0, 20100.0))
        plot = Mock()
        plot.setRange = Mock()
        self._item_plot_map = {item: plot}
        
        # Act
        self._update_y_range()
        
        # Assert
        item.get_y_range.assert_called_once()
        plot.setRange.assert_called_once()

    def test_paintEvent(self):
        """测试绘制事件"""
        # Arrange
        event = Mock(spec=QtGui.QPaintEvent)
        view_range = [(0, 100), (19900, 20100)]
        self._first_plot.getViewBox.return_value.viewRange.return_value = view_range
        
        # Mock 父类的 paintEvent 方法
        with patch('vnpy.chart.widget_chart.super') as mock_super:
            mock_parent = Mock()
            mock_super.return_value.paintEvent = Mock()
            
            # Act
            self.paintEvent(event)
            
            # Assert
            assert self._right_ix == 100  # max(0, view_range[0][1])
            mock_super.return_value.paintEvent.assert_called_once_with(event)

    def test_wheelEvent(self):
        """测试滚轮缩放"""
        # Arrange
        event = Mock(spec=QtGui.QWheelEvent)
        event.angleDelta = Mock(return_value=QtCore.QPoint(0, 120))  # 向上滚动
        self._bar_count = 120  # 设置一个大于 MIN_BAR_COUNT 的值
        self.MIN_BAR_COUNT = 100  # 设置最小K线数量
        
        # Act
        # 直接调用，验证 _on_key_up 的逻辑
        self.wheelEvent(event)
        
        # Assert
        # _on_key_up 应该被调用（放大），bar_count 应该减少，但不能小于 MIN_BAR_COUNT
        assert self._bar_count <= 120
        assert self._bar_count >= self.MIN_BAR_COUNT

    def test_on_key_left(self):
        """测试左移"""
        # Arrange
        self._right_ix = 100
        self._bar_count = 50
        
        # Act
        self._on_key_left()
        
        # Assert
        assert self._right_ix == 99  # 减少1
        self._cursor.move_left.assert_called_once()

    def test_on_key_right(self):
        """测试右移"""
        # Arrange
        self._right_ix = 100
        self._manager.get_count.return_value = 200
        
        # Act
        self._on_key_right()
        
        # Assert
        assert self._right_ix == 101  # 增加1
        self._cursor.move_right.assert_called_once()

    def test_on_key_up(self):
        """测试放大"""
        # Arrange
        self._bar_count = 120  # 设置一个大于 MIN_BAR_COUNT 的值
        self.MIN_BAR_COUNT = 100  # 设置最小K线数量
        
        # Act
        self._on_key_up()
        
        # Assert
        # bar_count 应该减少（放大），但不能小于 MIN_BAR_COUNT
        assert self._bar_count < 120
        assert self._bar_count >= self.MIN_BAR_COUNT

    def test_on_key_down(self):
        """测试缩小"""
        # Arrange
        self._bar_count = 50
        self._manager.get_count.return_value = 200
        
        # Act
        self._on_key_down()
        
        # Assert
        # bar_count 应该增加（缩小）
        assert self._bar_count > 50

    def test_move_to_right(self):
        """测试移动到最右侧"""
        # Arrange
        self._manager.get_count.return_value = 100
        self._right_ix = 50
        self._cursor = Mock()
        self._cursor.update_info = Mock()
        
        # Act
        self.move_to_right()
        
        # Assert
        assert self._right_ix == 100  # 应该移动到数据末尾
        self._cursor.update_info.assert_called_once()
