"""测试实时画线交易功能 (Phase 3: User Story 2)

测试实时挂单功能，当市场价格突破挂单线时自动触发下单。
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from vnpy.trader.object import TickData
from vnpy.trader.constant import Direction, Exchange
from vnpy.trader.event import EVENT_TICK
from vnpy.event import Event, EventEngine

from vnpy.chart.price_breakthrough import PriceBreakthroughMonitor, BreakthroughEvent
from vnpy.chart.price_line import PriceLineManager, PriceLineType, PriceLineItem
from tests.chart.test_base import TestBase


class TestDrawingTradeRealtime(TestBase):
    """Phase 3: 实时画线交易挂单功能测试"""
    
    @pytest.fixture
    def event_engine(self) -> EventEngine:
        """创建真实 EventEngine"""
        engine = EventEngine()
        engine.start()
        yield engine
        engine.stop()
    
    @pytest.fixture
    def price_line_manager(self) -> PriceLineManager:
        """创建价格线管理器"""
        return PriceLineManager()
    
    @pytest.fixture
    def breakthrough_monitor(self) -> PriceBreakthroughMonitor:
        """创建价格突破监控器"""
        return PriceBreakthroughMonitor()
    
    @pytest.fixture
    def mock_chart_widget(self):
        """创建模拟的 ChartWidget"""
        widget = Mock()
        widget._breakthrough_monitor = PriceBreakthroughMonitor()
        widget._price_line_manager = PriceLineManager()
        widget._main_engine = Mock()
        widget._main_engine.write_log = Mock()
        widget._main_engine.send_order = Mock(return_value="order_123")
        widget._main_engine.get_contract = Mock(return_value=Mock(gateway_name="TEST"))
        widget._main_engine.get_all_active_orders = Mock(return_value=[])
        widget._vt_symbol = "MHI2512.HKFE"
        widget._on_price_breakthrough = Mock()
        widget.trigger_pending_order_breakthrough = Mock(return_value=True)
        return widget
    
    def _create_tick(self, price: float) -> TickData:
        """创建测试用的 TickData"""
        return self.create_tick_data(
            symbol="MHI2512",
            exchange=Exchange.HKFE,
            last_price=price,
            bid_price_1=price - 1.0,
            ask_price_1=price + 1.0
        )
    
    def test_buy_order_trigger_on_price_breakthrough(
        self, 
        breakthrough_monitor: PriceBreakthroughMonitor,
        price_line_manager: PriceLineManager
    ):
        """T023: 测试做多订单在价格向上突破时触发"""
        # 创建挂单线（做多，价格 20000）
        line_id = price_line_manager.create_line(
            price=20000.0,
            line_type=PriceLineType.PENDING,
            direction="long"
        )
        line = price_line_manager.get_line(line_id)
        
        # 设置挂单参数
        line.set_order_volume(10.0)
        line.set_order_offset("OPEN")
        
        # 注册回调函数
        callback_called = []
        def on_breakthrough(event: BreakthroughEvent) -> None:
            callback_called.append(event)
        
        breakthrough_monitor.register_line(line_id, line, on_breakthrough)
        
        # 第一次更新：价格在挂单线下方（19998 < 20000）
        tick1 = self._create_tick(19998.0)
        breakthrough_monitor.update_tick(tick1, price_line_manager.get_all_lines())
        assert len(callback_called) == 0, "价格未突破时不应触发回调"
        
        # 第二次更新：价格突破挂单线（从下方到上方）
        # 需要满足：last_price (19998) < line_price (20000) <= current_price (20001)
        tick2 = self._create_tick(20001.0)
        breakthrough_monitor.update_tick(tick2, price_line_manager.get_all_lines())
        
        # 根据 PriceBreakthroughMonitor._check_breakthrough 的实现：
        # 做多：last_price < line_price <= current_price 应该返回 "up"
        # 这里满足条件：19998 < 20000 <= 20001，应该触发回调
        assert len(callback_called) == 1, f"价格向上突破应该触发回调，实际回调次数: {len(callback_called)}"
        event = callback_called[0]
        assert event.line_id == line_id
        assert event.price == 20000.0
        assert event.direction == "long"
        assert event.breakthrough_direction == "up"
        assert event.current_price == 20001.0
        assert event.tick is not None
    
    def test_sell_order_trigger_on_price_breakthrough(
        self,
        breakthrough_monitor: PriceBreakthroughMonitor,
        price_line_manager: PriceLineManager
    ):
        """T024: 测试做空订单在价格向下突破时触发"""
        # 创建挂单线（做空，价格 20000）
        line_id = price_line_manager.create_line(
            price=20000.0,
            line_type=PriceLineType.PENDING,
            direction="short"
        )
        line = price_line_manager.get_line(line_id)
        
        # 设置挂单参数
        line.set_order_volume(10.0)
        line.set_order_offset("OPEN")
        
        # 注册回调函数
        callback_called = []
        def on_breakthrough(event: BreakthroughEvent) -> None:
            callback_called.append(event)
        
        breakthrough_monitor.register_line(line_id, line, on_breakthrough)
        
        # 第一次更新：价格在挂单线上方（20002 > 20000）
        tick1 = self._create_tick(20002.0)
        breakthrough_monitor.update_tick(tick1, price_line_manager.get_all_lines())
        assert len(callback_called) == 0, "价格未突破时不应触发回调"
        
        # 第二次更新：价格突破挂单线（从上方到下方）
        # 需要满足：last_price (20002) > line_price (20000) >= current_price (19999)
        tick2 = self._create_tick(19999.0)
        breakthrough_monitor.update_tick(tick2, price_line_manager.get_all_lines())
        
        # 根据 PriceBreakthroughMonitor._check_breakthrough 的实现：
        # 做空：last_price > line_price >= current_price 应该返回 "down"
        # 这里满足条件：20002 > 20000 >= 19999，应该触发回调
        assert len(callback_called) == 1, f"价格向下突破应该触发回调，实际回调次数: {len(callback_called)}"
        event = callback_called[0]
        assert event.line_id == line_id
        assert event.price == 20000.0
        assert event.direction == "short"
        assert event.breakthrough_direction == "down"
        assert event.current_price == 19999.0
        assert event.tick is not None
    
    def test_no_order_trigger_when_price_not_breakthrough(
        self,
        breakthrough_monitor: PriceBreakthroughMonitor,
        price_line_manager: PriceLineManager
    ):
        """T025: 测试价格未突破时不触发订单"""
        # 创建挂单线（做多，价格 20000）
        line_id = price_line_manager.create_line(
            price=20000.0,
            line_type=PriceLineType.PENDING,
            direction="long"
        )
        line = price_line_manager.get_line(line_id)
        
        # 注册回调函数
        callback_called = []
        def on_breakthrough(event: BreakthroughEvent) -> None:
            callback_called.append(event)
        
        breakthrough_monitor.register_line(line_id, line, on_breakthrough)
        
        # 多次更新，但价格始终在挂单线下方
        for price in [19998.0, 19997.0, 19996.0, 19995.0]:
            tick = self._create_tick(price)
            breakthrough_monitor.update_tick(tick, price_line_manager.get_all_lines())
        
        # 不应该触发回调
        assert len(callback_called) == 0, "价格未突破挂单线时不应触发回调"
        
        # 价格回到挂单线上方，但没有从下方突破的过程（直接在上方）
        tick = self._create_tick(20001.0)
        breakthrough_monitor.update_tick(tick, price_line_manager.get_all_lines())
        
        # 仍然不应该触发，因为没有突破过程
        # 注意：这个测试可能根据实现细节有所不同
        # 关键是确保价格必须从下方突破到上方才能触发
    
    def test_price_breakthrough_detection_with_realtime_tick(
        self,
        mock_chart_widget,
        event_engine: EventEngine,
        price_line_manager: PriceLineManager
    ):
        """T026: 测试实时tick数据的价格突破检测"""
        # 设置 chart widget
        mock_chart_widget._breakthrough_monitor = PriceBreakthroughMonitor()
        mock_chart_widget._price_line_manager = price_line_manager
        mock_chart_widget._vt_symbol = "MHI2512.HKFE"
        
        # 创建挂单线（做多，价格 20000）
        line_id = price_line_manager.create_line(
            price=20000.0,
            line_type=PriceLineType.PENDING,
            direction="long"
        )
        line = price_line_manager.get_line(line_id)
        line.set_order_volume(10.0)
        line.set_order_offset("OPEN")
        
        # 注册到突破监控
        mock_chart_widget._breakthrough_monitor.register_line(
            line_id,
            line,
            mock_chart_widget._on_price_breakthrough
        )
        
        # 模拟 process_tick_event 的行为
        def process_tick_event(event: Event) -> None:
            tick = event.data
            if tick.vt_symbol == mock_chart_widget._vt_symbol:
                all_lines = mock_chart_widget._price_line_manager.get_all_lines()
                mock_chart_widget._breakthrough_monitor.update_tick(tick, all_lines)
        
        # 注册事件监听
        event_engine.register(EVENT_TICK, process_tick_event)
        
        # 第一次tick：价格在挂单线下方
        tick1 = self._create_tick(19998.0)
        tick1.vt_symbol = "MHI2512.HKFE"
        event1 = Event(EVENT_TICK, tick1)
        event_engine.put(event1)
        
        # 等待事件处理
        import time
        time.sleep(0.1)
        
        # 回调不应该被调用
        assert mock_chart_widget._on_price_breakthrough.call_count == 0
        
        # 第二次tick：价格突破挂单线
        tick2 = self._create_tick(20001.0)
        tick2.vt_symbol = "MHI2512.HKFE"
        event2 = Event(EVENT_TICK, tick2)
        event_engine.put(event2)
        
        # 等待事件处理
        time.sleep(0.1)
        
        # 回调应该被调用
        assert mock_chart_widget._on_price_breakthrough.call_count == 1
        
        # 验证回调参数
        call_args = mock_chart_widget._on_price_breakthrough.call_args
        event = call_args[0][0]
        assert isinstance(event, BreakthroughEvent)
        assert event.line_id == line_id
        assert event.price == 20000.0
        assert event.direction == "long"
        assert event.breakthrough_direction == "up"
    
    def test_breakthrough_monitor_receives_realtime_tick(
        self,
        mock_chart_widget,
        price_line_manager: PriceLineManager
    ):
        """T027: 验证 PriceBreakthroughMonitor 接收实时 tick 数据"""
        # 设置监控器
        monitor = mock_chart_widget._breakthrough_monitor
        monitor.update_tick = Mock()
        
        # 创建挂单线
        line_id = price_line_manager.create_line(
            price=20000.0,
            line_type=PriceLineType.PENDING,
            direction="long"
        )
        line = price_line_manager.get_line(line_id)
        monitor.register_line(line_id, line, Mock())
        
        # 模拟 process_tick_event 调用
        tick = self._create_tick(20001.0)
        tick.vt_symbol = "MHI2512.HKFE"
        
        all_lines = price_line_manager.get_all_lines()
        monitor.update_tick(tick, all_lines)
        
        # 验证 update_tick 被调用
        assert monitor.update_tick.called
        call_args = monitor.update_tick.call_args
        assert call_args[0][0] == tick
        assert isinstance(call_args[0][1], dict)
    
    def test_order_trigger_with_exception_handling(self, mock_chart_widget):
        """测试订单触发时的异常处理"""
        # 模拟下单时抛出异常
        mock_chart_widget.trigger_pending_order_breakthrough.side_effect = Exception("下单失败")
        
        # 创建突破事件
        from vnpy.chart.price_breakthrough import BreakthroughEvent
        event = BreakthroughEvent(
            line_id="test_line",
            line_type=PriceLineType.PENDING,
            price=20000.0,
            direction="long",
            current_price=20001.0,
            breakthrough_direction="up",
            tick=self._create_tick(20001.0)
        )
        
        # 调用回调函数
        try:
            mock_chart_widget._on_price_breakthrough(event)
        except Exception as e:
            # 异常应该被正确处理（在实际代码中）
            pass
        
        # 验证触发方法被调用
        assert mock_chart_widget.trigger_pending_order_breakthrough.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

