"""ChartWidget 持仓管理 Mixin

处理持仓更新、入场线盈亏计算等功能。
"""

from datetime import datetime
from typing import TYPE_CHECKING

from vnpy.trader.object import PositionData
from vnpy.trader.event import EVENT_POSITION, EVENT_POSITION_VIEW, EVENT_ORDER
from vnpy.event import Event

from .widget_mixin_base import ChartWidgetMixinBase
from .position_holding import PositionHolding
from .price_line import PriceLineType
from .widget_position_helper import (
    add_entry_to_holding,
    process_position_close
)

if TYPE_CHECKING:
    from .price_line import PriceLineItem


class ChartWidgetPositionMixin(ChartWidgetMixinBase):
    """持仓管理相关功能 Mixin"""
    
    def _register_position_events(self) -> None:
        """注册持仓更新事件，用于更新入场线的浮动盈亏"""
        if not self._event_engine:
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[持仓同步] 无法注册事件：_event_engine为None",
                    "Chart"
                )
            return
        
        # 监听持仓视图事件（包含浮动盈亏信息）
        self._event_engine.register(EVENT_POSITION_VIEW, self._on_position_update)
        # 也监听传统持仓事件（兼容性）
        self._event_engine.register(EVENT_POSITION, self._on_position_update)
        # 监听订单事件，用于更新价格线（订单成交后创建入场线）
        # 注意：_on_order_update 在 Phase 3 中实现，这里检查是否存在
        if hasattr(self, '_on_order_update'):
            self._event_engine.register(EVENT_ORDER, self._on_order_update)
            registered_events = "EVENT_POSITION_VIEW, EVENT_POSITION, EVENT_ORDER"
        else:
            registered_events = "EVENT_POSITION_VIEW, EVENT_POSITION"
        
        if hasattr(self, '_main_engine') and self._main_engine:
            self._main_engine.write_log(
                f"[持仓同步] 已注册事件监听: {registered_events}",
                "Chart"
            )
    
    def _on_position_update(self, event: Event) -> None:
        """处理持仓更新事件，更新入场线的浮动盈亏显示"""
        position: PositionData = event.data
        
        # 注释持仓更新事件接收日志，减少日志输出
        # if hasattr(self, '_main_engine') and self._main_engine:
        #     available_volume = position.volume - position.frozen
        #     self._main_engine.write_log(
        #         f"[持仓同步] 收到持仓更新事件: {position.vt_symbol} {position.direction.value} "
        #         f"volume={position.volume} frozen={position.frozen} available={available_volume} pnl={position.pnl}",
        #         "ChartWidget"
        #     )
        
        # 处理主力合约映射：如果图表是主力合约（如MHImain.HKFE），持仓是实际合约（如MHI2512.HKFE）
        # 需要检查持仓是否对应图表的主力合约
        position_vt_symbol = position.vt_symbol
        chart_vt_symbol = self._vt_symbol
        
        # 注释合约匹配检查日志，减少日志输出
        # if hasattr(self, '_main_engine') and self._main_engine:
        #     self._main_engine.write_log(
        #         f"[持仓同步] 合约匹配检查: 图表合约={chart_vt_symbol}, 持仓合约={position_vt_symbol}",
        #         "ChartWidget"
        #     )
        
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
                                    # 注释主力合约映射匹配日志，减少日志输出
                                    # if hasattr(self, '_main_engine') and self._main_engine:
                                    #     self._main_engine.write_log(
                                    #         f"[持仓同步] 主力合约映射匹配: 图表={chart_vt_symbol}, 持仓={position_vt_symbol} (通过映射 {main_symbol}->{actual_symbol})",
                                    #         "ChartWidget"
                                    #     )
                                    break
                        if matched:
                            break
            
            if not matched:
                if hasattr(self, '_main_engine') and self._main_engine:
                    self._main_engine.write_log(
                        f"[持仓同步] 持仓更新事件合约不匹配: 图表={chart_vt_symbol}, 持仓={position_vt_symbol}",
                        "Chart"
                    )
                return
        
        # 如果没有入场线，不需要更新
        if not self._drawing_order_controller:
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[持仓同步] 持仓更新事件: drawing_order_controller未初始化",
                    "Chart"
                )
            return
        
        # 如果持仓全部冻结（可用持仓为0），不显示盈亏，但保留入场线
        # 这种情况通常发生在休市时间，模拟交易平仓后，API返回的是冻结持仓而不是0持仓
        # 但持仓可能会解冻，所以不应该清除入场线
        # 只有当持仓数量为0时，才清除入场线
        if position.volume > 0 and position.volume == position.frozen:
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[持仓同步] 持仓全部冻结（可用=0），不更新盈亏但保留入场线: {position.vt_symbol} {position.direction.value}",
                    "Chart"
                )
            # 不更新盈亏，但保留入场线，等待持仓解冻
            # 直接返回，不调用 _update_entry_line_pnl
            return
        
        # 使用信号槽机制确保在主线程中执行
        from vnpy.trader.ui import QtCore
        
        # 注释调度准备日志，减少日志输出
        # if hasattr(self, '_main_engine') and self._main_engine:
        #     self._main_engine.write_log(
        #         f"[持仓同步] 准备更新入场线盈亏: 图表合约={chart_vt_symbol}, 持仓合约={position.vt_symbol}, "
        #         f"方向={position.direction.value}, volume={position.volume}, pnl={position.pnl}",
        #         "ChartWidget"
        #     )
        
        # 直接检查是否在主线程，如果是则直接调用，否则使用信号槽
        app = QtCore.QCoreApplication.instance()
        if app and QtCore.QThread.currentThread() == app.thread():
            # 已经在主线程，直接调用
            # 注释主线程调用日志，减少日志输出
            # if hasattr(self, '_main_engine') and self._main_engine:
            #     self._main_engine.write_log(
            #         f"[持仓同步] 已在主线程，直接调用 _update_entry_line_pnl",
            #         "ChartWidget"
            #     )
            self._update_entry_line_pnl(position)
        else:
            # 不在主线程，使用信号槽调度到主线程
            # 注释信号槽调度日志，减少日志输出
            # if hasattr(self, '_main_engine') and self._main_engine:
            #     self._main_engine.write_log(
            #         f"[持仓同步] 不在主线程，使用信号槽调度到主线程",
            #         "ChartWidget"
            #     )
            self._signal_position_update.emit(position)
    
    def _clear_frozen_position_lines(self, position: PositionData) -> None:
        """清除冻结持仓对应的入场线及其关联的止损止盈线"""
        position_direction = "long" if position.direction.value == "多" else "short"
        all_lines = self._price_line_manager.get_all_lines()
        
        if hasattr(self, '_main_engine') and self._main_engine:
            self._main_engine.write_log(
                f"[持仓同步] 清除冻结持仓的入场线: {position.vt_symbol} {position.direction.value} "
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
                        f"[持仓同步] 标记删除冻结持仓的入场线: {line_id} (方向={line_direction})",
                        "Chart"
                    )
        
        # 删除所有标记的线及其关联的止损止盈线
        deleted_count = 0
        for line_id in list(lines_to_delete):
            line = self._price_line_manager.get_line(line_id)
            if line and self._price_line_manager.delete_line(line_id):
                deleted_count += 1
                if hasattr(self, '_main_engine') and self._main_engine:
                    self._main_engine.write_log(
                        f"[持仓同步] 已删除冻结持仓的入场线: {line_id}",
                        "Chart"
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
                                                f"[持仓同步] 已删除关联止损线: {stop_loss_info['line_id']}",
                                                "Chart"
                                            )
                                take_profit_info = relations.get("take_profit")
                                if take_profit_info and take_profit_info.get("line_id"):
                                    if self._price_line_manager.delete_line(take_profit_info["line_id"]):
                                        deleted_count += 1
                                        if hasattr(self, '_main_engine') and self._main_engine:
                                            self._main_engine.write_log(
                                                f"[持仓同步] 已删除关联止盈线: {take_profit_info['line_id']}",
                                                "Chart"
                                            )
                                # 清理该挂单线的关联关系
                                self._drawing_order_controller._pending_line_relations.pop(pending_line_id, None)
                                break  # 找到并处理了，退出内层循环
        
        if hasattr(self, '_main_engine') and self._main_engine:
            self._main_engine.write_log(
                f"[持仓同步] 冻结持仓清除完成: 共删除 {deleted_count} 条价格线",
                "ChartWidget"
            )
    
    def _update_entry_line_pnl(self, position: PositionData) -> None:
        """更新入场线的浮动盈亏（在主线程中执行）
        
        使用 PositionHolding 来管理同方向的多个持仓，支持：
        1. 合并显示为一条入场线（显示加权平均价格）
        2. FIFO平仓逻辑（先进先出）
        3. 保留所有原始入场信息
        """
        # 初始化缓存字典（如果不存在）
        if not hasattr(self, '_position_update_cache'):
            self._position_update_cache = {}
        
        # 添加日志确认回调执行，包含冻结状态（事件驱动回调，保留但只在变化时输出）
        cache_key_callback = f"callback_{position.vt_symbol}_{position.direction.value}"
        current_callback = (position.volume, position.frozen, position.pnl)
        last_callback = self._position_update_cache.get(cache_key_callback)
        
        if last_callback != current_callback:
            # 注释回调开始执行日志，减少日志输出
            # if hasattr(self, '_main_engine') and self._main_engine:
            #     available_volume = position.volume - position.frozen
            #     self._main_engine.write_log(
            #         f"[持仓同步] _update_entry_line_pnl 回调开始执行: {position.vt_symbol} {position.direction.value} "
            #         f"volume={position.volume} frozen={position.frozen} available={available_volume} pnl={position.pnl}",
            #         "ChartWidget"
            #     )
            self._position_update_cache[cache_key_callback] = current_callback
        
        position_direction = "long" if position.direction.value == "多" else "short"
        all_lines = self._price_line_manager.get_all_lines()
        
        # 注释更新入场线盈亏详细信息日志，减少日志输出
        # entry_line_count = len([l for l in all_lines.values() if l.get_line_type() == PriceLineType.ENTRY])
        # available_volume = position.volume - position.frozen
        # cache_key_summary = f"{position_direction}_summary"
        # current_summary = (position.volume, position.frozen, available_volume, position.pnl, entry_line_count, len(all_lines))
        # last_summary = self._position_update_cache.get(cache_key_summary)
        # 
        # if last_summary != current_summary:
        #     if hasattr(self, '_main_engine') and self._main_engine:
        #         self._main_engine.write_log(
        #             f"[持仓同步] 更新入场线盈亏: 持仓方向={position_direction}, 持仓数量={position.volume}, "
        #             f"冻结={position.frozen}, 可用={available_volume}, 盈亏={position.pnl}, "
        #             f"入场线数量={entry_line_count}, 总价格线数量={len(all_lines)}",
        #             "ChartWidget"
        #         )
        #     self._position_update_cache[cache_key_summary] = current_summary
        
        # 获取该方向的持仓管理对象
        holding = self._position_holdings.get(position_direction)
        
        # 如果持仓为0，清除该方向的所有入场线和持仓记录
        if position.volume == 0:
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"检测到持仓为0，开始清除{position_direction}方向的入场线和持仓记录",
                    "Chart"
                )
        
            if holding:
                # 清空持仓记录
                holding.clear()
                self._position_holdings.pop(position_direction, None)
                if hasattr(self, '_main_engine') and self._main_engine:
                    self._main_engine.write_log(
                        f"持仓为0，已清空{position_direction}方向的持仓记录",
                        "Chart"
                    )
            else:
                if hasattr(self, '_main_engine') and self._main_engine:
                    self._main_engine.write_log(
                        f"持仓为0，但{position_direction}方向没有持仓记录（可能通过trade UI平仓），仍将删除入场线",
                        "Chart"
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
                                f"[持仓同步] 标记删除入场线: {line_id} (方向={line_direction}, 匹配={line_direction == position_direction})",
                                "Chart"
                            )
        
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[持仓同步] 找到 {len(lines_to_delete)} 条{position_direction}方向的入场线待删除",
                    "Chart"
                )
        
            deleted_count = 0
            for line_id in lines_to_delete:
                line = self._price_line_manager.get_line(line_id)
                if line:
                    # ✅ 正确顺序：先清理关联关系，再删除线本身
                    # 方法1：从 _entry_line_relations 查找关联关系
                    relations_found = False
                    relations = None
                    if hasattr(self, '_entry_line_relations') and line_id in self._entry_line_relations:
                        relations = self._entry_line_relations[line_id]
                        relations_found = True
                        
                        # ✅ 步骤1：先删除关联关系（内存）
                        self._entry_line_relations.pop(line_id, None)
                        
                        # ✅ 步骤2：再删除关联关系（数据库）
                        if self._price_line_database:
                            self._price_line_database.delete_relation(line_id)
                    
                    # ✅ 步骤3：删除关联的止损线和止盈线
                    if relations:
                        # 删除止损线
                        stop_loss_line_id = relations.get("stop_loss")
                        if stop_loss_line_id:
                            stop_loss_line = self._price_line_manager.get_line(stop_loss_line_id)
                            if stop_loss_line:
                                # 从 plot 中移除
                                if self._first_plot:
                                    try:
                                        self._first_plot.removeItem(stop_loss_line)
                                    except Exception:
                                        pass
                                # 从数据库中删除（在从管理器删除之前，确保数据库中也删除）
                                if self._price_line_database:
                                    self._price_line_database.delete_line(stop_loss_line_id)
                                # 从管理器中删除
                                if self._price_line_manager.delete_line(stop_loss_line_id):
                                    deleted_count += 1
                                    if hasattr(self, '_main_engine') and self._main_engine:
                                        self._main_engine.write_log(
                                            f"[持仓同步] 已删除关联止损线: {stop_loss_line_id}",
                                            "Chart"
                                        )
                    
                        # 删除止盈线
                        take_profit_line_id = relations.get("take_profit")
                        if take_profit_line_id:
                            take_profit_line = self._price_line_manager.get_line(take_profit_line_id)
                            if take_profit_line:
                                # 从 plot 中移除
                                if self._first_plot:
                                    try:
                                        self._first_plot.removeItem(take_profit_line)
                                    except Exception:
                                        pass
                                # 从数据库中删除（在从管理器删除之前，确保数据库中也删除）
                                if self._price_line_database:
                                    self._price_line_database.delete_line(take_profit_line_id)
                                # 从管理器中删除
                                if self._price_line_manager.delete_line(take_profit_line_id):
                                    deleted_count += 1
                                    if hasattr(self, '_main_engine') and self._main_engine:
                                        self._main_engine.write_log(
                                            f"[持仓同步] 已删除关联止盈线: {take_profit_line_id}",
                                            "Chart"
                                        )
                    
                    # 方法2：如果没有找到关联关系（例如恢复的入场线），从数据库查找
                    if not relations_found and self._price_line_database:
                        if hasattr(self, '_main_engine') and self._main_engine:
                            self._main_engine.write_log(
                                f"[持仓同步] 入场线 {line_id} 在内存中没有关联关系，尝试从数据库查找",
                                "Chart"
                            )
                        
                        db_relations = self._price_line_database.get_related_lines(line_id)
                        if db_relations:
                            if hasattr(self, '_main_engine') and self._main_engine:
                                self._main_engine.write_log(
                                    f"[持仓同步] 从数据库找到关联关系: {db_relations}",
                                    "Chart"
                                )
                            
                            # ✅ 步骤1：先删除关联关系（数据库）
                            self._price_line_database.delete_relation(line_id)
                            
                            # ✅ 步骤2：删除关联的止损线和止盈线
                            # 删除止损线
                            stop_loss_line_id = db_relations.get("stop_loss")
                            if stop_loss_line_id:
                                stop_loss_line = self._price_line_manager.get_line(stop_loss_line_id)
                                if stop_loss_line:
                                    if self._first_plot:
                                        try:
                                            self._first_plot.removeItem(stop_loss_line)
                                        except Exception:
                                            pass
                                    if self._price_line_database:
                                        self._price_line_database.delete_line(stop_loss_line_id)
                                    if self._price_line_manager.delete_line(stop_loss_line_id):
                                        deleted_count += 1
                                        if hasattr(self, '_main_engine') and self._main_engine:
                                            self._main_engine.write_log(
                                                f"[持仓同步] 已删除关联止损线（从数据库找到）: {stop_loss_line_id}",
                                                "Chart"
                                            )
                            
                            # 删除止盈线
                            take_profit_line_id = db_relations.get("take_profit")
                            if take_profit_line_id:
                                take_profit_line = self._price_line_manager.get_line(take_profit_line_id)
                                if take_profit_line:
                                    if self._first_plot:
                                        try:
                                            self._first_plot.removeItem(take_profit_line)
                                        except Exception:
                                            pass
                                    if self._price_line_database:
                                        self._price_line_database.delete_line(take_profit_line_id)
                                    if self._price_line_manager.delete_line(take_profit_line_id):
                                        deleted_count += 1
                                        if hasattr(self, '_main_engine') and self._main_engine:
                                            self._main_engine.write_log(
                                            f"[持仓同步] 已删除关联止盈线（从数据库找到）: {take_profit_line_id}",
                                            "Chart"
                                        )
                
                    # ✅ 步骤4：删除入场线本身
                    # 先从 plot 中移除（如果存在）
                    if self._first_plot:
                        try:
                            self._first_plot.removeItem(line)
                            if hasattr(self, '_main_engine') and self._main_engine:
                                self._main_engine.write_log(
                                    f"[持仓同步] 已从plot中移除入场线: {line_id}",
                                    "Chart"
                                )
                        except Exception as e:
                            if hasattr(self, '_main_engine') and self._main_engine:
                                    self._main_engine.write_log(
                                        f"[持仓同步] 从plot移除入场线失败: {line_id}, 错误: {str(e)}",
                                        "Chart"
                                    )
                
                    # 然后从管理器中删除
                    if self._price_line_manager.delete_line(line_id):
                        deleted_count += 1
                        if hasattr(self, '_main_engine') and self._main_engine:
                            self._main_engine.write_log(
                                f"[持仓同步] 已删除入场线: {line_id}",
                                "Chart"
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
                                f"[持仓同步] 警告: 从管理器删除入场线失败: {line_id}",
                                "Chart"
                            )
                else:
                    if hasattr(self, '_main_engine') and self._main_engine:
                        self._main_engine.write_log(
                            f"[持仓同步] 警告: 无法获取入场线: {line_id}",
                            "Chart"
                        )
        
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[持仓同步] 持仓为0，已删除 {deleted_count} 条{position_direction}方向的价格线（包括入场线及关联的止损/止盈线，共找到 {len(lines_to_delete)} 条入场线）",
                    "Chart"
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
                        f"[持仓同步] {position_direction}方向没有持仓记录，但从现有入场线创建持仓记录（找到 {len(entry_lines_for_direction)} 条入场线）",
                        "Chart"
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
                            f"[持仓同步] 警告: 有多条入场线但只有一条持仓记录，使用第一条入场线价格 {entry_price}，手数 {position.volume}",
                            "Chart"
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
                                        f"[持仓同步] 警告: 创建入场线失败，返回的line_id为空",
                                        "Chart"
                                    )
                                return
                        
                            # 验证入场线是否在manager中
                            created_line = self._price_line_manager.get_line(created_line_id)
                            if not created_line:
                                if hasattr(self, '_main_engine') and self._main_engine:
                                    self._main_engine.write_log(
                                        f"[持仓同步] 警告: 创建入场线后无法从manager获取: {created_line_id}",
                                        "Chart"
                                    )
                                return
                        
                            # 创建持仓记录
                            holding = PositionHolding(position_direction)
                            self._position_holdings[position_direction] = holding
                            add_entry_to_holding(
                                self._position_holdings,
                                line_id=created_line_id,
                                direction=position_direction,
                                price=entry_price,
                                volume=position.volume,
                                vt_orderid=None,
                                trade_time=datetime.now(),
                                database=self._price_line_database,
                                vt_symbol=self._vt_symbol
                            )
                        
                            if hasattr(self, '_main_engine') and self._main_engine:
                                self._main_engine.write_log(
                                    f"[持仓同步] 已根据持仓信息恢复入场线: {created_line_id}, 价格={entry_price}, 手数={position.volume}, 方向={position_direction}",
                                    "Chart"
                                )
                        
                            # 验证持仓记录中的入场线ID
                            entry_line_ids = holding.get_entry_line_ids()
                            if hasattr(self, '_main_engine') and self._main_engine:
                                self._main_engine.write_log(
                                    f"[持仓同步] 验证: 持仓记录中的入场线ID列表={entry_line_ids}, 期望包含={created_line_id}",
                                    "Chart"
                                )
                        
                            # 创建入场线后，继续执行后续的更新逻辑（不要return）
                            # 重新获取holding，因为刚刚创建了
                            holding = self._position_holdings.get(position_direction)
                        else:
                            if hasattr(self, '_main_engine') and self._main_engine:
                                self._main_engine.write_log(
                                    f"[持仓同步] 无法恢复入场线: drawing_order_controller未初始化",
                                    "Chart"
                                )
                            return
                    else:
                        if hasattr(self, '_main_engine') and self._main_engine:
                            self._main_engine.write_log(
                                f"[持仓同步] 无法恢复入场线: 持仓价格和当前价格都为0",
                                "Chart"
                            )
                        return
                else:
                    # 持仓数量为0，跳过
                    if hasattr(self, '_main_engine') and self._main_engine:
                        self._main_engine.write_log(
                            f"[持仓同步] {position_direction}方向没有持仓记录也没有入场线，且持仓数量为0，跳过更新",
                            "Chart"
                        )
                    return
        
        # 计算持仓变化：如果当前持仓手数小于持仓记录中的总手数，说明有平仓
        # 从 PositionHolding 的 entries 计算总手数（用于 FIFO 平仓判断）
        holding_total_volume = sum(e.volume for e in holding.get_all_entries())
        
        # 添加详细日志，帮助调试（只在持仓变化时输出）
        cache_key_check = f"{position_direction}_holding_check"
        current_check = (holding_total_volume, position.volume, len(holding.get_all_entries()))
        last_check = self._position_update_cache.get(cache_key_check)
        
        if last_check != current_check:
            # 注释持仓变化检查日志，减少日志输出
            # if hasattr(self, '_main_engine') and self._main_engine:
            #     self._main_engine.write_log(
            #         f"[持仓同步] 持仓变化检查: 持仓记录总手数={holding_total_volume}, 实际持仓手数={position.volume}, "
            #         f"持仓记录数量={len(holding.get_all_entries())}",
            #         "ChartWidget"
            #     )
            self._position_update_cache[cache_key_check] = current_check
        
        # 只有当实际持仓手数明显小于持仓记录总手数时，才认为是平仓
        # 使用 0.01 的容差，避免浮点数精度问题
        if position.volume < holding_total_volume - 0.01:
            # 有平仓，按照FIFO原则移除持仓记录
            close_volume = holding_total_volume - position.volume
        
            # 确保平仓手数不超过持仓记录总手数
            if close_volume > holding_total_volume:
                close_volume = holding_total_volume
        
            # 注释平仓检测日志，减少日志输出
            # if hasattr(self, '_main_engine') and self._main_engine:
            #     self._main_engine.write_log(
            #         f"[持仓同步] 检测到平仓: 平仓手数={close_volume}, 持仓记录总手数={holding_total_volume}, "
            #         f"实际持仓手数={position.volume}",
            #         "ChartWidget"
            #     )
        
            closed_entries = process_position_close(
                self._position_holdings, 
                position_direction, 
                close_volume,
                database=self._price_line_database,
                vt_symbol=self._vt_symbol
            )
        
            # 注释移除持仓记录日志，减少日志输出
            # if hasattr(self, '_main_engine') and self._main_engine:
            #     self._main_engine.write_log(
            #         f"[持仓同步] 已移除 {len(closed_entries)} 条持仓记录",
            #         "ChartWidget"
            #     )
        
            # 删除已平仓的入场线
            for closed_entry in closed_entries:
                line_id = closed_entry.line_id
                if self._price_line_manager.delete_line(line_id):
                    # 注释删除入场线日志，减少日志输出
                    # if hasattr(self, '_main_engine') and self._main_engine:
                    #     self._main_engine.write_log(
                    #         f"[持仓同步] 已删除已平仓的入场线: {line_id} (价格={closed_entry.price}, 手数={closed_entry.volume})",
                    #         "ChartWidget"
                    #     )
                    pass
                    # 清理订单映射
                    if hasattr(self, '_drawing_order_controller') and self._drawing_order_controller:
                        order_id = self._drawing_order_controller.get_order_id_for_line(line_id)
                        if order_id:
                            self._drawing_order_controller._line_order_map.pop(line_id, None)
                            self._drawing_order_controller._order_line_map.pop(order_id, None)
        elif abs(position.volume - holding_total_volume) <= 0.01:
            # 持仓手数一致，没有平仓（不输出日志，避免刷屏）
            pass
        else:
            # 实际持仓手数大于持仓记录总手数，可能是新开仓（通过 trade UI）
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[持仓同步] 实际持仓手数大于持仓记录总手数，可能是新开仓: "
                    f"持仓记录总手数={holding_total_volume}, 实际持仓手数={position.volume}",
                    "Chart"
                )
        
        # 重新获取持仓管理对象（可能已被修改）
        holding = self._position_holdings.get(position_direction)
        if not holding or holding.is_empty():
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[持仓同步] {position_direction}方向持仓记录为空，跳过更新",
                    "Chart"
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
        
        # 持仓统计（只在数据变化时输出）
        cache_key_stats = f"{position_direction}_stats"
        current_stats = (avg_price, total_volume, position.pnl, len(entry_lines))
        last_stats = self._position_update_cache.get(cache_key_stats)
        
        if last_stats != current_stats:
            # 注释持仓统计和入场线获取日志，减少日志输出
            # if hasattr(self, '_main_engine') and self._main_engine:
            #     self._main_engine.write_log(
            #         f"[持仓同步] 持仓统计: 方向={position_direction}, 加权均价={avg_price:.2f}, 总手数={total_volume}, 浮动盈亏={position.pnl}",
            #         "ChartWidget"
            #     )
            #     self._main_engine.write_log(
            #         f"[持仓同步] 从PriceLineManager获取入场线: {len(entry_lines)} 条（方向={position_direction}）",
            #         "ChartWidget"
            #     )
            self._position_update_cache[cache_key_stats] = current_stats
        
        # 如果PriceLineManager中没有入场线，但持仓数量>0，需要创建入场线
        if not entry_lines and position.volume > 0:
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[持仓同步] 持仓记录中的入场线ID都不存在，但持仓数量>0，需要重新创建入场线",
                    "Chart"
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
                            "Chart"
                        )
                else:
                    if hasattr(self, '_main_engine') and self._main_engine:
                        # 使用 % 格式化避免 loguru 的二次格式化问题
                        self._main_engine.write_log(
                            "[ChartWidget] 创建入场线失败: %s" % created_line_id,
                            "Chart"
                        )
                    return
        
        # 如果仍然没有入场线，跳过更新
        if not entry_lines:
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[持仓同步] {position_direction}方向没有入场线，跳过更新",
                    "Chart"
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
                    f"[持仓同步] 发现孤儿ID，从PositionHolding中移除: {list(to_remove)}",
                    "Chart"
                )
            # 从PositionHolding中移除孤儿ID
            holding._entries = [e for e in holding._entries if e.line_id not in to_remove]
        
        if to_add:
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[持仓同步] 发现新入场线，添加到PositionHolding: {list(to_add)}",
                    "Chart"
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
                    add_entry_to_holding(
                        self._position_holdings,
                        line_id=line_id,
                        direction=position_direction,
                        price=line.get_price(),
                        volume=volume,
                        vt_orderid=line.get_vt_orderid(),
                        trade_time=datetime.now(),
                        database=self._price_line_database,
                        vt_symbol=self._vt_symbol
                    )
        
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
        
        # 使用第一条入场线作为合并显示线
        main_line_id, main_line = entry_lines[0]
        
        # 更新合并显示线的价格为加权平均价格，并更新盈亏和手数
        old_price = main_line.get_price()
        if abs(old_price - avg_price) > 0.01:  # 价格有变化，更新价格
            main_line.set_price(avg_price, price_precision=0)
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[持仓同步] 更新合并显示线价格: {main_line_id} {old_price:.2f} -> {avg_price:.2f}",
                    "Chart"
                )
        
        # 更新盈亏和手数
        old_pnl = main_line.get_pnl()
        old_volume = main_line.get_volume()
        main_line.set_pnl_and_volume(position.pnl, total_volume)
        
        # 验证更新是否成功
        new_pnl = main_line.get_pnl()
        new_volume = main_line.get_volume()
        
        # 只在数据实际变化时输出日志
        cache_key_line = f"{main_line_id}_update"
        current_line_data = (old_pnl, new_pnl, old_volume, new_volume, avg_price)
        last_line_data = self._position_update_cache.get(cache_key_line)
        
        if last_line_data != current_line_data:
            # 只在盈亏有实际变化时打印简要日志
            if hasattr(self, '_main_engine') and self._main_engine and abs(new_pnl - old_pnl) > 0.01:
                price_precision = 0
                label_text = main_line._create_label(avg_price, PriceLineType.ENTRY, price_precision, position_direction)
                self._main_engine.write_log(
                    f"[入场线盈亏] {main_line_id}: {label_text}",
                    "Chart"
                )
                
                # 注释标签更新验证日志，减少日志输出
                # if main_line.label is not None:
                #     # 检查标签文本（InfLineLabel没有text()方法，但我们可以通过其他方式验证）
                #     self._main_engine.write_log(
                #         f"[持仓同步] 入场线 {main_line_id} 标签已更新，价格={avg_price}, 手数={new_volume}, 盈亏={new_pnl}",
                #         "ChartWidget"
                #     )
                # else:
                #     self._main_engine.write_log(
                #         f"[持仓同步] 警告: 入场线 {main_line_id} 的label为None，无法显示更新",
                #         "ChartWidget"
                #     )
            self._position_update_cache[cache_key_line] = current_line_data
        
        # 隐藏其他入场线（但不删除，保留原始信息）
        # 保留所有止损/止盈线，并为每条设置对应的手数
        for line_id, line in entry_lines[1:]:  # 跳过第一条（合并显示线）
            # 获取被隐藏入场线的手数（从 PositionHolding 中获取）
            entry_volume = 0.0
            if holding:
                entry = next((e for e in holding.get_all_entries() if e.line_id == line_id), None)
                if entry:
                    entry_volume = entry.volume
        
            # 为被隐藏入场线的止损/止盈线设置手数
            if hasattr(self, '_entry_line_relations') and line_id in self._entry_line_relations:
                hidden_relations = self._entry_line_relations[line_id]
            
                # 设置止损线手数（即使 entry_volume == 0，也要确保止损线可见）
                stop_loss_line_id = hidden_relations.get("stop_loss")
                if stop_loss_line_id:
                    stop_loss_line = self._price_line_manager.get_line(stop_loss_line_id)
                    if stop_loss_line:
                        if entry_volume > 0:
                            stop_loss_line.set_volume(entry_volume)
                        stop_loss_line.setVisible(True)  # 确保可见
                        if hasattr(self, '_main_engine') and self._main_engine:
                            self._main_engine.write_log(
                                f"[持仓同步] 合并显示：为入场线 {line_id} 的止损线 {stop_loss_line_id} 设置手数 {entry_volume}，确保可见",
                                "Chart"
                            )
            
                # 设置止盈线手数（即使 entry_volume == 0，也要确保止盈线可见）
                take_profit_line_id = hidden_relations.get("take_profit")
                if take_profit_line_id:
                    take_profit_line = self._price_line_manager.get_line(take_profit_line_id)
                    if take_profit_line:
                        if entry_volume > 0:
                            take_profit_line.set_volume(entry_volume)
                        take_profit_line.setVisible(True)  # 确保可见
                        if hasattr(self, '_main_engine') and self._main_engine:
                            self._main_engine.write_log(
                                f"[持仓同步] 合并显示：为入场线 {line_id} 的止盈线 {take_profit_line_id} 设置手数 {entry_volume}，确保可见",
                                "Chart"
                            )
        
            # 隐藏入场线（通过设置不可见）
            line.setVisible(False)
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[持仓同步] 已隐藏入场线: {line_id} (保留原始信息，手数={entry_volume})",
                    "Chart"
                )
        
        # 确保合并显示线可见
        main_line.setVisible(True)
        
        # 为合并显示线的止损/止盈线设置手数（如果有）
        if hasattr(self, '_entry_line_relations') and main_line_id in self._entry_line_relations:
            main_relations = self._entry_line_relations[main_line_id]
        
            # 获取合并显示线的手数（直接使用 position.volume，这是实际持仓总手数）
            # 注意：total_volume 已经在上面计算出来了（第1209行：total_volume = position.volume）
            # 这是最准确的总持仓手数，应该优先使用
            main_entry_volume = total_volume  # 使用已计算的 total_volume（来自 position.volume）
        
            # 如果 total_volume 为 0，尝试从 PositionHolding 获取（备用方案）
            if main_entry_volume <= 0 and holding:
                # 计算总持仓手数（从 PositionHolding 中计算）
                calculated_total_volume = sum(e.volume for e in holding.get_all_entries())
                if calculated_total_volume > 0:
                    main_entry_volume = calculated_total_volume
                else:
                    # 如果总手数为0，尝试从单个入场线获取（兼容旧逻辑）
                    main_entry = next((e for e in holding.get_all_entries() if e.line_id == main_line_id), None)
                    if main_entry:
                        main_entry_volume = main_entry.volume
        
            # 设置止损线手数并确保可见
            stop_loss_line_id = main_relations.get("stop_loss")
            if stop_loss_line_id:
                stop_loss_line = self._price_line_manager.get_line(stop_loss_line_id)
                if stop_loss_line:
                    if main_entry_volume > 0:
                        stop_loss_line.set_volume(main_entry_volume)
                    stop_loss_line.setVisible(True)
                    # 注释确保止损线可见日志，减少日志输出
                    # if hasattr(self, '_main_engine') and self._main_engine:
                    #     self._main_engine.write_log(
                    #         f"[持仓同步] 合并显示：确保止损线 {stop_loss_line_id} 可见（关联到合并显示线 {main_line_id}，手数={main_entry_volume}）",
                    #         "ChartWidget"
                    #     )
        
            # 设置止盈线手数并确保可见
            take_profit_line_id = main_relations.get("take_profit")
            if take_profit_line_id:
                take_profit_line = self._price_line_manager.get_line(take_profit_line_id)
                if take_profit_line:
                    if main_entry_volume > 0:
                        take_profit_line.set_volume(main_entry_volume)
                    take_profit_line.setVisible(True)
                    # 注释确保止盈线可见日志，减少日志输出
                    # if hasattr(self, '_main_engine') and self._main_engine:
                    #     self._main_engine.write_log(
                    #         f"[持仓同步] 合并显示：确保止盈线 {take_profit_line_id} 可见（关联到合并显示线 {main_line_id}，手数={main_entry_volume}）",
                    #         "ChartWidget"
                    #     )
        
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
                                f"[持仓同步] 持仓数为0，但存在其他方向持仓: {pos.vt_symbol} {pos.direction.value} volume={pos.volume}，不清除所有入场线",
                                "Chart"
                            )
                        break
        
            # 只有当所有方向持仓都为0时，才清除所有入场线
            if should_clear_all:
                if hasattr(self, '_main_engine') and self._main_engine:
                    self._main_engine.write_log(
                        f"[持仓同步] 持仓数为0，且所有方向持仓都为0，开始清除所有入场线、止损线和止盈线",
                        "Chart"
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
                                f"[持仓同步] 标记删除入场线: {line_id} (方向={line.get_direction()})",
                                "Chart"
                            )
                    
                        # 通过关联关系查找并标记关联的止损线和止盈线
                        if hasattr(self, '_entry_line_relations') and line_id in self._entry_line_relations:
                            relations = self._entry_line_relations[line_id]
                        
                            if hasattr(self, '_main_engine') and self._main_engine:
                                self._main_engine.write_log(
                                    f"[持仓同步] 入场线 {line_id} 的关联关系: {relations}",
                                    "Chart"
                                )
                        
                            # 标记止损线
                            stop_loss_line_id = relations.get("stop_loss")
                            if stop_loss_line_id:
                                if stop_loss_line_id not in lines_to_delete:
                                    lines_to_delete.append(stop_loss_line_id)
                                    if hasattr(self, '_main_engine') and self._main_engine:
                                        self._main_engine.write_log(
                                            f"[持仓同步] 通过关联关系标记删除止损线: {stop_loss_line_id} (关联到入场线 {line_id})",
                                            "Chart"
                                        )
                                else:
                                    if hasattr(self, '_main_engine') and self._main_engine:
                                        self._main_engine.write_log(
                                            f"[持仓同步] 止损线 {stop_loss_line_id} 已在删除列表中",
                                            "Chart"
                                        )
                            else:
                                if hasattr(self, '_main_engine') and self._main_engine:
                                    self._main_engine.write_log(
                                        f"[持仓同步] 入场线 {line_id} 没有关联的止损线",
                                        "Chart"
                                    )
                        
                            # 标记止盈线
                            take_profit_line_id = relations.get("take_profit")
                            if take_profit_line_id:
                                if take_profit_line_id not in lines_to_delete:
                                    lines_to_delete.append(take_profit_line_id)
                                    if hasattr(self, '_main_engine') and self._main_engine:
                                        self._main_engine.write_log(
                                            f"[持仓同步] 通过关联关系标记删除止盈线: {take_profit_line_id} (关联到入场线 {line_id})",
                                            "Chart"
                                        )
                                else:
                                    if hasattr(self, '_main_engine') and self._main_engine:
                                        self._main_engine.write_log(
                                            f"[持仓同步] 止盈线 {take_profit_line_id} 已在删除列表中",
                                            "Chart"
                                        )
                            else:
                                if hasattr(self, '_main_engine') and self._main_engine:
                                    self._main_engine.write_log(
                                        f"[持仓同步] 入场线 {line_id} 没有关联的止盈线",
                                        "Chart"
                                    )
                        else:
                            if hasattr(self, '_main_engine') and self._main_engine:
                                self._main_engine.write_log(
                                    f"[持仓同步] 入场线 {line_id} 没有关联关系记录",
                                    "Chart"
                                )
            
                # 查找所有未关联的止损线和止盈线（作为兜底，确保所有止损/止盈线都被删除）
                for line_id, line in all_lines.items():
                    line_type = line.get_line_type()
                    if (line_type == PriceLineType.STOP_LOSS or line_type == PriceLineType.TAKE_PROFIT) and line_id not in lines_to_delete:
                        lines_to_delete.append(line_id)
                        if hasattr(self, '_main_engine') and self._main_engine:
                            self._main_engine.write_log(
                                f"[持仓同步] 标记删除未关联的{line_type.value}线: {line_id} (方向={line.get_direction()})",
                                "Chart"
                            )
            
                # 删除所有标记的线
                deleted_count = 0
                deleted_entry_count = 0
                deleted_stop_loss_count = 0
                deleted_take_profit_count = 0
            
                for line_id in lines_to_delete:
                    # 获取线的类型，用于统计
                    line = self._price_line_manager.get_line(line_id)
                    if not line:
                        # 线不存在，跳过
                        if hasattr(self, '_main_engine') and self._main_engine:
                            self._main_engine.write_log(
                                f"[持仓同步] 警告：标记删除的线 {line_id} 不存在，跳过",
                                "Chart"
                            )
                        continue
                
                    line_type = line.get_line_type()
                
                    # 如果是入场线，先清理关联关系
                    if line_type == PriceLineType.ENTRY:
                        if hasattr(self, '_entry_line_relations') and line_id in self._entry_line_relations:
                            # 清理关联关系
                            self._entry_line_relations.pop(line_id, None)
                            # 清理数据库中的关联关系
                            if self._price_line_database:
                                self._price_line_database.delete_all_relations(line_id)
                
                    # 从 plot 中移除
                    if line.scene() is not None and self._first_plot:
                        try:
                            self._first_plot.removeItem(line)
                        except Exception as e:
                            if hasattr(self, '_main_engine') and self._main_engine:
                                self._main_engine.write_log(
                                    f"[持仓同步] 从plot移除线 {line_id} 失败: {str(e)}",
                                    "Chart"
                                )
                
                    # 从管理器中删除
                    if self._price_line_manager.delete_line(line_id):
                        deleted_count += 1
                    
                        # 统计删除的线类型
                        if line_type == PriceLineType.ENTRY:
                            deleted_entry_count += 1
                        elif line_type == PriceLineType.STOP_LOSS:
                            deleted_stop_loss_count += 1
                        elif line_type == PriceLineType.TAKE_PROFIT:
                            deleted_take_profit_count += 1
                    
                        if hasattr(self, '_main_engine') and self._main_engine:
                            self._main_engine.write_log(
                                f"[持仓同步] 已删除{line_type.value}线: {line_id}",
                                "Chart"
                            )
                    
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
                    
                        # 清理双击防抖记录
                        self._last_double_click_close.pop(line_id, None)
                    else:
                        if hasattr(self, '_main_engine') and self._main_engine:
                            self._main_engine.write_log(
                                f"[持仓同步] 警告：删除{line_type.value}线 {line_id} 失败",
                                "Chart"
                            )
            
                if hasattr(self, '_main_engine') and self._main_engine:
                    self._main_engine.write_log(
                        f"[持仓同步] 持仓数为0，已清除 {deleted_count} 条价格线 "
                        f"(入场线={deleted_entry_count}, 止损线={deleted_stop_loss_count}, 止盈线={deleted_take_profit_count})",
                        "Chart"
                    )
                return
            else:
                # 只清除与当前持仓方向匹配的入场线
                if hasattr(self, '_main_engine') and self._main_engine:
                    self._main_engine.write_log(
                        f"[持仓同步] 持仓数为0，但存在其他方向持仓，只清除{position_direction}方向的入场线",
                        "Chart"
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
                                f"[持仓同步] 标记删除{position_direction}方向入场线: {line_id}",
                                "Chart"
                            )
                    
                        # 通过关联关系查找并标记关联的止损线和止盈线
                        if hasattr(self, '_entry_line_relations') and line_id in self._entry_line_relations:
                            relations = self._entry_line_relations[line_id]
                        
                            # 标记止损线
                            stop_loss_line_id = relations.get("stop_loss")
                            if stop_loss_line_id and stop_loss_line_id not in lines_to_delete:
                                lines_to_delete.append(stop_loss_line_id)
                                if hasattr(self, '_main_engine') and self._main_engine:
                                    self._main_engine.write_log(
                                        f"[持仓同步] 通过关联关系标记删除止损线: {stop_loss_line_id} (关联到入场线 {line_id})",
                                        "Chart"
                                    )
                        
                            # 标记止盈线
                            take_profit_line_id = relations.get("take_profit")
                            if take_profit_line_id and take_profit_line_id not in lines_to_delete:
                                lines_to_delete.append(take_profit_line_id)
                                if hasattr(self, '_main_engine') and self._main_engine:
                                    self._main_engine.write_log(
                                        f"[持仓同步] 通过关联关系标记删除止盈线: {take_profit_line_id} (关联到入场线 {line_id})",
                                        "Chart"
                                    )
                
                    # 只清除匹配方向的未关联的止损线和止盈线（作为兜底）
                    if (line_type == PriceLineType.STOP_LOSS or line_type == PriceLineType.TAKE_PROFIT) and line_direction == position_direction and line_id not in lines_to_delete:
                        lines_to_delete.append(line_id)
                        if hasattr(self, '_main_engine') and self._main_engine:
                            self._main_engine.write_log(
                                f"[持仓同步] 标记删除{position_direction}方向未关联的{line_type.value}线: {line_id}",
                                "Chart"
                            )
            
                # 删除标记的线
                deleted_count = 0
                deleted_entry_count = 0
                deleted_stop_loss_count = 0
                deleted_take_profit_count = 0
            
                for line_id in lines_to_delete:
                    # 获取线的类型，用于统计
                    line = self._price_line_manager.get_line(line_id)
                    if not line:
                        # 线不存在，跳过
                        if hasattr(self, '_main_engine') and self._main_engine:
                            self._main_engine.write_log(
                                f"[持仓同步] 警告：标记删除的线 {line_id} 不存在，跳过",
                                "Chart"
                            )
                        continue
                
                    line_type = line.get_line_type()
                
                    # 如果是入场线，先清理关联关系
                    if line_type == PriceLineType.ENTRY:
                        if hasattr(self, '_entry_line_relations') and line_id in self._entry_line_relations:
                            # 清理关联关系
                            self._entry_line_relations.pop(line_id, None)
                            # 清理数据库中的关联关系
                            if self._price_line_database:
                                self._price_line_database.delete_all_relations(line_id)
                
                    # 从 plot 中移除
                    if line.scene() is not None and self._first_plot:
                        try:
                            self._first_plot.removeItem(line)
                        except Exception as e:
                            if hasattr(self, '_main_engine') and self._main_engine:
                                self._main_engine.write_log(
                                    f"[持仓同步] 从plot移除线 {line_id} 失败: {str(e)}",
                                    "Chart"
                                )
                
                    # 从管理器中删除
                    if self._price_line_manager.delete_line(line_id):
                        deleted_count += 1
                    
                        # 统计删除的线类型
                        if line_type == PriceLineType.ENTRY:
                            deleted_entry_count += 1
                        elif line_type == PriceLineType.STOP_LOSS:
                            deleted_stop_loss_count += 1
                        elif line_type == PriceLineType.TAKE_PROFIT:
                            deleted_take_profit_count += 1
                    
                        if hasattr(self, '_main_engine') and self._main_engine:
                            self._main_engine.write_log(
                                f"[持仓同步] 已删除{line_type.value}线: {line_id}",
                                "Chart"
                            )
                    
                        # 清理订单映射
                        if hasattr(self, '_drawing_order_controller') and self._drawing_order_controller:
                            order_id = self._drawing_order_controller.get_order_id_for_line(line_id)
                            if order_id:
                                self._drawing_order_controller._line_order_map.pop(line_id, None)
                                self._drawing_order_controller._order_line_map.pop(order_id, None)
                            if hasattr(self._drawing_order_controller, '_pending_line_relations'):
                                self._drawing_order_controller._pending_line_relations.pop(line_id, None)
                    
                        # 清理双击防抖记录
                        self._last_double_click_close.pop(line_id, None)
                    else:
                        if hasattr(self, '_main_engine') and self._main_engine:
                            self._main_engine.write_log(
                                f"[持仓同步] 警告：删除{line_type.value}线 {line_id} 失败",
                                "Chart"
                            )
            
                if hasattr(self, '_main_engine') and self._main_engine:
                    self._main_engine.write_log(
                        f"[持仓同步] 已清除 {deleted_count} 条{position_direction}方向的价格线 "
                        f"(入场线={deleted_entry_count}, 止损线={deleted_stop_loss_count}, 止盈线={deleted_take_profit_count})",
                        "Chart"
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
        
        # 只在持仓映射或入场线数量变化时输出日志
        cache_key_find = f"{position_direction}_find"
        position_map_items = list(position_map.items()) if position_map else []
        available_volume = position.volume - position.frozen
        current_find = (len(entry_lines), position.volume, position.frozen, available_volume, tuple(position_map_items))
        last_find = self._position_update_cache.get(cache_key_find)
        
        if last_find != current_find:
            # 注释获取所有持仓、匹配持仓、查找入场线的详细日志，减少日志输出
            # if hasattr(self, '_main_engine') and self._main_engine:
            #     self._main_engine.write_log(
            #         f"[持仓同步] 获取所有持仓: 总数={len(all_positions)}, 当前持仓方向={position_direction}, 当前持仓数量={position.volume}",
            #         "ChartWidget"
            #     )
            #     for pos in all_positions:
            #         pos_vt_symbol = pos.vt_symbol
            #         matched = False
            #         if chart_vt_symbol and pos_vt_symbol == chart_vt_symbol:
            #             matched = True
            #         else:
            #             pos_symbol = pos.symbol
            #             chart_symbol = chart_vt_symbol.split('.')[0] if '.' in chart_vt_symbol else chart_vt_symbol
            #             for gateway_name in self._main_engine.get_all_gateway_names():
            #                 gateway = self._main_engine.get_gateway(gateway_name)
            #                 if gateway and hasattr(gateway, 'get_main_contract_mapping'):
            #                     mapping = gateway.get_main_contract_mapping()
            #                     for main_symbol, actual_symbol in mapping.items():
            #                         if actual_symbol == pos_symbol:
            #                             main_vt_symbol = f"{main_symbol}.{pos.exchange.value}"
            #                             if main_vt_symbol == chart_vt_symbol:
            #                                 matched = True
            #                                 break
            #                     if matched:
            #                         break
            #         if matched:
            #             pos_direction = "long" if pos.direction.value == "多" else "short"
            #             self._main_engine.write_log(
            #                 f"[持仓同步] 匹配持仓: {pos.vt_symbol} {pos.direction.value} {pos.volume}手 -> position_map[{pos_direction}]={pos.volume}",
            #                 "ChartWidget"
            #             )
            #     self._main_engine.write_log(
            #         f"[持仓同步] 查找入场线: 总入场线数量={len(entry_lines)}, 持仓方向={position_direction}, "
            #         f"持仓数量={position.volume}, 冻结={position.frozen}, 可用={available_volume}, 持仓映射={position_map_items}",
            #         "ChartWidget"
            #     )
            self._position_update_cache[cache_key_find] = current_find
        
        # 收集需要删除的入场线（方向没有持仓或持仓为0）
        lines_to_delete = []
        
        # 收集匹配方向的入场线（用于更新）
        matching_entry_lines = []
        
        for line_id, line in all_lines.items():
            if line.get_line_type() != PriceLineType.ENTRY:
                continue
        
            # 检查持仓方向是否匹配
            direction = line.get_direction()
        
            # 检查入场线的日志只在变化时输出（注释掉，避免刷屏）
            # if hasattr(self, '_main_engine') and self._main_engine:
            #     self._main_engine.write_log(
            #         f"[持仓同步] 检查入场线 {line_id}: 方向={direction}, 持仓方向={position_direction}, 匹配={direction == position_direction}, 持仓数量={position.volume}",
            #         "ChartWidget"
            #     )
        
            # 检查该方向的持仓是否存在且不为0
            # 优先使用当前持仓更新的值（position.volume），如果为0，则检查position_map
            line_position_volume = position_map.get(direction, 0.0)
        
            # 如果当前持仓更新显示该方向持仓为0，且入场线方向匹配，则应该删除
            if direction == position_direction and position.volume <= 0:
                # 当前持仓更新显示持仓为0，应该删除这条入场线
                lines_to_delete.append((line_id, direction))
                if hasattr(self, '_main_engine') and self._main_engine:
                    self._main_engine.write_log(
                        f"[持仓同步] 标记删除入场线 {line_id}: 方向={direction}的持仓为0 (当前持仓更新: {position.volume}, 持仓映射中的值={line_position_volume})",
                        "Chart"
                    )
                continue
        
            # 如果持仓映射中该方向的持仓为0或不存在，也应该删除这条入场线
            if line_position_volume <= 0:
                # 该方向的持仓为0或不存在，应该删除这条入场线
                lines_to_delete.append((line_id, direction))
                if hasattr(self, '_main_engine') and self._main_engine:
                    self._main_engine.write_log(
                        f"[持仓同步] 标记删除入场线 {line_id}: 方向={direction}的持仓为0或不存在 (持仓映射中的值={line_position_volume})",
                        "Chart"
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
                        f"[持仓同步] 发现 {len(matching_entry_lines)} 条匹配方向的入场线，将更新第一条，删除其他",
                        "Chart"
                    )
                # 只保留第一条，其他标记为删除
                for i, (line_id, line) in enumerate(matching_entry_lines[1:], start=1):
                    lines_to_delete.append((line_id, position_direction))
                    if hasattr(self, '_main_engine') and self._main_engine:
                        self._main_engine.write_log(
                            f"[持仓同步] 标记删除重复入场线 {line_id} (保留第一条)",
                            "Chart"
                        )
        
            # 更新第一条入场线
            line_id, line = matching_entry_lines[0]
            old_pnl = line.get_pnl()
            old_volume = line.get_volume()
            line.set_pnl_and_volume(position.pnl, position.volume)
        
            # 只在盈亏或手数实际变化时输出日志
            cache_key_entry = f"{line_id}_entry_update"
            current_entry_data = (old_pnl, position.pnl, old_volume, position.volume)
            last_entry_data = self._position_update_cache.get(cache_key_entry)
            
            if last_entry_data != current_entry_data:
                # 注释更新入场线盈亏和手数日志，减少日志输出（已在合并显示线处打印）
                # if hasattr(self, '_main_engine') and self._main_engine:
                #     self._main_engine.write_log(
                #         f"[持仓同步] 更新入场线 {line_id} 盈亏和手数: 盈亏={old_pnl} -> {position.pnl}, 手数={old_volume} -> {position.volume}",
                #         "ChartWidget"
                #     )
                
                # 标签已通过set_pnl_and_volume自动更新，这里只需要记录
                if line.label is not None:
                    updated_count += 1
                    # 注释入场线标签更新日志，减少日志输出（已有[入场线盈亏]日志）
                    # if hasattr(self, '_main_engine') and self._main_engine:
                    #     # 重新生成标签文本用于日志记录（InfLineLabel没有text()方法）
                    #     price_precision = 0  # 默认整数显示
                    #     label_text = line._create_label(line._price, line._line_type, price_precision, line._direction)
                    #     self._main_engine.write_log(
                    #         f"[持仓同步] 已更新入场线 {line_id} 标签: {label_text}",
                    #         "ChartWidget"
                    #     )
                    pass
                else:
                    if hasattr(self, '_main_engine') and self._main_engine:
                        self._main_engine.write_log(
                            f"[持仓同步] 警告: 入场线 {line_id} 的label为None，无法更新显示",
                            "Chart"
                        )
                self._position_update_cache[cache_key_entry] = current_entry_data
            elif line.label is not None:
                updated_count += 1
        
        # 删除没有持仓的入场线及其关联的止损止盈线
        # 先打印数据库状态（用于调试）
        # if hasattr(self, '_price_line_database') and self._price_line_database and hasattr(self, '_main_engine') and self._main_engine:
        #     debug_info = self._price_line_database.debug_print_all_lines_and_relations(vt_symbol=self._vt_symbol)
        #     self._main_engine.write_log(
        #         f"[持仓同步] 删除入场线前，数据库状态:\n{debug_info}",
        #         "ChartWidget"
        #     )
        
        # 添加详细日志
        # if hasattr(self, '_main_engine') and self._main_engine:
        #     self._main_engine.write_log(
        #         f"[持仓同步] 准备删除入场线: lines_to_delete数量={len(lines_to_delete)}, "
        #         f"持仓方向={position_direction}, 持仓数量={position.volume}, 持仓映射={list(position_map.items()) if position_map else []}",
        #         "ChartWidget"
        #     )
        #     if lines_to_delete:
        #         for line_id, line_direction in lines_to_delete:
        #             self._main_engine.write_log(
        #                 f"[持仓同步] 待删除入场线: {line_id}, 方向={line_direction}",
        #                 "ChartWidget"
        #             )
        #     else:
        #         self._main_engine.write_log(
        #             f"[持仓同步] 警告: lines_to_delete为空，没有入场线需要删除",
        #             "ChartWidget"
        #         )
        
        deleted_count = 0
        deleted_entry_count = 0
        deleted_stop_loss_count = 0
        deleted_take_profit_count = 0
        
        for line_id, line_direction in lines_to_delete:
            # 先通过关联关系查找并标记关联的止损线和止盈线
            related_lines_to_delete = []
            if hasattr(self, '_entry_line_relations') and line_id in self._entry_line_relations:
                relations = self._entry_line_relations[line_id]
            
                # 标记止损线
                stop_loss_line_id = relations.get("stop_loss")
                if stop_loss_line_id:
                    related_lines_to_delete.append(("stop_loss", stop_loss_line_id))
                    if hasattr(self, '_main_engine') and self._main_engine:
                        self._main_engine.write_log(
                            f"[持仓同步] 通过关联关系标记删除止损线: {stop_loss_line_id} (关联到入场线 {line_id})",
                            "Chart"
                        )
            
                # 标记止盈线
                take_profit_line_id = relations.get("take_profit")
                if take_profit_line_id:
                    related_lines_to_delete.append(("take_profit", take_profit_line_id))
                    if hasattr(self, '_main_engine') and self._main_engine:
                        self._main_engine.write_log(
                            f"[持仓同步] 通过关联关系标记删除止盈线: {take_profit_line_id} (关联到入场线 {line_id})",
                            "Chart"
                        )
        
            # 先删除关联的止损线和止盈线
            for relation_type, related_line_id in related_lines_to_delete:
                related_line = self._price_line_manager.get_line(related_line_id)
                if related_line:
                    # 从 plot 中移除
                    if related_line.scene() is not None and self._first_plot:
                        try:
                            self._first_plot.removeItem(related_line)
                        except Exception as e:
                            if hasattr(self, '_main_engine') and self._main_engine:
                                self._main_engine.write_log(
                                    f"[持仓同步] 从plot移除{relation_type}线 {related_line_id} 失败: {str(e)}",
                                    "Chart"
                                )
                
                    # 从管理器中删除
                    if self._price_line_manager.delete_line(related_line_id):
                        deleted_count += 1
                        # 清理数据库中的关联关系（通过关联线ID删除）
                        if hasattr(self, '_price_line_database') and self._price_line_database:
                            if hasattr(self._price_line_database, 'delete_relations_by_related_line_id'):
                                self._price_line_database.delete_relations_by_related_line_id(related_line_id)
                                if hasattr(self, '_main_engine') and self._main_engine:
                                    self._main_engine.write_log(
                                        f"[持仓同步] 已清理数据库中的{relation_type}线关联关系: {related_line_id}",
                                        "Chart"
                                    )
                    
                        if relation_type == "stop_loss":
                            deleted_stop_loss_count += 1
                            if hasattr(self, '_main_engine') and self._main_engine:
                                self._main_engine.write_log(
                                    f"[持仓同步] 已删除关联止损线: {related_line_id}",
                                    "Chart"
                                )
                        elif relation_type == "take_profit":
                            deleted_take_profit_count += 1
                            if hasattr(self, '_main_engine') and self._main_engine:
                                self._main_engine.write_log(
                                    f"[持仓同步] 已删除关联止盈线: {related_line_id}",
                                    "Chart"
                                )
                else:
                    if hasattr(self, '_main_engine') and self._main_engine:
                        self._main_engine.write_log(
                            f"[持仓同步] 警告：关联的{relation_type}线 {related_line_id} 不存在",
                            "Chart"
                        )
        
            # 删除入场线
            entry_line = self._price_line_manager.get_line(line_id)
            if entry_line:
                # 从 plot 中移除
                if entry_line.scene() is not None and self._first_plot:
                    try:
                        self._first_plot.removeItem(entry_line)
                    except Exception as e:
                        if hasattr(self, '_main_engine') and self._main_engine:
                            self._main_engine.write_log(
                                f"[持仓同步] 从plot移除入场线 {line_id} 失败: {str(e)}",
                                "Chart"
                            )
            
                # 从管理器中删除
                if self._price_line_manager.delete_line(line_id):
                    deleted_count += 1
                    deleted_entry_count += 1
                    if hasattr(self, '_main_engine') and self._main_engine:
                        self._main_engine.write_log(
                            f"[持仓同步] 已从plot中移除入场线: {line_id}",
                            "Chart"
                        )
                        self._main_engine.write_log(
                            f"[持仓同步] 已删除入场线: {line_id}",
                            "Chart"
                        )
                
                    # 清理关联关系
                    if hasattr(self, '_entry_line_relations') and line_id in self._entry_line_relations:
                        self._entry_line_relations.pop(line_id, None)
                        # 清理数据库中的关联关系
                        if self._price_line_database:
                            self._price_line_database.delete_all_relations(line_id)
                
                    # 清理订单映射
                    if hasattr(self, '_drawing_order_controller') and self._drawing_order_controller:
                        order_id = self._drawing_order_controller.get_order_id_for_line(line_id)
                        if order_id:
                            self._drawing_order_controller._line_order_map.pop(line_id, None)
                            self._drawing_order_controller._order_line_map.pop(order_id, None)
                        if hasattr(self._drawing_order_controller, '_pending_line_relations'):
                            self._drawing_order_controller._pending_line_relations.pop(line_id, None)
                
                    # 清理双击防抖记录
                    self._last_double_click_close.pop(line_id, None)
                else:
                    if hasattr(self, '_main_engine') and self._main_engine:
                        self._main_engine.write_log(
                            f"[持仓同步] 警告：删除入场线 {line_id} 失败",
                            "Chart"
                        )
            else:
                if hasattr(self, '_main_engine') and self._main_engine:
                    self._main_engine.write_log(
                        f"[持仓同步] 警告：入场线 {line_id} 不存在",
                        "Chart"
                    )
        
        # 删除后再次打印数据库状态（用于调试）
        # if hasattr(self, '_price_line_database') and self._price_line_database and hasattr(self, '_main_engine') and self._main_engine:
        #     debug_info = self._price_line_database.debug_print_all_lines_and_relations(vt_symbol=self._vt_symbol)
        #     self._main_engine.write_log(
        #         f"[持仓同步] 删除入场线后，数据库状态:\n{debug_info}",
        #         "ChartWidget"
        #     )
        
        # 注释盈亏更新完成日志，减少日志输出
        # if updated_count > 0 or deleted_count > 0:
        #     if hasattr(self, '_main_engine') and self._main_engine:
        #         self._main_engine.write_log(
        #             f"[持仓同步] 盈亏更新完成: 共更新 {updated_count} 条入场线，删除 {deleted_count} 条价格线 "
        #             f"(入场线={deleted_entry_count}, 止损线={deleted_stop_loss_count}, 止盈线={deleted_take_profit_count})",
        #             "ChartWidget"
        #         )
    
    
    def _load_position_holdings(self) -> None:
        """从数据库加载持仓记录（用于FIFO平仓）"""
        # TODO: 从 widget.py 复制完整实现（4152-4192行）
        # 这里先提供一个占位实现
        if not self._price_line_database or not self._vt_symbol:
            return
        
        # 加载所有方向的持仓记录
        for direction in ["long", "short"]:
            entries_data = self._price_line_database.load_position_entries(
                vt_symbol=self._vt_symbol,
                direction=direction
            )
            
            if not entries_data:
                continue
            
            # 创建或获取 PositionHolding
            if direction not in self._position_holdings:
                self._position_holdings[direction] = PositionHolding(direction)
            
            holding = self._position_holdings[direction]
            
            # 加载持仓记录（按成交时间排序，确保FIFO顺序）
            for entry_data in entries_data:
                line_id = entry_data["line_id"]
                
                # 验证入场线是否存在
                manager = self.get_price_line_manager()
                if manager and manager.get_line(line_id):
                    holding.add_entry(
                        line_id=line_id,
                        price=entry_data["price"],
                        volume=entry_data["volume"],
                        vt_orderid=entry_data["vt_orderid"],
                        trade_time=entry_data["trade_time"]
                    )
            
            if hasattr(self, '_main_engine') and self._main_engine and entries_data:
                self._main_engine.write_log(
                    f"[持仓同步] 从数据库加载了 {len(entries_data)} 条{direction}方向的持仓记录",
                    "Chart"
                )
    
    def _sync_position_on_load(self) -> None:
        """
        在加载价格线后同步当前持仓状态。
        如果某个方向的持仓为0，清除对应方向的入场线。
        """
        if not hasattr(self, '_main_engine') or not self._main_engine:
            return
        
        if not self._vt_symbol:
            return
        
        # 查询所有持仓
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
        
        # 检查每个方向的持仓，如果为0则清除对应方向的入场线
        manager = self.get_price_line_manager()
        if not manager:
            return
        
        all_lines = manager.get_all_lines()
        if not all_lines:
            return
        
        for direction in ["long", "short"]:
            position_volume = position_map.get(direction, 0.0)
            if position_volume <= 0:
                # 持仓为0，清除该方向的所有入场线
                if hasattr(self, '_main_engine') and self._main_engine:
                    self._main_engine.write_log(
                        f"[持仓同步] 加载时同步持仓：{direction}方向持仓为0，清除对应入场线",
                        "Chart"
                    )
                
                # 复用现有的清除逻辑：创建一个虚拟的持仓对象
                from vnpy.trader.object import PositionData
                from vnpy.trader.constant import Direction, Exchange
                
                # 解析exchange：优先从chart_vt_symbol解析，失败时从main_engine获取合约信息
                exchange = None
                if '.' in chart_vt_symbol:
                    exchange_str = chart_vt_symbol.split('.')[1]
                    try:
                        exchange = Exchange(exchange_str)
                    except ValueError:
                        # 解析失败，尝试从main_engine获取合约信息
                        if hasattr(self, '_main_engine') and self._main_engine:
                            try:
                                contract = self._main_engine.get_contract(chart_vt_symbol)
                                if contract:
                                    exchange = contract.exchange
                                    if hasattr(self, '_main_engine') and self._main_engine:
                                        self._main_engine.write_log(
                                            f"[持仓同步] 从合约信息获取exchange: {chart_vt_symbol} -> {exchange.value}",
                                            "Chart"
                                        )
                            except Exception as e:
                                if hasattr(self, '_main_engine') and self._main_engine:
                                    self._main_engine.write_log(
                                        f"[持仓同步] 警告: 无法从chart_vt_symbol或合约信息获取exchange: {chart_vt_symbol}, 错误: {str(e)}",
                                        "Chart"
                                    )
                
                # 如果仍然无法确定exchange，记录警告并使用默认值
                if exchange is None:
                    if hasattr(self, '_main_engine') and self._main_engine:
                        self._main_engine.write_log(
                            f"[持仓同步] 警告: 无法确定exchange，使用默认值SHFE（可能不正确）: {chart_vt_symbol}",
                            "Chart"
                        )
                    exchange = Exchange.HKFE  # 默认值，但会记录警告
                
                virtual_position = PositionData(
                    symbol=chart_vt_symbol.split('.')[0] if '.' in chart_vt_symbol else chart_vt_symbol,
                    exchange=exchange,
                    direction=Direction.LONG if direction == "long" else Direction.SHORT,
                    volume=0,
                    frozen=0,
                    price=0,
                    pnl=0,
                    gateway_name=""
                )
                
                # 调用现有的清除逻辑
                self._update_entry_line_pnl(virtual_position)

