"""
测试价格线ID去重和PositionHolding持久化功能。
"""

import unittest
import tempfile
import os
from datetime import datetime

from vnpy.chart.price_line_database import PriceLineDatabase
from vnpy.chart.price_line import PriceLineManager, PriceLineType
from vnpy.chart.position_holding import PositionHolding
from vnpy.chart.widget_position_helper import add_entry_to_holding, process_position_close


class TestPriceLineIDAndPositionPersistence(unittest.TestCase):
    """测试ID去重和PositionHolding持久化"""
    
    def setUp(self):
        """创建临时数据库"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        self.database = PriceLineDatabase(db_path=self.db_path)
        self.vt_symbol = "TEST.HKFE"
    
    def tearDown(self):
        """清理临时文件"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_uuid_id_generation(self):
        """测试UUID ID生成（默认模式）"""
        manager = PriceLineManager(database=self.database, vt_symbol=self.vt_symbol, use_uuid=True)
        
        # 创建多条价格线
        line_ids = []
        for i in range(5):
            line_id = manager.create_line(
                price=100.0 + i,
                line_type=PriceLineType.ENTRY,
                direction="long"
            )
            line_ids.append(line_id)
        
        # 验证所有ID都是唯一的
        self.assertEqual(len(line_ids), len(set(line_ids)), "所有ID应该是唯一的")
        
        # 验证ID格式（应该包含UUID的hex字符）
        for line_id in line_ids:
            self.assertTrue(line_id.startswith("line_"), f"ID应该以'line_'开头: {line_id}")
            self.assertGreater(len(line_id), 10, f"ID应该足够长: {line_id}")
    
    def test_counter_id_with_database_init(self):
        """测试计数器ID模式，从数据库加载后初始化计数器"""
        manager = PriceLineManager(database=self.database, vt_symbol=self.vt_symbol, use_uuid=False)
        
        # 创建一些价格线并保存到数据库
        line_ids = []
        for i in range(3):
            line_id = manager.create_line(
                price=100.0 + i,
                line_type=PriceLineType.ENTRY,
                direction="long"
            )
            line_ids.append(line_id)
        
        # 创建新的管理器（模拟重启）
        new_manager = PriceLineManager(database=self.database, vt_symbol=self.vt_symbol, use_uuid=False)
        
        # 从数据库加载（不传入plot，避免Qt依赖）
        new_manager.load_from_database(plot=None)
        
        # 创建新的价格线，应该从最大ID+1开始
        new_line_id = new_manager.create_line(
            price=200.0,
            line_type=PriceLineType.ENTRY,
            direction="long"
        )
        
        # 验证新ID不会与已存在的ID冲突
        all_line_ids = list(new_manager.get_all_lines().keys())
        self.assertIn(new_line_id, all_line_ids, "新创建的ID应该存在")
        self.assertNotIn(new_line_id, line_ids, "新ID不应该与旧ID冲突")
        
        # 验证新ID的计数器值应该大于旧ID的最大值
        old_max = max(int(line_id.split("_")[1]) for line_id in line_ids if line_id.split("_")[1].isdigit())
        new_counter = int(new_line_id.split("_")[1])
        self.assertGreater(new_counter, old_max, "新计数器应该大于旧的最大值")
    
    def test_position_entry_persistence(self):
        """测试持仓记录持久化"""
        # 保存持仓记录
        line_id1 = "line_001"
        line_id2 = "line_002"
        
        self.database.save_position_entry(
            vt_symbol=self.vt_symbol,
            direction="long",
            line_id=line_id1,
            price=100.0,
            volume=2.0,
            vt_orderid="order_001",
            trade_time=datetime(2024, 1, 1, 10, 0, 0)
        )
        
        self.database.save_position_entry(
            vt_symbol=self.vt_symbol,
            direction="long",
            line_id=line_id2,
            price=101.0,
            volume=1.0,
            vt_orderid="order_002",
            trade_time=datetime(2024, 1, 1, 11, 0, 0)
        )
        
        # 加载持仓记录
        entries = self.database.load_position_entries(
            vt_symbol=self.vt_symbol,
            direction="long"
        )
        
        # 验证加载的数据
        self.assertEqual(len(entries), 2, "应该加载2条持仓记录")
        
        # 验证第一条记录（按时间排序）
        entry1 = entries[0]
        self.assertEqual(entry1["line_id"], line_id1)
        self.assertEqual(entry1["price"], 100.0)
        self.assertEqual(entry1["volume"], 2.0)
        self.assertEqual(entry1["vt_orderid"], "order_001")
        
        # 验证第二条记录
        entry2 = entries[1]
        self.assertEqual(entry2["line_id"], line_id2)
        self.assertEqual(entry2["price"], 101.0)
        self.assertEqual(entry2["volume"], 1.0)
    
    def test_position_holding_fifo_persistence(self):
        """测试PositionHolding FIFO持久化（完整流程）"""
        # 创建持仓记录
        position_holdings = {}
        
        # 添加第一条持仓
        add_entry_to_holding(
            position_holdings,
            line_id="line_001",
            direction="long",
            price=100.0,
            volume=2.0,
            vt_orderid="order_001",
            trade_time=datetime(2024, 1, 1, 10, 0, 0),
            database=self.database,
            vt_symbol=self.vt_symbol
        )
        
        # 添加第二条持仓
        add_entry_to_holding(
            position_holdings,
            line_id="line_002",
            direction="long",
            price=101.0,
            volume=1.0,
            vt_orderid="order_002",
            trade_time=datetime(2024, 1, 1, 11, 0, 0),
            database=self.database,
            vt_symbol=self.vt_symbol
        )
        
        # 验证持仓记录已保存到数据库
        entries = self.database.load_position_entries(
            vt_symbol=self.vt_symbol,
            direction="long"
        )
        self.assertEqual(len(entries), 2, "应该有2条持仓记录")
        
        # 部分平仓（FIFO：先平第一条）
        closed_entries = process_position_close(
            position_holdings,
            direction="long",
            close_volume=1.5,
            database=self.database,
            vt_symbol=self.vt_symbol
        )
        
        # 验证平仓结果
        self.assertEqual(len(closed_entries), 2, "应该平掉2条记录（第一条完全平仓，第二条部分平仓）")
        self.assertEqual(closed_entries[0].line_id, "line_001", "第一条应该完全平仓")
        self.assertEqual(closed_entries[0].volume, 2.0, "第一条应该平掉2手")
        self.assertEqual(closed_entries[1].line_id, "line_002", "第二条应该部分平仓")
        self.assertEqual(closed_entries[1].volume, 0.5, "第二条应该平掉0.5手")
        
        # 验证数据库中的剩余持仓
        remaining_entries = self.database.load_position_entries(
            vt_symbol=self.vt_symbol,
            direction="long"
        )
        self.assertEqual(len(remaining_entries), 1, "应该还有1条持仓记录")
        self.assertEqual(remaining_entries[0]["line_id"], "line_002", "剩余记录应该是第二条")
        self.assertEqual(remaining_entries[0]["volume"], 0.5, "剩余手数应该是0.5")
    
    def test_position_holding_restore_after_restart(self):
        """测试重启后恢复PositionHolding（模拟完整场景）"""
        # 第一步：创建并保存持仓记录
        position_holdings1 = {}
        add_entry_to_holding(
            position_holdings1,
            line_id="line_001",
            direction="long",
            price=100.0,
            volume=2.0,
            trade_time=datetime(2024, 1, 1, 10, 0, 0),
            database=self.database,
            vt_symbol=self.vt_symbol
        )
        add_entry_to_holding(
            position_holdings1,
            line_id="line_002",
            direction="long",
            price=101.0,
            volume=1.0,
            trade_time=datetime(2024, 1, 1, 11, 0, 0),
            database=self.database,
            vt_symbol=self.vt_symbol
        )
        
        # 第二步：模拟重启，从数据库恢复
        position_holdings2 = {}
        entries = self.database.load_position_entries(
            vt_symbol=self.vt_symbol,
            direction="long"
        )
        
        # 恢复PositionHolding
        if "long" not in position_holdings2:
            position_holdings2["long"] = PositionHolding("long")
        
        holding = position_holdings2["long"]
        for entry_data in entries:
            holding.add_entry(
                line_id=entry_data["line_id"],
                price=entry_data["price"],
                volume=entry_data["volume"],
                vt_orderid=entry_data["vt_orderid"],
                trade_time=entry_data["trade_time"]
            )
        
        # 验证恢复的数据
        self.assertEqual(holding.get_total_volume(), 3.0, "总手数应该是3.0")
        self.assertEqual(len(holding.get_all_entries()), 2, "应该有2条持仓记录")
        
        # 验证FIFO顺序（按成交时间排序）
        all_entries = holding.get_all_entries()
        self.assertEqual(all_entries[0].line_id, "line_001", "第一条应该是line_001")
        self.assertEqual(all_entries[1].line_id, "line_002", "第二条应该是line_002")
        
        # 第三步：验证FIFO平仓仍然正确
        closed_entries = process_position_close(
            position_holdings2,
            direction="long",
            close_volume=1.0,
            database=self.database,
            vt_symbol=self.vt_symbol
        )
        
        # 应该先平第一条（FIFO）
        self.assertEqual(len(closed_entries), 1, "应该平掉1条记录")
        self.assertEqual(closed_entries[0].line_id, "line_001", "应该先平第一条")
        self.assertEqual(closed_entries[0].volume, 1.0, "应该平掉1手")
        
        # 验证剩余持仓
        remaining_entries = holding.get_all_entries()
        self.assertEqual(len(remaining_entries), 2, "应该还有2条记录（第一条部分剩余，第二条完整）")
        self.assertEqual(remaining_entries[0].volume, 1.0, "第一条剩余1手")
        self.assertEqual(remaining_entries[1].volume, 1.0, "第二条完整1手")
    
    def test_position_entry_update_volume(self):
        """测试更新持仓手数（部分平仓）"""
        # 创建持仓记录
        self.database.save_position_entry(
            vt_symbol=self.vt_symbol,
            direction="long",
            line_id="line_001",
            price=100.0,
            volume=2.0
        )
        
        # 更新手数（部分平仓）
        self.database.update_position_entry_volume(
            vt_symbol=self.vt_symbol,
            direction="long",
            line_id="line_001",
            new_volume=1.0
        )
        
        # 验证更新
        entries = self.database.load_position_entries(
            vt_symbol=self.vt_symbol,
            direction="long"
        )
        self.assertEqual(len(entries), 1, "应该有1条记录")
        self.assertEqual(entries[0]["volume"], 1.0, "手数应该更新为1.0")
    
    def test_position_entry_delete(self):
        """测试删除持仓记录（完全平仓）"""
        # 创建持仓记录
        self.database.save_position_entry(
            vt_symbol=self.vt_symbol,
            direction="long",
            line_id="line_001",
            price=100.0,
            volume=2.0
        )
        
        # 删除记录
        result = self.database.delete_position_entry(
            vt_symbol=self.vt_symbol,
            direction="long",
            line_id="line_001"
        )
        
        self.assertTrue(result, "删除应该成功")
        
        # 验证删除
        entries = self.database.load_position_entries(
            vt_symbol=self.vt_symbol,
            direction="long"
        )
        self.assertEqual(len(entries), 0, "应该没有记录")


if __name__ == '__main__':
    unittest.main()

