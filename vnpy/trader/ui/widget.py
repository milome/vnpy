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
from ..period_utils import (
    get_period_start,
    get_hkfe_hour_period_start,
    get_hkfe_4hour_period,
    is_hkfe_trading_time,
    PeriodOpenPriceHelper
)


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
        # ✅ 性能优化：Qt组件已返回str类型，移除不必要的str()转换
        symbol = self.symbol_line.text()
        if not symbol:
            QtWidgets.QMessageBox.critical(self, _("委托失败"), _("请输入合约代码"))
            return

        volume_text = self.volume_line.text()
        if not volume_text:
            QtWidgets.QMessageBox.critical(self, _("委托失败"), _("请输入委托数量"))
            return
        volume: float = float(volume_text)

        price_text = self.price_line.text()
        order_type = OrderType(self.order_type_combo.currentText())

        # 确保vt_symbol已设置
        if not self.vt_symbol:
            # 尝试从symbol和exchange生成vt_symbol
            exchange_value = self.exchange_combo.currentText()
            if symbol and exchange_value:
                self.vt_symbol = f"{symbol}.{exchange_value}"
            else:
                QtWidgets.QMessageBox.critical(self, _("委托失败"), _("无法获取合约信息"))
                return

        # 获取最新行情数据（用于市价单和OPPONENT订单）
        tick_data = self.main_engine.get_tick(self.vt_symbol)

        direction = Direction(self.direction_combo.currentText())

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
            exchange=Exchange(self.exchange_combo.currentText()),
            direction=Direction(self.direction_combo.currentText()),
            type=order_type,  # Use pre-calculated order_type
            volume=volume,
            price=price,
            offset=Offset(self.offset_combo.currentText()),
            reference=reference
        )

        # 记录订单信息到日志
        order_info = f"订单提交: {symbol} {req.direction.value} {volume}@{price:.3f}"
        if chase_config["enabled"]:
            chase_info = f"[追价: 重试{chase_config['max_retry_times']}次]"
            self.main_engine.write_log(f"{order_info} {chase_info}")
        else:
            self.main_engine.write_log(order_info)

        gateway_name = self.gateway_combo.currentText()

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
                    # 转义花括号避免loguru格式化错误
                    error_msg = str(e).replace("{", "{{").replace("}", "}}")
                    self.main_engine.write_log(f"清理{gateway_name}的追价订单时发生异常：{error_msg}")

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


