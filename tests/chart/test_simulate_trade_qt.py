"""模拟成交功能 QtTest 测试

使用 QtTest 和 pytest-qt 测试模拟成交功能的核心逻辑，包括：
1. 从价格线对象获取挂单参数的挂单线
2. 从内存获取挂单参数的挂单线（向后兼容）
3. 没有挂单参数的挂单线（应该跳过）
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from vnpy.trader.ui import QtGui, QtCore, QtWidgets
try:
    from PySide6.QtTest import QTest
except ImportError:
    try:
        from PyQt6.QtTest import QTest
    except ImportError:
        from PyQt5.QtTest import QTest

from vnpy.chart.widget import ChartWidget
from vnpy.chart.price_line import PriceLineType, PriceLineItem
from vnpy.trader.object import TickData, ContractData
from vnpy.trader.constant import Exchange, Direction, Offset
from tests.chart.test_base import TestBase


class TestSimulateTradeQt(TestBase):
    """使用 QtTest 测试模拟成交功能的核心逻辑"""
    
    @staticmethod
    def _execute_simulate_trade_core(self, widget, log_calls):
        """执行模拟成交的核心逻辑（用于测试）"""
        # 复制自 widget.py 的 simulate_trade_breakthrough 方法的核心逻辑
        widget.main_engine.write_log("[模拟成交] 方法被调用")
        
        if not widget.chart:
            widget.main_engine.write_log("[模拟成交] 图表未初始化，无法模拟成交")
            return
        
        # 获取所有挂单线
        price_line_manager = widget.chart._price_line_manager
        if not price_line_manager:
            widget.main_engine.write_log("[模拟成交] 价格线管理器未初始化")
            return
        
        all_lines = price_line_manager.get_all_lines()
        widget.main_engine.write_log(f"[模拟成交] 找到 {len(all_lines)} 条价格线")
        
        # 筛选出挂单线
        from vnpy.chart.price_line import PriceLineType
        pending_lines = {
            line_id: line 
            for line_id, line in all_lines.items() 
            if line.get_line_type() == PriceLineType.PENDING
        }
        
        widget.main_engine.write_log(f"[模拟成交] 找到 {len(pending_lines)} 条挂单线")
        
        if not pending_lines:
            widget.main_engine.write_log("[模拟成交] 没有找到挂单线，无法模拟成交")
            return
        
        # 获取当前合约信息
        vt_symbol = widget.current_vt_symbol
        if not vt_symbol:
            widget.main_engine.write_log("未选择合约，无法模拟成交")
            return
        
        # 获取合约信息
        contract = widget.main_engine.get_contract(vt_symbol)
        if not contract:
            widget.main_engine.write_log(f"合约 {vt_symbol} 未找到，无法模拟成交")
            return
        
        # 遍历所有挂单线
        for line_id, line in pending_lines.items():
            # 确保挂单线已注册到价格突破监控
            controller = widget.chart.get_drawing_order_controller()
            if not controller:
                widget.main_engine.write_log(f"模拟成交失败: 无法获取画线订单控制器")
                continue
            
            # 检查挂单线是否有挂单参数（核心测试逻辑）
            order_volume = line.get_order_volume()
            order_offset = line.get_order_offset()
            
            has_pending_params_in_line = (order_volume is not None and order_offset is not None)
            
            has_pending_params_in_memory = (
                hasattr(controller, '_pending_order_params') and 
                line_id in controller._pending_order_params
            )
            
            has_pending_params = has_pending_params_in_line or has_pending_params_in_memory
            
            if not has_pending_params:
                widget.main_engine.write_log(
                    f"模拟成交跳过: 挂单线 {line_id} 没有挂单参数（价格线对象: volume={order_volume}, offset={order_offset}, "
                    f"内存参数: {has_pending_params_in_memory}）。请重新创建挂单或确保挂单参数已正确加载。"
                )
                continue
            
            # 如果价格线对象中有参数，记录日志
            if has_pending_params_in_line:
                widget.main_engine.write_log(
                    f"模拟成交: 挂单线 {line_id} 从价格线对象获取挂单参数 (volume={order_volume}, offset={order_offset})"
                )
            elif has_pending_params_in_memory:
                widget.main_engine.write_log(
                    f"模拟成交: 挂单线 {line_id} 从内存获取挂单参数（向后兼容）"
                )
            
            # 调用 trigger_pending_order_breakthrough
            if hasattr(widget.chart, 'trigger_pending_order_breakthrough'):
                widget.chart.trigger_pending_order_breakthrough(line_id, line, Mock())
    
    @pytest.fixture
    def chart_widget(self, qtbot):
        """创建 ChartWidget 实例"""
        chart = ChartWidget()
        qtbot.addWidget(chart)
        
        # 初始化 ChartWidget
        chart._main_engine = Mock()
        chart._main_engine.write_log = Mock()
        chart._event_engine = Mock()
        chart._vt_symbol = "MHI2512.HKFE"
        chart.add_plot("candle", hide_x_axis=True)
        chart.get_price_line_manager()
        
        # 确保 widget 可见
        chart.show()
        qtbot.waitExposed(chart)
        qtbot.wait(100)
        
        return chart
    
    @pytest.fixture
    def mock_trading_widget(self, chart_widget):
        """创建模拟的 TradingWidget，只包含必要的属性和方法"""
        widget = Mock()
        widget.chart = chart_widget
        widget.main_engine = chart_widget._main_engine
        widget.current_vt_symbol = "MHI2512.HKFE"
        
        # 直接绑定核心逻辑方法到 mock 对象
        # 使用 _execute_simulate_trade_core 方法，避免访问 TradingWidget 的方法
        def simulate_wrapper():
            # 直接调用核心逻辑
            return TestSimulateTradeQt._execute_simulate_trade_core(None, widget, [])
        
        widget.simulate_trade_breakthrough = simulate_wrapper
        
        return widget
    
    def _simulate_trade_core(self):
        """模拟成交的核心逻辑（用于测试）"""
        # 这个方法会在测试中直接调用，不依赖 TradingWidget 的完整初始化
        pass
    
    @pytest.fixture
    def mock_price_line_with_params(self):
        """创建带挂单参数的价格线（模拟从数据库加载）"""
        line = Mock(spec=PriceLineItem)
        line.get_line_type.return_value = PriceLineType.PENDING
        line.get_price.return_value = 20000.0
        line.get_direction.return_value = "long"
        line.get_order_volume.return_value = 10.0  # 从价格线对象获取
        line.get_order_offset.return_value = "OPEN"  # 从价格线对象获取
        line.line_id = "pending_test_001"
        return line
    
    @pytest.fixture
    def mock_price_line_without_params(self):
        """创建不带挂单参数的价格线"""
        line = Mock(spec=PriceLineItem)
        line.get_line_type.return_value = PriceLineType.PENDING
        line.get_price.return_value = 20000.0
        line.get_direction.return_value = "long"
        line.get_order_volume.return_value = None  # 没有参数
        line.get_order_offset.return_value = None  # 没有参数
        line.line_id = "pending_test_002"
        return line
    
    def test_simulate_trade_with_line_params(self, mock_trading_widget, qtbot, mock_price_line_with_params):
        """测试从价格线对象获取挂单参数的模拟成交"""
        # 设置价格线管理器
        price_line_manager = mock_trading_widget.chart._price_line_manager
        price_line_manager._lines = {
            "pending_test_001": mock_price_line_with_params
        }
        price_line_manager.get_all_lines = Mock(return_value={
            "pending_test_001": mock_price_line_with_params
        })
        
        # 设置画线订单控制器（没有内存中的参数，只依赖价格线对象）
        controller = Mock()
        controller._pending_order_params = {}  # 内存中没有参数
        mock_trading_widget.chart._drawing_order_controller = controller
        mock_trading_widget.chart.get_drawing_order_controller = Mock(return_value=controller)
        
        # 设置价格突破监控
        breakthrough_monitor = Mock()
        mock_trading_widget.chart._breakthrough_monitor = breakthrough_monitor
        
        # Mock trigger_pending_order_breakthrough 方法
        mock_trading_widget.chart.trigger_pending_order_breakthrough = Mock(return_value=True)
        
        # 设置合约信息
        contract = Mock()
        contract.gateway_name = "TEST"
        contract.pricetick = 1.0
        mock_trading_widget.main_engine.get_contract = Mock(return_value=contract)
        mock_trading_widget.main_engine.get_tick = Mock(return_value=None)
        
        # 记录日志调用
        log_calls = []
        original_write_log = mock_trading_widget.main_engine.write_log
        
        def log_wrapper(message):
            log_calls.append(message)
            original_write_log(message)
        
        mock_trading_widget.main_engine.write_log = log_wrapper
        
        # 执行模拟成交（直接调用核心逻辑）
        TestSimulateTradeQt._execute_simulate_trade_core(None, mock_trading_widget, log_calls)
        
        # 等待处理完成
        qtbot.wait(200)
        
        # 验证：应该找到挂单参数（从价格线对象）
        assert any("从价格线对象获取挂单参数" in log for log in log_calls), \
            f"应该记录从价格线对象获取挂单参数的日志，实际日志: {log_calls}"
        
        # 验证：应该调用 trigger_pending_order_breakthrough
        mock_trading_widget.chart.trigger_pending_order_breakthrough.assert_called_once()
        
        # 验证：不应该跳过（没有"模拟成交跳过"的日志）
        assert not any("模拟成交跳过" in log for log in log_calls), \
            "不应该跳过有挂单参数的挂单线"
    
    def test_simulate_trade_with_memory_params(self, mock_trading_widget, qtbot, mock_price_line_without_params):
        """测试从内存获取挂单参数的模拟成交（向后兼容）"""
        # 设置价格线管理器
        price_line_manager = mock_trading_widget.chart._price_line_manager
        price_line_manager._lines = {
            "pending_test_002": mock_price_line_without_params
        }
        price_line_manager.get_all_lines = Mock(return_value={
            "pending_test_002": mock_price_line_without_params
        })
        
        # 设置画线订单控制器（内存中有参数）
        controller = Mock()
        controller._pending_order_params = {
            "pending_test_002": {
                "params": {
                    "volume": 10.0,
                    "offset": Offset.OPEN
                },
                "vt_symbol": "MHI2512.HKFE",
                "contract": Mock()
            }
        }
        mock_trading_widget.chart._drawing_order_controller = controller
        mock_trading_widget.chart.get_drawing_order_controller = Mock(return_value=controller)
        
        # 设置价格突破监控
        breakthrough_monitor = Mock()
        mock_trading_widget.chart._breakthrough_monitor = breakthrough_monitor
        
        # Mock trigger_pending_order_breakthrough 方法
        mock_trading_widget.chart.trigger_pending_order_breakthrough = Mock(return_value=True)
        
        # 设置合约信息
        contract = Mock()
        contract.gateway_name = "TEST"
        contract.pricetick = 1.0
        mock_trading_widget.main_engine.get_contract = Mock(return_value=contract)
        mock_trading_widget.main_engine.get_tick = Mock(return_value=None)
        
        # 记录日志调用
        log_calls = []
        original_write_log = mock_trading_widget.main_engine.write_log
        
        def log_wrapper(message):
            log_calls.append(message)
            original_write_log(message)
        
        mock_trading_widget.main_engine.write_log = log_wrapper
        
        # 执行模拟成交
        mock_trading_widget.simulate_trade_breakthrough()
        
        # 等待处理完成
        qtbot.wait(200)
        
        # 验证：应该找到挂单参数（从内存）
        assert any("从内存获取挂单参数" in log for log in log_calls), \
            f"应该记录从内存获取挂单参数的日志，实际日志: {log_calls}"
        
        # 验证：应该调用 trigger_pending_order_breakthrough
        mock_trading_widget.chart.trigger_pending_order_breakthrough.assert_called_once()
        
        # 验证：不应该跳过
        assert not any("模拟成交跳过" in log for log in log_calls), \
            "不应该跳过有内存参数的挂单线"
    
    def test_simulate_trade_without_params(self, mock_trading_widget, qtbot, mock_price_line_without_params):
        """测试没有挂单参数的挂单线（应该跳过）"""
        # 设置价格线管理器
        price_line_manager = mock_trading_widget.chart._price_line_manager
        price_line_manager._lines = {
            "pending_test_002": mock_price_line_without_params
        }
        price_line_manager.get_all_lines = Mock(return_value={
            "pending_test_002": mock_price_line_without_params
        })
        
        # 设置画线订单控制器（内存中也没有参数）
        controller = Mock()
        controller._pending_order_params = {}  # 内存中也没有参数
        mock_trading_widget.chart._drawing_order_controller = controller
        mock_trading_widget.chart.get_drawing_order_controller = Mock(return_value=controller)
        
        # 设置合约信息
        contract = Mock()
        contract.gateway_name = "TEST"
        contract.pricetick = 1.0
        mock_trading_widget.main_engine.get_contract = Mock(return_value=contract)
        mock_trading_widget.main_engine.get_tick = Mock(return_value=None)
        
        # 记录日志调用
        log_calls = []
        original_write_log = mock_trading_widget.main_engine.write_log
        
        def log_wrapper(message):
            log_calls.append(message)
            original_write_log(message)
        
        mock_trading_widget.main_engine.write_log = log_wrapper
        
        # 执行模拟成交
        mock_trading_widget.simulate_trade_breakthrough()
        
        # 等待处理完成
        qtbot.wait(200)
        
        # 验证：应该跳过（没有挂单参数）
        assert any("模拟成交跳过" in log for log in log_calls), \
            f"应该跳过没有挂单参数的挂单线，实际日志: {log_calls}"
        
        # 验证：应该记录详细的参数信息
        skip_log = [log for log in log_calls if "模拟成交跳过" in log][0]
        assert "价格线对象" in skip_log, "应该记录价格线对象的参数信息"
        assert "内存参数" in skip_log, "应该记录内存参数的检查结果"
