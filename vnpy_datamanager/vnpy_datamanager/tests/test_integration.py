"""
集成测试：测试完整的数据更新流程
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from vnpy.trader.ui import QtWidgets

from vnpy.trader.engine import MainEngine, EventEngine
from vnpy.trader.constant import Interval, Exchange
from vnpy.trader.database import BarOverview, DB_TZ

from ..ui.widget import ManagerWidget
from ..engine import ManagerEngine


@pytest.fixture(scope="module")
def qapp():
    """创建QApplication实例"""
    import sys
    if not QtWidgets.QApplication.instance():
        app = QtWidgets.QApplication(sys.argv)
    else:
        app = QtWidgets.QApplication.instance()
    return app


class TestUpdateDataFlow:
    """测试数据更新流程"""
    
    def test_update_data_complete_flow(self, qapp):
        """测试完整的数据更新流程"""
        # 创建模拟对象
        mock_main_engine = Mock(spec=MainEngine)
        mock_main_engine.get_all_contracts = Mock(return_value=[])
        mock_event_engine = Mock(spec=EventEngine)
        mock_manager_engine = Mock(spec=ManagerEngine)
        
        # 设置模拟返回值
        overview1 = BarOverview(
            symbol="rb2401",
            exchange=Exchange.SHFE,
            interval=Interval.MINUTE,
            count=100,
            start=datetime(2024, 1, 1, 9, 0, 0, tzinfo=DB_TZ),
            end=datetime(2024, 1, 1, 15, 0, 0, tzinfo=DB_TZ)
        )
        overview2 = BarOverview(
            symbol="IF2401",
            exchange=Exchange.CFFEX,
            interval=Interval.MINUTE,
            count=200,
            start=datetime(2024, 1, 1, 9, 0, 0, tzinfo=DB_TZ),
            end=datetime(2024, 1, 1, 15, 0, 0, tzinfo=DB_TZ)
        )
        
        mock_manager_engine.get_bar_overview.return_value = [overview1, overview2]
        mock_manager_engine.download_bar_data.return_value = 50
        mock_manager_engine.aggregate_5minute_bars.return_value = 20
        mock_manager_engine.aggregate_hour_bars.return_value = 10
        mock_manager_engine.aggregate_4hour_bars.return_value = 5
        
        mock_main_engine.get_engine.return_value = mock_manager_engine
        
        # 创建widget
        widget = ManagerWidget(mock_main_engine, mock_event_engine)
        
        # 执行更新（不等待对话框）
        widget.update_data()
        
        # 验证调用了相关方法
        assert mock_manager_engine.get_bar_overview.called
        assert mock_manager_engine.download_bar_data.call_count == 2  # 两个合约
        assert mock_manager_engine.aggregate_5minute_bars.called
        assert mock_manager_engine.aggregate_hour_bars.called
        assert mock_manager_engine.aggregate_4hour_bars.called
        
        widget.close()


class TestAutoUpdateFlow:
    """测试自动更新流程"""
    
    def test_auto_update_enable_disable_flow(self, qapp):
        """测试启用和禁用自动更新的完整流程"""
        mock_main_engine = Mock(spec=MainEngine)
        mock_main_engine.get_all_contracts = Mock(return_value=[])
        mock_event_engine = Mock(spec=EventEngine)
        mock_manager_engine = Mock(spec=ManagerEngine)
        
        mock_manager_engine.get_bar_overview.return_value = []
        mock_main_engine.get_engine.return_value = mock_manager_engine
        
        widget = ManagerWidget(mock_main_engine, mock_event_engine)
        
        # 启用自动更新
        widget.auto_update_checkbox.setChecked(True)
        widget.on_auto_update_changed(2)  # Checked状态值
        
        assert widget.auto_update_enabled == True
        assert widget.auto_update_timer is not None
        assert widget.auto_update_timer.isActive()
        
        # 禁用自动更新
        widget.auto_update_checkbox.setChecked(False)
        widget.on_auto_update_changed(0)  # Unchecked状态值
        
        assert widget.auto_update_enabled == False
        if widget.auto_update_timer:
            assert not widget.auto_update_timer.isActive()
        
        widget.close()
    
    def test_auto_update_execution(self, qapp):
        """测试自动更新执行"""
        mock_main_engine = Mock(spec=MainEngine)
        mock_main_engine.get_all_contracts = Mock(return_value=[])
        mock_event_engine = Mock(spec=EventEngine)
        mock_manager_engine = Mock(spec=ManagerEngine)
        
        overview = BarOverview(
            symbol="rb2401",
            exchange=Exchange.SHFE,
            interval=Interval.MINUTE,
            count=100,
            start=datetime(2024, 1, 1, 9, 0, 0, tzinfo=DB_TZ),
            end=datetime(2024, 1, 1, 15, 0, 0, tzinfo=DB_TZ)
        )
        
        mock_manager_engine.get_bar_overview.return_value = [overview]
        mock_manager_engine.download_bar_data.return_value = 50
        mock_manager_engine.aggregate_5minute_bars.return_value = 20
        mock_manager_engine.aggregate_hour_bars.return_value = 10
        mock_manager_engine.aggregate_4hour_bars.return_value = 5
        
        mock_main_engine.get_engine.return_value = mock_manager_engine
        
        widget = ManagerWidget(mock_main_engine, mock_event_engine)
        
        # 执行自动更新
        widget._execute_auto_update()
        
        # 验证调用了相关方法
        assert mock_manager_engine.get_bar_overview.called
        assert mock_manager_engine.download_bar_data.called
        assert widget.is_updating == False  # 更新完成后应该重置标志
        
        widget.close()

