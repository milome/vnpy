from datetime import datetime

import pyqtgraph as pg      # type: ignore

from vnpy.trader.ui import QtGui, QtWidgets, QtCore
from vnpy.trader.object import BarData

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


pg.setConfigOptions(antialias=True)


class ChartWidget(pg.PlotWidget):
    """"""
    MIN_BAR_COUNT = 100

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
        
        # VT symbol for the chart
        self._vt_symbol: str | None = None
        
        # MainEngine reference (optional, for order operations)
        self._main_engine: object | None = None
        
        # Price precision (number of decimal places, 0 for integer, default 0 for MHImain)
        self._price_precision: int = 0

        self._right_ix: int = 0                     # Index of most right data
        self._bar_count: int = self.MIN_BAR_COUNT   # Total bar visible in chart
        self._future_bars: int = 0                  # Extra space for future bars

        self._init_ui()

    def _init_ui(self) -> None:
        """"""
        self.setWindowTitle("ChartWidget of VeighNa")

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
