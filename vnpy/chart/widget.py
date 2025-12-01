from datetime import datetime
from time import time
from typing import Optional

import pyqtgraph as pg      # type: ignore

from vnpy.trader.ui import QtGui, QtWidgets, QtCore
from vnpy.trader.object import BarData, PositionData, OrderData, TickData
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
from .price_line_database import PriceLineDatabase
from .position_holding import PositionHolding, EntryPosition
from .widget_position_helper import (
    add_entry_to_holding,
    update_position_holding_from_order,
    process_position_close
)
from .widget_position import ChartWidgetPositionMixin
from .widget_order import ChartWidgetOrderMixin
from .widget_trigger import ChartWidgetTriggerMixin
from .widget_mouse import ChartWidgetMouseMixin
from .widget_chart import ChartWidgetChartMixin
from .widget_database import ChartWidgetDatabaseMixin
from .widget_cursor import ChartCursor


pg.setConfigOptions(antialias=True)


class ChartWidget(
    pg.PlotWidget,
    ChartWidgetPositionMixin,
    ChartWidgetOrderMixin,
    ChartWidgetTriggerMixin,
    ChartWidgetMouseMixin,
    ChartWidgetChartMixin,
    ChartWidgetDatabaseMixin
):
    """
    ChartWidget - 图表组件主类
    
    通过 Mixin 模式组织代码，将不同功能模块分离到不同的 Mixin 类中：
    - ChartWidgetPositionMixin: 持仓管理相关功能
    - ChartWidgetOrderMixin: 订单处理相关功能
    - ChartWidgetTriggerMixin: 价格突破触发下单/平仓功能
    - ChartWidgetMouseMixin: 鼠标事件处理功能
    - ChartWidgetChartMixin: 图表更新和显示功能
    - ChartWidgetDatabaseMixin: 数据库操作功能
    
    这样可以保持单一类的同时，提高代码的可维护性和可测试性。
    
    Example:
        >>> from vnpy.chart import ChartWidget, CandleItem, VolumeItem
        >>> widget = ChartWidget()
        >>> widget.add_plot("candle", hide_x_axis=True)
        >>> widget.add_plot("volume", maximum_height=200)
        >>> widget.add_item(CandleItem, "candle", "candle")
        >>> widget.add_item(VolumeItem, "volume", "volume")
        >>> widget.add_cursor()
    """
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
        
        # Price line database (for persistence)
        self._price_line_database: PriceLineDatabase | None = None
        
        # Price line manager (will be initialized with database after vt_symbol is set)
        self._price_line_manager: PriceLineManager | None = None
        
        # Price line drag handler (will be initialized when plot is added)
        self._price_line_drag_handler: PriceLineDragHandler | None = None
        
        # Drawing order controller (will be initialized when plot is added)
        self._drawing_order_controller: DrawingOrderController | None = None
        
        # Price breakthrough monitor
        self._breakthrough_monitor: PriceBreakthroughMonitor = PriceBreakthroughMonitor()
        
        # Price line storage (legacy, kept for compatibility)
        self._price_line_storage: PriceLineStorage = PriceLineStorage()
        
        # 持仓管理：direction -> PositionHolding
        # 用于管理同方向的多个入场持仓，支持FIFO平仓和合并显示
        self._position_holdings: dict[str, PositionHolding] = {}  # "long" or "short" -> PositionHolding
        
        # 入场线与止损/止盈线的关联关系
        # entry_line_id -> {"stop_loss": line_id, "take_profit": line_id}
        self._entry_line_relations: dict[str, dict[str, str]] = {}
        
        # ✅ 性能优化：订单更新事件去重机制
        # 记录已处理的订单更新事件，避免重复处理
        # 格式：order_key -> timestamp
        # order_key = f"{vt_orderid}_{status.value}"
        self._processed_order_updates: dict[str, float] = {}
        self._order_update_dedup_ttl = 1.0  # 去重TTL：1秒（确保短时间内相同事件只处理一次）
        
        # ✅ 双击事件防抖机制：防止短时间内对同一入场线重复触发平仓
        # 格式：entry_line_id -> timestamp
        self._last_double_click_close: dict[str, float] = {}
        self._double_click_debounce_ttl = 2.0  # 防抖TTL：2秒（防止短时间内重复双击）
        
        # ✅ 止损/止盈触发保护：使用RLock确保一次只有一个止损/止盈线触发平仓
        # 保护的是"触发止损/止盈平仓"这个逻辑本身，无论是真实tickdata触发还是模拟触发
        from threading import RLock
        self._stop_loss_trigger_lock = RLock()  # 保护止损线触发平仓逻辑
        self._take_profit_trigger_lock = RLock()  # 保护止盈线触发平仓逻辑
        self._pending_order_trigger_lock = RLock()  # 保护挂单线触发下单逻辑
        
        # 主力合约映射：直接使用gateway的缓存，无需在此重复缓存
        
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
        
        # Callback for drawing mode click events
        self._on_drawing_click: callable | None = None
        
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
        
        Returns:
            PriceLineManager instance. If not initialized, creates a default one.
        """
        if self._price_line_manager is None:
            # 延迟初始化
            if self._price_line_database is None:
                self._price_line_database = PriceLineDatabase()
            self._price_line_manager = PriceLineManager(
                database=self._price_line_database,
                vt_symbol=self._vt_symbol if hasattr(self, '_vt_symbol') else None
            )
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
        
        # 初始化数据库和价格线管理器
        if self._price_line_database is None:
            self._price_line_database = PriceLineDatabase()
        
        if self._price_line_manager is None:
            self._price_line_manager = PriceLineManager(
                database=self._price_line_database,
                vt_symbol=vt_symbol
            )
        else:
            self._price_line_manager.set_database(self._price_line_database, vt_symbol)
        
        # 从数据库加载价格线
        if self._first_plot:
            count = self._price_line_manager.load_from_database(self._first_plot)
            if hasattr(self, '_main_engine') and self._main_engine and count > 0:
                self._main_engine.write_log(
                    f"[ChartWidget] 从数据库加载了 {count} 条价格线",
                    "ChartWidget"
                )
            
            # 加载关联关系
            self._load_line_relations()
            
            # 加载持仓记录（用于FIFO平仓）
            self._load_position_holdings()
        
        if self._drawing_order_controller:
            self._drawing_order_controller.set_vt_symbol(vt_symbol)
    
    def _get_main_contract_mapping(self, main_engine: object, force_refresh: bool = False) -> dict[str, str]:
        """
        获取主力合约映射（复用gateway的缓存）。
        
        Args:
            main_engine: MainEngine实例
            force_refresh: 已废弃，保留以兼容现有调用（gateway会自动更新缓存）
            
        Returns:
            主力合约映射字典：main_vt_symbol -> actual_vt_symbol
            例如：{"MHImain.HKFE": "MHI2512.HKFE"}
        """
        # 直接从gateway获取映射（gateway已有缓存机制，无需在此重复缓存）
        mapping: dict[str, str] = {}
        
        if main_engine and hasattr(main_engine, 'get_all_gateway_names'):
            for gateway_name in main_engine.get_all_gateway_names():
                gateway = main_engine.get_gateway(gateway_name)
                if gateway and hasattr(gateway, 'get_main_contract_mapping'):
                    contract_mapping = gateway.get_main_contract_mapping()
                    # 将映射转换为 vt_symbol 格式
                    for main_symbol, actual_symbol in contract_mapping.items():
                        # 尝试从main_engine获取实际合约来确定交易所
                        exchange = None
                        try:
                            # 尝试获取实际合约来确定交易所
                            # 先尝试直接使用actual_symbol作为vt_symbol查询
                            actual_contract = main_engine.get_contract(actual_symbol)
                            if actual_contract:
                                exchange = actual_contract.exchange
                            else:
                                # 如果直接查询失败，尝试从所有合约中查找匹配的
                                all_contracts = main_engine.get_all_contracts()
                                for contract in all_contracts:
                                    if contract.symbol == actual_symbol:
                                        exchange = contract.exchange
                                        break
                        except Exception:
                            pass
                        
                        if exchange:
                            main_vt_symbol = f"{main_symbol}.{exchange.value}"
                            actual_vt_symbol = f"{actual_symbol}.{exchange.value}"
                            mapping[main_vt_symbol] = actual_vt_symbol
        
        return mapping
    
    def _find_position_by_main_contract_mapping(
        self, 
        main_engine: object,
        main_vt_symbol: str,
        position_direction_enum,
        contract
    ) -> Optional["PositionData"]:
        """
        通过主力合约映射查找实际合约的持仓（复用方法）。
        
        Args:
            main_engine: MainEngine实例
            main_vt_symbol: 主力合约VT符号（如 "MHImain.HKFE"）
            position_direction_enum: 持仓方向枚举（Direction.LONG 或 Direction.SHORT）
            contract: 合约对象（用于获取gateway_name和exchange）
            
        Returns:
            持仓对象，如果未找到则返回None
        """
        # 首先尝试使用主力合约查询持仓
        vt_positionid = f"{contract.gateway_name}.{main_vt_symbol}.{position_direction_enum.value}"
        position = main_engine.get_position(vt_positionid)
        
        if position and position.volume > 0:
            return position
        
        # 如果没找到，尝试通过主力合约映射查找（直接使用gateway的缓存）
        mapping = self._get_main_contract_mapping(main_engine)
        actual_vt_symbol = mapping.get(main_vt_symbol)
        
        if actual_vt_symbol:
            # 使用实际合约查询持仓
            actual_vt_positionid = f"{contract.gateway_name}.{actual_vt_symbol}.{position_direction_enum.value}"
            position = main_engine.get_position(actual_vt_positionid)
            if position and position.volume > 0:
                if main_engine:
                    main_engine.write_log(
                        f"[ChartWidget] 通过主力合约映射找到持仓 "
                        f"(图表={main_vt_symbol}, 实际={actual_vt_symbol})",
                        "ChartWidget"
                    )
                return position
        
        return None
    
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
    
    def get_drawing_order_controller(self) -> DrawingOrderController | None:
        """
        Get drawing order controller instance.

        Returns:
            DrawingOrderController instance or None
        """
        return self._drawing_order_controller
    
    def _on_price_breakthrough(self, event) -> None:
        """
        处理价格突破事件，触发挂单成交（通用方法，供真实tickdata和模拟触发共用）
        
        Args:
            event: BreakthroughEvent实例
        """
        from .price_breakthrough import BreakthroughEvent
        
        line_id = event.line_id
        line = self._price_line_manager.get_line(line_id) if self._price_line_manager else None
        if not line:
            return
        
        # 获取tick数据（优先从event中获取，如果没有则从main_engine获取）
        from vnpy.trader.object import TickData
        tick = event.tick
        if not tick or tick.last_price <= 0:
            # 如果event中没有tick数据，从main_engine获取最新tick
            if not self._main_engine or not self._vt_symbol:
                return
            tick = self._main_engine.get_tick(self._vt_symbol)
            if not tick or tick.last_price <= 0:
                # 如果仍然没有tick数据，创建一个基于event的模拟tick
                from vnpy.trader.utility import extract_vt_symbol
                from datetime import datetime
                
                symbol, exchange = extract_vt_symbol(self._vt_symbol)
                contract = self._main_engine.get_contract(self._vt_symbol)
                if not contract:
                    return
                
                # 创建基于event的模拟tick
                tick = TickData(
                    symbol=symbol,
                    exchange=exchange,
                    datetime=datetime.now(),
                    gateway_name=contract.gateway_name,
                    last_price=event.current_price,
                    bid_price_1=event.current_price - 1.0,
                    ask_price_1=event.current_price + 1.0,
                    bid_volume_1=100,
                    ask_volume_1=100,
                    volume=0,
                    open_interest=0,
                )
        
        # 调用通用触发方法
        self.trigger_pending_order_breakthrough(line_id, line, tick)

    def clear_all(self) -> None:
        """
        Clear all data.
        """
        self._manager.clear_all()

        for item in self._items.values():
            item.clear_all()

        if self._cursor:
            self._cursor.clear_all()

        # Clear all price lines (if manager is initialized)
        if self._price_line_manager:
            self._price_line_manager.clear_all()
        
        # Clear breakthrough monitor
        if self._breakthrough_monitor:
            self._breakthrough_monitor.clear()

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
        
        super().keyPressEvent(event)
    
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
            
            # 如果正在拖拽，取消拖拽（包括从入场线拖拽）
            if self._price_line_drag_handler and self._price_line_drag_handler.is_dragging():
                self._price_line_drag_handler.cancel_drag()
                # 清理所有预览线（防止残留）
                if self._price_line_manager and self._first_plot:
                    count = self._price_line_manager.clear_preview_lines(self._first_plot)
                    if count > 0 and hasattr(self, '_main_engine') and self._main_engine:
                        self._main_engine.write_log(
                            f"[ChartWidget] 按ESC键清理了 {count} 条预览线",
                            "ChartWidget"
                        )
                event.accept()
                return
        
        super().keyPressEvent(event)
    
    def set_future_bars(self, bars: int) -> None:
        """
        Set the number of future bars (empty space on the right).
        """
        self._future_bars = bars
        if hasattr(self, '_update_plot_limits'):
            self._update_plot_limits()
    
    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """
        处理窗口关闭事件，确保数据库数据已保存。
        
        Args:
            event: 关闭事件
        """
        # 刷新数据库，确保所有数据已持久化
        if self._price_line_database:
            try:
                self._price_line_database.flush()
            except Exception as e:
                if hasattr(self, '_main_engine') and self._main_engine:
                    self._main_engine.write_log(
                        f"[ChartWidget] 关闭时刷新数据库失败: {e}",
                        "ChartWidget"
                    )
        
        # 调用父类方法
        super().closeEvent(event)
    
    def close(self) -> None:
        """
        关闭图表组件，确保数据库连接正确关闭。
        """
        # 关闭数据库连接
        if self._price_line_database:
            try:
                self._price_line_database.close()
            except Exception as e:
                if hasattr(self, '_main_engine') and self._main_engine:
                    self._main_engine.write_log(
                        f"[ChartWidget] 关闭数据库连接失败: {e}",
                        "ChartWidget"
                    )

    # ============================================================================
    # 鼠标事件方法：显式重写以确保 Mixin 方法被调用
    # ============================================================================
    # 注意：由于 MRO 顺序，PlotWidget 的鼠标事件方法会在 ChartWidgetMouseMixin 之前被调用
    # 因此需要在 ChartWidget 中显式重写这些方法，确保调用 Mixin 的方法
    
    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        """重写鼠标按下事件，确保调用 ChartWidgetMouseMixin 的方法"""
        # 直接调用 Mixin 的方法（通过 super() 会调用 PlotWidget 的方法，这不是我们想要的）
        ChartWidgetMouseMixin.mousePressEvent(self, event)
    
    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        """重写鼠标移动事件，确保调用 ChartWidgetMouseMixin 的方法"""
        ChartWidgetMouseMixin.mouseMoveEvent(self, event)
    
    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        """重写鼠标释放事件，确保调用 ChartWidgetMouseMixin 的方法"""
        ChartWidgetMouseMixin.mouseReleaseEvent(self, event)
    
    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:
        """重写鼠标双击事件，确保调用 ChartWidgetMouseMixin 的方法"""
        ChartWidgetMouseMixin.mouseDoubleClickEvent(self, event)
