"""
Basic widgets for UI.
"""

import csv
import platform
import time
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
    EVENT_LOG,
    EVENT_CONTRACT
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

            # 确保父窗口已显示
            if not parent.isVisible():
                parent.show()

            # 水平居中
            x = parent_rect.x() + (parent_rect.width() - self.width()) // 2

            if position == "center":
                # 屏幕中央
                y = parent_rect.y() + (parent_rect.height() - self.height()) // 2
            else:
                # 顶部（紧贴标题栏下方，不遮挡内容）
                y = parent_rect.y() + 35  # 紧贴标题栏

            self.move(x, y)
        else:
            # 如果没有父窗口，使用屏幕坐标
            from PySide6 import QtWidgets
            screen = QtWidgets.QApplication.primaryScreen().geometry()
            x = (screen.width() - self.width()) // 2
            if position == "center":
                y = (screen.height() - self.height()) // 2
            else:
                y = 50  # 顶部
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


class CommissionCell(BaseCell):
    """
    Cell used for showing commission/fee data from TradeData.extra field.
    """

    def __init__(self, content: Any, data: Any) -> None:
        """"""
        # content参数会被忽略，因为我们从data.extra中读取
        super().__init__("", data)
        self.set_content(content, data)

    def set_content(self, content: Any, data: Any) -> None:
        """
        Extract commission and fee from data.extra field.
        If not found, display "无".
        """
        if not hasattr(data, 'extra') or data.extra is None:
            self.setText("无")
            return

        # 尝试从extra中获取费用信息
        commission = data.extra.get("commission", 0)
        fee = data.extra.get("fee", 0)
        cost = data.extra.get("cost", 0)

        # 优先使用commission，其次fee，最后cost
        total_fee = 0
        if commission:
            total_fee = float(commission)
        elif fee:
            total_fee = float(fee)
        elif cost:
            total_fee = float(cost)

        # 如果都没有，尝试中文字段
        if total_fee == 0:
            commission_cn = data.extra.get("佣金", 0)
            fee_cn = data.extra.get("费用", 0)
            cost_cn = data.extra.get("手续费", 0)

            if commission_cn:
                total_fee = float(commission_cn)
            elif fee_cn:
                total_fee = float(fee_cn)
            elif cost_cn:
                total_fee = float(cost_cn)

        if total_fee > 0:
            # 格式化显示，保留2位小数
            self.setText(f"{total_fee:.2f}")
        else:
            self.setText("无")


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

            # 特殊处理：如果header是"commission"且使用CommissionCell，从extra字段读取
            if header == "commission" and setting["cell"] == CommissionCell:
                content = None  # CommissionCell会从data.extra中读取，content参数会被忽略
            else:
                # 尝试获取属性，如果不存在则使用getattr的默认值
                try:
                    content = data.__getattribute__(header)
                except AttributeError:
                    # 如果属性不存在，尝试从extra字段获取
                    if hasattr(data, 'extra') and data.extra and header in data.extra:
                        content = data.extra[header]
                    else:
                        content = None

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
            # 特殊处理：如果header是"commission"且使用CommissionCell，从extra字段读取
            if header == "commission" and isinstance(cell, CommissionCell):
                content = None  # CommissionCell会从data.extra中读取，content参数会被忽略
            else:
                # 尝试获取属性
                try:
                    content = data.__getattribute__(header)
                except AttributeError:
                    # 如果属性不存在，尝试从extra字段获取
                    if hasattr(data, 'extra') and data.extra and header in data.extra:
                        content = data.extra[header]
                    else:
                        content = None
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
        "commission": {"display": _("佣金手续费"), "cell": CommissionCell, "update": False},
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

        # 设置默认交易所为HKFE
        hkfe_index = -1
        for i, exchange in enumerate(exchanges):
            if exchange == Exchange.HKFE:
                hkfe_index = i
                break
        if hkfe_index >= 0:
            self.exchange_combo.setCurrentIndex(hkfe_index)

        self.symbol_line: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        # 设置默认合约名为MHImain
        self.symbol_line.setText("MHImain")
        self.symbol_line.returnPressed.connect(self.set_vt_symbol)

        self.name_line: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        self.name_line.setReadOnly(True)

        self.direction_combo: QtWidgets.QComboBox = QtWidgets.QComboBox()
        self.direction_combo.addItems(
            [Direction.LONG.value, Direction.SHORT.value])

        self.offset_combo: QtWidgets.QComboBox = QtWidgets.QComboBox()
        self.offset_combo.addItems([offset.value for offset in Offset])

        self.order_type_combo: QtWidgets.QComboBox = QtWidgets.QComboBox()
        order_types = [order_type.value for order_type in OrderType]
        self.order_type_combo.addItems(order_types)

        # 设置默认订单类型为对手价
        opponent_index = -1
        for i, order_type in enumerate(OrderType):
            if order_type == OrderType.OPPONENT:
                opponent_index = i
                break
        if opponent_index >= 0:
            self.order_type_combo.setCurrentIndex(opponent_index)

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

        # 初始化完成后，设置默认订单类型对应的价格框状态
        # 由于信号连接在设置默认值之后，需要手动调用一次
        current_order_type = str(self.order_type_combo.currentText())
        self.on_order_type_changed(current_order_type)

        # 如果默认合约已设置，尝试加载合约信息
        if self.symbol_line.text():
            # 使用QTimer延迟执行，确保UI完全初始化后再调用
            # QtCore已在文件顶部导入，直接使用
            QtCore.QTimer.singleShot(100, self.set_vt_symbol)

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
        # ✅ 注册合约事件，当合约信息加载后自动更新名称
        self.event_engine.register(EVENT_CONTRACT, self.process_contract_event)

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
            # ✅ 如果合约不存在，尝试通过主力合约映射查找实际合约
            # 例如：MHImain.HKFE -> MHI2512.HKFE
            actual_contract = None
            symbol_part = vt_symbol.split('.')[0] if '.' in vt_symbol else vt_symbol
            exchange_part = exchange_value

            # 尝试从所有gateway查找主力合约映射
            for gateway_name in self.main_engine.get_all_gateway_names():
                gateway = self.main_engine.get_gateway(gateway_name)
                if gateway and hasattr(gateway, 'get_main_contract_mapping'):
                    mapping = gateway.get_main_contract_mapping()
                    for main_symbol, actual_symbol in mapping.items():
                        if main_symbol == symbol_part:
                            # 找到了映射，尝试获取实际合约
                            actual_vt_symbol = f"{actual_symbol}.{exchange_part}"
                            actual_contract = self.main_engine.get_contract(actual_vt_symbol)
                            if actual_contract:
                                # 使用实际合约的信息，但保持主力合约代码显示
                                self.name_line.setText(actual_contract.name)
                                gateway_name = actual_contract.gateway_name
                                # Update gateway combo box.
                                ix: int = self.gateway_combo.findText(gateway_name)
                                if ix >= 0:
                                    self.gateway_combo.setCurrentIndex(ix)
                                # Update price digits
                                self.price_digits = get_digits(actual_contract.pricetick)
                                break
                    if actual_contract:
                        break

            # 如果仍然没有找到合约
            if not actual_contract:
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

    def process_contract_event(self, event: Event) -> None:
        """
        处理合约信息更新事件，如果当前设置的合约代码匹配，自动更新名称。
        """
        from ..object import ContractData
        from ..utility import get_digits
        contract: ContractData = event.data

        # 检查是否是当前设置的合约
        symbol: str = str(self.symbol_line.text())
        if not symbol:
            return

        exchange_value: str = str(self.exchange_combo.currentText())
        vt_symbol: str = f"{symbol}.{exchange_value}"

        # 直接匹配
        if contract.vt_symbol == vt_symbol:
            self.name_line.setText(contract.name)
            # 更新gateway combo box
            ix: int = self.gateway_combo.findText(contract.gateway_name)
            if ix >= 0:
                self.gateway_combo.setCurrentIndex(ix)
            # 更新价格精度
            self.price_digits = get_digits(contract.pricetick)
            return

        # 主力合约映射匹配：当前是主力合约，合约信息是实际合约
        symbol_part = vt_symbol.split('.')[0] if '.' in vt_symbol else vt_symbol
        contract_symbol_part = contract.vt_symbol.split('.')[0] if '.' in contract.vt_symbol else contract.vt_symbol

        # 尝试从所有gateway查找主力合约映射
        for gateway_name in self.main_engine.get_all_gateway_names():
            gateway = self.main_engine.get_gateway(gateway_name)
            if gateway and hasattr(gateway, 'get_main_contract_mapping'):
                mapping = gateway.get_main_contract_mapping()
                # 检查是否是主力合约映射关系
                for main_symbol, actual_symbol in mapping.items():
                    if main_symbol == symbol_part and actual_symbol == contract_symbol_part:
                        # 找到映射，更新名称
                        self.name_line.setText(contract.name)
                        # 更新gateway combo box
                        ix: int = self.gateway_combo.findText(contract.gateway_name)
                        if ix >= 0:
                            self.gateway_combo.setCurrentIndex(ix)
                        # 更新价格精度
                        self.price_digits = get_digits(contract.pricetick)
                        return

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


