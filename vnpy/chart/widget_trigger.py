"""ChartWidget 触发模块 Mixin

处理价格突破触发下单/平仓等功能。
"""

from typing import TYPE_CHECKING

from vnpy.trader.object import TickData

from .widget_mixin_base import ChartWidgetMixinBase

if TYPE_CHECKING:
    from .price_line import PriceLineItem


class ChartWidgetTriggerMixin(ChartWidgetMixinBase):
    """触发下单/平仓相关功能 Mixin"""
    
    def trigger_pending_order_breakthrough(
        self, 
        line_id: str, 
        line: "PriceLineItem", 
        tick: "TickData"
    ) -> bool:
        """
        触发挂单线突破下单（通用方法，供真实tickdata和模拟触发共用）
        
        Args:
            line_id: 挂单线ID
            line: 挂单线对象
            tick: TickData对象（可以是真实tick或模拟tick）
            
        Returns:
            True if order was sent successfully, False otherwise
        """
        # 使用RLock保护，确保一次只有一个挂单线触发下单
        with self._pending_order_trigger_lock:
            # 从价格线对象获取参数（减少对内存中_pending_order_params的依赖）
            # 优先从价格线对象获取，如果不存在则从内存中的_pending_order_params获取（向后兼容）
            order_volume = line.get_order_volume()
            order_offset_str = line.get_order_offset()
            
            # 如果价格线对象中没有挂单参数，尝试从内存中获取（向后兼容）
            if order_volume is None or order_offset_str is None:
                controller = self.get_drawing_order_controller()
                if controller and hasattr(controller, '_pending_order_params'):
                    if line_id in controller._pending_order_params:
                        order_data = controller._pending_order_params[line_id]
                        params = order_data["params"]
                        if order_volume is None:
                            order_volume = params.get("volume")
                        if order_offset_str is None:
                            order_offset_str = params.get("offset").value if hasattr(params.get("offset"), 'value') else str(params.get("offset"))
                        vt_symbol = order_data.get("vt_symbol", self._vt_symbol)
                        contract = order_data.get("contract")
                    else:
                        # 既没有价格线对象中的参数，也没有内存中的参数
                        return False
                else:
                    # 既没有价格线对象中的参数，也没有内存中的参数
                    return False
            else:
                # 从价格线对象获取参数
                vt_symbol = self._vt_symbol
                if not vt_symbol:
                    return False
                contract = None  # 稍后从main_engine获取
            
            # 从controller或ChartWidget获取main_engine
            controller = self.get_drawing_order_controller()
            main_engine = self._main_engine
            if not main_engine and controller and hasattr(controller, '_main_engine'):
                main_engine = controller._main_engine
            
            if not main_engine:
                # 如果仍然没有main_engine，无法发送订单
                return False
            
            # 获取合约对象（如果还没有）
            if contract is None:
                contract = main_engine.get_contract(vt_symbol)
                if not contract:
                    return False
            
            # 从价格线对象获取其他信息
            price = line.get_price()
            direction_str = line.get_direction()
            
            # 转换为枚举类型
            from vnpy.trader.constant import Direction, Offset
            direction = Direction.LONG if direction_str == "long" else Direction.SHORT
            offset = Offset.OPEN if order_offset_str == "OPEN" else Offset.CLOSE
            
            # ========== 检查是否为平仓操作 ==========
            # 即使 offset 是 OPEN，如果存在反向持仓，也应该视为平仓
            is_closing_order = False
            opposite_direction = Direction.SHORT if direction == Direction.LONG else Direction.LONG
            
            # 1. 优先从 PositionHolding 获取反向持仓（内存操作，极快）
            if hasattr(self, '_position_holdings') and self._position_holdings:
                opposite_direction_str = "long" if opposite_direction == Direction.LONG else "short"
                opposite_holding = self._position_holdings.get(opposite_direction_str)
                if opposite_holding:
                    opposite_total_volume = opposite_holding.get_total_volume()
                    if opposite_total_volume > 0 and order_volume <= opposite_total_volume:
                        is_closing_order = True
                        if main_engine:
                            main_engine.write_log(
                                f"[ChartWidget] 画线下单检测到平仓行为: 订单方向={direction.value}, "
                                f"订单手数={order_volume}, 反向持仓方向={opposite_direction.value}, "
                                f"反向持仓手数={opposite_total_volume}, 标记为平仓订单",
                                "ChartWidget"
                            )
            
            # 2. 如果 PositionHolding 中没有记录，尝试从 main_engine 获取最新持仓信息
            if not is_closing_order:
                all_positions = main_engine.get_all_positions()
                for pos in all_positions:
                    # 检查合约是否匹配（考虑主力合约映射）
                    pos_vt_symbol = pos.vt_symbol
                    if pos_vt_symbol == vt_symbol:
                        # 检查方向是否相反
                        if pos.direction == opposite_direction and pos.volume > 0:
                            if order_volume <= pos.volume:
                                is_closing_order = True
                                if main_engine:
                                    main_engine.write_log(
                                        f"[ChartWidget] 画线下单检测到平仓行为: 订单方向={direction.value}, "
                                        f"订单手数={order_volume}, 反向持仓方向={opposite_direction.value}, "
                                        f"反向持仓手数={pos.volume}, 标记为平仓订单",
                                        "ChartWidget"
                                    )
                                break
                    else:
                        # 尝试主力合约映射
                        if hasattr(main_engine, 'get_all_gateway_names'):
                            for gateway_name in main_engine.get_all_gateway_names():
                                gateway = main_engine.get_gateway(gateway_name)
                                if gateway and hasattr(gateway, 'get_main_contract_mapping'):
                                    mapping = gateway.get_main_contract_mapping()
                                    for main_symbol, actual_symbol in mapping.items():
                                        if actual_symbol == pos.symbol:
                                            main_vt_symbol = f"{main_symbol}.{pos.exchange.value}"
                                            if main_vt_symbol == vt_symbol:
                                                # 检查方向是否相反
                                                if pos.direction == opposite_direction and pos.volume > 0:
                                                    if order_volume <= pos.volume:
                                                        is_closing_order = True
                                                        if main_engine:
                                                            main_engine.write_log(
                                                                f"[ChartWidget] 画线下单检测到平仓行为（主力合约映射）: "
                                                                f"订单方向={direction.value}, 订单手数={order_volume}, "
                                                                f"反向持仓方向={opposite_direction.value}, 反向持仓手数={pos.volume}, "
                                                                f"标记为平仓订单",
                                                                "ChartWidget"
                                                            )
                                                        break
                                    if is_closing_order:
                                        break
                                if is_closing_order:
                                    break
            
            # 标记为平仓订单（用于成交后判断是否创建入场线）
            # 如果是从内存中的_pending_order_params获取的，更新标记
            if is_closing_order:
                if controller and hasattr(controller, '_pending_order_params'):
                    if line_id in controller._pending_order_params:
                        controller._pending_order_params[line_id]["is_closing"] = True
            
            # 创建订单请求
            from vnpy.trader.object import OrderRequest
            from vnpy.trader.constant import OrderType
            from vnpy.trader.utility import extract_vt_symbol
            
            symbol, exchange = extract_vt_symbol(vt_symbol)
            req = OrderRequest(
                symbol=symbol,
                exchange=exchange,
                direction=direction,
                type=OrderType.LIMIT,  # 画线下单使用限价单
                volume=order_volume,
                price=price,
                offset=offset
            )
            
            # 发送订单（下单前不查询活动订单，保证性能）
            vt_orderid = main_engine.send_order(req, contract.gateway_name)
            if vt_orderid:
                if main_engine:
                    main_engine.write_log(
                        f"[ChartWidget] 价格突破触发下单: {vt_symbol} {direction.value} "
                        f"{order_volume}@{price} (订单ID: {vt_orderid})",
                        "ChartWidget"
                    )
                    # 关联订单ID和价格线
                    main_engine.write_log(
                        f"[ChartWidget] 关联挂单线 {line_id} 到订单 {vt_orderid}",
                        "ChartWidget"
                    )
                # 确保controller存在
                if controller:
                    controller.link_line_to_order(line_id, vt_orderid)
                    
                    # 验证关联是否成功
                    linked_line_id = controller.get_line_id_for_order(vt_orderid)
                    if linked_line_id == line_id:
                        if main_engine:
                            main_engine.write_log(
                                f"[ChartWidget] 订单关联验证成功: 订单 {vt_orderid} -> 挂单线 {line_id}",
                                "ChartWidget"
                            )
                    else:
                        if main_engine:
                            main_engine.write_log(
                                f"[ChartWidget] 警告: 订单关联验证失败: 订单 {vt_orderid} -> 挂单线 {linked_line_id} (期望: {line_id})",
                                "ChartWidget"
                            )
                
                # 监听订单成交事件，创建入场线和成交标记
                # 这将在订单成交后通过update_line_from_order处理
            else:
                # 委托失败时才查询当前合约的活动订单，用于诊断问题
                all_active_orders = main_engine.get_all_active_orders()
                # 只查询当前合约的活动订单（性能优化）
                symbol_active_orders = [
                    order for order in all_active_orders
                    if order.vt_symbol == vt_symbol and order.is_active()
                ]
                opposite_orders = [
                    order for order in symbol_active_orders
                    if order.direction == opposite_direction
                ]
                
                # 构建错误信息
                error_msg = f"[ChartWidget] 价格突破触发下单失败: {vt_symbol} {direction.value} "
                error_msg += f"{order_volume}@{price}"
                
                if opposite_orders:
                    order_info = ", ".join([
                        f"{order.direction.value} {order.volume}@{order.price} (订单ID: {order.vt_orderid})"
                        for order in opposite_orders
                    ])
                    error_msg += f"\n  发现相反方向的未成交订单: {order_info}"
                    error_msg += f"\n  建议: 请先撤销相反方向的未成交订单后重试"
                elif symbol_active_orders:
                    # 虽然没有相反方向的订单，但有其他方向的订单，也记录下来
                    order_info = ", ".join([
                        f"{order.direction.value} {order.volume}@{order.price} (订单ID: {order.vt_orderid})"
                        for order in symbol_active_orders
                    ])
                    error_msg += f"\n  当前合约活动订单: {order_info}"
                else:
                    error_msg += f" (可能因账户限制等原因失败，但突破已触发)"
                
                if main_engine:
                    main_engine.write_log(error_msg, "ChartWidget")
            
            # 无论下单成功或失败，都移除内存中的挂单参数并取消注册价格突破监控
            # 因为价格已经突破，不应该再次触发
            # 注意：价格线对象中的挂单参数保留在数据库中，但触发后不再使用
            if controller and hasattr(controller, '_pending_order_params'):
                if line_id in controller._pending_order_params:
                    del controller._pending_order_params[line_id]
            # 取消注册价格突破监控（已触发，无论成功或失败）
            if self._breakthrough_monitor:
                self._breakthrough_monitor.unregister_line(line_id)
            
            return vt_orderid is not None
    
    def trigger_stop_loss_close(self, line_id: str, line: "PriceLineItem", tick: "TickData") -> bool:
        """
        触发止损线平仓（通用方法，供真实tickdata和模拟触发共用）
        
        Args:
            line_id: 止损线ID
            line: 止损线对象
            tick: TickData对象（可以是真实tick或模拟tick）
            
        Returns:
            True if order was sent successfully, False otherwise
        """
        # 从ChartWidget或controller获取main_engine和vt_symbol
        main_engine = self._main_engine
        vt_symbol = self._vt_symbol
        
        # 如果ChartWidget中没有，尝试从controller获取
        if not main_engine or not vt_symbol:
            controller = self.get_drawing_order_controller()
            if controller and hasattr(controller, '_main_engine'):
                main_engine = controller._main_engine
            # vt_symbol可以从tick中获取
            if not vt_symbol and tick:
                vt_symbol = f"{tick.symbol}.{tick.exchange.value}"
        
        if not main_engine or not vt_symbol:
            return False
        
        # 使用RLock保护，确保一次只有一个止损线触发平仓
        with self._stop_loss_trigger_lock:
            line_price = line.get_price()
            line_direction_str = line.get_direction()
            line_volume = line.get_volume()
            
            # 将方向字符串转换为标准格式
            if line_direction_str in ["多", "long", "LONG"]:
                line_direction = "long"
                position_direction = "多"
            elif line_direction_str in ["空", "short", "SHORT"]:
                line_direction = "short"
                position_direction = "空"
            else:
                if main_engine:
                    main_engine.write_log(
                        f"[ChartWidget] 触发止损跳过: 止损线 {line_id} 方向未知: {line_direction_str}",
                        "ChartWidget"
                    )
                return False
            
            # 检查止损线是否应该触发
            # 多仓：价格低于止损线时触发
            # 空仓：价格高于止损线时触发
            should_trigger = False
            if line_direction == "long":
                # 多仓止损：价格低于止损线
                should_trigger = tick.last_price <= line_price
            else:
                # 空仓止损：价格高于止损线
                should_trigger = tick.last_price >= line_price
            
            if not should_trigger:
                return False
            
            # 获取合约信息
            from vnpy.trader.utility import extract_vt_symbol
            symbol, exchange = extract_vt_symbol(vt_symbol)
            contract = main_engine.get_contract(vt_symbol)
            if not contract:
                if main_engine:
                    main_engine.write_log(
                        f"[ChartWidget] 触发止损失败: 合约 {vt_symbol} 未找到",
                        "ChartWidget"
                    )
                return False
            
            # 检查持仓是否存在且大于0
            # 支持主力合约映射：如果图表是主力合约（如MHImain.HKFE），持仓是实际合约（如MHI2512.HKFE）
            from vnpy.trader.constant import Direction
            position_direction_enum = Direction.LONG if line_direction == "long" else Direction.SHORT
            
            # 使用复用方法查找持仓（支持主力合约映射，带缓存）
            position = self._find_position_by_main_contract_mapping(
                main_engine, vt_symbol, position_direction_enum, contract
            )
            
            if not position or position.volume <= 0:
                if main_engine:
                    main_engine.write_log(
                        f"[ChartWidget] 触发止损跳过: 止损线 {line_id} 对应方向 {position_direction} 无持仓或持仓为0",
                        "ChartWidget"
                    )
                return False
            
            # 获取平仓手数（使用止损线的手数，但不超过持仓手数）
            # 如果止损线手数为0，则使用持仓的全部可用手数
            available_volume = position.volume - position.frozen
            if line_volume > 0:
                close_volume = min(line_volume, available_volume)
            else:
                # 止损线手数为0时，使用全部可用持仓
                close_volume = available_volume
            
            if close_volume <= 0:
                if main_engine:
                    main_engine.write_log(
                        f"[ChartWidget] 触发止损跳过: 止损线 {line_id} 可平仓手数为0（持仓={position.volume}, 冻结={position.frozen}, 止损线手数={line_volume}）",
                        "ChartWidget"
                    )
                return False
            
            # 发送平仓订单（对价平仓+智能追价）
            from vnpy.trader.object import OrderRequest
            from vnpy.trader.constant import Offset, OrderType
            
            # 确定平仓方向（与持仓方向相反）
            if line_direction == "long":
                close_direction = Direction.SHORT  # 平多仓
            else:
                close_direction = Direction.LONG  # 平空仓
            
            # 计算对手价：平多仓用买一价，平空仓用卖一价
            if close_direction == Direction.SHORT:
                # 平多仓：用买一价
                opponent_price = tick.bid_price_1 if tick.bid_price_1 > 0 else tick.last_price
            else:
                # 平空仓：用卖一价
                opponent_price = tick.ask_price_1 if tick.ask_price_1 > 0 else tick.last_price
            
            # 创建订单请求（对价+智能追价）
            req = OrderRequest(
                symbol=contract.symbol,
                exchange=contract.exchange,
                direction=close_direction,
                offset=Offset.CLOSE,
                type=OrderType.LIMIT,
                price=opponent_price,
                volume=close_volume,
                reference="OPPONENT_Retry2"  # 启用智能追价（重试2次）
            )
            
            # 发送订单
            try:
                vt_orderid = main_engine.send_order(req, contract.gateway_name)
                if main_engine:
                    main_engine.write_log(
                        f"[ChartWidget] 触发止损成功: {vt_symbol} {position_direction} 止损线 {line_price:.2f} "
                        f"触发平仓 {close_volume}手，订单ID: {vt_orderid}",
                        "ChartWidget"
                    )
                return True
            except Exception as e:
                if main_engine:
                    main_engine.write_log(
                        f"[ChartWidget] 触发止损失败: {vt_symbol} {position_direction} 止损线 {line_price:.2f} "
                        f"发送平仓订单失败: {str(e)}",
                        "ChartWidget"
                    )
                return False
    
    def trigger_take_profit_close(self, line_id: str, line: "PriceLineItem", tick) -> bool:
        """
        触发止盈线平仓（通用方法，供真实tickdata和模拟触发共用）
        
        Args:
            line_id: 止盈线ID
            line: 止盈线对象
            tick: TickData对象（可以是真实tick或模拟tick）
            
        Returns:
            True if order was sent successfully, False otherwise
        """
        # 从ChartWidget或controller获取main_engine和vt_symbol
        main_engine = self._main_engine
        vt_symbol = self._vt_symbol
        
        # 如果ChartWidget中没有，尝试从controller获取
        if not main_engine or not vt_symbol:
            controller = self.get_drawing_order_controller()
            if controller and hasattr(controller, '_main_engine'):
                main_engine = controller._main_engine
            # vt_symbol可以从tick中获取
            if not vt_symbol and tick:
                vt_symbol = f"{tick.symbol}.{tick.exchange.value}"
        
        if not main_engine or not vt_symbol:
            return False
        
        # 使用RLock保护，确保一次只有一个止盈线触发平仓
        with self._take_profit_trigger_lock:
            line_price = line.get_price()
            line_direction_str = line.get_direction()
            line_volume = line.get_volume()
            
            # 将方向字符串转换为标准格式
            if line_direction_str in ["多", "long", "LONG"]:
                line_direction = "long"
                position_direction = "多"
            elif line_direction_str in ["空", "short", "SHORT"]:
                line_direction = "short"
                position_direction = "空"
            else:
                if main_engine:
                    main_engine.write_log(
                        f"[ChartWidget] 触发止盈跳过: 止盈线 {line_id} 方向未知: {line_direction_str}",
                        "ChartWidget"
                    )
                return False
            
            # 检查止盈线是否应该触发
            # 多仓：价格高于止盈线时触发
            # 空仓：价格低于止盈线时触发
            should_trigger = False
            if line_direction == "long":
                # 多仓止盈：价格高于止盈线
                should_trigger = tick.last_price >= line_price
            else:
                # 空仓止盈：价格低于止盈线
                should_trigger = tick.last_price <= line_price
            
            if not should_trigger:
                return False
            
            # 获取合约信息
            from vnpy.trader.utility import extract_vt_symbol
            symbol, exchange = extract_vt_symbol(vt_symbol)
            contract = main_engine.get_contract(vt_symbol)
            if not contract:
                if main_engine:
                    main_engine.write_log(
                        f"[ChartWidget] 触发止盈失败: 合约 {vt_symbol} 未找到",
                        "ChartWidget"
                    )
                return False
            
            # 检查持仓是否存在且大于0
            # 支持主力合约映射：如果图表是主力合约（如MHImain.HKFE），持仓是实际合约（如MHI2512.HKFE）
            from vnpy.trader.constant import Direction
            position_direction_enum = Direction.LONG if line_direction == "long" else Direction.SHORT
            
            # 首先尝试使用图表合约查询持仓
            vt_positionid = f"{contract.gateway_name}.{vt_symbol}.{position_direction_enum.value}"
            position = main_engine.get_position(vt_positionid)
            
            # 如果没找到持仓，尝试通过主力合约映射查找
            if not position or position.volume <= 0:
                # 尝试从gateway获取主力合约映射
                for gateway_name in main_engine.get_all_gateway_names():
                    gateway = main_engine.get_gateway(gateway_name)
                    if gateway and hasattr(gateway, 'get_main_contract_mapping'):
                        mapping = gateway.get_main_contract_mapping()
                        # 检查是否有主力合约映射到实际合约
                        for main_symbol, actual_symbol in mapping.items():
                            main_vt_symbol = f"{main_symbol}.{contract.exchange.value}"
                            if main_vt_symbol == vt_symbol:
                                # 找到匹配的主力合约，使用实际合约查询持仓
                                actual_vt_symbol = f"{actual_symbol}.{contract.exchange.value}"
                                actual_vt_positionid = f"{gateway_name}.{actual_vt_symbol}.{position_direction_enum.value}"
                                position = main_engine.get_position(actual_vt_positionid)
                                if position and position.volume > 0:
                                    if main_engine:
                                        main_engine.write_log(
                                            f"[ChartWidget] 触发止盈: 通过主力合约映射找到持仓 "
                                            f"(图表={vt_symbol}, 实际={actual_vt_symbol})",
                                            "ChartWidget"
                                        )
                                    break
                        if position and position.volume > 0:
                            break
            
            if not position or position.volume <= 0:
                if main_engine:
                    main_engine.write_log(
                        f"[ChartWidget] 触发止盈跳过: 止盈线 {line_id} 对应方向 {position_direction} 无持仓或持仓为0",
                        "ChartWidget"
                    )
                return False
            
            # 获取平仓手数（使用止盈线的手数，但不超过持仓手数）
            # 如果止盈线手数为0，则使用持仓的全部可用手数
            available_volume = position.volume - position.frozen
            if line_volume > 0:
                close_volume = min(line_volume, available_volume)
            else:
                # 止盈线手数为0时，使用全部可用持仓
                close_volume = available_volume
            
            if close_volume <= 0:
                if main_engine:
                    main_engine.write_log(
                        f"[ChartWidget] 触发止盈跳过: 止盈线 {line_id} 可平仓手数为0（持仓={position.volume}, 冻结={position.frozen}, 止盈线手数={line_volume}）",
                        "ChartWidget"
                    )
                return False
            
            # 发送平仓订单（对价平仓+智能追价）
            from vnpy.trader.object import OrderRequest
            from vnpy.trader.constant import Offset, OrderType
            
            # 确定平仓方向（与持仓方向相反）
            if line_direction == "long":
                close_direction = Direction.SHORT  # 平多仓
            else:
                close_direction = Direction.LONG  # 平空仓
            
            # 计算对手价：平多仓用买一价，平空仓用卖一价
            if close_direction == Direction.SHORT:
                # 平多仓：用买一价
                opponent_price = tick.bid_price_1 if tick.bid_price_1 > 0 else tick.last_price
            else:
                # 平空仓：用卖一价
                opponent_price = tick.ask_price_1 if tick.ask_price_1 > 0 else tick.last_price
            
            # 创建订单请求（对价+智能追价）
            req = OrderRequest(
                symbol=contract.symbol,
                exchange=contract.exchange,
                direction=close_direction,
                offset=Offset.CLOSE,
                type=OrderType.LIMIT,
                price=opponent_price,
                volume=close_volume,
                reference="OPPONENT_Retry2"  # 启用智能追价（重试2次）
            )
            
            # 发送订单
            try:
                vt_orderid = self._main_engine.send_order(req, contract.gateway_name)
                if self._main_engine:
                    self._main_engine.write_log(
                        f"[ChartWidget] 触发止盈成功: {self._vt_symbol} {position_direction} 止盈线 {line_price:.2f} "
                        f"触发平仓 {close_volume}手，订单ID: {vt_orderid}",
                        "ChartWidget"
                    )
                return True
            except Exception as e:
                if self._main_engine:
                    self._main_engine.write_log(
                        f"[ChartWidget] 触发止盈失败: {self._vt_symbol} {position_direction} 止盈线 {line_price:.2f} "
                        f"发送平仓订单失败: {str(e)}",
                        "ChartWidget"
                    )
                return False

