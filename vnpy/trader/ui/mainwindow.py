"""
Implements main window of the trading platform.
"""

from types import ModuleType
from functools import partial
from importlib import import_module
from typing import TypeVar
from collections.abc import Callable

import vnpy
from vnpy.event import EventEngine

from .qt import QtCore, QtGui, QtWidgets
from .widget import (
    BaseMonitor,
    TickMonitor,
    OrderMonitor,
    TradeMonitor,
    PositionMonitor,
    AccountMonitor,
    LogMonitor,
    ActiveOrderMonitor,
    ConnectDialog,
    ContractManager,
    TradingWidget,
    AboutDialog,
    GlobalDialog,
    ToastNotification,
    ChartWindow
)
from ..engine import MainEngine, BaseApp
from ..utility import get_icon_path, TRADER_DIR
from ..locale import _
from ..event import EVENT_MAIN_CONTRACT_SWITCH


WidgetType = TypeVar("WidgetType", bound="QtWidgets.QWidget")


class MainWindow(QtWidgets.QMainWindow):
    """
    Main window of the trading platform.
    """

    # 信号定义（用于跨线程UI更新）
    signal_main_contract_switch = QtCore.Signal(object)
    
    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        """"""
        super().__init__()

        self.main_engine: MainEngine = main_engine
        self.event_engine: EventEngine = event_engine

        self.window_title: str = _("VeighNa Trader 社区版 - {}   [{}]").format(vnpy.__version__, TRADER_DIR)

        self.widgets: dict[str, QtWidgets.QWidget] = {}
        self.monitors: dict[str, BaseMonitor] = {}
        
        # Toast通知组件
        self.toast: ToastNotification = None

        self.init_ui()
        self.init_toast()
        self.register_event()

    def init_ui(self) -> None:
        """"""
        self.setWindowTitle(self.window_title)
        self.init_dock()
        self.init_toolbar()
        self.init_menu()
        self.load_window_setting("custom")

    def init_dock(self) -> None:
        """"""
        self.trading_widget, trading_dock = self.create_dock(
            TradingWidget, _("交易"), QtCore.Qt.DockWidgetArea.LeftDockWidgetArea
        )
        
        tick_widget, tick_dock = self.create_dock(
            TickMonitor, _("行情"), QtCore.Qt.DockWidgetArea.RightDockWidgetArea
        )
        order_widget, order_dock = self.create_dock(
            OrderMonitor, _("委托"), QtCore.Qt.DockWidgetArea.RightDockWidgetArea
        )
        active_widget, active_dock = self.create_dock(
            ActiveOrderMonitor, _("活动"), QtCore.Qt.DockWidgetArea.RightDockWidgetArea
        )
        trade_widget, trade_dock = self.create_dock(
            TradeMonitor, _("成交"), QtCore.Qt.DockWidgetArea.RightDockWidgetArea
        )
        log_widget, log_dock = self.create_dock(
            LogMonitor, _("日志"), QtCore.Qt.DockWidgetArea.BottomDockWidgetArea
        )
        account_widget, account_dock = self.create_dock(
            AccountMonitor, _("资金"), QtCore.Qt.DockWidgetArea.BottomDockWidgetArea
        )
        position_widget, position_dock = self.create_dock(
            PositionMonitor, _("持仓"), QtCore.Qt.DockWidgetArea.BottomDockWidgetArea
        )

        self.tabifyDockWidget(active_dock, order_dock)

        self.save_window_setting("default")

        tick_widget.itemDoubleClicked.connect(self.trading_widget.update_with_cell)
        position_widget.itemDoubleClicked.connect(self.trading_widget.update_with_cell)

    def init_menu(self) -> None:
        """"""
        bar: QtWidgets.QMenuBar = self.menuBar()
        bar.setNativeMenuBar(False)     # for mac and linux

        # System menu
        sys_menu: QtWidgets.QMenu = bar.addMenu(_("系统"))

        gateway_names: list = self.main_engine.get_all_gateway_names()
        for name in gateway_names:
            func: Callable = partial(self.connect_gateway, name)
            self.add_action(
                sys_menu,
                _("连接{}").format(name),
                get_icon_path(__file__, "connect.ico"),
                func
            )

        sys_menu.addSeparator()

        self.add_action(
            sys_menu,
            _("退出"),
            get_icon_path(__file__, "exit.ico"),
            self.close
        )

        # App menu
        app_menu: QtWidgets.QMenu = bar.addMenu(_("功能"))

        all_apps: list[BaseApp] = self.main_engine.get_all_apps()
        for app in all_apps:
            ui_module: ModuleType = import_module(app.app_module + ".ui")
            widget_class: type[QtWidgets.QWidget] = getattr(ui_module, app.widget_name)

            func = partial(self.open_widget, widget_class, app.app_name)

            self.add_action(app_menu, app.display_name, app.icon_name, func, True)

        # Global setting editor
        action: QtGui.QAction = QtGui.QAction(_("配置"), self)
        action.triggered.connect(self.edit_global_setting)
        bar.addAction(action)

        # Help menu
        help_menu: QtWidgets.QMenu = bar.addMenu(_("帮助"))

        # K线图表
        self.add_action(
            help_menu,
            _("K线图表"),
            get_icon_path(__file__, "chart.ico"),
            self.open_chart_window,
            True
        )
        
        # 模拟功能开关（toggle action）
        self.simulate_functions_action: QtGui.QAction = QtGui.QAction(_("禁用模拟功能"), self)
        self.simulate_functions_action.setCheckable(True)
        self.simulate_functions_action.setChecked(True)  # 默认启用（checked=True表示启用）
        self.simulate_functions_action.triggered.connect(self.toggle_simulate_functions)
        self.simulate_functions_action.setToolTip(_("统一控制模拟成交、模拟止损、模拟止盈三个按钮的启用/禁用状态（交易时段建议禁用）"))
        help_menu.addAction(self.simulate_functions_action)
        # 初始化菜单项文本（根据checked状态）
        self._update_simulate_functions_menu_text()

        self.add_action(
            help_menu,
            _("查询合约"),
            get_icon_path(__file__, "contract.ico"),
            partial(self.open_widget, ContractManager, "contract"),
            True
        )

        self.add_action(
            help_menu,
            _("还原窗口"),
            get_icon_path(__file__, "restore.ico"),
            self.restore_window_setting
        )

        self.add_action(
            help_menu,
            _("测试邮件"),
            get_icon_path(__file__, "email.ico"),
            self.send_test_email
        )

        self.add_action(
            help_menu,
            _("关于"),
            get_icon_path(__file__, "about.ico"),
            partial(self.open_widget, AboutDialog, "about"),
        )

    def init_toolbar(self) -> None:
        """"""
        self.toolbar: QtWidgets.QToolBar = QtWidgets.QToolBar(self)
        self.toolbar.setObjectName(_("工具栏"))
        self.toolbar.setFloatable(False)
        self.toolbar.setMovable(False)

        # Set button size
        w: int = 40
        size = QtCore.QSize(w, w)
        self.toolbar.setIconSize(size)

        # Set button spacing
        layout: QtWidgets.QLayout | None = self.toolbar.layout()
        if layout:
            layout.setSpacing(10)

        self.addToolBar(QtCore.Qt.ToolBarArea.LeftToolBarArea, self.toolbar)
    
    def init_toast(self) -> None:
        """初始化Toast通知组件"""
        self.toast = ToastNotification(self)
        
        # 初始化状态栏（用于显示滚动消息）
        self.statusBar().showMessage(_("就绪"))
    
    def register_event(self) -> None:
        """注册事件监听"""
        # 监听主力合约切换事件
        self.signal_main_contract_switch.connect(self.process_main_contract_switch)
        self.event_engine.register(EVENT_MAIN_CONTRACT_SWITCH, self.signal_main_contract_switch.emit)
        self.main_engine.write_log(f"[MainWindow] 已注册主力合约切换事件监听: {EVENT_MAIN_CONTRACT_SWITCH}")
    
    def process_main_contract_switch(self, event) -> None:
        """处理主力合约切换事件 - 显示Toast提示"""
        try:
            switch_data = event.data
            self.main_engine.write_log(f"[MainWindow] 收到主力合约切换事件: {switch_data.main_symbol} {switch_data.old_actual_symbol} -> {switch_data.new_actual_symbol}")
            
            # 判断是否提前切换
            is_early = getattr(switch_data, 'is_early_switch', False)
            self.main_engine.write_log(f"[MainWindow] 提前切换标志: {is_early}")
            
            if is_early:
                # 提前切换 - 更强的提示
                message = _("主力合约提前切换！{} → {}").format(
                    switch_data.old_actual_symbol,
                    switch_data.new_actual_symbol
                )
                
                # 确保Toast组件已初始化
                if not self.toast:
                    self.init_toast()
                
                # 显示更醒目的Toast（橙色警告色，显示更长时间，屏幕中央）
                if self.toast:
                    self.toast.show_message(
                        message, 
                        duration=8000,  # 显示8秒
                        icon="⚠️",
                        color="rgba(255, 140, 0, 240)",  # 深橙色背景（警告色）
                        position="center"  # 屏幕中央显示
                    )
                
                # 状态栏持续显示警告
                status_message = _("⚠️ 主力合约提前切换: {} → {} (当前日期早于新合约月份)").format(
                    switch_data.old_actual_symbol,
                    switch_data.new_actual_symbol
                )
                # 使用QTimer确保状态栏消息不被覆盖
                status_bar = self.statusBar()
                status_bar.showMessage(status_message, 0)  # 0表示永久显示
                
                # 设置状态栏样式为警告色
                status_bar.setStyleSheet(
                    "QStatusBar { background-color: #FFF3CD; color: #856404; font-weight: bold; }"
                )
                
                # 记录日志
                self.main_engine.write_log(f"主力合约提前切换通知已显示: {message}")
            else:
                # 正常切换 - 温和提示
                message = _("主力合约切换: {} → {}").format(
                    switch_data.old_actual_symbol,
                    switch_data.new_actual_symbol
                )
                
                # 确保Toast组件已初始化
                if not self.toast:
                    self.init_toast()
                
                # 显示Toast提示（温和的浮动通知，顶部显示）
                if self.toast:
                    self.toast.show_message(
                        message, 
                        duration=5000,  # 显示5秒
                        icon="🔄",
                        color="rgba(30, 144, 255, 230)",  # 道奇蓝色背景
                        position="top"  # 顶部显示，不遮挡内容
                    )
                
                # 状态栏显示30秒后消失
                status_message = _("📢 主力合约切换: {} → {}").format(
                    switch_data.old_actual_symbol,
                    switch_data.new_actual_symbol
                )
                status_bar = self.statusBar()
                status_bar.showMessage(status_message, 30000)
                
                # 恢复状态栏默认样式
                status_bar.setStyleSheet("")
                
                # 记录日志
                self.main_engine.write_log(f"主力合约切换通知已显示: {message}")
        except Exception as e:
            # 记录错误日志
            self.main_engine.write_log(f"处理主力合约切换事件时发生错误: {str(e)}", "MainWindow")

    def add_action(
        self,
        menu: QtWidgets.QMenu,
        action_name: str,
        icon_name: str,
        func: Callable,
        toolbar: bool = False
    ) -> None:
        """"""
        icon: QtGui.QIcon = QtGui.QIcon(icon_name)

        action: QtGui.QAction = QtGui.QAction(action_name, self)
        action.triggered.connect(func)
        action.setIcon(icon)

        menu.addAction(action)

        if toolbar:
            self.toolbar.addAction(action)

    def create_dock(
        self,
        widget_class: type[WidgetType],
        name: str,
        area: QtCore.Qt.DockWidgetArea
    ) -> tuple[WidgetType, QtWidgets.QDockWidget]:
        """
        Initialize a dock widget.
        """
        widget: WidgetType = widget_class(self.main_engine, self.event_engine)      # type: ignore
        if isinstance(widget, BaseMonitor):
            self.monitors[name] = widget

        dock: QtWidgets.QDockWidget = QtWidgets.QDockWidget(name)
        dock.setWidget(widget)
        dock.setObjectName(name)
        dock.setFeatures(dock.DockWidgetFeature.DockWidgetFloatable | dock.DockWidgetFeature.DockWidgetMovable)
        self.addDockWidget(area, dock)
        return widget, dock

    def connect_gateway(self, gateway_name: str) -> None:
        """
        Open connect dialog for gateway connection.
        """
        dialog: ConnectDialog = ConnectDialog(self.main_engine, gateway_name)
        dialog.exec()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """
        Call main engine close function before exit.
        """
        reply = QtWidgets.QMessageBox.question(
            self,
            _("退出"),
            _("确认退出？"),
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No,
        )

        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            for widget in self.widgets.values():
                widget.close()

            for monitor in self.monitors.values():
                monitor.save_setting()

            self.save_window_setting("custom")

            self.main_engine.close()

            event.accept()
        else:
            event.ignore()

    def open_widget(self, widget_class: type[QtWidgets.QWidget], name: str) -> None:
        """
        Open contract manager.
        """
        widget: QtWidgets.QWidget | None = self.widgets.get(name, None)
        if not widget:
            widget = widget_class(self.main_engine, self.event_engine)      # type: ignore
            self.widgets[name] = widget

        if isinstance(widget, QtWidgets.QDialog):
            widget.exec()
        else:
            widget.show()

    def save_window_setting(self, name: str) -> None:
        """
        Save current window size and state by trader path and setting name.
        """
        settings: QtCore.QSettings = QtCore.QSettings(self.window_title, name)
        settings.setValue("state", self.saveState())
        settings.setValue("geometry", self.saveGeometry())

    def load_window_setting(self, name: str) -> None:
        """
        Load previous window size and state by trader path and setting name.
        """
        settings: QtCore.QSettings = QtCore.QSettings(self.window_title, name)
        state = settings.value("state")
        geometry = settings.value("geometry")

        if isinstance(state, QtCore.QByteArray):
            self.restoreState(state)
            self.restoreGeometry(geometry)

    def restore_window_setting(self) -> None:
        """
        Restore window to default setting.
        """
        self.load_window_setting("default")
        self.showMaximized()

    def send_test_email(self) -> None:
        """
        Sending a test email.
        """
        self.main_engine.send_email("VeighNa Trader", "testing", None)

    def open_chart_window(self) -> None:
        """
        打开K线图表窗口。
        """
        chart_window: ChartWindow | None = self.widgets.get("chart_window", None)
        if not chart_window:
            chart_window = ChartWindow(self.main_engine, self.event_engine)
            self.widgets["chart_window"] = chart_window
            # 同步模拟功能开关状态
            if hasattr(self, 'simulate_functions_action'):
                chart_window.set_simulate_functions_enabled(self.simulate_functions_action.isChecked())
        
        chart_window.show()
    
    def _update_simulate_functions_menu_text(self) -> None:
        """更新模拟功能菜单项的文本"""
        if hasattr(self, 'simulate_functions_action'):
            checked = self.simulate_functions_action.isChecked()
            # checked=True表示启用，显示"禁用模拟功能"（点击后禁用）
            # checked=False表示禁用，显示"启用模拟功能"（点击后启用）
            if checked:
                self.simulate_functions_action.setText(_("禁用模拟功能"))
            else:
                self.simulate_functions_action.setText(_("启用模拟功能"))
    
    def toggle_simulate_functions(self, checked: bool) -> None:
        """
        切换模拟功能的启用/禁用状态。
        
        Args:
            checked: True表示启用，False表示禁用
        """
        # 更新菜单项文本
        self._update_simulate_functions_menu_text()
        
        # 更新所有ChartWindow的模拟功能状态
        chart_window: ChartWindow | None = self.widgets.get("chart_window", None)
        if chart_window:
            chart_window.set_simulate_functions_enabled(checked)
        
        # 记录日志
        status_text = _("已启用") if checked else _("已禁用")
        self.main_engine.write_log(
            f"[MainWindow] 模拟功能{status_text}：模拟成交、模拟止损、模拟止盈",
            "MainWindow"
        )

    def edit_global_setting(self) -> None:
        """
        """
        dialog: GlobalDialog = GlobalDialog()
        dialog.exec()
