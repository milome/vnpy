"""Pytest fixtures for chart module tests."""

import pytest
from unittest.mock import Mock, MagicMock

# 注意：ChartWidget 的导入需要在 qapp fixture 之后，因为需要 Qt 环境
# 所以这里不直接导入，而是在需要时延迟导入


@pytest.fixture
def mock_main_engine():
    """创建模拟的MainEngine"""
    engine = Mock()
    engine.write_log = Mock()
    engine.get_contract = Mock(return_value=Mock(gateway_name="test"))
    engine.get_all_positions = Mock(return_value=[])
    engine.get_all_active_orders = Mock(return_value=[])
    engine.send_order = Mock(return_value="order_123")
    engine.cancel_order = Mock(return_value=True)
    return engine


@pytest.fixture
def mock_event_engine():
    """创建模拟的EventEngine"""
    engine = Mock()
    engine.register = Mock()
    engine.unregister = Mock()
    engine.put = Mock()
    return engine


@pytest.fixture
def chart_widget(mock_main_engine, mock_event_engine, qtbot):
    """创建ChartWidget实例用于测试
    
    注意：使用 qtbot fixture（来自 pytest-qt）来确保 Qt 环境已初始化
    """
    from vnpy.chart.widget import ChartWidget
    
    widget = ChartWidget()
    widget._main_engine = mock_main_engine
    widget._event_engine = mock_event_engine
    widget._vt_symbol = "MHI2512.HKFE"
    return widget

