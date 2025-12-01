"""
持仓管理系统测试用例

测试覆盖：
- PositionHolding 类的基本功能
- FIFO（先进先出）平仓逻辑
- 加权平均价格计算
- 持仓记录管理
- 合并显示逻辑
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

from vnpy.chart.position_holding import PositionHolding, EntryPosition
from vnpy.chart.widget_position_helper import (
    add_entry_to_holding,
    update_position_holding_from_order,
    process_position_close
)
from vnpy.trader.object import OrderData
from vnpy.trader.constant import Direction, Status, Exchange, OrderType, Offset


class TestEntryPosition:
    """测试 EntryPosition 数据类"""
    
    def test_create_entry_position(self):
        """测试创建入场持仓记录"""
        entry = EntryPosition(
            line_id="line_1",
            price=26040.0,
            volume=1.0,
            vt_orderid="FUTU.12345",
            trade_time=datetime.now()
        )
        
        assert entry.line_id == "line_1"
        assert entry.price == 26040.0
        assert entry.volume == 1.0
        assert entry.vt_orderid == "FUTU.12345"
        assert entry.trade_time is not None


class TestPositionHolding:
    """测试 PositionHolding 类"""
    
    def test_create_position_holding(self):
        """测试创建持仓管理对象"""
        holding = PositionHolding("long")
        
        assert holding.direction == "long"
        assert holding.is_empty()
        assert holding.get_total_volume() == 0.0
        assert holding.get_average_price() == 0.0
    
    def test_add_entry(self):
        """测试添加入场持仓记录"""
        holding = PositionHolding("long")
        
        holding.add_entry("line_1", 26040.0, 1.0, "FUTU.12345", datetime.now())
        
        assert not holding.is_empty()
        assert holding.get_total_volume() == 1.0
        assert holding.get_average_price() == 26040.0
        assert holding.get_entry_line_ids() == ["line_1"]
    
    def test_add_multiple_entries(self):
        """测试添加多个入场持仓记录"""
        holding = PositionHolding("long")
        
        t1 = datetime.now()
        t2 = t1 + timedelta(seconds=1)
        t3 = t1 + timedelta(seconds=2)
        
        holding.add_entry("line_1", 26040.0, 1.0, "FUTU.12345", t1)
        holding.add_entry("line_2", 26050.0, 1.0, "FUTU.12346", t2)
        holding.add_entry("line_3", 26030.0, 1.0, "FUTU.12347", t3)
        
        assert holding.get_total_volume() == 3.0
        # 加权平均价格 = (26040*1 + 26050*1 + 26030*1) / 3 = 26040.0
        assert abs(holding.get_average_price() - 26040.0) < 0.01
        assert len(holding.get_entry_line_ids()) == 3
    
    def test_fifo_close_position_full(self):
        """测试FIFO平仓：完全平掉第一条持仓"""
        holding = PositionHolding("long")
        
        t1 = datetime.now()
        t2 = t1 + timedelta(seconds=1)
        
        holding.add_entry("line_1", 26040.0, 1.0, "FUTU.12345", t1)
        holding.add_entry("line_2", 26050.0, 1.0, "FUTU.12346", t2)
        
        # 平掉1手（应该平掉line_1）
        closed_entries = holding.close_position(1.0)
        
        assert len(closed_entries) == 1
        assert closed_entries[0].line_id == "line_1"
        assert closed_entries[0].volume == 1.0
        assert holding.get_total_volume() == 1.0
        assert holding.get_entry_line_ids() == ["line_2"]
    
    def test_fifo_close_position_partial(self):
        """测试FIFO平仓：部分平掉第一条持仓"""
        holding = PositionHolding("long")
        
        t1 = datetime.now()
        t2 = t1 + timedelta(seconds=1)
        
        holding.add_entry("line_1", 26040.0, 2.0, "FUTU.12345", t1)
        holding.add_entry("line_2", 26050.0, 1.0, "FUTU.12346", t2)
        
        # 平掉0.5手（应该部分平掉line_1）
        closed_entries = holding.close_position(0.5)
        
        assert len(closed_entries) == 1
        assert closed_entries[0].line_id == "line_1"
        assert closed_entries[0].volume == 0.5
        assert holding.get_total_volume() == 2.5  # 2.0 - 0.5 + 1.0
        assert holding.get_entry_line_ids() == ["line_1", "line_2"]
        
        # 检查剩余持仓
        remaining_entries = holding.get_all_entries()
        assert remaining_entries[0].line_id == "line_1"
        assert remaining_entries[0].volume == 1.5  # 2.0 - 0.5
    
    def test_fifo_close_position_multiple(self):
        """测试FIFO平仓：平掉多条持仓"""
        holding = PositionHolding("long")
        
        t1 = datetime.now()
        t2 = t1 + timedelta(seconds=1)
        t3 = t1 + timedelta(seconds=2)
        
        holding.add_entry("line_1", 26040.0, 1.0, "FUTU.12345", t1)
        holding.add_entry("line_2", 26050.0, 1.0, "FUTU.12346", t2)
        holding.add_entry("line_3", 26030.0, 1.0, "FUTU.12347", t3)
        
        # 平掉2.5手（应该平掉line_1和line_2的全部，以及line_3的部分）
        closed_entries = holding.close_position(2.5)
        
        assert len(closed_entries) == 3
        assert closed_entries[0].line_id == "line_1"
        assert closed_entries[0].volume == 1.0
        assert closed_entries[1].line_id == "line_2"
        assert closed_entries[1].volume == 1.0
        assert closed_entries[2].line_id == "line_3"
        assert closed_entries[2].volume == 0.5
        
        assert holding.get_total_volume() == 0.5
        assert holding.get_entry_line_ids() == ["line_3"]
        
        # 检查剩余持仓
        remaining_entries = holding.get_all_entries()
        assert remaining_entries[0].line_id == "line_3"
        assert remaining_entries[0].volume == 0.5
    
    def test_average_price_calculation(self):
        """测试加权平均价格计算"""
        holding = PositionHolding("long")
        
        # 添加不同价格的持仓
        holding.add_entry("line_1", 26040.0, 1.0, "FUTU.12345", datetime.now())
        holding.add_entry("line_2", 26050.0, 2.0, "FUTU.12346", datetime.now())
        holding.add_entry("line_3", 26030.0, 1.0, "FUTU.12347", datetime.now())
        
        # 加权平均价格 = (26040*1 + 26050*2 + 26030*1) / 4 = 26042.5
        expected_avg = (26040.0 * 1.0 + 26050.0 * 2.0 + 26030.0 * 1.0) / 4.0
        assert abs(holding.get_average_price() - expected_avg) < 0.01
    
    def test_clear_holding(self):
        """测试清空持仓记录"""
        holding = PositionHolding("long")
        
        holding.add_entry("line_1", 26040.0, 1.0, "FUTU.12345", datetime.now())
        holding.add_entry("line_2", 26050.0, 1.0, "FUTU.12346", datetime.now())
        
        assert not holding.is_empty()
        assert holding.get_total_volume() == 2.0
        
        holding.clear()
        
        assert holding.is_empty()
        assert holding.get_total_volume() == 0.0
        assert holding.get_average_price() == 0.0
    
    def test_entry_sorting_by_time(self):
        """测试持仓记录按时间排序（FIFO顺序）"""
        holding = PositionHolding("long")
        
        t1 = datetime.now()
        t2 = t1 + timedelta(seconds=2)  # 后添加
        t3 = t1 + timedelta(seconds=1)  # 中间添加
        
        # 按乱序添加
        holding.add_entry("line_2", 26050.0, 1.0, "FUTU.12346", t2)
        holding.add_entry("line_1", 26040.0, 1.0, "FUTU.12345", t1)
        holding.add_entry("line_3", 26030.0, 1.0, "FUTU.12347", t3)
        
        # 应该按时间排序
        entry_line_ids = holding.get_entry_line_ids()
        assert entry_line_ids == ["line_1", "line_3", "line_2"]


class TestPositionHoldingHelper:
    """测试持仓管理辅助函数"""
    
    def test_add_entry_to_holding(self):
        """测试添加持仓记录到持仓管理系统"""
        position_holdings = {}
        
        add_entry_to_holding(
            position_holdings,
            line_id="line_1",
            direction="long",
            price=26040.0,
            volume=1.0,
            vt_orderid="FUTU.12345",
            trade_time=datetime.now()
        )
        
        assert "long" in position_holdings
        holding = position_holdings["long"]
        assert holding.get_total_volume() == 1.0
        assert holding.get_average_price() == 26040.0
    
    def test_update_position_holding_from_order(self):
        """测试从订单数据更新持仓记录"""
        position_holdings = {}
        
        # 创建模拟订单
        order = Mock(spec=OrderData)
        order.direction = Direction.LONG
        order.price = 26040.0
        order.traded = 1.0
        order.vt_orderid = "FUTU.12345"
        order.datetime = datetime.now()
        
        update_position_holding_from_order(position_holdings, order, "line_1")
        
        assert "long" in position_holdings
        holding = position_holdings["long"]
        assert holding.get_total_volume() == 1.0
        assert holding.get_average_price() == 26040.0
    
    def test_process_position_close(self):
        """测试处理持仓平仓（FIFO）"""
        position_holdings = {}
        
        # 添加持仓记录
        holding = PositionHolding("long")
        t1 = datetime.now()
        t2 = t1 + timedelta(seconds=1)
        holding.add_entry("line_1", 26040.0, 1.0, "FUTU.12345", t1)
        holding.add_entry("line_2", 26050.0, 1.0, "FUTU.12346", t2)
        position_holdings["long"] = holding
        
        # 平掉1手
        closed_entries = process_position_close(position_holdings, "long", 1.0)
        
        assert len(closed_entries) == 1
        assert closed_entries[0].line_id == "line_1"
        assert position_holdings["long"].get_total_volume() == 1.0
    
    def test_process_position_close_empty(self):
        """测试处理持仓平仓：持仓为空时"""
        position_holdings = {}
        
        # 平掉不存在的持仓
        closed_entries = process_position_close(position_holdings, "long", 1.0)
        
        assert len(closed_entries) == 0
        assert "long" not in position_holdings
    
    def test_process_position_close_all(self):
        """测试处理持仓平仓：平掉所有持仓"""
        position_holdings = {}
        
        # 添加持仓记录
        holding = PositionHolding("long")
        holding.add_entry("line_1", 26040.0, 1.0, "FUTU.12345", datetime.now())
        position_holdings["long"] = holding
        
        # 平掉所有持仓
        closed_entries = process_position_close(position_holdings, "long", 1.0)
        
        assert len(closed_entries) == 1
        assert "long" not in position_holdings  # 持仓为空，应该被清理


class TestPositionHoldingIntegration:
    """测试持仓管理系统集成场景"""
    
    def test_multiple_entries_merge_display(self):
        """测试多条入场线合并显示场景"""
        holding = PositionHolding("long")
        
        # 模拟两次开仓
        t1 = datetime.now()
        t2 = t1 + timedelta(seconds=1)
        
        holding.add_entry("line_1", 26040.0, 1.0, "FUTU.12345", t1)
        holding.add_entry("line_2", 26050.0, 1.0, "FUTU.12346", t2)
        
        # 应该显示加权平均价格
        avg_price = holding.get_average_price()
        expected_avg = (26040.0 + 26050.0) / 2.0
        assert abs(avg_price - expected_avg) < 0.01
        
        # 总手数应该是2
        assert holding.get_total_volume() == 2.0
        
        # 应该保留所有入场线ID
        assert len(holding.get_entry_line_ids()) == 2
    
    def test_fifo_close_partial_position(self):
        """测试FIFO部分平仓场景：2手多仓，平掉1手"""
        holding = PositionHolding("long")
        
        t1 = datetime.now()
        t2 = t1 + timedelta(seconds=1)
        
        # 第一次开仓：1手@26040
        holding.add_entry("line_1", 26040.0, 1.0, "FUTU.12345", t1)
        # 第二次开仓：1手@26050
        holding.add_entry("line_2", 26050.0, 1.0, "FUTU.12346", t2)
        
        # 平掉1手（应该平掉line_1）
        closed_entries = holding.close_position(1.0)
        
        assert len(closed_entries) == 1
        assert closed_entries[0].line_id == "line_1"
        assert closed_entries[0].price == 26040.0
        
        # 剩余持仓应该是line_2
        assert holding.get_total_volume() == 1.0
        assert holding.get_entry_line_ids() == ["line_2"]
        assert holding.get_average_price() == 26050.0
    
    def test_fifo_close_with_different_volumes(self):
        """测试FIFO平仓：不同手数的持仓"""
        holding = PositionHolding("long")
        
        t1 = datetime.now()
        t2 = t1 + timedelta(seconds=1)
        t3 = t1 + timedelta(seconds=2)
        
        # 添加不同手数的持仓
        holding.add_entry("line_1", 26040.0, 2.0, "FUTU.12345", t1)  # 2手
        holding.add_entry("line_2", 26050.0, 1.0, "FUTU.12346", t2)  # 1手
        holding.add_entry("line_3", 26030.0, 3.0, "FUTU.12347", t3)  # 3手
        
        # 平掉4手（应该平掉line_1的全部2手，line_2的全部1手，line_3的1手）
        closed_entries = holding.close_position(4.0)
        
        assert len(closed_entries) == 3
        assert closed_entries[0].volume == 2.0  # line_1全部
        assert closed_entries[1].volume == 1.0  # line_2全部
        assert closed_entries[2].volume == 1.0  # line_3部分
        
        # 剩余持仓应该是line_3的2手
        assert holding.get_total_volume() == 2.0
        assert holding.get_entry_line_ids() == ["line_3"]
        assert holding.get_average_price() == 26030.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

