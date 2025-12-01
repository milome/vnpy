"""
Drawing order mode controller.

Manages drawing order mode state, preview line display, and order creation.
"""

from datetime import datetime
from typing import Optional, Callable

import pyqtgraph as pg  # type: ignore

from vnpy.trader.ui import QtCore, QtGui, QtWidgets
from vnpy.trader.object import OrderRequest, OrderData
from vnpy.trader.constant import Direction, Offset, OrderType, Exchange, Status

from .price_line import PriceLineItem, PriceLineManager, PriceLineType
from .price_line_drag import PriceLineDragHandler


class DrawingOrderController:
    """
    Controller for drawing order mode.
    
    Manages drawing mode state, preview line, and order creation workflow.
    """

    def __init__(
        self,
        widget: "ChartWidget",
        price_line_manager: PriceLineManager,
        drag_handler: PriceLineDragHandler,
        main_engine: Optional[object] = None,
        vt_symbol: Optional[str] = None
    ) -> None:
        """
        Initialize drawing order controller.

        Args:
            widget: ChartWidget instance
            price_line_manager: PriceLineManager instance
            drag_handler: PriceLineDragHandler instance
            main_engine: MainEngine instance for order operations
            vt_symbol: VT symbol for the chart (e.g., "MHI2512.HKFE")
        """
        self._widget = widget
        self._price_line_manager = price_line_manager
        self._drag_handler = drag_handler
        self._main_engine = main_engine
        self._vt_symbol = vt_symbol

        # Drawing mode state
        self._drawing_mode_enabled: bool = False
        
        # Preview line
        self._preview_line: Optional[PriceLineItem] = None
        self._preview_line_id: Optional[str] = None
        
        # Order tracking: line_id -> vt_orderid
        self._line_order_map: dict[str, str] = {}
        self._order_line_map: dict[str, str] = {}  # Reverse mapping
    
    def _get_price_line_manager(self) -> Optional[PriceLineManager]:
        """
        获取价格线管理器，如果未初始化则从widget获取。
        
        Returns:
            PriceLineManager实例，如果无法获取则返回None
        """
        # 如果已设置且不为None，直接返回
        if self._price_line_manager is not None:
            return self._price_line_manager
        
        # 否则从widget获取（widget的get_price_line_manager会自动初始化）
        if self._widget and hasattr(self._widget, 'get_price_line_manager'):
            try:
                manager = self._widget.get_price_line_manager()
                # 更新内部引用
                self._price_line_manager = manager
                return manager
            except Exception:
                pass
        
        return None

    def is_enabled(self) -> bool:
        """Check if drawing mode is enabled."""
        return self._drawing_mode_enabled

    def enable(self) -> None:
        """Enable drawing order mode."""
        if self._drawing_mode_enabled:
            return

        self._drawing_mode_enabled = True
        # Change cursor to indicate drawing mode
        if self._widget:
            self._widget.setCursor(QtCore.Qt.CursorShape.CrossCursor)

    def disable(self) -> None:
        """Disable drawing order mode."""
        if not self._drawing_mode_enabled:
            return

        self._drawing_mode_enabled = False
        
        # Remove preview line
        self._hide_preview_line()
        
        # 清理所有预览线（防止残留）
        price_line_manager = self._get_price_line_manager()
        if price_line_manager and self._widget and self._widget._first_plot:
            count = price_line_manager.clear_preview_lines(self._widget._first_plot)
            if count > 0 and hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                self._widget._main_engine.write_log(
                    f"[DrawingOrderController] 关闭画线下单模式时清理了 {count} 条预览线",
                    "DrawingOrderController"
                )
        
        # Restore cursor
        if self._widget:
            self._widget.setCursor(QtCore.Qt.CursorShape.ArrowCursor)

    def toggle(self) -> None:
        """Toggle drawing mode on/off."""
        if self._drawing_mode_enabled:
            self.disable()
        else:
            self.enable()

    def show_preview_line(self, price: float, direction: str = "long") -> None:
        """
        Show preview line at given price.

        Args:
            price: Price value for preview line
            direction: Trading direction ("long" or "short")
        """
        # Remove existing preview line
        self._hide_preview_line()

        # Get price line manager (ensure it's initialized)
        price_line_manager = self._get_price_line_manager()
        if not price_line_manager:
            return

        # Create new preview line
        self._preview_line_id = price_line_manager.create_line(
            price=price,
            line_type=PriceLineType.PREVIEW,
            direction=direction,
            movable=False
        )

        self._preview_line = price_line_manager.get_line(self._preview_line_id)

        # Add to plot
        if self._preview_line and self._widget._first_plot:
            self._widget._first_plot.addItem(self._preview_line)

    def update_preview_line(self, price: float) -> None:
        """
        Update preview line position.

        Args:
            price: New price value
        """
        if self._preview_line:
            self._preview_line.set_price(price)

    def _hide_preview_line(self) -> None:
        """Hide and remove preview line."""
        if self._preview_line:
            # 先从 plot 中移除预览线
            if self._preview_line.scene() is not None and self._widget and self._widget._first_plot:
                try:
                    self._widget._first_plot.removeItem(self._preview_line)
                except Exception:
                    pass
        
        if self._preview_line_id:
            price_line_manager = self._get_price_line_manager()
            if price_line_manager:
                price_line_manager.delete_line(self._preview_line_id)
            self._preview_line_id = None
            self._preview_line = None

    def get_preview_price(self) -> Optional[float]:
        """
        Get current preview line price.

        Returns:
            Price value or None if no preview line
        """
        if self._preview_line:
            return self._preview_line.get_price()
        return None

    def confirm_preview_price(self) -> Optional[float]:
        """
        Confirm preview price and return it.

        Returns:
            Confirmed price or None if no preview line
        """
        price = self.get_preview_price()
        if price is not None:
            # Remove preview line
            self._hide_preview_line()
        return price

    def set_vt_symbol(self, vt_symbol: str) -> None:
        """
        Set VT symbol for the chart.

        Args:
            vt_symbol: VT symbol (e.g., "MHI2512.HKFE")
        """
        self._vt_symbol = vt_symbol

    def set_main_engine(self, main_engine: object) -> None:
        """
        Set MainEngine instance for order operations.

        Args:
            main_engine: MainEngine instance
        """
        self._main_engine = main_engine

    def create_pending_order_line(
        self,
        price: float,
        direction: str = "long",
        line_id: Optional[str] = None
    ) -> str:
        """
        Create a pending order line (not yet submitted).

        Args:
            price: Order price
            direction: Trading direction ("long" or "short")
            line_id: Optional custom line ID

        Returns:
            Line ID string
        """
        price_line_manager = self._get_price_line_manager()
        if not price_line_manager:
            return None
        
        line_id = price_line_manager.create_line(
            price=price,
            line_type=PriceLineType.PENDING,
            direction=direction,
            movable=True,
            line_id=line_id
        )

        # Add to plot
        line = price_line_manager.get_line(line_id)
        if line and self._widget._first_plot:
            self._widget._first_plot.addItem(line)

        return line_id

    def create_entry_line(
        self,
        price: float,
        direction: str = "long",
        line_id: Optional[str] = None
    ) -> str:
        """
        Create an entry line (order filled).
        
        Note: This method should be called from the main thread.
        If called from a non-main thread, use QTimer.singleShot to schedule it.

        Args:
            price: Entry price
            direction: Trading direction ("long" or "short")
            line_id: Optional custom line ID

        Returns:
            Line ID string
        """
        # 检查是否在主线程中执行（create_entry_line由update_line_from_order调用，已确保在主线程）
        # 这里不需要再次检查，因为update_line_from_order已经处理了线程问题
        
        price_line_manager = self._get_price_line_manager()
        if not price_line_manager:
            return None
        
        line_id = price_line_manager.create_line(
            price=price,
            line_type=PriceLineType.ENTRY,
            direction=direction,
            movable=False,
            line_id=line_id
        )

        # Add to plot (Qt operation, must be in main thread)
        line = price_line_manager.get_line(line_id)
        if line:
            if self._widget._first_plot:
                self._widget._first_plot.addItem(line)
                if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                    self._widget._main_engine.write_log(
                        f"[DrawingOrderController] 已添加入场线 {line_id} 到图表，价格={price}，方向={direction}",
                        "DrawingOrderController"
                    )
            else:
                if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                    self._widget._main_engine.write_log(
                        f"[DrawingOrderController] 警告: 无法添加入场线 {line_id} 到图表，_first_plot为None",
                        "DrawingOrderController"
                    )
        else:
            if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                self._widget._main_engine.write_log(
                    f"[DrawingOrderController] 警告: 无法获取入场线 {line_id}",
                    "DrawingOrderController"
                )

        return line_id

    def link_line_to_order(self, line_id: str, vt_orderid: str) -> None:
        """
        Link a price line to an order.

        Args:
            line_id: Price line ID
            vt_orderid: VT order ID
        """
        # 添加日志
        if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
            self._widget._main_engine.write_log(
                f"[DrawingOrderController] link_line_to_order: 挂单线 {line_id} -> 订单 {vt_orderid}",
                "DrawingOrderController"
            )
        
        self._line_order_map[line_id] = vt_orderid
        self._order_line_map[vt_orderid] = line_id
        
        # 验证关联
        if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
            # 验证正向映射
            stored_orderid = self._line_order_map.get(line_id)
            # 验证反向映射
            stored_line_id = self._order_line_map.get(vt_orderid)
            self._widget._main_engine.write_log(
                f"[DrawingOrderController] 关联验证: 挂单线 {line_id} -> 订单 {stored_orderid}, 订单 {vt_orderid} -> 挂单线 {stored_line_id}",
                "DrawingOrderController"
            )

    def get_order_id_for_line(self, line_id: str) -> Optional[str]:
        """
        Get order ID for a price line.

        Args:
            line_id: Price line ID

        Returns:
            VT order ID or None if not linked
        """
        return self._line_order_map.get(line_id)

    def get_line_id_for_order(self, vt_orderid: str) -> Optional[str]:
        """
        Get line ID for an order.

        Args:
            vt_orderid: VT order ID

        Returns:
            Line ID or None if not linked
        """
        result = self._order_line_map.get(vt_orderid)
        
        # 添加日志
        if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
            all_order_ids = list(self._order_line_map.keys())
            self._widget._main_engine.write_log(
                f"[DrawingOrderController] get_line_id_for_order: 查询订单 {vt_orderid}, 结果={result}, 当前映射表中有 {len(all_order_ids)} 个订单: {all_order_ids}",
                "DrawingOrderController"
            )
        
        return result
    
    def _find_unlinked_pending_line(self, order: OrderData) -> Optional[str]:
        """
        查找未关联的挂单线（用于处理订单重委托场景）。
        
        当订单被撤销并重新委托时，新订单ID与旧订单ID不同，但应该关联到同一个挂单线。
        
        Args:
            order: 订单数据
            
        Returns:
            匹配的挂单线ID，如果没有找到则返回None
        """
        # 获取订单方向
        order_direction = "long" if order.direction == Direction.LONG else "short"
        
        if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
            self._widget._main_engine.write_log(
                f"[DrawingOrderController] 开始查找未关联挂单线: 订单={order.vt_orderid}, 方向={order_direction}, 价格={order.price}",
                "DrawingOrderController"
            )
        
        # 遍历所有价格线，查找未关联的挂单线
        price_line_manager = self._get_price_line_manager()
        if not price_line_manager:
            return None
        
        all_lines = price_line_manager.get_all_lines()
        pending_lines_count = 0
        unlinked_pending_lines_count = 0
        
        for line_id, line in all_lines.items():
            # 只检查挂单线
            if line.get_line_type() != PriceLineType.PENDING:
                continue
            
            pending_lines_count += 1
            
            # 检查是否已经关联到订单
            if line_id in self._line_order_map:
                linked_order_id = self._line_order_map.get(line_id)
                
                # ✅ 检查关联的订单是否已被撤销/取消
                # 如果订单已撤销/取消，应该清理映射关系，将此挂单线视为未关联
                is_order_cancelled = False
                if linked_order_id and hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                    # 尝试从main_engine获取订单状态
                    all_orders = self._widget._main_engine.get_all_orders()
                    for o in all_orders:
                        if o.vt_orderid == linked_order_id:
                            from vnpy.trader.constant import Status
                            if o.status in [Status.CANCELLED, Status.REJECTED]:
                                is_order_cancelled = True
                                # 清理映射关系
                                self._line_order_map.pop(line_id, None)
                                self._order_line_map.pop(linked_order_id, None)
                                if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                                    self._widget._main_engine.write_log(
                                        f"[DrawingOrderController] 挂单线 {line_id} 关联的订单 {linked_order_id} 已被撤销/取消，已清理映射关系，将此挂单线视为未关联",
                                        "DrawingOrderController"
                                    )
                                break
                            # 如果订单已全部成交，也应该清理映射（订单已成交，挂单线应该已被删除或转换）
                            elif o.status == Status.ALLTRADED:
                                is_order_cancelled = True
                                # 清理映射关系
                                self._line_order_map.pop(line_id, None)
                                self._order_line_map.pop(linked_order_id, None)
                                if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                                    self._widget._main_engine.write_log(
                                        f"[DrawingOrderController] 挂单线 {line_id} 关联的订单 {linked_order_id} 已全部成交，已清理映射关系，将此挂单线视为未关联",
                                        "DrawingOrderController"
                                    )
                                break
                
                # 如果订单已被撤销/取消/成交，继续处理此挂单线（视为未关联）
                if not is_order_cancelled:
                    if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                        self._widget._main_engine.write_log(
                            f"[DrawingOrderController] 挂单线 {line_id} 已关联到订单 {linked_order_id}，跳过",
                            "DrawingOrderController"
                        )
                    continue  # 已关联且订单仍然有效，跳过
            
            unlinked_pending_lines_count += 1
            
            # 检查方向是否匹配
            line_direction = line.get_direction()
            if line_direction != order_direction:
                if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                    self._widget._main_engine.write_log(
                        f"[DrawingOrderController] 挂单线 {line_id} 方向不匹配: 挂单线方向={line_direction}, 订单方向={order_direction}",
                        "DrawingOrderController"
                    )
                continue  # 方向不匹配，跳过
            
            # 检查价格是否匹配（允许一定的价格偏差，因为重委托时价格可能会调整）
            line_price = line.get_price()
            order_price = order.price
            
            # 如果订单价格为0或None，可能是"提交中"状态，尝试使用挂单线价格进行匹配
            if order_price == 0 or order_price is None:
                if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                    self._widget._main_engine.write_log(
                        f"[DrawingOrderController] 订单价格为0或None，尝试匹配挂单线 {line_id} (价格={line_price})",
                        "DrawingOrderController"
                    )
                # 对于价格为0的订单，如果方向匹配，直接匹配（可能是提交中状态，价格还未确定）
                if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                    self._widget._main_engine.write_log(
                        f"[DrawingOrderController] 找到匹配的未关联挂单线: {line_id} "
                        f"(方向={line_direction}, 挂单线价格={line_price}, 订单价格={order_price})",
                        "DrawingOrderController"
                    )
                return line_id
            
            price_diff = abs(line_price - order_price)
            price_tolerance = max(abs(line_price) * 0.01, 1.0)  # 允许1%或1个点的偏差
            
            if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                self._widget._main_engine.write_log(
                    f"[DrawingOrderController] 检查挂单线 {line_id}: 挂单线价格={line_price}, 订单价格={order_price}, 价格差={price_diff:.2f}, 容忍度={price_tolerance:.2f}",
                    "DrawingOrderController"
                )
            
            if price_diff <= price_tolerance:
                # 找到匹配的挂单线
                if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                    self._widget._main_engine.write_log(
                        f"[DrawingOrderController] 找到匹配的未关联挂单线: {line_id} "
                        f"(方向={line_direction}, 价格={line_price}, 订单价格={order_price}, 价格差={price_diff:.2f})",
                        "DrawingOrderController"
                    )
                return line_id
            else:
                if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                    self._widget._main_engine.write_log(
                        f"[DrawingOrderController] 挂单线 {line_id} 价格不匹配: 价格差={price_diff:.2f} > 容忍度={price_tolerance:.2f}",
                        "DrawingOrderController"
                    )
        
        # 没有找到匹配的挂单线
        if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
            self._widget._main_engine.write_log(
                f"[DrawingOrderController] 未找到匹配的未关联挂单线: 订单方向={order_direction}, 订单价格={order.price}, "
                f"总挂单线数量={pending_lines_count}, 未关联挂单线数量={unlinked_pending_lines_count}",
                "DrawingOrderController"
            )
        return None

    def _update_line_from_order_main_thread(self, order: OrderData) -> None:
        """在主线程中执行订单更新（由update_line_from_order调度）"""
        try:
            if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                self._widget._main_engine.write_log(
                    f"[DrawingOrderController] 主线程回调开始执行: order={order.vt_orderid}",
                    "DrawingOrderController"
                )
            self.update_line_from_order(order)
        except Exception as e:
            if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                import traceback
                self._widget._main_engine.write_log(
                    f"[DrawingOrderController] 主线程回调执行异常: {str(e)}\n{traceback.format_exc()}",
                    "DrawingOrderController"
                )
    
    def update_line_from_order(self, order: OrderData) -> bool:
        """
        Update price line based on order status.
        
        Note: This method should be called from the main thread.
        If called from a non-main thread, use QTimer.singleShot to schedule it.

        Args:
            order: Order data

        Returns:
            True if line was updated, False if order not linked to any line
        """
        # 明确引用全局的 Status，避免 UnboundLocalError
        from vnpy.trader.constant import Status as StatusEnum
        
        # 添加日志：开始处理订单更新
        if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
            self._widget._main_engine.write_log(
                f"[DrawingOrderController] update_line_from_order 开始处理: order={order.vt_orderid} status={order.status.value}",
                "DrawingOrderController"
            )
        
        # 检查是否在主线程中执行
        from vnpy.trader.ui import QtCore
        app = QtCore.QCoreApplication.instance()
        if app and QtCore.QThread.currentThread() != app.thread():
            # 不在主线程，使用QTimer调度到主线程
            if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                self._widget._main_engine.write_log(
                    f"[DrawingOrderController] 不在主线程，调度到主线程执行: order={order.vt_orderid}",
                    "DrawingOrderController"
                )
            # 使用functools.partial确保order对象正确传递
            from functools import partial
            QtCore.QTimer.singleShot(0, partial(self._update_line_from_order_main_thread, order))
            return True
        
        line_id = self.get_line_id_for_order(order.vt_orderid)
        if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
            self._widget._main_engine.write_log(
                f"[DrawingOrderController] 查找订单关联的挂单线: order={order.vt_orderid} line_id={line_id}",
                "DrawingOrderController"
            )
        if line_id is None:
            # ✅ 如果订单是平仓订单（offset=CLOSE），且没有关联挂单线，直接跳过
            # 平仓订单（如止损/止盈线触发的平仓订单）不应该关联挂单线
            if order.offset == Offset.CLOSE:
                if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                    self._widget._main_engine.write_log(
                        f"[DrawingOrderController] 订单 {order.vt_orderid} 是平仓订单且未关联挂单线，跳过处理（可能是止损/止盈线触发的平仓订单）",
                        "DrawingOrderController"
                    )
                # 如果是全部成交的平仓订单，添加成交标记到K线
                if order.status == StatusEnum.ALLTRADED and hasattr(self._widget, '_manager') and order.datetime:
                    direction_str = "long" if order.direction == Direction.LONG else "short"
                    self._add_trade_marker_to_chart(
                        order.datetime, direction_str, order.traded, order.price
                    )
                return True
            
            # 订单未关联到挂单线，尝试查找未关联的挂单线（用于处理订单重委托场景）
            if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                self._widget._main_engine.write_log(
                    f"[DrawingOrderController] 订单 {order.vt_orderid} 未直接关联到挂单线，尝试查找未关联的挂单线进行匹配",
                    "DrawingOrderController"
                )
            line_id = self._find_unlinked_pending_line(order)
            if line_id:
                # 找到匹配的挂单线，建立关联
                self.link_line_to_order(line_id, order.vt_orderid)
                if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                    self._widget._main_engine.write_log(
                        f"[DrawingOrderController] 订单 {order.vt_orderid} 已成功关联到未关联的挂单线 {line_id}",
                        "DrawingOrderController"
                    )
            else:
                # 订单未关联到挂单线（可能是通过 trade UI 下单）
                # 检查是否为平仓订单，如果是平仓，添加成交标记但不创建入场线
                if order.status == StatusEnum.ALLTRADED:
                    direction = "long" if order.direction == Direction.LONG else "short"
                    opposite_direction = "short" if direction == "long" else "long"
                    
                    # 检查是否为平仓行为
                    is_closing = False
                    opposite_total_volume = 0.0
                    
                    # 从 PositionHolding 获取反向持仓手数
                    if hasattr(self._widget, '_position_holdings'):
                        opposite_holding = self._widget._position_holdings.get(opposite_direction)
                        if opposite_holding:
                            opposite_total_volume = sum(e.volume for e in opposite_holding.get_all_entries())
                    
                    # 如果 PositionHolding 中没有记录，尝试从 main_engine 获取
                    if opposite_total_volume == 0 and hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                        all_positions = self._widget._main_engine.get_all_positions()
                        for pos in all_positions:
                            # 检查合约是否匹配（考虑主力合约映射）
                            pos_vt_symbol = pos.vt_symbol
                            chart_vt_symbol = getattr(self._widget, '_vt_symbol', None)
                            
                            matched = False
                            if chart_vt_symbol and pos_vt_symbol == chart_vt_symbol:
                                matched = True
                            elif chart_vt_symbol:
                                # 尝试主力合约映射
                                position_symbol = pos.symbol
                                chart_symbol = chart_vt_symbol.split('.')[0] if '.' in chart_vt_symbol else chart_vt_symbol
                                for gateway_name in self._widget._main_engine.get_all_gateway_names():
                                    gateway = self._widget._main_engine.get_gateway(gateway_name)
                                    if gateway and hasattr(gateway, 'get_main_contract_mapping'):
                                        mapping = gateway.get_main_contract_mapping()
                                        for main_symbol, actual_symbol in mapping.items():
                                            if actual_symbol == position_symbol:
                                                main_vt_symbol = f"{main_symbol}.{pos.exchange.value}"
                                                if main_vt_symbol == chart_vt_symbol:
                                                    matched = True
                                                    break
                                        if matched:
                                            break
                            
                            if matched:
                                pos_direction = "long" if pos.direction.value == "多" else "short"
                                if pos_direction == opposite_direction:
                                    opposite_total_volume = pos.volume
                                    break
                    
                    # 检查是否为平仓：订单手数 <= 反向持仓手数
                    if order.traded > 0 and order.traded <= opposite_total_volume:
                        is_closing = True
                        if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                            self._widget._main_engine.write_log(
                                f"[DrawingOrderController] 订单 {order.vt_orderid} 未关联挂单线，但检测到平仓行为: "
                                f"订单方向={direction}, 订单手数={order.traded}, 反向持仓方向={opposite_direction}, "
                                f"反向持仓手数={opposite_total_volume}, 添加成交标记",
                                "DrawingOrderController"
                            )
                        # 添加成交标记到K线（平仓也需要显示标记）
                        if hasattr(self._widget, '_manager') and order.datetime:
                            direction_str = "long" if order.direction == Direction.LONG else "short"
                            self._add_trade_marker_to_chart(
                                order.datetime, direction_str, order.traded, order.price
                            )
                        return True
                    else:
                        # 不是平仓，但也没有挂单线，无法创建入场线
                        if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                            self._widget._main_engine.write_log(
                                f"[DrawingOrderController] 订单 {order.vt_orderid} 未关联到任何挂单线，且未找到匹配的未关联挂单线，跳过更新",
                                "DrawingOrderController"
                            )
                        return False
                else:
                    # 订单未全部成交，且未关联到挂单线，跳过更新
                    if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                        self._widget._main_engine.write_log(
                            f"[DrawingOrderController] 订单 {order.vt_orderid} 未关联到任何挂单线，且未找到匹配的未关联挂单线，跳过更新",
                            "DrawingOrderController"
                        )
                    return False

        # 如果 line_id 仍然为 None，但订单状态为 ALLTRADED，尝试强制查找并删除挂单线
        if line_id is None and order.status == StatusEnum.ALLTRADED:
            # 对于模拟成交场景，可能订单没有关联到挂单线，但存在未关联的挂单线
            # 尝试查找所有未关联的挂单线，如果只有一个且方向/价格匹配，则删除它
            if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                self._widget._main_engine.write_log(
                    f"[DrawingOrderController] 订单 {order.vt_orderid} 状态为ALLTRADED但未关联挂单线，尝试强制查找并删除挂单线",
                    "DrawingOrderController"
                )
            
            # 再次尝试查找未关联的挂单线
            line_id = self._find_unlinked_pending_line(order)
            if line_id:
                # 找到匹配的挂单线，建立关联
                self.link_line_to_order(line_id, order.vt_orderid)
                if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                    self._widget._main_engine.write_log(
                        f"[DrawingOrderController] 强制查找：订单 {order.vt_orderid} 已成功关联到未关联的挂单线 {line_id}",
                        "DrawingOrderController"
                    )
            else:
                # 如果仍然没找到，尝试查找所有未关联的挂单线，如果只有一个且方向匹配，则使用它
                price_line_manager = self._get_price_line_manager()
                if price_line_manager:
                    all_lines = price_line_manager.get_all_lines()
                    unlinked_pending_lines = []
                    order_direction = "long" if order.direction == Direction.LONG else "short"
                    
                    for lid, line in all_lines.items():
                        if line.get_line_type() == PriceLineType.PENDING:
                            # 检查是否已关联
                            is_unlinked = False
                            if lid not in self._line_order_map:
                                is_unlinked = True
                            else:
                                # ✅ 检查关联的订单是否已被撤销/取消
                                linked_order_id = self._line_order_map.get(lid)
                                if linked_order_id and hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                                    # 尝试从main_engine获取订单状态
                                    all_orders = self._widget._main_engine.get_all_orders()
                                    for o in all_orders:
                                        if o.vt_orderid == linked_order_id:
                                            from vnpy.trader.constant import Status
                                            if o.status in [Status.CANCELLED, Status.REJECTED, Status.ALLTRADED]:
                                                # 订单已被撤销/取消/成交，清理映射关系
                                                self._line_order_map.pop(lid, None)
                                                self._order_line_map.pop(linked_order_id, None)
                                                is_unlinked = True
                                                if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                                                    self._widget._main_engine.write_log(
                                                        f"[DrawingOrderController] 挂单线 {lid} 关联的订单 {linked_order_id} 状态为{o.status.value}，已清理映射关系，视为未关联",
                                                        "DrawingOrderController"
                                                    )
                                                break
                            
                            if is_unlinked:
                                # 检查方向是否匹配
                                line_direction = line.get_direction()
                                if line_direction == order_direction:
                                    unlinked_pending_lines.append((lid, line))
                    
                    # 如果只有一个未关联的挂单线，且方向匹配，使用它并继续执行后续逻辑（创建入场线、迁移止损/止盈线）
                    if len(unlinked_pending_lines) == 1:
                        line_id, line = unlinked_pending_lines[0]
                        # 建立关联关系，以便后续逻辑能正确处理
                        self.link_line_to_order(line_id, order.vt_orderid)
                        if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                            self._widget._main_engine.write_log(
                                f"[DrawingOrderController] 强制查找：找到唯一的未关联挂单线 {line_id}，方向匹配，已建立关联关系，将继续执行创建入场线和迁移止损/止盈线的逻辑",
                                "DrawingOrderController"
                            )
                        # 注意：这里不直接删除挂单线，而是继续执行后续逻辑（删除挂单线、创建入场线、迁移止损/止盈线）
                        # 后续逻辑会在删除挂单线之前，先保存挂单线关联的止损/止盈线信息
                    elif len(unlinked_pending_lines) > 1:
                        if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                            self._widget._main_engine.write_log(
                                f"[DrawingOrderController] 强制查找：找到多个未关联挂单线（{len(unlinked_pending_lines)}个），无法确定使用哪一个，跳过",
                                "DrawingOrderController"
                            )
                        # 如果找到多个未关联挂单线，无法确定使用哪一个，设置为None，后续逻辑会跳过
                        line_id = None
        
        line = self._price_line_manager.get_line(line_id) if line_id else None
        if line is None:
            if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                self._widget._main_engine.write_log(
                    f"[DrawingOrderController] 挂单线 {line_id} 不存在，跳过更新",
                    "DrawingOrderController"
                )
            return False

        # Handle order status changes
        if order.status == StatusEnum.CANCELLED:
            # 订单被撤销：清理旧订单的映射关系，但保留挂单线，以便新订单（重委托）可以找到它
            if line_id:
                # 从反向映射中移除旧订单ID
                self._order_line_map.pop(order.vt_orderid, None)
                # 从正向映射中移除（但保留挂单线）
                self._line_order_map.pop(line_id, None)
                if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                    self._widget._main_engine.write_log(
                        f"[DrawingOrderController] 订单 {order.vt_orderid} 已撤销，已清理映射关系，保留挂单线 {line_id} 供新订单匹配",
                        "DrawingOrderController"
                    )
            return True
        
        # If order is filled, convert pending line to entry line
        if order.status == StatusEnum.ALLTRADED:
            if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                self._widget._main_engine.write_log(
                    f"[DrawingOrderController] 订单 {order.vt_orderid} 已全部成交，将挂单线 {line_id} 转换为入场线",
                    "DrawingOrderController"
                )
            
            # 在删除挂单线之前，保存挂单线关联的止损/止盈线信息，以便迁移到入场线
            pending_relations = None
            if hasattr(self, '_pending_line_relations') and line_id in self._pending_line_relations:
                pending_relations = self._pending_line_relations[line_id]
                if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                    self._widget._main_engine.write_log(
                        f"[DrawingOrderController] 挂单线 {line_id} 有关联的止损/止盈线，将在创建入场线后迁移",
                        "DrawingOrderController"
                    )
            
            # 在删除挂单线之前，先清理挂单线和订单的映射关系（避免映射关系混乱）
            # 注意：这里只清理旧的映射关系，新的映射关系将在创建入场线后建立
            old_line_id_in_order_map = self._order_line_map.pop(order.vt_orderid, None)
            if old_line_id_in_order_map and old_line_id_in_order_map != line_id:
                if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                    self._widget._main_engine.write_log(
                        f"[DrawingOrderController] 警告：订单 {order.vt_orderid} 在映射表中关联的挂单线 {old_line_id_in_order_map} 与当前挂单线 {line_id} 不一致，已清理旧映射",
                        "DrawingOrderController"
                    )
            if line_id:
                old_order_id_in_line_map = self._line_order_map.pop(line_id, None)
                if old_order_id_in_line_map and old_order_id_in_line_map != order.vt_orderid:
                    if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                        self._widget._main_engine.write_log(
                            f"[DrawingOrderController] 警告：挂单线 {line_id} 在映射表中关联的订单 {old_order_id_in_line_map} 与当前订单 {order.vt_orderid} 不一致，已清理旧映射",
                            "DrawingOrderController"
                        )
                if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                    self._widget._main_engine.write_log(
                        f"[DrawingOrderController] 已清理挂单线 {line_id} 和订单 {order.vt_orderid} 的映射关系（准备删除挂单线）",
                        "DrawingOrderController"
                    )
            
            # Remove old line
            # 先从 plot 中移除挂单线
            pending_line = self._price_line_manager.get_line(line_id)
            if pending_line and hasattr(self._widget, '_first_plot') and self._widget._first_plot:
                try:
                    self._widget._first_plot.removeItem(pending_line)
                except Exception:
                    pass
            
            # 然后从管理器中删除
            delete_result = self._price_line_manager.delete_line(line_id)
            if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                self._widget._main_engine.write_log(
                    f"[DrawingOrderController] 删除挂单线 {line_id} 结果: {delete_result}",
                    "DrawingOrderController"
                )
            
            # Create entry line
            direction = "long" if order.direction == Direction.LONG else "short"
            opposite_direction = "short" if direction == "long" else "long"
            
            # ========== 检查是否为平仓行为 ==========
            # 1. 首先检查下单时是否已标记为平仓订单（从 _pending_order_params）
            is_closing = False
            if hasattr(self, '_pending_order_params') and line_id in self._pending_order_params:
                order_data = self._pending_order_params.get(line_id)
                if order_data and order_data.get("is_closing", False):
                    is_closing = True
                    if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                        self._widget._main_engine.write_log(
                            f"[DrawingOrderController] 订单 {order.vt_orderid} 在下单时已标记为平仓订单，跳过创建入场线",
                            "DrawingOrderController"
                        )
            
            # 2. 如果未标记，继续检查（兼容旧逻辑，确保数据一致性）
            if not is_closing:
                # 1. 从PositionHolding获取反向持仓手数（这是业务逻辑层面的数据源，在订单成交时已更新）
                opposite_total_volume = 0.0
                opposite_avg_price = 0.0
                if hasattr(self._widget, '_position_holdings'):
                    opposite_holding = self._widget._position_holdings.get(opposite_direction)
                    if opposite_holding:
                        # 从 entries 计算总手数
                        opposite_total_volume = sum(e.volume for e in opposite_holding.get_all_entries())
                        # 计算加权平均价格
                        if opposite_total_volume > 0:
                            opposite_avg_price = sum(e.price * e.volume for e in opposite_holding.get_all_entries()) / opposite_total_volume
                
                # 2. 如果PositionHolding中没有记录，尝试从main_engine获取最新持仓信息（可能通过trade UI下单）
                if opposite_total_volume == 0 and hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                    all_positions = self._widget._main_engine.get_all_positions()
                    for pos in all_positions:
                        # 检查合约是否匹配（考虑主力合约映射）
                        pos_vt_symbol = pos.vt_symbol
                        chart_vt_symbol = getattr(self._widget, '_vt_symbol', None)
                        
                        # 合约匹配检查
                        matched = False
                        if chart_vt_symbol and pos_vt_symbol == chart_vt_symbol:
                            matched = True
                        elif chart_vt_symbol:
                            # 尝试主力合约映射
                            position_symbol = pos.symbol
                            chart_symbol = chart_vt_symbol.split('.')[0] if '.' in chart_vt_symbol else chart_vt_symbol
                            for gateway_name in self._widget._main_engine.get_all_gateway_names():
                                gateway = self._widget._main_engine.get_gateway(gateway_name)
                                if gateway and hasattr(gateway, 'get_main_contract_mapping'):
                                    mapping = gateway.get_main_contract_mapping()
                                    for main_symbol, actual_symbol in mapping.items():
                                        if actual_symbol == position_symbol:
                                            main_vt_symbol = f"{main_symbol}.{pos.exchange.value}"
                                            if main_vt_symbol == chart_vt_symbol:
                                                matched = True
                                                break
                                    if matched:
                                        break
                        
                        if matched:
                            # 检查方向是否相反
                            pos_direction = "long" if pos.direction.value == "多" else "short"
                            if pos_direction == opposite_direction:
                                opposite_total_volume = pos.volume
                                opposite_avg_price = pos.price if pos.price > 0 else 0.0
                                break
                
                # 3. 同步PriceLineManager：如果持仓信息显示有反向持仓，但PriceLineManager中没有入场线，先创建
                if opposite_total_volume > 0:
                    all_lines = self._price_line_manager.get_all_lines()
                    opposite_entry_lines = [
                        (lid, line) for lid, line in all_lines.items()
                        if line.get_line_type() == PriceLineType.ENTRY and line.get_direction() == opposite_direction
                    ]
                    
                    # 如果PriceLineManager中没有反向入场线，但持仓信息显示有反向持仓，先创建入场线
                    if not opposite_entry_lines:
                        if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                            self._widget._main_engine.write_log(
                                f"[DrawingOrderController] 同步PriceLineManager: 持仓信息显示有{opposite_direction}持仓{opposite_total_volume}手，但PriceLineManager中没有入场线，先创建",
                                "DrawingOrderController"
                            )
                        # 从持仓信息创建入场线
                        if opposite_avg_price > 0:
                            # 从持仓信息恢复入场线，不传入line_id，让系统自动生成entry_前缀的ID
                            recovered_line_id = self.create_entry_line(
                                price=opposite_avg_price,
                                direction=opposite_direction,
                                line_id=recovered_line_id
                            )
                            # 确保PositionHolding中有记录
                            if not hasattr(self._widget, '_position_holdings'):
                                self._widget._position_holdings = {}
                            if opposite_direction not in self._widget._position_holdings:
                                from .position_holding import PositionHolding
                                self._widget._position_holdings[opposite_direction] = PositionHolding(opposite_direction)
                            opposite_holding = self._widget._position_holdings[opposite_direction]
                            opposite_holding.add_entry(recovered_line_id, opposite_avg_price, opposite_total_volume, None, datetime.now())
                            if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                                self._widget._main_engine.write_log(
                                    f"[DrawingOrderController] 已从持仓信息创建反向入场线: {recovered_line_id}, 价格={opposite_avg_price}, 手数={opposite_total_volume}",
                                    "DrawingOrderController"
                                )
                    
                    # 4. 检查是否为平仓：订单手数 <= 反向持仓手数
                    if order.traded > 0 and order.traded <= opposite_total_volume:
                        is_closing = True
                        if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                            self._widget._main_engine.write_log(
                                f"[DrawingOrderController] 成交后检测到平仓行为: 订单方向={direction}, 订单手数={order.traded}, "
                                f"反向持仓方向={opposite_direction}, 反向持仓手数={opposite_total_volume}, 跳过创建入场线",
                                "DrawingOrderController"
                            )
            
            # 如果是平仓，不创建入场线，只删除挂单线并返回
            if is_closing:
                # 平仓时，删除挂单线关联的止损/止盈线（因为不会创建入场线）
                if pending_relations:
                    # 删除止损线
                    stop_loss_info = pending_relations.get("stop_loss")
                    if stop_loss_info and stop_loss_info.get("line_id"):
                        stop_loss_line_id = stop_loss_info["line_id"]
                        stop_loss_line = self._price_line_manager.get_line(stop_loss_line_id)
                        if stop_loss_line:
                            if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                                self._widget._main_engine.write_log(
                                    f"[DrawingOrderController] 平仓订单，删除挂单线 {line_id} 关联的止损线: {stop_loss_line_id}",
                                    "DrawingOrderController"
                                )
                            # 从 plot 中移除
                            if hasattr(self._widget, '_first_plot') and self._widget._first_plot:
                                try:
                                    self._widget._first_plot.removeItem(stop_loss_line)
                                except Exception:
                                    pass
                            # 从管理器中删除
                            self._price_line_manager.delete_line(stop_loss_line_id)
                    
                    # 删除止盈线
                    take_profit_info = pending_relations.get("take_profit")
                    if take_profit_info and take_profit_info.get("line_id"):
                        take_profit_line_id = take_profit_info["line_id"]
                        take_profit_line = self._price_line_manager.get_line(take_profit_line_id)
                        if take_profit_line:
                            if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                                self._widget._main_engine.write_log(
                                    f"[DrawingOrderController] 平仓订单，删除挂单线 {line_id} 关联的止盈线: {take_profit_line_id}",
                                    "DrawingOrderController"
                                )
                            # 从 plot 中移除
                            if hasattr(self._widget, '_first_plot') and self._widget._first_plot:
                                try:
                                    self._widget._first_plot.removeItem(take_profit_line)
                                except Exception:
                                    pass
                            # 从管理器中删除
                            self._price_line_manager.delete_line(take_profit_line_id)
                    
                    # 清理关联关系
                    self._pending_line_relations.pop(line_id, None)
                    if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                        self._widget._main_engine.write_log(
                            f"[DrawingOrderController] 平仓订单，已清理挂单线 {line_id} 的关联关系（止损/止盈线）",
                            "DrawingOrderController"
                        )
                
                # 清理订单映射
                self._line_order_map.pop(line_id, None)
                self._order_line_map.pop(order.vt_orderid, None)
                # 添加成交标记到K线（平仓也需要显示标记）
                if hasattr(self._widget, '_manager') and order.datetime:
                    direction_str = "long" if order.direction == Direction.LONG else "short"
                    self._add_trade_marker_to_chart(
                        order.datetime, direction_str, order.traded, order.price
                    )
                return True
            
            # ========== 不是平仓，创建入场线并迁移止损/止盈线 ==========
            # 创建入场线
            if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                self._widget._main_engine.write_log(
                    f"[DrawingOrderController] 准备创建入场线: 价格={order.price}，方向={direction}，line_id={line_id}",
                    "DrawingOrderController"
                )
            
            # 创建入场线时，不传入挂单线的ID，让系统自动生成新的UUID
            # 这样可以避免挂单线和入场线ID相同导致的关联关系混乱
            new_line_id = self.create_entry_line(
                price=order.price,
                direction=direction,
                line_id=None  # 不传入挂单线ID，让系统自动生成新的UUID
            )
            
            if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                self._widget._main_engine.write_log(
                    f"[DrawingOrderController] 挂单线 {line_id} 转换为入场线 {new_line_id} (使用新的UUID)",
                    "DrawingOrderController"
                )
            
            if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                self._widget._main_engine.write_log(
                    f"[DrawingOrderController] 已创建入场线 {new_line_id}，价格={order.price}，方向={direction}",
                    "DrawingOrderController"
                )
                # 验证入场线是否在管理器中
                all_lines = self._price_line_manager.get_all_lines()
                entry_lines = [l for l in all_lines.values() if l.get_line_type() == PriceLineType.ENTRY]
                self._widget._main_engine.write_log(
                    f"[DrawingOrderController] 验证: 入场线数量={len(entry_lines)}，总价格线数量={len(all_lines)}，入场线ID列表={[k for k, v in all_lines.items() if v.get_line_type() == PriceLineType.ENTRY]}",
                    "DrawingOrderController"
                )
            
            # 设置订单ID和手数到入场线
            entry_line = self._price_line_manager.get_line(new_line_id)
            if entry_line:
                entry_line.set_vt_orderid(order.vt_orderid)
                # 设置手数（从订单的traded字段获取）
                if order.traded > 0:
                    entry_line.set_volume(order.traded)
                    if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                        self._widget._main_engine.write_log(
                            f"[DrawingOrderController] 已设置入场线 {new_line_id} 的订单ID: {order.vt_orderid}，手数: {order.traded}",
                            "DrawingOrderController"
                        )
                else:
                    if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                        self._widget._main_engine.write_log(
                            f"[DrawingOrderController] 已设置入场线 {new_line_id} 的订单ID: {order.vt_orderid}（手数为0，未设置）",
                            "DrawingOrderController"
                        )
            else:
                if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                    self._widget._main_engine.write_log(
                        f"[DrawingOrderController] 警告: 无法获取入场线 {new_line_id}",
                        "DrawingOrderController"
                    )
            
            # Update mappings
            self._line_order_map[new_line_id] = order.vt_orderid
            self._order_line_map[order.vt_orderid] = new_line_id
            if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                self._widget._main_engine.write_log(
                    f"[DrawingOrderController] 已更新映射: 入场线 {new_line_id} <-> 订单 {order.vt_orderid}",
                    "DrawingOrderController"
                )
            
            # 迁移挂单线的止损/止盈线关联到入场线（在创建入场线之后执行）
            if pending_relations:
                # 确保入场线关联关系字典存在
                if not hasattr(self._widget, '_entry_line_relations'):
                    self._widget._entry_line_relations = {}
                
                if new_line_id not in self._widget._entry_line_relations:
                    self._widget._entry_line_relations[new_line_id] = {}
                
                # 检查入场线是否已有关联关系
                existing_relations = self._widget._entry_line_relations[new_line_id]
                existing_stop_loss = existing_relations.get("stop_loss")
                existing_take_profit = existing_relations.get("take_profit")
                
                if existing_stop_loss or existing_take_profit:
                    if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                        self._widget._main_engine.write_log(
                            f"[DrawingOrderController] 警告：入场线 {new_line_id} 已有关联关系 "
                            f"(止损={existing_stop_loss}, 止盈={existing_take_profit})，"
                            f"将从挂单线 {line_id} 迁移的关联关系将覆盖现有关系",
                            "DrawingOrderController"
                        )
                
                # 迁移止损线关联
                stop_loss_info = pending_relations.get("stop_loss")
                if stop_loss_info and stop_loss_info.get("line_id"):
                    stop_loss_line_id = stop_loss_info["line_id"]
                    stop_loss_line = self._price_line_manager.get_line(stop_loss_line_id)
                    if stop_loss_line:
                        # 如果入场线已有止损线关联，先清理旧的关联关系
                        if existing_stop_loss and existing_stop_loss != stop_loss_line_id:
                            # 删除数据库中的旧关联关系
                            if hasattr(self._widget, '_price_line_database') and self._widget._price_line_database:
                                self._widget._price_line_database.delete_relation(
                                    new_line_id, "stop_loss"
                                )
                            if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                                self._widget._main_engine.write_log(
                                    f"[DrawingOrderController] 已清理入场线 {new_line_id} 的旧止损线关联: {existing_stop_loss}",
                                    "DrawingOrderController"
                                )
                        
                        # 将止损线关联到入场线
                        self._widget._entry_line_relations[new_line_id]["stop_loss"] = stop_loss_line_id
                        
                        # ✅ 激活止损线：设置创建时间，使其可以被触发检查
                        # 挂单成交后，关联的止损线才被激活
                        from time import time
                        stop_loss_line.set_creation_time(time())
                        # 更新label（从"挂单止损"变为"止损"）
                        price_precision = getattr(stop_loss_line, '_price_precision', 0) if hasattr(stop_loss_line, '_price_precision') else 0
                        label_text = stop_loss_line._create_label(stop_loss_line.get_price(), stop_loss_line.get_line_type(), price_precision, stop_loss_line.get_direction())
                        if stop_loss_line.label is not None:
                            stop_loss_line.label.setText(label_text)
                        if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                            self._widget._main_engine.write_log(
                                f"[DrawingOrderController] 已激活止损线 {stop_loss_line_id}（挂单成交后激活）",
                                "DrawingOrderController"
                            )
                        
                        # 从入场线获取手数并设置到止损线
                        entry_line = self._price_line_manager.get_line(new_line_id)
                        if entry_line:
                            entry_volume = entry_line.get_volume()
                            if entry_volume > 0:
                                stop_loss_line.set_volume(entry_volume)
                                if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                                    self._widget._main_engine.write_log(
                                        f"[DrawingOrderController] 已设置止损线 {stop_loss_line_id} 的手数: {entry_volume}（从入场线 {new_line_id} 获取）",
                                        "DrawingOrderController"
                                    )
                            else:
                                # 如果入场线手数为0，尝试从原挂单线获取订单手数
                                pending_line = self._price_line_manager.get_line(line_id)
                                if pending_line:
                                    pending_order_volume = pending_line.get_order_volume()
                                    if pending_order_volume is not None and pending_order_volume > 0:
                                        stop_loss_line.set_volume(pending_order_volume)
                                        if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                                            self._widget._main_engine.write_log(
                                                f"[DrawingOrderController] 已设置止损线 {stop_loss_line_id} 的手数: {pending_order_volume}（从原挂单线 {line_id} 获取）",
                                                "DrawingOrderController"
                                            )
                        
                        # 保存关联关系到数据库
                        if hasattr(self._widget, '_price_line_database') and self._widget._price_line_database:
                            success = self._widget._price_line_database.save_relation(
                                new_line_id, stop_loss_line_id, "stop_loss"
                            )
                            if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                                if success:
                                    self._widget._main_engine.write_log(
                                        f"[DrawingOrderController] 已将挂单线 {line_id} 的止损线 {stop_loss_line_id} 迁移到入场线 {new_line_id}",
                                        "DrawingOrderController"
                                    )
                                else:
                                    self._widget._main_engine.write_log(
                                        f"[DrawingOrderController] 警告：保存止损线关联关系到数据库失败: {new_line_id} -> {stop_loss_line_id}",
                                        "DrawingOrderController"
                                    )
                
                # 迁移止盈线关联
                take_profit_info = pending_relations.get("take_profit")
                if take_profit_info and take_profit_info.get("line_id"):
                    take_profit_line_id = take_profit_info["line_id"]
                    take_profit_line = self._price_line_manager.get_line(take_profit_line_id)
                    if take_profit_line:
                        # 如果入场线已有止盈线关联，先清理旧的关联关系
                        if existing_take_profit and existing_take_profit != take_profit_line_id:
                            # 删除数据库中的旧关联关系
                            if hasattr(self._widget, '_price_line_database') and self._widget._price_line_database:
                                self._widget._price_line_database.delete_relation(
                                    new_line_id, "take_profit"
                                )
                            if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                                self._widget._main_engine.write_log(
                                    f"[DrawingOrderController] 已清理入场线 {new_line_id} 的旧止盈线关联: {existing_take_profit}",
                                    "DrawingOrderController"
                                )
                        
                        # 将止盈线关联到入场线
                        self._widget._entry_line_relations[new_line_id]["take_profit"] = take_profit_line_id
                        
                        # ✅ 激活止盈线：设置创建时间，使其可以被触发检查
                        # 挂单成交后，关联的止盈线才被激活
                        from time import time
                        take_profit_line.set_creation_time(time())
                        # 更新label（从"挂单止盈"变为"止盈"）
                        price_precision = getattr(take_profit_line, '_price_precision', 0) if hasattr(take_profit_line, '_price_precision') else 0
                        label_text = take_profit_line._create_label(take_profit_line.get_price(), take_profit_line.get_line_type(), price_precision, take_profit_line.get_direction())
                        if take_profit_line.label is not None:
                            take_profit_line.label.setText(label_text)
                        if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                            self._widget._main_engine.write_log(
                                f"[DrawingOrderController] 已激活止盈线 {take_profit_line_id}（挂单成交后激活）",
                                "DrawingOrderController"
                            )
                        
                        # 从入场线获取手数并设置到止盈线
                        entry_line = self._price_line_manager.get_line(new_line_id)
                        if entry_line:
                            entry_volume = entry_line.get_volume()
                            if entry_volume > 0:
                                take_profit_line.set_volume(entry_volume)
                                if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                                    self._widget._main_engine.write_log(
                                        f"[DrawingOrderController] 已设置止盈线 {take_profit_line_id} 的手数: {entry_volume}（从入场线 {new_line_id} 获取）",
                                        "DrawingOrderController"
                                    )
                            else:
                                # 如果入场线手数为0，尝试从原挂单线获取订单手数
                                pending_line = self._price_line_manager.get_line(line_id)
                                if pending_line:
                                    pending_order_volume = pending_line.get_order_volume()
                                    if pending_order_volume is not None and pending_order_volume > 0:
                                        take_profit_line.set_volume(pending_order_volume)
                                        if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                                            self._widget._main_engine.write_log(
                                                f"[DrawingOrderController] 已设置止盈线 {take_profit_line_id} 的手数: {pending_order_volume}（从原挂单线 {line_id} 获取）",
                                                "DrawingOrderController"
                                            )
                        
                        # 保存关联关系到数据库
                        if hasattr(self._widget, '_price_line_database') and self._widget._price_line_database:
                            success = self._widget._price_line_database.save_relation(
                                new_line_id, take_profit_line_id, "take_profit"
                            )
                            if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                                if success:
                                    self._widget._main_engine.write_log(
                                        f"[DrawingOrderController] 已将挂单线 {line_id} 的止盈线 {take_profit_line_id} 迁移到入场线 {new_line_id}",
                                        "DrawingOrderController"
                                    )
                                else:
                                    self._widget._main_engine.write_log(
                                        f"[DrawingOrderController] 警告：保存止盈线关联关系到数据库失败: {new_line_id} -> {take_profit_line_id}",
                                        "DrawingOrderController"
                                    )
                
                # 清理挂单线的关联关系（已迁移到入场线）
                # 注意：如果 line_id == new_line_id（挂单线直接转换为入场线，使用相同的ID），
                # 则不应该删除关联关系，因为关联关系已经迁移到入场线了
                if line_id != new_line_id:
                    # 挂单线和入场线ID不同，可以安全地清理挂单线的关联关系
                    # 先清理数据库中的关联关系（如果存在）
                    if hasattr(self._widget, '_price_line_database') and self._widget._price_line_database:
                        self._widget._price_line_database.delete_all_relations(line_id)
                        if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                            self._widget._main_engine.write_log(
                                f"[DrawingOrderController] 已清理挂单线 {line_id} 在数据库中的关联关系",
                                "DrawingOrderController"
                            )
                else:
                    # 挂单线和入场线ID相同，不需要清理数据库关联关系（因为已经迁移到入场线）
                    if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                        self._widget._main_engine.write_log(
                            f"[DrawingOrderController] 挂单线 {line_id} 和入场线 {new_line_id} ID相同，跳过清理数据库关联关系（已迁移）",
                            "DrawingOrderController"
                        )
                
                # 清理内存中的关联关系（无论ID是否相同，都需要清理挂单线的内存关联关系）
                self._pending_line_relations.pop(line_id, None)
                if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                    self._widget._main_engine.write_log(
                        f"[DrawingOrderController] 已清理挂单线 {line_id} 的内存关联关系（已迁移到入场线 {new_line_id}）",
                        "DrawingOrderController"
                    )
            
            # 添加持仓记录到持仓管理系统（用于FIFO平仓和合并显示）
            if hasattr(self._widget, '_position_holdings'):
                from .widget_position_helper import update_position_holding_from_order
                update_position_holding_from_order(
                    self._widget._position_holdings,
                    order,
                    new_line_id
                )
                if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                    holding = self._widget._position_holdings.get(direction)
                    if holding:
                        # 从 entries 计算总手数（用于日志显示）
                        total_volume = sum(e.volume for e in holding.get_all_entries())
                        # 计算加权平均价格（用于日志显示）
                        if total_volume > 0:
                            avg_price = sum(e.price * e.volume for e in holding.get_all_entries()) / total_volume
                        else:
                            avg_price = 0.0
                        self._widget._main_engine.write_log(
                            f"[DrawingOrderController] 已添加持仓记录: 方向={direction}, 总手数={total_volume}, 加权均价={avg_price:.2f}",
                            "DrawingOrderController"
                        )
            
            # 添加成交标记到K线（如果图表有BarManager）
            if hasattr(self._widget, '_manager') and order.datetime:
                direction_str = "long" if order.direction == Direction.LONG else "short"
                self._add_trade_marker_to_chart(
                    order.datetime, direction_str, order.traded, order.price
                )
        else:
            if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                self._widget._main_engine.write_log(
                    f"[DrawingOrderController] 订单 {order.vt_orderid} 状态为 {order.status.value}，未全部成交，不转换挂单线",
                    "DrawingOrderController"
                )

        return True
    
    def _add_trade_marker_to_chart(self, dt, direction_str: str, volume: float, price: float) -> None:
        """在主线程中添加成交标记到K线"""
        if hasattr(self._widget, '_manager') and dt:
            self._widget._manager.add_trade_marker(dt, direction_str, volume, price)
            # 触发K线重绘以显示箭头
            if "candle" in self._widget._items:
                self._widget._items["candle"].update()

    def remove_order_line(self, vt_orderid: str) -> bool:
        """
        Remove price line associated with an order.

        Args:
            vt_orderid: VT order ID

        Returns:
            True if line was removed, False if order not linked
        """
        line_id = self.get_line_id_for_order(vt_orderid)
        if line_id is None:
            return False

        # Remove line
        self._price_line_manager.delete_line(line_id)
        
        # Remove mappings
        self._line_order_map.pop(line_id, None)
        self._order_line_map.pop(vt_orderid, None)

        return True



