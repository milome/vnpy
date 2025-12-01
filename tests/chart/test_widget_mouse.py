"""ChartWidget 鼠标事件模块测试

测试 ChartWidgetMouseMixin 的所有方法。
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from vnpy.trader.ui import QtGui, QtCore
from vnpy.chart.widget_mixin_base import ChartWidgetMixinBase
from vnpy.chart.widget_mouse import ChartWidgetMouseMixin
from vnpy.chart.price_line import PriceLineManager, PriceLineType, PriceLineItem
from tests.chart.test_base import TestBase


# Mock PriceLineItem for testing
class MockPriceLineItem:
    """Mock PriceLineItem for testing"""
    def __init__(self, line_id: str, price: float, line_type: PriceLineType, direction: str, movable: bool = False):
        self._line_id = line_id
        self._price = price
        self._line_type = line_type
        self._direction = direction
        self.movable = movable
        self.label = Mock()
        self.setVisible = Mock()
        self.scene = Mock(return_value=None)

    def get_line_id(self) -> str:
        return self._line_id
    
    def get_price(self) -> float:
        return self._price
    
    def get_line_type(self) -> PriceLineType:
        return self._line_type
    
    def get_direction(self) -> str:
        return self._direction
    
    def set_price(self, price: float, precision: int = 0):
        self._price = price


class TestChartWidgetMouse(TestBase, ChartWidgetMouseMixin):
    """鼠标事件模块测试"""
    
    @pytest.fixture(autouse=True)
    def setup(self, qtbot):
        """为每个测试设置模拟对象"""
        self._main_engine = Mock()
        self._main_engine.write_log = Mock()
        self._main_engine.send_order = Mock(return_value="order_123")
        self._main_engine.get_contract = Mock(return_value=Mock(gateway_name="TEST"))
        self._main_engine.get_all_gateway_names = Mock(return_value=["TEST"])
        self._main_engine.get_gateway = Mock(return_value=None)
        self._main_engine.get_tick = Mock(return_value=None)
        self._main_engine.get_order = Mock(return_value=None)
        self._main_engine.cancel_order = Mock(return_value=True)
        
        self._vt_symbol = "MHI2512.HKFE"
        self._price_line_manager = Mock(spec=PriceLineManager)
        self._price_line_manager.get_all_lines = Mock(return_value={})
        self._price_line_manager.get_line = Mock(return_value=None)
        self._price_line_manager.delete_line = Mock(return_value=True)
        self._price_line_manager.create_line = Mock(return_value="new_line_id")
        self._price_line_manager.clear_preview_lines = Mock(return_value=0)
        
        self._drawing_order_controller = Mock()
        self._drawing_order_controller.is_enabled = Mock(return_value=False)
        self._drawing_order_controller.show_preview_line = Mock()
        self._drawing_order_controller.update_preview_line = Mock()
        self._drawing_order_controller.get_order_id_for_line = Mock(return_value=None)
        self._drawing_order_controller.remove_order_line = Mock()
        self._drawing_order_controller._pending_order_params = {}
        self._drawing_order_controller._pending_line_relations = {}
        
        self._price_line_drag_handler = Mock()
        self._price_line_drag_handler.is_dragging = Mock(return_value=False)
        self._price_line_drag_handler.is_dragging_from_entry = Mock(return_value=False)
        self._price_line_drag_handler.get_dragging_line = Mock(return_value=None)
        self._price_line_drag_handler.get_entry_line = Mock(return_value=None)
        self._price_line_drag_handler.get_preview_line = Mock(return_value=None)
        self._price_line_drag_handler.find_line_near_point = Mock(return_value=None)
        self._price_line_drag_handler.start_drag = Mock()
        self._price_line_drag_handler.start_drag_from_entry = Mock()
        self._price_line_drag_handler.end_drag = Mock(return_value=None)
        self._price_line_drag_handler.cancel_drag = Mock()
        self._price_line_drag_handler.update_drag = Mock()
        self._price_line_drag_handler.convert_scene_to_price = Mock(return_value=None)
        self._price_line_drag_handler.set_preview_line = Mock()
        
        self._first_plot = Mock()
        self._first_plot.getViewBox = Mock(return_value=Mock(
            mapSceneToView=Mock(return_value=Mock(y=Mock(return_value=20000.0))),
            height=Mock(return_value=400),
            viewRange=Mock(return_value=[(0, 100), (19900, 20100)])
        ))
        self._first_plot.addItem = Mock()
        self._first_plot.removeItem = Mock()
        
        self._price_precision = 0
        self._on_drawing_click = None
        self._on_drawing_mode_changed = None
        self._last_double_click_close = {}
        self._double_click_debounce_ttl = 1.0
        self._entry_line_relations = {}
        self._price_line_database = Mock()
        
        # Mock methods
        self.get_price_line_manager = Mock(return_value=self._price_line_manager)
        self.get_drawing_order_controller = Mock(return_value=self._drawing_order_controller)
        self.mapToScene = Mock(return_value=Mock())
        self.setCursor = Mock()
        
        # Mock super() calls
        self.super_mouseMoveEvent = Mock()
        self.super_mousePressEvent = Mock()
        self.super_mouseReleaseEvent = Mock()
        self.super_mouseDoubleClickEvent = Mock()

    def test_mouseMoveEvent_drawing_mode(self):
        """测试画线下单模式下的鼠标移动"""
        # Arrange
        event = Mock(spec=QtGui.QMouseEvent)
        event.pos = Mock(return_value=Mock())
        self._drawing_order_controller.is_enabled.return_value = True
        
        # Act
        with patch.object(self, 'super', return_value=Mock(mouseMoveEvent=self.super_mouseMoveEvent)):
            self.mouseMoveEvent(event)
        
        # Assert
        self._drawing_order_controller.update_preview_line.assert_called_once()

    def test_mouseMoveEvent_dragging(self):
        """测试拖拽价格线"""
        # Arrange
        event = Mock(spec=QtGui.QMouseEvent)
        event.pos = Mock(return_value=Mock())
        self._price_line_drag_handler.is_dragging.return_value = True
        self._price_line_drag_handler.convert_scene_to_price.return_value = 20001.0
        
        line = MockPriceLineItem("line_123", 20000.0, PriceLineType.PENDING, "long", movable=True)
        self._price_line_drag_handler.get_dragging_line.return_value = line
        
        # Act
        with patch.object(self, 'super', return_value=Mock(mouseMoveEvent=self.super_mouseMoveEvent)):
            self.mouseMoveEvent(event)
        
        # Assert
        self._price_line_drag_handler.update_drag.assert_called()

    def test_mouseMoveEvent_hover_detection(self):
        """测试悬停检测"""
        # Arrange
        event = Mock(spec=QtGui.QMouseEvent)
        event.pos = Mock(return_value=Mock())
        self._price_line_drag_handler.is_dragging.return_value = False
        
        line = MockPriceLineItem("line_123", 20000.0, PriceLineType.PENDING, "long", movable=True)
        self._price_line_drag_handler.find_line_near_point.return_value = line
        
        # Act
        with patch.object(self, 'super', return_value=Mock(mouseMoveEvent=self.super_mouseMoveEvent)):
            self.mouseMoveEvent(event)
        
        # Assert
        self.setCursor.assert_called()

    def test_mousePressEvent_start_drag(self):
        """测试开始拖拽"""
        # Arrange
        event = Mock(spec=QtGui.QMouseEvent)
        event.button = Mock(return_value=QtCore.Qt.MouseButton.LeftButton)
        event.pos = Mock(return_value=Mock())
        event.accept = Mock()
        
        line = MockPriceLineItem("line_123", 20000.0, PriceLineType.PENDING, "long", movable=True)
        self._price_line_drag_handler.find_line_near_point.return_value = line
        
        # Act
        with patch.object(self, 'super', return_value=Mock(mousePressEvent=self.super_mousePressEvent)):
            self.mousePressEvent(event)
        
        # Assert
        self._price_line_drag_handler.start_drag.assert_called_once_with(line)
        event.accept.assert_called_once()

    def test_mousePressEvent_drag_from_entry(self):
        """测试从入场线拖拽"""
        # Arrange
        event = Mock(spec=QtGui.QMouseEvent)
        event.button = Mock(return_value=QtCore.Qt.MouseButton.LeftButton)
        event.pos = Mock(return_value=Mock())
        event.accept = Mock()
        
        entry_line = MockPriceLineItem("entry_123", 20000.0, PriceLineType.ENTRY, "long", movable=False)
        self._price_line_drag_handler.find_line_near_point.side_effect = [None, entry_line]
        
        # Act
        with patch.object(self, 'super', return_value=Mock(mousePressEvent=self.super_mousePressEvent)):
            self.mousePressEvent(event)
        
        # Assert
        self._price_line_drag_handler.start_drag_from_entry.assert_called_once_with(entry_line)

    def test_mousePressEvent_drawing_click(self):
        """测试画线下单点击"""
        # Arrange
        event = Mock(spec=QtGui.QMouseEvent)
        event.button = Mock(return_value=QtCore.Qt.MouseButton.LeftButton)
        event.pos = Mock(return_value=Mock())
        event.accept = Mock()
        
        self._drawing_order_controller.is_enabled.return_value = True
        callback = Mock()
        self._on_drawing_click = callback
        
        # Act
        with patch.object(self, 'super', return_value=Mock(mousePressEvent=self.super_mousePressEvent)):
            self.mousePressEvent(event)
        
        # Assert
        callback.assert_called_once()

    def test_mouseReleaseEvent_end_drag(self):
        """测试结束拖拽"""
        # Arrange
        event = Mock(spec=QtGui.QMouseEvent)
        event.accept = Mock()
        
        line = MockPriceLineItem("line_123", 20000.0, PriceLineType.PENDING, "long", movable=True)
        self._price_line_drag_handler.is_dragging.return_value = True
        self._price_line_drag_handler.get_dragging_line.return_value = line
        self._price_line_drag_handler.end_drag.return_value = 20001.0
        
        # Act
        with patch.object(self, 'super', return_value=Mock(mouseReleaseEvent=self.super_mouseReleaseEvent)):
            self.mouseReleaseEvent(event)
        
        # Assert
        self._price_line_drag_handler.end_drag.assert_called_once()
        event.accept.assert_called_once()

    def test_mouseReleaseEvent_create_stop_loss_take_profit(self):
        """测试创建止损止盈线"""
        # Arrange
        event = Mock(spec=QtGui.QMouseEvent)
        event.accept = Mock()
        
        entry_line = MockPriceLineItem("entry_123", 20000.0, PriceLineType.ENTRY, "long", movable=False)
        preview_line = MockPriceLineItem("preview_123", 19900.0, PriceLineType.STOP_LOSS, "long", movable=True)
        
        self._price_line_drag_handler.is_dragging.return_value = True
        self._price_line_drag_handler.is_dragging_from_entry.return_value = True
        self._price_line_drag_handler.get_entry_line.return_value = entry_line
        self._price_line_drag_handler.get_preview_line.return_value = preview_line
        self._price_line_drag_handler.end_drag.return_value = 19900.0
        
        # Act
        with patch.object(self, 'super', return_value=Mock(mouseReleaseEvent=self.super_mouseReleaseEvent)):
            self.mouseReleaseEvent(event)
        
        # Assert
        # 应该创建止损/止盈线
        assert self._price_line_manager.create_line.called or self._price_line_manager.delete_line.called

    def test_mouseDoubleClickEvent_pending_line(self):
        """测试挂单线双击"""
        # Arrange
        event = Mock(spec=QtGui.QMouseEvent)
        event.accept = Mock()
        
        line = MockPriceLineItem("pending_123", 20000.0, PriceLineType.PENDING, "long", movable=True)
        self._price_line_drag_handler.find_line_near_point.return_value = line
        
        # Mock QMessageBox
        with patch('vnpy.chart.widget_mouse.QtWidgets.QMessageBox') as mock_msgbox:
            mock_msgbox.question.return_value = mock_msgbox.StandardButton.Yes
            
            # Act
            with patch.object(self, 'super', return_value=Mock(mouseDoubleClickEvent=self.super_mouseDoubleClickEvent)):
                self.mouseDoubleClickEvent(event)
            
            # Assert
            event.accept.assert_called_once()

    def test_mouseDoubleClickEvent_entry_line(self):
        """测试入场线双击平仓"""
        # Arrange
        event = Mock(spec=QtGui.QMouseEvent)
        event.accept = Mock()
        
        line = MockPriceLineItem("entry_123", 20000.0, PriceLineType.ENTRY, "long", movable=False)
        line.get_volume = Mock(return_value=10.0)
        self._price_line_drag_handler.find_line_near_point.return_value = line
        
        # Mock QMessageBox
        with patch('vnpy.chart.widget_mouse.QtWidgets.QMessageBox') as mock_msgbox:
            mock_msgbox.question.return_value = mock_msgbox.StandardButton.Yes
            
            # Act
            with patch.object(self, 'super', return_value=Mock(mouseDoubleClickEvent=self.super_mouseDoubleClickEvent)):
                self.mouseDoubleClickEvent(event)
            
            # Assert
            event.accept.assert_called_once()

    def test_mouseDoubleClickEvent_stop_loss_take_profit(self):
        """测试止损止盈线双击删除"""
        # Arrange
        event = Mock(spec=QtGui.QMouseEvent)
        event.accept = Mock()
        
        line = MockPriceLineItem("stop_loss_123", 19900.0, PriceLineType.STOP_LOSS, "long", movable=True)
        self._price_line_drag_handler.find_line_near_point.return_value = line
        self._price_line_manager.get_line.return_value = line
        
        # Act
        with patch.object(self, 'super', return_value=Mock(mouseDoubleClickEvent=self.super_mouseDoubleClickEvent)):
            self.mouseDoubleClickEvent(event)
        
        # Assert
        self._price_line_manager.delete_line.assert_called_once_with("stop_loss_123")
        event.accept.assert_called_once()

    def test_update_related_lines_on_drag(self):
        """测试拖拽时更新关联线"""
        # Arrange
        line = MockPriceLineItem("pending_123", 20000.0, PriceLineType.PENDING, "long", movable=True)
        self._price_line_manager.get_all_lines.return_value = {"pending_123": line}
        
        relations = {
            "stop_loss": {"line_id": "stop_loss_123", "points": 50},
            "take_profit": {"line_id": "take_profit_123", "points": 100}
        }
        self._drawing_order_controller._pending_line_relations = {"pending_123": relations}
        self._drawing_order_controller._pending_order_params = {
            "pending_123": {
                "params": {"direction": Mock(value="多")},
                "contract": Mock(pricetick=1.0)
            }
        }
        
        stop_loss_line = MockPriceLineItem("stop_loss_123", 19950.0, PriceLineType.STOP_LOSS, "long", movable=True)
        take_profit_line = MockPriceLineItem("take_profit_123", 20100.0, PriceLineType.TAKE_PROFIT, "long", movable=True)
        self._price_line_manager.get_line.side_effect = [stop_loss_line, take_profit_line]
        
        # Act
        self._update_related_lines_on_drag(line, 20001.0)
        
        # Assert
        # 止损线和止盈线的价格应该被更新
        assert stop_loss_line.set_price.called
        assert take_profit_line.set_price.called

    def test_update_points_on_line_drag(self):
        """测试更新点数"""
        # Arrange
        dragged_line = MockPriceLineItem("stop_loss_123", 19950.0, PriceLineType.STOP_LOSS, "long", movable=True)
        pending_line = MockPriceLineItem("pending_123", 20000.0, PriceLineType.PENDING, "long", movable=True)
        
        self._price_line_manager.get_all_lines.return_value = {
            "pending_123": pending_line,
            "stop_loss_123": dragged_line
        }
        
        relations = {
            "stop_loss": {"line_id": "stop_loss_123", "points": 50}
        }
        self._drawing_order_controller._pending_line_relations = {"pending_123": relations}
        self._drawing_order_controller._pending_order_params = {
            "pending_123": {
                "params": {"direction": Mock(value="多")},
                "contract": Mock(pricetick=1.0)
            }
        }
        
        self._price_line_manager.get_line.return_value = pending_line
        
        # Act
        self._update_points_on_line_drag(dragged_line, 19951.0, PriceLineType.STOP_LOSS)
        
        # Assert
        # 点数应该被更新
        assert relations["stop_loss"]["points"] == 49  # (20000 - 19951) / 1.0 = 49
