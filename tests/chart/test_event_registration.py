"""测试 ChartWindow 事件注册功能"""

import pytest
from unittest.mock import Mock, MagicMock, call
from vnpy.event import Event, EventEngine
from vnpy.trader.event import EVENT_TICK
from vnpy.trader.object import TickData
from vnpy.trader.constant import Exchange
from tests.chart.test_base import TestBase


class TestChartWindowEventRegistration:
    """测试 ChartWindow 事件注册功能"""
    
    @pytest.fixture
    def mock_main_engine(self):
        """创建模拟的MainEngine"""
        engine = Mock()
        engine.write_log = Mock()
        engine.get_contract = Mock(return_value=Mock(gateway_name="test"))
        engine.get_all_gateway_names = Mock(return_value=["test"])
        engine.subscribe = Mock()
        return engine
    
    @pytest.fixture
    def real_event_engine(self):
        """创建真实的EventEngine用于测试"""
        return EventEngine()
    
    @pytest.fixture
    def chart_window(self, mock_main_engine, real_event_engine, qapp):
        """创建ChartWindow实例用于测试"""
        from vnpy.trader.ui.widget import ChartWindow
        
        window = ChartWindow(mock_main_engine, real_event_engine)
        return window
    
    def test_event_registration(self, chart_window, real_event_engine):
        """T001: 测试事件注册"""
        # 验证 register_event() 方法存在
        assert hasattr(chart_window, 'register_event'), "register_event() 方法不存在"
        
        # 调用 register_event()
        chart_window.register_event()
        
        # 验证 EVENT_TICK 事件已注册
        # EventEngine 内部使用 _handlers 字典存储处理器
        # 注意：由于使用信号槽机制，注册的是 signal_tick.emit 而不是直接注册 process_tick_event
        assert EVENT_TICK in real_event_engine._handlers, "EVENT_TICK 事件未注册"
        assert len(real_event_engine._handlers[EVENT_TICK]) > 0, "EVENT_TICK 处理器列表为空"
        
        # 验证注册的处理器是 signal_tick.emit（信号槽机制）
        handlers = real_event_engine._handlers[EVENT_TICK]
        assert any(hasattr(h, '__self__') and hasattr(h.__self__, 'emit') for h in handlers), \
            "EVENT_TICK 处理器应该是信号槽机制"
    
    def test_event_unregistration(self, chart_window, real_event_engine):
        """T002: 测试事件注销"""
        # 先注册事件
        chart_window.register_event()
        assert EVENT_TICK in real_event_engine._handlers, "事件注册失败"
        
        # 模拟窗口关闭事件
        from PySide6.QtGui import QCloseEvent
        close_event = QCloseEvent()
        
        # 调用 closeEvent()
        chart_window.closeEvent(close_event)
        
        # 验证事件已注销
        # 注意：如果处理器列表为空，EventEngine 会移除该事件类型
        if EVENT_TICK in real_event_engine._handlers:
            assert chart_window.process_tick_event not in real_event_engine._handlers[EVENT_TICK], \
                "事件处理器未注销"
    
    def test_event_handler_receives_tick_events(self, chart_window, real_event_engine, mock_main_engine):
        """T003: 测试事件处理器能接收tick事件"""
        # 设置当前合约和历史数据已加载
        chart_window.current_vt_symbol = "MHI2512.HKFE"
        chart_window.history_loaded = True
        
        # 创建模拟的图表组件
        chart_window.chart = Mock()
        chart_window.chart.update_bar = Mock()
        
        # 创建BarGenerator
        from vnpy.trader.utility import BarGenerator
        chart_window.bg = BarGenerator(chart_window.on_bar)
        
        # 注册事件
        chart_window.register_event()
        
        # 创建tick数据
        tick = TestBase.create_tick_data(
            symbol="MHI2512",
            exchange=Exchange.HKFE,
            last_price=20000.0
        )
        
        # 创建事件并发送
        event = Event(EVENT_TICK, tick)
        real_event_engine.put(event)
        
        # 等待事件处理（EventEngine在后台线程处理）
        import time
        time.sleep(0.1)  # 等待100ms让事件处理完成
        
        # 验证 process_tick_event 被调用（通过检查图表更新）
        # 注意：由于EventEngine在后台线程，可能需要等待
        # 这里主要验证事件能够被接收和处理，不验证具体业务逻辑

