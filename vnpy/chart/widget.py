from datetime import datetime
from typing import Optional

import pyqtgraph as pg      # type: ignore

from vnpy.trader.ui import QtGui, QtWidgets, QtCore
from vnpy.trader.object import BarData, PositionData, OrderData
from vnpy.trader.event import EVENT_POSITION, EVENT_POSITION_VIEW, EVENT_ORDER
from vnpy.event import Event, EventEngine

from .manager import BarManager
from .base import (
    GREY_COLOR, WHITE_COLOR, CURSOR_COLOR, BLACK_COLOR,
    to_int, NORMAL_FONT
)
from .axis import DatetimeAxis
from .item import ChartItem
from .price_line import PriceLineManager, PriceLineItem, PriceLineType
from .price_line_drag import PriceLineDragHandler
from .drawing_order import DrawingOrderController
from .price_breakthrough import PriceBreakthroughMonitor, BreakthroughEvent
from .price_line_storage import PriceLineStorage, PriceLineData
from .position_holding import PositionHolding, EntryPosition
from .widget_position_helper import (
    add_entry_to_holding,
    update_position_holding_from_order,
    process_position_close
)


pg.setConfigOptions(antialias=True)


class ChartWidget(pg.PlotWidget):
    """"""
    MIN_BAR_COUNT = 100
    
    # 信号定义：用于跨线程调用
    _signal_position_update = QtCore.Signal(object)  # type: ignore
    _signal_order_update = QtCore.Signal(object)  # type: ignore

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        """"""
        super().__init__(parent)

        self._manager: BarManager = BarManager()

        self._plots: dict[str, pg.PlotItem] = {}
        self._items: dict[str, ChartItem] = {}
        self._item_plot_map: dict[ChartItem, pg.PlotItem] = {}

        self._first_plot: pg.PlotItem | None = None
        self._cursor: ChartCursor | None = None
        
        # Price line manager
        self._price_line_manager: PriceLineManager = PriceLineManager()
        
        # Price line drag handler (will be initialized when plot is added)
        self._price_line_drag_handler: PriceLineDragHandler | None = None
        
        # Drawing order controller (will be initialized when plot is added)
        self._drawing_order_controller: DrawingOrderController | None = None
        
        # Price breakthrough monitor
        self._breakthrough_monitor: PriceBreakthroughMonitor = PriceBreakthroughMonitor()
        
        # Price line storage
        self._price_line_storage: PriceLineStorage = PriceLineStorage()
        
        # 持仓管理：direction -> PositionHolding
        # 用于管理同方向的多个入场持仓，支持FIFO平仓和合并显示
        self._position_holdings: dict[str, PositionHolding] = {}  # "long" or "short" -> PositionHolding
        
        # VT symbol for the chart
        self._vt_symbol: str | None = None
        
        # MainEngine reference (optional, for order operations)
        self._main_engine: object | None = None
        
        # EventEngine reference (for listening to position updates)
        self._event_engine: EventEngine | None = None
        
        # 连接信号槽
        self._signal_position_update.connect(self._update_entry_line_pnl)
        self._signal_order_update.connect(self._process_order_update)
        
        # Price precision (number of decimal places, 0 for integer, default 0 for MHImain)
        self._price_precision: int = 0
        
        # Callback for drawing mode state changes (e.g., when ESC is pressed)
        self._on_drawing_mode_changed: callable | None = None

        self._right_ix: int = 0                     # Index of most right data
        self._bar_count: int = self.MIN_BAR_COUNT   # Total bar visible in chart
        self._future_bars: int = 0                  # Extra space for future bars

        self._init_ui()

    def _init_ui(self) -> None:
        """"""
        self.setWindowTitle("ChartWidget of VeighNa")
        
        # Enable keyboard focus to receive key events (e.g., ESC key)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

        self._layout: pg.GraphicsLayout = pg.GraphicsLayout()
        self._layout.setContentsMargins(10, 10, 10, 10)
        self._layout.setSpacing(0)
        self._layout.setBorder(color=GREY_COLOR, width=0.8)
        self._layout.setZValue(0)
        self.setCentralItem(self._layout)

    def _get_new_x_axis(self) -> DatetimeAxis:
        return DatetimeAxis(self._manager, orientation="bottom")

    def add_cursor(self) -> None:
        """"""
        if not self._cursor:
            self._cursor = ChartCursor(
                self, self._manager, self._plots, self._item_plot_map)

    def add_plot(
        self,
        plot_name: str,
        minimum_height: int = 80,
        maximum_height: int | None = None,
        hide_x_axis: bool = False
    ) -> None:
        """
        Add plot area.
        """
        # Create plot object
        plot: pg.PlotItem = pg.PlotItem(axisItems={"bottom": self._get_new_x_axis()})
        plot.setMenuEnabled(False)
        plot.setClipToView(True)
        plot.hideAxis("left")
        plot.showAxis("right")
        plot.setDownsampling(mode="peak")
        plot.setRange(xRange=(0, 1), yRange=(0, 1))
        plot.hideButtons()
        plot.setMinimumHeight(minimum_height)

        if maximum_height:
            plot.setMaximumHeight(maximum_height)

        if hide_x_axis:
            plot.hideAxis("bottom")

        if not self._first_plot:
            self._first_plot = plot

        # Connect view change signal to update y range function
        view: pg.ViewBox = plot.getViewBox()
        view.sigXRangeChanged.connect(self._update_y_range)
        view.setMouseEnabled(x=True, y=False)

        # Set right axis
        right_axis: pg.AxisItem = plot.getAxis("right")
        right_axis.setWidth(60)
        right_axis.tickFont = NORMAL_FONT

        # Connect x-axis link
        if self._plots:
            first_plot: pg.PlotItem = list(self._plots.values())[0]
            plot.setXLink(first_plot)

        # Store plot object in dict
        self._plots[plot_name] = plot

        # Add plot onto the layout
        self._layout.nextRow()
        self._layout.addItem(plot)
        
        # Initialize drag handler for first plot (main price chart)
        if not self._price_line_drag_handler:
            self._price_line_drag_handler = PriceLineDragHandler(plot)
        
        # Initialize drawing order controller for first plot
        if not self._drawing_order_controller and self._first_plot:
            self._drawing_order_controller = DrawingOrderController(
                widget=self,
                price_line_manager=self._price_line_manager,
                drag_handler=self._price_line_drag_handler,
                main_engine=self._main_engine,
                vt_symbol=self._vt_symbol
            )

    def add_item(
        self,
        item_class: type[ChartItem],
        item_name: str,
        plot_name: str
    ) -> None:
        """
        Add chart item.
        """
        item: ChartItem = item_class(self._manager)
        self._items[item_name] = item

        plot: pg.PlotItem = self._plots.get(plot_name)
        plot.addItem(item)

        self._item_plot_map[item] = plot

    def get_plot(self, plot_name: str) -> pg.PlotItem:
        """
        Get specific plot with its name.
        """
        return self._plots.get(plot_name, None)

    def get_all_plots(self) -> list[pg.PlotItem]:
        """
        Get all plot objects.
        """
        return list(self._plots.values())

    def get_price_line_manager(self) -> PriceLineManager:
        """
        Get price line manager instance.
        """
        return self._price_line_manager

    def add_price_line(
        self,
        price: float,
        line_type: str,
        direction: str = "long",
        plot_name: str | None = None,
        movable: bool = False,
        line_id: str | None = None
    ) -> str:
        """
        Add a price line to the chart.

        Args:
            price: Price value for the line
            line_type: Type of price line ("entry", "pending", "stop_loss", "take_profit", "preview")
            direction: Trading direction ("long" or "short")
            plot_name: Name of the plot to add the line to. If None, use first plot.
            movable: Whether the line can be dragged
            line_id: Optional custom line ID

        Returns:
            Line ID string
        """
        from .price_line import PriceLineType

        # Convert string to enum
        type_map = {
            "entry": PriceLineType.ENTRY,
            "pending": PriceLineType.PENDING,
            "stop_loss": PriceLineType.STOP_LOSS,
            "take_profit": PriceLineType.TAKE_PROFIT,
            "preview": PriceLineType.PREVIEW
        }
        price_line_type = type_map.get(line_type.lower(), PriceLineType.PREVIEW)

        # Get target plot
        if plot_name is None:
            plot = self._first_plot
        else:
            plot = self._plots.get(plot_name)

        if plot is None:
            raise ValueError(f"Plot '{plot_name}' not found")

        # Create price line
        line_id = self._price_line_manager.create_line(
            price=price,
            line_type=price_line_type,
            direction=direction,
            movable=movable,
            line_id=line_id
        )

        # Add to plot
        line = self._price_line_manager.get_line(line_id)
        if line:
            plot.addItem(line)

        return line_id

    def remove_price_line(self, line_id: str) -> bool:
        """
        Remove a price line from the chart.

        Args:
            line_id: Line ID to remove

        Returns:
            True if successful, False if line not found
        """
        # Unregister from breakthrough monitor
        if self._breakthrough_monitor:
            self._breakthrough_monitor.unregister_line(line_id)
        
        return self._price_line_manager.delete_line(line_id)
    
    def set_vt_symbol(self, vt_symbol: str) -> None:
        """
        Set VT symbol for the chart.

        Args:
            vt_symbol: VT symbol (e.g., "MHI2512.HKFE")
        """
        self._vt_symbol = vt_symbol
        if self._drawing_order_controller:
            self._drawing_order_controller.set_vt_symbol(vt_symbol)
    
    def set_main_engine(self, main_engine: object) -> None:
        """
        Set MainEngine instance for order operations.

        Args:
            main_engine: MainEngine instance
        """
        self._main_engine = main_engine
        if self._drawing_order_controller:
            self._drawing_order_controller.set_main_engine(main_engine)
        
        # 获取EventEngine用于监听持仓更新
        if hasattr(main_engine, 'event_engine'):
            self._event_engine = main_engine.event_engine
            self._register_position_events()
    
    def _register_position_events(self) -> None:
        """注册持仓更新事件，用于更新入场线的浮动盈亏"""
        if not self._event_engine:
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[ChartWidget] 无法注册事件：_event_engine为None",
                    "ChartWidget"
                )
            return
        
        # 监听持仓视图事件（包含浮动盈亏信息）
        self._event_engine.register(EVENT_POSITION_VIEW, self._on_position_update)
        # 也监听传统持仓事件（兼容性）
        self._event_engine.register(EVENT_POSITION, self._on_position_update)
        # 监听订单事件，用于更新价格线（订单成交后创建入场线）
        self._event_engine.register(EVENT_ORDER, self._on_order_update)
        
        if hasattr(self, '_main_engine') and self._main_engine:
            self._main_engine.write_log(
                f"[ChartWidget] 已注册事件监听: EVENT_POSITION_VIEW, EVENT_POSITION, EVENT_ORDER",
                "ChartWidget"
            )
    
    def _on_position_update(self, event: Event) -> None:
        """处理持仓更新事件，更新入场线的浮动盈亏显示"""
        position: PositionData = event.data
        
        # 添加日志确认收到持仓更新事件，包含冻结状态
        if hasattr(self, '_main_engine') and self._main_engine:
            available_volume = position.volume - position.frozen
            self._main_engine.write_log(
                f"[ChartWidget] 收到持仓更新事件: {position.vt_symbol} {position.direction.value} "
                f"volume={position.volume} frozen={position.frozen} available={available_volume} pnl={position.pnl}",
                "ChartWidget"
            )
        
        # 处理主力合约映射：如果图表是主力合约（如MHImain.HKFE），持仓是实际合约（如MHI2512.HKFE）
        # 需要检查持仓是否对应图表的主力合约
        position_vt_symbol = position.vt_symbol
        chart_vt_symbol = self._vt_symbol
        
        # 添加日志确认合约匹配检查
        if hasattr(self, '_main_engine') and self._main_engine:
            self._main_engine.write_log(
                f"[ChartWidget] 合约匹配检查: 图表合约={chart_vt_symbol}, 持仓合约={position_vt_symbol}",
                "ChartWidget"
            )
        
        if chart_vt_symbol and position_vt_symbol != chart_vt_symbol:
            # 尝试通过主力合约映射匹配
            # 从持仓的实际合约符号提取主力合约符号（如MHI2512.HKFE -> MHImain.HKFE）
            position_symbol = position.symbol
            chart_symbol = chart_vt_symbol.split('.')[0] if '.' in chart_vt_symbol else chart_vt_symbol
            
            # 检查持仓符号是否以图表符号开头（如MHI2512以MHI开头，对应MHImain）
            # 或者通过gateway获取主力合约映射
            matched = False
            if hasattr(self, '_main_engine') and self._main_engine:
                # 尝试从gateway获取主力合约映射
                for gateway_name in self._main_engine.get_all_gateway_names():
                    gateway = self._main_engine.get_gateway(gateway_name)
                    if gateway and hasattr(gateway, 'get_main_contract_mapping'):
                        mapping = gateway.get_main_contract_mapping()
                        # 检查是否有主力合约映射到当前持仓符号
                        for main_symbol, actual_symbol in mapping.items():
                            if actual_symbol == position_symbol:
                                # 找到匹配的主力合约
                                main_vt_symbol = f"{main_symbol}.{position.exchange.value}"
                                if main_vt_symbol == chart_vt_symbol:
                                    matched = True
                                    if hasattr(self, '_main_engine') and self._main_engine:
                                        self._main_engine.write_log(
                                            f"[ChartWidget] 主力合约映射匹配: 图表={chart_vt_symbol}, 持仓={position_vt_symbol} (通过映射 {main_symbol}->{actual_symbol})",
                                            "ChartWidget"
                                        )
                                    break
                        if matched:
                            break
            
            if not matched:
                if hasattr(self, '_main_engine') and self._main_engine:
                    self._main_engine.write_log(
                        f"[ChartWidget] 持仓更新事件合约不匹配: 图表={chart_vt_symbol}, 持仓={position_vt_symbol}",
                        "ChartWidget"
                    )
                return
        
        # 如果没有入场线，不需要更新
        if not self._drawing_order_controller:
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[ChartWidget] 持仓更新事件: drawing_order_controller未初始化",
                    "ChartWidget"
                )
            return
        
        # 如果持仓全部冻结（可用持仓为0），不显示盈亏，但保留入场线
        # 这种情况通常发生在休市时间，模拟交易平仓后，API返回的是冻结持仓而不是0持仓
        # 但持仓可能会解冻，所以不应该清除入场线
        # 只有当持仓数量为0时，才清除入场线
        if position.volume > 0 and position.volume == position.frozen:
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[ChartWidget] 持仓全部冻结（可用=0），不更新盈亏但保留入场线: {position.vt_symbol} {position.direction.value}",
                    "ChartWidget"
                )
            # 不更新盈亏，但保留入场线，等待持仓解冻
            # 直接返回，不调用 _update_entry_line_pnl
            return
        
        # 使用信号槽机制确保在主线程中执行
        from vnpy.trader.ui import QtCore
        
        # 添加日志确认调度，包含合约匹配信息
        if hasattr(self, '_main_engine') and self._main_engine:
            self._main_engine.write_log(
                f"[ChartWidget] 准备更新入场线盈亏: 图表合约={chart_vt_symbol}, 持仓合约={position.vt_symbol}, "
                f"方向={position.direction.value}, volume={position.volume}, pnl={position.pnl}",
                "ChartWidget"
            )
        
        # 直接检查是否在主线程，如果是则直接调用，否则使用信号槽
        app = QtCore.QCoreApplication.instance()
        if app and QtCore.QThread.currentThread() == app.thread():
            # 已经在主线程，直接调用
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[ChartWidget] 已在主线程，直接调用 _update_entry_line_pnl",
                    "ChartWidget"
                )
            self._update_entry_line_pnl(position)
        else:
            # 不在主线程，使用信号槽调度到主线程
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[ChartWidget] 不在主线程，使用信号槽调度到主线程",
                    "ChartWidget"
                )
            self._signal_position_update.emit(position)
    
    def _clear_frozen_position_lines(self, position: PositionData) -> None:
        """清除冻结持仓对应的入场线及其关联的止损止盈线"""
        position_direction = "long" if position.direction.value == "多" else "short"
        all_lines = self._price_line_manager.get_all_lines()
        
        if hasattr(self, '_main_engine') and self._main_engine:
            self._main_engine.write_log(
                f"[ChartWidget] 清除冻结持仓的入场线: {position.vt_symbol} {position.direction.value} "
                f"volume={position.volume} frozen={position.frozen}",
                "ChartWidget"
            )
        
        # 收集需要删除的入场线（匹配方向）
        lines_to_delete = set()
        for line_id, line in all_lines.items():
            line_type = line.get_line_type()
            line_direction = line.get_direction()
            
            if line_type == PriceLineType.ENTRY and line_direction == position_direction:
                lines_to_delete.add(line_id)
                if hasattr(self, '_main_engine') and self._main_engine:
                    self._main_engine.write_log(
                        f"[ChartWidget] 标记删除冻结持仓的入场线: {line_id} (方向={line_direction})",
                        "ChartWidget"
                    )
        
        # 删除所有标记的线及其关联的止损止盈线
        deleted_count = 0
        for line_id in list(lines_to_delete):
            line = self._price_line_manager.get_line(line_id)
            if line and self._price_line_manager.delete_line(line_id):
                deleted_count += 1
                if hasattr(self, '_main_engine') and self._main_engine:
                    self._main_engine.write_log(
                        f"[ChartWidget] 已删除冻结持仓的入场线: {line_id}",
                        "ChartWidget"
                    )
                
                # 清理订单映射（如果存在）
                if hasattr(self, '_drawing_order_controller') and self._drawing_order_controller:
                    order_id = self._drawing_order_controller.get_order_id_for_line(line_id)
                    if order_id:
                        self._drawing_order_controller._line_order_map.pop(line_id, None)
                        self._drawing_order_controller._order_line_map.pop(order_id, None)
                    # 从挂单线关联关系中移除（如果存在）
                    if hasattr(self._drawing_order_controller, '_pending_line_relations'):
                        self._drawing_order_controller._pending_line_relations.pop(line_id, None)
                
                # 删除关联的止损线和止盈线
                if hasattr(self._drawing_order_controller, '_pending_line_relations'):
                    # 查找与此入场线关联的止损止盈线
                    entry_order_id = line.get_vt_orderid()
                    if entry_order_id:
                        # 遍历所有挂单线关联关系，找到与此entry_order_id关联的原始pending_line_id
                        for pending_line_id, relations in self._drawing_order_controller._pending_line_relations.items():
                            if self._drawing_order_controller.get_order_id_for_line(pending_line_id) == entry_order_id:
                                stop_loss_info = relations.get("stop_loss")
                                if stop_loss_info and stop_loss_info.get("line_id"):
                                    if self._price_line_manager.delete_line(stop_loss_info["line_id"]):
                                        deleted_count += 1
                                        if hasattr(self, '_main_engine') and self._main_engine:
                                            self._main_engine.write_log(
                                                f"[ChartWidget] 已删除关联止损线: {stop_loss_info['line_id']}",
                                                "ChartWidget"
                                            )
                                take_profit_info = relations.get("take_profit")
                                if take_profit_info and take_profit_info.get("line_id"):
                                    if self._price_line_manager.delete_line(take_profit_info["line_id"]):
                                        deleted_count += 1
                                        if hasattr(self, '_main_engine') and self._main_engine:
                                            self._main_engine.write_log(
                                                f"[ChartWidget] 已删除关联止盈线: {take_profit_info['line_id']}",
                                                "ChartWidget"
                                            )
                                # 清理该挂单线的关联关系
                                self._drawing_order_controller._pending_line_relations.pop(pending_line_id, None)
                                break  # 找到并处理了，退出内层循环
        
        if hasattr(self, '_main_engine') and self._main_engine:
            self._main_engine.write_log(
                f"[ChartWidget] 冻结持仓清除完成: 共删除 {deleted_count} 条价格线",
                "ChartWidget"
            )
    
    def _update_entry_line_pnl(self, position: PositionData) -> None:
        """更新入场线的浮动盈亏（在主线程中执行）
        
        使用 PositionHolding 来管理同方向的多个持仓，支持：
        1. 合并显示为一条入场线（显示加权平均价格）
        2. FIFO平仓逻辑（先进先出）
        3. 保留所有原始入场信息
        """
        # 添加日志确认回调执行，包含冻结状态
        if hasattr(self, '_main_engine') and self._main_engine:
            available_volume = position.volume - position.frozen
            self._main_engine.write_log(
                f"[ChartWidget] _update_entry_line_pnl 回调开始执行: {position.vt_symbol} {position.direction.value} "
                f"volume={position.volume} frozen={position.frozen} available={available_volume} pnl={position.pnl}",
                "ChartWidget"
            )
        
        position_direction = "long" if position.direction.value == "多" else "short"
        all_lines = self._price_line_manager.get_all_lines()
        
        # 添加日志，包含冻结状态
        if hasattr(self, '_main_engine') and self._main_engine:
            entry_line_count = len([l for l in all_lines.values() if l.get_line_type() == PriceLineType.ENTRY])
            available_volume = position.volume - position.frozen
            self._main_engine.write_log(
                f"[ChartWidget] 更新入场线盈亏: 持仓方向={position_direction}, 持仓数量={position.volume}, "
                f"冻结={position.frozen}, 可用={available_volume}, 盈亏={position.pnl}, "
                f"入场线数量={entry_line_count}, 总价格线数量={len(all_lines)}",
                "ChartWidget"
            )
        
        # 获取该方向的持仓管理对象
        holding = self._position_holdings.get(position_direction)
        
        # 如果持仓为0，清除该方向的所有入场线和持仓记录
        if position.volume == 0:
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[ChartWidget] 检测到持仓为0，开始清除{position_direction}方向的入场线和持仓记录",
                    "ChartWidget"
                )
            
            if holding:
                # 清空持仓记录
                holding.clear()
                self._position_holdings.pop(position_direction, None)
                if hasattr(self, '_main_engine') and self._main_engine:
                    self._main_engine.write_log(
                        f"[ChartWidget] 持仓为0，已清空{position_direction}方向的持仓记录",
                        "ChartWidget"
                    )
            else:
                if hasattr(self, '_main_engine') and self._main_engine:
                    self._main_engine.write_log(
                        f"[ChartWidget] 持仓为0，但{position_direction}方向没有持仓记录（可能通过trade UI平仓），仍将删除入场线",
                        "ChartWidget"
                    )
            
            # 删除该方向的所有入场线（无论是否有持仓记录）
            lines_to_delete = []
            for line_id, line in all_lines.items():
                if line.get_line_type() == PriceLineType.ENTRY:
                    line_direction = line.get_direction()
                    if line_direction == position_direction:
                        lines_to_delete.append(line_id)
                        if hasattr(self, '_main_engine') and self._main_engine:
                            self._main_engine.write_log(
                                f"[ChartWidget] 标记删除入场线: {line_id} (方向={line_direction}, 匹配={line_direction == position_direction})",
                                "ChartWidget"
                            )
            
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[ChartWidget] 找到 {len(lines_to_delete)} 条{position_direction}方向的入场线待删除",
                    "ChartWidget"
                )
            
            deleted_count = 0
            for line_id in lines_to_delete:
                line = self._price_line_manager.get_line(line_id)
                if line:
                    # 先从 plot 中移除（如果存在）
                    if self._first_plot:
                        try:
                            self._first_plot.removeItem(line)
                            if hasattr(self, '_main_engine') and self._main_engine:
                                self._main_engine.write_log(
                                    f"[ChartWidget] 已从plot中移除入场线: {line_id}",
                                    "ChartWidget"
                                )
                        except Exception as e:
                            if hasattr(self, '_main_engine') and self._main_engine:
                                self._main_engine.write_log(
                                    f"[ChartWidget] 从plot移除入场线失败: {line_id}, 错误: {str(e)}",
                                    "ChartWidget"
                                )
                    
                    # 然后从管理器中删除
                    if self._price_line_manager.delete_line(line_id):
                        deleted_count += 1
                        if hasattr(self, '_main_engine') and self._main_engine:
                            self._main_engine.write_log(
                                f"[ChartWidget] 已删除入场线: {line_id}",
                                "ChartWidget"
                            )
                        # 清理订单映射
                        if hasattr(self, '_drawing_order_controller') and self._drawing_order_controller:
                            order_id = self._drawing_order_controller.get_order_id_for_line(line_id)
                            if order_id:
                                self._drawing_order_controller._line_order_map.pop(line_id, None)
                                self._drawing_order_controller._order_line_map.pop(order_id, None)
                    else:
                        if hasattr(self, '_main_engine') and self._main_engine:
                            self._main_engine.write_log(
                                f"[ChartWidget] 警告: 从管理器删除入场线失败: {line_id}",
                                "ChartWidget"
                            )
                else:
                    if hasattr(self, '_main_engine') and self._main_engine:
                        self._main_engine.write_log(
                            f"[ChartWidget] 警告: 无法获取入场线: {line_id}",
                            "ChartWidget"
                        )
            
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[ChartWidget] 持仓为0，已删除 {deleted_count} 条{position_direction}方向的入场线（共找到 {len(lines_to_delete)} 条）",
                    "ChartWidget"
                )
            return
        
        # 如果持仓管理对象不存在，尝试从现有入场线创建持仓记录或直接更新入场线
        # 这种情况可能发生在通过trade UI下单，或者订单成交时没有正确添加持仓记录
        if not holding:
            # 查找该方向的所有入场线
            entry_lines_for_direction = []
            for line_id, line in all_lines.items():
                if line.get_line_type() == PriceLineType.ENTRY and line.get_direction() == position_direction:
                    entry_lines_for_direction.append((line_id, line))
            
            if entry_lines_for_direction:
                # 有入场线但没有持仓记录，创建持仓记录
                holding = PositionHolding(position_direction)
                self._position_holdings[position_direction] = holding
                
                if hasattr(self, '_main_engine') and self._main_engine:
                    self._main_engine.write_log(
                        f"[ChartWidget] {position_direction}方向没有持仓记录，但从现有入场线创建持仓记录（找到 {len(entry_lines_for_direction)} 条入场线）",
                        "ChartWidget"
                    )
                
                # 从现有入场线创建持仓记录（使用入场线价格和实际持仓手数）
                # 如果有多条入场线，使用加权平均价格
                if len(entry_lines_for_direction) == 1:
                    # 只有一条入场线，直接使用其价格
                    line_id, line = entry_lines_for_direction[0]
                    entry_price = line.get_price()
                    # 使用实际持仓手数
                    holding.add_entry(line_id, entry_price, position.volume, line.get_vt_orderid(), datetime.now())
                else:
                    # 有多条入场线，需要计算加权平均价格
                    # 暂时使用第一条入场线的价格，手数使用实际持仓手数
                    line_id, line = entry_lines_for_direction[0]
                    entry_price = line.get_price()
                    holding.add_entry(line_id, entry_price, position.volume, line.get_vt_orderid(), datetime.now())
                    
                    if hasattr(self, '_main_engine') and self._main_engine:
                        self._main_engine.write_log(
                            f"[ChartWidget] 警告: 有多条入场线但只有一条持仓记录，使用第一条入场线价格 {entry_price}，手数 {position.volume}",
                            "ChartWidget"
                        )
            else:
                # 没有入场线也没有持仓记录，但持仓数量>0，应该根据持仓信息创建入场线
                # 这种情况通常发生在程序重启后，入场线信息丢失
                if position.volume > 0:
                    # 使用持仓价格作为入场价格（如果为0，尝试使用当前市场价格）
                    # 使用持仓价格作为入场价格（如果为0，尝试从manager获取最新价格）
                    entry_price = position.price if position.price > 0 else 0.0
                    if entry_price == 0:
                        # 尝试从manager获取最新价格
                        if hasattr(self, '_manager') and self._manager:
                            # 获取最新的bar数据
                            all_bars = self._manager.get_all_bars()
                            if all_bars:
                                entry_price = all_bars[-1].close_price
                    
                    # 如果仍然为0，使用一个默认值（例如当前图表显示范围的中点）
                    if entry_price == 0:
                        if self._first_plot:
                            view_range = self._first_plot.viewRange()
                            if view_range and len(view_range) > 1:
                                y_range = view_range[1]
                                if y_range and len(y_range) > 1:
                                    entry_price = (y_range[0] + y_range[1]) / 2
                    
                    if entry_price > 0:
                        # 创建入场线
                        if hasattr(self, '_drawing_order_controller') and self._drawing_order_controller:
                            # 生成唯一的line_id
                            import uuid
                            line_id = f"entry_recovered_{uuid.uuid4().hex[:8]}"
                            
                            # 创建入场线
                            created_line_id = self._drawing_order_controller.create_entry_line(
                                price=entry_price,
                                direction=position_direction,
                                line_id=line_id
                            )
                            
                            # 验证入场线是否创建成功
                            if not created_line_id:
                                if hasattr(self, '_main_engine') and self._main_engine:
                                    self._main_engine.write_log(
                                        f"[ChartWidget] 警告: 创建入场线失败，返回的line_id为空",
                                        "ChartWidget"
                                    )
                                return
                            
                            # 验证入场线是否在manager中
                            created_line = self._price_line_manager.get_line(created_line_id)
                            if not created_line:
                                if hasattr(self, '_main_engine') and self._main_engine:
                                    self._main_engine.write_log(
                                        f"[ChartWidget] 警告: 创建入场线后无法从manager获取: {created_line_id}",
                                        "ChartWidget"
                                    )
                                return
                            
                            # 创建持仓记录
                            holding = PositionHolding(position_direction)
                            self._position_holdings[position_direction] = holding
                            holding.add_entry(created_line_id, entry_price, position.volume, None, datetime.now())
                            
                            if hasattr(self, '_main_engine') and self._main_engine:
                                self._main_engine.write_log(
                                    f"[ChartWidget] 已根据持仓信息恢复入场线: {created_line_id}, 价格={entry_price}, 手数={position.volume}, 方向={position_direction}",
                                    "ChartWidget"
                                )
                            
                            # 验证持仓记录中的入场线ID
                            entry_line_ids = holding.get_entry_line_ids()
                            if hasattr(self, '_main_engine') and self._main_engine:
                                self._main_engine.write_log(
                                    f"[ChartWidget] 验证: 持仓记录中的入场线ID列表={entry_line_ids}, 期望包含={created_line_id}",
                                    "ChartWidget"
                                )
                            
                            # 创建入场线后，继续执行后续的更新逻辑（不要return）
                            # 重新获取holding，因为刚刚创建了
                            holding = self._position_holdings.get(position_direction)
                        else:
                            if hasattr(self, '_main_engine') and self._main_engine:
                                self._main_engine.write_log(
                                    f"[ChartWidget] 无法恢复入场线: drawing_order_controller未初始化",
                                    "ChartWidget"
                                )
                            return
                    else:
                        if hasattr(self, '_main_engine') and self._main_engine:
                            self._main_engine.write_log(
                                f"[ChartWidget] 无法恢复入场线: 持仓价格和当前价格都为0",
                                "ChartWidget"
                            )
                        return
                else:
                    # 持仓数量为0，跳过
                    if hasattr(self, '_main_engine') and self._main_engine:
                        self._main_engine.write_log(
                            f"[ChartWidget] {position_direction}方向没有持仓记录也没有入场线，且持仓数量为0，跳过更新",
                            "ChartWidget"
                        )
                    return
        
        # 计算持仓变化：如果当前持仓手数小于持仓记录中的总手数，说明有平仓
        # 从 PositionHolding 的 entries 计算总手数（用于 FIFO 平仓判断）
        holding_total_volume = sum(e.volume for e in holding.get_all_entries())
        
        # 添加详细日志，帮助调试
        if hasattr(self, '_main_engine') and self._main_engine:
            self._main_engine.write_log(
                f"[ChartWidget] 持仓变化检查: 持仓记录总手数={holding_total_volume}, 实际持仓手数={position.volume}, "
                f"持仓记录数量={len(holding.get_all_entries())}",
                "ChartWidget"
            )
        
        # 只有当实际持仓手数明显小于持仓记录总手数时，才认为是平仓
        # 使用 0.01 的容差，避免浮点数精度问题
        if position.volume < holding_total_volume - 0.01:
            # 有平仓，按照FIFO原则移除持仓记录
            close_volume = holding_total_volume - position.volume
            
            # 确保平仓手数不超过持仓记录总手数
            if close_volume > holding_total_volume:
                close_volume = holding_total_volume
            
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[ChartWidget] 检测到平仓: 平仓手数={close_volume}, 持仓记录总手数={holding_total_volume}, "
                    f"实际持仓手数={position.volume}",
                    "ChartWidget"
                )
            
            closed_entries = process_position_close(self._position_holdings, position_direction, close_volume)
            
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[ChartWidget] 已移除 {len(closed_entries)} 条持仓记录",
                    "ChartWidget"
                )
            
            # 删除已平仓的入场线
            for closed_entry in closed_entries:
                line_id = closed_entry.line_id
                if self._price_line_manager.delete_line(line_id):
                    if hasattr(self, '_main_engine') and self._main_engine:
                        self._main_engine.write_log(
                            f"[ChartWidget] 已删除已平仓的入场线: {line_id} (价格={closed_entry.price}, 手数={closed_entry.volume})",
                            "ChartWidget"
                        )
                    # 清理订单映射
                    if hasattr(self, '_drawing_order_controller') and self._drawing_order_controller:
                        order_id = self._drawing_order_controller.get_order_id_for_line(line_id)
                        if order_id:
                            self._drawing_order_controller._line_order_map.pop(line_id, None)
                            self._drawing_order_controller._order_line_map.pop(order_id, None)
        elif abs(position.volume - holding_total_volume) <= 0.01:
            # 持仓手数一致，没有平仓
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[ChartWidget] 持仓手数一致，无平仓: 持仓记录总手数={holding_total_volume}, 实际持仓手数={position.volume}",
                    "ChartWidget"
                )
        else:
            # 实际持仓手数大于持仓记录总手数，可能是新开仓（通过 trade UI）
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[ChartWidget] 实际持仓手数大于持仓记录总手数，可能是新开仓: "
                    f"持仓记录总手数={holding_total_volume}, 实际持仓手数={position.volume}",
                    "ChartWidget"
                )
        
        # 重新获取持仓管理对象（可能已被修改）
        holding = self._position_holdings.get(position_direction)
        if not holding or holding.is_empty():
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[ChartWidget] {position_direction}方向持仓记录为空，跳过更新",
                    "ChartWidget"
                )
            return
        
        # ========== 统一数据源：以PriceLineManager为准 ==========
        # 从PriceLineManager获取该方向的所有入场线（这是唯一的数据源）
        all_lines = self._price_line_manager.get_all_lines()
        entry_lines = []
        for line_id, line in all_lines.items():
            if line.get_line_type() == PriceLineType.ENTRY and line.get_direction() == position_direction:
                entry_lines.append((line_id, line))
        
        # ========== 直接使用 position.price 和 position.volume（不再从 PositionHolding 计算） ==========
        # 使用 futu_gateway 上报的加权平均价格
        avg_price = position.price if position.price > 0 else 0.0
        
        # 如果 position.price == 0，尝试从入场线计算（备用方案）
        if avg_price == 0 and entry_lines:
            # 从 PriceLineManager 获取入场线并计算加权平均价格
            total_value = 0.0
            total_vol = 0.0
            for line_id, line in entry_lines:
                line_price = line.get_price()
                # 从 PositionHolding 获取该入场线的手数
                entry = next((e for e in holding.get_all_entries() if e.line_id == line_id), None)
                if entry:
                    line_volume = entry.volume
                else:
                    # 如果没有记录，平均分配
                    line_volume = position.volume / len(entry_lines) if entry_lines else 0
                total_value += line_price * line_volume
                total_vol += line_volume
            if total_vol > 0:
                avg_price = total_value / total_vol
        
        # 直接使用 position.volume 作为总手数
        total_volume = position.volume
        
        if hasattr(self, '_main_engine') and self._main_engine:
            self._main_engine.write_log(
                f"[ChartWidget] 持仓统计: 方向={position_direction}, 加权均价={avg_price:.2f}, 总手数={total_volume}, 浮动盈亏={position.pnl}",
                "ChartWidget"
            )
        
        if hasattr(self, '_main_engine') and self._main_engine:
            self._main_engine.write_log(
                f"[ChartWidget] 从PriceLineManager获取入场线: {len(entry_lines)} 条（方向={position_direction}）",
                "ChartWidget"
            )
        
        # 如果PriceLineManager中没有入场线，但持仓数量>0，需要创建入场线
        if not entry_lines and position.volume > 0:
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[ChartWidget] 持仓记录中的入场线ID都不存在，但持仓数量>0，需要重新创建入场线",
                    "ChartWidget"
                )
            # 清空持仓记录，重新创建
            holding.clear()
            # 使用持仓价格创建入场线
            entry_price = position.price if position.price > 0 else 0.0
            if entry_price == 0:
                # 尝试从manager获取最新价格
                if hasattr(self, '_manager') and self._manager:
                    all_bars = self._manager.get_all_bars()
                    if all_bars:
                        entry_price = all_bars[-1].close_price
            if entry_price == 0 and self._first_plot:
                view_range = self._first_plot.viewRange()
                if view_range and len(view_range) > 1:
                    y_range = view_range[1]
                    if y_range and len(y_range) > 1:
                        entry_price = (y_range[0] + y_range[1]) / 2
            
            if entry_price > 0 and hasattr(self, '_drawing_order_controller') and self._drawing_order_controller:
                import uuid
                line_id = f"entry_recovered_{uuid.uuid4().hex[:8]}"
                created_line_id = self._drawing_order_controller.create_entry_line(
                    price=entry_price,
                    direction=position_direction,
                    line_id=line_id
                )
                
                # 验证创建成功
                created_line = self._price_line_manager.get_line(created_line_id)
                if created_line_id and created_line:
                    # 重新获取入场线列表（包含新创建的）
                    all_lines = self._price_line_manager.get_all_lines()
                    entry_lines = []
                    for lid, line in all_lines.items():
                        if line.get_line_type() == PriceLineType.ENTRY and line.get_direction() == position_direction:
                            entry_lines.append((lid, line))
                    
                    if hasattr(self, '_main_engine') and self._main_engine:
                        # 使用 % 格式化避免 loguru 的二次格式化问题
                        self._main_engine.write_log(
                            "[ChartWidget] 已创建入场线: %s, 价格=%.2f, 手数=%.1f" % (created_line_id, entry_price, position.volume),
                            "ChartWidget"
                        )
                else:
                    if hasattr(self, '_main_engine') and self._main_engine:
                        # 使用 % 格式化避免 loguru 的二次格式化问题
                        self._main_engine.write_log(
                            "[ChartWidget] 创建入场线失败: %s" % created_line_id,
                            "ChartWidget"
                        )
                    return
        
        # 如果仍然没有入场线，跳过更新
        if not entry_lines:
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[ChartWidget] {position_direction}方向没有入场线，跳过更新",
                    "ChartWidget"
                )
            return
        
        # ========== 同步PositionHolding：根据PriceLineManager中的入场线来同步 ==========
        # 获取PositionHolding中现有的line_id集合
        holding_line_ids = set(holding.get_entry_line_ids())
        # 获取PriceLineManager中的line_id集合
        manager_line_ids = {line_id for line_id, _ in entry_lines}
        
        # 找出需要添加的（在manager中但不在holding中）
        to_add = manager_line_ids - holding_line_ids
        # 找出需要移除的（在holding中但不在manager中，即孤儿ID）
        to_remove = holding_line_ids - manager_line_ids
        
        if to_remove:
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[ChartWidget] 发现孤儿ID，从PositionHolding中移除: {list(to_remove)}",
                    "ChartWidget"
                )
            # 从PositionHolding中移除孤儿ID
            holding._entries = [e for e in holding._entries if e.line_id not in to_remove]
        
        if to_add:
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[ChartWidget] 发现新入场线，添加到PositionHolding: {list(to_add)}",
                    "ChartWidget"
                )
            # 将新入场线添加到PositionHolding
            for line_id in to_add:
                line = self._price_line_manager.get_line(line_id)
                if line:
                    # 使用入场线的价格，手数使用实际持仓手数（如果是新创建的，可能需要分配）
                    # 如果有多条入场线，平均分配手数；如果只有一条，使用全部手数
                    if len(entry_lines) == 1:
                        volume = position.volume
                    else:
                        # 平均分配（简单处理，实际应该根据价格加权）
                        volume = position.volume / len(entry_lines)
                    holding.add_entry(line_id, line.get_price(), volume, line.get_vt_orderid(), datetime.now())
        
        # ========== 直接使用 position.price 和 position.volume（不再从 PositionHolding 计算） ==========
        # 使用 futu_gateway 上报的加权平均价格
        avg_price = position.price if position.price > 0 else 0.0
        
        # 如果 position.price == 0，尝试从入场线计算（备用方案）
        if avg_price == 0 and entry_lines:
            # 从 PriceLineManager 获取入场线并计算加权平均价格
            total_value = 0.0
            total_vol = 0.0
            for line_id, line in entry_lines:
                line_price = line.get_price()
                # 从 PositionHolding 获取该入场线的手数
                entry = next((e for e in holding.get_all_entries() if e.line_id == line_id), None)
                if entry:
                    line_volume = entry.volume
                else:
                    # 如果没有记录，平均分配
                    line_volume = position.volume / len(entry_lines) if entry_lines else 0
                total_value += line_price * line_volume
                total_vol += line_volume
            if total_vol > 0:
                avg_price = total_value / total_vol
        
        # 直接使用 position.volume 作为总手数
        total_volume = position.volume
        
        if hasattr(self, '_main_engine') and self._main_engine:
            self._main_engine.write_log(
                f"[ChartWidget] 持仓统计: 方向={position_direction}, 加权均价={avg_price:.2f}, 总手数={total_volume}, 浮动盈亏={position.pnl}",
                "ChartWidget"
            )
        
        # 使用第一条入场线作为合并显示线
        main_line_id, main_line = entry_lines[0]
        
        # 更新合并显示线的价格为加权平均价格，并更新盈亏和手数
        old_price = main_line.get_price()
        if abs(old_price - avg_price) > 0.01:  # 价格有变化，更新价格
            main_line.set_price(avg_price, price_precision=0)
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[ChartWidget] 更新合并显示线价格: {main_line_id} {old_price:.2f} -> {avg_price:.2f}",
                    "ChartWidget"
                )
        
        # 更新盈亏和手数
        old_pnl = main_line.get_pnl()
        old_volume = main_line.get_volume()
        main_line.set_pnl_and_volume(position.pnl, total_volume)
        
        # 验证更新是否成功
        new_pnl = main_line.get_pnl()
        new_volume = main_line.get_volume()
        
        if hasattr(self, '_main_engine') and self._main_engine:
            price_precision = 0
            label_text = main_line._create_label(avg_price, PriceLineType.ENTRY, price_precision, position_direction)
            self._main_engine.write_log(
                f"[ChartWidget] 已更新合并显示线: {main_line_id}, "
                f"盈亏={old_pnl} -> {new_pnl}, 手数={old_volume} -> {new_volume}, 标签={label_text}",
                "ChartWidget"
            )
            
            # 验证标签是否正确更新
            if main_line.label is not None:
                # 检查标签文本（InfLineLabel没有text()方法，但我们可以通过其他方式验证）
                self._main_engine.write_log(
                    f"[ChartWidget] 入场线 {main_line_id} 标签已更新，价格={avg_price}, 手数={new_volume}, 盈亏={new_pnl}",
                    "ChartWidget"
                )
            else:
                self._main_engine.write_log(
                    f"[ChartWidget] 警告: 入场线 {main_line_id} 的label为None，无法显示更新",
                    "ChartWidget"
                )
        
        # 隐藏其他入场线（但不删除，保留原始信息）
        for line_id, line in entry_lines[1:]:  # 跳过第一条（合并显示线）
            # 隐藏入场线（通过设置不可见）
            line.setVisible(False)
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[ChartWidget] 已隐藏入场线: {line_id} (保留原始信息)",
                    "ChartWidget"
                )
        
        # 确保合并显示线可见
        main_line.setVisible(True)
        
        # 如果持仓数为0，检查是否应该清除入场线
        # 只有当该合约的所有方向持仓都为0时，才清除所有入场线
        if position.volume == 0:
            # 检查该合约的所有方向持仓是否都为0
            should_clear_all = True
            if hasattr(self, '_main_engine') and self._main_engine:
                # 获取该合约的所有持仓
                all_positions = self._main_engine.get_all_positions()
                for pos in all_positions:
                    # 检查是否与当前持仓是同一个合约（考虑主力合约映射）
                    pos_vt_symbol = pos.vt_symbol
                    chart_vt_symbol = self._vt_symbol
                    
                    # 检查合约是否匹配（直接匹配或通过主力合约映射）
                    matched = False
                    if chart_vt_symbol and pos_vt_symbol == chart_vt_symbol:
                        matched = True
                    else:
                        # 尝试通过主力合约映射匹配
                        pos_symbol = pos.symbol
                        chart_symbol = chart_vt_symbol.split('.')[0] if '.' in chart_vt_symbol else chart_vt_symbol
                        for gateway_name in self._main_engine.get_all_gateway_names():
                            gateway = self._main_engine.get_gateway(gateway_name)
                            if gateway and hasattr(gateway, 'get_main_contract_mapping'):
                                mapping = gateway.get_main_contract_mapping()
                                for main_symbol, actual_symbol in mapping.items():
                                    if actual_symbol == pos_symbol:
                                        main_vt_symbol = f"{main_symbol}.{pos.exchange.value}"
                                        if main_vt_symbol == chart_vt_symbol:
                                            matched = True
                                            break
                                if matched:
                                    break
                    
                    if matched and pos.volume > 0:
                        # 找到匹配的合约且持仓不为0，不应该清除所有入场线
                        should_clear_all = False
                        if hasattr(self, '_main_engine') and self._main_engine:
                            self._main_engine.write_log(
                                f"[ChartWidget] 持仓数为0，但存在其他方向持仓: {pos.vt_symbol} {pos.direction.value} volume={pos.volume}，不清除所有入场线",
                                "ChartWidget"
                            )
                        break
            
            # 只有当所有方向持仓都为0时，才清除所有入场线
            if should_clear_all:
                if hasattr(self, '_main_engine') and self._main_engine:
                    self._main_engine.write_log(
                        f"[ChartWidget] 持仓数为0，且所有方向持仓都为0，开始清除所有入场线、止损线和止盈线",
                        "ChartWidget"
                    )
                
                # 收集所有需要删除的线ID
                lines_to_delete = []
                
                # 查找所有入场线（包括匹配和不匹配方向的）
                for line_id, line in all_lines.items():
                    line_type = line.get_line_type()
                    if line_type == PriceLineType.ENTRY:
                        lines_to_delete.append(line_id)
                        if hasattr(self, '_main_engine') and self._main_engine:
                            self._main_engine.write_log(
                                f"[ChartWidget] 标记删除入场线: {line_id} (方向={line.get_direction()})",
                                "ChartWidget"
                            )
                
                # 查找所有止损线和止盈线
                for line_id, line in all_lines.items():
                    line_type = line.get_line_type()
                    if line_type == PriceLineType.STOP_LOSS or line_type == PriceLineType.TAKE_PROFIT:
                        lines_to_delete.append(line_id)
                        if hasattr(self, '_main_engine') and self._main_engine:
                            self._main_engine.write_log(
                                f"[ChartWidget] 标记删除{line_type.value}线: {line_id} (方向={line.get_direction()})",
                                "ChartWidget"
                            )
                
                # 删除所有标记的线
                deleted_count = 0
                for line_id in lines_to_delete:
                    if self._price_line_manager.delete_line(line_id):
                        deleted_count += 1
                        # 清理订单映射（如果存在）
                        if hasattr(self, '_drawing_order_controller') and self._drawing_order_controller:
                            # 从订单映射中移除
                            order_id = self._drawing_order_controller.get_order_id_for_line(line_id)
                            if order_id:
                                self._drawing_order_controller._line_order_map.pop(line_id, None)
                                self._drawing_order_controller._order_line_map.pop(order_id, None)
                            # 从挂单线关联关系中移除（如果存在）
                            if hasattr(self._drawing_order_controller, '_pending_line_relations'):
                                self._drawing_order_controller._pending_line_relations.pop(line_id, None)
                
                if hasattr(self, '_main_engine') and self._main_engine:
                    self._main_engine.write_log(
                        f"[ChartWidget] 持仓数为0，已清除 {deleted_count} 条价格线",
                        "ChartWidget"
                    )
                return
            else:
                # 只清除与当前持仓方向匹配的入场线
                if hasattr(self, '_main_engine') and self._main_engine:
                    self._main_engine.write_log(
                        f"[ChartWidget] 持仓数为0，但存在其他方向持仓，只清除{position_direction}方向的入场线",
                        "ChartWidget"
                    )
                
                # 只清除与当前持仓方向匹配的入场线
                lines_to_delete = []
                for line_id, line in all_lines.items():
                    line_type = line.get_line_type()
                    line_direction = line.get_direction()
                    # 只清除匹配方向的入场线
                    if line_type == PriceLineType.ENTRY and line_direction == position_direction:
                        lines_to_delete.append(line_id)
                        if hasattr(self, '_main_engine') and self._main_engine:
                            self._main_engine.write_log(
                                f"[ChartWidget] 标记删除{position_direction}方向入场线: {line_id}",
                                "ChartWidget"
                            )
                    
                    # 只清除匹配方向的止损线和止盈线
                    if (line_type == PriceLineType.STOP_LOSS or line_type == PriceLineType.TAKE_PROFIT) and line_direction == position_direction:
                        lines_to_delete.append(line_id)
                        if hasattr(self, '_main_engine') and self._main_engine:
                            self._main_engine.write_log(
                                f"[ChartWidget] 标记删除{position_direction}方向{line_type.value}线: {line_id}",
                                "ChartWidget"
                            )
                
                # 删除标记的线
                deleted_count = 0
                for line_id in lines_to_delete:
                    if self._price_line_manager.delete_line(line_id):
                        deleted_count += 1
                        # 清理订单映射
                        if hasattr(self, '_drawing_order_controller') and self._drawing_order_controller:
                            order_id = self._drawing_order_controller.get_order_id_for_line(line_id)
                            if order_id:
                                self._drawing_order_controller._line_order_map.pop(line_id, None)
                                self._drawing_order_controller._order_line_map.pop(order_id, None)
                            if hasattr(self._drawing_order_controller, '_pending_line_relations'):
                                self._drawing_order_controller._pending_line_relations.pop(line_id, None)
                
                if hasattr(self, '_main_engine') and self._main_engine:
                    self._main_engine.write_log(
                        f"[ChartWidget] 已清除 {deleted_count} 条{position_direction}方向的价格线",
                        "ChartWidget"
                    )
                return
        
        # 获取该合约的所有持仓（用于检查其他方向的持仓）
        all_positions = []
        if hasattr(self, '_main_engine') and self._main_engine:
            all_positions = self._main_engine.get_all_positions()
        
        # 构建持仓映射：direction -> volume
        position_map = {}
        chart_vt_symbol = self._vt_symbol
        for pos in all_positions:
            # 检查是否与图表合约匹配（考虑主力合约映射）
            pos_vt_symbol = pos.vt_symbol
            matched = False
            if chart_vt_symbol and pos_vt_symbol == chart_vt_symbol:
                matched = True
            else:
                # 尝试通过主力合约映射匹配
                pos_symbol = pos.symbol
                chart_symbol = chart_vt_symbol.split('.')[0] if '.' in chart_vt_symbol else chart_vt_symbol
                for gateway_name in self._main_engine.get_all_gateway_names():
                    gateway = self._main_engine.get_gateway(gateway_name)
                    if gateway and hasattr(gateway, 'get_main_contract_mapping'):
                        mapping = gateway.get_main_contract_mapping()
                        for main_symbol, actual_symbol in mapping.items():
                            if actual_symbol == pos_symbol:
                                main_vt_symbol = f"{main_symbol}.{pos.exchange.value}"
                                if main_vt_symbol == chart_vt_symbol:
                                    matched = True
                                    break
                        if matched:
                            break
            
            if matched:
                pos_direction = "long" if pos.direction.value == "多" else "short"
                position_map[pos_direction] = pos.volume
        
        updated_count = 0
        entry_lines = [l for l in all_lines.values() if l.get_line_type() == PriceLineType.ENTRY]
        if hasattr(self, '_main_engine') and self._main_engine:
            # 使用list()避免空字典{}被loguru解析为格式化占位符
            position_map_items = list(position_map.items()) if position_map else []
            available_volume = position.volume - position.frozen
            self._main_engine.write_log(
                f"[ChartWidget] 查找入场线: 总入场线数量={len(entry_lines)}, 持仓方向={position_direction}, "
                f"持仓数量={position.volume}, 冻结={position.frozen}, 可用={available_volume}, 持仓映射={position_map_items}",
                "ChartWidget"
            )
        
        # 收集需要删除的入场线（方向没有持仓或持仓为0）
        lines_to_delete = []
        
        # 收集匹配方向的入场线（用于更新）
        matching_entry_lines = []
        
        for line_id, line in all_lines.items():
            if line.get_line_type() != PriceLineType.ENTRY:
                continue
            
            # 检查持仓方向是否匹配
            direction = line.get_direction()
            
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[ChartWidget] 检查入场线 {line_id}: 方向={direction}, 持仓方向={position_direction}, 匹配={direction == position_direction}, 持仓数量={position.volume}",
                    "ChartWidget"
                )
            
            # 检查该方向的持仓是否存在且不为0
            line_position_volume = position_map.get(direction, 0.0)
            
            if line_position_volume <= 0:
                # 该方向的持仓为0或不存在，应该删除这条入场线
                lines_to_delete.append((line_id, direction))
                if hasattr(self, '_main_engine') and self._main_engine:
                    self._main_engine.write_log(
                        f"[ChartWidget] 标记删除入场线 {line_id}: 方向={direction}的持仓为0或不存在 (持仓映射中的值={line_position_volume})",
                        "ChartWidget"
                    )
                continue
            
            # 收集匹配方向的入场线
            if direction == position_direction and position.volume > 0:
                matching_entry_lines.append((line_id, line))
        
        # 更新所有匹配方向的入场线
        # 如果有多条入场线，只更新第一条，其他删除（或者可以合并显示，这里选择只保留第一条）
        if matching_entry_lines:
            if len(matching_entry_lines) > 1:
                if hasattr(self, '_main_engine') and self._main_engine:
                    self._main_engine.write_log(
                        f"[ChartWidget] 发现 {len(matching_entry_lines)} 条匹配方向的入场线，将更新第一条，删除其他",
                        "ChartWidget"
                    )
                # 只保留第一条，其他标记为删除
                for i, (line_id, line) in enumerate(matching_entry_lines[1:], start=1):
                    lines_to_delete.append((line_id, position_direction))
                    if hasattr(self, '_main_engine') and self._main_engine:
                        self._main_engine.write_log(
                            f"[ChartWidget] 标记删除重复入场线 {line_id} (保留第一条)",
                            "ChartWidget"
                        )
            
            # 更新第一条入场线
            line_id, line = matching_entry_lines[0]
            old_pnl = line.get_pnl()
            old_volume = line.get_volume()
            line.set_pnl_and_volume(position.pnl, position.volume)
            
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[ChartWidget] 更新入场线 {line_id} 盈亏和手数: 盈亏={old_pnl} -> {position.pnl}, 手数={old_volume} -> {position.volume}",
                    "ChartWidget"
                )
            
            # 标签已通过set_pnl_and_volume自动更新，这里只需要记录
            if line.label is not None:
                updated_count += 1
                if hasattr(self, '_main_engine') and self._main_engine:
                    # 重新生成标签文本用于日志记录（InfLineLabel没有text()方法）
                    price_precision = 0  # 默认整数显示
                    label_text = line._create_label(line._price, line._line_type, price_precision, line._direction)
                    self._main_engine.write_log(
                        f"[ChartWidget] 已更新入场线 {line_id} 标签: {label_text}",
                        "ChartWidget"
                    )
            else:
                if hasattr(self, '_main_engine') and self._main_engine:
                    self._main_engine.write_log(
                        f"[ChartWidget] 警告: 入场线 {line_id} 的label为None，无法更新显示",
                        "ChartWidget"
                    )
        
        # 删除没有持仓的入场线及其关联的止损止盈线
        deleted_count = 0
        for line_id, line_direction in lines_to_delete:
            # 删除入场线
            if self._price_line_manager.delete_line(line_id):
                deleted_count += 1
                if hasattr(self, '_main_engine') and self._main_engine:
                    self._main_engine.write_log(
                        f"[ChartWidget] 已删除入场线 {line_id} (方向={line_direction}的持仓为0)",
                        "ChartWidget"
                    )
                
                # 清理订单映射
                if hasattr(self, '_drawing_order_controller') and self._drawing_order_controller:
                    order_id = self._drawing_order_controller.get_order_id_for_line(line_id)
                    if order_id:
                        self._drawing_order_controller._line_order_map.pop(line_id, None)
                        self._drawing_order_controller._order_line_map.pop(order_id, None)
                    if hasattr(self._drawing_order_controller, '_pending_line_relations'):
                        self._drawing_order_controller._pending_line_relations.pop(line_id, None)
            
            # 查找并删除关联的止损线和止盈线
            for other_line_id, other_line in all_lines.items():
                other_line_type = other_line.get_line_type()
                other_line_direction = other_line.get_direction()
                if (other_line_type == PriceLineType.STOP_LOSS or other_line_type == PriceLineType.TAKE_PROFIT) and other_line_direction == line_direction:
                    # 检查是否与已删除的入场线关联（通过检查是否有相同的订单ID或通过_pending_line_relations）
                    # 简单方法：如果止损/止盈线的方向与已删除的入场线方向相同，也删除它
                    if self._price_line_manager.delete_line(other_line_id):
                        deleted_count += 1
                        if hasattr(self, '_main_engine') and self._main_engine:
                            self._main_engine.write_log(
                                f"[ChartWidget] 已删除{other_line_type.value}线 {other_line_id} (方向={line_direction}的入场线已删除)",
                                "ChartWidget"
                            )
        
        if hasattr(self, '_main_engine') and self._main_engine:
            self._main_engine.write_log(
                f"[ChartWidget] 盈亏更新完成: 共更新 {updated_count} 条入场线，删除 {deleted_count} 条价格线",
                "ChartWidget"
            )
    
    def _on_order_update(self, event: Event) -> None:
        """处理订单更新事件，订单成交后创建入场线（确保在主线程中执行）"""
        order: OrderData = event.data
        
        # 添加详细日志
        if hasattr(self, '_main_engine') and self._main_engine:
            self._main_engine.write_log(
                f"[ChartWidget] 收到订单更新事件: {order.vt_symbol} {order.direction.value if order.direction else 'N/A'} "
                f"status={order.status.value} orderid={order.orderid} vt_orderid={order.vt_orderid}",
                "ChartWidget"
            )
            # 检查订单状态
            from vnpy.trader.constant import Status
            if order.status == Status.ALLTRADED:
                self._main_engine.write_log(
                    f"[ChartWidget] 订单 {order.vt_orderid} 状态为全部成交，准备转换为入场线",
                    "ChartWidget"
                )
        
        # 处理主力合约映射：如果图表是主力合约，订单是实际合约，需要匹配
        order_vt_symbol = order.vt_symbol
        chart_vt_symbol = self._vt_symbol
        
        if chart_vt_symbol and order_vt_symbol != chart_vt_symbol:
            # 尝试通过主力合约映射匹配
            order_symbol = order.symbol
            chart_symbol = chart_vt_symbol.split('.')[0] if '.' in chart_vt_symbol else chart_vt_symbol
            
            matched = False
            if hasattr(self, '_main_engine') and self._main_engine:
                # 尝试从gateway获取主力合约映射
                for gateway_name in self._main_engine.get_all_gateway_names():
                    gateway = self._main_engine.get_gateway(gateway_name)
                    if gateway and hasattr(gateway, 'get_main_contract_mapping'):
                        mapping = gateway.get_main_contract_mapping()
                        for main_symbol, actual_symbol in mapping.items():
                            if actual_symbol == order_symbol:
                                main_vt_symbol = f"{main_symbol}.{order.exchange.value}"
                                if main_vt_symbol == chart_vt_symbol:
                                    matched = True
                                    if hasattr(self, '_main_engine') and self._main_engine:
                                        self._main_engine.write_log(
                                            f"[ChartWidget] 订单主力合约映射匹配: 图表={chart_vt_symbol}, 订单={order_vt_symbol} (通过映射 {main_symbol}->{actual_symbol})",
                                            "ChartWidget"
                                        )
                                    break
                        if matched:
                            break
            
            if not matched:
                if hasattr(self, '_main_engine') and self._main_engine:
                    self._main_engine.write_log(
                        f"[ChartWidget] 订单更新事件合约不匹配: 图表={chart_vt_symbol}, 订单={order_vt_symbol}",
                        "ChartWidget"
                    )
                return
        
        # 如果没有drawing_order_controller，不需要更新
        if not self._drawing_order_controller:
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[ChartWidget] 订单更新事件: drawing_order_controller未初始化",
                    "ChartWidget"
                )
            return
        
        # 添加日志：检查订单是否关联到挂单线
        if hasattr(self, '_main_engine') and self._main_engine:
            line_id = self._drawing_order_controller.get_line_id_for_order(order.vt_orderid)
            self._main_engine.write_log(
                f"[ChartWidget] 订单 {order.vt_orderid} 关联的挂单线: {line_id}",
                "ChartWidget"
            )
        
        # 使用信号槽机制确保在主线程中执行，避免线程问题
        from vnpy.trader.ui import QtCore
        if hasattr(self, '_main_engine') and self._main_engine:
            self._main_engine.write_log(
                f"[ChartWidget] 准备调用 update_line_from_order 更新挂单线",
                "ChartWidget"
            )
        
        # 直接检查是否在主线程，如果是则直接调用，否则使用信号槽
        app = QtCore.QCoreApplication.instance()
        if app and QtCore.QThread.currentThread() == app.thread():
            # 已经在主线程，直接调用
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[ChartWidget] 已在主线程，直接调用 _process_order_update",
                    "ChartWidget"
                )
            self._process_order_update(order)
        else:
            # 不在主线程，使用信号槽调度到主线程
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[ChartWidget] 不在主线程，使用信号槽调度 _process_order_update",
                    "ChartWidget"
                )
            self._signal_order_update.emit(order)
    
    def _process_order_update(self, order: OrderData) -> None:
        """在主线程中处理订单更新"""
        if hasattr(self, '_main_engine') and self._main_engine:
            self._main_engine.write_log(
                f"[ChartWidget] 开始处理订单更新: {order.vt_orderid} status={order.status.value}",
                "ChartWidget"
            )
        if self._drawing_order_controller:
            result = self._drawing_order_controller.update_line_from_order(order)
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[ChartWidget] update_line_from_order 返回结果: {result}",
                    "ChartWidget"
                )
    
    def get_drawing_order_controller(self) -> DrawingOrderController | None:
        """
        Get drawing order controller instance.

        Returns:
            DrawingOrderController instance or None
        """
        return self._drawing_order_controller
    
    def save_price_lines(self) -> bool:
        """
        Save all price lines to storage.

        Returns:
            True if successful, False otherwise
        """
        if not self._vt_symbol:
            return False
        
        try:
            all_lines = self._price_line_manager.get_all_lines()
            line_data_list = []
            
            for line_id, line in all_lines.items():
                # Get order ID if linked
                vt_orderid = None
                if self._drawing_order_controller:
                    vt_orderid = self._drawing_order_controller.get_order_id_for_line(line_id)
                
                line_data = PriceLineData(
                    line_id=line_id,
                    price=line.get_price(),
                    line_type=line.get_line_type(),
                    direction=line.get_direction(),
                    vt_symbol=self._vt_symbol,
                    vt_orderid=vt_orderid
                )
                line_data_list.append(line_data)
            
            return self._price_line_storage.save_lines(line_data_list, self._vt_symbol)
        except Exception as e:
            print(f"Error saving price lines: {e}")
            return False
    
    def load_price_lines(self) -> bool:
        """
        Load price lines from storage.

        Returns:
            True if successful, False otherwise
        """
        if not self._vt_symbol:
            return False
        
        try:
            line_data_list = self._price_line_storage.load_lines(self._vt_symbol)
            
            for line_data in line_data_list:
                # Create price line
                line_id = self.add_price_line(
                    price=line_data.price,
                    line_type=line_data.line_type.value,
                    direction=line_data.direction,
                    line_id=line_data.line_id,
                    movable=(line_data.line_type == PriceLineType.PENDING)
                )
                
                # Link to order if exists
                if line_data.vt_orderid and self._drawing_order_controller:
                    self._drawing_order_controller.link_line_to_order(line_id, line_data.vt_orderid)
                
                # Register for breakthrough monitoring if pending
                if line_data.line_type == PriceLineType.PENDING and self._breakthrough_monitor:
                    line = self._price_line_manager.get_line(line_id)
                    if line:
                        # Register with a default callback (can be customized)
                        self._breakthrough_monitor.register_line(
                            line_id, line, self._on_price_breakthrough
                        )
            
            return True
        except Exception as e:
            print(f"Error loading price lines: {e}")
            return False
    
    def _on_price_breakthrough(self, event) -> None:
        """
        Handle price breakthrough event.

        Args:
            event: BreakthroughEvent instance
        """
        # This is a default callback - can be overridden or extended
        print(f"Price breakthrough detected: {event.line_id} at {event.current_price}")

    def clear_all(self) -> None:
        """
        Clear all data.
        """
        self._manager.clear_all()

        for item in self._items.values():
            item.clear_all()

        if self._cursor:
            self._cursor.clear_all()

        # Clear all price lines
        self._price_line_manager.clear_all()
        
        # Clear breakthrough monitor
        if self._breakthrough_monitor:
            self._breakthrough_monitor.clear()

    def update_history(self, history: list[BarData]) -> None:
        """
        Update a list of bar data.
        """
        self._manager.update_history(history)

        for item in self._items.values():
            item.update_history(history)

        self._update_plot_limits()

        self.move_to_right()

    def update_bar(self, bar: BarData) -> None:
        """
        Update single bar data.
        """
        self._manager.update_bar(bar)

        for item in self._items.values():
            item.update_bar(bar)

        self._update_plot_limits()

        # 只有当视图在数据范围内且接近末尾时才自动跟随
        # 如果用户已将视图移到未来空间，则不自动移动
        data_count = self._manager.get_count()
        if self._right_ix <= data_count and self._right_ix >= (data_count - self._bar_count / 2):
            self.move_to_right()
        
        # Update breakthrough monitor with bar data
        if self._breakthrough_monitor:
            all_lines = self._price_line_manager.get_all_lines()
            self._breakthrough_monitor.update_bar(bar, all_lines)

    def _update_plot_limits(self) -> None:
        """
        Update the limit of plots.
        """
        for item, plot in self._item_plot_map.items():
            min_value, max_value = item.get_y_range()

            plot.setLimits(
                xMin=-1,
                xMax=self._manager.get_count() + self._future_bars,
                yMin=min_value,
                yMax=max_value
            )

    def _update_x_range(self) -> None:
        """
        Update the x-axis range of plots.
        """
        max_ix: int = self._right_ix
        min_ix: int = self._right_ix - self._bar_count

        for plot in self._plots.values():
            plot.setRange(xRange=(min_ix, max_ix), padding=0)

    def _update_y_range(self) -> None:
        """
        Update the y-axis range of plots.
        """
        if not self._first_plot:
            return

        view: pg.ViewBox = self._first_plot.getViewBox()
        view_range: list = view.viewRange()

        min_ix: int = max(0, int(view_range[0][0]))
        max_ix: int = min(self._manager.get_count(), int(view_range[0][1]))

        # Update limit for y-axis
        for item, plot in self._item_plot_map.items():
            y_range: tuple = item.get_y_range(min_ix, max_ix)
            plot.setRange(yRange=y_range)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        """
        Reimplement this method of parent to update current max_ix value.
        """
        if not self._first_plot:
            return

        view: pg.ViewBox = self._first_plot.getViewBox()
        view_range: list = view.viewRange()
        self._right_ix = max(0, view_range[0][1])

        super().paintEvent(event)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        """
        Reimplement this method of parent to move chart horizontally and zoom in/out.
        """
        Key = QtCore.Qt.Key

        # Handle ESC key to cancel drag
        if event.key() == Key.Key_Escape:
            if self._price_line_drag_handler and self._price_line_drag_handler.cancel_drag():
                event.accept()
                return

        if event.key() == Key.Key_Left:
            self._on_key_left()
        elif event.key() == Key.Key_Right:
            self._on_key_right()
        elif event.key() == Key.Key_Up:
            self._on_key_up()
        elif event.key() == Key.Key_Down:
            self._on_key_down()

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        """
        Reimplement this method of parent to zoom in/out.
        """
        delta: QtCore.QPoint = event.angleDelta()

        if delta.y() > 0:
            self._on_key_up()
        elif delta.y() < 0:
            self._on_key_down()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        """
        Handle mouse move event for price line hover detection and dragging.
        """
        # Check if in drawing mode - show preview line
        if self._drawing_order_controller and self._drawing_order_controller.is_enabled():
            if self._first_plot:
                view_box = self._first_plot.getViewBox()
                if view_box:
                    scene_pos = self.mapToScene(event.pos())
                    view_pos = view_box.mapSceneToView(scene_pos)
                    price = view_pos.y()
                    
                    if price > 0:
                        self._drawing_order_controller.update_preview_line(price)
                    super().mouseMoveEvent(event)
                    return

        if not self._price_line_drag_handler or not self._first_plot:
            super().mouseMoveEvent(event)
            return

        # Get scene position
        scene_pos = self.mapToScene(event.pos())
        
        # Get all price lines
        all_lines = list(self._price_line_manager.get_all_lines().values())
        
        # If dragging, update drag position
        if self._price_line_drag_handler.is_dragging():
            new_price = self._price_line_drag_handler.convert_scene_to_price(scene_pos)
            if new_price is not None:
                self._price_line_drag_handler.update_drag(new_price)
                # 如果拖拽的是挂单线，实时更新关联的止损/止盈线
                dragging_line = self._price_line_drag_handler.get_dragging_line()
                if dragging_line:
                    self._update_related_lines_on_drag(dragging_line, new_price)
        else:
            # Check for hover
            hovered_line = self._price_line_drag_handler.find_line_near_point(
                scene_pos, all_lines
            )
            
            # Change cursor style
            if hovered_line:
                self.setCursor(QtCore.Qt.CursorShape.SizeVerCursor)
            else:
                self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)

        super().mouseMoveEvent(event)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        """
        Handle mouse press event to start dragging price line or create order in drawing mode.
        """
        # Only handle left button
        if event.button() != QtCore.Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        if not self._price_line_drag_handler or not self._first_plot:
            super().mousePressEvent(event)
            return

        # Get scene position
        scene_pos = self.mapToScene(event.pos())
        
        # Get all price lines
        all_lines = list(self._price_line_manager.get_all_lines().values())
        
        # Find line near click position (优先检查是否可以拖拽)
        clicked_line = self._price_line_drag_handler.find_line_near_point(
            scene_pos, all_lines
        )
        
        # 如果点击的是可拖拽的价格线，优先处理拖拽
        if clicked_line and clicked_line.movable:
            self._price_line_drag_handler.start_drag(clicked_line)
            event.accept()
            return

        # Check if in drawing mode (只有在没有点击到价格线时才处理画线)
        if self._drawing_order_controller and self._drawing_order_controller.is_enabled():
            # Handle drawing order mode
            if self._first_plot:
                # Get click price
                view_box = self._first_plot.getViewBox()
                if view_box:
                    scene_pos = self.mapToScene(event.pos())
                    view_pos = view_box.mapSceneToView(scene_pos)
                    price = view_pos.y()
                    
                    if price > 0:
                        # Show preview line
                        self._drawing_order_controller.show_preview_line(price, "long")
                        
                        # Emit signal for order dialog (will be handled by parent widget)
                        # For now, we'll create a callback mechanism
                        if hasattr(self, '_on_drawing_click'):
                            self._on_drawing_click(price)
                        event.accept()
                        return

        super().mousePressEvent(event)
    
    def set_drawing_click_callback(self, callback) -> None:
        """
        Set callback for drawing mode click events.
        
        Args:
            callback: Callback function(price: float) called when clicking in drawing mode
        """
        self._on_drawing_click = callback
    
    def set_drawing_mode_changed_callback(self, callback) -> None:
        """
        Set callback for drawing mode state changes.
        
        Args:
            callback: Callback function(enabled: bool) called when drawing mode is enabled/disabled
        """
        self._on_drawing_mode_changed = callback
    
    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        """
        Handle key press events.
        
        - ESC: Disable drawing order mode
        """
        if event.key() == QtCore.Qt.Key.Key_Escape:
            # Disable drawing order mode when ESC is pressed
            if self._drawing_order_controller and self._drawing_order_controller.is_enabled():
                self._drawing_order_controller.disable()
                # Notify parent widget to update button state
                if self._on_drawing_mode_changed:
                    self._on_drawing_mode_changed(False)
                event.accept()
                return
        
        super().keyPressEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        """
        Handle mouse release event to end dragging price line.
        """
        if self._price_line_drag_handler and self._price_line_drag_handler.is_dragging():
            dragging_line = self._price_line_drag_handler.get_dragging_line()
            final_price = self._price_line_drag_handler.end_drag()
            
            if dragging_line and final_price is not None:
                # 检查拖拽的是挂单线还是止损/止盈线
                from .price_line import PriceLineType
                line_type = dragging_line.get_line_type()
                
                if line_type == PriceLineType.PENDING:
                    # 如果拖拽的是挂单线，更新关联的止损/止盈线
                    self._update_related_lines_on_drag_end(dragging_line, final_price)
                elif line_type in (PriceLineType.STOP_LOSS, PriceLineType.TAKE_PROFIT):
                    # 如果拖拽的是止损/止盈线，更新保存的点数
                    self._update_points_on_line_drag(dragging_line, final_price, line_type)
            
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:
        """
        Handle double click event for price line actions.
        
        - Double click pending line: Delete entire pending order
        - Double click entry line: Close position
        - Double click stop loss/take profit line: Delete the line
        """
        if not self._price_line_drag_handler or not self._first_plot:
            super().mouseDoubleClickEvent(event)
            return

        # Get scene position
        scene_pos = self.mapToScene(event.pos())
        
        # Get all price lines
        all_lines = list(self._price_line_manager.get_all_lines().values())
        
        # Find line near click position
        clicked_line = self._price_line_drag_handler.find_line_near_point(
            scene_pos, all_lines
        )
        
        if clicked_line:
            line_type = clicked_line.get_line_type()
            
            # Find line ID in manager
            line_id = None
            for lid, line in self._price_line_manager.get_all_lines().items():
                if line == clicked_line:
                    line_id = lid
                    break
            
            if line_id:
                if line_type == PriceLineType.PENDING:
                    # Double click pending line: Delete entire pending order with confirmation
                    from vnpy.trader.ui import QtWidgets
                    from vnpy.trader.locale import _
                    
                    reply = QtWidgets.QMessageBox.question(
                        self,
                        _("确认删除"),
                        _("确定要删除挂单线吗？\n这将同时撤销关联的订单。"),
                        QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                        QtWidgets.QMessageBox.StandardButton.No
                    )
                    
                    if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                        # Get order ID if linked
                        vt_orderid = None
                        if self._drawing_order_controller:
                            vt_orderid = self._drawing_order_controller.get_order_id_for_line(line_id)
                            
                            # 删除关联的止损线和止盈线
                            if hasattr(self._drawing_order_controller, '_pending_line_relations'):
                                relations = self._drawing_order_controller._pending_line_relations.get(line_id)
                                if relations:
                                    # 删除止损线
                                    stop_loss_info = relations.get("stop_loss")
                                    if stop_loss_info and stop_loss_info.get("line_id"):
                                        self._price_line_manager.delete_line(stop_loss_info["line_id"])
                                    # 删除止盈线
                                    take_profit_info = relations.get("take_profit")
                                    if take_profit_info and take_profit_info.get("line_id"):
                                        self._price_line_manager.delete_line(take_profit_info["line_id"])
                                # 清理关联关系
                                self._drawing_order_controller._pending_line_relations.pop(line_id, None)
                            
                            # 清理挂单参数（如果存在）
                            if hasattr(self._drawing_order_controller, '_pending_order_params'):
                                self._drawing_order_controller._pending_order_params.pop(line_id, None)
                            
                            # 取消注册价格突破监控
                            if self._breakthrough_monitor:
                                self._breakthrough_monitor.unregister_line(line_id)
                            
                            if vt_orderid:
                                # Cancel order if exists
                                # Note: This requires access to main_engine, which should be set via set_main_engine
                                if self._main_engine:
                                    try:
                                        # Get order to cancel
                                        order = self._main_engine.get_order(vt_orderid)
                                        if order:
                                            from vnpy.trader.object import CancelRequest
                                            cancel_req = CancelRequest(
                                                orderid=order.orderid,
                                                symbol=order.symbol,
                                                exchange=order.exchange
                                            )
                                            self._main_engine.cancel_order(cancel_req, order.gateway_name)
                                    except Exception as e:
                                        print(f"Error canceling order {vt_orderid}: {e}")
                            
                            # Remove line from controller (this will also remove mappings)
                            if vt_orderid:
                                self._drawing_order_controller.remove_order_line(vt_orderid)
                            else:
                                # If no order linked, just remove the line
                                self._price_line_manager.delete_line(line_id)
                        else:
                            # No controller, just remove the line
                            self._price_line_manager.delete_line(line_id)
                elif line_type == PriceLineType.ENTRY:
                    # Double click entry line: Close position
                    # TODO: In Phase 3, this will trigger close position order
                    pass
                elif line_type in (PriceLineType.STOP_LOSS, PriceLineType.TAKE_PROFIT):
                    # Double click stop loss/take profit: Delete the line
                    self._price_line_manager.delete_line(line_id)
            
            event.accept()
            return

        super().mouseDoubleClickEvent(event)
    
    def _update_related_lines_on_drag(self, dragging_line, new_price: float) -> None:
        """
        拖拽挂单线时，实时更新关联的止损/止盈线位置。
        
        Args:
            dragging_line: 正在拖拽的价格线
            new_price: 新的价格
        """
        if not self._drawing_order_controller:
            return
        
        # 检查是否是挂单线
        from .price_line import PriceLineType
        if dragging_line.get_line_type() != PriceLineType.PENDING:
            return
        
        # 找到挂单线的ID
        line_id = None
        for lid, line in self._price_line_manager.get_all_lines().items():
            if line == dragging_line:
                line_id = lid
                break
        
        if not line_id:
            return
        
        # 获取关联关系
        if not hasattr(self._drawing_order_controller, '_pending_line_relations'):
            return
        
        relations = self._drawing_order_controller._pending_line_relations.get(line_id)
        if not relations:
            return
        
        # 获取订单参数以获取方向和pricetick
        if not hasattr(self._drawing_order_controller, '_pending_order_params'):
            return
        
        order_data = self._drawing_order_controller._pending_order_params.get(line_id)
        if not order_data:
            return
        
        params = order_data.get("params", {})
        contract = order_data.get("contract")
        if not contract:
            return
        
        direction = params.get("direction")
        # 对于 MHImain，最小变动单位是 1 个点
        # 如果合约数据中的 pricetick 不正确，使用默认值 1.0
        pricetick = contract.pricetick if contract.pricetick > 0 else 1.0
        pricetick = max(pricetick, 1.0)  # 确保至少为 1.0
        
        # 判断方向：Direction.LONG 或 "多" 表示做多
        from vnpy.trader.constant import Direction
        is_long = (direction == Direction.LONG)
        
        # 更新止损线
        stop_loss_info = relations.get("stop_loss")
        if stop_loss_info:
            stop_loss_line_id = stop_loss_info.get("line_id")
            stop_loss_points = stop_loss_info.get("points", 50)
            if stop_loss_line_id:
                stop_loss_line = self._price_line_manager.get_line(stop_loss_line_id)
                if stop_loss_line:
                    # 根据新价格和点数计算止损价格（使用pricetick）
                    if is_long:
                        new_stop_loss_price = new_price - stop_loss_points * pricetick
                    else:
                        new_stop_loss_price = new_price + stop_loss_points * pricetick
                    # 获取价格精度
                    price_precision = getattr(self, '_price_precision', 0)
                    stop_loss_line.set_price(new_stop_loss_price, price_precision)
        
        # 更新止盈线
        take_profit_info = relations.get("take_profit")
        if take_profit_info:
            take_profit_line_id = take_profit_info.get("line_id")
            take_profit_points = take_profit_info.get("points", 50)
            if take_profit_line_id:
                take_profit_line = self._price_line_manager.get_line(take_profit_line_id)
                if take_profit_line:
                    # 根据新价格和点数计算止盈价格（使用pricetick）
                    if is_long:
                        new_take_profit_price = new_price + take_profit_points * pricetick
                    else:
                        new_take_profit_price = new_price - take_profit_points * pricetick
                    # 获取价格精度
                    price_precision = getattr(self, '_price_precision', 0)
                    take_profit_line.set_price(new_take_profit_price, price_precision)
    
    def _update_related_lines_on_drag_end(self, dragging_line, final_price: float) -> None:
        """
        拖拽挂单线结束时，最终更新关联的止损/止盈线位置。
        
        Args:
            dragging_line: 正在拖拽的价格线
            final_price: 最终价格
        """
        # 使用相同的逻辑更新
        self._update_related_lines_on_drag(dragging_line, final_price)
    
    def _update_points_on_line_drag(self, dragged_line, new_price: float, line_type) -> None:
        """
        当单独拖拽止损线或止盈线时，根据新价格反推点数并更新保存。
        
        Args:
            dragged_line: 被拖拽的止损/止盈线
            new_price: 新的价格
            line_type: 价格线类型（STOP_LOSS 或 TAKE_PROFIT）
        """
        if not self._drawing_order_controller:
            return
        
        # 找到被拖拽的线的ID
        dragged_line_id = None
        for lid, line in self._price_line_manager.get_all_lines().items():
            if line == dragged_line:
                dragged_line_id = lid
                break
        
        if not dragged_line_id:
            return
        
        # 反向查找：找到包含此止损/止盈线的挂单线
        if not hasattr(self._drawing_order_controller, '_pending_line_relations'):
            return
        
        pending_line_id = None
        relation_key = None
        
        # 遍历所有挂单线的关联关系，找到包含此止损/止盈线的挂单线
        for pid, relations in self._drawing_order_controller._pending_line_relations.items():
            stop_loss_info = relations.get("stop_loss")
            take_profit_info = relations.get("take_profit")
            
            if stop_loss_info and stop_loss_info.get("line_id") == dragged_line_id:
                pending_line_id = pid
                relation_key = "stop_loss"
                break
            elif take_profit_info and take_profit_info.get("line_id") == dragged_line_id:
                pending_line_id = pid
                relation_key = "take_profit"
                break
        
        if not pending_line_id or not relation_key:
            return
        
        # 获取挂单线的价格和订单参数
        pending_line = self._price_line_manager.get_line(pending_line_id)
        if not pending_line:
            return
        
        pending_price = pending_line.get_price()
        
        # 获取订单参数以获取方向和pricetick
        if not hasattr(self._drawing_order_controller, '_pending_order_params'):
            return
        
        order_data = self._drawing_order_controller._pending_order_params.get(pending_line_id)
        if not order_data:
            return
        
        params = order_data.get("params", {})
        contract = order_data.get("contract")
        if not contract:
            return
        
        direction = params.get("direction")
        # 对于 MHImain，最小变动单位是 1 个点
        pricetick = contract.pricetick if contract.pricetick > 0 else 1.0
        pricetick = max(pricetick, 1.0)  # 确保至少为 1.0
        
        # 判断方向：Direction.LONG 或 "多" 表示做多
        from vnpy.trader.constant import Direction
        is_long = (direction == Direction.LONG)
        
        # 根据新价格和挂单线价格，反推点数
        price_diff = abs(new_price - pending_price)
        new_points = int(round(price_diff / pricetick))
        
        # 确保点数至少为1
        if new_points < 1:
            new_points = 1
        
        # 更新保存的点数
        relations = self._drawing_order_controller._pending_line_relations.get(pending_line_id)
        if relations and relation_key in relations:
            relations[relation_key]["points"] = new_points
            # 记录日志（如果有main_engine的话）
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"更新{relation_key}点数: 挂单价格={pending_price:.2f}, 新价格={new_price:.2f}, "
                    f"价格差={price_diff:.2f}, pricetick={pricetick}, 新点数={new_points}"
                )

    def _on_key_left(self) -> None:
        """
        Move chart to left.
        """
        self._right_ix -= 1
        self._right_ix = max(self._right_ix, self._bar_count)

        self._update_x_range()

        if self._cursor:
            self._cursor.move_left()
            self._cursor.update_info()

    def _on_key_right(self) -> None:
        """
        Move chart to right.
        """
        self._right_ix += 1
        self._right_ix = min(self._right_ix, self._manager.get_count())

        self._update_x_range()

        if self._cursor:
            self._cursor.move_right()
            self._cursor.update_info()

    def _on_key_down(self) -> None:
        """
        Zoom out the chart.
        """
        self._bar_count = int(self._bar_count * 1.2)
        self._bar_count = min(int(self._bar_count), self._manager.get_count())

        self._update_x_range()

        if self._cursor:
            self._cursor.update_info()

    def _on_key_up(self) -> None:
        """
        Zoom in the chart.
        """
        self._bar_count = int(self._bar_count / 1.2)
        self._bar_count = max(int(self._bar_count), self.MIN_BAR_COUNT)

        self._update_x_range()

        if self._cursor:
            self._cursor.update_info()

    def move_to_right(self) -> None:
        """
        Move chart to the most right.
        """
        self._right_ix = self._manager.get_count()
        self._update_x_range()

        if self._cursor:
            self._cursor.update_info()
    
    def set_future_bars(self, bars: int) -> None:
        """
        Set the number of future bars (empty space on the right).
        """
        self._future_bars = bars
        self._update_plot_limits()


