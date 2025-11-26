"""
Basic widgets for UI.
"""

import csv
import platform
from enum import Enum
from typing import cast, Any
from copy import copy
from tzlocal import get_localzone_name
from datetime import datetime
from importlib import metadata

from .qt import QtCore, QtGui, QtWidgets, Qt
from ..constant import Direction, Exchange, Offset, OrderType
from ..engine import MainEngine, Event, EventEngine
from ..event import (
    EVENT_QUOTE,
    EVENT_TICK,
    EVENT_TRADE,
    EVENT_ORDER,
    EVENT_POSITION,
    EVENT_POSITION_VIEW,
    EVENT_ACCOUNT,
    EVENT_LOG
)
from ..object import (
    OrderRequest,
    SubscribeRequest,
    CancelRequest,
    ContractData,
    PositionData,
    OrderData,
    QuoteData,
    TickData
)
from ..utility import load_json, save_json, get_digits, ZoneInfo
from ..setting import SETTING_FILENAME, SETTINGS
from ..locale import _


COLOR_LONG = QtGui.QColor("red")
COLOR_SHORT = QtGui.QColor("green")
COLOR_BID = QtGui.QColor(255, 174, 201)
COLOR_ASK = QtGui.QColor(160, 255, 160)
COLOR_BLACK = QtGui.QColor("black")