class ChartWindow(QtWidgets.QWidget):
    """
    K线图表窗口，作为独立窗口显示实时K线数据。
    
    功能：
    - 支持多周期K线显示（1分钟、5分钟、1小时、4小时、1天）
    - 支持从数据库或CSV文件加载数据
    - 根据tickdata实时更新K线
    - 支持切换不同合约
    - 底部滚动条可以快速切换时间范围
    """
    
    # 默认显示的合约
    DEFAULT_SYMBOL: str = "MHImain.HKFE"
    
    # 周期选项映射
    INTERVAL_MAP: dict = {
        "1分钟": "1m",
        "5分钟": "5m",
        "1小时": "1h",
        "4小时": "4h",
        "1天": "1d"
    }
    
    # 数据源选项
    DATA_SOURCE_DB: str = "数据库"
    DATA_SOURCE_CSV: str = "CSV文件"
    
    signal_tick: QtCore.Signal = QtCore.Signal(Event)
    signal_history: QtCore.Signal = QtCore.Signal(object)
    
    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        """构造函数"""
        super().__init__()
        
        self.main_engine: MainEngine = main_engine
        self.event_engine: EventEngine = event_engine
        
        # 当前显示的合约
        self.current_vt_symbol: str = ""
        
        # 当前选择的周期
        self.current_interval: str = "1m"
        
        # 当前数据源
        self.current_data_source: str = self.DATA_SOURCE_DB
        
        # CSV文件路径
        self.csv_file_path: str = ""
        
        # K线生成器（用于将tick合成K线）
        self.bg: "BarGenerator" = None
        
        # 图表组件
        self.chart: "ChartWidget" = None
        
        # 历史数据加载状态
        self.history_loaded: bool = False
        
        # 历史数据缓存（用于滚动条）
        self.history_data: list = []
        
        # 开盘价获取辅助类（复用通用工具模块）
        self.open_price_helper: PeriodOpenPriceHelper = PeriodOpenPriceHelper()
        
        # 当前未完成的K线（用于大周期实时更新）
        self._current_bar: "BarData" = None
        self._current_bar_period: "datetime" = None
        self._current_bar_index: int = -1
        
        # 周期开始时的基准成交量（用于计算周期内成交量）
        self._period_start_volume: float = 0
        self._period_start_turnover: float = 0
        
        # 数据缺口状态
        self._has_data_gap: bool = False
        self._gap_info: str = ""
        
        self.init_ui()
        self.register_event()
        
        # 默认加载合约数据
        self.load_default_symbol()
    
    def init_ui(self) -> None:
        """初始化界面"""
        from vnpy.chart import ChartWidget, CandleItem, VolumeItem
        
        self.setWindowTitle(_("K线图表"))
        self.setWindowFlags(
            QtCore.Qt.WindowType.Window |
            QtCore.Qt.WindowType.WindowCloseButtonHint |
            QtCore.Qt.WindowType.WindowMinMaxButtonsHint
        )
        
        # 合约选择区域
        self.symbol_line: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        self.symbol_line.setPlaceholderText(_("输入合约代码，如 MHImain.HKFE"))
        self.symbol_line.returnPressed.connect(self.switch_chart)
        
        self.switch_button: QtWidgets.QPushButton = QtWidgets.QPushButton(_("切换"))
        self.switch_button.clicked.connect(self.switch_chart)
        
        # 周期选择下拉框
        self.interval_combo: QtWidgets.QComboBox = QtWidgets.QComboBox()
        for name in self.INTERVAL_MAP.keys():
            self.interval_combo.addItem(name)
        self.interval_combo.setCurrentText("1分钟")
        self.interval_combo.setToolTip(_("选择K线周期"))
        self.interval_combo.setFixedWidth(80)
        self.interval_combo.currentTextChanged.connect(self.on_interval_changed)
        
        # 数据源选择下拉框
        self.datasource_combo: QtWidgets.QComboBox = QtWidgets.QComboBox()
        self.datasource_combo.addItem(self.DATA_SOURCE_DB)
        self.datasource_combo.addItem(self.DATA_SOURCE_CSV)
        self.datasource_combo.setCurrentText(self.DATA_SOURCE_DB)
        self.datasource_combo.setToolTip(_("选择数据加载来源"))
        self.datasource_combo.setFixedWidth(80)
        self.datasource_combo.currentTextChanged.connect(self.on_datasource_changed)
        
        # CSV文件选择按钮
        self.csv_button: QtWidgets.QPushButton = QtWidgets.QPushButton(_("选择文件"))
        self.csv_button.clicked.connect(self.select_csv_file)
        self.csv_button.setToolTip(_("选择CSV数据文件"))
        self.csv_button.setFixedWidth(70)
        self.csv_button.setEnabled(False)  # 默认禁用，只有选择CSV数据源时启用
        
        # CSV文件路径显示
        self.csv_path_label: QtWidgets.QLabel = QtWidgets.QLabel("")
        self.csv_path_label.setStyleSheet("color: #666; font-size: 11px;")
        self.csv_path_label.setToolTip("")
        
        # 日期时间选择器（只需设置起始时间，结束时间默认为最新）
        self.start_datetime: QtWidgets.QDateTimeEdit = QtWidgets.QDateTimeEdit()
        self.start_datetime.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.start_datetime.setCalendarPopup(True)
        # 默认开始时间：7天前
        default_start = QtCore.QDateTime.currentDateTime().addDays(-7)
        self.start_datetime.setDateTime(default_start)
        self.start_datetime.setToolTip(_("历史数据开始时间，结束时间默认为最新"))
        
        # 刷新按钮
        self.refresh_button: QtWidgets.QPushButton = QtWidgets.QPushButton(_("加载"))
        self.refresh_button.clicked.connect(self.refresh_chart)
        self.refresh_button.setToolTip(_("从起始时间加载数据到最新"))
        
        # 跳转到指定日期
        self.goto_date: QtWidgets.QDateTimeEdit = QtWidgets.QDateTimeEdit()
        self.goto_date.setDisplayFormat("MM-dd HH:mm")
        self.goto_date.setCalendarPopup(True)
        self.goto_date.setDateTime(QtCore.QDateTime.currentDateTime())
        self.goto_date.setToolTip(_("选择要跳转到的日期时间"))
        self.goto_date.setFixedWidth(110)
        
        self.goto_button: QtWidgets.QPushButton = QtWidgets.QPushButton(_("跳转"))
        self.goto_button.clicked.connect(self.goto_datetime)
        self.goto_button.setToolTip(_("跳转到指定日期时间"))
        
        # 跳转到最新按钮
        self.latest_button: QtWidgets.QPushButton = QtWidgets.QPushButton(_("最新"))
        self.latest_button.clicked.connect(self.goto_latest)
        self.latest_button.setToolTip(_("跳转到最新K线"))
        
        # 保存CSV按钮
        self.save_csv_button: QtWidgets.QPushButton = QtWidgets.QPushButton(_("保存CSV"))
        self.save_csv_button.clicked.connect(self.save_to_csv)
        self.save_csv_button.setToolTip(_("将当前加载的数据保存为CSV文件"))
        
        # 顶部布局 - 第一行：合约选择、周期、数据源
        hbox1: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        hbox1.addWidget(QtWidgets.QLabel(_("合约:")))
        hbox1.addWidget(self.symbol_line, 1)
        hbox1.addWidget(QtWidgets.QLabel(_("周期:")))
        hbox1.addWidget(self.interval_combo)
        hbox1.addWidget(QtWidgets.QLabel(_("数据源:")))
        hbox1.addWidget(self.datasource_combo)
        hbox1.addWidget(self.csv_button)
        hbox1.addWidget(self.csv_path_label)
        hbox1.addWidget(self.switch_button)
        
        # 顶部布局 - 第二行：时间范围选择（结束时间默认为最新）
        hbox2: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        hbox2.addWidget(QtWidgets.QLabel(_("起始时间:")))
        hbox2.addWidget(self.start_datetime)
        hbox2.addWidget(self.refresh_button)
        hbox2.addSpacing(20)
        hbox2.addWidget(QtWidgets.QLabel(_("跳转:")))
        hbox2.addWidget(self.goto_date)
        hbox2.addWidget(self.goto_button)
        hbox2.addWidget(self.latest_button)
        hbox2.addSpacing(20)
        hbox2.addWidget(self.save_csv_button)
        hbox2.addStretch()
        
        # 创建K线图表
        self.chart = ChartWidget()
        self.chart.add_plot("candle", hide_x_axis=True)
        self.chart.add_plot("volume", maximum_height=150)
        self.chart.add_item(CandleItem, "candle", "candle")
        self.chart.add_item(VolumeItem, "volume", "volume")
        self.chart.add_cursor()
        
        # 时间滚动条（横向）
        self.time_slider: QtWidgets.QSlider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.time_slider.setMinimum(0)
        self.time_slider.setMaximum(100)
        self.time_slider.setValue(100)  # 默认显示最新
        self.time_slider.setToolTip(_("拖动滚动条查看不同时间段的K线"))
        self.time_slider.valueChanged.connect(self.on_time_slider_changed)
        
        # 价格滚动条（竖向）- 用于缩放价格范围
        self.price_slider: QtWidgets.QSlider = QtWidgets.QSlider(QtCore.Qt.Orientation.Vertical)
        self.price_slider.setMinimum(10)
        self.price_slider.setMaximum(200)
        self.price_slider.setValue(100)  # 默认100%显示
        self.price_slider.setToolTip(_("拖动滚动条缩放K线数量（上多下少）"))
        self.price_slider.valueChanged.connect(self.on_price_slider_changed)
        self.price_slider.setFixedWidth(20)
        
        # 时间范围标签
        self.time_start_label: QtWidgets.QLabel = QtWidgets.QLabel("")
        self.time_end_label: QtWidgets.QLabel = QtWidgets.QLabel("")
        self.time_start_label.setStyleSheet("color: #666; font-size: 11px;")
        self.time_end_label.setStyleSheet("color: #666; font-size: 11px;")
        self.time_start_label.setFixedWidth(80)
        self.time_end_label.setFixedWidth(80)
        
        # 图表和竖向滚动条的水平布局
        chart_layout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        chart_layout.setSpacing(5)
        chart_layout.addWidget(self.chart, 1)
        chart_layout.addWidget(self.price_slider)
        
        # 底部时间滚动条布局（扩展更多空间）
        slider_layout: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        slider_layout.setContentsMargins(0, 5, 25, 0)  # 右边留出空间对齐竖向滚动条
        slider_layout.addWidget(self.time_start_label)
        slider_layout.addWidget(self.time_slider, 1)
        slider_layout.addWidget(self.time_end_label)
        
        # 状态标签
        self.status_label: QtWidgets.QLabel = QtWidgets.QLabel(_("请输入合约代码开始查看K线"))
        self.status_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #888; font-size: 12px;")
        
        # 总体布局
        vbox: QtWidgets.QVBoxLayout = QtWidgets.QVBoxLayout()
        vbox.setContentsMargins(10, 10, 10, 10)
        vbox.addLayout(hbox1)
        vbox.addLayout(hbox2)
        vbox.addLayout(chart_layout, 1)
        vbox.addLayout(slider_layout)
        vbox.addWidget(self.status_label)
        
        self.setLayout(vbox)
        self.resize(1100, 750)
    
    def register_event(self) -> None:
        """注册事件监听"""
        self.signal_tick.connect(self.process_tick_event)
        self.signal_history.connect(self.process_history_data)
        self.event_engine.register(EVENT_TICK, self.signal_tick.emit)
    
    def on_interval_changed(self, text: str) -> None:
        """周期选择改变时的处理"""
        self.current_interval = self.INTERVAL_MAP.get(text, "1m")
        # 如果已加载合约，自动刷新
        if self.current_vt_symbol:
            self.refresh_chart()
    
    def on_datasource_changed(self, text: str) -> None:
        """数据源选择改变时的处理"""
        self.current_data_source = text
        
        # 根据数据源启用/禁用CSV文件选择按钮
        if text == self.DATA_SOURCE_CSV:
            self.csv_button.setEnabled(True)
            # 如果已选择了CSV文件，显示路径
            if self.csv_file_path:
                self.csv_path_label.setText(self.csv_file_path.split("/")[-1])
            else:
                self.csv_path_label.setText(_("请选择文件"))
        else:
            self.csv_button.setEnabled(False)
            self.csv_path_label.setText("")
    
    def select_csv_file(self) -> None:
        """选择CSV数据文件"""
        file_path, selected_filter = QtWidgets.QFileDialog.getOpenFileName(
            self,
            _("选择CSV数据文件"),
            "",
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            self.csv_file_path = file_path
            # 显示文件名（不显示完整路径）
            file_name = file_path.split("/")[-1].split("\\")[-1]
            self.csv_path_label.setText(file_name)
            self.csv_path_label.setToolTip(file_path)
            
            # 如果已选择合约，自动加载
            if self.current_vt_symbol:
                self.refresh_chart()
    
    def save_to_csv(self) -> None:
        """将当前加载的数据保存为CSV文件"""
        if not self.history_data:
            QtWidgets.QMessageBox.warning(
                self,
                _("警告"),
                _("没有可保存的数据，请先加载数据")
            )
            return
        
        # 生成默认文件名
        from datetime import datetime
        interval_name = self.interval_combo.currentText()
        default_name = f"{self.current_vt_symbol}_{self.current_interval}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        file_path, selected_filter = QtWidgets.QFileDialog.getSaveFileName(
            self,
            _("保存CSV文件"),
            default_name,
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if not file_path:
            return
        
        try:
            import csv
            
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # 写入表头
                writer.writerow([
                    'datetime', 'open', 'high', 'low', 'close', 
                    'volume', 'turnover', 'open_interest'
                ])
                
                # 写入数据
                for bar in self.history_data:
                    writer.writerow([
                        bar.datetime.strftime('%Y-%m-%d %H:%M:%S'),
                        bar.open_price,
                        bar.high_price,
                        bar.low_price,
                        bar.close_price,
                        bar.volume,
                        bar.turnover if bar.turnover else 0,
                        bar.open_interest if bar.open_interest else 0
                    ])
            
            self.main_engine.write_log(f"[保存CSV] 已保存 {len(self.history_data)} 根K线到 {file_path}")
            
            QtWidgets.QMessageBox.information(
                self,
                _("成功"),
                _("已保存 {} 根K线到:\n{}").format(len(self.history_data), file_path)
            )
            
        except Exception as e:
            error_msg = str(e).replace("{", "{{").replace("}", "}}")
            self.main_engine.write_log(f"[保存CSV] 保存失败: {error_msg}")
            QtWidgets.QMessageBox.critical(
                self,
                _("错误"),
                _("保存失败: {}").format(str(e))
            )
    
    def _get_interval_enum(self) -> "Interval":
        """根据当前选择的周期返回Interval枚举"""
        from vnpy.trader.constant import Interval
        
        interval_map = {
            "1m": Interval.MINUTE,
            "5m": Interval.MINUTE_5,
            "1h": Interval.HOUR,
            "4h": Interval.HOUR_4,
            "1d": Interval.DAILY
        }
        return interval_map.get(self.current_interval, Interval.MINUTE)
    
    def _get_future_bars(self) -> int:
        """根据当前周期返回未来空间的K线数量"""
        # 未来2小时的空间，根据不同周期计算K线数量
        future_bars_map = {
            "1m": 120,    # 2小时 = 120分钟
            "5m": 24,     # 2小时 = 24根5分钟K线
            "1h": 2,      # 2小时 = 2根1小时K线
            "4h": 1,      # 4小时周期，预留1根
            "1d": 1       # 日线周期，预留1根
        }
        return future_bars_map.get(self.current_interval, 120)
    
    def switch_chart(self) -> None:
        """切换到新的合约图表"""
        vt_symbol: str = str(self.symbol_line.text()).strip()
        if not vt_symbol:
            self.status_label.setText(_("请输入有效的合约代码"))
            return
        
        if vt_symbol == self.current_vt_symbol:
            return
        
        # 保存新的合约代码
        self.current_vt_symbol = vt_symbol
        self.history_loaded = False
        self.history_data = []
        
        # 重置当前K线状态
        self._current_bar = None
        self._current_bar_period = None
        self._current_bar_index = -1
        
        # 重置成交量追踪状态
        self._period_start_volume = 0
        self._period_start_turnover = 0
        self._bar_historical_volume = 0
        self._bar_historical_turnover = 0
        self._need_init_baseline = True
        
        # 重置数据缺口状态
        self._has_data_gap = False
        self._gap_info = ""
        
        # 清空图表
        self.chart.clear_all()
        
        # 重置滚动条
        self.time_slider.setValue(100)
        self.time_start_label.setText("")
        self.time_end_label.setText("")
        
        # 创建新的K线生成器
        # 对于HKFE交易所，使用HKFEBarGenerator以确保时间边界正确
        from vnpy.trader.utility import BarGenerator, extract_vt_symbol
        from vnpy.trader.constant import Exchange, Interval
        from vnpy.trader.hkfe_bar_generator import create_bar_generator
        
        # 检查是否为HKFE交易所
        try:
            symbol, exchange = extract_vt_symbol(vt_symbol)
            if exchange == Exchange.HKFE:
                # 使用HKFEBarGenerator（仅用于1分钟K线合成）
                self.bg = create_bar_generator(
                    self.on_bar,
                    window=0,
                    on_window_bar=None,
                    interval=Interval.MINUTE,
                    daily_end=None,
                    exchange=exchange,
                    symbol=symbol
                )
            else:
                # 其他交易所使用标准BarGenerator
                self.bg = BarGenerator(self.on_bar)
        except:
            # 如果提取失败，使用标准BarGenerator
            self.bg = BarGenerator(self.on_bar)
        
        # 更新窗口标题（显示合约和周期）
        interval_name = self.interval_combo.currentText()
        self.setWindowTitle(_("K线图表 - {} - {}").format(vt_symbol, interval_name))
        
        # 更新状态
        self.status_label.setText(_("正在加载 {} 的历史数据...").format(vt_symbol))
        
        # 加载历史K线数据（最近7天的1分钟数据）
        self.load_history_data(vt_symbol)
        
        # 订阅行情数据
        self.subscribe_tick(vt_symbol)
    
    def refresh_chart(self) -> None:
        """刷新当前图表"""
        if self.current_vt_symbol:
            self.history_loaded = False
            self.history_data = []
            
            # 重置当前K线状态
            self._current_bar = None
            self._current_bar_period = None
            self._current_bar_index = -1
            
            # 重置成交量追踪状态
            self._period_start_volume = 0
            self._period_start_turnover = 0
            self._bar_historical_volume = 0
            self._bar_historical_turnover = 0
            self._need_init_baseline = True
            
            # 重置数据缺口状态
            self._has_data_gap = False
            self._gap_info = ""
            
            self.chart.clear_all()
            self.status_label.setStyleSheet("color: #888; font-size: 12px;")
            self.status_label.setText(_("正在刷新 {} 的数据...").format(self.current_vt_symbol))
            self.load_history_data(self.current_vt_symbol)
    
    def goto_latest(self) -> None:
        """
        跳转到最新K线（包含未来空间）
        
        确保各个周期都能正确跳转到最新的实时K线
        """
        if not self.history_data:
            return
        
        # 设置滚动条到最右边
        self.time_slider.setValue(100)
        
        # 扩展限制并移动到扩展后的末尾
        self.extend_chart_x_limit(move_to_end=True)
        
        # 更新状态显示
        if self.history_data:
            last_bar = self.history_data[-1]
            interval_name = self.interval_combo.currentText()
            
            # 检查是否是当前进行中的K线
            is_current = ""
            if hasattr(self, '_current_bar') and self._current_bar is not None:
                if self._current_bar.datetime == last_bar.datetime:
                    is_current = _(" (进行中)")
            
            self.status_label.setText(
                _("已跳转到最新 | {} | {} | 最后K线: {}{}").format(
                    self.current_vt_symbol,
                    interval_name,
                    last_bar.datetime.strftime("%m-%d %H:%M"),
                    is_current
                )
            )
    
    def goto_datetime(self) -> None:
        """跳转到指定日期时间"""
        if not self.history_data:
            return
        
        # 获取目标日期时间
        target_qdt = self.goto_date.dateTime()
        target_py = target_qdt.toPython()
        
        # 在历史数据中查找最接近的K线索引
        target_ix = None
        min_diff = None
        
        for ix, bar in enumerate(self.history_data):
            # 比较时间差（忽略时区）
            bar_dt = bar.datetime.replace(tzinfo=None)
            target_dt = target_py.replace(tzinfo=None) if hasattr(target_py, 'tzinfo') else target_py
            
            diff = abs((bar_dt - target_dt).total_seconds())
            
            if min_diff is None or diff < min_diff:
                min_diff = diff
                target_ix = ix
        
        if target_ix is not None:
            # 计算滚动条位置（让目标K线显示在视图中央）
            visible_bars = self.chart._bar_count
            right_ix = target_ix + visible_bars // 2
            
            total_bars = len(self.history_data)
            future_bars = self._get_future_bars()
            max_right_ix = total_bars + future_bars
            
            right_ix = max(visible_bars, min(max_right_ix, right_ix))
            
            # 更新图表视图
            self.chart._right_ix = right_ix
            self.chart._update_x_range()
            
            # 更新滚动条位置
            if max_right_ix > visible_bars:
                slider_value = int((right_ix - visible_bars) / (max_right_ix - visible_bars) * 100)
                slider_value = max(0, min(100, slider_value))
                self.time_slider.blockSignals(True)
                self.time_slider.setValue(slider_value)
                self.time_slider.blockSignals(False)
            
            # 更新状态
            bar = self.history_data[target_ix]
            self.status_label.setText(
                _("已跳转到 {} | 索引 {}/{}").format(
                    bar.datetime.strftime("%m-%d %H:%M"),
                    target_ix + 1,
                    total_bars
                )
            )
    
    def on_time_slider_changed(self, value: int) -> None:
        """时间滚动条值改变时更新图表视图（横向滚动）"""
        if not self.history_data:
            return
        
        total_bars = len(self.history_data)
        if total_bars == 0:
            return
        
        # 获取当前显示的K线数量
        visible_bars = self.chart._bar_count
        
        # 根据当前周期获取未来空间K线数量
        future_bars = self._get_future_bars()
        
        # 先确保图表的x轴限制已扩展
        self.extend_chart_x_limit()
        
        # 根据滚动条位置计算右边界索引
        # value=0时显示最早的数据，value=100时显示最新数据+未来空间
        max_right_ix = total_bars + future_bars  # 扩展到未来
        min_right_ix = visible_bars
        
        right_ix = int(min_right_ix + (max_right_ix - min_right_ix) * value / 100)
        right_ix = max(visible_bars, min(max_right_ix, right_ix))
        
        # 更新图表视图
        self.chart._right_ix = right_ix
        self.chart._update_x_range()
    
    def on_price_slider_changed(self, value: int) -> None:
        """价格滚动条值改变时更新图表视图（缩放K线数量）"""
        if not self.history_data:
            return
        
        total_bars = len(self.history_data)
        if total_bars == 0:
            return
        
        # value范围10-200，对应显示K线数量
        # value=10时显示较少K线（放大），value=200时显示较多K线（缩小）
        min_bars = 50
        max_bars = min(500, total_bars)
        
        # 计算显示的K线数量
        bar_count = int(min_bars + (max_bars - min_bars) * value / 200)
        bar_count = max(min_bars, min(max_bars, bar_count))
        
        # 更新图表的K线数量
        self.chart._bar_count = bar_count
        self.chart._update_x_range()
        
        # 根据当前周期获取未来空间K线数量
        future_bars = self._get_future_bars()
        max_right_ix = total_bars + future_bars
        
        # 同步更新时间滚动条位置
        if hasattr(self.chart, '_right_ix'):
            current_right = self.chart._right_ix
            # 确保时间滚动条位置正确
            if max_right_ix > bar_count:
                slider_value = int((current_right - bar_count) / (max_right_ix - bar_count) * 100)
                slider_value = max(0, min(100, slider_value))
                self.time_slider.blockSignals(True)
                self.time_slider.setValue(slider_value)
                self.time_slider.blockSignals(False)
    
    def load_history_data(self, vt_symbol: str) -> None:
        """加载历史K线数据"""
        from threading import Thread
        from datetime import datetime
        from tzlocal import get_localzone_name
        
        # 获取用户选择的起始时间
        start_qdt = self.start_datetime.dateTime()
        
        # 转换为Python datetime
        start_py = start_qdt.toPython()
        
        # 获取当前选择的周期和数据源
        interval_enum = self._get_interval_enum()
        data_source = self.current_data_source
        csv_path = self.csv_file_path
        
        def _load():
            try:
                from vnpy.trader.utility import extract_vt_symbol, ZoneInfo
                from vnpy.trader.constant import Interval
                from vnpy.trader.object import HistoryRequest, BarData
                from vnpy.trader.database import get_database
                from vnpy.trader.datafeed import get_datafeed
                
                symbol, exchange = extract_vt_symbol(vt_symbol)
                
                # 起始时间使用用户选择，结束时间使用当前最新时间
                local_tz = ZoneInfo(get_localzone_name())
                start: datetime = start_py.replace(tzinfo=local_tz)
                end: datetime = datetime.now(local_tz)  # 结束时间始终为当前最新
                
                data = None
                
                # 根据数据源加载数据
                if data_source == self.DATA_SOURCE_CSV:
                    # 从CSV文件加载
                    data = self._load_from_csv(csv_path, symbol, exchange, interval_enum, start, end)
                else:
                    # 从数据库加载（用户选择了"从数据库加载"）
                    database = get_database()
                    data = database.load_bar_data(
                        symbol,
                        exchange,
                        interval_enum,
                        start,
                        end
                    )
                    
                    # 如果数据库中没有数据或数据不完整，根据周期类型进行处理
                    # 对于5分钟、1小时和4小时数据，尝试从1分钟数据自动合成补齐
                    if interval_enum in [Interval.MINUTE_5, Interval.HOUR, Interval.HOUR_4]:
                        # 检测数据中的缺失时间段并补齐
                        data = self._fill_missing_bars(
                            data, symbol, exchange, interval_enum, start, end, database
                        )
                    elif not data:
                        # 对于其他周期（如1分钟），如果数据库中没有数据，提示用户
                        self.write_log(f"数据库中没有{interval_enum.value}数据，请先在DataManager中下载数据")
                
                # 对于1小时数据，如果从CSV加载，需要检测并补齐gap（这个主要是用于CSV到当前时间的gap，不是历史数据的gap）
                if data and interval_enum == Interval.HOUR and data_source == self.DATA_SOURCE_CSV:
                    # 检测并补齐gap
                    data = self._detect_and_fill_gap(data, vt_symbol, interval_enum)
                
                # 发送历史数据更新信号
                if data:
                    self.signal_history.emit(data)
                else:
                    self.signal_history.emit([])
                    
            except Exception as e:
                # 转义花括号避免loguru格式化错误
                error_msg = str(e).replace("{", "{{").replace("}", "}}")
                self.main_engine.write_log(f"加载K线历史数据失败: {error_msg}")
                self.signal_history.emit([])
        
        # 在后台线程加载
        thread: Thread = Thread(target=_load)
        thread.start()
    
    def _load_from_csv(
        self,
        csv_path: str,
        symbol: str,
        exchange: "Exchange",
        interval: "Interval",
        start: "datetime",
        end: "datetime"
    ) -> list:
        """从CSV文件加载K线数据"""
        import csv
        from datetime import datetime
        from vnpy.trader.object import BarData
        from vnpy.trader.constant import Interval
        
        if not csv_path:
            self.main_engine.write_log("未选择CSV文件")
            return []
        
        try:
            bars: list[BarData] = []
            
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    try:
                        # 解析日期时间（支持多种格式）
                        dt_str = row.get("datetime", row.get("date", row.get("time", "")))
                        if not dt_str:
                            continue
                        
                        # 尝试多种日期格式
                        dt = None
                        for fmt in [
                            "%Y-%m-%d %H:%M:%S",
                            "%Y-%m-%d %H:%M",
                            "%Y/%m/%d %H:%M:%S",
                            "%Y/%m/%d %H:%M",
                            "%Y-%m-%dT%H:%M:%S",
                            "%Y-%m-%d"
                        ]:
                            try:
                                dt = datetime.strptime(dt_str, fmt)
                                break
                            except ValueError:
                                continue
                        
                        if dt is None:
                            continue
                        
                        # 添加时区
                        if dt.tzinfo is None:
                            from tzlocal import get_localzone_name
                            from vnpy.trader.utility import ZoneInfo
                            dt = dt.replace(tzinfo=ZoneInfo(get_localzone_name()))
                        
                        # 过滤时间范围
                        if dt < start or dt > end:
                            continue
                        
                        # 创建BarData对象
                        bar = BarData(
                            symbol=symbol,
                            exchange=exchange,
                            datetime=dt,
                            interval=interval,
                            open_price=float(row.get("open", row.get("open_price", 0))),
                            high_price=float(row.get("high", row.get("high_price", 0))),
                            low_price=float(row.get("low", row.get("low_price", 0))),
                            close_price=float(row.get("close", row.get("close_price", 0))),
                            volume=float(row.get("volume", 0)),
                            turnover=float(row.get("turnover", row.get("amount", 0))),
                            open_interest=float(row.get("open_interest", row.get("oi", 0))),
                            gateway_name="CSV"
                        )
                        bars.append(bar)
                        
                    except (ValueError, KeyError) as e:
                        continue
            
            # 按时间排序
            bars.sort(key=lambda x: x.datetime)
            
            self.main_engine.write_log(f"从CSV加载了 {len(bars)} 根K线数据")
            return bars
            
        except Exception as e:
            error_msg = str(e).replace("{", "{{").replace("}", "}}")
            self.main_engine.write_log(f"CSV文件读取失败: {error_msg}")
            return []
    
    def _fill_missing_bars(
        self,
        data: list,
        symbol: str,
        exchange: "Exchange",
        interval: "Interval",
        start: datetime,
        end: datetime,
        database
    ) -> list:
        """
        检测并补齐数据中的缺失时间段
        
        对于5分钟、1小时、4小时K线，检测查询范围内是否有缺失的时间段，
        如果有缺失，从1分钟数据自动聚合补齐。
        
        Args:
            data: 已加载的K线数据（可能为空或部分数据）
            symbol: 合约代码
            exchange: 交易所
            interval: K线周期
            start: 查询起始时间
            end: 查询结束时间
            database: 数据库实例
            
        Returns:
            补齐后的K线数据列表（按时间排序）
        """
        from vnpy.trader.constant import Interval
        from vnpy.trader.database import DB_TZ
        
        # 如果没有数据，尝试整个范围自动合成
        if not data:
            return self._synthesize_missing_bars(
                symbol, exchange, interval, start, end, database
            )
        
        # 对数据进行排序
        data.sort(key=lambda x: x.datetime)
        
        # 检查数据是否完整覆盖查询范围
        data_start = data[0].datetime if data else None
        data_end = data[-1].datetime if data else None
        
        # 判断是否需要补齐：检查整体范围或中间缺失
        need_fill = False
        
        # 1. 检查是否完全没有数据
        if not data:
            need_fill = True
            self.main_engine.write_log(f"数据库中没有{interval.value}数据，尝试从1分钟数据自动合成...")
        
        # 2. 检查数据范围是否不完整
        elif data_start and data_end:
            data_range = (data_end - data_start).total_seconds()
            query_range = (end - start).total_seconds()
            
            # 如果数据范围小于查询范围的80%，或数据起始/结束时间不在查询范围内，补齐整个范围
            if (data_range < query_range * 0.8 or 
                data_start > start + (end - start) * 0.1 or
                data_end < end - (end - start) * 0.1):
                need_fill = True
                self.main_engine.write_log(
                    f"检测到{interval.value}数据范围不完整（数据范围: {data_start.strftime('%m-%d %H:%M')} - "
                    f"{data_end.strftime('%m-%d %H:%M')}，查询范围: {start.strftime('%m-%d %H:%M')} - "
                    f"{end.strftime('%m-%d %H:%M')}），尝试补齐..."
                )
        
        # 如果整体范围不完整，直接补齐整个查询范围
        if need_fill:
            synthesized_data = self._synthesize_missing_bars(
                symbol, exchange, interval, start, end, database
            )
            
            if synthesized_data:
                # 合并数据，去重（使用datetime作为key）
                merged_dict = {}
                
                # 先添加已有数据
                for bar in data:
                    bar_dt = bar.datetime.replace(tzinfo=None) if bar.datetime.tzinfo else bar.datetime
                    merged_dict[bar_dt] = bar
                
                # 添加合成的数据（不覆盖已有数据）
                for bar in synthesized_data:
                    bar_dt = bar.datetime.replace(tzinfo=None) if bar.datetime.tzinfo else bar.datetime
                    if bar_dt not in merged_dict:
                        merged_dict[bar_dt] = bar
                
                # 按时间排序返回
                result = list(merged_dict.values())
                result.sort(key=lambda x: x.datetime)
                self.main_engine.write_log(f"补齐完成，合并后共有 {len(result)} 根{interval.value}K线（原有{len(data)}根，新增{len(result) - len(data)}根）")
                return result
            else:
                self.main_engine.write_log(f"无法补齐{interval.value}数据，使用已有数据")
                return data
        
        # 3. 即使整体范围完整，也要检查中间是否有缺失的数据段
        # 通过检查连续K线之间的时间间隔来判断
        if data and len(data) > 1:
            from vnpy.trader.period_utils import get_period_start
            from datetime import timedelta
            
            missing_ranges = []
            
            # 计算每个周期的期望间隔（秒）
            if interval == Interval.MINUTE_5:
                expected_interval = 300  # 5分钟 = 300秒
            elif interval == Interval.HOUR:
                expected_interval = 3600  # 1小时 = 3600秒
            elif interval == Interval.HOUR_4:
                expected_interval = 14400  # 4小时 = 14400秒
            else:
                expected_interval = 60  # 默认1分钟
            
            # 检查连续K线之间是否有缺失
            for i in range(len(data) - 1):
                bar1 = data[i]
                bar2 = data[i + 1]
                
                bar1_dt = bar1.datetime.replace(tzinfo=None) if bar1.datetime.tzinfo else bar1.datetime
                bar2_dt = bar2.datetime.replace(tzinfo=None) if bar2.datetime.tzinfo else bar2.datetime
                
                # 计算时间间隔
                time_gap = (bar2_dt - bar1_dt).total_seconds()
                
                # 如果间隔明显大于期望间隔（允许10%的误差），说明中间有缺失
                if time_gap > expected_interval * 1.5:  # 1.5倍阈值，考虑到HKFE的特殊时段划分
                    gap_start = bar1_dt
                    gap_end = bar2_dt
                    missing_ranges.append((gap_start, gap_end))
            
            # 如果有缺失的段，补齐这些段
            if missing_ranges:
                self.main_engine.write_log(f"检测到{len(missing_ranges)}个缺失时间段，开始补齐...")
                synthesized_bars = []
                
                for gap_start, gap_end in missing_ranges:
                    # 稍微扩大范围，确保包含边界
                    gap_start_expanded = gap_start + timedelta(seconds=1)
                    gap_end_expanded = gap_end - timedelta(seconds=1)
                    
                    gap_data = self._synthesize_missing_bars(
                        symbol, exchange, interval, gap_start_expanded, gap_end_expanded, database
                    )
                    if gap_data:
                        synthesized_bars.extend(gap_data)
                
                if synthesized_bars:
                    # 合并数据，去重
                    merged_dict = {}
                    
                    # 先添加已有数据
                    for bar in data:
                        bar_dt = bar.datetime.replace(tzinfo=None) if bar.datetime.tzinfo else bar.datetime
                        merged_dict[bar_dt] = bar
                    
                    # 添加补齐的数据（不覆盖已有数据）
                    for bar in synthesized_bars:
                        bar_dt = bar.datetime.replace(tzinfo=None) if bar.datetime.tzinfo else bar.datetime
                        if bar_dt not in merged_dict:
                            merged_dict[bar_dt] = bar
                    
                    # 按时间排序返回
                    result = list(merged_dict.values())
                    result.sort(key=lambda x: x.datetime)
                    self.main_engine.write_log(f"中间缺失段补齐完成，合并后共有 {len(result)} 根{interval.value}K线（原有{len(data)}根，新增{len(result) - len(data)}根）")
                    return result
        
        return data
    
    def _synthesize_missing_bars(
        self,
        symbol: str,
        exchange: "Exchange",
        interval: "Interval",
        start: datetime,
        end: datetime,
        database
    ) -> list:
        """
        从1分钟数据合成缺失的K线数据
        
        Args:
            symbol: 合约代码
            exchange: 交易所
            interval: K线周期
            start: 查询起始时间
            end: 查询结束时间
            database: 数据库实例
            
        Returns:
            合成后的K线数据列表
        """
        from vnpy_datamanager import APP_NAME
        from vnpy.trader.database import DB_TZ
        from vnpy.trader.constant import Interval
        
        try:
            manager_engine = self.main_engine.get_engine(APP_NAME)
            if not manager_engine:
                self.main_engine.write_log(f"无法获取DataManager引擎，请确保DataManager模块已加载")
                return []
            
            # 转换时区到数据库时区
            if start.tzinfo:
                start_db = start.astimezone(DB_TZ)
            else:
                start_db = start.replace(tzinfo=DB_TZ)
            
            if end.tzinfo:
                end_db = end.astimezone(DB_TZ)
            else:
                end_db = end.replace(tzinfo=DB_TZ)
            
            # 合成数据（会保存到数据库）
            count = 0
            if interval == Interval.MINUTE_5:
                count = manager_engine.aggregate_5minute_bars(symbol, exchange, start_db, end_db)
            elif interval == Interval.HOUR:
                count = manager_engine.aggregate_hour_bars(symbol, exchange, start_db, end_db)
            elif interval == Interval.HOUR_4:
                count = manager_engine.aggregate_4hour_bars(symbol, exchange, start_db, end_db)
            
            if count > 0:
                self.main_engine.write_log(f"自动合成了 {count} 根{interval.value}K线，正在加载...")
                # 从数据库重新加载合成后的数据
                synthesized_data = database.load_bar_data(
                    symbol,
                    exchange,
                    interval,
                    start,
                    end
                )
                return synthesized_data if synthesized_data else []
            else:
                self.main_engine.write_log(f"无法合成{interval.value}数据：可能缺少1分钟基础数据，请先在DataManager中下载1分钟数据")
                return []
        except ImportError:
            self.main_engine.write_log(f"无法导入DataManager模块，请确保DataManager已安装")
            return []
        except Exception as e:
            self.main_engine.write_log(f"自动合成{interval.value}数据失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _detect_and_fill_gap(
        self,
        history: list,
        vt_symbol: str,
        interval: "Interval"
    ) -> list:
        """
        检测并填充数据缺口
        
        对于所有周期的K线，检测历史数据与当前时间的gap：
        - 1分钟周期：先从数据库加载，没有则从FUTU API获取
        - 大周期（>1分钟）：先从数据库加载1分钟数据，没有则从FUTU API获取，然后合成
        
        注意：所有大周期合成都使用相同的 _synthesize_bars_from_minute 方法，
        确保合成逻辑一致。
        
        Args:
            history: 已加载的历史K线数据
            vt_symbol: 合约代码
            interval: K线周期
            
        Returns:
            填充后的K线数据列表
        """
        from datetime import datetime, timedelta
        from vnpy.trader.constant import Interval
        from vnpy.trader.utility import extract_vt_symbol, ZoneInfo
        from vnpy.trader.database import get_database
        from tzlocal import get_localzone_name
        
        if not history:
            return history
        
        try:
            # 获取最后一根K线的时间
            last_bar = history[-1]
            last_bar_time = last_bar.datetime
            
            # 获取当前时间
            local_tz = ZoneInfo(get_localzone_name())
            now = datetime.now(local_tz)
            
            # 计算需要补齐的时间范围
            gap_start = last_bar_time + timedelta(minutes=1)
            gap_end = now
            
            # 如果没有gap，直接返回
            if gap_start >= gap_end:
                self._has_data_gap = False
                return history
            
            # 计算gap的大小（小时）
            gap_hours = (gap_end - gap_start).total_seconds() / 3600
            
            interval_name = self.interval_combo.currentText() if hasattr(self, 'interval_combo') else str(interval)
            self.main_engine.write_log(
                f"[数据补齐] 检测到{interval_name}数据缺口: {gap_start.strftime('%m-%d %H:%M')} - {gap_end.strftime('%m-%d %H:%M')} (约{gap_hours:.1f}小时)"
            )
            
            # 从数据库加载1分钟数据来填充gap（仅1分钟周期尝试数据库）
            symbol, exchange = extract_vt_symbol(vt_symbol)
            minute_bars = []
            
            if interval == Interval.MINUTE:
                # 1分钟周期：先尝试数据库
                database = get_database()
                minute_bars = database.load_bar_data(
                    symbol,
                    exchange,
                    Interval.MINUTE,
                    gap_start,
                    gap_end
                )
                
                if minute_bars:
                    self.main_engine.write_log(f"[数据补齐] 从数据库加载了 {len(minute_bars)} 根1分钟K线用于补齐")
            
            # 如果没有从数据库获取到数据，尝试FUTU API
            if not minute_bars:
                self.main_engine.write_log("[数据补齐] 尝试从FUTU API获取1分钟数据...")
                
                minute_bars = self._fetch_bars_from_futu(
                    symbol, exchange, Interval.MINUTE, gap_start, gap_end
                )
                
                if not minute_bars:
                    # 标记存在数据缺口，无法补齐
                    self._has_data_gap = True
                    self._gap_info = f"{gap_start.strftime('%m-%d %H:%M')} - {gap_end.strftime('%m-%d %H:%M')}"
                    
                    self.main_engine.write_log(
                        f"[数据补齐] 未能获取到1分钟数据用于补齐。"
                    )
                    return history
                
                self.main_engine.write_log(f"[数据补齐] 从FUTU API获取了 {len(minute_bars)} 根1分钟K线")
            
            # 根据目标周期处理补齐数据
            if interval == Interval.MINUTE:
                # 1分钟周期：直接使用加载的1分钟数据
                self._has_data_gap = False
                self.main_engine.write_log(f"[数据补齐] 补齐了 {len(minute_bars)} 根1分钟K线")
                
                # 合并历史数据和补齐数据
                result = list(history)
                
                # 检查是否有重复的时间戳
                existing_times = {bar.datetime for bar in result}
                for bar in minute_bars:
                    if bar.datetime not in existing_times:
                        result.append(bar)
                
                # 按时间排序
                result.sort(key=lambda x: x.datetime)
                return result
            else:
                # 大周期：从1分钟数据合成
                synthesized_bars = []
                
                # 对于1小时数据，使用DataManager的精确合成逻辑
                if interval == Interval.HOUR:
                    try:
                        from vnpy_datamanager import APP_NAME
                        from vnpy.trader.database import DB_TZ
                        
                        manager_engine = self.main_engine.get_engine(APP_NAME)
                        if manager_engine:
                            # 转换时区到数据库时区
                            if gap_start.tzinfo:
                                gap_start_db = gap_start.astimezone(DB_TZ)
                            else:
                                gap_start_db = gap_start.replace(tzinfo=DB_TZ)
                            
                            if gap_end.tzinfo:
                                gap_end_db = gap_end.astimezone(DB_TZ)
                            else:
                                gap_end_db = gap_end.replace(tzinfo=DB_TZ)
                            
                            # 先保存1分钟数据到数据库（临时），然后合成1小时数据
                            database = get_database()
                            if minute_bars:
                                # 临时保存1分钟数据用于合成
                                database.save_bar_data(minute_bars)
                                self.main_engine.write_log(f"[数据补齐] 临时保存了 {len(minute_bars)} 根1分钟K线用于合成1小时数据")
                            
                            # 使用DataManager的精确1小时合成逻辑
                            count = manager_engine.aggregate_hour_bars(symbol, exchange, gap_start_db, gap_end_db)
                            if count > 0:
                                # 从数据库加载合成后的1小时数据
                                synthesized_bars = database.load_bar_data(
                                    symbol,
                                    exchange,
                                    Interval.HOUR,
                                    gap_start,
                                    gap_end
                                )
                                self.main_engine.write_log(f"[数据补齐] 使用DataManager精确合成逻辑，合成了 {len(synthesized_bars)} 根1小时K线")
                        else:
                            self.main_engine.write_log("[数据补齐] 无法获取DataManager引擎，使用通用合成方法")
                            # 降级到通用合成方法
                            synthesized_bars = self._synthesize_bars_from_minute(
                                minute_bars, interval, symbol, exchange
                            )
                    except Exception as e:
                        self.main_engine.write_log(f"[数据补齐] 使用DataManager合成1小时数据失败: {e}，降级到通用合成方法")
                        # 降级到通用合成方法
                        synthesized_bars = self._synthesize_bars_from_minute(
                            minute_bars, interval, symbol, exchange
                        )
                else:
                    # 其他大周期：使用统一的合成方法
                    synthesized_bars = self._synthesize_bars_from_minute(
                        minute_bars, interval, symbol, exchange
                    )
                
                if synthesized_bars:
                    self.main_engine.write_log(f"[数据补齐] 从1分钟数据合成了 {len(synthesized_bars)} 根{interval_name}K线")
                    self._has_data_gap = False
                    
                    # 合并历史数据和补齐数据
                    # 注意：最后一根可能是未完成的K线，需要特殊处理
                    result = list(history)
                    
                    for bar in synthesized_bars:
                        # 检查是否与最后一根历史K线是同一周期
                        if result and self._is_same_period(result[-1], bar, interval):
                            # 更新最后一根K线
                            result[-1] = self._merge_bars(result[-1], bar)
                        else:
                            result.append(bar)
                    
                    return result
            
            self._has_data_gap = False
            return history
            
        except Exception as e:
            error_msg = str(e).replace("{", "{{").replace("}", "}}")
            self.main_engine.write_log(f"[数据补齐] 填充失败: {error_msg}")
            self._has_data_gap = False
            return history
    
    def _fetch_bars_from_futu(
        self,
        symbol: str,
        exchange: "Exchange",
        interval: "Interval",
        start: "datetime",
        end: "datetime"
    ) -> list:
        """
        从FUTU API获取K线数据
        
        Args:
            symbol: 合约代码
            exchange: 交易所
            interval: K线周期
            start: 开始时间
            end: 结束时间
            
        Returns:
            K线数据列表，失败返回空列表
        """
        from vnpy.trader.object import HistoryRequest
        
        try:
            # 尝试从main_engine获取datafeed
            datafeed = None
            
            # 尝试获取已连接的datafeed
            if hasattr(self.main_engine, 'get_datafeed'):
                datafeed = self.main_engine.get_datafeed()
            
            # 如果没有现成的datafeed，尝试创建FUTU datafeed
            if datafeed is None:
                try:
                    from vnpy_futu.datafeed import Datafeed as FutuDatafeed
                    datafeed = FutuDatafeed()
                    if not datafeed.init(output=self.main_engine.write_log):
                        self.main_engine.write_log("[FUTU API] 无法初始化FUTU数据服务，请确保富途牛牛已启动")
                        return []
                except ImportError:
                    self.main_engine.write_log("[FUTU API] 未安装vnpy_futu模块")
                    return []
                except Exception as e:
                    error_msg = str(e).replace("{", "{{").replace("}", "}}")
                    self.main_engine.write_log(f"[FUTU API] 初始化失败: {error_msg}")
                    return []
            
            # 创建历史数据请求
            req = HistoryRequest(
                symbol=symbol,
                exchange=exchange,
                interval=interval,
                start=start,
                end=end
            )
            
            # 查询数据
            bars = datafeed.query_bar_history(req, output=self.main_engine.write_log)
            
            if bars:
                self.main_engine.write_log(f"[FUTU API] 成功获取 {len(bars)} 根K线数据")
            else:
                self.main_engine.write_log("[FUTU API] 未获取到数据")
            
            return bars
            
        except Exception as e:
            error_msg = str(e).replace("{", "{{").replace("}", "}}")
            self.main_engine.write_log(f"[FUTU API] 获取数据失败: {error_msg}")
            return []
    
    def _synthesize_bars_from_minute(
        self,
        minute_bars: list,
        target_interval: "Interval",
        symbol: str,
        exchange: "Exchange"
    ) -> list:
        """
        从1分钟K线合成大周期K线
        
        支持的周期：5分钟、1小时、4小时、日线
        4小时K线按照HKFE交易时段边界合成
        
        特殊处理：
        - 第三根4小时K线（01:15-03:00 + 09:15-11:29）跨越周末或金融假期时，
          需要正确合并数据
        
        Args:
            minute_bars: 1分钟K线数据列表
            target_interval: 目标周期
            symbol: 合约代码
            exchange: 交易所
            
        Returns:
            合成的K线数据列表
        """
        from vnpy.trader.constant import Interval
        from vnpy.trader.object import BarData
        
        if not minute_bars:
            return []
        
        # 对于4小时周期，使用特殊的合成逻辑处理跨假期情况
        if target_interval == Interval.HOUR_4:
            return self._synthesize_4hour_bars(minute_bars, symbol, exchange)
        
        # 其他周期使用标准逻辑
        period_bars: dict = {}
        
        for bar in minute_bars:
            period_start = get_period_start(bar.datetime, target_interval, exchange)
            if period_start is None:
                continue
            
            if period_start not in period_bars:
                period_bars[period_start] = []
            period_bars[period_start].append(bar)
        
        # 合成K线
        result: list[BarData] = []
        
        for period_start in sorted(period_bars.keys()):
            bars = period_bars[period_start]
            if not bars:
                continue
            
            # 按时间排序
            bars.sort(key=lambda x: x.datetime)
            
            # 计算OHLCV
            synthesized = BarData(
                symbol=symbol,
                exchange=exchange,
                datetime=period_start,
                interval=target_interval,
                open_price=bars[0].open_price,
                high_price=max(b.high_price for b in bars),
                low_price=min(b.low_price for b in bars),
                close_price=bars[-1].close_price,
                volume=sum(b.volume for b in bars),
                turnover=sum(b.turnover for b in bars),
                open_interest=bars[-1].open_interest,
                gateway_name="SYNTHESIZED"
            )
            result.append(synthesized)
        
        return result
    
    def _synthesize_4hour_bars(
        self,
        minute_bars: list,
        symbol: str,
        exchange: "Exchange"
    ) -> list:
        """
        专门合成4小时K线，正确处理跨周末和金融假期的情况
        
        第三根4小时K线（01:15-03:00 + 09:15-11:29）特殊处理：
        - 周末：周五夜盘01:15开始，周一早盘11:29结束
        - 金融假期：假期前夜盘01:15开始，假期后第一个交易日11:29结束
        """
        from datetime import timedelta
        from vnpy.trader.constant import Interval
        from vnpy.trader.object import BarData
        
        if not minute_bars:
            return []
        
        # 按时间排序
        sorted_bars = sorted(minute_bars, key=lambda x: x.datetime)
        
        # 分组逻辑：维护一个"待完成的第三周期"
        period_bars: dict = {}
        pending_period3_start = None  # 待完成的第三周期起始时间
        pending_period3_bars = []     # 待完成的第三周期数据
        
        for bar in sorted_bars:
            dt = bar.datetime
            hour = dt.hour
            minute = dt.minute
            time_value = hour * 100 + minute
            
            # 判断属于哪个时段
            if 1715 <= time_value <= 2114:
                # 时段1: 17:15-21:14
                period_start = dt.replace(hour=17, minute=15, second=0, microsecond=0)
                if period_start not in period_bars:
                    period_bars[period_start] = []
                period_bars[period_start].append(bar)
                
            elif 2115 <= time_value <= 2359:
                # 时段2前半: 21:15-23:59
                period_start = dt.replace(hour=21, minute=15, second=0, microsecond=0)
                if period_start not in period_bars:
                    period_bars[period_start] = []
                period_bars[period_start].append(bar)
                
            elif 0 <= time_value <= 114:
                # 时段2后半: 00:00-01:14
                period_start = (dt - timedelta(days=1)).replace(hour=21, minute=15, second=0, microsecond=0)
                if period_start not in period_bars:
                    period_bars[period_start] = []
                period_bars[period_start].append(bar)
                
            elif 115 <= time_value <= 300:
                # 时段3前半: 01:15-03:00（夜盘尾段）
                # 如果有待完成的第三周期，先完成它
                if pending_period3_start is not None and pending_period3_bars:
                    if pending_period3_start not in period_bars:
                        period_bars[pending_period3_start] = []
                    period_bars[pending_period3_start].extend(pending_period3_bars)
                    pending_period3_bars = []
                
                # 开始新的第三周期
                pending_period3_start = dt.replace(hour=1, minute=15, second=0, microsecond=0)
                pending_period3_bars = [bar]
                
            elif 915 <= time_value <= 1129:
                # 时段3后半: 09:15-11:29（早盘）
                if pending_period3_start is not None:
                    # 有未完成的第三周期（来自之前的01:15-03:00），继续添加数据
                    pending_period3_bars.append(bar)
                else:
                    # 没有夜盘数据（意外停盘情况），创建新周期
                    # 使用当天01:15作为起始时间
                    period_start = dt.replace(hour=1, minute=15, second=0, microsecond=0)
                    if period_start not in period_bars:
                        period_bars[period_start] = []
                    period_bars[period_start].append(bar)
                
            elif (1130 <= time_value <= 1200) or (1300 <= time_value <= 1629):
                # 时段4: 11:30-12:00 + 13:00-16:29
                # 如果有待完成的第三周期，先完成它
                if pending_period3_start is not None and pending_period3_bars:
                    if pending_period3_start not in period_bars:
                        period_bars[pending_period3_start] = []
                    period_bars[pending_period3_start].extend(pending_period3_bars)
                    pending_period3_start = None
                    pending_period3_bars = []
                
                period_start = dt.replace(hour=11, minute=30, second=0, microsecond=0)
                if period_start not in period_bars:
                    period_bars[period_start] = []
                period_bars[period_start].append(bar)
        
        # 处理最后可能剩余的待完成第三周期
        if pending_period3_start is not None and pending_period3_bars:
            if pending_period3_start not in period_bars:
                period_bars[pending_period3_start] = []
            period_bars[pending_period3_start].extend(pending_period3_bars)
        
        # 合成K线
        result: list[BarData] = []
        
        for period_start in sorted(period_bars.keys()):
            bars = period_bars[period_start]
            if not bars:
                continue
            
            # 按时间排序
            bars.sort(key=lambda x: x.datetime)
            
            # 计算OHLCV
            synthesized = BarData(
                symbol=symbol,
                exchange=exchange,
                datetime=period_start,
                interval=Interval.HOUR_4,
                open_price=bars[0].open_price,
                high_price=max(b.high_price for b in bars),
                low_price=min(b.low_price for b in bars),
                close_price=bars[-1].close_price,
                volume=sum(b.volume for b in bars),
                turnover=sum(b.turnover for b in bars),
                open_interest=bars[-1].open_interest,
                gateway_name="SYNTHESIZED"
            )
            result.append(synthesized)
        
        return result
    
    def _is_same_period(self, bar1: "BarData", bar2: "BarData", interval: "Interval") -> bool:
        """判断两根K线是否属于同一周期"""
        period1 = get_period_start(bar1.datetime, interval, bar1.exchange)
        period2 = get_period_start(bar2.datetime, interval, bar2.exchange)
        return period1 == period2
    
    def _merge_bars(self, bar1: "BarData", bar2: "BarData") -> "BarData":
        """合并两根K线（用于更新未完成的K线）"""
        from vnpy.trader.object import BarData
        
        return BarData(
            symbol=bar1.symbol,
            exchange=bar1.exchange,
            datetime=bar1.datetime,  # 保持原始时间戳
            interval=bar1.interval,
            open_price=bar1.open_price,  # 保持原始开盘价
            high_price=max(bar1.high_price, bar2.high_price),
            low_price=min(bar1.low_price, bar2.low_price),
            close_price=bar2.close_price,  # 使用新的收盘价
            volume=bar1.volume + bar2.volume,
            turnover=bar1.turnover + bar2.turnover,
            open_interest=bar2.open_interest,
            gateway_name=bar1.gateway_name
        )
    
    def _create_current_bar_from_tick(self, tick: "TickData") -> "BarData":
        """
        根据tick数据创建当前未完成的K线
        用于大周期K线的实时更新
        """
        from vnpy.trader.object import BarData
        
        interval_enum = self._get_interval_enum()
        period_start = self._get_period_start(tick.datetime, interval_enum)
        
        if period_start is None:
            return None
        
        return BarData(
            symbol=tick.symbol,
            exchange=tick.exchange,
            datetime=period_start,
            interval=interval_enum,
            open_price=tick.last_price,
            high_price=tick.last_price,
            low_price=tick.last_price,
            close_price=tick.last_price,
            volume=0,
            turnover=0,
            open_interest=tick.open_interest,
            gateway_name=tick.gateway_name
        )
    
    def subscribe_tick(self, vt_symbol: str) -> None:
        """订阅行情数据"""
        from vnpy.trader.utility import extract_vt_symbol
        
        try:
            symbol, exchange = extract_vt_symbol(vt_symbol)
            req: SubscribeRequest = SubscribeRequest(
                symbol=symbol,
                exchange=exchange
            )
            
            # 查找合约并订阅
            contract = self.main_engine.get_contract(vt_symbol)
            if contract:
                self.main_engine.subscribe(req, contract.gateway_name)
            else:
                # 尝试所有gateway
                gateway_names = self.main_engine.get_all_gateway_names()
                for gw_name in gateway_names:
                    self.main_engine.subscribe(req, gw_name)
                    
        except Exception as e:
            # 转义花括号避免loguru格式化错误
            error_msg = str(e).replace("{", "{{").replace("}", "}}")
            self.main_engine.write_log(f"订阅行情失败: {error_msg}")
    
    def process_tick_event(self, event: Event) -> None:
        """处理Tick事件 - 支持所有周期的实时更新"""
        tick: TickData = event.data
        
        # 只处理当前显示合约的tick
        if tick.vt_symbol != self.current_vt_symbol:
            return
        
        # 如果历史数据还没加载完，跳过
        if not self.history_loaded:
            return
        
        # 获取当前周期
        interval_enum = self._get_interval_enum()
        from vnpy.trader.constant import Interval
        
        if interval_enum == Interval.MINUTE:
            # 1分钟周期：使用BarGenerator从tick合成K线
            if self.bg:
                self.bg.update_tick(tick)
                
                # 实时更新当前K线
                if self.bg.bar:
                    from vnpy.trader.object import BarData
                    bar: BarData = copy(self.bg.bar)
                    bar.datetime = bar.datetime.replace(second=0, microsecond=0)
                    self.chart.update_bar(bar)
        else:
            # 5分钟、1小时、4小时周期：使用tick数据直接更新当前未完成的K线
            # 这样可以实现所有周期的实时更新
            self._update_current_bar_with_tick(tick, interval_enum)
    
    def _update_current_bar_with_tick(self, tick: "TickData", interval: "Interval") -> None:
        """
        用tick数据更新当前大周期K线
        
        根据tick时间判断是否属于当前周期：
        - 如果属于当前周期，更新当前K线
        - 如果属于新周期，完成当前K线并创建新K线
        
        成交量计算：
        - tick.volume 是当日累计成交量
        - 需要记录周期开始时的基准成交量，用当前累计量减去基准得到周期内成交量
        - 如果K线来自历史数据（有历史成交量），需要累加
        """
        from vnpy.trader.object import BarData
        
        # 获取tick所属的周期
        from vnpy.trader.utility import extract_vt_symbol
        _, exchange = extract_vt_symbol(tick.vt_symbol)
        tick_period = get_period_start(tick.datetime, interval, exchange)
        
        if tick_period is None:
            # tick时间不在交易时段内
            return
        
        # 获取当前累计成交量和成交额
        current_volume = tick.volume if tick.volume else 0
        current_turnover = tick.turnover if tick.turnover else 0
        
        # 获取该周期第一根分钟K线的开盘价（用于1小时、4小时等大周期）
        open_price = self.open_price_helper.get_period_open_price(
            tick_period, interval, tick.vt_symbol, tick=tick,
            minute_bar_generator=self.bg, history_data=self.history_data
        )
        
        # 如果无法获取开盘价，使用tick价格作为fallback（仅用于创建新K线时）
        if not open_price or open_price <= 0:
            open_price = tick.last_price if tick.last_price > 0 else None
            if open_price:
                self.main_engine.write_log(
                    f"[实时K线] 无法获取{tick_period.strftime('%H:%M')}周期开盘价，使用tick价格: {open_price}"
                )
        
        # 检查是否有当前K线
        if not hasattr(self, '_current_bar') or self._current_bar is None:
            # 记录周期开始时的基准成交量
            self._period_start_volume = current_volume
            self._period_start_turnover = current_turnover
            self._bar_historical_volume = 0
            self._bar_historical_turnover = 0
            self._need_init_baseline = False
            
            # 创建新的当前K线（使用该周期第一根分钟K线的开盘价）
            # 如果open_price无效，使用tick价格作为fallback
            final_open_price = open_price if open_price and open_price > 0 else tick.last_price
            self._current_bar = BarData(
                symbol=tick.symbol,
                exchange=tick.exchange,
                datetime=tick_period,
                interval=interval,
                open_price=final_open_price,
                high_price=tick.last_price,
                low_price=tick.last_price,
                close_price=tick.last_price,
                volume=0,
                turnover=0,
                open_interest=tick.open_interest if tick.open_interest else 0,
                gateway_name=tick.gateway_name
            )
            self._current_bar_period = tick_period
            
            # 添加到历史数据
            self.history_data.append(self._current_bar)
            self._current_bar_index = len(self.history_data) - 1
            
        elif self._current_bar_period is None or tick_period != self._current_bar_period:
            # 新周期开始，完成当前K线
            if self._current_bar_period is not None:
                self.main_engine.write_log(
                    f"[K线切换] {self._current_bar_period.strftime('%m-%d %H:%M')} -> {tick_period.strftime('%m-%d %H:%M')}"
                )
            else:
                self.main_engine.write_log(
                    f"[K线开始] 开始新周期: {tick_period.strftime('%m-%d %H:%M')}"
                )
            
            # 记录新周期开始时的基准成交量
            self._period_start_volume = current_volume
            self._period_start_turnover = current_turnover
            self._bar_historical_volume = 0
            self._bar_historical_turnover = 0
            self._need_init_baseline = False
            
            # 创建新的当前K线（使用该周期第一根分钟K线的开盘价）
            # 如果open_price无效，使用tick价格作为fallback
            final_open_price = open_price if open_price and open_price > 0 else tick.last_price
            self._current_bar = BarData(
                symbol=tick.symbol,
                exchange=tick.exchange,
                datetime=tick_period,
                interval=interval,
                open_price=final_open_price,
                high_price=tick.last_price,
                low_price=tick.last_price,
                close_price=tick.last_price,
                volume=0,
                turnover=0,
                open_interest=tick.open_interest if tick.open_interest else 0,
                gateway_name=tick.gateway_name
            )
            self._current_bar_period = tick_period
            
            # 添加到历史数据
            self.history_data.append(self._current_bar)
            self._current_bar_index = len(self.history_data) - 1
            
        else:
            # 更新当前K线
            
            # 如果需要初始化基准（来自历史数据的当前K线）
            if hasattr(self, '_need_init_baseline') and self._need_init_baseline:
                self._period_start_volume = current_volume
                self._period_start_turnover = current_turnover
                self._need_init_baseline = False
                self.main_engine.write_log(
                    f"[成交量基准] 初始化基准: {current_volume}, 历史成交量: {self._bar_historical_volume}"
                )
            
            self._current_bar.high_price = max(self._current_bar.high_price, tick.last_price)
            self._current_bar.low_price = min(self._current_bar.low_price, tick.last_price)
            self._current_bar.close_price = tick.last_price
            
            # 计算周期内的成交量
            # = 历史成交量（来自加载数据）+ tick增量成交量（当前累计 - 基准）
            tick_delta_volume = 0
            tick_delta_turnover = 0
            
            if current_volume >= self._period_start_volume:
                tick_delta_volume = current_volume - self._period_start_volume
            
            if current_turnover >= self._period_start_turnover:
                tick_delta_turnover = current_turnover - self._period_start_turnover
            
            # 获取历史成交量
            historical_volume = getattr(self, '_bar_historical_volume', 0)
            historical_turnover = getattr(self, '_bar_historical_turnover', 0)
            
            self._current_bar.volume = historical_volume + tick_delta_volume
            self._current_bar.turnover = historical_turnover + tick_delta_turnover
            
            if tick.open_interest:
                self._current_bar.open_interest = tick.open_interest
            
            # 更新历史数据中的当前K线
            if self._current_bar_index >= 0 and self._current_bar_index < len(self.history_data):
                self.history_data[self._current_bar_index] = self._current_bar
        
        # 更新图表显示
        self.chart.update_bar(self._current_bar)
    
    def on_bar(self, bar: "BarData") -> None:
        """K线合成回调（仅用于1分钟周期）"""
        from vnpy.trader.constant import Interval
        
        self.chart.update_bar(bar)
        # 更新历史数据缓存
        self.history_data.append(bar)
        
        # 缓存1分钟K线（用于快速查找开盘价）
        if bar.interval == Interval.MINUTE:
            self.open_price_helper.cache_minute_bar(bar)
        
        # 检查是否需要更新大周期K线的开盘价
        # 如果当前有大周期K线正在生成，且该分钟K线是该周期的第一根，更新开盘价
        self._update_period_open_price_if_needed(bar)
    
    def _update_period_open_price_if_needed(self, minute_bar: "BarData") -> None:
        """
        检查是否需要更新大周期K线的开盘价
        
        当第一根分钟K线完成时，如果当前有大周期K线正在生成，
        且该分钟K线是该周期的第一根，更新大周期K线的开盘价。
        """
        from vnpy.trader.constant import Interval
        
        # 只处理1分钟K线
        if minute_bar.interval != Interval.MINUTE:
            return
        
        # 检查是否有当前大周期K线
        if not hasattr(self, '_current_bar') or self._current_bar is None:
            return
        
        # 获取当前周期类型
        current_interval = self._current_bar.interval
        
        # 只处理大周期（5分钟、1小时、4小时）
        if current_interval == Interval.MINUTE:
            return
        
        # 获取该分钟K线所属的大周期
        from vnpy.trader.utility import extract_vt_symbol
        _, exchange = extract_vt_symbol(minute_bar.vt_symbol)
        minute_bar_period = get_period_start(minute_bar.datetime, current_interval, exchange)
        
        # 检查该分钟K线是否属于当前大周期K线的第一根
        if minute_bar_period == self._current_bar.datetime:
            # 获取该分钟K线的周期起始时间（应该是该分钟K线本身的时间）
            minute_period = get_period_start(minute_bar.datetime, Interval.MINUTE, exchange)
            
            # 检查该分钟K线是否是该大周期的第一根（分钟K线的时间应该等于大周期的开始时间）
            if minute_period == self._current_bar.datetime:
                # 如果当前大周期K线的开盘价不是该分钟K线的开盘价，需要更新
                if (minute_bar.open_price and minute_bar.open_price > 0 and 
                    self._current_bar.open_price != minute_bar.open_price):
                    old_open_price = self._current_bar.open_price
                    self._current_bar.open_price = minute_bar.open_price
                    
                    self.main_engine.write_log(
                        f"[开盘价更新] {current_interval.value}K线({self._current_bar.datetime.strftime('%H:%M')}) "
                        f"开盘价已更新: {old_open_price} -> {minute_bar.open_price} "
                        f"(来自{minute_bar.datetime.strftime('%H:%M')}分钟K线)"
                    )
                    
                    # 更新历史数据中的当前K线
                    if self._current_bar_index >= 0 and self._current_bar_index < len(self.history_data):
                        self.history_data[self._current_bar_index] = self._current_bar
                    
                    # 更新图表显示
                    self.chart.update_bar(self._current_bar)
    
    def process_history_data(self, history: list) -> None:
        """处理历史数据"""
        if not history:
            self.status_label.setText(_("未找到历史数据，等待实时行情..."))
            self.history_loaded = True
            return
        
        # 确保是当前合约的数据
        first_bar = history[0]
        if first_bar.vt_symbol != self.current_vt_symbol:
            return
        
        # 获取当前周期
        interval_enum = self._get_interval_enum()
        from vnpy.trader.constant import Interval
        
        # 尝试检测并填充数据缺口（所有周期都检测）
        self.status_label.setText(_("正在检测数据缺口并补齐..."))
        history = self._detect_and_fill_gap(
            history,
            self.current_vt_symbol,
            interval_enum
        )
        
        # 缓存历史数据
        self.history_data = list(history)
        
        # 先标记最后一根K线是否为当前未完成的K线（在修正之前）
        # 这样可以在修正时跳过正在进行的K线，避免错误修正
        self._mark_current_bar(self.history_data, interval_enum)
        
        # 修正所有已完成K线的开盘价（使用该周期第一根分钟K线的开盘价）
        # 这对于从数据库加载的历史数据很重要，因为历史数据中的开盘价可能不正确
        # 注意：修正会直接修改self.history_data中的K线对象，但会跳过正在进行的K线
        self._correct_all_bars_open_price(self.history_data, interval_enum)
        
        # 如果标记了当前K线，需要确保开盘价正确（使用第一根分钟K线的开盘价）
        # 这必须在更新图表之前完成
        if hasattr(self, '_current_bar') and self._current_bar:
            # 更新历史数据中的当前K线（如果开盘价被修正了）
            if self._current_bar_index >= 0 and self._current_bar_index < len(self.history_data):
                self.history_data[self._current_bar_index] = self._current_bar
        
        # 先设置未来空间，再更新历史数据
        future_bars = self._get_future_bars()
        self.chart.set_future_bars(future_bars)
        
        # 更新图表（使用修正后的历史数据）
        self.chart.update_history(self.history_data)
        self.history_loaded = True
        
        # 更新时间范围标签
        if history:
            start_time = history[0].datetime.strftime("%m-%d %H:%M")
            end_time = history[-1].datetime.strftime("%m-%d %H:%M")
            self.time_start_label.setText(start_time)
            self.time_end_label.setText(end_time)
        
        # 更新状态（显示周期和数据源）
        interval_name = self.interval_combo.currentText()
        source_name = self.datasource_combo.currentText()
        
        # 检查是否有当前未完成的K线
        current_bar_info = ""
        if hasattr(self, '_current_bar') and self._current_bar:
            current_bar_info = _(" | 当前K线进行中")
        
        # 检查是否有数据缺口
        gap_warning = ""
        if hasattr(self, '_has_data_gap') and self._has_data_gap:
            gap_warning = _(" | ⚠️数据有缺口")
            # 设置状态标签为警告颜色
            self.status_label.setStyleSheet("color: #ff6600; font-size: 12px;")
        else:
            self.status_label.setStyleSheet("color: #888; font-size: 12px;")
        
        self.status_label.setText(
            _("{} | {} | {} | {} 根K线{}{}").format(
                self.current_vt_symbol,
                interval_name,
                source_name,
                len(history),
                current_bar_info,
                gap_warning
            )
        )
        
        # 如果有数据缺口，显示详细提示
        if hasattr(self, '_has_data_gap') and self._has_data_gap and hasattr(self, '_gap_info'):
            self.status_label.setToolTip(
                _("数据缺口: {}\n\n如需补齐，请先到数据管理器下载1分钟数据").format(self._gap_info)
            )
        else:
            self.status_label.setToolTip("")
        
        # 确保滚动条在最右边
        self.time_slider.setValue(100)
    
    def _mark_current_bar(self, history: list, interval: "Interval") -> None:
        """
        标记当前未完成的K线
        
        检查最后一根K线是否属于当前正在进行的周期，
        如果是，则标记为当前K线，用于后续tick更新。
        
        成交量处理：
        - 标记现有K线时，记录该K线已有的成交量作为"历史成交量"
        - 后续tick更新时，需要在历史成交量基础上累加
        """
        from datetime import datetime
        from vnpy.trader.constant import Interval
        from vnpy.trader.utility import ZoneInfo
        from tzlocal import get_localzone_name
        
        self._current_bar = None
        self._current_bar_period = None
        self._current_bar_index = -1
        self._period_start_volume = 0
        self._period_start_turnover = 0
        # 标记已有的历史成交量（来自加载的数据）
        self._bar_historical_volume = 0
        self._bar_historical_turnover = 0
        # 标记是否需要在第一个tick时初始化基准
        self._need_init_baseline = True
        
        if not history or interval == Interval.MINUTE:
            return
        
        try:
            # 获取当前时间
            local_tz = ZoneInfo(get_localzone_name())
            now = datetime.now(local_tz)
            
            # 获取当前时间应该属于的周期
            from vnpy.trader.utility import extract_vt_symbol
            _, exchange = extract_vt_symbol(self.current_vt_symbol)
            current_period = get_period_start(now, interval, exchange)
            
            if current_period is None:
                return
            
            # 检查最后一根K线是否属于当前周期
            last_bar = history[-1]
            last_bar_period = get_period_start(last_bar.datetime, interval, exchange)
            
            if last_bar_period == current_period:
                # 最后一根K线是当前未完成的K线
                self._current_bar = last_bar
                self._current_bar_period = current_period
                self._current_bar_index = len(history) - 1
                
                # 记录历史成交量（来自加载的数据，需要在tick更新时累加）
                self._bar_historical_volume = last_bar.volume if last_bar.volume else 0
                self._bar_historical_turnover = last_bar.turnover if last_bar.turnover else 0
                
                # 检查并更新开盘价（使用该周期第一根分钟K线的开盘价）
                # 因为历史数据中的开盘价可能不正确（可能是从tick价格生成的）
                self._update_current_bar_open_price()
                
                self.main_engine.write_log(
                    f"[当前K线] 标记当前未完成K线: {current_period.strftime('%m-%d %H:%M')}, "
                    f"已有成交量: {self._bar_historical_volume}, "
                    f"开盘价: {self._current_bar.open_price}"
                )
            else:
                # 需要创建一个新的当前K线
                # 这种情况下，最后一根历史K线是完整的，当前周期还没有K线
                pass
                
        except Exception as e:
            error_msg = str(e).replace("{", "{{").replace("}", "}}")
            self.main_engine.write_log(f"[当前K线] 标记失败: {error_msg}")
    
    def _correct_all_bars_open_price(self, history: list, interval: "Interval") -> None:
        """
        修正所有K线的开盘价（使用该周期第一根分钟K线的开盘价）
        
        对于从数据库加载的历史数据，开盘价可能不正确（可能是从tick价格生成的），
        需要重新从第一根分钟K线获取正确的开盘价。
        """
        from vnpy.trader.constant import Interval
        
        # 只处理大周期（5分钟、1小时、4小时）
        if interval == Interval.MINUTE:
            return
        
        try:
            corrected_count = 0
            
            # 检查是否有正在进行的当前K线，如果有则跳过它
            current_bar_index = getattr(self, '_current_bar_index', -1)
            current_bar_period = getattr(self, '_current_bar_period', None)
            
            for i, bar in enumerate(history):
                # 跳过正在进行的当前K线（它的开盘价应该在实时更新时处理，或者在标记时已经更新）
                if i == current_bar_index and current_bar_period is not None:
                    from vnpy.trader.period_utils import get_period_start
                    from vnpy.trader.utility import extract_vt_symbol
                    _, exchange = extract_vt_symbol(bar.vt_symbol)
                    bar_period = get_period_start(bar.datetime, bar.interval, exchange)
                    if bar_period == current_bar_period:
                        # 这是正在进行的当前K线，跳过修正（开盘价应该在实时更新时处理）
                        bar_dt_str = bar.datetime.strftime('%Y-%m-%d %H:%M:%S')
                        print(f"[DEBUG] _correct_all_bars_open_price: - 跳过正在进行的当前K线 | bar_dt={bar_dt_str}, 开盘价={bar.open_price}, 当前K线开盘价将在实时更新时处理")
                        continue
                
                # 获取该周期第一根分钟K线的开盘价
                from vnpy.trader.object import TickData
                temp_tick = TickData(
                    symbol=bar.symbol,
                    exchange=bar.exchange,
                    datetime=bar.datetime,
                    last_price=bar.close_price,
                    gateway_name=bar.gateway_name
                )
                
                from vnpy.trader.utility import extract_vt_symbol
                from vnpy.trader.period_utils import get_period_start
                _, exchange = extract_vt_symbol(bar.vt_symbol)
                
                # 获取该K线的周期起始时间（重要：不能直接使用bar.datetime）
                period_start = get_period_start(bar.datetime, bar.interval, exchange)
                if period_start is None:
                    # 无法确定周期起始时间，跳过
                    continue
                
                bar_dt_str = bar.datetime.strftime('%Y-%m-%d %H:%M:%S')
                period_start_str = period_start.strftime('%Y-%m-%d %H:%M:%S')
                print(f"[DEBUG] _correct_all_bars_open_price: 开始修正 | bar_dt={bar_dt_str}, period_start={period_start_str}, interval={bar.interval.value}, current_open_price={bar.open_price}, current_close_price={bar.close_price}")
                
                correct_open_price = self.open_price_helper.get_period_open_price(
                    period_start,  # 使用周期起始时间，而不是bar.datetime
                    bar.interval,
                    bar.vt_symbol,
                    tick=temp_tick,
                    minute_bar_generator=self.bg,
                    history_data=self.history_data
                )
                
                print(f"[DEBUG] _correct_all_bars_open_price: 获取到的开盘价 | correct_open_price={correct_open_price}, correct_open_price_time={period_start_str}, current_open_price={bar.open_price}, 是否不同={bar.open_price != correct_open_price if correct_open_price else 'N/A'}")
                
                # 如果无法获取correct_open_price，说明该周期第一根1分钟K线可能不存在
                # 此时不应该修正，因为current_open_price可能已经是正确的（来自DataManager的合成逻辑）
                if not correct_open_price or correct_open_price <= 0:
                    print(f"[DEBUG] _correct_all_bars_open_price: ✗ 无法获取开盘价，跳过修正 | bar_dt={bar_dt_str}, correct_open_price={correct_open_price}, 保持current_open_price={bar.open_price}")
                    continue
                
                # 如果获取到了正确的开盘价，且与当前开盘价不同，则更新
                if bar.open_price != correct_open_price:
                    old_open_price = bar.open_price
                    price_diff = abs(old_open_price - correct_open_price)
                    
                    # 检查：如果correct_open_price来自该周期内第二根或更后的1分钟K线，
                    # 而current_open_price已经正确，则不应该修正
                    # 这里通过比较差异来判断：如果差异很小（<1.0），可能是数据精度问题，不应该修正
                    # 或者，如果无法找到period_start对应的1分钟K线，说明它不存在，应该保持current_open_price
                    print(f"[DEBUG] _correct_all_bars_open_price: 价格差异 | old_open={old_open_price}, new_open={correct_open_price}, 差异={price_diff}")
                    
                    bar.open_price = correct_open_price
                    self.history_data[i] = bar
                    corrected_count += 1
                    
                    print(f"[DEBUG] _correct_all_bars_open_price: ✓ 执行修正 | bar_dt={bar_dt_str}, old_open={old_open_price} -> new_open={correct_open_price}, 差异={price_diff}")
                    
                    self.main_engine.write_log(
                        f"[开盘价修正] {bar.interval.value}K线({bar.datetime.strftime('%H:%M')}) "
                        f"开盘价已修正: {old_open_price} -> {correct_open_price}"
                    )
                else:
                    print(f"[DEBUG] _correct_all_bars_open_price: - 无需修正 | bar_dt={bar_dt_str}, open_price={bar.open_price} == correct_open_price={correct_open_price}")
            
            if corrected_count > 0:
                self.main_engine.write_log(
                    f"[开盘价修正] 共修正了 {corrected_count} 根K线的开盘价"
                )
        except Exception as e:
            error_msg = str(e).replace("{", "{{").replace("}", "}}")
            self.main_engine.write_log(f"[开盘价修正] 批量修正失败: {error_msg}")
    
    def _update_current_bar_open_price(self) -> None:
        """
        更新当前K线的开盘价（使用该周期第一根分钟K线的开盘价）
        
        当从历史数据中标记当前K线时，需要检查并更新开盘价，
        因为历史数据中的开盘价可能不正确（可能是从tick价格生成的）。
        """
        if not hasattr(self, '_current_bar') or self._current_bar is None:
            return
        
        from vnpy.trader.constant import Interval
        
        # 只处理大周期（5分钟、1小时、4小时）
        if self._current_bar.interval == Interval.MINUTE:
            return
        
        try:
            # 获取该周期第一根分钟K线的开盘价
            # 创建一个临时的tick对象用于查询
            from vnpy.trader.object import TickData
            temp_tick = TickData(
                symbol=self._current_bar.symbol,
                exchange=self._current_bar.exchange,
                datetime=self._current_bar.datetime,
                last_price=self._current_bar.close_price,
                gateway_name=self._current_bar.gateway_name
            )
            
            from vnpy.trader.utility import extract_vt_symbol
            _, exchange = extract_vt_symbol(self._current_bar.vt_symbol)
            correct_open_price = self.open_price_helper.get_period_open_price(
                self._current_bar.datetime,
                self._current_bar.interval,
                self._current_bar.vt_symbol,
                tick=temp_tick,
                minute_bar_generator=self.bg,
                history_data=self.history_data
            )
            
            # 如果获取到了正确的开盘价，且与当前开盘价不同，则更新
            if (correct_open_price and correct_open_price > 0 and 
                self._current_bar.open_price != correct_open_price):
                old_open_price = self._current_bar.open_price
                self._current_bar.open_price = correct_open_price
                
                self.main_engine.write_log(
                    f"[开盘价修正] {self._current_bar.interval.value}K线({self._current_bar.datetime.strftime('%H:%M')}) "
                    f"开盘价已修正: {old_open_price} -> {correct_open_price} "
                    f"(从历史数据标记时修正)"
                )
                
                # 更新历史数据中的当前K线
                if self._current_bar_index >= 0 and self._current_bar_index < len(self.history_data):
                    self.history_data[self._current_bar_index] = self._current_bar
                
                # 更新图表显示
                if hasattr(self, 'chart') and self.chart:
                    self.chart.update_bar(self._current_bar)
        except Exception as e:
            error_msg = str(e).replace("{", "{{").replace("}", "}}")
            self.main_engine.write_log(f"[开盘价修正] 更新失败: {error_msg}")
    
    def extend_chart_x_limit(self, move_to_end: bool = False) -> None:
        """扩展图表的x轴限制，允许显示未来空间"""
        # 根据当前周期获取未来空间K线数量
        future_bars = self._get_future_bars()
        
        # 使用ChartWidget的新方法设置未来空间
        self.chart.set_future_bars(future_bars)
        
        # 如果需要移动到扩展后的末尾
        if move_to_end and self.history_data:
            total_bars = len(self.history_data)
            max_x = total_bars + future_bars
            self.chart._right_ix = max_x
            self.chart._update_x_range()
    
    def load_default_symbol(self) -> None:
        """加载默认合约数据"""
        self.symbol_line.setText(self.DEFAULT_SYMBOL)
        self.switch_chart()
    
    def set_symbol(self, vt_symbol: str) -> None:
        """外部设置合约代码"""
        self.symbol_line.setText(vt_symbol)
        self.switch_chart()
    
    def show(self) -> None:
        """显示窗口"""
        super().show()
        self.activateWindow()
        self.raise_()
        self.raise_()