class ChartCursor(QtCore.QObject):
    """"""

    def __init__(
        self,
        widget: ChartWidget,
        manager: BarManager,
        plots: dict[str, pg.GraphicsObject],
        item_plot_map: dict[ChartItem, pg.GraphicsObject]
    ) -> None:
        """"""
        super().__init__()

        self._widget: ChartWidget = widget
        self._manager: BarManager = manager
        self._plots: dict[str, pg.GraphicsObject] = plots
        self._item_plot_map: dict[ChartItem, pg.GraphicsObject] = item_plot_map

        self._x: int = 0
        self._y: float = 0
        self._plot_name: str = ""

        self._init_ui()
        self._connect_signal()

    def _init_ui(self) -> None:
        """"""
        self._init_line()
        self._init_label()
        self._init_info()

    def _init_line(self) -> None:
        """
        Create line objects.
        """
        self._v_lines: dict[str, pg.InfiniteLine] = {}
        self._h_lines: dict[str, pg.InfiniteLine] = {}
        self._views: dict[str, pg.ViewBox] = {}

        pen: QtGui.QPen = pg.mkPen(WHITE_COLOR)

        for plot_name, plot in self._plots.items():
            v_line: pg.InfiniteLine = pg.InfiniteLine(angle=90, movable=False, pen=pen)
            h_line: pg.InfiniteLine = pg.InfiniteLine(angle=0, movable=False, pen=pen)
            view: pg.ViewBox = plot.getViewBox()

            for line in [v_line, h_line]:
                line.setZValue(0)
                line.hide()
                view.addItem(line)

            self._v_lines[plot_name] = v_line
            self._h_lines[plot_name] = h_line
            self._views[plot_name] = view

    def _init_label(self) -> None:
        """
        Create label objects on axis.
        """
        self._y_labels: dict[str, pg.TextItem] = {}
        for plot_name, plot in self._plots.items():
            label: pg.TextItem = pg.TextItem(
                plot_name, fill=CURSOR_COLOR, color=BLACK_COLOR)
            label.hide()
            label.setZValue(2)
            label.setFont(NORMAL_FONT)
            plot.addItem(label, ignoreBounds=True)
            self._y_labels[plot_name] = label

        self._x_label: pg.TextItem = pg.TextItem(
            "datetime", fill=CURSOR_COLOR, color=BLACK_COLOR)
        self._x_label.hide()
        self._x_label.setZValue(2)
        self._x_label.setFont(NORMAL_FONT)
        plot.addItem(self._x_label, ignoreBounds=True)

    def _init_info(self) -> None:
        """
        """
        self._infos: dict[str, pg.TextItem] = {}
        for plot_name, plot in self._plots.items():
            info: pg.TextItem = pg.TextItem(
                "info",
                color=CURSOR_COLOR,
                border=CURSOR_COLOR,
                fill=BLACK_COLOR
            )
            info.hide()
            info.setZValue(2)
            info.setFont(NORMAL_FONT)
            plot.addItem(info)  # , ignoreBounds=True)
            self._infos[plot_name] = info

    def _connect_signal(self) -> None:
        """
        Connect mouse move signal to update function.
        """
        self._widget.scene().sigMouseMoved.connect(self._mouse_moved)

    def _mouse_moved(self, evt: tuple) -> None:
        """
        Callback function when mouse is moved.
        """
        if not self._manager.get_count():
            return

        # First get current mouse point
        pos: tuple = evt

        for plot_name, view in self._views.items():
            rect = view.sceneBoundingRect()

            if rect.contains(pos):
                mouse_point = view.mapSceneToView(pos)
                self._x = to_int(mouse_point.x())
                self._y = mouse_point.y()
                self._plot_name = plot_name
                break

        # Then update cursor component
        self._update_line()
        self._update_label()
        self.update_info()

    def _update_line(self) -> None:
        """"""
        for v_line in self._v_lines.values():
            v_line.setPos(self._x)
            v_line.show()

        for plot_name, h_line in self._h_lines.items():
            if plot_name == self._plot_name:
                h_line.setPos(self._y)
                h_line.show()
            else:
                h_line.hide()

    def _update_label(self) -> None:
        """"""
        bottom_plot: pg.PlotItem = list(self._plots.values())[-1]
        axis_width = bottom_plot.getAxis("right").width()
        axis_height = bottom_plot.getAxis("bottom").height()
        axis_offset: QtCore.QPointF = QtCore.QPointF(axis_width, axis_height)

        bottom_view: pg.ViewBox = list(self._views.values())[-1]
        bottom_right = bottom_view.mapSceneToView(
            bottom_view.sceneBoundingRect().bottomRight() - axis_offset
        )

        for plot_name, label in self._y_labels.items():
            if plot_name == self._plot_name:
                label.setText(str(self._y))
                label.show()
                label.setPos(bottom_right.x(), self._y)
            else:
                label.hide()

        dt: datetime | None = self._manager.get_datetime(self._x)
        if dt:
            self._x_label.setText(dt.strftime("%Y-%m-%d %H:%M:%S"))
            self._x_label.show()
            self._x_label.setPos(self._x, bottom_right.y())
            self._x_label.setAnchor((0, 0))

    def update_info(self) -> None:
        """"""
        buf: dict = {}

        for item, plot in self._item_plot_map.items():
            item_info_text: str = item.get_info_text(self._x)

            if plot not in buf:
                buf[plot] = item_info_text
            else:
                if item_info_text:
                    buf[plot] += ("\n\n" + item_info_text)

        for plot_name, plot in self._plots.items():
            plot_info_text: str = buf[plot]
            info: pg.TextItem = self._infos[plot_name]
            info.setText(plot_info_text)
            info.show()

            view: pg.ViewBox = self._views[plot_name]
            top_left = view.mapSceneToView(view.sceneBoundingRect().topLeft())
            info.setPos(top_left)

    def move_right(self) -> None:
        """
        Move cursor index to right by 1.
        """
        if self._x == self._manager.get_count() - 1:
            return
        self._x += 1

        self._update_after_move()

    def move_left(self) -> None:
        """
        Move cursor index to left by 1.
        """
        if self._x == 0:
            return
        self._x -= 1

        self._update_after_move()

    def _update_after_move(self) -> None:
        """
        Update cursor after moved by left/right.
        """
        bar: BarData | None = self._manager.get_bar(self._x)
        if bar is None:
            return

        self._y = bar.close_price

        self._update_line()
        self._update_label()

    def clear_all(self) -> None:
        """
        Clear all data.
        """
        self._x = 0
        self._y = 0
        self._plot_name = ""

        for line in list(self._v_lines.values()) + list(self._h_lines.values()):
            line.hide()

        for label in list(self._y_labels.values()) + [self._x_label]:
            label.hide()
