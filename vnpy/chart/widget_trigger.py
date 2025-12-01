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
                type=OrderType.OPPONENT,  # 画线下单使用对手价单（与止损止盈一致）
                volume=order_volume,
                price=price,
                offset=offset
            )
            
            # 发送订单（下单前不查询活动订单，保证性能）
            vt_orderid = None
            try:
                vt_orderid = main_engine.send_order(req, contract.gateway_name)
                if vt_orderid:
                    if main_engine:
                        # 记录订单触发成功的详细日志
                        from datetime import datetime
                        current_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        main_engine.write_log(
                            f"[ChartWidget] [实时挂单触发] {current_time} {vt_symbol} {direction.value} "
                            f"{order_volume}手@{price} (挂单线: {line_id}, 订单ID: {vt_orderid}, "
                            f"开平: {offset.value}, 当前价格: {tick.last_price})",
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
            except Exception as e:
                # 记录发送订单时的异常
                if main_engine:
                    main_engine.write_log(
                        f"[ChartWidget] [实时挂单触发失败] 发送订单时发生异常: {vt_symbol} {direction.value} "
                        f"{order_volume}手@{price} (挂单线: {line_id}, 错误: {str(e)}, 当前价格: {tick.last_price})",
                        "ChartWidget"
                    )
                vt_orderid = None
            
            if not vt_orderid:
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
                
                # 构建详细的错误信息
                from datetime import datetime
                current_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                error_msg = f"[ChartWidget] [实时挂单触发失败] {current_time} {vt_symbol} {direction.value} "
                error_msg += f"{order_volume}手@{price} (挂单线: {line_id}, 当前价格: {tick.last_price})"
                
                if opposite_orders:
                    order_info = ", ".join([
                        f"{order.direction.value} {order.volume}@{order.price} (订单ID: {order.vt_orderid}, 状态: {order.status.value})"
                        for order in opposite_orders
                    ])
                    error_msg += f"\n  发现相反方向的未成交订单: {order_info}"
                    error_msg += f"\n  建议: 请先撤销相反方向的未成交订单后重试"
                elif symbol_active_orders:
                    # 虽然没有相反方向的订单，但有其他方向的订单，也记录下来
                    order_info = ", ".join([
                        f"{order.direction.value} {order.volume}@{order.price} (订单ID: {order.vt_orderid}, 状态: {order.status.value})"
                        for order in symbol_active_orders
                    ])
                    error_msg += f"\n  当前合约活动订单: {order_info}"
                else:
                    error_msg += f"\n  可能原因: 账户限制、资金不足、合约限制等原因导致订单被拒绝"
                    error_msg += f"\n  注意: 价格突破已触发，挂单线将不再监控，请手动检查订单状态"
                
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
            # ✅ 防重复触发机制：检查是否已经触发过（防止短时间内重复触发）
            from time import time
            trigger_key = f"stop_loss_{line_id}"
            current_time = time()
            
            # 检查是否已有触发记录（防抖：30秒内不重复触发，但要先检查未成交订单）
            if hasattr(self, '_trigger_records'):
                last_trigger_time = self._trigger_records.get(trigger_key, 0)
                time_since_trigger = current_time - last_trigger_time
                
                # 如果防抖期内，直接跳过
                if time_since_trigger < 3.0:  # 3秒内直接跳过
                    if main_engine:
                        main_engine.write_log(
                            f"[ChartWidget] 触发止损跳过: 止损线 {line_id} 在 {time_since_trigger:.2f} 秒前已触发，防抖保护",
                            "ChartWidget"
                        )
                    return False
            else:
                # 初始化触发记录字典
                self._trigger_records = {}
            
            # ✅ 检查止损线是否已激活：只有已激活的止损线才能触发
            # 挂单线关联的止损线在创建时创建时间为None（未激活），只有在挂单成交后才激活（设置创建时间）
            creation_time = line.get_creation_time()
            if creation_time is None:
                # 止损线未激活（关联挂单线但挂单未成交），跳过触发
                if main_engine:
                    main_engine.write_log(
                        f"[ChartWidget] 触发止损跳过: 止损线 {line_id} 未激活（关联挂单线但挂单未成交），不触发",
                        "ChartWidget"
                    )
                return False
            
            # ✅ 检查创建时间：如果刚激活（<500ms），忽略触发（防止激活后立即触发）
            time_since_creation = current_time - creation_time
            if time_since_creation < 0.5:  # 500ms内忽略触发
                if main_engine:
                    main_engine.write_log(
                        f"[ChartWidget] 触发止损跳过: 止损线 {line_id} 刚激活 {time_since_creation:.3f} 秒前，忽略触发（防误触发）",
                        "ChartWidget"
                    )
                return False
            
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
            
            # ✅ 防重复下单：检查是否已有未成交的平仓订单（支持主力合约映射）
            all_active_orders = main_engine.get_all_active_orders()
            from vnpy.trader.constant import Direction, Offset
            
            # 确定平仓方向（与持仓方向相反）
            if line_direction == "long":
                close_direction = Direction.SHORT  # 平多仓
            else:
                close_direction = Direction.LONG  # 平空仓
            
            # 获取主力合约映射（复用已有缓存机制）
            # _get_main_contract_mapping 返回 main_vt_symbol -> actual_vt_symbol 的映射
            # 例如：{"MHImain.HKFE": "MHI2512.HKFE"}
            main_contract_mapping = {}
            if hasattr(self, '_get_main_contract_mapping'):
                # 复用现有的缓存方法（使用gateway的缓存）
                mapping = self._get_main_contract_mapping(main_engine)
                # 提取actual_symbol（从actual_vt_symbol中提取symbol部分）
                from vnpy.trader.utility import extract_vt_symbol
                for main_vt_symbol_key, actual_vt_symbol in mapping.items():
                    try:
                        actual_symbol, _ = extract_vt_symbol(actual_vt_symbol)
                        main_contract_mapping[main_vt_symbol_key] = actual_symbol
                    except:
                        pass
            
            # 检查是否已有同方向的平仓订单（未成交），支持主力合约映射
            existing_close_orders = []
            for order in all_active_orders:
                if order.direction == close_direction and order.offset == Offset.CLOSE and order.is_active():
                    # 直接匹配
                    if order.vt_symbol == vt_symbol:
                        existing_close_orders.append(order)
                    # 主力合约映射匹配：图表是主力合约，订单是实际合约
                    elif vt_symbol in main_contract_mapping:
                        actual_symbol = main_contract_mapping[vt_symbol]
                        if order.symbol == actual_symbol:
                            # 检查exchange是否匹配
                            from vnpy.trader.utility import extract_vt_symbol
                            try:
                                _, order_exchange = extract_vt_symbol(order.vt_symbol)
                                _, chart_exchange = extract_vt_symbol(vt_symbol)
                                if order_exchange == chart_exchange:
                                    existing_close_orders.append(order)
                            except:
                                pass
            
            if existing_close_orders:
                # 已有未成交的平仓订单，跳过（并更新防抖时间）
                order_info = ", ".join([
                    f"{order.vt_orderid} ({order.status.value})"
                    for order in existing_close_orders
                ])
                if main_engine:
                    main_engine.write_log(
                        f"[ChartWidget] 触发止损跳过: 止损线 {line_id} 已有未成交的平仓订单: {order_info}",
                        "ChartWidget"
                    )
                # 更新防抖时间，防止在订单未成交期间重复检查
                if not hasattr(self, '_trigger_records'):
                    self._trigger_records = {}
                self._trigger_records[trigger_key] = current_time
                return False
            
            # 发送平仓订单（对手价平仓+智能追价）
            from vnpy.trader.object import OrderRequest
            from vnpy.trader.constant import OrderType
            
            # 计算对手价：平多仓用买一价，平空仓用卖一价
            if close_direction == Direction.SHORT:
                # 平多仓：用买一价（对手价）
                opponent_price = tick.bid_price_1 if tick.bid_price_1 > 0 else tick.last_price
            else:
                # 平空仓：用卖一价（对手价）
                opponent_price = tick.ask_price_1 if tick.ask_price_1 > 0 else tick.last_price
            
            # 创建订单请求（对手价订单+智能追价）
            # 使用对手价订单，确保在波动率大的时段也能快速成交
            req = OrderRequest(
                symbol=contract.symbol,
                exchange=contract.exchange,
                direction=close_direction,
                offset=Offset.CLOSE,
                type=OrderType.OPPONENT,  # 对手价订单类型
                price=opponent_price,  # 对手价：买一/卖一
                volume=close_volume,
                reference="OPPONENT_Retry2"  # 启用智能追价（重试2次）
            )
            
            # 发送订单
            try:
                from datetime import datetime
                current_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                
                vt_orderid = main_engine.send_order(req, contract.gateway_name)
                if vt_orderid:
                    # ✅ 记录触发时间，防止重复触发
                    if not hasattr(self, '_trigger_records'):
                        self._trigger_records = {}
                    self._trigger_records[trigger_key] = time()
                    
                    if main_engine:
                        # 记录详细的止损触发成功日志
                        price_precision = getattr(line, '_price_precision', 0) if hasattr(line, '_price_precision') else 0
                        if price_precision == 0:
                            line_price_str = f"{int(line_price)}"
                            current_price_str = f"{int(tick.last_price)}"
                            opponent_price_str = f"{int(opponent_price)}"
                        else:
                            line_price_str = f"{line_price:.{price_precision}f}"
                            current_price_str = f"{tick.last_price:.{price_precision}f}"
                            opponent_price_str = f"{opponent_price:.{price_precision}f}"
                        
                        main_engine.write_log(
                            f"[触发下单] 止损 {vt_symbol} {position_direction} 止损线{line_price_str} → 平仓{close_volume}手 @对手价{opponent_price_str} (当前价{current_price_str}) 订单ID={vt_orderid}",
                            "ChartWidget"
                        )
                    return True
                else:
                    # 订单发送失败（返回None）
                    if main_engine:
                        price_precision = getattr(line, '_price_precision', 0) if hasattr(line, '_price_precision') else 0
                        if price_precision == 0:
                            line_price_str = f"{int(line_price)}"
                            current_price_str = f"{int(tick.last_price)}"
                        else:
                            line_price_str = f"{line_price:.{price_precision}f}"
                            current_price_str = f"{tick.last_price:.{price_precision}f}"
                        
                        error_msg = (
                            f"[ChartWidget] [实时止损触发失败] {current_time} {vt_symbol} {position_direction} "
                            f"止损线 {line_price_str} 触发平仓失败 (当前价格: {current_price_str}, 止损线ID: {line_id})\n"
                            f"  可能原因: 账户限制、资金不足、合约限制等原因导致订单被拒绝\n"
                            f"  注意: 止损条件已触发，请手动检查订单状态或重新设置止损"
                        )
                        main_engine.write_log(error_msg, "ChartWidget")
                    return False
            except Exception as e:
                # 记录发送订单时的异常
                if main_engine:
                    from datetime import datetime
                    current_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    price_precision = getattr(line, '_price_precision', 0) if hasattr(line, '_price_precision') else 0
                    if price_precision == 0:
                        line_price_str = f"{int(line_price)}"
                        current_price_str = f"{int(tick.last_price)}"
                    else:
                        line_price_str = f"{line_price:.{price_precision}f}"
                        current_price_str = f"{tick.last_price:.{price_precision}f}"
                    
                    main_engine.write_log(
                        f"[ChartWidget] [实时止损触发失败] {current_time} {vt_symbol} {position_direction} "
                        f"止损线 {line_price_str} 发送平仓订单时发生异常 (当前价格: {current_price_str}, "
                        f"止损线ID: {line_id}, 错误: {str(e)})",
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
            # ✅ 防重复触发机制：检查是否已经触发过（防止短时间内重复触发）
            from time import time
            trigger_key = f"take_profit_{line_id}"
            current_time = time()
            
            # 检查是否已有触发记录（防抖：30秒内不重复触发，但要先检查未成交订单）
            if hasattr(self, '_trigger_records'):
                last_trigger_time = self._trigger_records.get(trigger_key, 0)
                time_since_trigger = current_time - last_trigger_time
                
                # 如果防抖期内，直接跳过
                if time_since_trigger < 3.0:  # 3秒内直接跳过
                    if main_engine:
                        main_engine.write_log(
                            f"[ChartWidget] 触发止盈跳过: 止盈线 {line_id} 在 {time_since_trigger:.2f} 秒前已触发，防抖保护",
                            "ChartWidget"
                        )
                    return False
            else:
                # 初始化触发记录字典
                self._trigger_records = {}
            
            # ✅ 检查止盈线是否已激活：只有已激活的止盈线才能触发
            # 挂单线关联的止盈线在创建时创建时间为None（未激活），只有在挂单成交后才激活（设置创建时间）
            creation_time = line.get_creation_time()
            if creation_time is None:
                # 止盈线未激活（关联挂单线但挂单未成交），跳过触发
                if main_engine:
                    main_engine.write_log(
                        f"[ChartWidget] 触发止盈跳过: 止盈线 {line_id} 未激活（关联挂单线但挂单未成交），不触发",
                        "ChartWidget"
                    )
                return False
            
            # ✅ 检查创建时间：如果刚激活（<500ms），忽略触发（防止激活后立即触发）
            time_since_creation = current_time - creation_time
            if time_since_creation < 0.5:  # 500ms内忽略触发
                if main_engine:
                    main_engine.write_log(
                        f"[ChartWidget] 触发止盈跳过: 止盈线 {line_id} 刚激活 {time_since_creation:.3f} 秒前，忽略触发（防误触发）",
                        "ChartWidget"
                    )
                return False
            
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
            
            # ✅ 防重复下单：检查是否已有未成交的平仓订单（支持主力合约映射）
            all_active_orders = main_engine.get_all_active_orders()
            from vnpy.trader.constant import Offset
            
            # 确定平仓方向（与持仓方向相反）
            if line_direction == "long":
                close_direction = Direction.SHORT  # 平多仓
            else:
                close_direction = Direction.LONG  # 平空仓
            
            # 获取主力合约映射（复用已有缓存机制）
            # _get_main_contract_mapping 返回 main_vt_symbol -> actual_vt_symbol 的映射
            # 例如：{"MHImain.HKFE": "MHI2512.HKFE"}
            main_contract_mapping = {}
            if hasattr(self, '_get_main_contract_mapping'):
                # 复用现有的缓存方法（使用gateway的缓存）
                mapping = self._get_main_contract_mapping(main_engine)
                # 提取actual_symbol（从actual_vt_symbol中提取symbol部分）
                from vnpy.trader.utility import extract_vt_symbol
                for main_vt_symbol_key, actual_vt_symbol in mapping.items():
                    try:
                        actual_symbol, _ = extract_vt_symbol(actual_vt_symbol)
                        main_contract_mapping[main_vt_symbol_key] = actual_symbol
                    except:
                        pass
            
            # 检查是否已有同方向的平仓订单（未成交），支持主力合约映射
            existing_close_orders = []
            for order in all_active_orders:
                if order.direction == close_direction and order.offset == Offset.CLOSE and order.is_active():
                    # 直接匹配
                    if order.vt_symbol == vt_symbol:
                        existing_close_orders.append(order)
                    # 主力合约映射匹配：图表是主力合约，订单是实际合约
                    elif vt_symbol in main_contract_mapping:
                        actual_symbol = main_contract_mapping[vt_symbol]
                        if order.symbol == actual_symbol:
                            # 检查exchange是否匹配
                            from vnpy.trader.utility import extract_vt_symbol
                            try:
                                _, order_exchange = extract_vt_symbol(order.vt_symbol)
                                _, chart_exchange = extract_vt_symbol(vt_symbol)
                                if order_exchange == chart_exchange:
                                    existing_close_orders.append(order)
                            except:
                                pass
            
            if existing_close_orders:
                # 已有未成交的平仓订单，跳过（并更新防抖时间）
                order_info = ", ".join([
                    f"{order.vt_orderid} ({order.status.value})"
                    for order in existing_close_orders
                ])
                if main_engine:
                    main_engine.write_log(
                        f"[ChartWidget] 触发止盈跳过: 止盈线 {line_id} 已有未成交的平仓订单: {order_info}",
                        "ChartWidget"
                    )
                # 更新防抖时间，防止在订单未成交期间重复检查
                if not hasattr(self, '_trigger_records'):
                    self._trigger_records = {}
                self._trigger_records[trigger_key] = current_time
                return False
            
            # 发送平仓订单（对手价平仓+智能追价）
            from vnpy.trader.object import OrderRequest
            from vnpy.trader.constant import OrderType
            
            # 计算对手价：平多仓用买一价，平空仓用卖一价
            if close_direction == Direction.SHORT:
                # 平多仓：用买一价（对手价）
                opponent_price = tick.bid_price_1 if tick.bid_price_1 > 0 else tick.last_price
            else:
                # 平空仓：用卖一价（对手价）
                opponent_price = tick.ask_price_1 if tick.ask_price_1 > 0 else tick.last_price
            
            # 创建订单请求（对手价订单+智能追价）
            # 使用对手价订单，确保在波动率大的时段也能快速成交
            req = OrderRequest(
                symbol=contract.symbol,
                exchange=contract.exchange,
                direction=close_direction,
                offset=Offset.CLOSE,
                type=OrderType.OPPONENT,  # 对手价订单类型
                price=opponent_price,  # 对手价：买一/卖一
                volume=close_volume,
                reference="OPPONENT_Retry2"  # 启用智能追价（重试2次）
            )
            
            # 发送订单
            try:
                from datetime import datetime
                current_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                
                vt_orderid = main_engine.send_order(req, contract.gateway_name)
                if vt_orderid:
                    # ✅ 记录触发时间，防止重复触发
                    if not hasattr(self, '_trigger_records'):
                        self._trigger_records = {}
                    from time import time
                    self._trigger_records[trigger_key] = time()
                    
                    if main_engine:
                        # 记录详细的止盈触发成功日志
                        price_precision = getattr(line, '_price_precision', 0) if hasattr(line, '_price_precision') else 0
                        if price_precision == 0:
                            line_price_str = f"{int(line_price)}"
                            current_price_str = f"{int(tick.last_price)}"
                            opponent_price_str = f"{int(opponent_price)}"
                        else:
                            line_price_str = f"{line_price:.{price_precision}f}"
                            current_price_str = f"{tick.last_price:.{price_precision}f}"
                            opponent_price_str = f"{opponent_price:.{price_precision}f}"
                        
                        main_engine.write_log(
                            f"[触发下单] 止盈 {vt_symbol} {position_direction} 止盈线{line_price_str} → 平仓{close_volume}手 @对手价{opponent_price_str} (当前价{current_price_str}) 订单ID={vt_orderid}",
                            "ChartWidget"
                        )
                    return True
                else:
                    # 订单发送失败（返回None）
                    if main_engine:
                        price_precision = getattr(line, '_price_precision', 0) if hasattr(line, '_price_precision') else 0
                        if price_precision == 0:
                            line_price_str = f"{int(line_price)}"
                            current_price_str = f"{int(tick.last_price)}"
                        else:
                            line_price_str = f"{line_price:.{price_precision}f}"
                            current_price_str = f"{tick.last_price:.{price_precision}f}"
                        
                        error_msg = (
                            f"[ChartWidget] [实时止盈触发失败] {current_time} {vt_symbol} {position_direction} "
                            f"止盈线 {line_price_str} 触发平仓失败 (当前价格: {current_price_str}, 止盈线ID: {line_id})\n"
                            f"  可能原因: 账户限制、资金不足、合约限制等原因导致订单被拒绝\n"
                            f"  注意: 止盈条件已触发，请手动检查订单状态或重新设置止盈"
                        )
                        main_engine.write_log(error_msg, "ChartWidget")
                    return False
            except Exception as e:
                # 记录发送订单时的异常
                if main_engine:
                    from datetime import datetime
                    current_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    price_precision = getattr(line, '_price_precision', 0) if hasattr(line, '_price_precision') else 0
                    if price_precision == 0:
                        line_price_str = f"{int(line_price)}"
                        current_price_str = f"{int(tick.last_price)}"
                    else:
                        line_price_str = f"{line_price:.{price_precision}f}"
                        current_price_str = f"{tick.last_price:.{price_precision}f}"
                    
                    main_engine.write_log(
                        f"[ChartWidget] [实时止盈触发失败] {current_time} {vt_symbol} {position_direction} "
                        f"止盈线 {line_price_str} 发送平仓订单时发生异常 (当前价格: {current_price_str}, "
                        f"止盈线ID: {line_id}, 错误: {str(e)})",
                        "ChartWidget"
                    )
                return False

