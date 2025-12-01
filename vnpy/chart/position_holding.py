"""
持仓管理模块：支持多条入场线的合并显示和FIFO平仓逻辑。
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class EntryPosition:
    """单个入场持仓记录"""
    line_id: str  # 入场线ID
    price: float  # 入场价格
    volume: float  # 持仓手数
    vt_orderid: Optional[str] = None  # 关联的订单ID
    trade_time: Optional[datetime] = None  # 成交时间


class PositionHolding:
    """
    同方向的持仓管理类，支持FIFO（先进先出）平仓逻辑。
    
    维护多个入场持仓记录，计算加权平均价格，支持部分平仓。
    """
    
    def __init__(self, direction: str) -> None:
        """
        初始化持仓管理。
        
        Args:
            direction: 持仓方向 ("long" 或 "short")
        """
        self.direction = direction
        self._entries: list[EntryPosition] = []  # 按时间顺序存储的持仓记录（FIFO队列）
    
    def add_entry(self, line_id: str, price: float, volume: float, 
                  vt_orderid: Optional[str] = None, 
                  trade_time: Optional[datetime] = None) -> None:
        """
        添加入场持仓记录。
        
        Args:
            line_id: 入场线ID
            price: 入场价格
            volume: 持仓手数
            vt_orderid: 关联的订单ID
            trade_time: 成交时间
        """
        # 统一处理datetime：如果trade_time是aware的，转换为naive；如果是None，使用now()
        if trade_time is None:
            normalized_trade_time = datetime.now()
        else:
            # 如果trade_time是aware的（带时区信息），转换为naive
            if trade_time.tzinfo is not None:
                normalized_trade_time = trade_time.replace(tzinfo=None)
            else:
                normalized_trade_time = trade_time
        
        entry = EntryPosition(
            line_id=line_id,
            price=price,
            volume=volume,
            vt_orderid=vt_orderid,
            trade_time=normalized_trade_time
        )
        self._entries.append(entry)
        # 按成交时间排序，确保FIFO顺序
        # 使用统一的datetime.min作为默认值（naive）
        self._entries.sort(key=lambda x: x.trade_time if x.trade_time is not None else datetime.min)
    
    def close_position(self, close_volume: float) -> list[EntryPosition]:
        """
        按照FIFO原则平仓，返回被平掉的持仓记录列表。
        
        Args:
            close_volume: 平仓手数
            
        Returns:
            被平掉的持仓记录列表（可能包含部分平仓的记录）
        """
        closed_entries: list[EntryPosition] = []
        remaining_volume = close_volume
        
        # 按FIFO顺序平仓
        while remaining_volume > 0 and self._entries:
            entry = self._entries[0]
            
            if entry.volume <= remaining_volume:
                # 完全平掉这条持仓
                closed_entries.append(entry)
                remaining_volume -= entry.volume
                self._entries.pop(0)
            else:
                # 部分平仓：创建新的部分平仓记录，并更新原记录
                closed_entry = EntryPosition(
                    line_id=entry.line_id,
                    price=entry.price,
                    volume=remaining_volume,
                    vt_orderid=entry.vt_orderid,
                    trade_time=entry.trade_time
                )
                closed_entries.append(closed_entry)
                # 更新原记录的剩余手数
                entry.volume -= remaining_volume
                remaining_volume = 0
        
        return closed_entries
    
    def get_total_volume(self) -> float:
        """获取总持仓手数"""
        return sum(entry.volume for entry in self._entries)
    
    def get_average_price(self) -> float:
        """计算加权平均入场价格"""
        total_volume = self.get_total_volume()
        if total_volume == 0:
            return 0.0
        
        total_value = sum(entry.price * entry.volume for entry in self._entries)
        return total_value / total_volume
    
    def get_all_entries(self) -> list[EntryPosition]:
        """获取所有持仓记录"""
        return self._entries.copy()
    
    def get_entry_line_ids(self) -> list[str]:
        """获取所有入场线ID"""
        return [entry.line_id for entry in self._entries]
    
    def clear(self) -> None:
        """清空所有持仓记录"""
        self._entries.clear()
    
    def is_empty(self) -> bool:
        """检查是否为空"""
        return len(self._entries) == 0

