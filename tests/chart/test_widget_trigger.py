"""ChartWidget 触发模块测试

测试 ChartWidgetTriggerMixin 的所有方法。
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from vnpy.trader.object import TickData, PositionData
from vnpy.trader.constant import Direction, Exchange
from vnpy.chart.widget_mixin_base import ChartWidgetMixinBase
from vnpy.chart.widget_trigger import ChartWidgetTriggerMixin
from vnpy.chart.price_line import PriceLineManager, PriceLineType, PriceLineItem
from tests.chart.test_base import TestBase


# Mock PriceLineItem for testing
class MockPriceLineItem:
    """Mock PriceLineItem for testing (不继承真实类，避免初始化问题)"""
    def __init__(self, line_id: str, price: float, line_type: PriceLineType, direction: str, volume: float = 0.0, order_volume: float = None, order_offset: str = None):
        self._line_id = line_id
        self._price = price
        self._line_type = line_type
        self._direction = direction
        self._volume = volume
        self._order_volume = order_volume
        self._order_offset = order_offset
        self.label = Mock()
        self.setVisible = Mock()

    def get_line_id(self) -> str:
        return self._line_id
    
    def get_price(self) -> float:
        return self._price
    
    def get_line_type(self) -> PriceLineType:
        return self._line_type
    
    def get_direction(self) -> str:
        return self._direction
    
    def get_volume(self) -> float:
        return self._volume
    
    def get_order_volume(self) -> float | None:
        return self._order_volume
    
    def get_order_offset(self) -> str | None:
        return self._order_offset


class TestChartWidgetTrigger(TestBase, ChartWidgetTriggerMixin):
    """触发模块测试"""
    
    @pytest.fixture(autouse=True)
    def setup(self, qtbot):
        """为每个测试设置模拟对象"""
        self._main_engine = Mock()
        self._main_engine.write_log = Mock()
        self._main_engine.send_order = Mock(return_value="order_123")
        self._main_engine.get_contract = Mock(return_value=Mock(gateway_name="TEST"))
        self._main_engine.get_all_gateway_names = Mock(return_value=["TEST"])
        self._main_engine.get_gateway = Mock(return_value=None)
        self._main_engine.get_position = Mock(return_value=None)
        self._main_engine.get_all_positions = Mock(return_value=[])
        
        self._vt_symbol = "MHI2512.HKFE"
        self._price_line_manager = Mock(spec=PriceLineManager)
        self._drawing_order_controller = Mock()
        self._drawing_order_controller.link_line_to_order = Mock()
        self._drawing_order_controller.get_line_id_for_order = Mock(return_value=None)
        self._drawing_order_controller._pending_order_params = {}
        
        # 添加 get_drawing_order_controller 方法
        self.get_drawing_order_controller = Mock(return_value=self._drawing_order_controller)
        
        self._breakthrough_monitor = Mock()
        self._breakthrough_monitor.unregister_line = Mock()
        
        self._pending_order_trigger_lock = Mock()
        self._pending_order_trigger_lock.__enter__ = Mock(return_value=None)
        self._pending_order_trigger_lock.__exit__ = Mock(return_value=None)
        
        self._stop_loss_trigger_lock = Mock()
        self._stop_loss_trigger_lock.__enter__ = Mock(return_value=None)
        self._stop_loss_trigger_lock.__exit__ = Mock(return_value=None)
        
        self._take_profit_trigger_lock = Mock()
        self._take_profit_trigger_lock.__enter__ = Mock(return_value=None)
        self._take_profit_trigger_lock.__exit__ = Mock(return_value=None)

    def test_trigger_pending_order_breakthrough_success(self):
        """测试挂单线突破下单成功"""
        line = MockPriceLineItem(
            line_id="pending_line_123",
            price=20000.0,
            line_type=PriceLineType.PENDING,
            direction="long",
            order_volume=10.0,
            order_offset="OPEN"
        )
        
        tick = self.create_tick_data(
            symbol="MHI2512",
            exchange=Exchange.HKFE,
            last_price=20001.0  # 价格突破挂单线
        )
        
        result = self.trigger_pending_order_breakthrough("pending_line_123", line, tick)
        
        # 应该成功发送订单
        assert result is True
        self._main_engine.send_order.assert_called_once()

    def test_trigger_pending_order_breakthrough_closing_order(self):
        """测试平仓订单判断"""
        line = MockPriceLineItem(
            line_id="pending_line_123",
            price=20000.0,
            line_type=PriceLineType.PENDING,
            direction="long",
            order_volume=10.0,
            order_offset="CLOSE"
        )
        
        tick = self.create_tick_data(
            symbol="MHI2512",
            exchange=Exchange.HKFE,
            last_price=20001.0
        )
        
        # 标记为平仓订单
        self._drawing_order_controller._pending_order_params["pending_line_123"] = {
            "is_closing": True
        }
        
        result = self.trigger_pending_order_breakthrough("pending_line_123", line, tick)
        
        # 平仓订单应该也能成功发送
        assert result is True

    def test_trigger_pending_order_breakthrough_order_failed(self):
        """测试下单失败处理"""
        line = MockPriceLineItem(
            line_id="pending_line_123",
            price=20000.0,
            line_type=PriceLineType.PENDING,
            direction="long",
            order_volume=10.0,
            order_offset="OPEN"
        )
        
        tick = self.create_tick_data(
            symbol="MHI2512",
            exchange=Exchange.HKFE,
            last_price=20001.0
        )
        
        # 模拟下单失败
        self._main_engine.send_order.return_value = None
        
        result = self.trigger_pending_order_breakthrough("pending_line_123", line, tick)
        
        # 应该返回 False
        assert result is False

    def test_trigger_stop_loss_close_long_position(self):
        """测试多仓止损触发"""
        line = MockPriceLineItem(
            line_id="stop_loss_123",
            price=19900.0,
            line_type=PriceLineType.STOP_LOSS,
            direction="long",
            volume=10.0
        )
        
        tick = self.create_tick_data(
            symbol="MHI2512",
            exchange=Exchange.HKFE,
            last_price=19899.0,  # 低于止损价
            bid_price_1=19899.0,
            ask_price_1=19900.0
        )
        
        # 模拟有持仓
        position = self.create_position_data(
            symbol="MHI2512",
            exchange=Exchange.HKFE,
            direction=Direction.LONG,
            volume=10.0
        )
        self._main_engine.get_position.return_value = position
        
        result = self.trigger_stop_loss_close("stop_loss_123", line, tick)
        
        # 应该成功发送平仓订单
        assert result is True
        self._main_engine.send_order.assert_called_once()

    def test_trigger_stop_loss_close_short_position(self):
        """测试空仓止损触发"""
        line = MockPriceLineItem(
            line_id="stop_loss_123",
            price=20100.0,
            line_type=PriceLineType.STOP_LOSS,
            direction="short",
            volume=10.0
        )
        
        tick = self.create_tick_data(
            symbol="MHI2512",
            exchange=Exchange.HKFE,
            last_price=20101.0,  # 高于止损价（空仓止损）
            bid_price_1=20100.0,
            ask_price_1=20101.0
        )
        
        # 模拟有持仓
        position = self.create_position_data(
            symbol="MHI2512",
            exchange=Exchange.HKFE,
            direction=Direction.SHORT,
            volume=10.0
        )
        self._main_engine.get_position.return_value = position
        
        result = self.trigger_stop_loss_close("stop_loss_123", line, tick)
        
        # 应该成功发送平仓订单
        assert result is True
        self._main_engine.send_order.assert_called_once()

    def test_trigger_stop_loss_close_no_position(self):
        """测试无持仓跳过"""
        line = MockPriceLineItem(
            line_id="stop_loss_123",
            price=19900.0,
            line_type=PriceLineType.STOP_LOSS,
            direction="long",
            volume=10.0
        )
        
        tick = self.create_tick_data(
            symbol="MHI2512",
            exchange=Exchange.HKFE,
            last_price=19899.0
        )
        
        # 模拟无持仓
        self._main_engine.get_position.return_value = None
        
        result = self.trigger_stop_loss_close("stop_loss_123", line, tick)
        
        # 应该返回 False（无持仓）
        assert result is False
        self._main_engine.send_order.assert_not_called()

    def test_trigger_take_profit_close_long_position(self):
        """测试多仓止盈触发"""
        line = MockPriceLineItem(
            line_id="take_profit_123",
            price=20100.0,
            line_type=PriceLineType.TAKE_PROFIT,
            direction="long",
            volume=10.0
        )
        
        tick = self.create_tick_data(
            symbol="MHI2512",
            exchange=Exchange.HKFE,
            last_price=20101.0,  # 高于止盈价
            bid_price_1=20100.0,
            ask_price_1=20101.0
        )
        
        # 模拟有持仓
        position = self.create_position_data(
            symbol="MHI2512",
            exchange=Exchange.HKFE,
            direction=Direction.LONG,
            volume=10.0
        )
        self._main_engine.get_position.return_value = position
        
        result = self.trigger_take_profit_close("take_profit_123", line, tick)
        
        # 应该成功发送平仓订单
        assert result is True
        self._main_engine.send_order.assert_called_once()

    def test_trigger_take_profit_close_short_position(self):
        """测试空仓止盈触发"""
        line = MockPriceLineItem(
            line_id="take_profit_123",
            price=19900.0,
            line_type=PriceLineType.TAKE_PROFIT,
            direction="short",
            volume=10.0
        )
        
        tick = self.create_tick_data(
            symbol="MHI2512",
            exchange=Exchange.HKFE,
            last_price=19899.0,  # 低于止盈价（空仓止盈）
            bid_price_1=19899.0,
            ask_price_1=19900.0
        )
        
        # 模拟有持仓
        position = self.create_position_data(
            symbol="MHI2512",
            exchange=Exchange.HKFE,
            direction=Direction.SHORT,
            volume=10.0
        )
        self._main_engine.get_position.return_value = position
        
        result = self.trigger_take_profit_close("take_profit_123", line, tick)
        
        # 应该成功发送平仓订单
        assert result is True
        self._main_engine.send_order.assert_called_once()

    def test_trigger_take_profit_close_no_position(self):
        """测试无持仓跳过"""
        line = MockPriceLineItem(
            line_id="take_profit_123",
            price=20100.0,
            line_type=PriceLineType.TAKE_PROFIT,
            direction="long",
            volume=10.0
        )
        
        tick = self.create_tick_data(
            symbol="MHI2512",
            exchange=Exchange.HKFE,
            last_price=20101.0
        )
        
        # 模拟无持仓
        self._main_engine.get_position.return_value = None
        
        result = self.trigger_take_profit_close("take_profit_123", line, tick)
        
        # 应该返回 False（无持仓）
        assert result is False
        self._main_engine.send_order.assert_not_called()
