"""
测试ManagerWidget和UpdateProgressDialog
"""
import pytest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime, timedelta

from vnpy.trader.ui import QtWidgets, QtCore

from vnpy.trader.engine import MainEngine, EventEngine
from vnpy.trader.constant import Interval, Exchange
from vnpy.trader.database import BarOverview, DB_TZ

from ..ui.widget import ManagerWidget, UpdateProgressDialog
from ..engine import ManagerEngine


@pytest.fixture(scope="module")
def qapp():
    """创建QApplication实例（模块级别，所有测试共享）"""
    import sys
    if not QtWidgets.QApplication.instance():
        app = QtWidgets.QApplication(sys.argv)
    else:
        app = QtWidgets.QApplication.instance()
    return app


@pytest.fixture
def mock_main_engine():
    """创建模拟的MainEngine"""
    engine = Mock(spec=MainEngine)
    engine.write_log = Mock()
    engine.get_all_contracts = Mock(return_value=[])
    return engine


@pytest.fixture
def mock_event_engine():
    """创建模拟的EventEngine"""
    engine = Mock(spec=EventEngine)
    engine.register = Mock()
    return engine


@pytest.fixture
def mock_manager_engine():
    """创建模拟的ManagerEngine"""
    engine = Mock(spec=ManagerEngine)
    engine.get_bar_overview = Mock(return_value=[])
    engine.download_bar_data = Mock(return_value=100)
    engine.aggregate_5minute_bars = Mock(return_value=50)
    engine.aggregate_hour_bars = Mock(return_value=20)
    engine.aggregate_4hour_bars = Mock(return_value=10)
    return engine


@pytest.fixture
def manager_widget(mock_main_engine, mock_event_engine, mock_manager_engine, qapp):
    """创建ManagerWidget实例"""
    with patch.object(mock_main_engine, 'get_engine', return_value=mock_manager_engine):
        widget = ManagerWidget(mock_main_engine, mock_event_engine)
        yield widget
        widget.close()


class TestUpdateProgressDialog:
    """测试UpdateProgressDialog类"""
    
    def test_init(self, qapp):
        """测试对话框初始化"""
        dialog = UpdateProgressDialog()
        assert dialog.windowTitle() == "更新进度"
        assert dialog.progress_bar.value() == 0
        assert dialog.progress_bar.maximum() == 100
        assert not dialog.close_button.isEnabled()
        assert dialog.total_tasks == 0
        assert dialog.completed_tasks == 0
        assert dialog.total_bars == 0
    
    def test_set_total_tasks(self, qapp):
        """测试设置总任务数"""
        dialog = UpdateProgressDialog()
        dialog.set_total_tasks(10)
        assert dialog.total_tasks == 10
        assert "找到 10 个合约需要更新" in dialog.message_list.toPlainText()
    
    def test_update_progress(self, qapp):
        """测试更新进度"""
        dialog = UpdateProgressDialog()
        dialog.set_total_tasks(10)
        dialog.update_progress(5, 10, "测试任务")
        assert dialog.progress_bar.value() == 50
        assert "测试任务 (5/10)" in dialog.current_task_label.text()
    
    def test_append_message(self, qapp):
        """测试追加消息"""
        dialog = UpdateProgressDialog()
        dialog.append_message("测试消息")
        text = dialog.message_list.toPlainText()
        assert "测试消息" in text
        # 检查时间戳格式
        assert "[" in text and "]" in text
    
    def test_set_completed(self, qapp):
        """测试设置完成状态"""
        dialog = UpdateProgressDialog()
        dialog.set_total_tasks(10)
        dialog.set_completed(1000, 10, 10)
        assert dialog.progress_bar.value() == 100
        assert dialog.current_task_label.text() == "更新完成！"
        assert dialog.close_button.isEnabled()
        assert "更新完成" in dialog.message_list.toPlainText()
        assert "1,000" in dialog.stats_label.text()


