"""
持仓管理辅助方法：用于在 ChartWidget 中管理持仓记录。
"""

from datetime import datetime
from typing import Optional

from vnpy.trader.object import OrderData, PositionData

from .position_holding import PositionHolding, EntryPosition
from .price_line_database import PriceLineDatabase


def add_entry_to_holding(
    position_holdings: dict[str, PositionHolding],
    line_id: str,
    direction: str,
    price: float,
    volume: float,
    vt_orderid: Optional[str] = None,
    trade_time: Optional[datetime] = None,
    database: Optional[PriceLineDatabase] = None,
    vt_symbol: Optional[str] = None
) -> None:
    """
    添加持仓记录到持仓管理系统。
    
    Args:
        position_holdings: 持仓管理字典 (direction -> PositionHolding)
        line_id: 入场线ID
        direction: 持仓方向 ("long" 或 "short")
        price: 入场价格
        volume: 持仓手数
        vt_orderid: 关联的订单ID
        trade_time: 成交时间
        database: 可选的数据库实例（用于持久化）
        vt_symbol: VT符号（用于持久化）
    """
    if direction not in position_holdings:
        position_holdings[direction] = PositionHolding(direction)
    
    holding = position_holdings[direction]
    holding.add_entry(line_id, price, volume, vt_orderid, trade_time)
    
    # 保存到数据库（如果启用）
    if database and vt_symbol:
        database.save_position_entry(
            vt_symbol=vt_symbol,
            direction=direction,
            line_id=line_id,
            price=price,
            volume=volume,
            vt_orderid=vt_orderid,
            trade_time=trade_time
        )


def update_position_holding_from_order(
    position_holdings: dict[str, PositionHolding],
    order: OrderData,
    line_id: str
) -> None:
    """
    从订单数据更新持仓记录。
    
    Args:
        position_holdings: 持仓管理字典
        order: 订单数据
        line_id: 入场线ID
    """
    direction = "long" if order.direction.value == "多" else "short"
    add_entry_to_holding(
        position_holdings,
        line_id=line_id,
        direction=direction,
        price=order.price,
        volume=order.traded,
        vt_orderid=order.vt_orderid,
        trade_time=order.datetime
    )


def process_position_close(
    position_holdings: dict[str, PositionHolding],
    direction: str,
    close_volume: float,
    database: Optional[PriceLineDatabase] = None,
    vt_symbol: Optional[str] = None
) -> list[EntryPosition]:
    """
    处理持仓平仓（FIFO原则）。
    
    Args:
        position_holdings: 持仓管理字典
        direction: 持仓方向 ("long" 或 "short")
        close_volume: 平仓手数
        database: 可选的数据库实例（用于持久化）
        vt_symbol: VT符号（用于持久化）
        
    Returns:
        被平掉的持仓记录列表
    """
    if direction not in position_holdings:
        return []
    
    holding = position_holdings[direction]
    closed_entries = holding.close_position(close_volume)
    
    # 更新数据库（如果启用）
    if database and vt_symbol:
        for entry in closed_entries:
            # 检查是否完全平仓
            remaining_entries = holding.get_all_entries()
            entry_still_exists = any(e.line_id == entry.line_id for e in remaining_entries)
            
            if entry_still_exists:
                # 部分平仓：更新剩余手数
                remaining_entry = next((e for e in remaining_entries if e.line_id == entry.line_id), None)
                if remaining_entry:
                    database.update_position_entry_volume(
                        vt_symbol=vt_symbol,
                        direction=direction,
                        line_id=entry.line_id,
                        new_volume=remaining_entry.volume
                    )
            else:
                # 完全平仓：删除记录
                database.delete_position_entry(
                    vt_symbol=vt_symbol,
                    direction=direction,
                    line_id=entry.line_id
                )
    
    # 如果持仓为空，清理
    if holding.is_empty():
        position_holdings.pop(direction, None)
        # 从数据库删除该方向的所有记录
        if database and vt_symbol:
            database.delete_position_entries_by_symbol(vt_symbol, direction)
    
    return closed_entries

