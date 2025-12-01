"""ChartWidget 光标类测试

测试 ChartCursor 类的所有方法。
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from vnpy.trader.ui import QtGui, QtCore
from vnpy.trader.object import BarData
from vnpy.trader.constant import Exchange
from vnpy.chart.widget_cursor import ChartCursor
from vnpy.chart.manager import BarManager
from vnpy.chart.item import ChartItem
from tests.chart.test_base import TestBase


class TestChartCursor(TestBase):
    """光标类测试"""
    
    @pytest.fixture(autouse=True)
    def setup(self, qtbot):
        """为每个测试设置模拟对象"""
        self.widget = Mock()
        self.widget.scene = Mock(return_value=Mock(sigMouseMoved=Mock(connect=Mock())))
        
        self.manager = Mock(spec=BarManager)
        self.manager.get_count = Mock(return_value=100)
        self.manager.get_datetime = Mock(return_value=datetime.now())
        self.manager.get_bar = Mock(return_value=self.create_bar_data())
        
        self.plots = {
            "candle": Mock(),
            "volume": Mock()
        }
        self.plots["candle"].getViewBox = Mock(return_value=Mock(
            sceneBoundingRect=Mock(return_value=Mock(contains=Mock(return_value=True))),
            mapSceneToView=Mock(return_value=QtCore.QPointF(50, 20000))
        ))
        self.plots["candle"].getAxis = Mock(return_value=Mock(width=Mock(return_value=50), height=Mock(return_value=20)))
        self.plots["candle"].addItem = Mock()
        
        self.item_plot_map = {
            Mock(spec=ChartItem): self.plots["candle"]
        }
        self.item_plot_map[list(self.item_plot_map.keys())[0]].get_info_text = Mock(return_value="Info text")
        
        # Create cursor instance
        self.cursor = ChartCursor(
            self.widget,
            self.manager,
            self.plots,
            self.item_plot_map
        )

    def test_init(self):
        """测试初始化"""
        # Assert
        assert self.cursor._widget == self.widget
        assert self.cursor._manager == self.manager
        assert self.cursor._plots == self.plots
        assert self.cursor._item_plot_map == self.item_plot_map
        assert self.cursor._x == 0
        assert self.cursor._y == 0.0
        assert self.cursor._plot_name == ""

    def test_init_ui(self):
        """测试UI初始化"""
        # Assert
        assert hasattr(self.cursor, '_v_lines')
        assert hasattr(self.cursor, '_h_lines')
        assert hasattr(self.cursor, '_views')
        assert hasattr(self.cursor, '_y_labels')
        assert hasattr(self.cursor, '_x_label')
        assert hasattr(self.cursor, '_infos')

    def test_mouse_moved(self):
        """测试鼠标移动"""
        # Arrange
        evt = (100, 200)
        view = Mock()
        view.sceneBoundingRect = Mock(return_value=Mock(contains=Mock(return_value=True)))
        view.mapSceneToView = Mock(return_value=QtCore.QPointF(50, 20000))
        self.cursor._views = {"candle": view}
        self.cursor._update_line = Mock()
        self.cursor._update_label = Mock()
        self.cursor.update_info = Mock()
        
        # Act
        self.cursor._mouse_moved(evt)
        
        # Assert
        assert self.cursor._x == 50
        assert self.cursor._y == 20000.0
        assert self.cursor._plot_name == "candle"

    def test_update_line(self):
        """测试更新线条"""
        # Arrange
        self.cursor._x = 50
        self.cursor._y = 20000.0
        self.cursor._plot_name = "candle"
        v_line = Mock()
        h_line = Mock()
        self.cursor._v_lines = {"candle": v_line}
        self.cursor._h_lines = {"candle": h_line}
        
        # Act
        self.cursor._update_line()
        
        # Assert
        v_line.setPos.assert_called_once_with(50)
        v_line.show.assert_called_once()
        h_line.setPos.assert_called_once_with(20000.0)
        h_line.show.assert_called_once()

    def test_update_label(self):
        """测试更新标签"""
        # Arrange
        self.cursor._x = 50
        self.cursor._y = 20000.0
        self.cursor._plot_name = "candle"
        self.cursor._manager.get_datetime.return_value = datetime.now()
        
        y_label = Mock()
        x_label = Mock()
        self.cursor._y_labels = {"candle": y_label}
        self.cursor._x_label = x_label
        
        bottom_plot = Mock()
        bottom_plot.getAxis = Mock(return_value=Mock(width=Mock(return_value=50), height=Mock(return_value=20)))
        self.cursor._plots = {"candle": bottom_plot}
        
        bottom_view = Mock()
        bottom_view.sceneBoundingRect = Mock(return_value=Mock(bottomRight=Mock(return_value=QtCore.QPointF(100, 200))))
        bottom_view.mapSceneToView = Mock(return_value=QtCore.QPointF(50, 20000))
        self.cursor._views = {"candle": bottom_view}
        
        # Act
        self.cursor._update_label()
        
        # Assert
        y_label.setText.assert_called_once()
        y_label.show.assert_called_once()
        x_label.setText.assert_called_once()
        x_label.show.assert_called_once()

    def test_update_info(self):
        """测试更新信息"""
        # Arrange
        self.cursor._x = 50
        item = list(self.item_plot_map.keys())[0]
        item.get_info_text = Mock(return_value="Info text")
        plot = self.item_plot_map[item]
        
        info = Mock()
        self.cursor._infos = {"candle": info}
        self.cursor._plots = {"candle": plot}
        
        view = Mock()
        view.sceneBoundingRect = Mock(return_value=Mock(topLeft=Mock(return_value=QtCore.QPointF(0, 0))))
        view.mapSceneToView = Mock(return_value=QtCore.QPointF(0, 0))
        self.cursor._views = {"candle": view}
        
        # Act
        self.cursor.update_info()
        
        # Assert
        item.get_info_text.assert_called_once_with(50)
        info.setText.assert_called_once()
        info.show.assert_called_once()

    def test_move_right(self):
        """测试右移"""
        # Arrange
        self.cursor._x = 50
        self.cursor._manager.get_count.return_value = 100
        self.cursor._update_after_move = Mock()
        
        # Act
        self.cursor.move_right()
        
        # Assert
        assert self.cursor._x == 51
        self.cursor._update_after_move.assert_called_once()

    def test_move_left(self):
        """测试左移"""
        # Arrange
        self.cursor._x = 50
        self.cursor._update_after_move = Mock()
        
        # Act
        self.cursor.move_left()
        
        # Assert
        assert self.cursor._x == 49
        self.cursor._update_after_move.assert_called_once()

    def test_clear_all(self):
        """测试清除所有"""
        # Arrange
        self.cursor._x = 50
        self.cursor._y = 20000.0
        self.cursor._plot_name = "candle"
        
        v_line = Mock()
        h_line = Mock()
        y_label = Mock()
        x_label = Mock()
        self.cursor._v_lines = {"candle": v_line}
        self.cursor._h_lines = {"candle": h_line}
        self.cursor._y_labels = {"candle": y_label}
        self.cursor._x_label = x_label
        
        # Act
        self.cursor.clear_all()
        
        # Assert
        assert self.cursor._x == 0
        assert self.cursor._y == 0.0
        assert self.cursor._plot_name == ""
        v_line.hide.assert_called_once()
        h_line.hide.assert_called_once()
        y_label.hide.assert_called_once()
        x_label.hide.assert_called_once()