class TestManagerWidget:
    """测试ManagerWidget类"""
    
    def test_init(self, manager_widget):
        """测试初始化"""
        assert manager_widget.windowTitle() == "数据管理"
        assert manager_widget.auto_update_enabled == False
        assert manager_widget.auto_update_interval == 60
        assert manager_widget.is_updating == False
    
    def test_auto_update_checkbox_initial_state(self, manager_widget):
        """测试自动更新复选框初始状态"""
        assert not manager_widget.auto_update_checkbox.isChecked()
        assert not manager_widget.auto_update_interval_spin.isEnabled()
        assert not manager_widget.next_update_label.isEnabled()
    
    def test_on_auto_update_changed_enable(self, manager_widget):
        """测试启用自动更新"""
        manager_widget.auto_update_checkbox.setChecked(True)
        manager_widget.on_auto_update_changed(QtCore.Qt.CheckState.Checked.value)
        
        assert manager_widget.auto_update_enabled == True
        assert manager_widget.auto_update_interval_spin.isEnabled()
        assert manager_widget.next_update_label.isEnabled()
        assert manager_widget.auto_update_timer is not None
        assert manager_widget.auto_update_timer.isActive()
    
    def test_on_auto_update_changed_disable(self, manager_widget):
        """测试禁用自动更新"""
        # 先启用
        manager_widget.auto_update_checkbox.setChecked(True)
        manager_widget.on_auto_update_changed(QtCore.Qt.CheckState.Checked.value)
        
        # 再禁用
        manager_widget.auto_update_checkbox.setChecked(False)
        manager_widget.on_auto_update_changed(QtCore.Qt.CheckState.Unchecked.value)
        
        assert manager_widget.auto_update_enabled == False
        if manager_widget.auto_update_timer:
            assert not manager_widget.auto_update_timer.isActive()
    
    def test_on_auto_update_interval_changed(self, manager_widget):
        """测试更新间隔改变"""
        # 启用自动更新
        manager_widget.auto_update_checkbox.setChecked(True)
        manager_widget.on_auto_update_changed(QtCore.Qt.CheckState.Checked.value)
        
        # 改变间隔
        manager_widget.auto_update_interval_spin.setValue(30)
        manager_widget.on_auto_update_interval_changed(30)
        
        assert manager_widget.auto_update_interval == 30
    
    def test_start_auto_update(self, manager_widget, qapp):
        """测试启动自动更新"""
        manager_widget.auto_update_interval = 30
        manager_widget.auto_update_enabled = True  # 先设置为启用状态
        manager_widget.start_auto_update()
        
        # 处理Qt事件，确保UI更新
        qapp.processEvents()
        
        assert manager_widget.auto_update_timer is not None
        assert manager_widget.auto_update_timer.isActive()
        # 验证标签文本已更新（可能包含时间信息）
        label_text = manager_widget.next_update_label.text()
        assert label_text != ""  # 标签应该有内容
    
    def test_stop_auto_update(self, manager_widget):
        """测试停止自动更新"""
        manager_widget.start_auto_update()
        manager_widget.stop_auto_update()
        
        if manager_widget.auto_update_timer:
            assert not manager_widget.auto_update_timer.isActive()
        assert manager_widget.next_update_label.text() == ""
    
    def test_update_next_update_time(self, manager_widget):
        """测试更新下次更新时间"""
        manager_widget.auto_update_enabled = True
        manager_widget.start_auto_update()
        manager_widget.update_next_update_time()
        
        assert "下次更新:" in manager_widget.next_update_label.text()
        # 检查时间格式
        assert ":" in manager_widget.next_update_label.text()
    
    def test_update_data_no_overviews(self, manager_widget, mock_manager_engine):
        """测试更新数据 - 没有数据"""
        mock_manager_engine.get_bar_overview.return_value = []
        
        # 使用patch来捕获QMessageBox
        with patch('vnpy_datamanager.ui.widget.QtWidgets.QMessageBox.information') as mock_msg:
            manager_widget.update_data()
            mock_msg.assert_called_once()
    
    def test_update_data_with_overviews(self, manager_widget, mock_manager_engine, qapp):
        """测试更新数据 - 有数据"""
        # 创建测试数据
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
        
        # 执行更新（不等待对话框关闭）
        manager_widget.update_data()
        
        # 验证调用了下载方法
        assert mock_manager_engine.download_bar_data.called
    
    def test_auto_update_data(self, manager_widget, mock_manager_engine):
        """测试自动更新数据"""
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
        
        # 执行自动更新
        manager_widget._execute_auto_update()
        
        # 验证调用了下载方法
        assert mock_manager_engine.download_bar_data.called
        assert manager_widget.is_updating == False
    
    def test_auto_update_data_prevent_duplicate(self, manager_widget, mock_manager_engine):
        """测试防止重复更新"""
        manager_widget.is_updating = True
        
        # 尝试触发自动更新
        manager_widget.auto_update_data()
        
        # 由于is_updating为True，应该不会执行更新
        # 这里主要验证不会抛出异常
    
    def test_close_event(self, manager_widget):
        """测试窗口关闭事件"""
        manager_widget.start_auto_update()
        
        # 模拟关闭事件
        from vnpy.trader.ui import QtGui
        event = QtGui.QCloseEvent()
        manager_widget.closeEvent(event)
        
        # 验证定时器已停止
        if manager_widget.auto_update_timer:
            assert not manager_widget.auto_update_timer.isActive()
    
    def test_output_method(self, manager_widget):
        """测试output方法（不再弹出弹窗）"""
        with patch('builtins.print') as mock_print:
            manager_widget.output("测试消息")
            mock_print.assert_called_once()
            # 验证没有调用QMessageBox
            assert "[数据下载] 测试消息" in str(mock_print.call_args)