class ToastNotification(QtWidgets.QLabel):
    """
    Toast提示组件 - 温和的浮动通知，自动淡入淡出消失。
    
    用于显示主力合约切换等重要但不紧急的通知。
    """
    
    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        
        # 设置样式
        self.setStyleSheet("""
            QLabel {
                background-color: rgba(50, 50, 50, 220);
                color: #ffffff;
                padding: 12px 20px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setWindowFlags(
            QtCore.Qt.WindowType.FramelessWindowHint | 
            QtCore.Qt.WindowType.WindowStaysOnTopHint |
            QtCore.Qt.WindowType.Tool
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        # 动画效果
        self.opacity_effect = QtWidgets.QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        
        # 淡入动画
        self.fade_in_animation = QtCore.QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_in_animation.setDuration(300)
        self.fade_in_animation.setStartValue(0.0)
        self.fade_in_animation.setEndValue(1.0)
        
        # 淡出动画
        self.fade_out_animation = QtCore.QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_out_animation.setDuration(500)
        self.fade_out_animation.setStartValue(1.0)
        self.fade_out_animation.setEndValue(0.0)
        self.fade_out_animation.finished.connect(self.hide)
        
        # 定时器（显示时长）
        self.timer = QtCore.QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.start_fade_out)
        
        self.hide()
    
    def show_message(self, message: str, duration: int = 4000, 
                     icon: str = "🔄", color: str = None,
                     position: str = "top") -> None:
        """
        显示Toast消息。
        
        Args:
            message: 消息内容
            duration: 显示时长（毫秒），默认4秒
            icon: 消息图标，默认为刷新图标
            color: 背景颜色，默认深灰色
            position: 显示位置，"top"=顶部中央，"center"=屏幕中央
        """
        # 设置消息内容
        self.setText(f"  {icon}  {message}  ")
        
        # 自定义颜色
        if color:
            self.setStyleSheet(f"""
                QLabel {{
                    background-color: {color};
                    color: #ffffff;
                    padding: 12px 20px;
                    border-radius: 8px;
                    font-size: 14px;
                    font-weight: bold;
                }}
            """)
        
        # 调整大小
        self.adjustSize()
        
        # 计算位置
        if self.parent():
            parent = self.parent()
            parent_rect = parent.geometry()
            
            # 水平居中
            x = parent_rect.x() + (parent_rect.width() - self.width()) // 2
            
            if position == "center":
                # 屏幕中央
                y = parent_rect.y() + (parent_rect.height() - self.height()) // 2
            else:
                # 顶部（紧贴标题栏下方，不遮挡内容）
                y = parent_rect.y() + 35  # 紧贴标题栏
            
            self.move(x, y)
        
        # 显示并开始动画
        self.show()
        self.raise_()
        self.fade_in_animation.start()
        
        # 设置定时器
        self.timer.start(duration)
    
    def start_fade_out(self) -> None:
        """开始淡出动画"""
        self.fade_out_animation.start()


class BaseCell(QtWidgets.QTableWidgetItem):
    """
    General cell used in tablewidgets.
    """

    def __init__(self, content: Any, data: Any) -> None:
        """"""
        super().__init__()

        self._text: str = ""
        self._data: Any = None

        self.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self.set_content(content, data)

    def set_content(self, content: Any, data: Any) -> None:
        """
        Set text content.
        """
        self._text = str(content)
        self._data = data

        self.setText(self._text)

    def get_data(self) -> Any:
        """
        Get data object.
        """
        return self._data

    def __lt__(self, other: "BaseCell") -> bool:        # type: ignore
        """
        Sort by text content.
        """
        result: bool = self._text < other._text
        return result


class EnumCell(BaseCell):
    """
    Cell used for showing enum data.
    """

    def __init__(self, content: Enum, data: Any) -> None:
        """"""
        super().__init__(content, data)

    def set_content(self, content: Any, data: Any) -> None:
        """
        Set text using enum.constant.value.
        """
        if content:
            super().set_content(content.value, data)


class DirectionCell(EnumCell):
    """
    Cell used for showing direction data.
    """

    def __init__(self, content: Enum, data: Any) -> None:
        """"""
        super().__init__(content, data)

    def set_content(self, content: Any, data: Any) -> None:
        """
        Cell color is set according to direction.
        """
        super().set_content(content, data)

        if content is Direction.SHORT:
            self.setForeground(COLOR_SHORT)
        else:
            self.setForeground(COLOR_LONG)


class BidCell(BaseCell):
    """
    Cell used for showing bid price and volume.
    """

    def __init__(self, content: Any, data: Any) -> None:
        """"""
        super().__init__(content, data)

        self.setForeground(COLOR_BID)


class AskCell(BaseCell):
    """
    Cell used for showing ask price and volume.
    """

    def __init__(self, content: Any, data: Any) -> None:
        """"""
        super().__init__(content, data)

        self.setForeground(COLOR_ASK)


class PnlCell(BaseCell):
    """
    Cell used for showing pnl data.
    """

    def __init__(self, content: Any, data: Any) -> None:
        """"""
        super().__init__(content, data)

    def set_content(self, content: Any, data: Any) -> None:
        """
        Cell color is set based on whether pnl is
        positive or negative.
        """
        super().set_content(content, data)

        if str(content).startswith("-"):
            self.setForeground(COLOR_SHORT)
        else:
            self.setForeground(COLOR_LONG)


class TimeCell(BaseCell):
    """
    Cell used for showing time string from datetime object.
    """

    local_tz = ZoneInfo(get_localzone_name())

    def __init__(self, content: Any, data: Any) -> None:
        """"""
        super().__init__(content, data)

    def set_content(self, content: datetime | None, data: Any) -> None:
        """"""
        if content is None:
            return

        content = content.astimezone(self.local_tz)
        timestamp: str = content.strftime("%H:%M:%S")

        millisecond: int = int(content.microsecond / 1000)
        if millisecond:
            timestamp = f"{timestamp}.{millisecond}"
        else:
            timestamp = f"{timestamp}.000"

        self.setText(timestamp)
        self._data = data


class DateCell(BaseCell):
    """
    Cell used for showing date string from datetime object.
    """

    def __init__(self, content: Any, data: Any) -> None:
        """"""
        super().__init__(content, data)

    def set_content(self, content: Any, data: Any) -> None:
        """"""
        if content is None:
            return

        self.setText(content.strftime("%Y-%m-%d"))
        self._data = data


class MsgCell(BaseCell):
    """
    Cell used for showing msg data.
    """

    def __init__(self, content: str, data: Any) -> None:
        """"""
        super().__init__(content, data)
        self.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)


class BaseMonitor(QtWidgets.QTableWidget):
    """
    Monitor data update.
    """

    event_type: str = ""
    data_key: str = ""
    sorting: bool = False
    headers: dict = {}

    signal: QtCore.Signal = QtCore.Signal(Event)

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        """"""
        super().__init__()

        self.main_engine: MainEngine = main_engine
        self.event_engine: EventEngine = event_engine
        self.cells: dict[str, dict] = {}

        self.init_ui()
        self.load_setting()
        self.register_event()

    def init_ui(self) -> None:
        """"""
        self.init_table()
        self.init_menu()

    def init_table(self) -> None:
        """
        Initialize table.
        """
        self.setColumnCount(len(self.headers))

        labels: list = [d["display"] for d in self.headers.values()]
        self.setHorizontalHeaderLabels(labels)

        self.verticalHeader().setVisible(False)
        self.setEditTriggers(self.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(self.sorting)

    def init_menu(self) -> None:
        """
        Create right click menu.
        """
        self.menu: QtWidgets.QMenu = QtWidgets.QMenu(self)

        resize_action: QtGui.QAction = QtGui.QAction(_("调整列宽"), self)
        resize_action.triggered.connect(self.resize_columns)
        self.menu.addAction(resize_action)

        save_action: QtGui.QAction = QtGui.QAction(_("保存数据"), self)
        save_action.triggered.connect(self.save_csv)
        self.menu.addAction(save_action)

    def register_event(self) -> None:
        """
        Register event handler into event engine.
        """
        if self.event_type:
            self.signal.connect(self.process_event)
            self.event_engine.register(self.event_type, self.signal.emit)

    def process_event(self, event: Event) -> None:
        """
        Process new data from event and update into table.
        """
        # Disable sorting to prevent unwanted error.
        if self.sorting:
            self.setSortingEnabled(False)

        # Update data into table.
        data = event.data

        if not self.data_key:
            self.insert_new_row(data)
        else:
            key: str = data.__getattribute__(self.data_key)

            if key in self.cells:
                self.update_old_row(data)
            else:
                self.insert_new_row(data)

        # Enable sorting
        if self.sorting:
            self.setSortingEnabled(True)

    def insert_new_row(self, data: Any) -> None:
        """
        Insert a new row at the top of table.
        """
        self.insertRow(0)

        row_cells: dict = {}
        for column, header in enumerate(self.headers.keys()):
            setting: dict = self.headers[header]

            content = data.__getattribute__(header)
            cell: QtWidgets.QTableWidgetItem = setting["cell"](content, data)
            self.setItem(0, column, cell)

            if setting["update"]:
                row_cells[header] = cell

        if self.data_key:
            key: str = data.__getattribute__(self.data_key)
            self.cells[key] = row_cells

    def update_old_row(self, data: Any) -> None:
        """
        Update an old row in table.
        """
        key: str = data.__getattribute__(self.data_key)
        row_cells = self.cells[key]

        for header, cell in row_cells.items():
            content = data.__getattribute__(header)
            cell.set_content(content, data)

    def resize_columns(self) -> None:
        """
        Resize all columns according to contents.
        """
        self.horizontalHeader().resizeSections(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)

    def save_csv(self) -> None:
        """
        Save table data into a csv file
        """
        path, __ = QtWidgets.QFileDialog.getSaveFileName(
            self, _("保存数据"), "", "CSV(*.csv)")

        if not path:
            return

        with open(path, "w") as f:
            writer = csv.writer(f, lineterminator="\n")

            headers: list = [d["display"] for d in self.headers.values()]
            writer.writerow(headers)

            for row in range(self.rowCount()):
                if self.isRowHidden(row):
                    continue

                row_data: list = []
                for column in range(self.columnCount()):
                    item: QtWidgets.QTableWidgetItem | None = self.item(row, column)
                    if item:
                        row_data.append(str(item.text()))
                    else:
                        row_data.append("")
                writer.writerow(row_data)

    def contextMenuEvent(self, event: QtGui.QContextMenuEvent) -> None:
        """
        Show menu with right click.
        """
        self.menu.popup(QtGui.QCursor.pos())

    def save_setting(self) -> None:
        """"""
        settings: QtCore.QSettings = QtCore.QSettings(self.__class__.__name__, "custom")
        settings.setValue("column_state", self.horizontalHeader().saveState())

    def load_setting(self) -> None:
        """"""
        settings: QtCore.QSettings = QtCore.QSettings(self.__class__.__name__, "custom")
        column_state = settings.value("column_state")

        if isinstance(column_state, QtCore.QByteArray):
            self.horizontalHeader().restoreState(column_state)
            self.horizontalHeader().setSortIndicator(-1, QtCore.Qt.SortOrder.AscendingOrder)


class TickMonitor(BaseMonitor):
    """
    Monitor for tick data.
    """

    event_type: str = EVENT_TICK
    data_key: str = "vt_symbol"
    sorting: bool = True

    headers: dict = {
        "symbol": {"display": _("代码"), "cell": BaseCell, "update": False},
        "exchange": {"display": _("交易所"), "cell": EnumCell, "update": False},
        "name": {"display": _("名称"), "cell": BaseCell, "update": True},
        "last_price": {"display": _("最新价"), "cell": BaseCell, "update": True},
        "volume": {"display": _("成交量"), "cell": BaseCell, "update": True},
        "open_price": {"display": _("开盘价"), "cell": BaseCell, "update": True},
        "high_price": {"display": _("最高价"), "cell": BaseCell, "update": True},
        "low_price": {"display": _("最低价"), "cell": BaseCell, "update": True},
        "bid_price_1": {"display": _("买1价"), "cell": BidCell, "update": True},
        "bid_volume_1": {"display": _("买1量"), "cell": BidCell, "update": True},
        "ask_price_1": {"display": _("卖1价"), "cell": AskCell, "update": True},
        "ask_volume_1": {"display": _("卖1量"), "cell": AskCell, "update": True},
        "datetime": {"display": _("时间"), "cell": TimeCell, "update": True},
        "gateway_name": {"display": _("接口"), "cell": BaseCell, "update": False},
    }


class LogMonitor(BaseMonitor):
    """
    Monitor for log data.
    """

    event_type: str = EVENT_LOG
    data_key: str = ""
    sorting: bool = False

    headers: dict = {
        "time": {"display": _("时间"), "cell": TimeCell, "update": False},
        "msg": {"display": _("信息"), "cell": MsgCell, "update": False},
        "gateway_name": {"display": _("接口"), "cell": BaseCell, "update": False},
    }


class TradeMonitor(BaseMonitor):
    """
    Monitor for trade data.
    """

    event_type: str = EVENT_TRADE
    data_key: str = ""
    sorting: bool = True

    headers: dict = {
        "tradeid": {"display": _("成交号"), "cell": BaseCell, "update": False},
        "orderid": {"display": _("委托号"), "cell": BaseCell, "update": False},
        "symbol": {"display": _("代码"), "cell": BaseCell, "update": False},
        "exchange": {"display": _("交易所"), "cell": EnumCell, "update": False},
        "direction": {"display": _("方向"), "cell": DirectionCell, "update": False},
        "offset": {"display": _("开平"), "cell": EnumCell, "update": False},
        "price": {"display": _("价格"), "cell": BaseCell, "update": False},
        "volume": {"display": _("数量"), "cell": BaseCell, "update": False},
        "datetime": {"display": _("时间"), "cell": TimeCell, "update": False},
        "gateway_name": {"display": _("接口"), "cell": BaseCell, "update": False},
    }


class OrderMonitor(BaseMonitor):
    """
    Monitor for order data.
    """

    event_type: str = EVENT_ORDER
    data_key: str = "vt_orderid"
    sorting: bool = True

    headers: dict = {
        "orderid": {"display": _("委托号"), "cell": BaseCell, "update": False},
        "reference": {"display": _("来源"), "cell": BaseCell, "update": False},
        "symbol": {"display": _("代码"), "cell": BaseCell, "update": False},
        "exchange": {"display": _("交易所"), "cell": EnumCell, "update": False},
        "type": {"display": _("类型"), "cell": EnumCell, "update": False},
        "direction": {"display": _("方向"), "cell": DirectionCell, "update": False},
        "offset": {"display": _("开平"), "cell": EnumCell, "update": False},
        "price": {"display": _("价格"), "cell": BaseCell, "update": False},
        "volume": {"display": _("总数量"), "cell": BaseCell, "update": True},
        "traded": {"display": _("已成交"), "cell": BaseCell, "update": True},
        "status": {"display": _("状态"), "cell": EnumCell, "update": True},
        "datetime": {"display": _("时间"), "cell": TimeCell, "update": True},
        "gateway_name": {"display": _("接口"), "cell": BaseCell, "update": False},
    }

    def init_ui(self) -> None:
        """
        Connect signal.
        """
        super().init_ui()

        self.setToolTip(_("双击单元格撤单"))
        self.itemDoubleClicked.connect(self.cancel_order)

    def cancel_order(self, cell: BaseCell) -> None:
        """
        Cancel order if cell double clicked.
        """
        order: OrderData = cell.get_data()
        req: CancelRequest = order.create_cancel_request()
        self.main_engine.cancel_order(req, order.gateway_name)


class PositionMonitor(BaseMonitor):
    """
    Monitor for position data.
    """

    event_type: str = EVENT_POSITION
    data_key: str = "vt_positionid"
    sorting: bool = True

    headers: dict = {
        "symbol": {"display": _("代码"), "cell": BaseCell, "update": False},
        "exchange": {"display": _("交易所"), "cell": EnumCell, "update": False},
        "direction": {"display": _("方向"), "cell": DirectionCell, "update": False},
        "volume": {"display": _("数量"), "cell": BaseCell, "update": True},
        "yd_volume": {"display": _("昨仓"), "cell": BaseCell, "update": True},
        "frozen": {"display": _("冻结"), "cell": BaseCell, "update": True},
        "price": {"display": _("均价"), "cell": BaseCell, "update": True},
        "pnl": {"display": _("盈亏"), "cell": PnlCell, "update": True},
        "gateway_name": {"display": _("接口"), "cell": BaseCell, "update": False},
    }

    def register_event(self) -> None:
        """
        Register position events (view + legacy) to monitor.
        """
        self.signal.connect(self.process_event)
        self.event_engine.register(EVENT_POSITION, self.signal.emit)

        if SETTINGS.get("position.view.enabled", False):
            self.event_engine.register(EVENT_POSITION_VIEW, self.signal.emit)

    def process_event(self, event: Event) -> None:
        """
        Process position event and remove row if volume is zero.
        """
        position: PositionData = event.data
        key: str = position.vt_positionid
        
        # If volume is zero, remove the row and don't process further
        if position.volume <= 0:
            if key in self.cells:
                row_cells = self.cells[key]
                # Get the row number from any cell
                if row_cells:
                    first_cell = next(iter(row_cells.values()))
                    row: int = self.row(first_cell)
                    if row >= 0:
                        self.removeRow(row)
                    del self.cells[key]
            else:
                # Key not in cells, but volume is 0 - try to find and remove by searching all rows
                for row in range(self.rowCount()):
                    item = self.item(row, 0)  # Get first column item
                    if item and isinstance(item, BaseCell):
                        cell_data = item.get_data()
                        if cell_data and hasattr(cell_data, 'vt_positionid') and cell_data.vt_positionid == key:
                            self.removeRow(row)
                            # Also remove from cells if it exists
                            if key in self.cells:
                                del self.cells[key]
                            break
            # Don't call parent's process_event to avoid inserting/updating zero-volume positions
            return
        
        # Otherwise, use parent's process_event
        super().process_event(event)


class AccountMonitor(BaseMonitor):
    """
    Monitor for account data.
    """

    event_type: str = EVENT_ACCOUNT
    data_key: str = "vt_accountid"
    sorting: bool = True

    headers: dict = {
        "accountid": {"display": _("账号"), "cell": BaseCell, "update": False},
        "balance": {"display": _("余额"), "cell": BaseCell, "update": True},
        "frozen": {"display": _("冻结"), "cell": BaseCell, "update": True},
        "available": {"display": _("可用"), "cell": BaseCell, "update": True},
        "gateway_name": {"display": _("接口"), "cell": BaseCell, "update": False},
    }


class QuoteMonitor(BaseMonitor):
    """
    Monitor for quote data.
    """

    event_type: str = EVENT_QUOTE
    data_key: str = "vt_quoteid"
    sorting: bool = True

    headers: dict = {
        "quoteid": {"display": _("报价号"), "cell": BaseCell, "update": False},
        "reference": {"display": _("来源"), "cell": BaseCell, "update": False},
        "symbol": {"display": _("代码"), "cell": BaseCell, "update": False},
        "exchange": {"display": _("交易所"), "cell": EnumCell, "update": False},
        "bid_offset": {"display": _("买开平"), "cell": EnumCell, "update": False},
        "bid_volume": {"display": _("买量"), "cell": BidCell, "update": False},
        "bid_price": {"display": _("买价"), "cell": BidCell, "update": False},
        "ask_price": {"display": _("卖价"), "cell": AskCell, "update": False},
        "ask_volume": {"display": _("卖量"), "cell": AskCell, "update": False},
        "ask_offset": {"display": _("卖开平"), "cell": EnumCell, "update": False},
        "status": {"display": _("状态"), "cell": EnumCell, "update": True},
        "datetime": {"display": _("时间"), "cell": TimeCell, "update": True},
        "gateway_name": {"display": _("接口"), "cell": BaseCell, "update": False},
    }

    def init_ui(self) -> None:
        """
        Connect signal.
        """
        super().init_ui()

        self.setToolTip(_("双击单元格撤销报价"))
        self.itemDoubleClicked.connect(self.cancel_quote)

    def cancel_quote(self, cell: BaseCell) -> None:
        """
        Cancel quote if cell double clicked.
        """
        quote: QuoteData = cell.get_data()
        req: CancelRequest = quote.create_cancel_request()
        self.main_engine.cancel_quote(req, quote.gateway_name)


class ConnectDialog(QtWidgets.QDialog):
    """
    Start connection of a certain gateway.
    """

    def __init__(self, main_engine: MainEngine, gateway_name: str) -> None:
        """"""
        super().__init__()

        self.main_engine: MainEngine = main_engine
        self.gateway_name: str = gateway_name
        self.filename: str = f"connect_{gateway_name.lower()}.json"

        self.widgets: dict[str, tuple[QtWidgets.QWidget, type]] = {}

        self.init_ui()

    def init_ui(self) -> None:
        """"""
        self.setWindowTitle(_("连接{}").format(self.gateway_name))

        # Default setting provides field name, field data type and field default value.
        default_setting: dict | None = self.main_engine.get_default_setting(self.gateway_name)

        # Saved setting provides field data used last time.
        loaded_setting: dict = load_json(self.filename)

        # Initialize line edits and form layout based on setting.
        form: QtWidgets.QFormLayout = QtWidgets.QFormLayout()

        if default_setting:
            for field_name, field_value in default_setting.items():
                field_type: type = type(field_value)

                if field_type is list:
                    combo: QtWidgets.QComboBox = QtWidgets.QComboBox()
                    combo.addItems(field_value)

                    if field_name in loaded_setting:
                        saved_value = loaded_setting[field_name]
                        ix: int = combo.findText(saved_value)
                        combo.setCurrentIndex(ix)

                    form.addRow(f"{field_name} <{field_type.__name__}>", combo)
                    self.widgets[field_name] = (combo, field_type)
                else:
                    line: QtWidgets.QLineEdit = QtWidgets.QLineEdit(str(field_value))

                    if field_name in loaded_setting:
                        saved_value = loaded_setting[field_name]
                        line.setText(str(saved_value))

                    if _("密码") in field_name:
                        line.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)

                    if field_type is int:
                        validator: QtGui.QIntValidator = QtGui.QIntValidator()
                        line.setValidator(validator)

                    form.addRow(f"{field_name} <{field_type.__name__}>", line)
                    self.widgets[field_name] = (line, field_type)

        button: QtWidgets.QPushButton = QtWidgets.QPushButton(_("连接"))
        button.clicked.connect(self.connect_gateway)
        form.addRow(button)

        self.setLayout(form)

    def connect_gateway(self) -> None:
        """
        Get setting value from line edits and connect the gateway.
        """
        setting: dict = {}

        for field_name, tp in self.widgets.items():
            widget, field_type = tp
            if field_type is list:
                combo: QtWidgets.QComboBox = cast(QtWidgets.QComboBox, widget)
                field_value = str(combo.currentText())
            else:
                line: QtWidgets.QLineEdit = cast(QtWidgets.QLineEdit, widget)
                try:
                    field_value = field_type(line.text())
                except ValueError:
                    field_value = field_type()
            setting[field_name] = field_value

        save_json(self.filename, setting)

        self.main_engine.connect(setting, self.gateway_name)
        self.accept()


class TradingWidget(QtWidgets.QWidget):
    """
    General manual trading widget.
    """

    signal_tick: QtCore.Signal = QtCore.Signal(Event)

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        """"""
        super().__init__()

        self.main_engine: MainEngine = main_engine
        self.event_engine: EventEngine = event_engine

        self.vt_symbol: str = ""
        self.price_digits: int = 0

        self.init_ui()
        self.register_event()

    def init_ui(self) -> None:
        """"""
        self.setFixedWidth(300)

        # Trading function area
        exchanges: list[Exchange] = self.main_engine.get_all_exchanges()
        self.exchange_combo: QtWidgets.QComboBox = QtWidgets.QComboBox()
        self.exchange_combo.addItems([exchange.value for exchange in exchanges])

        self.symbol_line: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        self.symbol_line.returnPressed.connect(self.set_vt_symbol)

        self.name_line: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        self.name_line.setReadOnly(True)

        self.direction_combo: QtWidgets.QComboBox = QtWidgets.QComboBox()
        self.direction_combo.addItems(
            [Direction.LONG.value, Direction.SHORT.value])

        self.offset_combo: QtWidgets.QComboBox = QtWidgets.QComboBox()
        self.offset_combo.addItems([offset.value for offset in Offset])

        self.order_type_combo: QtWidgets.QComboBox = QtWidgets.QComboBox()
        self.order_type_combo.addItems(
            [order_type.value for order_type in OrderType])

        double_validator: QtGui.QDoubleValidator = QtGui.QDoubleValidator()
        double_validator.setBottom(0)

        self.price_line: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        self.price_line.setValidator(double_validator)

        self.volume_line: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        self.volume_line.setValidator(double_validator)

        self.gateway_combo: QtWidgets.QComboBox = QtWidgets.QComboBox()
        self.gateway_combo.addItems(self.main_engine.get_all_gateway_names())

        self.price_check: QtWidgets.QCheckBox = QtWidgets.QCheckBox()
        self.price_check.setToolTip(_("设置价格随行情更新"))

        # 移除OPPONENT复选框，改为订单类型

        # 添加追价功能配置
        self.chase_check: QtWidgets.QCheckBox = QtWidgets.QCheckBox()
        self.chase_check.setToolTip(_("启用智能追价功能，自动处理滑点"))
        self.chase_check.setText(_("智能追价"))
        self.chase_check.setChecked(True)  # 默认启用

        # 追价配置选项组
        # 移除追价次数控件（与重试次数重复，只保留重试次数）
        # 移除最大滑点控件（使用买一/卖一价格时滑点限制无意义）

        # 超时重试配置
        self.max_retry_times_spin: QtWidgets.QSpinBox = QtWidgets.QSpinBox()
        self.max_retry_times_spin.setRange(1, 10)
        self.max_retry_times_spin.setValue(2)
        self.max_retry_times_spin.setSuffix(_("次"))
        self.max_retry_times_spin.setToolTip(_("超时后最大重委托次数"))

        # 移除追价步长控件（不再需要，直接使用买一/卖一价格）

        # 移除OPPONENT事件连接，现在通过订单类型下拉框处理

        # 追价功能状态变化处理
        self.chase_check.stateChanged.connect(self.on_chase_enabled_changed)

        # 当订单类型改变时，更新价格显示
        self.order_type_combo.currentTextChanged.connect(self.on_order_type_changed)

        # 当交易方向改变时，更新市价单价格显示
        self.direction_combo.currentTextChanged.connect(self.on_direction_changed)

        send_button: QtWidgets.QPushButton = QtWidgets.QPushButton(_("委托"))
        send_button.clicked.connect(self.send_order)

        cancel_button: QtWidgets.QPushButton = QtWidgets.QPushButton(_("全撤"))
        cancel_button.clicked.connect(self.cancel_all)

        grid: QtWidgets.QGridLayout = QtWidgets.QGridLayout()
        grid.addWidget(QtWidgets.QLabel(_("交易所")), 0, 0)
        grid.addWidget(QtWidgets.QLabel(_("代码")), 1, 0)
        grid.addWidget(QtWidgets.QLabel(_("名称")), 2, 0)
        grid.addWidget(QtWidgets.QLabel(_("方向")), 3, 0)
        grid.addWidget(QtWidgets.QLabel(_("开平")), 4, 0)
        grid.addWidget(QtWidgets.QLabel(_("类型")), 5, 0)
        grid.addWidget(QtWidgets.QLabel(_("价格")), 6, 0)
        grid.addWidget(QtWidgets.QLabel(_("数量")), 7, 0)
        grid.addWidget(self.exchange_combo, 0, 1, 1, 2)
        grid.addWidget(self.symbol_line, 1, 1, 1, 2)
        grid.addWidget(self.name_line, 2, 1, 1, 2)
        grid.addWidget(self.direction_combo, 3, 1, 1, 2)
        grid.addWidget(self.offset_combo, 4, 1, 1, 2)
        grid.addWidget(self.order_type_combo, 5, 1, 1, 2)
        grid.addWidget(self.price_line, 6, 1, 1, 1)
        grid.addWidget(self.price_check, 6, 2, 1, 1)
        grid.addWidget(self.volume_line, 7, 1, 1, 2)

        # 追价配置区域
        grid.addWidget(QtWidgets.QLabel(_("追价设置")), 8, 0)
        grid.addWidget(self.chase_check, 8, 1, 1, 2)
        grid.addWidget(QtWidgets.QLabel(_("重试次数")), 9, 0)
        grid.addWidget(self.max_retry_times_spin, 9, 1, 1, 2)

        grid.addWidget(QtWidgets.QLabel(_("接口")), 10, 0)
        grid.addWidget(self.gateway_combo, 10, 1, 1, 2)
        grid.addWidget(send_button, 11, 0, 1, 3)
        grid.addWidget(cancel_button, 12, 0, 1, 3)

        # Market depth display area
        bid_color: str = "rgb(255,174,201)"
        ask_color: str = "rgb(160,255,160)"

        self.bp1_label: QtWidgets.QLabel = self.create_label(bid_color)
        self.bp2_label: QtWidgets.QLabel = self.create_label(bid_color)
        self.bp3_label: QtWidgets.QLabel = self.create_label(bid_color)
        self.bp4_label: QtWidgets.QLabel = self.create_label(bid_color)
        self.bp5_label: QtWidgets.QLabel = self.create_label(bid_color)

        self.bv1_label: QtWidgets.QLabel = self.create_label(
            bid_color, alignment=QtCore.Qt.AlignmentFlag.AlignRight)
        self.bv2_label: QtWidgets.QLabel = self.create_label(
            bid_color, alignment=QtCore.Qt.AlignmentFlag.AlignRight)
        self.bv3_label: QtWidgets.QLabel = self.create_label(
            bid_color, alignment=QtCore.Qt.AlignmentFlag.AlignRight)
        self.bv4_label: QtWidgets.QLabel = self.create_label(
            bid_color, alignment=QtCore.Qt.AlignmentFlag.AlignRight)
        self.bv5_label: QtWidgets.QLabel = self.create_label(
            bid_color, alignment=QtCore.Qt.AlignmentFlag.AlignRight)

        self.ap1_label: QtWidgets.QLabel = self.create_label(ask_color)
        self.ap2_label: QtWidgets.QLabel = self.create_label(ask_color)
        self.ap3_label: QtWidgets.QLabel = self.create_label(ask_color)
        self.ap4_label: QtWidgets.QLabel = self.create_label(ask_color)
        self.ap5_label: QtWidgets.QLabel = self.create_label(ask_color)

        self.av1_label: QtWidgets.QLabel = self.create_label(
            ask_color, alignment=QtCore.Qt.AlignmentFlag.AlignRight)
        self.av2_label: QtWidgets.QLabel = self.create_label(
            ask_color, alignment=QtCore.Qt.AlignmentFlag.AlignRight)
        self.av3_label: QtWidgets.QLabel = self.create_label(
            ask_color, alignment=QtCore.Qt.AlignmentFlag.AlignRight)
        self.av4_label: QtWidgets.QLabel = self.create_label(
            ask_color, alignment=QtCore.Qt.AlignmentFlag.AlignRight)
        self.av5_label: QtWidgets.QLabel = self.create_label(
            ask_color, alignment=QtCore.Qt.AlignmentFlag.AlignRight)

        self.lp_label: QtWidgets.QLabel = self.create_label()
        self.return_label: QtWidgets.QLabel = self.create_label(alignment=QtCore.Qt.AlignmentFlag.AlignRight)

        # 移除追价状态显示，改为仅在日志中记录

        form: QtWidgets.QFormLayout = QtWidgets.QFormLayout()
        form.addRow(self.ap5_label, self.av5_label)
        form.addRow(self.ap4_label, self.av4_label)
        form.addRow(self.ap3_label, self.av3_label)
        form.addRow(self.ap2_label, self.av2_label)
        form.addRow(self.ap1_label, self.av1_label)
        form.addRow(self.lp_label, self.return_label)
        form.addRow(self.bp1_label, self.bv1_label)
        form.addRow(self.bp2_label, self.bv2_label)
        form.addRow(self.bp3_label, self.bv3_label)
        form.addRow(self.bp5_label, self.bv5_label)

        # Overall layout
        vbox: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout()
        vbox.addLayout(grid)
        vbox.addLayout(form)
        self.setLayout(vbox)

    def create_label(
        self,
        color: str = "",
        alignment: int = QtCore.Qt.AlignmentFlag.AlignLeft
    ) -> QtWidgets.QLabel:
        """
        Create label with certain font color.
        """
        label: QtWidgets.QLabel = QtWidgets.QLabel()
        if color:
            label.setStyleSheet(f"color:{color}")
        label.setAlignment(Qt.AlignmentFlag(alignment))
        return label

    def register_event(self) -> None:
        """"""
        self.signal_tick.connect(self.process_tick_event)
        self.event_engine.register(EVENT_TICK, self.signal_tick.emit)

    def process_tick_event(self, event: Event) -> None:
        """"""
        tick: TickData = event.data
        if tick.vt_symbol != self.vt_symbol:
            return

        price_digits: int = self.price_digits

        self.lp_label.setText(f"{tick.last_price:.{price_digits}f}")
        self.bp1_label.setText(f"{tick.bid_price_1:.{price_digits}f}")
        self.bv1_label.setText(str(tick.bid_volume_1))
        self.ap1_label.setText(f"{tick.ask_price_1:.{price_digits}f}")
        self.av1_label.setText(str(tick.ask_volume_1))

        if tick.pre_close:
            r: float = (tick.last_price / tick.pre_close - 1) * 100
            self.return_label.setText(f"{r:.2f}%")

        if tick.bid_price_2:
            self.bp2_label.setText(f"{tick.bid_price_2:.{price_digits}f}")
            self.bv2_label.setText(str(tick.bid_volume_2))
            self.ap2_label.setText(f"{tick.ask_price_2:.{price_digits}f}")
            self.av2_label.setText(str(tick.ask_volume_2))

            self.bp3_label.setText(f"{tick.bid_price_3:.{price_digits}f}")
            self.bv3_label.setText(str(tick.bid_volume_3))
            self.ap3_label.setText(f"{tick.ask_price_3:.{price_digits}f}")
            self.av3_label.setText(str(tick.ask_volume_3))

            self.bp4_label.setText(f"{tick.bid_price_4:.{price_digits}f}")
            self.bv4_label.setText(str(tick.bid_volume_4))
            self.ap4_label.setText(f"{tick.ask_price_4:.{price_digits}f}")
            self.av4_label.setText(str(tick.ask_volume_4))

            self.bp5_label.setText(f"{tick.bid_price_5:.{price_digits}f}")
            self.bv5_label.setText(str(tick.bid_volume_5))
            self.ap5_label.setText(f"{tick.ask_price_5:.{price_digits}f}")
            self.av5_label.setText(str(tick.ask_volume_5))

        if self.price_check.isChecked():
            self.price_line.setText(f"{tick.last_price:.{price_digits}f}")

        # 实时更新对手价和超价的价格显示
        order_type_text = str(self.order_type_combo.currentText())
        current_price_text = str(self.price_line.text())

        if order_type_text == OrderType.OPPONENT.value:
            # 对手价：强制实时更新价格
            if current_price_text in ["等待行情数据...", "请先输入合约代码", "0.00", ""]:
                # 立即更新，因为现在有了行情数据
                self.calculate_and_display_opponent_price()
                self.price_line.setEnabled(False)
            else:
                # 正常的实时更新
                self.calculate_and_display_opponent_price()
        elif order_type_text == OrderType.OVER.value:
            # 超价：强制实时更新价格
            if current_price_text in ["等待行情数据...", "请先输入合约代码", "0.00", ""]:
                # 立即更新，因为现在有了行情数据
                self.calculate_and_display_over_price()
                self.price_line.setEnabled(False)
            else:
                # 正常的实时更新
                self.calculate_and_display_over_price()
        elif order_type_text == OrderType.MARKET.value:
            # 市价单（不推荐）：使用对手价逻辑
            self.calculate_and_display_opponent_price()

    def set_vt_symbol(self) -> None:
        """
        Set the tick depth data to monitor by vt_symbol.
        """
        symbol: str = str(self.symbol_line.text())
        if not symbol:
            return

        # Generate vt_symbol from symbol and exchange
        exchange_value: str = str(self.exchange_combo.currentText())
        vt_symbol: str = f"{symbol}.{exchange_value}"

        if vt_symbol == self.vt_symbol:
            return
        self.vt_symbol = vt_symbol

        # Update name line widget and clear all labels
        contract: ContractData | None = self.main_engine.get_contract(vt_symbol)
        if not contract:
            self.name_line.setText("")
            gateway_name: str = self.gateway_combo.currentText()
        else:
            self.name_line.setText(contract.name)
            gateway_name = contract.gateway_name

            # Update gateway combo box.
            ix: int = self.gateway_combo.findText(gateway_name)
            self.gateway_combo.setCurrentIndex(ix)

            # Update price digits
            self.price_digits = get_digits(contract.pricetick)

        self.clear_label_text()
        self.volume_line.setText("")
        self.price_line.setText("")

        # Subscribe tick data
        req: SubscribeRequest = SubscribeRequest(
            symbol=symbol, exchange=Exchange(exchange_value)
        )

        self.main_engine.subscribe(req, gateway_name)

        # 订阅后立即检查并更新价格显示（根据订单类型）
        # 给一个短暂延迟让订阅生效，然后自动计算价格
        from threading import Timer
        def delayed_price_update():
            order_type_text = str(self.order_type_combo.currentText())
            if order_type_text == OrderType.OPPONENT.value:
                # 对手价：自动计算并显示
                self.calculate_and_display_opponent_price()
                # 如果没有数据，延迟重试
                if self.price_line.text() == "等待行情数据...":
                    Timer(1.0, self.calculate_and_display_opponent_price).start()
            elif order_type_text == OrderType.OVER.value:
                # 超价：自动计算并显示
                self.calculate_and_display_over_price()
                # 如果没有数据，延迟重试
                if self.price_line.text() == "等待行情数据...":
                    Timer(1.0, self.calculate_and_display_over_price).start()
            elif order_type_text == OrderType.MARKET.value:
                # 市价单（不推荐）：使用对手价逻辑
                self.calculate_and_display_opponent_price()
                if self.price_line.text() == "等待行情数据...":
                    Timer(1.0, self.calculate_and_display_opponent_price).start()

        # 延迟100ms执行价格更新，确保订阅已生效
        Timer(0.1, delayed_price_update).start()

    def clear_label_text(self) -> None:
        """
        Clear text on all labels.
        """
        self.lp_label.setText("")
        self.return_label.setText("")

        self.bv1_label.setText("")
        self.bv2_label.setText("")
        self.bv3_label.setText("")
        self.bv4_label.setText("")
        self.bv5_label.setText("")

        self.av1_label.setText("")
        self.av2_label.setText("")
        self.av3_label.setText("")
        self.av4_label.setText("")
        self.av5_label.setText("")

        self.bp1_label.setText("")
        self.bp2_label.setText("")
        self.bp3_label.setText("")
        self.bp4_label.setText("")
        self.bp5_label.setText("")

        self.ap1_label.setText("")
        self.ap2_label.setText("")
        self.ap3_label.setText("")
        self.ap4_label.setText("")
        self.ap5_label.setText("")

    def on_chase_enabled_changed(self, state: int) -> None:
        """处理追价功能开关状态变化"""
        enabled = (state == 2)

        # 控制追价参数控件的可用性
        self.max_retry_times_spin.setEnabled(enabled)

        # 记录追价状态变化到日志
        if enabled:
            config = self.get_chase_config()
            self.main_engine.write_log(
                f"[追价] 已启用 - 重试{config['max_retry_times']}次"
            )
        else:
            self.main_engine.write_log("[追价] 已禁用")

    def get_chase_config(self) -> dict:
        """获取当前追价配置"""
        return {
            "enabled": self.chase_check.isChecked(),
            "max_chase_times": 10,  # 使用较大的默认值（不再在UI中显示，避免与重试次数重复）
            "chase_interval": 0.5,  # 固定追价间隔
            "timeout_seconds": 3.0,  # 超时阈值（秒）
            "enable_timeout_cancel": True,  # 是否启用超时撤单
            "max_retry_times": self.max_retry_times_spin.value(),  # 最大重委托次数
        }

    def on_direction_changed(self) -> None:
        """处理交易方向改变"""
        order_type_text = str(self.order_type_combo.currentText())
        if order_type_text == OrderType.OPPONENT.value:
            # 对手价：重新计算价格
            self.calculate_and_display_opponent_price()
        elif order_type_text == OrderType.OVER.value:
            # 超价：重新计算价格
            self.calculate_and_display_over_price()
        elif order_type_text == OrderType.MARKET.value:
            # 市价单（不推荐）：使用对手价逻辑
            self.calculate_and_display_opponent_price()

    def on_order_type_changed(self, order_type_text: str) -> None:
        """处理订单类型改变"""
        # 确保vt_symbol已设置
        if not self.vt_symbol:
            symbol: str = str(self.symbol_line.text())
            exchange_value: str = str(self.exchange_combo.currentText())
            if symbol and exchange_value:
                self.vt_symbol = f"{symbol}.{exchange_value}"

        if order_type_text == OrderType.OPPONENT.value:
            # 对手价：买用卖一，卖用买一
            self.calculate_and_display_opponent_price()
            self.price_line.setEnabled(False)  # 设为只读
        elif order_type_text == OrderType.OVER.value:
            # 超价：对手价基础上加价
            self.calculate_and_display_over_price()
            self.price_line.setEnabled(False)  # 设为只读
        elif order_type_text == OrderType.MARKET.value:
            # 市价单：暂时保留原逻辑，但不推荐使用
            self.calculate_and_display_opponent_price()  # 使用对手价逻辑
            self.price_line.setEnabled(False)
        elif order_type_text == OrderType.LIMIT.value:
            # 限价单：启用价格输入
            self.price_line.setEnabled(True)
            if self.price_line.text() == "0.00":  # 如果是系统设置的市价，清空让用户输入
                self.price_line.clear()

    def calculate_and_display_opponent_price(self) -> None:
        """计算并显示对手价（买用卖一，卖用买一）"""
        if not self.vt_symbol:
            self.price_line.setText("请先输入合约代码")
            self.price_line.setToolTip("请先输入合约代码和选择交易所")
            return

        # 获取当前合约的行情数据
        tick_data = self.main_engine.get_tick(self.vt_symbol)
        if not tick_data:
            self.price_line.setText("等待行情数据...")
            self.price_line.setToolTip(f"正在等待 {self.vt_symbol} 的行情数据，请确保已订阅该合约")
            self.main_engine.write_log(f"对手价: 等待 {self.vt_symbol} 行情数据，请确保已订阅该合约")
            return

        # 根据方向计算对手价
        direction_text = str(self.direction_combo.currentText())
        direction = Direction(direction_text)

        if direction == Direction.LONG:
            # 买单使用卖一价
            opponent_price = tick_data.ask_price_1 if tick_data.ask_price_1 > 0 else tick_data.last_price
        else:
            # 卖单使用买一价
            opponent_price = tick_data.bid_price_1 if tick_data.bid_price_1 > 0 else tick_data.last_price

        if opponent_price > 0:
            # 显示对手价
            self.price_line.setText(f"{opponent_price:.3f}")
            # 设置工具提示显示更新时间
            import datetime
            update_time = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
            price_source = "ask" if direction == Direction.LONG else "bid"
            self.price_line.setToolTip(f"对手价({price_source}) - 更新: {update_time}")
        else:
            self.price_line.setText("0.00")
            self.price_line.setToolTip("无有效对手价")

    def calculate_and_display_over_price(self) -> None:
        """计算并显示超价（对手价基础上加价，原OPPONENT逻辑，增强风险控制）"""
        if not self.vt_symbol:
            self.price_line.setText("请先输入合约代码")
            self.price_line.setToolTip("请先输入合约代码和选择交易所")
            return

        # 获取当前合约的行情数据
        tick_data = self.main_engine.get_tick(self.vt_symbol)
        if not tick_data:
            self.price_line.setText("等待行情数据...")
            self.price_line.setToolTip(f"正在等待 {self.vt_symbol} 的行情数据，请确保已订阅该合约")
            # 记录提示信息
            self.main_engine.write_log(f"超价: 等待 {self.vt_symbol} 行情数据，请确保已订阅该合约")
            return

        # 根据方向计算超价（对手价基础上加价）
        direction_text = str(self.direction_combo.currentText())
        direction = Direction(direction_text)

        # 🛡️ 增强风险控制：检查价差和流动性
        bid_ask_spread = abs(tick_data.ask_price_1 - tick_data.bid_price_1) if (tick_data.ask_price_1 > 0 and tick_data.bid_price_1 > 0) else 0
        mid_price = (tick_data.ask_price_1 + tick_data.bid_price_1) / 2 if (tick_data.ask_price_1 > 0 and tick_data.bid_price_1 > 0) else tick_data.last_price

        # 风险控制参数
        MAX_SPREAD_PCT = 1.0  # 最大买卖价差比例 1%
        MAX_OVER_PREMIUM = 0.2  # 最大超价溢价 0.2%
        MIN_VOLUME = 1  # 最小盘口数量要求

        # 检查市场流动性风险
        risk_warnings = []

        if mid_price > 0:
            spread_pct = (bid_ask_spread / mid_price) * 100
            if spread_pct > MAX_SPREAD_PCT:
                risk_warnings.append(f"价差过大({spread_pct:.2f}%)")

        if direction == Direction.LONG:
            # 买单检查卖盘流动性
            if tick_data.ask_volume_1 < MIN_VOLUME:
                risk_warnings.append(f"卖盘不足({tick_data.ask_volume_1})")
        else:
            # 卖单检查买盘流动性
            if tick_data.bid_volume_1 < MIN_VOLUME:
                risk_warnings.append(f"买盘不足({tick_data.bid_volume_1})")

        if direction == Direction.LONG:
            # 买单使用卖一价，超价加价
            base_price = tick_data.ask_price_1 if tick_data.ask_price_1 > 0 else tick_data.last_price
            over_price = base_price * (1 + MAX_OVER_PREMIUM / 100)  # 最大0.2%溢价
        else:
            # 卖单使用买一价，超价减价
            base_price = tick_data.bid_price_1 if tick_data.bid_price_1 > 0 else tick_data.last_price
            over_price = base_price * (1 - MAX_OVER_PREMIUM / 100)  # 最大0.2%折扣

        # 🛡️ 额外安全检查：确保价格合理性
        if mid_price > 0:
            price_deviation_pct = abs(over_price - mid_price) / mid_price * 100
            if price_deviation_pct > 0.5:  # 超过0.5%偏离中间价
                risk_warnings.append(f"价格偏离过大({price_deviation_pct:.2f}%)")
                # 修正到更安全的价格
                if direction == Direction.LONG:
                    over_price = mid_price * 1.002  # 中间价+0.2%
                else:
                    over_price = mid_price * 0.998  # 中间价-0.2%

        if over_price > 0:
            # 显示超价（带风险提示）
            price_display = f"{over_price:.3f}"
            if risk_warnings:
                price_display += "⚠️"

            self.price_line.setText(price_display)

            # 设置详细的工具提示（包含风险信息）
            import datetime
            update_time = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
            price_source = f"ask+{MAX_OVER_PREMIUM}%" if direction == Direction.LONG else f"bid-{MAX_OVER_PREMIUM}%"

            tooltip_text = f"超价({price_source}) 基准:{base_price:.3f} - 更新: {update_time}"
            if risk_warnings:
                tooltip_text += f"\n⚠️ 风险提示: {', '.join(risk_warnings)}"
                tooltip_text += "\n🛡️ 已应用保守定价保护"

            self.price_line.setToolTip(tooltip_text)

            # 记录风险警告到日志
            if risk_warnings:
                self.main_engine.write_log(f"🛡️ 超价风险控制: {', '.join(risk_warnings)} - 已调整为保守定价")
        else:
            self.price_line.setText("0.00")
            self.price_line.setToolTip("无有效超价")

    def calculate_and_display_market_price(self) -> None:
        """计算并显示市价单的实时对手价"""
        if not self.vt_symbol:
            self.price_line.setText("请先输入合约代码")
            self.price_line.setToolTip("请先输入合约代码和选择交易所")
            return

        # 获取当前合约的行情数据
        tick_data = self.main_engine.get_tick(self.vt_symbol)
        if not tick_data:
            self.price_line.setText("等待行情数据...")
            self.price_line.setToolTip(f"正在等待 {self.vt_symbol} 的行情数据，请确保已订阅该合约")
            # 记录提示信息
            self.main_engine.write_log(f"市价单: 等待 {self.vt_symbol} 行情数据，请确保已订阅该合约")
            return

        # 根据方向计算对手价
        direction_text = str(self.direction_combo.currentText())
        direction = Direction(direction_text)

        if direction == Direction.LONG:
            # 买单使用卖一价
            market_price = tick_data.ask_price_1 if tick_data.ask_price_1 > 0 else tick_data.last_price
        else:
            # 卖单使用买一价
            market_price = tick_data.bid_price_1 if tick_data.bid_price_1 > 0 else tick_data.last_price

        if market_price > 0:
            # 显示实时价格
            self.price_line.setText(f"{market_price:.2f}")
            # 设置工具提示显示更新时间
            import datetime
            update_time = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
            price_source = "ask" if direction == Direction.LONG else "bid"
            self.price_line.setToolTip(f"实时市价({price_source}) - 最后更新: {update_time}")
        else:
            self.price_line.setText("0.00")
            self.price_line.setToolTip("无有效市场价格")

    def extract_price_from_text(self, price_text: str) -> float:
        """从价格文本中提取纯数字价格（去除价格来源等说明信息）"""
        if not price_text:
            return 0.0

        # 过滤提示性文本
        if "请先输入" in price_text or "等待" in price_text:
            return 0.0

        try:
            # 如果包含括号，只取括号前的部分
            if "(" in price_text:
                price_text = price_text.split("(")[0].strip()

            # 转换为浮点数
            return float(price_text)
        except ValueError:
            return 0.0

    def send_order(self) -> None:
        """
        Send new order manually.
        """
        symbol: str = str(self.symbol_line.text())
        if not symbol:
            QtWidgets.QMessageBox.critical(self, _("委托失败"), _("请输入合约代码"))
            return

        volume_text: str = str(self.volume_line.text())
        if not volume_text:
            QtWidgets.QMessageBox.critical(self, _("委托失败"), _("请输入委托数量"))
            return
        volume: float = float(volume_text)

        price_text: str = str(self.price_line.text())
        order_type = OrderType(str(self.order_type_combo.currentText()))

        # 确保vt_symbol已设置
        if not self.vt_symbol:
            # 尝试从symbol和exchange生成vt_symbol
            exchange_value: str = str(self.exchange_combo.currentText())
            if symbol and exchange_value:
                self.vt_symbol = f"{symbol}.{exchange_value}"
            else:
                QtWidgets.QMessageBox.critical(self, _("委托失败"), _("无法获取合约信息"))
                return

        # 获取最新行情数据（用于市价单和OPPONENT订单）
        tick_data = self.main_engine.get_tick(self.vt_symbol)

        direction = Direction(str(self.direction_combo.currentText()))

        # 根据订单类型确定价格
        if order_type == OrderType.OVER.value:
            # 超价：必须使用最新计算的超价（带风险控制）
            if not tick_data:
                QtWidgets.QMessageBox.critical(self, _("委托失败"), _("无法获取实时行情，无法计算超价"))
                return

            # 🛡️ 应用与UI相同的风险控制逻辑
            bid_ask_spread = abs(tick_data.ask_price_1 - tick_data.bid_price_1) if (tick_data.ask_price_1 > 0 and tick_data.bid_price_1 > 0) else 0
            mid_price = (tick_data.ask_price_1 + tick_data.bid_price_1) / 2 if (tick_data.ask_price_1 > 0 and tick_data.bid_price_1 > 0) else tick_data.last_price

            # 风险控制参数（与UI保持一致）
            MAX_SPREAD_PCT = 1.0  # 最大买卖价差比例 1%
            MAX_OVER_PREMIUM = 0.2  # 最大超价溢价 0.2%

            # 检查流动性风险
            if mid_price > 0:
                spread_pct = (bid_ask_spread / mid_price) * 100
                if spread_pct > MAX_SPREAD_PCT:
                    # 价差过大，询问用户是否继续
                    reply = QtWidgets.QMessageBox.question(
                        self,
                        "风险提示",
                        f"当前买卖价差较大({spread_pct:.2f}%)，可能存在流动性风险。\n是否继续提交超价订单？",
                        QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
                    )
                    if reply == QtWidgets.QMessageBox.StandardButton.No:
                        return

            # 计算保守的超价
            if direction == Direction.LONG:
                base_price = tick_data.ask_price_1 if tick_data.ask_price_1 > 0 else tick_data.last_price
                price = base_price * (1 + MAX_OVER_PREMIUM / 100)  # 最大0.2%溢价
            else:
                base_price = tick_data.bid_price_1 if tick_data.bid_price_1 > 0 else tick_data.last_price
                price = base_price * (1 - MAX_OVER_PREMIUM / 100)  # 最大0.2%折扣

            # 🛡️ 最终安全检查：限制价格偏离
            if mid_price > 0:
                price_deviation_pct = abs(price - mid_price) / mid_price * 100
                if price_deviation_pct > 0.5:  # 超过0.5%偏离中间价
                    # 修正到更安全的价格
                    if direction == Direction.LONG:
                        price = mid_price * 1.002  # 中间价+0.2%
                    else:
                        price = mid_price * 0.998  # 中间价-0.2%

            if price <= 0:
                QtWidgets.QMessageBox.critical(self, _("委托失败"), _("超价计算失败"))
                return

            # 记录风险控制应用
            ui_price = self.extract_price_from_text(price_text)
            if ui_price > 0 and abs(price - ui_price) / ui_price > 0.001:
                self.main_engine.write_log(f"🛡️ 超价风控: UI显示{ui_price:.3f} -> 安全价格{price:.3f}")
            else:
                self.main_engine.write_log(f"🛡️ 超价已通过风控检查: {price:.3f}")

        elif order_type == OrderType.OPPONENT.value:
            # 对手价：买用卖一，卖用买一
            if not tick_data:
                QtWidgets.QMessageBox.critical(self, _("委托失败"), _("无法获取实时行情，无法计算对手价"))
                return

            # 计算对手价
            if direction == Direction.LONG:
                price = tick_data.ask_price_1 if tick_data.ask_price_1 > 0 else tick_data.last_price
            else:
                price = tick_data.bid_price_1 if tick_data.bid_price_1 > 0 else tick_data.last_price

            if price <= 0:
                QtWidgets.QMessageBox.critical(self, _("委托失败"), _("无法获取有效的对手价"))
                return

            # 记录价格对比
            ui_price = self.extract_price_from_text(price_text)
            if ui_price > 0 and abs(price - ui_price) / ui_price > 0.001:
                self.main_engine.write_log(f"对手价已更新: UI显示{ui_price:.3f} -> 最新计算{price:.3f}")
            else:
                self.main_engine.write_log(f"对手价确认: {price:.3f}")

        elif order_type == OrderType.MARKET.value:
            # 市价单：暂时保留但不推荐，使用对手价逻辑
            if not tick_data:
                QtWidgets.QMessageBox.critical(self, _("委托失败"), _("无法获取实时行情，无法执行市价单"))
                return

            # 使用对手价逻辑
            if direction == Direction.LONG:
                price = tick_data.ask_price_1 if tick_data.ask_price_1 > 0 else tick_data.last_price
            else:
                price = tick_data.bid_price_1 if tick_data.bid_price_1 > 0 else tick_data.last_price

            if price <= 0:
                QtWidgets.QMessageBox.critical(self, _("委托失败"), _("无法获取有效的市场价格"))
                return

            # 记录价格对比
            ui_price = self.extract_price_from_text(price_text)
            if ui_price > 0 and abs(price - ui_price) / ui_price > 0.001:
                self.main_engine.write_log(f"市价已更新: UI显示{ui_price:.2f} -> 最新计算{price:.2f}")

        else:
            # 限价单：使用用户输入的价格
            try:
                price = self.extract_price_from_text(price_text)
                if price <= 0:
                    QtWidgets.QMessageBox.critical(self, _("委托失败"), _("限价单请输入有效价格"))
                    return
            except ValueError:
                QtWidgets.QMessageBox.critical(self, _("委托失败"), _("请输入有效的价格"))
                return

        # 设置订单引用标识和追价配置
        if order_type == OrderType.OVER.value:
            reference = "OVER"
        elif order_type == OrderType.OPPONENT.value:
            reference = "OPPONENT"
        elif order_type == OrderType.MARKET.value:
            reference = "MarketPrice"
        else:
            reference = "ManualTrading"

        # 添加追价配置到reference中（如果启用追价）
        chase_config = self.get_chase_config()
        if chase_config["enabled"]:
            # 将追价配置编码到reference中（只保留重试次数，移除滑点限制）
            chase_suffix = f"_Retry{chase_config['max_retry_times']}"
            reference += chase_suffix

        req: OrderRequest = OrderRequest(
            symbol=symbol,
            exchange=Exchange(str(self.exchange_combo.currentText())),
            direction=Direction(str(self.direction_combo.currentText())),
            type=order_type,  # Use pre-calculated order_type
            volume=volume,
            price=price,
            offset=Offset(str(self.offset_combo.currentText())),
            reference=reference
        )

        # 记录订单信息到日志
        order_info = f"订单提交: {symbol} {req.direction.value} {volume}@{price:.3f}"
        if chase_config["enabled"]:
            chase_info = f"[追价: 重试{chase_config['max_retry_times']}次]"
            self.main_engine.write_log(f"{order_info} {chase_info}")
        else:
            self.main_engine.write_log(order_info)

        gateway_name: str = str(self.gateway_combo.currentText())

        self.main_engine.send_order(req, gateway_name)

    def cancel_all(self) -> None:
        """
        Cancel all active orders.
        """
        order_list: list[OrderData] = self.main_engine.get_all_active_orders()
        for order in order_list:
            req: CancelRequest = order.create_cancel_request()
            self.main_engine.cancel_order(req, order.gateway_name)
        
        # 清理所有gateway的追价订单（包括等待tick数据的订单，即使它们不在active_orders中）
        # 这对于Futu gateway特别重要，因为等待tick数据时订单状态是CANCELLED，不在active_orders中
        for gateway_name, gateway in self.main_engine.gateways.items():
            if hasattr(gateway, 'cancel_all_chase_orders'):
                try:
                    gateway.cancel_all_chase_orders()
                except Exception as e:
                    self.main_engine.write_log(f"清理{gateway_name}的追价订单时发生异常：{str(e)}")

    def update_with_cell(self, cell: BaseCell) -> None:
        """"""
        data = cell.get_data()

        self.symbol_line.setText(data.symbol)
        self.exchange_combo.setCurrentIndex(
            self.exchange_combo.findText(data.exchange.value)
        )

        self.set_vt_symbol()

        if isinstance(data, PositionData):
            if data.direction == Direction.SHORT:
                direction: Direction = Direction.LONG
            elif data.direction == Direction.LONG:
                direction = Direction.SHORT
            else:       # Net position mode
                if data.volume > 0:
                    direction = Direction.SHORT
                else:
                    direction = Direction.LONG

            self.direction_combo.setCurrentIndex(
                self.direction_combo.findText(direction.value)
            )
            self.offset_combo.setCurrentIndex(
                self.offset_combo.findText(Offset.CLOSE.value)
            )
            self.volume_line.setText(str(abs(data.volume)))


class ActiveOrderMonitor(OrderMonitor):
    """
    Monitor which shows active order only.
    """

    def process_event(self, event: Event) -> None:
        """
        Hides the row if order is not active.
        """
        super().process_event(event)

        order: OrderData = event.data
        row_cells: dict = self.cells[order.vt_orderid]
        row: int = self.row(row_cells["volume"])

        if order.is_active():
            self.showRow(row)
        else:
            self.hideRow(row)


class ContractManager(QtWidgets.QWidget):
    """
    Query contract data available to trade in system.
    """

    headers: dict[str, str] = {
        "vt_symbol": _("本地代码"),
        "symbol": _("代码"),
        "exchange": _("交易所"),
        "name": _("名称"),
        "product": _("合约分类"),
        "size": _("合约乘数"),
        "pricetick": _("价格跳动"),
        "min_volume": _("最小委托量"),
        "option_portfolio": _("期权产品"),
        "option_expiry": _("期权到期日"),
        "option_strike": _("期权行权价"),
        "option_type": _("期权类型"),
        "gateway_name": _("交易接口"),
    }

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        super().__init__()

        self.main_engine: MainEngine = main_engine
        self.event_engine: EventEngine = event_engine

        self.init_ui()

    def init_ui(self) -> None:
        """"""
        self.setWindowTitle(_("合约查询"))
        self.resize(1000, 600)

        self.filter_line: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        self.filter_line.setPlaceholderText(_("输入合约代码或者交易所，留空则查询所有合约"))

        self.button_show: QtWidgets.QPushButton = QtWidgets.QPushButton(_("查询"))
        self.button_show.clicked.connect(self.show_contracts)

        labels: list = []
        for name, display in self.headers.items():
            label: str = f"{display}\n{name}"
            labels.append(label)

        self.contract_table: QtWidgets.QTableWidget = QtWidgets.QTableWidget()
        self.contract_table.setColumnCount(len(self.headers))
        self.contract_table.setHorizontalHeaderLabels(labels)
        self.contract_table.verticalHeader().setVisible(False)
        self.contract_table.setEditTriggers(self.contract_table.EditTrigger.NoEditTriggers)
        self.contract_table.setAlternatingRowColors(True)

        hbox: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        hbox.addWidget(self.filter_line)
        hbox.addWidget(self.button_show)

        vbox: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout()
        vbox.addLayout(hbox)
        vbox.addWidget(self.contract_table)

        self.setLayout(vbox)

    def show_contracts(self) -> None:
        """
        Show contracts by symbol
        """
        flt: str = str(self.filter_line.text())

        all_contracts: list[ContractData] = self.main_engine.get_all_contracts()
        if flt:
            contracts: list[ContractData] = [
                contract for contract in all_contracts if flt in contract.vt_symbol
            ]
        else:
            contracts = all_contracts

        self.contract_table.clearContents()
        self.contract_table.setRowCount(len(contracts))

        for row, contract in enumerate(contracts):
            for column, name in enumerate(self.headers.keys()):
                value: Any = getattr(contract, name)

                if value in {None, 0}:
                    value = ""

                cell: BaseCell
                if isinstance(value, Enum):
                    cell = EnumCell(value, contract)
                elif isinstance(value, datetime):
                    cell = DateCell(value, contract)
                else:
                    cell = BaseCell(value, contract)
                self.contract_table.setItem(row, column, cell)

        self.contract_table.resizeColumnsToContents()


class AboutDialog(QtWidgets.QDialog):
    """
    Information about the trading platform.
    """

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        """"""
        super().__init__()

        self.main_engine: MainEngine = main_engine
        self.event_engine: EventEngine = event_engine

        self.init_ui()

    def init_ui(self) -> None:
        """"""
        self.setWindowTitle(_("关于VeighNa Trader"))

        from ... import __version__ as vnpy_version

        text: str = f"""
            By Traders, For Traders.

            Created by VeighNa Technology


            License：MIT
            Website：www.vnpy.com
            Github：www.github.com/vnpy/vnpy


            VeighNa - {vnpy_version}
            Python - {platform.python_version()}
            PySide6 - {metadata.version("pyside6")}
            NumPy - {metadata.version("numpy")}
            pandas - {metadata.version("pandas")}
            """

        label: QtWidgets.QLabel = QtWidgets.QLabel()
        label.setText(text)
        label.setMinimumWidth(500)

        vbox: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout()
        vbox.addWidget(label)
        self.setLayout(vbox)


class GlobalDialog(QtWidgets.QDialog):
    """
    Start connection of a certain gateway.
    """

    def __init__(self) -> None:
        """"""
        super().__init__()

        self.widgets: dict[str, tuple[QtWidgets.QLineEdit, type]] = {}

        self.init_ui()

    def init_ui(self) -> None:
        """"""
        self.setWindowTitle(_("全局配置"))
        self.setMinimumWidth(800)

        settings: dict = copy(SETTINGS)
        settings.update(load_json(SETTING_FILENAME))

        # Initialize line edits and form layout based on setting.
        form: QtWidgets.QFormLayout = QtWidgets.QFormLayout()

        for field_name, field_value in settings.items():
            field_type: type = type(field_value)
            widget: QtWidgets.QLineEdit = QtWidgets.QLineEdit(str(field_value))

            form.addRow(f"{field_name} <{field_type.__name__}>", widget)
            self.widgets[field_name] = (widget, field_type)

        button: QtWidgets.QPushButton = QtWidgets.QPushButton(_("确定"))
        button.clicked.connect(self.update_setting)
        form.addRow(button)

        scroll_widget: QtWidgets.QWidget = QtWidgets.QWidget()
        scroll_widget.setLayout(form)

        scroll_area: QtWidgets.QScrollArea = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(scroll_widget)

        vbox: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout()
        vbox.addWidget(scroll_area)
        self.setLayout(vbox)

    def update_setting(self) -> None:
        """
        Get setting value from line edits and update global setting file.
        """
        settings: dict = {}
        for field_name, tp in self.widgets.items():
            widget, field_type = tp
            value_text: str = widget.text()

            if field_type is bool:
                if value_text == "True":
                    field_value: bool = True
                else:
                    field_value = False
            else:
                field_value = field_type(value_text)

            settings[field_name] = field_value

        QtWidgets.QMessageBox.information(
            self,
            _("注意"),
            _("全局配置的修改需要重启后才会生效！"),
            QtWidgets.QMessageBox.StandardButton.Ok
        )

        save_json(SETTING_FILENAME, settings)
        self.accept()
