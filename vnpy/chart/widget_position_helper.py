"""
持仓管理辅助方法：用于在 ChartWidget 中管理持仓记录。
"""

from datetime import datetime
from typing import Optional

from vnpy.trader.object import OrderData, PositionData

from .position_holding import PositionHolding, EntryPosition


def add_entry_to_holding(
    position_holdings: dict[str, PositionHolding],
    line_id: str,
    direction: str,
    price: float,
    volume: float,
    vt_orderid: Optional[str] = None,
    trade_time: Optional[datetime] = None
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
    """
    if direction not in position_holdings:
        position_holdings[direction] = PositionHolding(direction)
    
    holding = position_holdings[direction]
    holding.add_entry(line_id, price, volume, vt_orderid, trade_time)


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
    close_volume: float
) -> list[EntryPosition]:
    """
    处理持仓平仓（FIFO原则）。
    
    Args:
        position_holdings: 持仓管理字典
        direction: 持仓方向 ("long" 或 "short")
        close_volume: 平仓手数
        
    Returns:
        被平掉的持仓记录列表
    """
    if direction not in position_holdings:
        return []
    
    holding = position_holdings[direction]
    closed_entries = holding.close_position(close_volume)
    
    # 如果持仓为空，清理
    if holding.is_empty():
        position_holdings.pop(direction, None)
    
    return closed_entries

