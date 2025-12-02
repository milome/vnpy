"""ChartWidget 订单处理 Mixin

处理订单更新、创建入场线等功能。
"""

from time import time
from typing import TYPE_CHECKING

from vnpy.trader.object import OrderData
from vnpy.trader.event import EVENT_ORDER
from vnpy.event import Event

from .widget_mixin_base import ChartWidgetMixinBase

if TYPE_CHECKING:
    pass


class ChartWidgetOrderMixin(ChartWidgetMixinBase):
    """订单处理相关功能 Mixin"""
    
    def _on_order_update(self, event: Event) -> None:
        """处理订单更新事件，订单成交后创建入场线（确保在主线程中执行）"""
        order: OrderData = event.data
        
        # ✅ 性能优化：订单更新事件去重检查
        order_key = f"{order.vt_orderid}_{order.status.value}"
        current_time = time()
        
        # 检查是否已处理过（在TTL内）
        from vnpy.trader.constant import Status
        is_duplicate = False
        if order_key in self._processed_order_updates:
            last_time = self._processed_order_updates[order_key]
            if current_time - last_time < self._order_update_dedup_ttl:
                is_duplicate = True
                # 对于"全部成交"状态，即使去重已标记，也要继续处理以确保挂单线被删除
                if order.status == Status.ALLTRADED:
                    # 注释重复处理日志，减少日志输出
                    # if hasattr(self, '_main_engine') and self._main_engine:
                    #     self._main_engine.write_log(
                    #         f"[ChartWidget] 订单更新事件已处理，但ALLTRADED状态需要强制处理以确保挂单线被删除: {order.vt_orderid}",
                    #         "ChartWidget"
                    #     )
                    # 继续处理，不return
                    pass
                else:
                    # 已处理过，跳过（非ALLTRADED状态）
                    # 注释重复处理日志，减少日志输出
                    # if hasattr(self, '_main_engine') and self._main_engine:
                    #     self._main_engine.write_log(
                    #         f"[ChartWidget] 订单更新事件已处理，跳过重复处理: {order.vt_orderid} status={order.status.value}",
                    #         "ChartWidget"
                    #     )
                    return
        
        # 标记为已处理
        self._processed_order_updates[order_key] = current_time
        
        # 清理过期的去重记录（保留最近100条）
        if len(self._processed_order_updates) > 100:
            # 删除最旧的记录
            sorted_items = sorted(self._processed_order_updates.items(), key=lambda x: x[1])
            for old_key, _ in sorted_items[:-100]:
                self._processed_order_updates.pop(old_key, None)
        
        # 注释详细日志，减少日志输出
        # if hasattr(self, '_main_engine') and self._main_engine:
        #     self._main_engine.write_log(
        #         f"[ChartWidget] 收到订单更新事件: {order.vt_symbol} {order.direction.value if order.direction else 'N/A'} "
        #         f"status={order.status.value} orderid={order.orderid} vt_orderid={order.vt_orderid}",
        #         "ChartWidget"
        #     )
            # 检查订单状态
            from vnpy.trader.constant import Status, Offset
            if order.status == Status.ALLTRADED:
                # 检查是否为平仓订单，如果是平仓则不会转换为入场线
                # 方法1: 直接检查 order.offset
                is_close_order = (hasattr(order, 'offset') and 
                                 order.offset in (Offset.CLOSE, Offset.CLOSETODAY, Offset.CLOSEYESTERDAY))
                
                # 方法2: 如果 offset 为 NONE，尝试通过订单方向与持仓方向判断（作为备用检查）
                # 注意：这个方法在 update_line_from_order 中已经有更完善的实现，这里只是用于日志
                if not is_close_order and hasattr(self, '_drawing_order_controller') and self._drawing_order_controller:
                    # 简单检查：如果订单未关联挂单线，很可能是平仓订单（通过止损/止盈触发）
                    # 但这里不进行复杂判断，只记录日志，实际判断在 update_line_from_order 中进行
                    pass
                
                # 注释订单成交状态日志，减少日志输出
                # if is_close_order:
                #     self._main_engine.write_log(
                #         f"[ChartWidget] 订单 {order.vt_orderid} 状态为全部成交（平仓订单，不会转换为入场线）",
                #         "ChartWidget"
                #     )
                # else:
                #     self._main_engine.write_log(
                #         f"[ChartWidget] 订单 {order.vt_orderid} 状态为全部成交，准备检查是否转换为入场线",
                #         "ChartWidget"
                #     )
                pass
        
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
                                    # 注释主力合约映射匹配日志，减少日志输出
                                    # if hasattr(self, '_main_engine') and self._main_engine:
                                    #     self._main_engine.write_log(
                                    #         f"[ChartWidget] 订单主力合约映射匹配: 图表={chart_vt_symbol}, 订单={order_vt_symbol} (通过映射 {main_symbol}->{actual_symbol})",
                                    #         "ChartWidget"
                                    #     )
                                    break
                        if matched:
                            break
            
            if not matched:
                # 注释合约不匹配日志，减少日志输出
                # if hasattr(self, '_main_engine') and self._main_engine:
                #     self._main_engine.write_log(
                #         f"[ChartWidget] 订单更新事件合约不匹配: 图表={chart_vt_symbol}, 订单={order_vt_symbol}",
                #         "ChartWidget"
                #     )
                return
        
        # 如果没有drawing_order_controller，不需要更新
        if not self._drawing_order_controller:
            # 注释未初始化日志，减少日志输出
            # if hasattr(self, '_main_engine') and self._main_engine:
            #     self._main_engine.write_log(
            #         f"[ChartWidget] 订单更新事件: drawing_order_controller未初始化",
            #         "ChartWidget"
            #     )
            return
        
        # 注释查询挂单线关联日志，减少日志输出
        # if hasattr(self, '_main_engine') and self._main_engine:
        #     line_id = self._drawing_order_controller.get_line_id_for_order(order.vt_orderid)
        #     self._main_engine.write_log(
        #         f"[ChartWidget] 订单 {order.vt_orderid} 关联的挂单线: {line_id}",
        #         "ChartWidget"
        #     )
        
        # 使用信号槽机制确保在主线程中执行，避免线程问题
        from vnpy.trader.ui import QtCore
        # 注释准备调用日志，减少日志输出
        # if hasattr(self, '_main_engine') and self._main_engine:
        #     self._main_engine.write_log(
        #         f"[ChartWidget] 准备调用 update_line_from_order 更新挂单线",
        #         "ChartWidget"
        #     )
        
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
            # 注释调度日志，减少日志输出
            # if hasattr(self, '_main_engine') and self._main_engine:
            #     self._main_engine.write_log(
            #         f"[ChartWidget] 不在主线程，使用信号槽调度 _process_order_update",
            #         "ChartWidget"
            #     )
            self._signal_order_update.emit(order)
    
    def _process_order_update(self, order: OrderData) -> None:
        """在主线程中处理订单更新"""
        from vnpy.trader.constant import Status
        
        # ✅ 性能优化：再次检查去重（防止信号槽多次触发）
        order_key = f"{order.vt_orderid}_{order.status.value}"
        current_time = time()
        
        # 检查是否已处理过（在TTL内）
        is_duplicate = False
        if order_key in self._processed_order_updates:
            last_time = self._processed_order_updates[order_key]
            if current_time - last_time < self._order_update_dedup_ttl:
                is_duplicate = True
                # 对于"全部成交"状态，即使去重已标记，也要确保挂单线、入场线及关联的止损/止盈线被删除
                if order.status == Status.ALLTRADED:
                    if self._drawing_order_controller and self._price_line_manager:
                        line_id = self._drawing_order_controller.get_line_id_for_order(order.vt_orderid)
                        if line_id:
                            from .price_line import PriceLineType
                            line = self._price_line_manager.get_line(line_id)
                            if line:
                                line_type = line.get_line_type()
                                
                                # 检查挂单线是否还存在
                                if line_type == PriceLineType.PENDING:
                                    # 挂单线仍然存在，需要删除（可能是之前的处理没有成功）
                                    # 但需要先判断是否为平仓操作，以决定止损/止盈线的处理方式
                                    if hasattr(self, '_main_engine') and self._main_engine:
                                        self._main_engine.write_log(
                                            f"[ChartWidget] 检测到重复的订单更新事件，但挂单线 {line_id} 仍然存在，需要判断是否为平仓操作",
                                            "ChartWidget"
                                        )
                                    
                                    # 判断是否为平仓操作（使用与 update_line_from_order 相同的逻辑）
                                    from vnpy.trader.constant import Direction
                                    direction = "long" if order.direction == Direction.LONG else "short"
                                    opposite_direction = "short" if direction == "long" else "long"
                                    
                                    is_closing = False
                                    # 1. 检查下单时是否已标记为平仓订单
                                    if hasattr(self._drawing_order_controller, '_pending_order_params') and line_id in self._drawing_order_controller._pending_order_params:
                                        order_data = self._drawing_order_controller._pending_order_params.get(line_id)
                                        if order_data and order_data.get("is_closing", False):
                                            is_closing = True
                                    
                                    # 2. 如果未标记，检查反向持仓手数
                                    if not is_closing:
                                        opposite_total_volume = 0.0
                                        if hasattr(self, '_position_holdings'):
                                            opposite_holding = self._position_holdings.get(opposite_direction)
                                            if opposite_holding:
                                                opposite_total_volume = sum(e.volume for e in opposite_holding.get_all_entries())
                                        
                                        # 如果PositionHolding中没有记录，尝试从main_engine获取
                                        if opposite_total_volume == 0 and hasattr(self, '_main_engine') and self._main_engine:
                                            all_positions = self._main_engine.get_all_positions()
                                            for pos in all_positions:
                                                # 检查合约是否匹配（考虑主力合约映射）
                                                pos_vt_symbol = pos.vt_symbol
                                                chart_vt_symbol = self._vt_symbol
                                                
                                                matched = False
                                                if chart_vt_symbol and pos_vt_symbol == chart_vt_symbol:
                                                    matched = True
                                                elif chart_vt_symbol:
                                                    position_symbol = pos.symbol
                                                    chart_symbol = chart_vt_symbol.split('.')[0] if '.' in chart_vt_symbol else chart_vt_symbol
                                                    for gateway_name in self._main_engine.get_all_gateway_names():
                                                        gateway = self._main_engine.get_gateway(gateway_name)
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
                                    
                                    # 根据是否为平仓，决定止损/止盈线的处理方式
                                    if is_closing:
                                        # 平仓操作：删除挂单线关联的止损/止盈线
                                        if hasattr(self._drawing_order_controller, '_pending_line_relations') and line_id in self._drawing_order_controller._pending_line_relations:
                                            relations = self._drawing_order_controller._pending_line_relations[line_id]
                                            
                                            # 删除止损线
                                            stop_loss_info = relations.get("stop_loss")
                                            if stop_loss_info and stop_loss_info.get("line_id"):
                                                stop_loss_line_id = stop_loss_info["line_id"]
                                                stop_loss_line = self._price_line_manager.get_line(stop_loss_line_id)
                                                if stop_loss_line:
                                                    if hasattr(self, '_main_engine') and self._main_engine:
                                                        self._main_engine.write_log(
                                                            f"[ChartWidget] 平仓订单，删除挂单线 {line_id} 关联的止损线: {stop_loss_line_id}",
                                                            "ChartWidget"
                                                        )
                                                    # 从 plot 中移除
                                                    if self._first_plot:
                                                        try:
                                                            self._first_plot.removeItem(stop_loss_line)
                                                        except Exception:
                                                            pass
                                                    # 从管理器中删除
                                                    self._price_line_manager.delete_line(stop_loss_line_id)
                                            
                                            # 删除止盈线
                                            take_profit_info = relations.get("take_profit")
                                            if take_profit_info and take_profit_info.get("line_id"):
                                                take_profit_line_id = take_profit_info["line_id"]
                                                take_profit_line = self._price_line_manager.get_line(take_profit_line_id)
                                                if take_profit_line:
                                                    if hasattr(self, '_main_engine') and self._main_engine:
                                                        self._main_engine.write_log(
                                                            f"[ChartWidget] 平仓订单，删除挂单线 {line_id} 关联的止盈线: {take_profit_line_id}",
                                                            "ChartWidget"
                                                        )
                                                    # 从 plot 中移除
                                                    if self._first_plot:
                                                        try:
                                                            self._first_plot.removeItem(take_profit_line)
                                                        except Exception:
                                                            pass
                                                    # 从管理器中删除
                                                    self._price_line_manager.delete_line(take_profit_line_id)
                                            
                                            # 清理关联关系
                                            self._drawing_order_controller._pending_line_relations.pop(line_id, None)
                                        
                                        # 删除挂单线
                                        if self._first_plot:
                                            try:
                                                self._first_plot.removeItem(line)
                                            except Exception:
                                                pass
                                        self._price_line_manager.delete_line(line_id)
                                        # 清理订单映射
                                        if hasattr(self._drawing_order_controller, '_line_order_map'):
                                            self._drawing_order_controller._line_order_map.pop(line_id, None)
                                        if hasattr(self._drawing_order_controller, '_order_line_map'):
                                            self._drawing_order_controller._order_line_map.pop(order.vt_orderid, None)
                                        
                                        if hasattr(self, '_main_engine') and self._main_engine:
                                            self._main_engine.write_log(
                                                f"[ChartWidget] 平仓订单，已删除挂单线 {line_id} 及其关联的止损/止盈线",
                                                "ChartWidget"
                                            )
                                        return
                                    else:
                                        # 非平仓操作：不应该在这里直接删除止损/止盈线
                                        # 应该继续处理，让 update_line_from_order 方法正确处理（创建入场线并迁移止损/止盈线）
                                        if hasattr(self, '_main_engine') and self._main_engine:
                                            self._main_engine.write_log(
                                                f"[ChartWidget] 非平仓订单，挂单线 {line_id} 仍然存在，继续处理以创建入场线并迁移止损/止盈线",
                                                "ChartWidget"
                                            )
                                        # 继续处理，不return，确保调用 update_line_from_order
                                
                                # 检查入场线是否还存在，以及是否有关联的止损/止盈线
                                elif line_type == PriceLineType.ENTRY:
                                    # 入场线仍然存在，检查是否有关联的止损/止盈线需要删除
                                    if hasattr(self, '_entry_line_relations') and line_id in self._entry_line_relations:
                                        relations = self._entry_line_relations[line_id]
                                        
                                        # 删除止损线
                                        stop_loss_line_id = relations.get("stop_loss")
                                        if stop_loss_line_id:
                                            stop_loss_line = self._price_line_manager.get_line(stop_loss_line_id)
                                            if stop_loss_line:
                                                if hasattr(self, '_main_engine') and self._main_engine:
                                                    self._main_engine.write_log(
                                                        f"[ChartWidget] 检测到重复的订单更新事件，但止损线 {stop_loss_line_id} 仍然存在，强制删除",
                                                        "ChartWidget"
                                                    )
                                                # 从 plot 中移除
                                                if self._first_plot:
                                                    try:
                                                        self._first_plot.removeItem(stop_loss_line)
                                                    except Exception:
                                                        pass
                                                # 从管理器中删除
                                                self._price_line_manager.delete_line(stop_loss_line_id)
                                        
                                        # 删除止盈线
                                        take_profit_line_id = relations.get("take_profit")
                                        if take_profit_line_id:
                                            take_profit_line = self._price_line_manager.get_line(take_profit_line_id)
                                            if take_profit_line:
                                                if hasattr(self, '_main_engine') and self._main_engine:
                                                    self._main_engine.write_log(
                                                        f"[ChartWidget] 检测到重复的订单更新事件，但止盈线 {take_profit_line_id} 仍然存在，强制删除",
                                                        "ChartWidget"
                                                    )
                                                # 从 plot 中移除
                                                if self._first_plot:
                                                    try:
                                                        self._first_plot.removeItem(take_profit_line)
                                                    except Exception:
                                                        pass
                                                # 从管理器中删除
                                                self._price_line_manager.delete_line(take_profit_line_id)
                                        
                                        # 清理关联关系
                                        self._entry_line_relations.pop(line_id, None)
                                        
                                        # 从数据库删除关联关系
                                        if self._price_line_database:
                                            self._price_line_database.delete_relation(line_id)
                                        
                                        if hasattr(self, '_main_engine') and self._main_engine:
                                            self._main_engine.write_log(
                                                f"[ChartWidget] 已清理入场线 {line_id} 的关联关系（止损/止盈线）",
                                                "ChartWidget"
                                            )
                                    
                                    # 删除入场线本身
                                    if hasattr(self, '_main_engine') and self._main_engine:
                                        self._main_engine.write_log(
                                            f"[ChartWidget] 检测到重复的订单更新事件，但入场线 {line_id} 仍然存在，强制删除",
                                            "ChartWidget"
                                        )
                                    # 从 plot 中移除
                                    if self._first_plot:
                                        try:
                                            self._first_plot.removeItem(line)
                                        except Exception:
                                            pass
                                    # 从管理器中删除
                                    self._price_line_manager.delete_line(line_id)
                                    # 清理订单映射
                                    if hasattr(self._drawing_order_controller, '_line_order_map'):
                                        self._drawing_order_controller._line_order_map.pop(line_id, None)
                                    if hasattr(self._drawing_order_controller, '_order_line_map'):
                                        self._drawing_order_controller._order_line_map.pop(order.vt_orderid, None)
                                    return
                
                # 对于ALLTRADED状态，即使去重已标记，也要继续处理以确保挂单线被删除和入场线被创建
                if order.status == Status.ALLTRADED:
                    # 注释重复处理日志，减少日志输出
                    # if hasattr(self, '_main_engine') and self._main_engine:
                    #     self._main_engine.write_log(
                    #         f"[ChartWidget] _process_order_update: 订单更新事件已处理，但ALLTRADED状态需要继续处理: {order.vt_orderid}",
                    #         "ChartWidget"
                    #     )
                    # 继续处理，不return，确保调用 update_line_from_order
                    pass
                else:
                    # 已处理过，跳过（非ALLTRADED状态）
                    # 注释重复处理日志，减少日志输出
                    # if hasattr(self, '_main_engine') and self._main_engine:
                    #     self._main_engine.write_log(
                    #         f"[ChartWidget] _process_order_update: 订单更新事件已处理，跳过重复处理: {order.vt_orderid} status={order.status.value}",
                    #         "ChartWidget"
                    #     )
                    return
        
        # 标记为已处理
        self._processed_order_updates[order_key] = current_time
        
        # 注释开始处理订单更新日志，减少日志输出
        # if hasattr(self, '_main_engine') and self._main_engine:
        #     self._main_engine.write_log(
        #         f"[ChartWidget] 开始处理订单更新: {order.vt_orderid} status={order.status.value}",
        #         "ChartWidget"
        #     )
        if self._drawing_order_controller:
            result = self._drawing_order_controller.update_line_from_order(order)
            # 注释返回结果日志，减少日志输出
            # if hasattr(self, '_main_engine') and self._main_engine:
            #     self._main_engine.write_log(
            #         f"[ChartWidget] update_line_from_order 返回结果: {result}",
            #         "ChartWidget"
            #     )

