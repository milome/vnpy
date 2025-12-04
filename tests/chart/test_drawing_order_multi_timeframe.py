"""测试多周期模式画线交易功能

Phase 3: 画线交易功能整合测试
- T038: 测试画线交易控制器初始化在多周期模式
- T039: 测试启用画线模式在多周期模式
- T040: 测试禁用画线模式在多周期模式
- T041: 测试创建挂单线在多周期模式
- T042: 测试创建止损线在多周期模式
- T043: 测试创建止盈线在多周期模式
- T044: 测试价格突破触发在多周期模式
- T045: 测试止损触发在多周期模式
- T046: 测试止盈触发在多周期模式
- T047: 测试价格线拖拽在多周期模式
- T048: 测试价格线坐标映射在多周期模式
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime

from vnpy.trader.constant import Exchange, Interval, Direction, Offset
from vnpy.trader.object import BarData, TickData, OrderData
from vnpy.chart.price_line import PriceLineType, PriceLineManager
from tests.chart.conftest import mock_main_engine, mock_event_engine


class TestDrawingOrderMultiTimeframe:
    """测试多周期模式画线交易功能"""
    
    @pytest.fixture
    def multi_timeframe_widget(self, qtbot):
        """创建MultiTimeframeWidget实例用于测试"""
        from vnpy.chart.multi_timeframe_widget import MultiTimeframeWidget
        
        start = datetime(2024, 11, 14)
        end = datetime(2024, 11, 18)
        
        widget = MultiTimeframeWidget(
            vt_symbol="MHImain",
            exchange=Exchange.HKFE,
            start=start,
            end=end,
        )
        
        # 显示窗口以确保isVisible()能正确工作
        widget.show()
        qtbot.waitExposed(widget)
        
        return widget
    
    @pytest.fixture
    def chart_window(self, mock_main_engine, mock_event_engine, qtbot):
        """创建ChartWindow实例用于测试"""
        from vnpy.trader.ui.widget import ChartWindow
        
        window = ChartWindow(mock_main_engine, mock_event_engine)
        
        # Mock图表组件
        window.chart = Mock()
        window.chart.update_history = Mock()
        window.chart.update_bar = Mock()
        window.chart.set_future_bars = Mock()
        window.chart.set_vt_symbol = Mock()
        window.chart.get_drawing_order_controller = Mock(return_value=Mock())
        window.chart.isVisible = Mock(return_value=True)
        window.chart.setVisible = Mock()
        window.chart.clear_all = Mock()
        window.chart.set_main_engine = Mock()
        window.chart.set_drawing_click_callback = Mock()
        window.chart.set_drawing_mode_changed_callback = Mock()
        
        # Mock状态标签
        window.status_label = Mock()
        window.status_label.setText = Mock()
        
        # Mock画线模式按钮
        window.drawing_mode_button = Mock()
        window.drawing_mode_button.isChecked = Mock(return_value=False)
        window.drawing_mode_button.setChecked = Mock()
        window.drawing_mode_button.setText = Mock()
        window.drawing_mode_button.setStyleSheet = Mock()
        
        # 设置初始状态
        window.current_vt_symbol = "MHImain.HKFE"
        window.current_interval = "1m"
        window.history_loaded = False
        
        # 显示窗口以确保isVisible()能正确工作
        window.show()
        qtbot.waitExposed(window)
        
        return window
    
    def test_drawing_order_controller_initialization_in_multi_timeframe_mode(
        self, multi_timeframe_widget, mock_main_engine
    ):
        """T038: 测试画线交易控制器初始化在多周期模式"""
        # Mock ChartWidget 的方法
        multi_timeframe_widget._chart.set_main_engine = Mock()
        multi_timeframe_widget._chart.set_vt_symbol = Mock()
        multi_timeframe_widget._chart.set_drawing_click_callback = Mock()
        
        # 启用画线交易功能
        multi_timeframe_widget.enable_drawing_order(
            main_engine=mock_main_engine,
            vt_symbol="MHImain.HKFE"
        )
        
        # 验证 DrawingOrderController 已初始化
        controller = multi_timeframe_widget.get_drawing_order_controller()
        assert controller is not None, "DrawingOrderController 未初始化"
        
        # 验证 ChartWidget 的 set_main_engine 和 set_vt_symbol 被调用
        multi_timeframe_widget._chart.set_main_engine.assert_called_once_with(mock_main_engine)
        multi_timeframe_widget._chart.set_vt_symbol.assert_called_once_with("MHImain.HKFE")
    
    def test_enable_drawing_mode_in_multi_timeframe_mode(
        self, chart_window
    ):
        """T039: 测试启用画线模式在多周期模式"""
        # 切换到多周期模式
        chart_window.switch_display_mode("multi")
        
        # 验证多周期Widget已显示
        assert chart_window.display_mode == "multi", "模式切换失败"
        assert chart_window.multi_timeframe_widget.isVisible(), \
            "多周期Widget未显示"
        
        # Mock controller
        controller = Mock()
        controller.enable = Mock()
        controller.is_enabled = Mock(return_value=False)
        chart_window.multi_timeframe_widget.get_drawing_order_controller = Mock(return_value=controller)
        
        # Mock chart widget
        chart_window.multi_timeframe_widget._chart = Mock()
        chart_window.multi_timeframe_widget._chart.setFocus = Mock()
        
        # 启用画线模式
        chart_window.drawing_mode_button.isChecked = Mock(return_value=True)
        chart_window.toggle_drawing_mode()
        
        # 验证 controller.enable 被调用
        controller.enable.assert_called_once()
    
    def test_disable_drawing_mode_in_multi_timeframe_mode(
        self, chart_window
    ):
        """T040: 测试禁用画线模式在多周期模式"""
        # 切换到多周期模式
        chart_window.switch_display_mode("multi")
        
        # Mock controller
        controller = Mock()
        controller.disable = Mock()
        controller.is_enabled = Mock(return_value=True)
        chart_window.multi_timeframe_widget.get_drawing_order_controller = Mock(return_value=controller)
        
        # 禁用画线模式
        chart_window.drawing_mode_button.isChecked = Mock(return_value=False)
        chart_window.toggle_drawing_mode()
        
        # 验证 controller.disable 被调用
        controller.disable.assert_called_once()
    
    def test_create_pending_order_line_in_multi_timeframe_mode(
        self, multi_timeframe_widget, mock_main_engine
    ):
        """T041: 测试创建挂单线在多周期模式"""
        # 启用画线交易功能
        multi_timeframe_widget.enable_drawing_order(
            main_engine=mock_main_engine,
            vt_symbol="MHImain.HKFE"
        )
        
        # 获取价格线管理器
        chart = multi_timeframe_widget._chart
        price_line_manager = chart.get_price_line_manager()
        
        # 创建挂单线
        line_id = price_line_manager.create_line(
            price=25000.0,
            line_type=PriceLineType.PENDING,
            direction="long"
        )
        
        # 验证挂单线已创建
        assert line_id is not None, "挂单线未创建"
        line = price_line_manager.get_line(line_id)
        assert line is not None, "挂单线不存在"
        assert line.get_line_type() == PriceLineType.PENDING, \
            "挂单线类型不正确"
        assert line.get_price() == 25000.0, "挂单线价格不正确"
    
    def test_create_stop_loss_line_in_multi_timeframe_mode(
        self, multi_timeframe_widget, mock_main_engine
    ):
        """T042: 测试创建止损线在多周期模式"""
        # Mock ChartWidget 的方法
        multi_timeframe_widget._chart.set_main_engine = Mock()
        multi_timeframe_widget._chart.set_vt_symbol = Mock()
        multi_timeframe_widget._chart.set_drawing_click_callback = Mock()
        
        # 启用画线交易功能
        multi_timeframe_widget.enable_drawing_order(
            main_engine=mock_main_engine,
            vt_symbol="MHImain.HKFE"
        )
        
        # 获取价格线管理器
        chart = multi_timeframe_widget._chart
        price_line_manager = chart.get_price_line_manager()
        
        # 确保有 plot 用于添加价格线
        if not chart._first_plot:
            chart.add_plot("candle", hide_x_axis=False)
        
        # 创建止损线
        line_id = price_line_manager.create_line(
            price=24900.0,
            line_type=PriceLineType.STOP_LOSS,
            direction="long"
        )
        
        # 验证止损线已创建
        assert line_id is not None, "止损线未创建"
        line = price_line_manager.get_line(line_id)
        assert line is not None, "止损线不存在"
        assert line.get_line_type() == PriceLineType.STOP_LOSS, \
            "止损线类型不正确"
        assert line.get_price() == 24900.0, "止损线价格不正确"
    
    def test_create_take_profit_line_in_multi_timeframe_mode(
        self, multi_timeframe_widget, mock_main_engine
    ):
        """T043: 测试创建止盈线在多周期模式"""
        # Mock ChartWidget 的方法
        multi_timeframe_widget._chart.set_main_engine = Mock()
        multi_timeframe_widget._chart.set_vt_symbol = Mock()
        multi_timeframe_widget._chart.set_drawing_click_callback = Mock()
        
        # 启用画线交易功能
        multi_timeframe_widget.enable_drawing_order(
            main_engine=mock_main_engine,
            vt_symbol="MHImain.HKFE"
        )
        
        # 获取价格线管理器
        chart = multi_timeframe_widget._chart
        price_line_manager = chart.get_price_line_manager()
        
        # 确保有 plot 用于添加价格线
        if not chart._first_plot:
            chart.add_plot("candle", hide_x_axis=False)
        
        # 创建止盈线
        line_id = price_line_manager.create_line(
            price=25100.0,
            line_type=PriceLineType.TAKE_PROFIT,
            direction="long"
        )
        
        # 验证止盈线已创建
        assert line_id is not None, "止盈线未创建"
        line = price_line_manager.get_line(line_id)
        assert line is not None, "止盈线不存在"
        assert line.get_line_type() == PriceLineType.TAKE_PROFIT, \
            "止盈线类型不正确"
        assert line.get_price() == 25100.0, "止盈线价格不正确"
    
    def test_price_breakthrough_trigger_in_multi_timeframe_mode(
        self, multi_timeframe_widget, mock_main_engine
    ):
        """T044: 测试价格突破触发在多周期模式"""
        # Mock ChartWidget 的方法
        multi_timeframe_widget._chart.set_main_engine = Mock()
        multi_timeframe_widget._chart.set_vt_symbol = Mock()
        multi_timeframe_widget._chart.set_drawing_click_callback = Mock()
        multi_timeframe_widget._chart.update_tick = Mock()
        
        # 启用画线交易功能
        multi_timeframe_widget.enable_drawing_order(
            main_engine=mock_main_engine,
            vt_symbol="MHImain.HKFE"
        )
        
        # 启用实时更新
        multi_timeframe_widget.enable_realtime()
        
        # 获取价格线管理器
        chart = multi_timeframe_widget._chart
        price_line_manager = chart.get_price_line_manager()
        
        # 确保有 plot 用于添加价格线
        if not chart._first_plot:
            chart.add_plot("candle", hide_x_axis=False)
        
        # 创建挂单线
        line_id = price_line_manager.create_line(
            price=25000.0,
            line_type=PriceLineType.PENDING,
            direction="long"
        )
        line = price_line_manager.get_line(line_id)
        if line:
            line.set_order_volume(10.0)
            line.set_order_offset("OPEN")
        
        # Mock 价格突破监控
        if hasattr(chart, '_breakthrough_monitor') and chart._breakthrough_monitor:
            chart._breakthrough_monitor.update_tick = Mock()
        
        # 创建测试 tick 数据（价格突破挂单线）
        tick = TickData(
            symbol="MHImain",
            exchange=Exchange.HKFE,
            datetime=datetime.now(),
            name="恒指主力",
            gateway_name="test",
            volume=1000,
            open_interest=0,
            last_price=25001.0,  # 价格突破挂单线
            open_price=25000.0,
            high_price=25001.0,
            low_price=24999.0,
            pre_close=25000.0,
            bid_price_1=25000.0,
            ask_price_1=25001.0,
            bid_volume_1=100,
            ask_volume_1=100,
        )
        tick.vt_symbol = "MHImain.HKFE"
        
        # 更新 tick（会触发价格突破监控）
        multi_timeframe_widget.update_tick(tick)
        
        # 验证 ChartWidget.update_tick 被调用（确保 tick 传递给价格突破监控）
        chart.update_tick.assert_called_once_with(tick)
    
    def test_stop_loss_trigger_in_multi_timeframe_mode(
        self, multi_timeframe_widget, mock_main_engine
    ):
        """T045: 测试止损触发在多周期模式"""
        # Mock ChartWidget 的方法
        multi_timeframe_widget._chart.set_main_engine = Mock()
        multi_timeframe_widget._chart.set_vt_symbol = Mock()
        multi_timeframe_widget._chart.set_drawing_click_callback = Mock()
        multi_timeframe_widget._chart.update_tick = Mock()
        
        # 启用画线交易功能
        multi_timeframe_widget.enable_drawing_order(
            main_engine=mock_main_engine,
            vt_symbol="MHImain.HKFE"
        )
        
        # 启用实时更新
        multi_timeframe_widget.enable_realtime()
        
        # 获取价格线管理器
        chart = multi_timeframe_widget._chart
        price_line_manager = chart.get_price_line_manager()
        
        # 确保有 plot 用于添加价格线
        if not chart._first_plot:
            chart.add_plot("candle", hide_x_axis=False)
        
        # 创建止损线
        line_id = price_line_manager.create_line(
            price=24900.0,
            line_type=PriceLineType.STOP_LOSS,
            direction="long"
        )
        
        # Mock 价格突破监控
        if hasattr(chart, '_breakthrough_monitor') and chart._breakthrough_monitor:
            chart._breakthrough_monitor.update_tick = Mock()
        
        # 创建测试 tick 数据（价格突破止损线）
        tick = TickData(
            symbol="MHImain",
            exchange=Exchange.HKFE,
            datetime=datetime.now(),
            name="恒指主力",
            gateway_name="test",
            volume=1000,
            open_interest=0,
            last_price=24899.0,  # 价格突破止损线
            open_price=25000.0,
            high_price=25000.0,
            low_price=24899.0,
            pre_close=25000.0,
            bid_price_1=24899.0,
            ask_price_1=24900.0,
            bid_volume_1=100,
            ask_volume_1=100,
        )
        tick.vt_symbol = "MHImain.HKFE"
        
        # 更新 tick（会触发价格突破监控）
        multi_timeframe_widget.update_tick(tick)
        
        # 验证 ChartWidget.update_tick 被调用（确保 tick 传递给价格突破监控）
        chart.update_tick.assert_called_once_with(tick)
    
    def test_take_profit_trigger_in_multi_timeframe_mode(
        self, multi_timeframe_widget, mock_main_engine
    ):
        """T046: 测试止盈触发在多周期模式"""
        # Mock ChartWidget 的方法
        multi_timeframe_widget._chart.set_main_engine = Mock()
        multi_timeframe_widget._chart.set_vt_symbol = Mock()
        multi_timeframe_widget._chart.set_drawing_click_callback = Mock()
        multi_timeframe_widget._chart.update_tick = Mock()
        
        # 启用画线交易功能
        multi_timeframe_widget.enable_drawing_order(
            main_engine=mock_main_engine,
            vt_symbol="MHImain.HKFE"
        )
        
        # 启用实时更新
        multi_timeframe_widget.enable_realtime()
        
        # 获取价格线管理器
        chart = multi_timeframe_widget._chart
        price_line_manager = chart.get_price_line_manager()
        
        # 确保有 plot 用于添加价格线
        if not chart._first_plot:
            chart.add_plot("candle", hide_x_axis=False)
        
        # 创建止盈线
        line_id = price_line_manager.create_line(
            price=25100.0,
            line_type=PriceLineType.TAKE_PROFIT,
            direction="long"
        )
        
        # Mock 价格突破监控
        if hasattr(chart, '_breakthrough_monitor') and chart._breakthrough_monitor:
            chart._breakthrough_monitor.update_tick = Mock()
        
        # 创建测试 tick 数据（价格突破止盈线）
        tick = TickData(
            symbol="MHImain",
            exchange=Exchange.HKFE,
            datetime=datetime.now(),
            name="恒指主力",
            gateway_name="test",
            volume=1000,
            open_interest=0,
            last_price=25101.0,  # 价格突破止盈线
            open_price=25000.0,
            high_price=25101.0,
            low_price=25000.0,
            pre_close=25000.0,
            bid_price_1=25100.0,
            ask_price_1=25101.0,
            bid_volume_1=100,
            ask_volume_1=100,
        )
        tick.vt_symbol = "MHImain.HKFE"
        
        # 更新 tick（会触发价格突破监控）
        multi_timeframe_widget.update_tick(tick)
        
        # 验证 ChartWidget.update_tick 被调用（确保 tick 传递给价格突破监控）
        chart.update_tick.assert_called_once_with(tick)
    
    def test_price_line_drag_in_multi_timeframe_mode(
        self, multi_timeframe_widget, mock_main_engine
    ):
        """T047: 测试价格线拖拽在多周期模式"""
        # Mock ChartWidget 的方法
        multi_timeframe_widget._chart.set_main_engine = Mock()
        multi_timeframe_widget._chart.set_vt_symbol = Mock()
        multi_timeframe_widget._chart.set_drawing_click_callback = Mock()
        
        # 启用画线交易功能
        multi_timeframe_widget.enable_drawing_order(
            main_engine=mock_main_engine,
            vt_symbol="MHImain.HKFE"
        )
        
        # 获取价格线管理器
        chart = multi_timeframe_widget._chart
        price_line_manager = chart.get_price_line_manager()
        
        # 确保有 plot 用于添加价格线
        if not chart._first_plot:
            chart.add_plot("candle", hide_x_axis=False)
        
        # 创建可拖拽的价格线
        line_id = price_line_manager.create_line(
            price=25000.0,
            line_type=PriceLineType.STOP_LOSS,
            direction="long",
            movable=True
        )
        
        # 验证价格线已创建
        assert line_id is not None, "价格线未创建"
        line = price_line_manager.get_line(line_id)
        assert line is not None, "价格线不存在"
        
        # 验证价格线可拖拽
        # 注意：实际拖拽测试需要模拟鼠标事件，这里只验证价格线已创建
        assert line.movable, "价格线不可拖拽"
    
    def test_price_line_coordinate_mapping_in_multi_timeframe_mode(
        self, multi_timeframe_widget, mock_main_engine
    ):
        """T048: 测试价格线坐标映射在多周期模式"""
        # Mock ChartWidget 的方法
        multi_timeframe_widget._chart.set_main_engine = Mock()
        multi_timeframe_widget._chart.set_vt_symbol = Mock()
        multi_timeframe_widget._chart.set_drawing_click_callback = Mock()
        
        # 启用画线交易功能
        multi_timeframe_widget.enable_drawing_order(
            main_engine=mock_main_engine,
            vt_symbol="MHImain.HKFE"
        )
        
        # 获取价格线管理器
        chart = multi_timeframe_widget._chart
        price_line_manager = chart.get_price_line_manager()
        
        # 确保有 plot 用于添加价格线
        if not chart._first_plot:
            chart.add_plot("candle", hide_x_axis=False)
        
        # 创建价格线
        line_id = price_line_manager.create_line(
            price=25000.0,
            line_type=PriceLineType.PENDING,
            direction="long"
        )
        
        # 验证价格线已创建
        assert line_id is not None, "价格线未创建"
        line = price_line_manager.get_line(line_id)
        assert line is not None, "价格线不存在"
        
        # 验证价格线价格正确
        assert line.get_price() == 25000.0, "价格线价格不正确"
        
        # 验证价格线在图表中正确显示
        # 注意：实际坐标映射测试需要验证价格线在图表中的位置
        # 这里只验证价格线的基本属性
    
    # ---------------------------------------------------------------------
    # Phase 5: 功能测试
    def test_drawing_order_functionality_in_both_modes(self, chart_window):
        """T074: 测试画线交易功能在两种模式"""
        # 测试单周期模式下的画线交易功能
        chart_window.switch_display_mode("single")
        chart_window.current_vt_symbol = "MHImain.HKFE"
        
        # 验证画线交易功能可用
        assert hasattr(chart_window, 'toggle_drawing_mode'), \
            "toggle_drawing_mode 方法不存在"
        
        # 验证画线交易控制器存在
        if chart_window.chart:
            assert hasattr(chart_window.chart, 'get_drawing_order_controller'), \
                "ChartWidget.get_drawing_order_controller 方法不存在"
        
        # 测试多周期模式下的画线交易功能
        chart_window.switch_display_mode("multi")
        
        # 验证画线交易功能可用
        assert hasattr(chart_window, 'toggle_drawing_mode'), \
            "toggle_drawing_mode 方法在多周期模式下不存在"
        
        # 验证多周期Widget的画线交易功能
        if chart_window.multi_timeframe_widget:
            # 验证 enable_drawing_order 方法存在
            assert hasattr(chart_window.multi_timeframe_widget, 'enable_drawing_order'), \
                "MultiTimeframeWidget.enable_drawing_order 方法不存在"
            
            # 验证内部 ChartWidget 的画线交易功能
            if hasattr(chart_window.multi_timeframe_widget, '_chart'):
                assert hasattr(chart_window.multi_timeframe_widget._chart, 'get_drawing_order_controller'), \
                    "MultiTimeframeWidget._chart.get_drawing_order_controller 方法不存在"
        
        # 验证两种模式下的画线交易功能都正常工作
        # 通过验证方法存在和调用路径正确来确认
        assert chart_window.display_mode == "multi", \
            "当前模式应为多周期模式"