class MultiTimeframeLoadProgressDialog(QtWidgets.QDialog):
    """
    多周期数据加载进度对话框（借鉴 DataManager 设计）
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("多周期数据加载")
        self.setFixedSize(500, 300)
        self.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        
        # 进度条
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        
        # 当前状态标签
        self.status_label = QtWidgets.QLabel("准备加载多周期数据...")
        self.status_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        
        # 消息列表
        self.message_list = QtWidgets.QTextEdit()
        self.message_list.setReadOnly(True)
        self.message_list.setStyleSheet(
            "font-family: 'Consolas', 'Monaco', monospace; "
            "font-size: 10px; "
            "background-color: #1e1e1e; "
            "color: #d4d4d4;"
        )
        
        # 布局
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(QtWidgets.QLabel("加载详情:"))
        layout.addWidget(self.message_list)
        self.setLayout(layout)
        
        self.append_message("开始加载多周期数据...")
    
    def set_status(self, status: str):
        """设置当前状态"""
        self.status_label.setText(status)
        self.append_message(status)
        QtWidgets.QApplication.processEvents()
    
    def set_progress(self, value: int):
        """设置进度值 (0-100)"""
        self.progress_bar.setValue(value)
        QtWidgets.QApplication.processEvents()
    
    def append_message(self, msg: str):
        """追加消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.message_list.append(f"[{timestamp}] {msg}")
        scrollbar = self.message_list.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        QtWidgets.QApplication.processEvents()
    
    def set_completed(self):
        """设置为完成状态"""
        self.status_label.setText("✅ 加载完成！")
        self.status_label.setStyleSheet("font-weight: bold; font-size: 12px; color: green;")
        self.append_message("多周期数据加载完成！")
    
    def set_error(self, error_msg: str):
        """设置为错误状态"""
        self.status_label.setText("❌ 加载失败")
        self.status_label.setStyleSheet("font-weight: bold; font-size: 12px; color: red;")
        self.append_message(f"错误: {error_msg}")


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

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        """
        Handle key press events at window level.

        - ESC: Disable drawing order mode
        """
        if event.key() == QtCore.Qt.Key.Key_Escape:
            # Disable drawing order mode when ESC is pressed
            if (self.chart and
                self.chart.get_drawing_order_controller() and
                self.chart.get_drawing_order_controller().is_enabled()):
                # 禁用画线下单模式
                self.drawing_mode_button.setChecked(False)
                self.toggle_drawing_mode()
                event.accept()
                return

        super().keyPressEvent(event)

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
    signal_update_data_complete: QtCore.Signal = QtCore.Signal(bool, str)  # (success, message)

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
        self.bg: BarGenerator = None

        # 图表组件
        self.chart: ChartWidget = None

        # 显示模式：单周期或多周期叠加
        self.display_mode: str = "single"  # "single" 或 "multi"

        # 多周期Widget实例（延迟初始化，在init_ui中创建）
        self.multi_timeframe_widget = None  # type: Optional[MultiTimeframeWidget]

        # 历史数据加载状态
        self.history_loaded: bool = False

        # 历史数据缓存（用于滚动条）
        self.history_data: list = []

        # 开盘价获取辅助类（复用通用工具模块）
        self.open_price_helper: PeriodOpenPriceHelper = PeriodOpenPriceHelper()

        # 当前未完成的K线（用于大周期实时更新）
        self._current_bar: BarData = None
        self._current_bar_period: datetime = None
        self._current_bar_index: int = -1

        # 周期开始时的基准成交量（用于计算周期内成交量）
        self._period_start_volume: float = 0
        self._period_start_turnover: float = 0

        # 数据缺口状态
        self._has_data_gap: bool = False
        self._gap_info: str = ""

        # Query cache for open prices (reduces database and Datafeed queries)
        # Format: (symbol: str, datetime: datetime) -> (open_price: float, timestamp: float)
        self._open_price_cache: dict[tuple[str, datetime], tuple[float, float]] = {}
        self._cache_ttl: int = 60  # Cache TTL: 60 seconds
        self._cache_max_size: int = 1000  # Maximum cache size: 1000 entries

        # 注意：不再需要 _cached_datafeed，因为使用全局单例 DatafeedManager
        # Datafeed 连接现在由 DatafeedManager 管理，程序退出时自动关闭

        # Performance monitoring (optional, enabled via configuration)
        from vnpy.trader.setting import SETTINGS
        self._perf_monitoring_enabled: bool = SETTINGS.get("chart.performance_monitoring", False)
        self._perf_stats: dict = {
            "tick_update": {
                "count": 0,
                "total_time_ms": 0.0,
                "min_time_ms": float('inf'),
                "max_time_ms": 0.0,
                "last_time_ms": 0.0,
                "last_log_time": 0.0
            },
            "chart_refresh": {
                "count": 0,
                "total_time_ms": 0.0,
                "min_time_ms": float('inf'),
                "max_time_ms": 0.0,
                "last_time_ms": 0.0,
                "last_log_time": 0.0
            },
            "price_breakthrough": {
                "count": 0,
                "total_time_ms": 0.0,
                "min_time_ms": float('inf'),
                "max_time_ms": 0.0,
                "last_time_ms": 0.0,
                "last_log_time": 0.0
            }
        }
        self._perf_log_interval: float = 60.0  # 每60秒记录一次性能统计

        # 创建 MultiTimeframeWidget 实例（延迟加载数据，在模式切换时再加载）
        # 使用默认值创建，后续在切换模式或合约时会更新
        try:
            from vnpy.chart.multi_timeframe_widget import MultiTimeframeWidget
            from vnpy.trader.utility import extract_vt_symbol
            from datetime import timedelta

            # 使用默认值创建（后续会在切换模式时更新）
            default_vt_symbol = self.DEFAULT_SYMBOL if self.DEFAULT_SYMBOL else "MHImain.HKFE"
            symbol, exchange = extract_vt_symbol(default_vt_symbol)
            end = datetime.now()
            start = end - timedelta(days=7)  # 默认加载最近7天数据

            self.multi_timeframe_widget = MultiTimeframeWidget(
                vt_symbol=default_vt_symbol,
                exchange=exchange,
                start=start,
                end=end,
                parent=self
            )
            # 初始状态隐藏（在init_ui中添加到布局后会再次设置）
            self.multi_timeframe_widget.setVisible(False)
        except Exception as e:
            # 如果创建失败，记录日志但不阻止初始化
            self.main_engine.write_log(
                f"[ChartWindow] 创建 MultiTimeframeWidget 失败: {e}",
                "ChartWindow"
            )
            self.multi_timeframe_widget = None

        self.init_ui()
        self.register_event()
        # 连接更新数据完成信号槽（在主线程中）
        self.signal_update_data_complete.connect(self._on_update_data_complete)

        # 默认加载合约数据（必须在init_ui()之后调用，因为需要symbol_line组件）
        self.load_default_symbol()

    def _get_cached_open_price(self, symbol: str, bar_datetime: datetime) -> float | None:
        """
        Get cached open price for a symbol and bar datetime.
        
        This method implements a TTL-based cache (60 seconds) to reduce
        redundant database and Datafeed queries for open prices.
        
        Args:
            symbol: Contract symbol
            bar_datetime: Bar datetime
            
        Returns:
            Cached open price if available and not expired, None otherwise
        """
        cache_key = (symbol, bar_datetime)
        if cache_key in self._open_price_cache:
            price, timestamp = self._open_price_cache[cache_key]
            current_time = time.time()
            if current_time - timestamp < self._cache_ttl:
                return price  # ✅ 缓存有效
            else:
                # 缓存过期，删除
                del self._open_price_cache[cache_key]
        return None

    def _set_cached_open_price(self, symbol: str, bar_datetime: datetime, price: float) -> None:
        """
        Set cached open price for a symbol and bar datetime.
        
        This method automatically cleans up expired cache entries when
        the cache size exceeds the limit (1000 entries).
        
        Args:
            symbol: Contract symbol
            bar_datetime: Bar datetime
            price: Open price to cache
        """
        cache_key = (symbol, bar_datetime)
        self._open_price_cache[cache_key] = (price, time.time())

        # 如果缓存大小超过限制，清理过期缓存
        if len(self._open_price_cache) > self._cache_max_size:
            self._clean_expired_cache()

    def _clean_expired_cache(self) -> None:
        """
        Clean up expired cache entries.
        
        Removes all cache entries that have exceeded the TTL (60 seconds).
        This method is called automatically when the cache size exceeds
        the maximum limit (1000 entries).
        """
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self._open_price_cache.items()
            if current_time - timestamp >= self._cache_ttl
        ]
        for key in expired_keys:
            del self._open_price_cache[key]

    def _get_datafeed(self, show_error_dialog: bool = False, check_health: bool = False):
        """
        Get global singleton Datafeed instance.
        
        使用全局单例 DatafeedManager，确保整个程序只有一个 Datafeed 连接。
        这解决了多个 ChartWindow 创建重复连接导致超过 128 连接限制的问题。
        
        Args:
            show_error_dialog: 是否在首次失败时显示错误对话框
            check_health: 是否检查连接健康状态（用于运行时断开检测）
        
        Returns:
            Datafeed instance if available, None otherwise
        """
        try:
            from vnpy.trader.datafeed_manager import get_global_datafeed, _datafeed_manager

            # 如果需要检查健康状态（运行时断开检测）
            if check_health:
                _datafeed_manager.check_connection_health(
                    write_log=self.main_engine.write_log,
                    show_error_dialog=show_error_dialog
                )

            # 使用全局单例 Datafeed
            datafeed = get_global_datafeed(
                write_log=self.main_engine.write_log,
                show_error_dialog=show_error_dialog
            )

            return datafeed

        except Exception as e:
            # 记录错误但不抛出异常
            if self.main_engine:
                self.main_engine.write_log(
                    f"[ChartWindow-{id(self)}] 获取全局Datafeed失败: {e}"
                )
            return None

    def _get_connection_count(self) -> dict[str, int] | None:
        """
        Get connection count statistics.
        
        Returns connection count for Datafeed and database connections.
        Note: Database connection count is usually not directly available
        as most database drivers use connection pools.
        
        Returns:
            Dictionary with connection counts: {"database": count, "datafeed": count},
            or None if unable to retrieve
        """
        try:
            result = {}

            # Datafeed连接数：检查缓存的Datafeed实例
            datafeed_count = 0
            if self._cached_datafeed is not None:
                datafeed_count = 1
            result["datafeed"] = datafeed_count

            # 数据库连接数：尝试从数据库获取（如果支持）
            # 注意：大多数数据库驱动使用连接池，无法直接获取连接数
            # 这里只返回Datafeed连接数
            result["database"] = None  # 数据库连接数通常无法直接获取

            return result
        except Exception:
            return None

    def _log_connection_count(self) -> None:
        """
        Log connection count statistics.
        
        Periodically logs connection counts to help diagnose connection leaks.
        Issues a warning when connection count approaches the limit (90% threshold
        for Futu OpenAPI's 128 connection limit).
        """
        try:
            connection_count = self._get_connection_count()
            if connection_count:
                datafeed_count = connection_count.get("datafeed", 0)
                database_count = connection_count.get("database", "N/A")

                # 检查是否接近限制（Futu OpenAPI限制为128）
                futu_limit = 128
                if datafeed_count is not None and datafeed_count > 0:
                    if datafeed_count >= futu_limit * 0.9:  # 90%阈值
                        warning_msg = (
                            f"[ChartWindow] ⚠️ 警告：Datafeed连接数接近限制！"
                            f"当前: {datafeed_count}/{futu_limit}"
                        )
                        if self.main_engine:
                            self.main_engine.write_log(warning_msg)
                    else:
                        info_msg = (
                            f"[ChartWindow] 连接数统计 - "
                            f"Datafeed: {datafeed_count}, Database: {database_count}"
                        )
                        if self.main_engine:
                            self.main_engine.write_log(info_msg)
        except Exception as e:
            # 记录连接数失败，不影响主流程
            if self.main_engine:
                self.main_engine.write_log(
                    f"[ChartWindow] 记录连接数失败: {e}"
                )

    def _check_connection_count_before_create(self) -> bool:
        """
        Check connection count before creating new connection.
        
        This method checks if the connection count is approaching the limit
        (80% threshold for Futu OpenAPI's 128 connection limit) and issues
        a warning if so. Still allows connection creation but logs a warning.
        
        Returns:
            True if connection can be created, False if approaching limit
        """
        try:
            connection_count = self._get_connection_count()
            if connection_count:
                datafeed_count = connection_count.get("datafeed", 0)
                futu_limit = 128

                # 如果Datafeed连接数接近限制，发出警告
                if datafeed_count is not None and datafeed_count >= futu_limit * 0.8:  # 80%阈值
                    if self.main_engine:
                        self.main_engine.write_log(
                            f"[ChartWindow] ⚠️ 警告：Datafeed连接数较高 ({datafeed_count}/{futu_limit})，"
                            f"建议复用现有连接",
                            "ChartWindow"
                        )
                    # 仍然允许创建，但发出警告
                    return True
            return True
        except Exception:
            # 检查失败，允许创建（保守策略）
            return True

    def _record_performance_metric(self, metric_name: str, latency_ms: float) -> None:
        """
        Performance monitoring helper method - unified performance metrics logging

        Args:
            metric_name: 指标名称（"tick_update", "chart_refresh", "price_breakthrough"）
            latency_ms: 延迟时间（毫秒）
        """
        if not self._perf_monitoring_enabled:
            return

        # 确保统计项存在
        if metric_name not in self._perf_stats:
            self._perf_stats[metric_name] = {
                "count": 0,
                "total_time_ms": 0.0,
                "min_time_ms": float('inf'),
                "max_time_ms": 0.0,
                "last_time_ms": 0.0,
                "last_log_time": 0.0
            }

        # 更新统计信息
        stats = self._perf_stats[metric_name]
        stats["count"] += 1
        stats["total_time_ms"] += latency_ms
        stats["min_time_ms"] = min(stats["min_time_ms"], latency_ms)
        stats["max_time_ms"] = max(stats["max_time_ms"], latency_ms)
        stats["last_time_ms"] = latency_ms

        # 定期输出性能统计（每60秒）
        current_time = time.time()
        if current_time - stats["last_log_time"] >= self._perf_log_interval:
            avg_time_ms = stats["total_time_ms"] / stats["count"] if stats["count"] > 0 else 0

            # 指标名称映射（用于日志显示）
            metric_display_names = {
                "tick_update": "Tick更新延迟",
                "chart_refresh": "图表刷新延迟",
                "price_breakthrough": "价格突破监控延迟"
            }
            display_name = metric_display_names.get(metric_name, metric_name)

            if self.main_engine:
                self.main_engine.write_log(
                    f"[ChartWindow] [性能监控] {display_name}: "
                    f"平均={avg_time_ms:.3f}ms, 最小={stats['min_time_ms']:.3f}ms, "
                    f"最大={stats['max_time_ms']:.3f}ms, 最新={latency_ms:.3f}ms, "
                    f"样本数={stats['count']}",
                    "ChartWindow"
                )
            stats["last_log_time"] = current_time

    def load_default_symbol(self) -> None:
        """加载默认合约"""
        if self.DEFAULT_SYMBOL:
            # 设置合约输入框的文本
            self.symbol_line.setText(self.DEFAULT_SYMBOL)
            # 切换到默认合约（会自动加载数据）
            self.switch_chart()

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
        # 设置默认合约
        self.symbol_line.setText(self.DEFAULT_SYMBOL)
        self.symbol_line.setPlaceholderText(_("输入合约代码，如 MHImain.HKFE"))
        self.symbol_line.returnPressed.connect(self.switch_chart)

        self.switch_button: QtWidgets.QPushButton = QtWidgets.QPushButton(_("切换"))
        self.switch_button.clicked.connect(self.switch_chart)

        # 画线交易功能按钮
        self.drawing_mode_button: QtWidgets.QPushButton = QtWidgets.QPushButton(_("画线下单"))
        self.drawing_mode_button.setCheckable(True)
        self.drawing_mode_button.clicked.connect(self.toggle_drawing_mode)
        self.drawing_mode_button.setToolTip(_("启用画线下单模式：在图表上点击价格位置创建订单"))

        # 模拟成交按钮（用于休市时测试挂单成交）
        self.simulate_trade_button: QtWidgets.QPushButton = QtWidgets.QPushButton(_("模拟成交"))
        self.simulate_trade_button.clicked.connect(self.simulate_trade_breakthrough)
        self.simulate_trade_button.setToolTip(_("模拟tick突破挂单线，触发挂单成交（用于休市测试）"))
        self.simulate_trade_button.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold;")

        # 模拟止损按钮（用于休市时测试止损触发）
        self.simulate_stop_loss_button: QtWidgets.QPushButton = QtWidgets.QPushButton(_("模拟止损"))
        self.simulate_stop_loss_button.clicked.connect(self.simulate_stop_loss)
        self.simulate_stop_loss_button.setToolTip(_("模拟tick触及止损线，触发平仓（用于休市测试）"))
        self.simulate_stop_loss_button.setStyleSheet("background-color: #F44336; color: white; font-weight: bold;")

        # 模拟止盈按钮（用于休市时测试止盈触发）
        self.simulate_take_profit_button: QtWidgets.QPushButton = QtWidgets.QPushButton(_("模拟止盈"))
        self.simulate_take_profit_button.clicked.connect(self.simulate_take_profit)
        self.simulate_take_profit_button.setToolTip(_("模拟tick触及止盈线，触发平仓（用于休市测试）"))
        self.simulate_take_profit_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")

        # 模拟功能开关状态（默认启用，用于控制三个模拟按钮）
        self._simulate_functions_enabled: bool = True

        # 注意：RLock保护逻辑在ChartWidget中实现，这里不需要重复定义
        # ChartWidget中的 _stop_loss_trigger_lock 和 _take_profit_trigger_lock
        # 保护的是"触发止损/止盈平仓"这个逻辑本身，无论是真实tickdata触发还是模拟触发

        # 显示模式选择下拉框
        self.mode_combo: QtWidgets.QComboBox = QtWidgets.QComboBox()
        self.mode_combo.addItem("单周期")
        self.mode_combo.addItem("多周期叠加")
        self.mode_combo.setCurrentText("单周期")
        self.mode_combo.setToolTip(_("选择显示模式：单周期或多周期叠加"))
        self.mode_combo.setFixedWidth(100)
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)

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

        # 更新数据按钮
        self.update_data_button: QtWidgets.QPushButton = QtWidgets.QPushButton(_("更新数据"))
        self.update_data_button.clicked.connect(self.update_history_data)
        self.update_data_button.setToolTip(_("从数据库已有数据的结束日期开始，下载截止到当前最新日期的1分钟K线数据并补齐大周期"))

        # 顶部布局 - 第一行：合约选择、模式、周期、数据源
        hbox1: QtWidgets.QHBoxLayout = QtWidgets.QHBoxLayout()
        hbox1.addWidget(QtWidgets.QLabel(_("合约:")))
        hbox1.addWidget(self.symbol_line, 1)
        hbox1.addWidget(QtWidgets.QLabel(_("模式:")))
        hbox1.addWidget(self.mode_combo)
        hbox1.addWidget(QtWidgets.QLabel(_("周期:")))
        hbox1.addWidget(self.interval_combo)
        hbox1.addWidget(QtWidgets.QLabel(_("数据源:")))
        hbox1.addWidget(self.datasource_combo)
        hbox1.addWidget(self.csv_button)
        hbox1.addWidget(self.csv_path_label)
        hbox1.addWidget(self.switch_button)
        hbox1.addWidget(self.drawing_mode_button)
        hbox1.addWidget(self.simulate_trade_button)
        hbox1.addWidget(self.simulate_stop_loss_button)
        hbox1.addWidget(self.simulate_take_profit_button)

        # 多周期设置按钮（T065）
        self.multi_timeframe_settings_button: QtWidgets.QPushButton = QtWidgets.QPushButton(_("多周期设置"))
        self.multi_timeframe_settings_button.clicked.connect(self.show_multi_timeframe_settings)
        self.multi_timeframe_settings_button.setToolTip(_("打开多周期K线显示设置对话框"))
        self.multi_timeframe_settings_button.setFixedWidth(100)
        self.multi_timeframe_settings_button.setVisible(False)  # 初始隐藏，只在多周期模式显示
        hbox1.addWidget(self.multi_timeframe_settings_button)

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
        hbox2.addSpacing(20)
        hbox2.addWidget(self.update_data_button)
        hbox2.addStretch()

        # 创建K线图表
        self.chart = ChartWidget()
        self.chart.add_plot("candle", hide_x_axis=True)
        self.chart.add_plot("volume", maximum_height=150)
        self.chart.add_item(CandleItem, "candle", "candle")
        self.chart.add_item(VolumeItem, "volume", "volume")
        self.chart.add_cursor()

        # 设置 MainEngine 和事件监听
        self.chart.set_main_engine(self.main_engine)

        # 设置画线模式点击回调
        self.chart.set_drawing_click_callback(self._on_drawing_click)

        # 设置画线模式状态变化回调（用于ESC键退出）
        self.chart.set_drawing_mode_changed_callback(self._on_drawing_mode_changed)

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
        # 将 multi_timeframe_widget 也添加到布局中（初始隐藏，与chart共享位置）
        # 注意：两个widget在同一个位置，通过setVisible控制显示哪一个
        if self.multi_timeframe_widget:
            chart_layout.addWidget(self.multi_timeframe_widget, 1)
            # 确保初始状态隐藏（在添加到布局后设置）
            self.multi_timeframe_widget.setVisible(False)
            # 确保widget在布局中（即使隐藏）
            self.multi_timeframe_widget.setParent(self)
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
        """
        Register event listeners

        注册 EVENT_TICK 和 EVENT_ORDER 事件监听，用于接收实时 tick 数据并更新图表。
        使用信号-槽机制确保线程安全。

        注意：
        - 合约切换时不需要重新注册事件，因为 process_tick_event 已经通过过滤
          current_vt_symbol 来处理，只处理当前显示合约的 tick。
        - 窗口关闭时会自动调用 closeEvent() 注销所有事件监听器。
        - 窗口重新打开时会自动调用 showEvent() 重新注册事件监听器。
        """
        try:
            # 检查 event_engine 是否已初始化
            if not self.event_engine:
                if self.main_engine:
                    self.main_engine.write_log(
                        "[ChartWindow] 警告：EventEngine 未初始化，无法注册事件监听",
                        "ChartWindow"
                    )
                return

            from vnpy.trader.event import EVENT_TICK

            # 注册 tick 事件监听（使用信号槽机制确保线程安全）
            # 先检查是否已连接，避免重复连接
            try:
                self.signal_tick.disconnect(self.process_tick_event)
            except (TypeError, RuntimeError):
                # 连接不存在，这是正常的，继续注册
                pass

            # 先注销（如果已注册），避免重复注册
            try:
                self.event_engine.unregister(EVENT_TICK, self.signal_tick.emit)
            except (KeyError, ValueError):
                # 未注册，这是正常的，继续注册
                pass

            self.signal_tick.connect(self.process_tick_event)
            self.event_engine.register(EVENT_TICK, self.signal_tick.emit)

            # 注册历史数据事件监听
            self.signal_history.connect(self.process_history_data)

            # 注册订单事件（用于画线交易功能）
            from vnpy.trader.event import EVENT_ORDER
            # 先注销（如果已注册），避免重复注册
            try:
                self.event_engine.unregister(EVENT_ORDER, self.process_order_event)
            except (KeyError, ValueError):
                # 未注册，这是正常的，继续注册
                pass
            self.event_engine.register(EVENT_ORDER, self.process_order_event)

            # 记录日志
            if self.main_engine:
                self.main_engine.write_log(
                    "已注册事件监听：EVENT_TICK (signal_tick.emit), EVENT_ORDER (process_order_event)",
                    "ChartWindow"
                )

            # 初始化按钮状态（有合约时启用，无合约时禁用）
            self._update_simulate_buttons_state()
        except Exception as e:
            # 错误处理：记录错误但不阻止窗口初始化
            if self.main_engine:
                self.main_engine.write_log(
                    f"[ChartWindow] 注册事件监听失败：{str(e)}",
                    "ChartWindow"
                )

    def process_tick_event(self, event: Event) -> None:
        """
        处理Tick事件 - 支持所有周期的实时更新

        此方法同时处理：
        1. 多周期K线实时更新（1分钟、5分钟、1小时、4小时、1日）
        2. 价格突破监控（用于画线交易功能）
        3. 按钮状态更新

        Performance monitoring - measure tick update latency
        """
        from vnpy.trader.object import TickData
        tick: TickData = event.data

        # Performance monitoring - start measuring tick update latency
        tick_update_start_time = None
        if self._perf_monitoring_enabled:
            tick_update_start_time = time.perf_counter()

        # 只处理当前显示合约的tick
        if tick.vt_symbol != self.current_vt_symbol:
            return

        # 如果当前是多周期模式，将tick数据路由到MultiTimeframeWidget（T035, T036）
        if self.display_mode == "multi" and self.multi_timeframe_widget:
            self.main_engine.write_log(
                f"[Tick路由] 多周期模式，路由tick到MultiTimeframeWidget - "
                f"价格: {tick.last_price}, 时间: {tick.datetime}",
                "ChartWindow"
            )
            if hasattr(self.multi_timeframe_widget, 'update_tick'):
                self.multi_timeframe_widget.update_tick(tick)
                self.main_engine.write_log("[Tick路由] update_tick() 已调用", "ChartWindow")
            else:
                self.main_engine.write_log("[Tick路由] ⚠️ MultiTimeframeWidget 没有 update_tick 方法", "ChartWindow")
            # 注意：多周期模式下，单周期模式的实时更新逻辑仍然执行
            # 这样可以确保两种模式都能正常工作
            # 但主要更新由MultiTimeframeWidget处理

        # 获取当前周期（无论历史数据是否加载完成，都需要知道当前周期）
        interval_enum = self._get_interval_enum()
        from vnpy.trader.constant import Interval

        # 1分钟周期：即使历史数据未加载完成，也允许实时K线更新
        # 这样可以确保用户能够看到实时K线，即使历史数据还在加载中
        if interval_enum == Interval.MINUTE:
            # 1分钟周期：使用BarGenerator从tick合成K线
            if self.bg:
                # 更新BarGenerator（这会自动创建或更新bg.bar）
                self.bg.update_tick(tick)

                # 实时更新当前K线（每次tick都更新，确保实时显示）
                # 注意：bg.bar在第一个有效tick时会被创建，之后每次tick都会更新
                if self.bg.bar:
                        from vnpy.trader.object import BarData
                        # 创建当前K线的副本用于实时更新（避免修改原始bar对象）
                        bar: BarData = copy(self.bg.bar)
                        # 规范化datetime（去掉秒和微秒，确保与历史数据一致）
                        bar.datetime = bar.datetime.replace(second=0, microsecond=0)

                        # For 1-minute interval, check and correct open price
                        #
                        # 【开盘价定义】：1分钟K线的开盘价 = 该分钟第一个tick的last_price
                        #
                        # 【判定是否需要修正】：
                        # 1. 如果当前tick的秒数 > 0，说明该分钟已经开始，第一个tick已经过去
                        #    BarGenerator创建K线时用的不是第一个tick，开盘价不正确，需要修正
                        # 2. 如果当前tick的秒数 = 0，说明可能是该分钟的第一个tick（或接近）
                        #    但为了安全起见，仍然检查是否有更准确的参照物
                        #
                        # 【参照物（按优先级）】：
                        # 1. 保存的删除K线开盘价（最高优先级，来自历史数据，已完成）
                        # 2. 历史数据中的该分钟K线（已完成，开盘价来自完整tick数据）
                        # 3. 数据库中的该分钟K线（已完成，开盘价来自完整tick数据）
                        # 4. 该分钟第一个tick的last_price（通过查询tick数据获取）
                        #
                        # 【判定改的对不对】：
                        # - 参照物的开盘价是从完整的历史数据生成的，理论上应该是正确的
                        # - 如果找不到参照物，只能使用BarGenerator的开盘价（可能不正确，但无法验证）
                        bar_minute_start = bar.datetime.replace(second=0, microsecond=0)
                        correct_open_price = None
                        need_correct = False

                        # 判断是否需要修正：如果tick的秒数>0，说明该分钟已经开始，第一个tick已过去
                        tick_second = tick.datetime.second
                        if tick_second > 0:
                            # 该分钟已经开始，BarGenerator创建K线时用的不是第一个tick，需要修正
                            need_correct = True
                            # 暂时注释掉日志，减少日志输出
                            # self.main_engine.write_log(
                            #     f"[实时K线] 检测到该分钟已开始({tick.datetime.strftime('%H:%M:%S')})，"
                            #     f"需要修正开盘价（BarGenerator使用的不是第一个tick）"
                            # )
                        else:
                            # 可能是该分钟的第一个tick，但仍然检查是否有更准确的参照物
                            # （例如历史数据中的K线，可能是从更完整的tick数据生成的）
                            need_correct = True  # 仍然检查，但优先级较低

                        # 只有需要修正时才查找参照物
                        if need_correct:
                            # 方法1（最高优先级）：检查是否有保存的被删除K线的开盘价
                            # 参照物：删除前历史数据中的K线开盘价（已完成，理论上正确）
                            if (hasattr(self, '_removed_minute_bar_open_price') and
                                self._removed_minute_bar_open_price and
                                hasattr(self, '_removed_minute_bar_datetime') and
                                self._removed_minute_bar_datetime == bar_minute_start):
                                correct_open_price = self._removed_minute_bar_open_price
                                self.main_engine.write_log(
                                    f"[实时K线] 1分钟K线({bar_minute_start.strftime('%H:%M')}) "
                                    f"使用保存的开盘价: {correct_open_price} (参照物：删除的历史K线，已完成)"
                                )
                                # 使用后清除，避免重复使用
                                self._removed_minute_bar_open_price = None
                                self._removed_minute_bar_datetime = None

                            # 方法2：检查历史数据中是否有该分钟的K线
                            # 参照物：历史数据中的K线开盘价（已完成，从完整tick数据生成，理论上正确）
                            if not correct_open_price and self.history_data:
                                for hist_bar in reversed(self.history_data):
                                    hist_bar_minute_start = hist_bar.datetime.replace(second=0, microsecond=0)
                                    if hist_bar_minute_start == bar_minute_start:
                                        # 找到历史数据中该分钟的K线，使用其开盘价
                                        if hist_bar.open_price > 0:
                                            correct_open_price = hist_bar.open_price
                                            self.main_engine.write_log(
                                                f"[实时K线] 1分钟K线({bar_minute_start.strftime('%H:%M')}) "
                                                f"从历史数据获取开盘价: {correct_open_price} "
                                                f"(参照物：历史K线，已完成)"
                                            )
                                        break

                            # 方法3：如果历史数据中没有，尝试从数据库加载该分钟的K线
                            # 参照物：数据库中的K线开盘价（已完成，从完整tick数据生成，理论上正确）
                            if not correct_open_price:
                                # Check cache first to reduce database queries
                                try:
                                    from vnpy.trader.utility import extract_vt_symbol
                                    symbol, exchange = extract_vt_symbol(self.current_vt_symbol)
                                    cached_price = self._get_cached_open_price(symbol, bar_minute_start)
                                    if cached_price is not None:
                                        correct_open_price = cached_price
                                    else:
                                        # 缓存未命中，查询数据库
                                        from vnpy.trader.database import get_database
                                        from vnpy.trader.constant import Interval

                                        database = get_database()
                                        symbol, exchange = extract_vt_symbol(self.current_vt_symbol)

                                        # 查询该分钟的K线数据
                                        minute_bars = database.load_bar_data(
                                            symbol,
                                            exchange,
                                            Interval.MINUTE,
                                            bar_minute_start,
                                            bar_minute_start
                                        )

                                        if minute_bars and len(minute_bars) > 0:
                                            # 找到该分钟的K线，使用其开盘价
                                            minute_bar = minute_bars[0]
                                            if minute_bar.open_price > 0:
                                                correct_open_price = minute_bar.open_price
                                                # Cache the result to reduce future queries
                                                self._set_cached_open_price(symbol, bar_minute_start, correct_open_price)
                                                self.main_engine.write_log(
                                                    f"[实时K线] 1分钟K线({bar_minute_start.strftime('%H:%M')}) "
                                                    f"从数据库获取开盘价: {correct_open_price} "
                                                    f"(参照物：数据库K线，已完成)"
                                                )
                                except Exception as e:
                                    # Database query failed, log error but don't interrupt main flow
                                    if self.main_engine:
                                        self.main_engine.write_log(
                                            f"[ChartWindow] 数据库查询开盘价失败: {e}",
                                            "ChartWindow"
                                        )
                                    # Don't re-raise exception to ensure main flow continues

                            # 方法4（最后手段）：从tick数据恢复正确的开盘价
                            # 参照物：该分钟第一个tick的last_price（这是开盘价的准确定义）
                            # 如果前三种方法都无法获取，尝试从数据库或datafeed查询该分钟的历史tick数据
                            if not correct_open_price:
                                # Check cache first (tick data queries use the same cache key)
                                try:
                                    from vnpy.trader.utility import extract_vt_symbol
                                    symbol, exchange = extract_vt_symbol(self.current_vt_symbol)
                                    cached_price = self._get_cached_open_price(symbol, bar_minute_start)
                                    if cached_price is not None:
                                        correct_open_price = cached_price
                                    else:
                                        # 缓存未命中，查询数据库或datafeed
                                        from datetime import timedelta
                                        from vnpy.trader.database import get_database
                                        from vnpy.trader.constant import Interval
                                        from vnpy.trader.object import HistoryRequest

                                        # 计算该分钟的时间范围
                                        minute_end = bar_minute_start + timedelta(minutes=1)

                                        # 方法4.1：尝试从数据库加载该分钟的tick数据
                                        try:
                                            database = get_database()
                                            ticks = database.load_tick_data(
                                                symbol,
                                                exchange,
                                                bar_minute_start,
                                                minute_end
                                            )

                                            if ticks:
                                                # 按时间排序，找到第一个tick
                                                ticks.sort(key=lambda x: x.datetime)
                                                first_tick = ticks[0]
                                                if first_tick.last_price > 0:
                                                    correct_open_price = first_tick.last_price
                                                    # Cache the result to reduce future queries
                                                    self._set_cached_open_price(symbol, bar_minute_start, correct_open_price)
                                                    # 暂时注释掉日志，减少日志输出
                                                    # self.main_engine.write_log(
                                                    #     f"[实时K线] 1分钟K线({bar_minute_start.strftime('%H:%M')}) "
                                                    #     f"从数据库tick数据获取开盘价: {correct_open_price} "
                                                    #     f"(参照物：该分钟第一个tick，时间: {first_tick.datetime.strftime('%H:%M:%S')})"
                                                    # )
                                                    pass  # 确保代码块不为空
                                        except Exception as e:
                                            # Database tick query failed, log error but continue with datafeed
                                            if self.main_engine:
                                                self.main_engine.write_log(
                                                    f"[ChartWindow] 数据库查询tick数据失败: {e}",
                                                    "ChartWindow"
                                                )
                                            # Continue with datafeed query, don't interrupt main flow

                                        # 方法4.2：如果数据库没有，尝试从datafeed查询该分钟的tick数据
                                        # 注意：FUTU datafeed的query_tick_history会返回空列表（不会发API请求）
                                        # 其他支持tick数据查询的datafeed可以正常使用
                                        if not correct_open_price:
                                            try:
                                                # Use cached Datafeed instance to avoid frequent connection creation
                                                datafeed = self._get_datafeed()

                                                if datafeed:
                                                    req = HistoryRequest(
                                                        symbol=symbol,
                                                        exchange=exchange,
                                                        interval=Interval.TICK,
                                                        start=bar_minute_start,
                                                        end=minute_end
                                                    )

                                                    ticks = datafeed.query_tick_history(req, output=self.main_engine.write_log)

                                                    if ticks:
                                                        # 按时间排序，找到第一个tick
                                                        ticks.sort(key=lambda x: x.datetime)
                                                        first_tick = ticks[0]
                                                        if first_tick.last_price > 0:
                                                            correct_open_price = first_tick.last_price
                                                            # Cache the result to reduce future queries
                                                            self._set_cached_open_price(symbol, bar_minute_start, correct_open_price)
                                                            # 暂时注释掉日志，减少日志输出
                                                            # self.main_engine.write_log(
                                                            #     f"[实时K线] 1分钟K线({bar_minute_start.strftime('%H:%M')}) "
                                                            #     f"从datafeed tick数据获取开盘价: {correct_open_price} "
                                                            #     f"(参照物：该分钟第一个tick，时间: {first_tick.datetime.strftime('%H:%M:%S')})"
                                                            # )
                                                            pass  # 确保代码块不为空
                                            except Exception as e:
                                                # Datafeed query failed, log error but don't interrupt main flow
                                                if self.main_engine:
                                                    self.main_engine.write_log(
                                                        f"[ChartWindow] Datafeed查询tick数据失败: {e}",
                                                        "ChartWindow"
                                                    )
                                                # Don't re-raise exception to ensure main flow continues
                                except Exception as e:
                                    # Tick data query failed, log error but don't interrupt main flow
                                    if self.main_engine:
                                        self.main_engine.write_log(
                                            f"[ChartWindow] 查询tick数据失败: {e}",
                                            "ChartWindow"
                                        )
                                    # Don't re-raise exception to ensure main flow continues

                        # 如果找到了参照物且开盘价不同，则使用参照物的开盘价
                        if correct_open_price and correct_open_price > 0:
                            if correct_open_price != bar.open_price:
                                old_open_price = bar.open_price
                                bar.open_price = correct_open_price
                                # 暂时注释掉开盘价修正日志，减少日志输出
                                # self.main_engine.write_log(
                                #     f"[实时K线] 1分钟K线({bar_minute_start.strftime('%H:%M')}) "
                                #     f"开盘价已修正: {old_open_price} -> {correct_open_price} "
                                #     f"(使用参照物修正)"
                                # )
                            else:
                                # 开盘价相同，说明BarGenerator的开盘价是正确的（可能是第一个tick）
                                # 暂时注释掉日志，减少日志输出
                                # self.main_engine.write_log(
                                #     f"[实时K线] 1分钟K线({bar_minute_start.strftime('%H:%M')}) "
                                #     f"开盘价验证正确: {bar.open_price} (与参照物一致)"
                                # )
                                pass
                        elif need_correct:
                            # 需要修正但找不到参照物，记录警告
                            # 暂时注释掉日志，减少日志输出
                            # self.main_engine.write_log(
                            #     f"[实时K线] 1分钟K线({bar_minute_start.strftime('%H:%M')}) "
                            #     f"无法获取参照物修正开盘价，使用BarGenerator的开盘价: {bar.open_price} "
                            #     f"(可能不准确，因为该分钟已开始: {tick.datetime.strftime('%H:%M:%S')})"
                            # )
                            pass

                        # 更新图表显示（BarManager会自动处理新bar的添加和已有bar的更新）
                        # 这会实时更新最后一根K线的显示（如果bar已存在）或添加新K线（如果bar不存在）
                        # Performance monitoring - measure chart refresh latency
                        chart_refresh_start_time = None
                        if self._perf_monitoring_enabled:
                            chart_refresh_start_time = time.perf_counter()

                        self.chart.update_bar(bar)

                        # Performance monitoring - log chart refresh latency
                        if self._perf_monitoring_enabled and chart_refresh_start_time is not None:
                            chart_refresh_end_time = time.perf_counter()
                            chart_refresh_latency_ms = (chart_refresh_end_time - chart_refresh_start_time) * 1000
                            self._record_performance_metric("chart_refresh", chart_refresh_latency_ms)
            else:
                # 5分钟、1小时、4小时周期：使用tick数据直接更新当前未完成的K线
                # 这样可以实现所有周期的实时更新
                self._update_current_bar_with_tick(tick, interval_enum)

        # 更新价格突破监控（用于画线交易功能）
        if self.chart and self.chart._breakthrough_monitor:
            all_lines = self.chart._price_line_manager.get_all_lines()
            # 只处理挂单线（PENDING类型），避免不必要的处理
            from vnpy.chart.price_line import PriceLineType
            pending_lines = {
                line_id: line
                for line_id, line in all_lines.items()
                if line.get_line_type() == PriceLineType.PENDING
            }
            if pending_lines:
                # Performance monitoring - measure price breakthrough trigger latency
                breakthrough_start_time = None
                if self._perf_monitoring_enabled:
                    breakthrough_start_time = time.perf_counter()

                self.chart._breakthrough_monitor.update_tick(tick, all_lines)

                # Performance monitoring - log price breakthrough trigger latency
                if self._perf_monitoring_enabled and breakthrough_start_time is not None:
                    breakthrough_end_time = time.perf_counter()
                    breakthrough_latency_ms = (breakthrough_end_time - breakthrough_start_time) * 1000
                    self._record_performance_metric("price_breakthrough", breakthrough_latency_ms)

        # Update stop loss/take profit line monitoring (real-time stop loss/take profit feature)
        if self.chart and self.chart._price_line_manager:
            all_lines = self.chart._price_line_manager.get_all_lines()
            from vnpy.chart.price_line import PriceLineType

            # 处理止损线（不提前过滤，让内部方法判断是否激活）
            stop_loss_lines = {
                line_id: line
                for line_id, line in all_lines.items()
                if line.get_line_type() == PriceLineType.STOP_LOSS
            }
            for line_id, line in stop_loss_lines.items():
                try:
                    # 调用触发方法，方法内部会检查激活状态和价格是否触及止损线
                    # 未激活的线会在内部静默跳过（不记录日志，避免刷屏）
                    self.chart.trigger_stop_loss_close(line_id, line, tick)
                except Exception as e:
                    if self.main_engine:
                        self.main_engine.write_log(
                            f"[ChartWindow] 止损线监控异常: {line_id} (价格: {tick.last_price}, 止损价: {line.get_price()}): {str(e)}",
                            "ChartWindow"
                        )

            # 处理止盈线（不提前过滤，让内部方法判断是否激活）
            take_profit_lines = {
                line_id: line
                for line_id, line in all_lines.items()
                if line.get_line_type() == PriceLineType.TAKE_PROFIT
            }
            for line_id, line in take_profit_lines.items():
                try:
                    # 调用触发方法，方法内部会检查激活状态和价格是否触及止盈线
                    # 未激活的线会在内部静默跳过（不记录日志，避免刷屏）
                    self.chart.trigger_take_profit_close(line_id, line, tick)
                except Exception as e:
                    if self.main_engine:
                        self.main_engine.write_log(
                            f"[ChartWindow] 止盈线监控异常: {line_id} (价格: {tick.last_price}, 止盈价: {line.get_price()}): {str(e)}",
                            "ChartWindow"
                        )

        # 更新按钮状态（现在始终启用，如果有合约的话）
        self._update_simulate_buttons_state()

        # Performance monitoring - log tick update latency
        if self._perf_monitoring_enabled and tick_update_start_time is not None:
            tick_update_end_time = time.perf_counter()
            tick_update_latency_ms = (tick_update_end_time - tick_update_start_time) * 1000
            self._record_performance_metric("tick_update", tick_update_latency_ms)

    def on_mode_changed(self, text: str) -> None:
        """模式选择改变时的处理（T015, T066, T067）"""
        if text == "单周期":
            self.switch_display_mode("single")
        elif text == "多周期叠加":
            self.switch_display_mode("multi")

        # 更新控制面板可见性（T066, T067）
        self._update_control_panel_visibility()

    def _update_control_panel_visibility(self) -> None:
        """
        更新控制面板可见性（T066, T067）
        
        根据当前模式显示/隐藏相应的控制面板
        """
        if self.display_mode == "single":
            # 单周期模式：显示单周期控制，隐藏多周期控制
            if hasattr(self, 'interval_combo'):
                self.interval_combo.setVisible(True)
            if hasattr(self, 'multi_timeframe_settings_button'):
                self.multi_timeframe_settings_button.setVisible(False)
            # 隐藏 MultiTimeframeWidget 的控制面板
            if self.multi_timeframe_widget:
                # 获取控制面板（通过查找 control_layout）
                # 注意：MultiTimeframeWidget 的控制面板在 layout 中
                # 我们可以通过查找包含 control_layout 的 widget 来隐藏它
                # 但更简单的方法是直接隐藏整个控制面板区域
                # 由于控制面板是 MultiTimeframeWidget 的一部分，我们不需要单独隐藏
                pass
        else:
            # 多周期模式：隐藏单周期控制，显示多周期控制
            if hasattr(self, 'interval_combo'):
                self.interval_combo.setVisible(False)
            if hasattr(self, 'multi_timeframe_settings_button'):
                self.multi_timeframe_settings_button.setVisible(True)

    def show_multi_timeframe_settings(self) -> None:
        """
        显示多周期设置对话框（T064）
        """
        if not self.multi_timeframe_widget:
            return

        # 调用 MultiTimeframeWidget 的设置对话框
        if hasattr(self.multi_timeframe_widget, 'show_settings_dialog'):
            self.multi_timeframe_widget.show_settings_dialog()

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
        self.interval_combo.currentText()
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

    def update_history_data(self) -> None:
        """
        更新历史数据：从数据库已有数据的结束日期开始，下载截止到当前最新日期的1分钟K线数据。
        
        短期解决方案：调用DataManager的更新数据功能。
        """
        # 检查是否有当前合约
        if not self.current_vt_symbol:
            QtWidgets.QMessageBox.warning(
                self,
                _("警告"),
                _("请先选择合约后再更新数据")
            )
            return

        from threading import Thread
        from datetime import datetime, timedelta
        from tzlocal import get_localzone_name
        from vnpy.trader.utility import extract_vt_symbol, ZoneInfo
        from vnpy.trader.constant import Interval
        from vnpy.trader.database import get_database

        # 验证vt_symbol格式
        if "." not in self.current_vt_symbol:
            QtWidgets.QMessageBox.warning(
                self,
                _("警告"),
                _("合约代码格式不正确，应为：合约代码.交易所（如：MHImain.HKFE）")
            )
            return

        try:
            symbol, exchange = extract_vt_symbol(self.current_vt_symbol)
        except (ValueError, AttributeError) as e:
            QtWidgets.QMessageBox.warning(
                self,
                _("警告"),
                _("无法解析合约代码：{}\n请检查格式是否正确（如：MHImain.HKFE）").format(self.current_vt_symbol)
            )
            self.main_engine.write_log(
                f"[ChartWindow] 解析合约代码失败: {self.current_vt_symbol}, 错误: {e}",
                "ChartWindow"
            )
            return

        # 显示进度提示（在主线程中创建）
        self._update_progress_dialog = QtWidgets.QProgressDialog(
            _("正在更新数据，请稍候..."),
            _("取消"),
            0,
            0,
            self
        )
        self._update_progress_dialog.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        self._update_progress_dialog.setAutoClose(False)
        self._update_progress_dialog.setAutoReset(False)
        self._update_progress_dialog.show()

        def _update():
            try:
                # 1. 尝试通过DataManagerApp更新数据
                datamanager_app = None
                if hasattr(self.main_engine, 'apps'):
                    # 尝试获取DataManagerApp
                    for app_name, app in self.main_engine.apps.items():
                        # 检查是否是DataManagerApp（通过app_name或类型判断）
                        if app_name == "DataManager" or (hasattr(app, 'app_name') and app.app_name == "DataManager"):
                            datamanager_app = app
                            break
                        # 也尝试通过类型判断
                        try:
                            from vnpy_datamanager import DataManagerApp
                            if isinstance(app, DataManagerApp):
                                datamanager_app = app
                                break
                        except ImportError:
                            pass

                if datamanager_app:
                    # 尝试获取DataManager引擎
                    datamanager_engine = None
                    if hasattr(self.main_engine, 'engines'):
                        datamanager_engine = self.main_engine.engines.get("DataManager")

                    if datamanager_engine and hasattr(datamanager_engine, 'update_data'):
                        # 使用DataManager的更新数据功能
                        self.main_engine.write_log(
                            f"[ChartWindow] 使用DataManager更新数据: {self.current_vt_symbol}",
                            "ChartWindow"
                        )

                        # 构建更新参数（DataManager的update_data可能需要特定格式）
                        # 这里我们尝试调用update_data方法，传入当前合约信息
                        try:
                            # 尝试直接调用update_data方法（如果它接受参数）
                            # 注意：DataManager的update_data可能不接受参数，而是更新所有合约
                            # 这里我们先尝试获取数据库最后日期，然后手动更新当前合约
                            database = get_database()

                            # 查询数据库中1分钟数据的最后日期
                            local_tz = ZoneInfo(get_localzone_name())
                            # 查询最近30天的数据来确定最后日期
                            end_date = datetime.now(local_tz)
                            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=30)

                            existing_bars = database.load_bar_data(
                                symbol,
                                exchange,
                                Interval.MINUTE,
                                start_date,
                                end_date
                            )

                            if existing_bars:
                                # 找到最后一条数据的日期
                                existing_bars.sort(key=lambda x: x.datetime)
                                last_bar_date = existing_bars[-1].datetime
                                # 从最后一条数据的下一条开始下载
                                update_start = last_bar_date.replace(second=0, microsecond=0) + timedelta(minutes=1)
                            else:
                                # 如果没有数据，从7天前开始下载
                                update_start = end_date.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=7)

                            # 调用DataManager的下载方法（如果可用）
                            if hasattr(datamanager_engine, 'download_history_data'):
                                self.main_engine.write_log(
                                    f"[ChartWindow] 调用DataManager下载数据: {symbol}.{exchange.value} "
                                    f"从 {update_start.strftime('%Y-%m-%d %H:%M')} 到 {end_date.strftime('%Y-%m-%d %H:%M')}",
                                    "ChartWindow"
                                )
                                datamanager_engine.download_history_data(
                                    symbol=symbol,
                                    exchange=exchange,
                                    interval=Interval.MINUTE,
                                    start=update_start,
                                    end=end_date
                                )
                            else:
                                # 如果没有download_history_data方法，使用datafeed直接下载
                                self._download_and_save_minute_data(
                                    symbol, exchange, update_start, end_date, database
                                )

                            # 发送完成信号（在主线程中处理UI更新）
                            self.signal_update_data_complete.emit(True, _("数据更新完成，已刷新图表"))
                            return

                        except Exception as e:
                            error_msg = str(e).replace("{", "{{").replace("}", "}}")
                            self.main_engine.write_log(
                                f"[ChartWindow] DataManager更新数据失败: {error_msg}，尝试直接下载",
                                "ChartWindow"
                            )
                            # 如果DataManager方法失败，降级到直接下载

                # 2. 如果没有DataManager，直接实现数据更新逻辑
                database = get_database()
                local_tz = ZoneInfo(get_localzone_name())
                end_date = datetime.now(local_tz)

                # 查询数据库中1分钟数据的最后日期
                # 查询最近30天的数据来确定最后日期
                start_query = end_date.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=30)

                existing_bars = database.load_bar_data(
                    symbol,
                    exchange,
                    Interval.MINUTE,
                    start_query,
                    end_date
                )

                if existing_bars:
                    # 找到最后一条数据的日期
                    existing_bars.sort(key=lambda x: x.datetime)
                    last_bar_date = existing_bars[-1].datetime
                    # 从最后一条数据的下一条开始下载
                    update_start = last_bar_date.replace(second=0, microsecond=0) + timedelta(minutes=1)
                    self.main_engine.write_log(
                        f"[ChartWindow] 数据库中最后一条1分钟数据日期: {last_bar_date.strftime('%Y-%m-%d %H:%M')}",
                        "ChartWindow"
                    )
                else:
                    # 如果没有数据，从7天前开始下载
                    update_start = end_date.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=7)
                    self.main_engine.write_log(
                        f"[ChartWindow] 数据库中没有1分钟数据，从 {update_start.strftime('%Y-%m-%d %H:%M')} 开始下载",
                        "ChartWindow"
                    )

                # 检查是否需要更新（如果最后数据已经是最新的，不需要更新）
                if update_start >= end_date:
                    self.signal_update_data_complete.emit(False, _("数据已是最新，无需更新"))
                    return

                # 下载并保存1分钟数据
                self._download_and_save_minute_data(
                    symbol, exchange, update_start, end_date, database
                )

                # 发送完成信号（在主线程中处理UI更新）
                self.signal_update_data_complete.emit(True, _("数据更新完成，已刷新图表"))

            except Exception as e:
                error_msg = str(e).replace("{", "{{").replace("}", "}}")
                self.main_engine.write_log(
                    f"[ChartWindow] 更新数据失败: {error_msg}",
                    "ChartWindow"
                )
                import traceback
                self.main_engine.write_log(
                    f"[ChartWindow] 更新数据异常堆栈: {traceback.format_exc()}",
                    "ChartWindow"
                )
                # 发送错误信号（在主线程中处理UI更新）
                error_message = _("更新数据失败: {}\n\n请检查数据服务配置或网络连接").format(str(e))
                self.signal_update_data_complete.emit(False, error_message)

        # 在后台线程执行更新
        thread = Thread(target=_update)
        thread.start()

    def _on_update_data_complete(self, success: bool, message: str) -> None:
        """
        处理更新数据完成信号（在主线程中执行）
        
        Args:
            success: 是否成功
            message: 消息内容
        """
        # 关闭进度对话框
        if hasattr(self, '_update_progress_dialog'):
            self._update_progress_dialog.close()
            delattr(self, '_update_progress_dialog')

        # 显示消息
        if success:
            QtWidgets.QMessageBox.information(
                self,
                _("成功"),
                message
            )
            # 刷新图表
            QtCore.QTimer.singleShot(100, lambda: self.refresh_chart())
        else:
            if "数据已是最新" in message or "无需更新" in message:
                QtWidgets.QMessageBox.information(
                    self,
                    _("提示"),
                    message
                )
            else:
                QtWidgets.QMessageBox.critical(
                    self,
                    _("错误"),
                    message
                )

    def _download_and_save_minute_data(
        self,
        symbol: str,
        exchange: "Exchange",
        start: datetime,
        end: datetime,
        database
    ) -> None:
        """
        下载并保存1分钟K线数据到数据库
        
        Args:
            symbol: 合约代码
            exchange: 交易所
            start: 开始时间
            end: 结束时间
            database: 数据库实例
        """
        from vnpy.trader.object import HistoryRequest
        from vnpy.trader.constant import Interval

        self.main_engine.write_log(
            f"[数据加载] 开始下载1分钟数据: {symbol}.{exchange.value} "
            f"从 {start.strftime('%Y-%m-%d %H:%M')} 到 {end.strftime('%Y-%m-%d %H:%M')}"
        )

        # 使用全局单例 Datafeed（核心功能，失败时显示错误）
        datafeed = self._get_datafeed(show_error_dialog=True)
        if not datafeed:
            self.main_engine.write_log(
                "[数据加载] Datafeed 服务不可用，无法下载数据"
            )
            raise Exception(_("Datafeed 服务不可用"))

        # 使用全局单例，不需要关闭连接
        try:

            # 创建历史数据请求
            req = HistoryRequest(
                symbol=symbol,
                exchange=exchange,
                interval=Interval.MINUTE,
                start=start,
                end=end
            )

            # 查询历史数据
            bars = datafeed.query_bar_history(req, output=self.main_engine.write_log)

            if not bars:
                self.main_engine.write_log(
                    "[ChartWindow] 未获取到1分钟数据，可能数据服务不支持该合约或时间范围内无数据",
                    "ChartWindow"
                )
                raise Exception(_("未获取到数据"))

            self.main_engine.write_log(
                f"[ChartWindow] 成功获取 {len(bars)} 条1分钟K线数据",
                "ChartWindow"
            )

            # 保存到数据库
            if database.save_bar_data(bars):
                self.main_engine.write_log(
                    f"[ChartWindow] 已保存 {len(bars)} 条1分钟K线数据到数据库",
                    "ChartWindow"
                )
            else:
                self.main_engine.write_log(
                    "[ChartWindow] 保存数据到数据库失败",
                    "ChartWindow"
                )
                raise Exception(_("保存数据到数据库失败"))

            # ✅ 自动聚合大周期K线数据（5分钟、1小时、4小时）
            # 复用DataManager的聚合逻辑，确保严格按照港期时间边界划分规则（period_utils.py）进行聚合
            self._aggregate_larger_intervals_using_datamanager(symbol, exchange)
        except Exception as e:
            # 数据加载失败，记录日志并重新抛出
            error_msg = str(e).replace("{", "{{").replace("}", "}}")
            self.main_engine.write_log(f"[数据加载] 加载失败: {error_msg}")
            raise

        # 注意：不需要在 finally 中关闭 datafeed
        # 因为使用的是全局单例，由 DatafeedManager 管理生命周期

    def _aggregate_larger_intervals_using_datamanager(
        self,
        symbol: str,
        exchange: "Exchange"
    ) -> None:
        """
        使用DataManager的聚合方法自动聚合大周期K线数据
        
        复用DataManager的聚合逻辑，确保严格按照港期时间边界划分规则（period_utils.py）进行聚合：
        - 5分钟K线：使用 get_period_start(bar_dt, Interval.MINUTE_5, exchange)
        - 1小时K线：使用 get_hkfe_hour_period_start(bar_dt)
        - 4小时K线：使用 get_hkfe_4hour_period(bar_dt)
        
        Args:
            symbol: 合约代码
            exchange: 交易所
        """
        # 尝试获取DataManager引擎，复用其聚合方法
        datamanager_engine = None
        if hasattr(self.main_engine, 'engines'):
            datamanager_engine = self.main_engine.engines.get("DataManager")

        if datamanager_engine and hasattr(datamanager_engine, 'aggregate_5minute_bars'):
            # 使用DataManager的聚合方法（推荐方式）
            try:
                self.main_engine.write_log(
                    f"[ChartWindow] 使用DataManager聚合5分钟K线数据: {symbol}.{exchange.value}",
                    "ChartWindow"
                )
                count_5m = datamanager_engine.aggregate_5minute_bars(symbol, exchange)
                if count_5m > 0:
                    self.main_engine.write_log(
                        f"[ChartWindow] 已聚合 {count_5m} 条5分钟K线数据",
                        "ChartWindow"
                    )
            except Exception as e:
                error_msg = str(e).replace("{", "{{").replace("}", "}}")
                self.main_engine.write_log(
                    f"[ChartWindow] 聚合5分钟K线数据失败: {error_msg}",
                    "ChartWindow"
                )

            try:
                self.main_engine.write_log(
                    f"[ChartWindow] 使用DataManager聚合1小时K线数据: {symbol}.{exchange.value}",
                    "ChartWindow"
                )
                count_1h = datamanager_engine.aggregate_hour_bars(symbol, exchange)
                if count_1h > 0:
                    self.main_engine.write_log(
                        f"[ChartWindow] 已聚合 {count_1h} 条1小时K线数据",
                        "ChartWindow"
                    )
            except Exception as e:
                error_msg = str(e).replace("{", "{{").replace("}", "}}")
                self.main_engine.write_log(
                    f"[ChartWindow] 聚合1小时K线数据失败: {error_msg}",
                    "ChartWindow"
                )

            try:
                self.main_engine.write_log(
                    f"[ChartWindow] 使用DataManager聚合4小时K线数据: {symbol}.{exchange.value}",
                    "ChartWindow"
                )
                count_4h = datamanager_engine.aggregate_4hour_bars(symbol, exchange)
                if count_4h > 0:
                    self.main_engine.write_log(
                        f"[数据加载] 已聚合 {count_4h} 条4小时K线数据"
                    )
            except Exception as e:
                error_msg = str(e).replace("{", "{{").replace("}", "}}")
                self.main_engine.write_log(
                    f"[ChartWindow] 聚合4小时K线数据失败: {error_msg}",
                    "ChartWindow"
                )
        else:
            # DataManager不可用，记录警告（不强制要求DataManager）
            self.main_engine.write_log(
                "[ChartWindow] DataManager引擎不可用，跳过自动聚合大周期K线数据",
                "ChartWindow"
            )
            self.main_engine.write_log(
                "[ChartWindow] 建议：加载DataManager模块后可自动聚合5分钟、1小时、4小时K线数据",
                "ChartWindow"
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

    def _get_future_bars_for_interval(self, interval: str) -> int:
        """
        根据周期获取未来空间K线数量（辅助方法，用于多周期模式）
        
        Args:
            interval: 周期字符串（如 "1m", "5m", "1h", "4h"）
        
        Returns:
            未来空间K线数量
        """
        from vnpy.trader.constant import Interval  # type: ignore

        interval_map = {
            "1m": Interval.MINUTE,
            "5m": Interval.MINUTE_5,
            "1h": Interval.HOUR,
            "4h": Interval.HOUR_4,
        }

        interval_obj = interval_map.get(interval, Interval.MINUTE)
        return self._calculate_future_bars(interval_obj)

    def _calculate_future_bars(self, interval) -> int:
        """
        计算未来空间K线数量（内部辅助方法）
        
        Args:
            interval: Interval 枚举值
        
        Returns:
            未来空间K线数量
        """
        from vnpy.trader.constant import Interval  # type: ignore

        # 根据周期计算未来空间（与原有逻辑一致）
        if interval == Interval.MINUTE:
            return 60  # 1分钟：显示未来60根K线
        elif interval == Interval.MINUTE_5:
            return 12  # 5分钟：显示未来12根K线
        elif interval == Interval.HOUR:
            return 4   # 1小时：显示未来4根K线
        elif interval == Interval.HOUR_4:
            return 1   # 4小时：显示未来1根K线
        else:
            return 60  # 默认值

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
    
    def _get_optimized_load_strategy(
        self,
        database,
        symbol: str,
        exchange: "Exchange",
        user_start: "datetime",
        end: "datetime"
    ) -> tuple:
        """
        优化数据加载策略（针对1分钟周期）
        
        策略：
        1. 查询数据库最早和最新数据时间
        2. 如果用户选择早于数据库最早时间 → 数据不全 → 下载用户选择范围
        3. 如果数据库最新数据很新（< 1小时） → 数据足够 → 不下载
        4. 如果数据库最新数据较旧（>= 1小时） → 数据过期 → 下载最近7天
        
        Returns:
            (optimized_start, need_download): 优化后的起始时间和是否需要下载
        """
        from datetime import timedelta
        from vnpy.trader.constant import Interval
        
        try:
            # 查询数据库最近90天的数据，用于分析
            query_start = end - timedelta(days=90)
            existing_bars = database.load_bar_data(
                symbol=symbol,
                exchange=exchange,
                interval=Interval.MINUTE,
                start=query_start,
                end=end
            )
            
            if existing_bars and len(existing_bars) > 0:
                # 排序找到最早和最新数据
                existing_bars.sort(key=lambda x: x.datetime)
                db_earliest = existing_bars[0].datetime
                db_latest = existing_bars[-1].datetime
                
                self.main_engine.write_log(
                    f"[加载优化] 数据库状态: 最早={db_earliest}, 最新={db_latest}, 数据量={len(existing_bars)}"
                )
                self.main_engine.write_log(
                    f"[加载优化] 用户选择: 起始={user_start}, 结束={end}"
                )
                
                # 判断策略
                if user_start < db_earliest:
                    # 情况1：用户选择早于数据库 → 数据不全 → 下载用户选择范围
                    self.main_engine.write_log(
                        f"[加载优化] 策略1: 用户选择 {user_start} 早于数据库最早 {db_earliest}"
                    )
                    self.main_engine.write_log(
                        f"[加载优化] 需要从 FUTU API 下载补齐数据"
                    )
                    return user_start, True
                else:
                    # 检查数据新鲜度
                    data_age = end - db_latest
                    
                    if data_age < timedelta(hours=1):
                        # 情况2：数据很新（< 1小时） → 不需要下载
                        self.main_engine.write_log(
                            f"[加载优化] 策略2: 数据库数据很新（最新数据距今 {data_age.total_seconds()/60:.1f} 分钟）"
                        )
                        self.main_engine.write_log(
                            f"[加载优化] 跳过下载，直接使用数据库数据"
                        )
                        return user_start, False  # 不需要下载
                    else:
                        # 情况3：数据较旧（>= 1小时） → 下载最近7天
                        optimized_start = end - timedelta(days=7)
                        self.main_engine.write_log(
                            f"[加载优化] 策略3: 数据库数据较旧（最新数据距今 {data_age.total_seconds()/3600:.1f} 小时）"
                        )
                        self.main_engine.write_log(
                            f"[加载优化] 优化为下载最近7天: {optimized_start} ~ {end}"
                        )
                        return optimized_start, True
            else:
                # 数据库无数据 → 下载最近7天
                optimized_start = end - timedelta(days=7)
                self.main_engine.write_log(
                    f"[加载优化] 策略4: 数据库无数据，下载最近7天: {optimized_start} ~ {end}"
                )
                return optimized_start, True
                
        except Exception as e:
            self.main_engine.write_log(f"[加载优化] 分析数据库状态失败: {e}，使用用户选择时间")
            return user_start, False

    def switch_display_mode(self, mode: str) -> None:
        """
        切换显示模式（T011）
        
        Args:
            mode: "single" 或 "multi"
        """
        if mode not in ["single", "multi"]:
            self.main_engine.write_log(
                f"[ChartWindow] 无效的显示模式: {mode}",
                "ChartWindow"
            )
            return

        if mode == self.display_mode:
            # 已经是目标模式，无需切换
            return

        self.display_mode = mode

        if mode == "single":
            self._switch_to_single_timeframe_mode()
        else:
            self._switch_to_multi_timeframe_mode()

    def _switch_to_single_timeframe_mode(self) -> None:
        """切换到单周期模式（T012）"""
        # 隐藏多周期Widget
        if self.multi_timeframe_widget:
            self.multi_timeframe_widget.setVisible(False)

        # 显示单周期ChartWidget
        if self.chart:
            self.chart.setVisible(True)

        # 禁用画线模式（根据澄清文档，切换时不保留画线状态）（T057）
        if self.drawing_mode_button:
            self.drawing_mode_button.setChecked(False)
        if self.chart and self.chart.get_drawing_order_controller():
            self.chart.get_drawing_order_controller().disable()

    def _switch_to_multi_timeframe_mode(self) -> None:
        """切换到多周期模式（T013）"""
        # 隐藏单周期ChartWidget
        if self.chart:
            self.chart.setVisible(False)

        # 显示多周期Widget
        if self.multi_timeframe_widget:
            # 确保widget在布局中且有正确的父窗口
            if self.multi_timeframe_widget.parent() != self:
                self.multi_timeframe_widget.setParent(self)
            
            # 启用画线交易功能（T049-T052）
            if hasattr(self.multi_timeframe_widget, 'enable_drawing_order'):
                self.multi_timeframe_widget.enable_drawing_order(
                    main_engine=self.main_engine,
                    vt_symbol=self.current_vt_symbol,
                    on_drawing_click=self._on_drawing_click
                )
                # 设置画线模式状态变化回调（用于ESC键退出等功能）
                if hasattr(self.multi_timeframe_widget, '_chart'):
                    chart = self.multi_timeframe_widget._chart
                    if chart and hasattr(chart, 'set_drawing_mode_changed_callback'):
                        chart.set_drawing_mode_changed_callback(self._on_drawing_mode_changed)
            
            # ✅ 先启用实时更新（在加载数据之前）
            if hasattr(self.multi_timeframe_widget, 'enable_realtime'):
                self.multi_timeframe_widget.enable_realtime()
                self.main_engine.write_log("[多周期] 实时更新已启用", "ChartWindow")
            
            # ✅ 自动加载数据（使用默认时间范围）
            self.main_engine.write_log("[多周期] 开始自动加载数据（使用默认时间范围）", "ChartWindow")
            self._load_multi_timeframe_data()
            # 同步价格线从单周期图表到多周期图表
            # 注意：只同步入场线和已激活的止损止盈线，不同步挂单止损止盈线
            if self.chart and self.chart._price_line_manager:
                from vnpy.chart.price_line import PriceLineType
                
                single_chart_lines = self.chart._price_line_manager.get_all_lines()
                if single_chart_lines and hasattr(self.multi_timeframe_widget, '_chart'):
                    multi_chart = self.multi_timeframe_widget._chart
                    if multi_chart and multi_chart._price_line_manager:
                        multi_chart_manager = multi_chart._price_line_manager
                        
                        # 筛选需要同步的价格线
                        synced_count = 0
                        for line_id, line in single_chart_lines.items():
                            line_type = line.get_line_type()
                            
                            # 只同步以下类型的线：
                            # 1. 入场线（ENTRY）
                            # 2. 已关联到入场线的止损止盈线
                            should_sync = False
                            
                            if line_type == PriceLineType.ENTRY:
                                # 入场线：始终同步
                                should_sync = True
                            elif line_type in [PriceLineType.STOP_LOSS, PriceLineType.TAKE_PROFIT]:
                                # 止损止盈线：只同步已关联到入场线的（不同步挂单线）
                                if hasattr(line, 'entry_line_id') and line.entry_line_id:
                                    should_sync = True
                                    self.main_engine.write_log(
                                        f"[ChartWindow] 同步已激活的{line_type.value}线: {line_id} (关联到 {line.entry_line_id})"
                                    )
                                else:
                                    # 这是挂单线，不同步
                                    self.main_engine.write_log(
                                        f"[ChartWindow] 跳过未激活的{line_type.value}线: {line_id} (挂单线，未关联入场线)"
                                    )
                            elif line_type == PriceLineType.PENDING:
                                # 挂单线：始终同步
                                should_sync = True
                            
                            if should_sync:
                                if not multi_chart_manager.get_line(line_id):
                                    # 如果多周期图表中还没有这条线，则添加
                                    multi_chart_manager.add_line(line_id, line)
                                    if multi_chart._first_plot:
                                        multi_chart._first_plot.addItem(line)
                                    synced_count += 1
                        
                        self.main_engine.write_log(f"[ChartWindow] 已同步 {synced_count} 条价格线到多周期图表（过滤了挂单止损止盈线）")
            
            # 显示widget（确保它在布局中可见）
            # 注意：在Qt中，isVisible()会检查整个父窗口链的可见性
            # 如果父窗口未显示，isVisible()可能返回False，但setVisible(True)会设置widget的可见状态
            self.multi_timeframe_widget.setVisible(True)
            self.multi_timeframe_widget.show()
            # 强制更新布局和重绘
            if hasattr(self, 'layout') and self.layout():
                self.layout().update()
            self.multi_timeframe_widget.update()
            self.multi_timeframe_widget.repaint()
        else:
            self.main_engine.write_log(
                "[ChartWindow] MultiTimeframeWidget 未初始化",
                "ChartWindow"
            )

        # 禁用画线模式（根据澄清文档，切换时不保留画线状态）（T057）
        if self.drawing_mode_button:
            self.drawing_mode_button.setChecked(False)
        # 禁用多周期模式的画线模式
        if self.multi_timeframe_widget:
            controller = self.multi_timeframe_widget.get_drawing_order_controller()
            if controller:
                controller.disable()

    def _load_multi_timeframe_data(self) -> None:
        """
        多周期模式下独立加载数据
        
        不依赖单周期数据，完全独立加载：
        1. 从UI控件读取当前设置的起始时间（保留用户在单周期的设置）
        2. 调用 MultiTimeframeWidget.switch_symbol 独立加载
        3. MultiTimeframeWidget 内部会检查数据完整性并使用智能下载策略
        """
        if not self.multi_timeframe_widget:
            self.main_engine.write_log("[多周期加载] MultiTimeframeWidget 未初始化", "ChartWindow")
            return
        
        if not self.current_vt_symbol:
            self.main_engine.write_log("[多周期加载] 当前合约为空", "ChartWindow")
            return
        
        # 提取 symbol 和 exchange
        from vnpy.trader.utility import extract_vt_symbol
        symbol, exchange = extract_vt_symbol(self.current_vt_symbol)
        
        # 从UI控件读取当前设置的起始时间
        # 注意：这个时间可能是默认的（7天前），也可能是用户在单周期模式设定的
        # 多周期会保留并使用这个时间作为加载范围
        user_start = self.start_datetime.dateTime().toPython()
        end = datetime.now()
        
        self.main_engine.write_log(
            f"[多周期加载] 合约: {symbol}, 交易所: {exchange}",
            "ChartWindow"
        )
        self.main_engine.write_log(
            f"[多周期加载] 用户选择范围: {user_start} ~ {end}",
            "ChartWindow"
        )
        
        # 创建进度对话框
        from vnpy.trader.ui.widget import MultiTimeframeLoadProgressDialog
        progress = MultiTimeframeLoadProgressDialog(self)
        progress.setWindowTitle("多周期数据加载")
        progress.show()
        QtWidgets.QApplication.processEvents()
        
        def progress_callback(message: str, percent: int):
            """进度回调"""
            progress.set_status(message)
            progress.set_progress(percent)
            QtWidgets.QApplication.processEvents()
        
        # 异步调用 switch_symbol（避免UI卡顿）
        def load_data():
            try:
                self.multi_timeframe_widget.switch_symbol(
                    vt_symbol=symbol,
                    exchange=exchange,
                    start=user_start,
                    end=end,
                    progress_callback=progress_callback
                )
                progress.close()
                self.main_engine.write_log("[多周期加载] 数据加载完成", "ChartWindow")
                
                # 数据加载完成后，启用实时更新（T037）
                if hasattr(self.multi_timeframe_widget, 'enable_realtime'):
                    self.multi_timeframe_widget.enable_realtime()
                    self.main_engine.write_log("[多周期加载] 实时更新已启用", "ChartWindow")
                
            except Exception as e:
                progress.close()
                import traceback
                self.main_engine.write_log(
                    f"[多周期加载] 数据加载失败: {e}",
                    "ChartWindow"
                )
                self.main_engine.write_log(
                    f"[多周期加载] 错误堆栈: {traceback.format_exc()}",
                    "ChartWindow"
                )
        
        # 使用 QTimer 异步执行
        QtCore.QTimer.singleShot(50, load_data)
    
    def sync_data_to_multi_timeframe(self) -> None:
        """
        准备多周期模式的数据加载（已废弃，保留以兼容）
        
        注意：现在多周期模式下使用 _load_multi_timeframe_data() 独立加载
        不再自动同步单周期数据
        """
        if not self.multi_timeframe_widget:
            self.main_engine.write_log(
                "[ChartWindow] MultiTimeframeWidget 未初始化",
                "ChartWindow"
            )
            return

        if not self.current_vt_symbol:
            self.main_engine.write_log(
                "[ChartWindow] 当前合约为空",
                "ChartWindow"
            )
            return

        # 提示用户重新加载数据
        self.main_engine.write_log(
            "[多周期] 已切换到多周期模式，请选择起始时间后点击'加载'按钮",
            "ChartWindow"
        )

        try:
            from vnpy.trader.utility import extract_vt_symbol

            symbol, exchange = extract_vt_symbol(self.current_vt_symbol)

            # 从 history_data 获取时间范围
            if self.history_data:
                start_datetime = self.history_data[0].datetime
                # 使用当前时间作为结束时间，而不是 history_data 的最后时间
                # 原因：history_data 可能不包含最新的实时K线
                end_datetime = datetime.now()

                self.main_engine.write_log(
                    f"[ChartWindow] 同步数据到多周期模式 - "
                    f"合约: {self.current_vt_symbol}, "
                    f"数据量: {len(self.history_data)}, "
                    f"时间范围: {start_datetime} ~ {end_datetime}",
                    "ChartWindow"
                )
            else:
                # 如果没有 history_data，使用 start_datetime 和当前时间
                start_datetime = self.start_datetime.dateTime().toPython()
                end_datetime = datetime.now()

                self.main_engine.write_log(
                    f"[ChartWindow] 同步数据到多周期模式（使用时间范围）- "
                    f"合约: {self.current_vt_symbol}, "
                    f"时间范围: {start_datetime} ~ {end_datetime}",
                    "ChartWindow"
                )

            # 如果MultiTimeframeWidget有switch_symbol方法，异步调用它
            if hasattr(self.multi_timeframe_widget, 'switch_symbol'):
                # 注意：MultiTimeframeWidget 的 load_bar_data 需要 symbol（不带交易所后缀）
                # 而不是 vt_symbol（带交易所后缀）
                self.main_engine.write_log(
                    f"[ChartWindow] 准备加载多周期数据 - "
                    f"symbol: {symbol}, exchange: {exchange}, "
                    f"start: {start_datetime}, end: {end_datetime}",
                    "ChartWindow"
                )
                
                # 创建并显示进度对话框（借鉴 DataManager 设计）
                progress = MultiTimeframeLoadProgressDialog(self)
                progress.show()
                
                # 强制处理事件，确保进度对话框显示
                QtWidgets.QApplication.processEvents()
                
                # 定义进度回调函数
                def on_progress(message: str, progress_value: int):
                    """进度回调，在主线程中更新UI"""
                    progress.set_status(message)
                    progress.set_progress(progress_value)
                
                # 使用 QTimer 在主线程中异步执行
                def _load_multi_data():
                    try:
                        # 调用 switch_symbol，传入进度回调
                        self.multi_timeframe_widget.switch_symbol(
                            vt_symbol=symbol,
                            exchange=exchange,
                            start=start_datetime,
                            end=end_datetime,
                            progress_callback=on_progress
                        )
                        
                        progress.set_completed()
                        self.main_engine.write_log("[ChartWindow] 多周期数据加载完成")
                        
                        # 延迟关闭，让用户看到完成状态
                        QtCore.QTimer.singleShot(800, progress.close)
                        
                    except Exception as e:
                        error_msg = str(e).replace("{", "{{").replace("}", "}}")
                        self.main_engine.write_log(f"[ChartWindow] 多周期数据加载失败: {error_msg}")
                        progress.set_error(f"加载失败: {error_msg}")
                        # 3秒后自动关闭
                        QtCore.QTimer.singleShot(3000, progress.close)
                
                # 延迟 50ms 执行
                QtCore.QTimer.singleShot(50, _load_multi_data)
            else:
                # 如果还没有switch_symbol方法，记录日志
                self.main_engine.write_log(
                    "[ChartWindow] MultiTimeframeWidget.switch_symbol() 方法尚未实现",
                    "ChartWindow"
                )
        except Exception as e:
            self.main_engine.write_log(
                f"[ChartWindow] 同步数据到多周期模式失败: {e}",
                "ChartWindow"
            )

    def switch_chart(self) -> None:
        """
        切换到新的合约图表

        Event handling when switching contracts:
        - 不需要取消注册和重新注册事件监听器
        - process_tick_event 方法已经通过过滤 current_vt_symbol 来处理，
          只处理当前显示合约的 tick，因此切换合约时只需更新 current_vt_symbol
        - 这种设计避免了频繁的事件注册/注销操作，提高了性能
        """
        vt_symbol: str = str(self.symbol_line.text()).strip()
        if not vt_symbol:
            self.status_label.setText(_("请输入有效的合约代码"))
            return

        if vt_symbol == self.current_vt_symbol:
            return

        # When switching contracts, event listeners remain unchanged, only update current contract code
        # process_tick_event 会通过过滤 current_vt_symbol 自动处理新合约的 tick
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
        except Exception:
            # 如果提取失败，使用标准BarGenerator
            self.bg = BarGenerator(self.on_bar)

        # 更新窗口标题（显示合约和周期）
        interval_name = self.interval_combo.currentText()
        self.setWindowTitle(_("K线图表 - {} - {}").format(vt_symbol, interval_name))

        # 更新状态
        self.status_label.setText(_("正在加载 {} 的历史数据...").format(vt_symbol))

        # 设置图表的 VT symbol（用于画线交易功能）
        self.chart.set_vt_symbol(vt_symbol)

        # 更新模拟功能按钮状态（切换合约时更新）
        self._update_simulate_buttons_state()

        # 注意：不再自动同步数据到多周期
        # 用户需要点击"加载"按钮来加载数据
        # 加载历史K线数据（最近7天的1分钟数据）
        if self.display_mode != "multi":
            self.load_history_data(vt_symbol)

        # 订阅行情数据（订阅后可能会收到tick数据，从而更新按钮状态）
        # 注意：这里不直接调用subscribe_tick，因为可能没有gateway
        # 按钮状态会在收到tick事件时自动更新

    def refresh_chart(self) -> None:
        """刷新当前图表"""
        if not self.current_vt_symbol:
            return
        
        # 检测当前显示模式
        if self.display_mode == "multi" and self.multi_timeframe_widget:
            # 多周期模式：独立加载（不依赖单周期）
            self._load_multi_timeframe_data()
        else:
            # 单周期模式：使用原有逻辑
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

            # 设置图表的 VT symbol（用于画线交易功能）
            self.chart.set_vt_symbol(self.current_vt_symbol)

            # 更新模拟功能按钮状态
            self._update_simulate_buttons_state()

            self.status_label.setStyleSheet("color: #888; font-size: 12px;")
            self.status_label.setText(_("正在刷新 {} 的数据...").format(self.current_vt_symbol))
            
            # 单周期模式：加载历史数据
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
        """跳转到指定日期时间（T070）"""
        # 如果当前是多周期模式，使用 MultiTimeframeWidget 的图表
        if self.display_mode == "multi" and self.multi_timeframe_widget:
            chart = self.multi_timeframe_widget._chart
            # 获取多周期模式的历史数据（从主管理器）
            if hasattr(self.multi_timeframe_widget, '_main_manager'):
                all_bars = self.multi_timeframe_widget._main_manager.get_all_bars()
                if not all_bars:
                    return

                # 获取目标日期时间
                target_qdt = self.goto_date.dateTime()
                target_py = target_qdt.toPython()

                # 在历史数据中查找最接近的K线索引
                target_ix = None
                min_diff = None

                for ix, bar in enumerate(all_bars):
                    # 比较时间差（忽略时区）
                    bar_dt = bar.datetime.replace(tzinfo=None)
                    target_dt = target_py.replace(tzinfo=None) if hasattr(target_py, 'tzinfo') else target_py

                    diff = abs((bar_dt - target_dt).total_seconds())

                    if min_diff is None or diff < min_diff:
                        min_diff = diff
                        target_ix = ix

                if target_ix is not None:
                    # 计算滚动条位置（让目标K线显示在视图中央）
                    visible_bars = chart._bar_count
                    right_ix = target_ix + visible_bars // 2

                    total_bars = len(all_bars)
                    future_bars = self._get_future_bars_for_interval("1m")
                    max_right_ix = total_bars + future_bars

                    right_ix = max(visible_bars, min(max_right_ix, right_ix))

                    # 更新图表视图
                    chart._right_ix = right_ix
                    chart._update_x_range()

                    # 更新滚动条位置
                    if max_right_ix > visible_bars:
                        slider_value = int((right_ix - visible_bars) / (max_right_ix - visible_bars) * 100)
                        slider_value = max(0, min(100, slider_value))
                        self.time_slider.blockSignals(True)
                        self.time_slider.setValue(slider_value)
                        self.time_slider.blockSignals(False)

                    # 更新状态
                    bar = all_bars[target_ix]
                    self.status_label.setText(
                        _("已跳转到 {} | 索引 {}/{}").format(
                            bar.datetime.strftime("%m-%d %H:%M"),
                            target_ix + 1,
                            total_bars
                        )
                    )
            return

        # 单周期模式：原有逻辑
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
        """时间滚动条值改变时更新图表视图（横向滚动）（T068, T069）"""
        # 如果当前是多周期模式，使用 MultiTimeframeWidget 的图表
        if self.display_mode == "multi" and self.multi_timeframe_widget:
            chart = self.multi_timeframe_widget._chart
            # 获取多周期模式的历史数据（从主管理器）
            if hasattr(self.multi_timeframe_widget, '_main_manager'):
                all_bars = self.multi_timeframe_widget._main_manager.get_all_bars()
                total_bars = len(all_bars)
                if total_bars == 0:
                    return

                # 获取当前显示的K线数量
                visible_bars = chart._bar_count

                # 根据当前周期获取未来空间K线数量（多周期模式使用1分钟周期）
                future_bars = self._get_future_bars_for_interval("1m")

                # 先确保图表的x轴限制已扩展
                if hasattr(self, 'extend_chart_x_limit'):
                    # 临时切换到 chart 以扩展限制
                    original_chart = self.chart
                    self.chart = chart
                    self.extend_chart_x_limit()
                    self.chart = original_chart

                # 根据滚动条位置计算右边界索引
                max_right_ix = total_bars + future_bars
                min_right_ix = visible_bars

                right_ix = int(min_right_ix + (max_right_ix - min_right_ix) * value / 100)
                right_ix = max(visible_bars, min(max_right_ix, right_ix))

                # 更新图表视图
                chart._right_ix = right_ix
                chart._update_x_range()
            return

        # 单周期模式：原有逻辑
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
        """加载历史K线数据（已优化：智能下载策略）"""
        from threading import Thread
        from datetime import datetime, timedelta
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
                from vnpy.trader.database import get_database

                symbol, exchange = extract_vt_symbol(vt_symbol)

                # 起始时间使用用户选择，结束时间使用当前最新时间
                local_tz = ZoneInfo(get_localzone_name())
                user_start: datetime = start_py.replace(tzinfo=local_tz)
                end: datetime = datetime.now(local_tz)  # 结束时间始终为当前最新

                data = None

                # 根据数据源加载数据
                if data_source == self.DATA_SOURCE_CSV:
                    # 从CSV文件加载
                    data = self._load_from_csv(csv_path, symbol, exchange, interval_enum, user_start, end)
                else:
                    # 从数据库加载（用户选择了"从数据库加载"）
                    database = get_database()
                    
                    # 从数据库加载（用户选择了"从数据库加载"）
                    data = database.load_bar_data(
                        symbol,
                        exchange,
                        interval_enum,
                        user_start,  # 始终使用用户选择的起始时间
                        end
                    )

                    # ============================================================
                    # 🚀 优化：智能下载策略（只针对1分钟周期）
                    # 目的：减少从 FUTU API 下载的数据量
                    # ============================================================
                    if interval_enum == Interval.MINUTE:
                        # 分析数据库状态，决定下载策略
                        download_start, need_download = self._get_optimized_load_strategy(
                            database, symbol, exchange, user_start, end
                        )
                        
                        if need_download:
                            # 需要从FUTU下载（数据不全或过期）
                            # 注意：download_start 可能不同于 user_start
                            # - 如果数据不全：download_start = user_start（全量下载）
                            # - 如果数据较旧：download_start = now - 7天（只下载最近7天）
                            self.main_engine.write_log(
                                f"[加载优化] 需要从 FUTU API 下载数据 ({download_start} ~ {end})"
                            )
                            # 调用现有的补齐逻辑
                            data = self._fill_missing_bars(
                                data, symbol, exchange, interval_enum, download_start, end, database
                            )
                        else:
                            self.main_engine.write_log(
                                f"[加载优化] 数据库数据足够新（< 1小时），跳过下载"
                            )

                    # 如果数据库中没有数据或数据不完整，根据周期类型进行处理
                    # 对于5分钟、1小时和4小时数据，尝试从1分钟数据自动合成补齐
                    if interval_enum in [Interval.MINUTE_5, Interval.HOUR, Interval.HOUR_4]:
                        # 检测数据中的缺失时间段并补齐
                        data = self._fill_missing_bars(
                            data, symbol, exchange, interval_enum, user_start, end, database
                        )
                    elif interval_enum == Interval.MINUTE and not data:
                        # 对于1分钟数据，如果数据库中没有数据，尝试从FUTU API获取
                        self.main_engine.write_log(f"数据库中没有{interval_enum.value}数据，尝试从FUTU API获取...")
                        data = self._fetch_bars_from_futu(
                            symbol, exchange, interval_enum, start, end
                        )
                        if data:
                            self.main_engine.write_log(f"从FUTU API获取了 {len(data)} 根{interval_enum.value}K线")
                        else:
                            self.main_engine.write_log(f"无法从FUTU API获取{interval_enum.value}数据，请先在DataManager中下载数据")

                # 对于1小时数据，如果从CSV加载，需要检测并补齐gap（这个主要是用于CSV到当前时间的gap，不是历史数据的gap）
                if data and interval_enum == Interval.HOUR and data_source == self.DATA_SOURCE_CSV:
                    # 检测并补齐gap
                    data = self._detect_and_fill_gap(data, vt_symbol, interval_enum)

                # 发送历史数据更新信号（仅用于单周期模式）
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

        if not csv_path:
            self.main_engine.write_log("未选择CSV文件")
            return []

        try:
            bars: list[BarData] = []

            with open(csv_path, encoding="utf-8") as f:
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

                    except (ValueError, KeyError):
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
                self.main_engine.write_log("无法获取DataManager引擎，请确保DataManager模块已加载")
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
            self.main_engine.write_log("无法导入DataManager模块，请确保DataManager已安装")
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

            # 解析合约代码和交易所（提前解析，避免后面使用时未定义）
            symbol, exchange = extract_vt_symbol(vt_symbol)

            # ✅ 对于1分钟和5分钟周期，排除当前时间周期，避免补齐未完成的K线
            # 这样可以确保最后几根K线的数据准确，不会被未完成的K线覆盖
            from vnpy.trader.period_utils import get_period_start
            gap_end = now

            if interval == Interval.MINUTE:
                # 1分钟周期：排除当前分钟
                current_minute_start = get_period_start(now, Interval.MINUTE, exchange)
                if current_minute_start and current_minute_start < now:
                    # 当前分钟已经开始，排除当前分钟
                    gap_end = current_minute_start
                    self.main_engine.write_log(
                        f"[数据补齐] 1分钟周期：排除当前分钟K线 ({current_minute_start.strftime('%H:%M')})，"
                        f"避免补齐未完成的K线"
                    )
            elif interval == Interval.MINUTE_5:
                # 5分钟周期：排除当前5分钟周期
                current_period_start = get_period_start(now, Interval.MINUTE_5, exchange)
                if current_period_start and current_period_start < now:
                    # 当前5分钟周期已经开始，排除当前周期
                    gap_end = current_period_start
                    self.main_engine.write_log(
                        f"[数据补齐] 5分钟周期：排除当前5分钟周期K线 ({current_period_start.strftime('%H:%M')})，"
                        f"避免补齐未完成的K线"
                    )

            # 计算需要补齐的时间范围
            gap_start = last_bar_time + timedelta(minutes=1) if interval == Interval.MINUTE else (
                last_bar_time + timedelta(minutes=5) if interval == Interval.MINUTE_5 else
                last_bar_time + timedelta(hours=1) if interval == Interval.HOUR else
                last_bar_time + timedelta(hours=4) if interval == Interval.HOUR_4 else
                last_bar_time + timedelta(days=1)
            )

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
                        "[数据补齐] 未能获取到1分钟数据用于补齐。"
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
            # 使用全局单例 Datafeed（检查健康状态，运行时断开会提示并尝试重连）
            datafeed = self._get_datafeed(
                show_error_dialog=False,  # 不在这里弹窗，由 check_health 处理
                check_health=True  # 检查连接健康状态
            )

            if datafeed is None:
                # 全局 Datafeed 不可用 - 数据补齐失败，但不阻止查看已有数据
                self.main_engine.write_log(
                    "[数据补齐] Datafeed 服务不可用，无法补齐数据缺口。"
                    "已有数据仍可查看。"
                )
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
                self.main_engine.write_log(f"[数据补齐] 从Datafeed获取了 {len(bars)} 根K线数据")
            else:
                self.main_engine.write_log("[数据补齐] Datafeed未返回数据")

            return bars

        except Exception as e:
            error_msg = str(e).replace("{", "{{").replace("}", "}}")
            self.main_engine.write_log(f"[数据补齐] 从Datafeed获取数据失败: {error_msg}")
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
            # 标记开盘价是否已更新（新创建的K线，开盘价已设置）
            self._current_bar_open_price_updated = (open_price and open_price > 0)

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
            # 标记开盘价是否已更新（新创建的K线，开盘价已设置）
            self._current_bar_open_price_updated = (open_price and open_price > 0)

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

            # ✅ 实时更新时，如果开盘价还没有被正确设置，尝试更新开盘价
            # 这对于从历史数据标记的当前K线很重要，因为历史数据的开盘价可能不准确
            # 只有在开盘价还没有被正确设置时才更新（避免覆盖已正确的开盘价）
            if (self._current_bar.open_price <= 0 or
                (hasattr(self, '_current_bar_open_price_updated') and not self._current_bar_open_price_updated)):
                # 尝试获取正确的开盘价
                correct_open_price = self.open_price_helper.get_period_open_price(
                    tick_period, interval, tick.vt_symbol, tick=tick,
                    minute_bar_generator=self.bg, history_data=self.history_data
                )

                if correct_open_price and correct_open_price > 0:
                    if self._current_bar.open_price != correct_open_price:
                        old_open_price = self._current_bar.open_price
                        self._current_bar.open_price = correct_open_price
                        self._current_bar_open_price_updated = True
                        self.main_engine.write_log(
                            f"[实时K线] {interval.value}K线({tick_period.strftime('%H:%M')}) "
                            f"开盘价已更新: {old_open_price} -> {correct_open_price} (实时更新时修正)"
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
        # Performance monitoring - measure chart refresh latency (large timeframe update)
        chart_refresh_start_time = None
        if self._perf_monitoring_enabled:
            chart_refresh_start_time = time.perf_counter()

        self.chart.update_bar(self._current_bar)

        # Performance monitoring - log chart refresh latency (large timeframe update)
        if self._perf_monitoring_enabled and chart_refresh_start_time is not None:
            chart_refresh_end_time = time.perf_counter()
            chart_refresh_latency_ms = (chart_refresh_end_time - chart_refresh_start_time) * 1000
            self._record_performance_metric("chart_refresh", chart_refresh_latency_ms)

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
        # 添加调试日志
        self.main_engine.write_log(
            f"[ChartWindow] process_history_data 被调用，数据量: {len(history) if history else 0}"
        )

        if not history:
            self.status_label.setText(_("未找到历史数据，等待实时行情..."))
            self.history_loaded = True
            self.main_engine.write_log("[ChartWindow] 无历史数据，已设置 history_loaded = True")
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

        # ✅ 对于1分钟和5分钟周期，确保最后几根K线与实时数据对齐
        # 删除当前时间周期的K线，让实时tick创建新的当前K线
        if interval_enum in (Interval.MINUTE, Interval.MINUTE_5) and self.history_data:
            self._remove_current_period_bars_for_alignment(interval_enum)

        # 更新图表（使用修正后的历史数据）
        self.chart.update_history(self.history_data)
        self.history_loaded = True

        # 添加调试日志
        self.main_engine.write_log(
            f"[ChartWindow] 历史数据加载完成，已设置 history_loaded = True，"
            f"数据量: {len(self.history_data)}"
        )

        # 更新时间范围标签
        if self.history_data:
            start_time = self.history_data[0].datetime.strftime("%m-%d %H:%M")
            end_time = self.history_data[-1].datetime.strftime("%m-%d %H:%M")
            self.time_start_label.setText(start_time)
            self.time_end_label.setText(end_time)

        # 注意：不再自动同步数据到多周期模式
        # 多周期模式下的数据加载由 _load_multi_timeframe_data() 独立处理
        # if self.display_mode == "multi" and self.multi_timeframe_widget:
        #     self.main_engine.write_log("[ChartWindow] 历史数据加载完成，同步到多周期模式")
        #     self.sync_data_to_multi_timeframe()

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

        # 订阅实时行情数据（用于实时更新K线）
        if self.current_vt_symbol:
            self.subscribe_tick(self.current_vt_symbol)

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
        # 标记当前K线的开盘价是否已更新（用于实时更新时判断是否需要更新开盘价）
        self._current_bar_open_price_updated = False

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
                # 开始修正K线开盘价

                correct_open_price = self.open_price_helper.get_period_open_price(
                    period_start,  # 使用周期起始时间，而不是bar.datetime
                    bar.interval,
                    bar.vt_symbol,
                    tick=temp_tick,
                    minute_bar_generator=self.bg,
                    history_data=self.history_data
                )

                # 获取到的开盘价

                # 如果无法获取correct_open_price，说明该周期第一根1分钟K线可能不存在
                # 此时不应该修正，因为current_open_price可能已经是正确的（来自DataManager的合成逻辑）
                if not correct_open_price or correct_open_price <= 0:
                    # 无法获取开盘价，跳过修正
                    continue

                # 如果获取到了正确的开盘价，且与当前开盘价不同，则更新
                if bar.open_price != correct_open_price:
                    old_open_price = bar.open_price
                    price_diff = abs(old_open_price - correct_open_price)

                    # 检查：如果correct_open_price来自该周期内第二根或更后的1分钟K线，
                    # 而current_open_price已经正确，则不应该修正
                    # 这里通过比较差异来判断：如果差异很小（<1.0），可能是数据精度问题，不应该修正
                    # 或者，如果无法找到period_start对应的1分钟K线，说明它不存在，应该保持current_open_price
                    # 价格差异计算

                    bar.open_price = correct_open_price
                    self.history_data[i] = bar
                    corrected_count += 1

                    # 执行修正K线开盘价

                    # 暂时注释掉开盘价修正日志，减少日志输出
                    # self.main_engine.write_log(
                    #     f"[开盘价修正] {bar.interval.value}K线({bar.datetime.strftime('%H:%M')}) "
                    #     f"开盘价已修正: {old_open_price} -> {correct_open_price}"
                    # )
                else:
                    # 无需修正，开盘价已正确
                    pass

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

                # 暂时注释掉开盘价修正日志，减少日志输出
                # self.main_engine.write_log(
                #     f"[开盘价修正] {self._current_bar.interval.value}K线({self._current_bar.datetime.strftime('%H:%M')}) "
                #     f"开盘价已修正: {old_open_price} -> {correct_open_price} "
                #     f"(从历史数据标记时修正)"
                # )

                # 更新历史数据中的当前K线
                if self._current_bar_index >= 0 and self._current_bar_index < len(self.history_data):
                    self.history_data[self._current_bar_index] = self._current_bar

                # 更新图表显示
                if hasattr(self, 'chart') and self.chart:
                    self.chart.update_bar(self._current_bar)
        except Exception as e:
            error_msg = str(e).replace("{", "{{").replace("}", "}}")
            self.main_engine.write_log(f"[开盘价修正] 更新失败: {error_msg}")

    def _remove_current_period_bars_for_alignment(self, interval: "Interval") -> None:
        """
        对于1分钟和5分钟周期，删除当前时间周期的K线，确保实时数据对齐
        
        问题：
        1. 如果历史数据的最后一根K线是当前分钟/5分钟的，实时更新时会创建新的当前K线，导致重复或不一致
        2. 数据补齐时可能会包含未完成的当前周期K线，这些K线数据不准确，需要删除
        
        解决：
        - 删除当前时间周期的K线（1分钟周期：当前分钟；5分钟周期：当前5分钟周期）
        - 让实时tick创建新的当前K线，确保历史数据和实时数据无缝对齐
        - 删除最后几根可能是当前时间周期的K线，确保数据准确性
        - ✅ 对于1分钟周期，保存被删除K线的开盘价，用于后续修正BarGenerator创建的新K线
        """
        from datetime import datetime
        from vnpy.trader.constant import Interval
        from vnpy.trader.utility import ZoneInfo
        from tzlocal import get_localzone_name
        from vnpy.trader.period_utils import get_period_start
        from vnpy.trader.utility import extract_vt_symbol

        if not self.history_data:
            return

        try:
            # 获取当前时间
            local_tz = ZoneInfo(get_localzone_name())
            now = datetime.now(local_tz)

            # 获取当前时间所属的周期开始时间
            _, exchange = extract_vt_symbol(self.history_data[-1].vt_symbol)
            current_period_start = get_period_start(now, interval, exchange)

            if not current_period_start:
                return

            # 从后往前检查，删除所有属于当前时间周期的K线
            removed_count = 0
            # ✅ 对于1分钟周期，保存被删除K线的开盘价
            if interval == Interval.MINUTE:
                self._removed_minute_bar_open_price = None
                self._removed_minute_bar_datetime = None

            while self.history_data:
                last_bar = self.history_data[-1]
                last_bar_period_start = get_period_start(last_bar.datetime, interval, exchange)

                # 如果最后一根K线是当前时间周期的，删除它
                if last_bar_period_start and last_bar_period_start == current_period_start:
                    removed_bar = self.history_data.pop()
                    removed_count += 1

                    # ✅ 对于1分钟周期，保存被删除K线的开盘价和datetime
                    if interval == Interval.MINUTE and removed_bar.open_price > 0:
                        self._removed_minute_bar_open_price = removed_bar.open_price
                        self._removed_minute_bar_datetime = removed_bar.datetime.replace(second=0, microsecond=0)
                        self.main_engine.write_log(
                            f"[数据对齐] 删除当前1分钟周期的K线 ({removed_bar.datetime.strftime('%H:%M')})，"
                            f"保存开盘价: {removed_bar.open_price}，等待实时tick创建新的当前K线以确保对齐"
                        )
                    else:
                        self.main_engine.write_log(
                            f"[数据对齐] 删除当前{interval.value}周期的K线 ({removed_bar.datetime.strftime('%H:%M')})，"
                            f"等待实时tick创建新的当前K线以确保对齐"
                        )
                else:
                    break

            if removed_count > 0:
                self.main_engine.write_log(
                    f"[数据对齐] 共删除了 {removed_count} 根当前{interval.value}周期的K线，"
                    f"确保实时数据准确对齐"
                )
        except Exception as e:
            error_msg = str(e).replace("{", "{{").replace("}", "}}")
            self.main_engine.write_log(f"[数据对齐] 删除当前周期K线失败: {error_msg}")

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

    def process_order_event(self, event: Event) -> None:
        """处理订单事件，转发给图表的DrawingOrderController"""
        from vnpy.trader.object import OrderData

        order: OrderData = event.data
        if self.chart and self.chart.get_drawing_order_controller():
            self.chart.get_drawing_order_controller().update_line_from_order(order)

    def toggle_drawing_mode(self) -> None:
        """切换画线下单模式（T053）"""
        # 根据当前模式选择对应的 controller
        if self.display_mode == "multi" and self.multi_timeframe_widget:
            # 多周期模式：使用 MultiTimeframeWidget 的 controller
            self.main_engine.write_log("[画线模式] 切换画线模式 (多周期模式)")
            self.main_engine.write_log(f"[画线模式] 当前合约: {self.current_vt_symbol}")
            
            controller = self.multi_timeframe_widget.get_drawing_order_controller()
            chart_widget = self.multi_timeframe_widget._chart if hasattr(self.multi_timeframe_widget, '_chart') else None
            
            # 重新设置参数，确保正确
            if chart_widget:
                self.main_engine.write_log("[画线模式] 设置 chart_widget 参数")
                chart_widget.set_main_engine(self.main_engine)
                chart_widget.set_vt_symbol(self.current_vt_symbol)
                
                if controller:
                    # 确保 controller 也设置了参数
                    if hasattr(controller, 'set_vt_symbol'):
                        controller.set_vt_symbol(self.current_vt_symbol)
                        self.main_engine.write_log(f"[画线模式] 已设置 controller.vt_symbol: {self.current_vt_symbol}")
                    if hasattr(controller, 'set_main_engine'):
                        controller.set_main_engine(self.main_engine)
                        self.main_engine.write_log("[画线模式] 已设置 controller.main_engine")
                    
                    self.main_engine.write_log(f"[画线模式] 验证: controller._vt_symbol = {getattr(controller, '_vt_symbol', 'NOT SET')}")
                    self.main_engine.write_log(f"[画线模式] 验证: controller._main_engine = {getattr(controller, '_main_engine', 'NOT SET')}")
        else:
            # 单周期模式：使用 ChartWidget 的 controller
            controller = self.chart.get_drawing_order_controller() if self.chart else None
            chart_widget = self.chart

        if not controller:
            self.main_engine.write_log("[画线模式] 错误: controller 为 None，无法切换画线模式")
            self.drawing_mode_button.setChecked(False)
            return

        if self.drawing_mode_button.isChecked():
            self.main_engine.write_log("[画线模式] 启用画线模式")
            controller.enable()
            self.drawing_mode_button.setText(_("画线下单 (已启用)"))
            self.drawing_mode_button.setStyleSheet("background-color: #4CAF50; color: white;")
            # 让图表获得焦点，以便接收键盘事件（如ESC键）
            if chart_widget:
                chart_widget.setFocus()
            self.main_engine.write_log("[画线模式] 画线模式已启用")
        else:
            self.main_engine.write_log("[画线模式] 禁用画线模式")
            controller.disable()
            self.drawing_mode_button.setText(_("画线下单"))
            self.drawing_mode_button.setStyleSheet("")
            self.main_engine.write_log("[画线模式] 画线模式已禁用")

    def _on_drawing_mode_changed(self, enabled: bool) -> None:
        """画线下单模式状态变化回调（由ChartWidget调用，例如按下ESC键时）"""
        # 更新按钮状态以反映实际的状态
        if self.drawing_mode_button.isChecked() != enabled:
            # 直接更新按钮状态和UI，不触发toggle_drawing_mode（避免递归）
            self.drawing_mode_button.blockSignals(True)  # 临时阻止信号，避免触发toggle_drawing_mode
            self.drawing_mode_button.setChecked(enabled)
            if enabled:
                self.drawing_mode_button.setText(_("画线下单 (已启用)"))
                self.drawing_mode_button.setStyleSheet("background-color: #4CAF50; color: white;")
            else:
                self.drawing_mode_button.setText(_("画线下单"))
                self.drawing_mode_button.setStyleSheet("")
            self.drawing_mode_button.blockSignals(False)  # 恢复信号

    def _on_drawing_click(self, price: float) -> None:
        """处理画线模式下的点击事件（用于画线下单）"""
        from vnpy.chart.order_dialog import OrderDialog

        if not self.chart:
            return

        # 获取合约信息以获取最小变动单位和价格精度
        vt_symbol = self.current_vt_symbol
        pricetick = 1.0  # 默认值（MHImain 的最小变动单位是 1 个点）
        size = 1.0  # 默认值
        price_precision = 0  # 默认整数显示（MHImain）

        if vt_symbol:
            contract = self.main_engine.get_contract(vt_symbol)
            if contract:
                # 对于 MHImain，最小变动单位是 1 个点
                # 如果合约数据中的 pricetick 不正确，使用默认值 1.0
                pricetick = contract.pricetick if contract.pricetick > 0 else 1.0
                # 确保 pricetick 至少为 1.0（MHImain 的最小变动单位）
                pricetick = max(pricetick, 1.0)
                size = contract.size  # 合约乘数（一跳的价格数）
                self.main_engine.write_log(f"[画线下单] 合约信息: {vt_symbol}, pricetick={pricetick}, size={size}")

                # 尝试从 FUTU gateway 查询价格精度
                gateway_name = contract.gateway_name if hasattr(contract, 'gateway_name') else None
                if gateway_name:
                    gateway = self.main_engine.get_gateway(gateway_name)
                    if gateway and hasattr(gateway, 'quote_ctx'):
                        try:
                            # 尝试多种导入方式，确保兼容性
                            # update_and_run.bat 使用 pip install -e . 安装（可编辑模式）
                            # 已安装包和开发环境源文件应该是一致的，都指向 vnpy_futu/vnpy_futu/ 目录
                            # 但 setup.cfg 配置 packages = vnpy_futu，安装后可通过 vnpy_futu.futu_gateway 访问
                            convert_symbol_vt2futu = None
                            import_error_msgs = []

                            try:
                                # 方式1：从已安装的包导入（推荐方式，测试文件中使用）
                                # update_and_run.bat 使用 pip install -e . 安装（可编辑模式）
                                # 安装后包结构：vnpy_futu/futu_gateway.py（通过setup.cfg配置）
                                from vnpy_futu.futu_gateway import convert_symbol_vt2futu
                                self.main_engine.write_log("[画线下单] 成功导入convert_symbol_vt2futu: from vnpy_futu.futu_gateway")
                            except ImportError as e1:
                                import_error_msgs.append(f"方式1失败: from vnpy_futu.futu_gateway - {str(e1)}")
                                try:
                                    # 方式2：从源文件路径导入（开发环境，如果方式1失败）
                                    # 源文件结构：vnpy_futu/vnpy_futu/futu_gateway.py
                                    from vnpy_futu.vnpy_futu.futu_gateway import convert_symbol_vt2futu
                                    self.main_engine.write_log("[画线下单] 成功导入convert_symbol_vt2futu: from vnpy_futu.vnpy_futu.futu_gateway")
                                except ImportError as e2:
                                    import_error_msgs.append(f"方式2失败: from vnpy_futu.vnpy_futu.futu_gateway - {str(e2)}")
                                    try:
                                        # 方式3：从datafeed模块导入（备用）
                                        from vnpy_futu.datafeed import convert_symbol_vt2futu
                                        self.main_engine.write_log("[画线下单] 成功导入convert_symbol_vt2futu: from vnpy_futu.datafeed")
                                    except ImportError as e3:
                                        import_error_msgs.append(f"方式3失败: from vnpy_futu.datafeed - {str(e3)}")
                                        # 方式4：从gateway对象获取（如果gateway是FutuGateway实例）
                                        if hasattr(gateway, 'convert_symbol_vt2futu'):
                                            convert_symbol_vt2futu = gateway.convert_symbol_vt2futu
                                            self.main_engine.write_log("[画线下单] 从gateway对象获取convert_symbol_vt2futu")
                                        else:
                                            # 方式5：尝试从模块对象导入
                                            try:
                                                import vnpy_futu.futu_gateway as futu_gateway_module
                                                convert_symbol_vt2futu = futu_gateway_module.convert_symbol_vt2futu
                                                self.main_engine.write_log("[画线下单] 从模块对象获取convert_symbol_vt2futu")
                                            except Exception as e5:
                                                import_error_msgs.append(f"方式5失败: 从模块对象导入 - {str(e5)}")

                            if convert_symbol_vt2futu:
                                from vnpy.trader.constant import Exchange
                                futu_symbol = convert_symbol_vt2futu(vt_symbol.split('.')[0], Exchange(contract.exchange.value))
                                ret, data = gateway.quote_ctx.get_future_info(futu_symbol)
                                if ret == 0 and data is not None and not data.empty:
                                    # 从 FUTU API 获取 price_tick（如果存在）
                                    if 'price_tick' in data.columns:
                                        futu_pricetick = float(data['price_tick'].iloc[0])
                                        if futu_pricetick > 0:
                                            pricetick = futu_pricetick
                                            self.main_engine.write_log(f"[画线下单] 从FUTU API查询到pricetick: {pricetick}")

                                    # 根据 pricetick 计算价格精度
                                    # 如果 pricetick >= 1.0，显示整数；否则显示相应的小数位数
                                    if pricetick >= 1.0:
                                        price_precision = 0  # 整数显示
                                    else:
                                        # 计算需要的小数位数
                                        price_precision = len(str(pricetick).split('.')[-1].rstrip('0'))
                                        if price_precision == 0:
                                            price_precision = 0  # 整数
                                        else:
                                            price_precision = min(price_precision, 4)  # 最多4位小数

                                    self.main_engine.write_log(f"[画线下单] 价格精度: {price_precision} (pricetick={pricetick})")
                            else:
                                # 所有导入方式都失败
                                error_msg = "\n  ".join(import_error_msgs)
                                self.main_engine.write_log(
                                    f"[画线下单] FUTU模块导入失败，所有导入方式均失败:\n  {error_msg}\n"
                                    f"  请确认vnpy_futu模块已正确安装，使用默认pricetick: {pricetick}"
                                )
                        except ImportError as e:
                            # 如果vnpy_futu模块未安装或导入失败，记录详细错误信息
                            self.main_engine.write_log(
                                f"[画线下单] FUTU模块导入失败: {str(e)}\n"
                                f"  请确认vnpy_futu模块已正确安装，使用默认pricetick: {pricetick}"
                            )
                        except Exception as e:
                            # 其他错误（如API调用失败）记录详细错误信息
                            self.main_engine.write_log(
                                f"[画线下单] 查询FUTU API失败: {str(e)}\n"
                                f"  使用默认pricetick: {pricetick}"
                            )

        # 显示下单对话框
        dialog = OrderDialog(price=price, direction="long", pricetick=pricetick, size=size, parent=self.chart)
        # 设置价格精度
        dialog._price_precision = price_precision
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            params = dialog.get_order_params()
            self._create_pending_order_line(params)
        else:
            # 取消时隐藏预览线
            controller = self.chart.get_drawing_order_controller()
            if controller:
                controller.disable()
                controller.enable()  # 重新启用以保持画线模式

    def _create_pending_order_line(self, params: dict) -> None:
        """从画线模式创建挂单线（不立即下单，等待价格突破触发）"""

        vt_symbol = self.current_vt_symbol
        if not vt_symbol:
            return

        contract = self.main_engine.get_contract(vt_symbol)
        if not contract:
            self.main_engine.write_log(f"合约 {vt_symbol} 未找到，无法创建挂单线")
            return

        # 根据当前显示模式选择正确的图表（重要！）
        if self.display_mode == "multi" and self.multi_timeframe_widget:
            # 多周期模式：使用 MultiTimeframeWidget 的图表
            chart = self.multi_timeframe_widget._chart if hasattr(self.multi_timeframe_widget, '_chart') else None
            self.main_engine.write_log("[画线下单] 多周期模式：使用 multi_timeframe_widget._chart 创建价格线")
        else:
            # 单周期模式：使用 ChartWindow 的图表
            chart = self.chart
            self.main_engine.write_log("[画线下单] 单周期模式：使用 self.chart 创建价格线")
        
        if not chart:
            self.main_engine.write_log("[画线下单] 错误: chart 为 None")
            return
        
        # 添加挂单线到图表
        controller = chart.get_drawing_order_controller()
        if not controller:
            self.main_engine.write_log("[画线下单] 错误: controller 为 None")
            return

        # 将Direction枚举转换为"long"或"short"字符串
        from vnpy.trader.constant import Direction
        direction_str = "long" if params["direction"] == Direction.LONG else "short"

        line_id = controller.create_pending_order_line(
            price=params["price"],
            direction=direction_str
        )

        # 存储订单参数到挂单线（用于价格突破时下单）
        # 使用 controller 的额外存储来保存订单参数
        if not hasattr(controller, '_pending_order_params'):
            controller._pending_order_params = {}
        if not hasattr(controller, '_pending_line_relations'):
            controller._pending_line_relations = {}  # 挂单线ID -> [止损线ID, 止盈线ID]

        controller._pending_order_params[line_id] = {
            "params": params,
            "vt_symbol": vt_symbol,
            "contract": contract
        }

        # 初始化关联关系（存储止损/止盈线ID和点数信息）
        controller._pending_line_relations[line_id] = {
            "stop_loss": None,  # {"line_id": str, "points": int}
            "take_profit": None  # {"line_id": str, "points": int}
        }

        # 设置挂单参数到价格线对象（持久化到数据库）
        line = chart._price_line_manager.get_line(line_id)
        if line:
            # 设置挂单参数
            line.set_order_volume(params["volume"])
            line.set_order_offset(params["offset"].value if hasattr(params["offset"], 'value') else str(params["offset"]))

            # 获取价格精度并设置到chart和价格线
            price_precision = params.get("price_precision", 0)
            chart._price_precision = price_precision
            line.set_price_precision(price_precision)

            # 保存到数据库（PriceLineManager会自动保存）
            # 通过更新价格来触发保存（因为create_line已经保存了基本信息）
            chart._price_line_manager.update_line_price(line_id, params["price"])

        # 注册到价格突破监控
        # 使用ChartWidget的通用方法，与真实tickdata触发共用逻辑
        if line and chart._breakthrough_monitor:
            chart._breakthrough_monitor.register_line(
                line_id,
                line,
                chart._on_price_breakthrough
            )

        # 格式化价格显示
        price_precision = params.get("price_precision", 0)
        if price_precision == 0:
            price_str = f"{int(params['price'])}"
        else:
            price_str = f"{params['price']:.{price_precision}f}"

        self.main_engine.write_log(
            f"创建挂单线: {vt_symbol} {params['direction'].value} "
            f"{params['volume']}@{price_str} (等待价格突破触发)"
        )
        
        self.main_engine.write_log(f"[画线下单] 挂单线已创建: line_id={line_id}, 使用图表: {'multi' if self.display_mode == 'multi' else 'single'}")

        # 如果设置了止损，创建止损线
        stop_loss_price = params.get("stop_loss")
        if stop_loss_price is not None and stop_loss_price > 0:
            from vnpy.chart.price_line import PriceLineType
            # 获取方向字符串
            direction_str = params["direction"].value if hasattr(params["direction"], "value") else str(params["direction"])
            # 获取价格精度（从chart获取，如果chart有设置的话）
            price_precision = getattr(chart, '_price_precision', 0)
            stop_loss_line_id = chart._price_line_manager.create_line(
                price=stop_loss_price,
                line_type=PriceLineType.STOP_LOSS,
                direction=direction_str,
                movable=True,
                price_precision=price_precision
            )
            stop_loss_line = chart._price_line_manager.get_line(stop_loss_line_id)
            if stop_loss_line and chart._first_plot:
                chart._first_plot.addItem(stop_loss_line)
                # ✅ 挂单线的止损止盈线在创建后立即将创建时间设置为None，表示"未激活"
                # 只有在挂单成交后才会激活（设置创建时间），此时才会被触发检查
                stop_loss_line.set_creation_time_explicit(None)  # 设置为None，表示未激活

                # 建立关联关系（保存止损线ID和点数）
                stop_loss_points = params.get("stop_loss_points", 50)
                controller._pending_line_relations[line_id]["stop_loss"] = {
                    "line_id": stop_loss_line_id,
                    "points": stop_loss_points
                }
                # 从挂单线获取订单手数并设置到止损线
                if line:
                    order_volume = line.get_order_volume()
                    if order_volume is not None and order_volume > 0:
                        stop_loss_line.set_volume(order_volume)
                # 添加详细日志
                direction_str = params["direction"].value if hasattr(params["direction"], "value") else str(params["direction"])
                order_price = params.get("price", 0)
                # 格式化价格显示
                price_precision = getattr(self.chart, '_price_precision', 0)
                if price_precision == 0:
                    price_str = f"{int(stop_loss_price)}"
                    order_price_str = f"{int(order_price)}"
                else:
                    price_str = f"{stop_loss_price:.{price_precision}f}"
                    order_price_str = f"{order_price:.{price_precision}f}"

                self.main_engine.write_log(
                    f"创建止损线: {price_str} (关联挂单线: {line_id}, 点数: {stop_loss_points}, "
                    f"订单价格: {order_price_str}, 方向: {direction_str}, size: {contract.size if contract else 'N/A'})"
                )

        # 如果设置了止盈，创建止盈线
        take_profit_price = params.get("take_profit")
        if take_profit_price is not None and take_profit_price > 0:
            from vnpy.chart.price_line import PriceLineType
            # 获取方向字符串
            direction_str = params["direction"].value if hasattr(params["direction"], "value") else str(params["direction"])
            # 获取价格精度（从chart获取，如果chart有设置的话）
            price_precision = getattr(self.chart, '_price_precision', 0)
            take_profit_line_id = chart._price_line_manager.create_line(
                price=take_profit_price,
                line_type=PriceLineType.TAKE_PROFIT,
                direction=direction_str,
                movable=True,
                price_precision=price_precision
            )
            take_profit_line = chart._price_line_manager.get_line(take_profit_line_id)
            if take_profit_line and chart._first_plot:
                chart._first_plot.addItem(take_profit_line)
                # ✅ 挂单线的止损止盈线在创建后立即将创建时间设置为None，表示"未激活"
                # 只有在挂单成交后才会激活（设置创建时间），此时才会被触发检查
                take_profit_line.set_creation_time_explicit(None)  # 设置为None，表示未激活

                # 建立关联关系（保存止盈线ID和点数）
                take_profit_points = params.get("take_profit_points", 50)
                controller._pending_line_relations[line_id]["take_profit"] = {
                    "line_id": take_profit_line_id,
                    "points": take_profit_points
                }
                # 从挂单线获取订单手数并设置到止盈线
                if line:
                    order_volume = line.get_order_volume()
                    if order_volume is not None and order_volume > 0:
                        take_profit_line.set_volume(order_volume)
                # 添加详细日志
                order_price = params.get("price", 0)
                # 格式化价格显示
                price_precision = getattr(self.chart, '_price_precision', 0)
                if price_precision == 0:
                    price_str = f"{int(take_profit_price)}"
                    order_price_str = f"{int(order_price)}"
                else:
                    price_str = f"{take_profit_price:.{price_precision}f}"
                    order_price_str = f"{order_price:.{price_precision}f}"

                self.main_engine.write_log(
                    f"创建止盈线: {price_str} (关联挂单线: {line_id}, 点数: {take_profit_points}, "
                    f"订单价格: {order_price_str}, 方向: {direction_str}, size: {contract.size if contract else 'N/A'})"
                )

    def _on_price_breakthrough(self, event, controller) -> None:
        """
        处理价格突破事件，触发下单（已废弃，现在使用ChartWidget的通用方法）

        注意：此方法保留用于向后兼容，实际逻辑已迁移到ChartWidget.trigger_pending_order_breakthrough
        """
        # 直接调用ChartWidget的通用方法
        # ChartWidget的_on_price_breakthrough会调用trigger_pending_order_breakthrough
        if self.chart:
            self.chart._on_price_breakthrough(event)

    def simulate_trade_breakthrough(self) -> None:
        """
        模拟tick突破挂单线，触发挂单成交（用于休市测试）

        功能：
        1. 获取所有挂单线（PENDING类型）
        2. 模拟一个tick数据，价格突破挂单线
        3. 触发价格突破监控，从而触发下单
        4. 下单后会自动更新持仓和浮动盈亏
        """
        self.main_engine.write_log("[模拟成交] 方法被调用")

        # 根据当前显示模式选择正确的图表
        if self.display_mode == "multi" and self.multi_timeframe_widget:
            # 多周期模式：使用 MultiTimeframeWidget 的图表
            chart = self.multi_timeframe_widget._chart if hasattr(self.multi_timeframe_widget, '_chart') else None
            self.main_engine.write_log("[模拟成交] 使用多周期图表")
        else:
            # 单周期模式：使用 ChartWindow 的图表
            chart = self.chart
            self.main_engine.write_log("[模拟成交] 使用单周期图表")

        if not chart:
            self.main_engine.write_log("[模拟成交] 图表未初始化，无法模拟成交")
            return

        # 获取所有挂单线
        price_line_manager = chart._price_line_manager
        if not price_line_manager:
            self.main_engine.write_log("[模拟成交] 价格线管理器未初始化")
            return

        all_lines = price_line_manager.get_all_lines()
        self.main_engine.write_log(f"[模拟成交] 找到 {len(all_lines)} 条价格线")

        # 筛选出挂单线
        from vnpy.chart.price_line import PriceLineType
        pending_lines = {
            line_id: line
            for line_id, line in all_lines.items()
            if line.get_line_type() == PriceLineType.PENDING
        }

        self.main_engine.write_log(f"[模拟成交] 找到 {len(pending_lines)} 条挂单线")

        if not pending_lines:
            self.main_engine.write_log("[模拟成交] 没有找到挂单线，无法模拟成交")
            QtWidgets.QMessageBox.information(
                self,
                _("提示"),
                _("当前没有挂单线，请先创建挂单线后再使用模拟成交功能。")
            )
            return

        # 获取当前合约信息
        vt_symbol = self.current_vt_symbol
        if not vt_symbol:
            self.main_engine.write_log("未选择合约，无法模拟成交")
            QtWidgets.QMessageBox.information(
                self,
                _("提示"),
                _("请先选择合约后再使用模拟成交功能。")
            )
            return

        # 获取合约信息
        contract = self.main_engine.get_contract(vt_symbol)
        if not contract:
            self.main_engine.write_log(f"合约 {vt_symbol} 未找到，无法模拟成交")
            return

        # 获取合约的最小变动单位（pricetick）
        # 按照用户要求，pricetick按照最小1个点设计
        pricetick = contract.pricetick if contract.pricetick > 0 else 1.0
        pricetick = max(pricetick, 1.0)  # 确保至少为1.0（最小1个点）

        # 获取当前tick数据（如果有的话，用于获取其他字段）
        current_tick = self.main_engine.get_tick(vt_symbol)

        # 遍历所有挂单线，模拟价格突破
        from vnpy.trader.object import TickData
        from vnpy.trader.utility import extract_vt_symbol

        symbol, exchange = extract_vt_symbol(vt_symbol)

        triggered_count = 0
        for line_id, line in pending_lines.items():
            line_price = line.get_price()
            direction_str = line.get_direction()

            # 将方向字符串转换为标准格式（"long"或"short"）
            # 处理中文"多"/"空"和英文"long"/"short"两种情况
            if direction_str in ["多", "long", "LONG"]:
                direction = "long"
            elif direction_str in ["空", "short", "SHORT"]:
                direction = "short"
            else:
                self.main_engine.write_log(f"模拟成交跳过: 挂单线 {line_id} 方向未知: {direction_str}")
                continue

            # 根据方向模拟突破价格
            # 做多：需要满足 last_price < line_price <= current_price
            # 做空：需要满足 last_price > line_price >= current_price
            # 按照最小1个点设计，使用整数pricetick，所有价格计算使用整数
            pricetick_int = max(int(pricetick), 1)  # 确保至少为1个整数点

            # 将挂单价格转换为整数（向下取整，确保计算准确）
            line_price_int = int(line_price)

            # 突破幅度：使用多个点（至少3个点），确保突破明显
            breakthrough_points = max(pricetick_int * 3, 3)  # 至少3个点，确保突破明显

            # 计算突破价格（使用整数计算）
            if direction == "long":
                # 做多：模拟价格从挂单价格下方突破到上方
                # 需要满足：last_price < line_price <= current_price
                # 设置last_price明显低于挂单价格，current_price明显高于挂单价格
                last_price = line_price_int - breakthrough_points  # 明显低于挂单价格（多个点）
                current_price = line_price_int + breakthrough_points  # 明显高于挂单价格（多个点）

                # 验证计算
                if not (last_price < line_price_int <= current_price):
                    self.main_engine.write_log(
                        f"模拟成交错误: 做多价格计算错误 - "
                        f"line_price_int={line_price_int}, breakthrough_points={breakthrough_points}, "
                        f"last_price={last_price}, current_price={current_price}"
                    )
                    continue
            else:  # short
                # 做空：模拟价格从挂单价格上方突破到下方
                # 需要满足：last_price > line_price >= current_price
                # 设置last_price明显高于挂单价格，current_price明显低于挂单价格
                last_price = line_price_int + breakthrough_points  # 明显高于挂单价格（多个点）
                current_price = line_price_int - breakthrough_points  # 明显低于挂单价格（多个点）

                # 验证计算
                if not (last_price > line_price_int >= current_price):
                    self.main_engine.write_log(
                        f"模拟成交错误: 做空价格计算错误 - "
                        f"line_price_int={line_price_int}, breakthrough_points={breakthrough_points}, "
                        f"last_price={last_price}, current_price={current_price}"
                    )
                    continue

            # 验证突破条件（使用整数价格）
            if direction == "long":
                if not (last_price < line_price_int <= current_price):
                    self.main_engine.write_log(
                        f"模拟成交警告: 做多突破条件不满足 - "
                        f"last_price={last_price}, line_price_int={line_price_int}, current_price={current_price}"
                    )
                    continue
            else:  # short
                if not (last_price > line_price_int >= current_price):
                    self.main_engine.write_log(
                        f"模拟成交警告: 做空突破条件不满足 - "
                        f"last_price={last_price}, line_price_int={line_price_int}, current_price={current_price}"
                    )
                    continue

            # 创建模拟tick数据
            from datetime import datetime
            simulate_tick = TickData(
                symbol=symbol,
                exchange=exchange,
                datetime=datetime.now(),
                gateway_name=contract.gateway_name,
                last_price=current_price,
                # 如果有当前tick，复制其他字段
                bid_price_1=current_tick.bid_price_1 if current_tick else current_price - pricetick,
                ask_price_1=current_tick.ask_price_1 if current_tick else current_price + pricetick,
                bid_volume_1=current_tick.bid_volume_1 if current_tick else 100,
                ask_volume_1=current_tick.ask_volume_1 if current_tick else 100,
                volume=current_tick.volume if current_tick else 0,
                open_interest=current_tick.open_interest if current_tick else 0,
            )

            # 确保挂单线已注册到价格突破监控
            controller = chart.get_drawing_order_controller()
            if not controller:
                self.main_engine.write_log("模拟成交失败: 无法获取画线订单控制器")
                continue

            # 检查挂单线是否有挂单参数（说明是有效的挂单线）
            # 优先检查价格线对象中的挂单参数（从数据库加载的挂单线参数存储在这里）
            # 如果价格线对象中没有，再检查内存中的_pending_order_params（向后兼容）
            order_volume = line.get_order_volume()
            order_offset = line.get_order_offset()

            has_pending_params_in_line = (order_volume is not None and order_offset is not None)

            has_pending_params_in_memory = (
                hasattr(controller, '_pending_order_params') and
                line_id in controller._pending_order_params
            )

            has_pending_params = has_pending_params_in_line or has_pending_params_in_memory

            if not has_pending_params:
                self.main_engine.write_log(
                    f"模拟成交跳过: 挂单线 {line_id} 没有挂单参数（价格线对象: volume={order_volume}, offset={order_offset}, "
                    f"内存参数: {has_pending_params_in_memory}）。请重新创建挂单或确保挂单参数已正确加载。"
                )
                continue

            # 如果价格线对象中有参数，记录日志
            if has_pending_params_in_line:
                self.main_engine.write_log(
                    f"模拟成交: 挂单线 {line_id} 从价格线对象获取挂单参数 (volume={order_volume}, offset={order_offset})"
                )
            elif has_pending_params_in_memory:
                self.main_engine.write_log(
                    f"模拟成交: 挂单线 {line_id} 从内存获取挂单参数（向后兼容）"
                )

            # 检查挂单线是否已注册到价格突破监控
            if not chart._breakthrough_monitor:
                self.main_engine.write_log("模拟成交失败: 价格突破监控未初始化")
                continue

            # 直接调用ChartWidget的通用触发方法（与真实tickdata触发共用逻辑）
            # 不再通过PriceBreakthroughMonitor，直接调用trigger_pending_order_breakthrough
            direction_display = "多" if direction == "long" else "空"
            
            self.main_engine.write_log(
                f"模拟成交: {vt_symbol} {direction_display} 挂单线 {line_price_int} "
                f"准备触发突破 (last_price={last_price:.2f}, current_price={current_price:.2f}, "
                f"突破幅度={breakthrough_points}个点)"
            )

            # 调用ChartWidget的通用触发方法
            try:
                result = chart.trigger_pending_order_breakthrough(line_id, line, simulate_tick)
                if result:
                    triggered_count += 1
                    self.main_engine.write_log(
                        f"模拟成交成功: {vt_symbol} {direction_display} 挂单线 {line_price:.2f} 已触发突破并下单"
                    )
                else:
                    self.main_engine.write_log(
                        f"模拟成交失败: {vt_symbol} {direction_display} 挂单线 {line_price:.2f} 未触发突破 "
                        f"(可能挂单参数已不存在或下单失败)"
                    )
            except AttributeError as e:
                # 方法不存在
                error_msg = str(e).replace("{", "{{").replace("}", "}}")
                self.main_engine.write_log(
                    f"模拟成交失败: ChartWidget没有trigger_pending_order_breakthrough方法: {error_msg}"
                )
                import traceback
                self.main_engine.write_log(f"异常堆栈: {traceback.format_exc()}")
            except Exception as e:
                # 其他异常
                error_msg = str(e).replace("{", "{{").replace("}", "}}")
                self.main_engine.write_log(
                    f"模拟成交异常: {vt_symbol} {direction_display} 挂单线 {line_price:.2f} 触发失败: {error_msg}"
                )
                import traceback
                self.main_engine.write_log(f"异常堆栈: {traceback.format_exc()}")
                self.main_engine.write_log(
                    f"模拟成交异常: {vt_symbol} {direction_display} 挂单线 {line_price:.2f} 触发失败: {error_msg}"
                )
                import traceback
                self.main_engine.write_log(f"异常堆栈: {traceback.format_exc()}")

        if triggered_count > 0:
            self.main_engine.write_log(
                f"模拟成交完成: 共触发 {triggered_count} 个挂单线，请查看持仓和浮动盈亏"
            )
            QtWidgets.QMessageBox.information(
                self,
                _("模拟成交"),
                _("已模拟触发 {} 个挂单线成交。\n请查看【持仓】和【资金】窗口查看持仓和浮动盈亏。").format(triggered_count)
            )
        else:
            self.main_engine.write_log("模拟成交失败: 未能触发任何挂单线")

    def _update_simulate_buttons_state(self) -> None:
        """
        更新模拟功能按钮的状态

        规则：
        - 未选择合约时：三个按钮全部disabled
        - 有合约时：三个按钮全部enabled（允许在有tickdata时也使用模拟功能进行测试）
        """
        if not self.current_vt_symbol:
            # 未选择合约，按钮禁用
            self.simulate_trade_button.setEnabled(False)
            self.simulate_stop_loss_button.setEnabled(False)
            self.simulate_take_profit_button.setEnabled(False)
            return

        # 有合约时，按钮全部启用（允许在有tickdata时也使用模拟功能进行测试）
        self.simulate_trade_button.setEnabled(True)
        self.simulate_stop_loss_button.setEnabled(True)
        self.simulate_take_profit_button.setEnabled(True)

    def simulate_stop_loss(self) -> None:
        """
        模拟tick触及止损线后触发平仓

        功能：
        1. 获取所有止损线（STOP_LOSS类型）
        2. 创建模拟tick数据，价格触及止损线
        3. 调用ChartWidget的通用触发方法（与真实tickdata触发共用逻辑）
        """
        self.main_engine.write_log("[模拟止损] 方法被调用")

        if not self.chart:
            self.main_engine.write_log("[模拟止损] 图表未初始化，无法模拟止损")
            return

        # 获取所有价格线
        price_line_manager = self.chart._price_line_manager
        if not price_line_manager:
            self.main_engine.write_log("[模拟止损] 价格线管理器未初始化，无法模拟止损")
            return

        all_lines = price_line_manager.get_all_lines()
        self.main_engine.write_log(f"[模拟止损] 找到 {len(all_lines)} 条价格线")

        # 筛选出止损线（包括所有类型的止损线）
        from vnpy.chart.price_line import PriceLineType
        stop_loss_lines = {
            line_id: line
            for line_id, line in all_lines.items()
            if line.get_line_type() == PriceLineType.STOP_LOSS
        }

        self.main_engine.write_log(f"[模拟止损] 找到 {len(stop_loss_lines)} 条止损线")
        
        # 如果当前图表中没有止损线，尝试从另一个图表加载
        if not stop_loss_lines and self.display_mode == "multi":
            # 多周期模式：尝试从单周期图表加载
            if self.chart and self.chart._price_line_manager:
                single_chart_lines = self.chart._price_line_manager.get_all_lines()
                stop_loss_lines = {
                    line_id: line
                    for line_id, line in single_chart_lines.items()
                    if line.get_line_type() == PriceLineType.STOP_LOSS
                }
                if stop_loss_lines:
                    self.main_engine.write_log(f"[模拟止损] 从单周期图表找到 {len(stop_loss_lines)} 条止损线，正在同步到多周期图表")
                    # 将止损线添加到多周期图表
                    for line_id, line in stop_loss_lines.items():
                        chart._price_line_manager.add_line(line_id, line)
                        if chart._first_plot:
                            chart._first_plot.addItem(line)
        elif not stop_loss_lines and self.display_mode == "single":
            # 单周期模式：尝试从多周期图表加载
            if self.multi_timeframe_widget and hasattr(self.multi_timeframe_widget, '_chart'):
                multi_chart = self.multi_timeframe_widget._chart
                if multi_chart and multi_chart._price_line_manager:
                    multi_chart_lines = multi_chart._price_line_manager.get_all_lines()
                    stop_loss_lines = {
                        line_id: line
                        for line_id, line in multi_chart_lines.items()
                        if line.get_line_type() == PriceLineType.STOP_LOSS
                    }
                    if stop_loss_lines:
                        self.main_engine.write_log(f"[模拟止损] 从多周期图表找到 {len(stop_loss_lines)} 条止损线，正在同步到单周期图表")
                        # 将止损线添加到单周期图表
                        for line_id, line in stop_loss_lines.items():
                            chart._price_line_manager.add_line(line_id, line)
                            if chart._first_plot:
                                chart._first_plot.addItem(line)

        if not stop_loss_lines:
            self.main_engine.write_log("[模拟止损] 没有找到止损线，无法模拟止损")
            QtWidgets.QMessageBox.information(
                self,
                _("提示"),
                _("当前没有止损线，请先创建止损线后再使用模拟止损功能。")
            )
            return

        # 获取当前合约信息
        vt_symbol = self.current_vt_symbol
        if not vt_symbol:
            self.main_engine.write_log("未选择合约，无法模拟止损")
            QtWidgets.QMessageBox.information(
                self,
                _("提示"),
                _("请先选择合约后再使用模拟止损功能。")
            )
            return

        # 获取合约信息
        contract = self.main_engine.get_contract(vt_symbol)
        if not contract:
            self.main_engine.write_log(f"合约 {vt_symbol} 未找到，无法模拟止损")
            return

        # 获取当前tick数据（用于获取其他字段）
        current_tick = self.main_engine.get_tick(vt_symbol)

        # 创建模拟tick数据
        from vnpy.trader.object import TickData
        from vnpy.trader.utility import extract_vt_symbol
        from datetime import datetime

        symbol, exchange = extract_vt_symbol(vt_symbol)
        pricetick = contract.pricetick if contract.pricetick > 0 else 1.0

        triggered_count = 0

        # 遍历所有止损线，创建模拟tick并触发
        for line_id, line in stop_loss_lines.items():
            line_price = line.get_price()
            line_direction_str = line.get_direction()

            # 将方向字符串转换为标准格式
            if line_direction_str in ["多", "long", "LONG"]:
                line_direction = "long"
            elif line_direction_str in ["空", "short", "SHORT"]:
                line_direction = "short"
            else:
                self.main_engine.write_log(f"模拟止损跳过: 止损线 {line_id} 方向未知: {line_direction_str}")
                continue

            # 创建模拟tick数据，价格触及止损线
            # 多仓止损：价格低于止损线
            # 空仓止损：价格高于止损线
            if line_direction == "long":
                # 多仓止损：价格低于止损线
                simulate_price = line_price - pricetick
            else:
                # 空仓止损：价格高于止损线
                simulate_price = line_price + pricetick

            # 创建模拟tick
            simulate_tick = TickData(
                symbol=symbol,
                exchange=exchange,
                datetime=datetime.now(),
                gateway_name=contract.gateway_name,
                last_price=simulate_price,
                # 如果有当前tick，复制其他字段
                bid_price_1=current_tick.bid_price_1 if current_tick else simulate_price - pricetick,
                ask_price_1=current_tick.ask_price_1 if current_tick else simulate_price + pricetick,
                bid_volume_1=current_tick.bid_volume_1 if current_tick else 100,
                ask_volume_1=current_tick.ask_volume_1 if current_tick else 100,
                volume=current_tick.volume if current_tick else 0,
                open_interest=current_tick.open_interest if current_tick else 0,
            )

            # 调用ChartWidget的通用触发方法（与真实tickdata触发共用逻辑）
            try:
                self.main_engine.write_log(
                    f"[模拟止损] 准备触发止损线 {line_id}: "
                    f"价格={line_price:.2f}, 方向={line_direction}, 模拟价格={simulate_price:.2f}"
                )
                # 根据当前模式选择正确的图表
                if self.display_mode == "多周期叠加":
                    chart = self.multi_timeframe_widget._chart
                else:
                    chart = self.chart
                
                result = chart.trigger_stop_loss_close(line_id, line, simulate_tick)
                if result:
                    triggered_count += 1
                    self.main_engine.write_log(f"[模拟止损] 止损线 {line_id} 触发成功")
                else:
                    self.main_engine.write_log(f"[模拟止损] 止损线 {line_id} 触发失败（可能无持仓或持仓为0）")
            except AttributeError as e:
                self.main_engine.write_log(f"[模拟止损] 错误: ChartWidget没有trigger_stop_loss_close方法: {e}")
                import traceback
                self.main_engine.write_log(f"[模拟止损] 异常堆栈: {traceback.format_exc()}")
            except Exception as e:
                self.main_engine.write_log(f"[模拟止损] 异常: {e}")
                import traceback
                self.main_engine.write_log(f"[模拟止损] 异常堆栈: {traceback.format_exc()}")

        if triggered_count > 0:
            self.main_engine.write_log(
                f"模拟止损完成: 共触发 {triggered_count} 个止损线，请查看持仓和订单"
            )
            QtWidgets.QMessageBox.information(
                self,
                _("模拟止损"),
                _("已模拟触发 {} 个止损线平仓。\n请查看【持仓】和【委托】窗口查看持仓和订单状态。").format(triggered_count)
            )
        else:
            self.main_engine.write_log("模拟止损失败: 未能触发任何止损线（可能无持仓或持仓为0）")

    def simulate_take_profit(self) -> None:
        """
        模拟tick触及止盈线后触发平仓

        功能：
        1. 获取所有止盈线（TAKE_PROFIT类型）
        2. 创建模拟tick数据，价格触及止盈线
        3. 调用ChartWidget的通用触发方法（与真实tickdata触发共用逻辑）
        """
        self.main_engine.write_log("[模拟止盈] 方法被调用")

        # 根据当前显示模式选择正确的图表
        if self.display_mode == "multi" and self.multi_timeframe_widget:
            # 多周期模式：使用 MultiTimeframeWidget 的图表
            chart = self.multi_timeframe_widget._chart if hasattr(self.multi_timeframe_widget, '_chart') else None
            self.main_engine.write_log("[模拟止盈] 使用多周期图表")
        else:
            # 单周期模式：使用 ChartWindow 的图表
            chart = self.chart
            self.main_engine.write_log("[模拟止盈] 使用单周期图表")

        if not chart:
            self.main_engine.write_log("[模拟止盈] 图表未初始化，无法模拟止盈")
            return

        # 获取所有价格线
        price_line_manager = chart._price_line_manager
        if not price_line_manager:
            self.main_engine.write_log("[模拟止盈] 价格线管理器未初始化，无法模拟止盈")
            return

        all_lines = price_line_manager.get_all_lines()
        self.main_engine.write_log(f"[模拟止盈] 找到 {len(all_lines)} 条价格线")
        
        # 添加详细调试信息
        for line_id, line in all_lines.items():
            line_type = line.get_line_type()
            line_price = line.get_price()
            self.main_engine.write_log(f"[模拟止盈] 价格线详情: id={line_id}, type={line_type}, price={line_price}")

        # 筛选出止盈线
        from vnpy.chart.price_line import PriceLineType
        take_profit_lines = {
            line_id: line
            for line_id, line in all_lines.items()
            if line.get_line_type() == PriceLineType.TAKE_PROFIT
        }

        self.main_engine.write_log(f"[模拟止盈] 找到 {len(take_profit_lines)} 条止盈线")

        if not take_profit_lines:
            self.main_engine.write_log("[模拟止盈] 没有找到止盈线，无法模拟止盈")
            QtWidgets.QMessageBox.information(
                self,
                _("提示"),
                _("当前没有止盈线，请先创建止盈线后再使用模拟止盈功能。")
            )
            return

        # 获取当前合约信息
        vt_symbol = self.current_vt_symbol
        if not vt_symbol:
            self.main_engine.write_log("未选择合约，无法模拟止盈")
            QtWidgets.QMessageBox.information(
                self,
                _("提示"),
                _("请先选择合约后再使用模拟止盈功能。")
            )
            return

        # 获取合约信息
        contract = self.main_engine.get_contract(vt_symbol)
        if not contract:
            self.main_engine.write_log(f"合约 {vt_symbol} 未找到，无法模拟止盈")
            return

        # 获取当前tick数据（用于获取其他字段）
        current_tick = self.main_engine.get_tick(vt_symbol)

        # 创建模拟tick数据
        from vnpy.trader.object import TickData
        from vnpy.trader.utility import extract_vt_symbol
        from datetime import datetime

        symbol, exchange = extract_vt_symbol(vt_symbol)
        pricetick = contract.pricetick if contract.pricetick > 0 else 1.0

        triggered_count = 0

        # 遍历所有止盈线，创建模拟tick并触发
        for line_id, line in take_profit_lines.items():
            line_price = line.get_price()
            line_direction_str = line.get_direction()

            # 将方向字符串转换为标准格式
            if line_direction_str in ["多", "long", "LONG"]:
                line_direction = "long"
            elif line_direction_str in ["空", "short", "SHORT"]:
                line_direction = "short"
            else:
                self.main_engine.write_log(f"模拟止盈跳过: 止盈线 {line_id} 方向未知: {line_direction_str}")
                continue

            # 创建模拟tick数据，价格触及止盈线
            # 多仓止盈：价格高于止盈线
            # 空仓止盈：价格低于止盈线
            if line_direction == "long":
                # 多仓止盈：价格高于止盈线
                simulate_price = line_price + pricetick
            else:
                # 空仓止盈：价格低于止盈线
                simulate_price = line_price - pricetick

            # 创建模拟tick
            simulate_tick = TickData(
                symbol=symbol,
                exchange=exchange,
                datetime=datetime.now(),
                gateway_name=contract.gateway_name,
                last_price=simulate_price,
                # 如果有当前tick，复制其他字段
                bid_price_1=current_tick.bid_price_1 if current_tick else simulate_price - pricetick,
                ask_price_1=current_tick.ask_price_1 if current_tick else simulate_price + pricetick,
                bid_volume_1=current_tick.bid_volume_1 if current_tick else 100,
                ask_volume_1=current_tick.ask_volume_1 if current_tick else 100,
                volume=current_tick.volume if current_tick else 0,
                open_interest=current_tick.open_interest if current_tick else 0,
            )

            # 调用ChartWidget的通用触发方法（与真实tickdata触发共用逻辑）
            try:
                self.main_engine.write_log(
                    f"[模拟止盈] 准备触发止盈线 {line_id}: "
                    f"价格={line_price:.2f}, 方向={line_direction}, 模拟价格={simulate_price:.2f}"
                )
                # 根据当前模式选择正确的图表
                if self.display_mode == "多周期叠加":
                    chart = self.multi_timeframe_widget._chart
                else:
                    chart = self.chart
                
                result = chart.trigger_take_profit_close(line_id, line, simulate_tick)
                if result:
                    triggered_count += 1
                    self.main_engine.write_log(f"[模拟止盈] 止盈线 {line_id} 触发成功")
                else:
                    self.main_engine.write_log(f"[模拟止盈] 止盈线 {line_id} 触发失败（可能无持仓或持仓为0）")
            except AttributeError as e:
                self.main_engine.write_log(f"[模拟止盈] 错误: ChartWidget没有trigger_take_profit_close方法: {e}")
                import traceback
                self.main_engine.write_log(f"[模拟止盈] 异常堆栈: {traceback.format_exc()}")
            except Exception as e:
                self.main_engine.write_log(f"[模拟止盈] 异常: {e}")
                import traceback
                self.main_engine.write_log(f"[模拟止盈] 异常堆栈: {traceback.format_exc()}")

        if triggered_count > 0:
            self.main_engine.write_log(
                f"模拟止盈完成: 共触发 {triggered_count} 个止盈线，请查看持仓和订单"
            )
            QtWidgets.QMessageBox.information(
                self,
                _("模拟止盈"),
                _("已模拟触发 {} 个止盈线平仓。\n请查看【持仓】和【委托】窗口查看持仓和订单状态。").format(triggered_count)
            )
        else:
            self.main_engine.write_log("模拟止盈失败: 未能触发任何止盈线（可能无持仓或持仓为0）")

    def show(self) -> None:
        """显示窗口"""
        super().show()
        self.activateWindow()
        self.raise_()
        self.raise_()

    def set_simulate_functions_enabled(self, enabled: bool) -> None:
        """
        设置模拟功能按钮的启用/禁用状态。

        Args:
            enabled: True表示启用，False表示禁用
        """
        self._simulate_functions_enabled = enabled
        self.simulate_trade_button.setEnabled(enabled)
        self.simulate_stop_loss_button.setEnabled(enabled)
        self.simulate_take_profit_button.setEnabled(enabled)

        # 更新按钮样式以反映状态
        if enabled:
            self.simulate_trade_button.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold;")
            self.simulate_stop_loss_button.setStyleSheet("background-color: #F44336; color: white; font-weight: bold;")
            self.simulate_take_profit_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        else:
            self.simulate_trade_button.setStyleSheet("background-color: #CCCCCC; color: #666666; font-weight: normal;")
            self.simulate_stop_loss_button.setStyleSheet("background-color: #CCCCCC; color: #666666; font-weight: normal;")
            self.simulate_take_profit_button.setStyleSheet("background-color: #CCCCCC; color: #666666; font-weight: normal;")

        if self.main_engine:
            status_text = _("已启用") if enabled else _("已禁用")
            self.main_engine.write_log(
                f"[ChartWindow] 模拟功能{status_text}：模拟成交、模拟止损、模拟止盈",
                "ChartWindow"
            )

    def is_simulate_functions_enabled(self) -> bool:
        """
        获取模拟功能按钮的启用/禁用状态。

        Returns:
            True表示启用，False表示禁用
        """
        return self._simulate_functions_enabled

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """
        Unregister event listeners when window closes

        确保在窗口关闭时正确注销所有事件监听器，避免内存泄漏。

        注意：
        - 合约切换时不需要特殊处理，因为 process_tick_event 已经通过过滤
          current_vt_symbol 来处理，只处理当前显示合约的 tick。
        - 事件注册使用信号-槽机制（signal_tick.emit），注销时也要使用相同的处理器。
        """
        try:
            # 检查 event_engine 是否已初始化
            if not self.event_engine:
                super().closeEvent(event)
                return

            # 注销 tick 事件监听（使用信号-槽机制，注册的是 signal_tick.emit）
            try:
                from vnpy.trader.event import EVENT_TICK
                self.event_engine.unregister(EVENT_TICK, self.signal_tick.emit)
                # 断开信号连接（如果连接存在）
                try:
                    self.signal_tick.disconnect(self.process_tick_event)
                except (TypeError, RuntimeError):
                    # 连接不存在或已经断开，这是正常的，不需要记录错误
                    pass
                if self.main_engine:
                    self.main_engine.write_log(
                        "[ChartWindow] 已注销 EVENT_TICK 事件监听器（signal_tick.emit）",
                        "ChartWindow"
                    )
            except Exception as e:
                if self.main_engine:
                    self.main_engine.write_log(
                        f"[ChartWindow] 注销 EVENT_TICK 失败：{str(e)}",
                        "ChartWindow"
                    )

            # 注销订单事件监听（如果已注册）
            try:
                from vnpy.trader.event import EVENT_ORDER
                if hasattr(self, 'process_order_event'):
                    self.event_engine.unregister(EVENT_ORDER, self.process_order_event)
                    if self.main_engine:
                        self.main_engine.write_log(
                            "[ChartWindow] 已注销 EVENT_ORDER 事件监听器",
                            "ChartWindow"
                        )
            except Exception as e:
                if self.main_engine:
                    self.main_engine.write_log(
                        f"[ChartWindow] 注销 EVENT_ORDER 失败：{str(e)}",
                        "ChartWindow"
                    )

            # 记录日志
            if self.main_engine:
                self.main_engine.write_log(
                    "[ChartWindow] 窗口关闭，已注销所有事件监听",
                    "ChartWindow"
                )
        except Exception as e:
            # 错误处理：记录错误但不阻止窗口关闭
            if self.main_engine:
                self.main_engine.write_log(
                    f"[ChartWindow] 注销事件监听时发生错误：{str(e)}",
                    "ChartWindow"
                )
        finally:
            # Clean up cache (注意：不再需要关闭 Datafeed，因为使用全局单例)
            # Datafeed 连接由 DatafeedManager 管理，程序退出时自动关闭

            self._open_price_cache.clear()
            if self.main_engine:
                self.main_engine.write_log(
                    f"[ChartWindow-{id(self)}] 已清空开盘价缓存"
                )

            # Ensure parent class method is called
            super().closeEvent(event)

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        """
        窗口显示时重新注册事件监听器
        
        当窗口被关闭后重新打开时，事件监听器可能已被注销，
        需要重新注册以确保实时数据更新正常工作。
        """
        # 重新注册事件监听器（如果已注册会先注销再注册，避免重复）
        self.register_event()

        # 调用父类方法
        super().showEvent(event)
