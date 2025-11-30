"""
价格线数据库持久化测试用例。

使用 TDD 方式编写，测试价格线数据库的完整功能。
"""

import unittest
import tempfile
import os
from pathlib import Path
from datetime import datetime

from vnpy.chart.price_line_database import PriceLineDatabase
from vnpy.chart.price_line import PriceLineType


class TestPriceLineDatabase(unittest.TestCase):
    """价格线数据库测试类。"""
    
    def setUp(self) -> None:
        """每个测试前创建临时数据库。"""
        # 创建临时数据库文件
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        # 创建数据库实例
        self.db = PriceLineDatabase(self.db_path)
    
    def tearDown(self) -> None:
        """每个测试后清理临时数据库。"""
        # 关闭数据库连接
        if hasattr(self.db, '_get_connection'):
            conn = self.db._get_connection()
            conn.close()
        
        # 删除临时文件
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_init_tables(self) -> None:
        """测试数据库表初始化。"""
        # 验证表是否存在
        conn = self.db._get_connection()
        cursor = conn.cursor()
        
        # 检查 price_lines 表
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='price_lines'
        """)
        self.assertIsNotNone(cursor.fetchone())
        
        # 检查 price_line_relations 表
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='price_line_relations'
        """)
        self.assertIsNotNone(cursor.fetchone())
        
        # 检查索引
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name='idx_price_lines_vt_symbol'
        """)
        self.assertIsNotNone(cursor.fetchone())
        
        conn.close()
    
    def test_save_and_load_line(self) -> None:
        """测试保存和加载价格线。"""
        # 保存价格线
        result = self.db.save_line(
            line_id="line_1",
            price=25971.0,
            line_type=PriceLineType.ENTRY,
            direction="long",
            vt_symbol="MHImain.HKFE",
            movable=False,
            price_precision=0,
            vt_orderid="order_123"
        )
        self.assertTrue(result)
        
        # 加载价格线
        lines = self.db.load_lines()
        self.assertEqual(len(lines), 1)
        
        line = lines[0]
        self.assertEqual(line["line_id"], "line_1")
        self.assertEqual(line["price"], 25971.0)
        self.assertEqual(line["line_type"], PriceLineType.ENTRY)
        self.assertEqual(line["direction"], "long")
        self.assertEqual(line["vt_symbol"], "MHImain.HKFE")
        self.assertEqual(line["vt_orderid"], "order_123")
        self.assertFalse(line["movable"])
        self.assertEqual(line["price_precision"], 0)
        self.assertIn("created_at", line)
        self.assertIn("updated_at", line)
    
    def test_save_line_update_existing(self) -> None:
        """测试更新已存在的价格线。"""
        # 保存第一条价格线
        self.db.save_line(
            line_id="line_1",
            price=25971.0,
            line_type=PriceLineType.ENTRY,
            direction="long",
            vt_symbol="MHImain.HKFE"
        )
        
        # 获取创建时间
        lines = self.db.load_lines()
        original_created_at = lines[0]["created_at"]
        
        # 更新价格线
        self.db.save_line(
            line_id="line_1",
            price=25980.0,  # 更新价格
            line_type=PriceLineType.ENTRY,
            direction="long",
            vt_symbol="MHImain.HKFE"
        )
        
        # 验证更新
        lines = self.db.load_lines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["price"], 25980.0)
        # 创建时间应该保持不变
        self.assertEqual(lines[0]["created_at"], original_created_at)
        # 更新时间应该已更新
        self.assertNotEqual(lines[0]["updated_at"], original_created_at)
    
    def test_load_lines_filter_by_symbol(self) -> None:
        """测试按合约过滤加载价格线。"""
        # 保存多条价格线
        self.db.save_line("line_1", 25971.0, PriceLineType.ENTRY, "long", "MHImain.HKFE")
        self.db.save_line("line_2", 25980.0, PriceLineType.ENTRY, "short", "MHI2512.HKFE")
        self.db.save_line("line_3", 26000.0, PriceLineType.STOP_LOSS, "long", "MHImain.HKFE")
        
        # 按合约过滤
        lines = self.db.load_lines(vt_symbol="MHImain.HKFE")
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0]["line_id"], "line_1")
        self.assertEqual(lines[1]["line_id"], "line_3")
    
    def test_load_lines_filter_by_type(self) -> None:
        """测试按类型过滤加载价格线。"""
        # 保存多条价格线
        self.db.save_line("line_1", 25971.0, PriceLineType.ENTRY, "long", "MHImain.HKFE")
        self.db.save_line("line_2", 25950.0, PriceLineType.STOP_LOSS, "long", "MHImain.HKFE")
        self.db.save_line("line_3", 26000.0, PriceLineType.TAKE_PROFIT, "long", "MHImain.HKFE")
        
        # 按类型过滤
        lines = self.db.load_lines(line_type=PriceLineType.STOP_LOSS)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["line_id"], "line_2")
    
    def test_delete_line(self) -> None:
        """测试删除价格线。"""
        # 保存价格线
        self.db.save_line("line_1", 25971.0, PriceLineType.ENTRY, "long", "MHImain.HKFE")
        self.db.save_line("line_2", 25980.0, PriceLineType.ENTRY, "short", "MHImain.HKFE")
        
        # 删除一条
        result = self.db.delete_line("line_1")
        self.assertTrue(result)
        
        # 验证删除
        lines = self.db.load_lines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["line_id"], "line_2")
    
    def test_delete_nonexistent_line(self) -> None:
        """测试删除不存在的价格线。"""
        result = self.db.delete_line("nonexistent")
        self.assertFalse(result)
    
    def test_delete_lines_by_symbol(self) -> None:
        """测试删除指定合约的所有价格线。"""
        # 保存多条价格线
        self.db.save_line("line_1", 25971.0, PriceLineType.ENTRY, "long", "MHImain.HKFE")
        self.db.save_line("line_2", 25950.0, PriceLineType.STOP_LOSS, "long", "MHImain.HKFE")
        self.db.save_line("line_3", 25980.0, PriceLineType.ENTRY, "short", "MHI2512.HKFE")
        
        # 删除指定合约的价格线
        result = self.db.delete_lines_by_symbol("MHImain.HKFE")
        self.assertTrue(result)
        
        # 验证删除
        lines = self.db.load_lines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["line_id"], "line_3")
    
    def test_save_and_load_relation(self) -> None:
        """测试保存和加载价格线关联关系。"""
        # 先保存价格线
        self.db.save_line("entry_1", 25971.0, PriceLineType.ENTRY, "long", "MHImain.HKFE")
        self.db.save_line("stop_1", 25950.0, PriceLineType.STOP_LOSS, "long", "MHImain.HKFE")
        self.db.save_line("profit_1", 26000.0, PriceLineType.TAKE_PROFIT, "long", "MHImain.HKFE")
        
        # 保存关联关系
        result1 = self.db.save_relation("entry_1", "stop_1", "stop_loss")
        result2 = self.db.save_relation("entry_1", "profit_1", "take_profit")
        self.assertTrue(result1)
        self.assertTrue(result2)
        
        # 加载关联关系
        relations = self.db.load_relations(entry_line_id="entry_1")
        self.assertEqual(len(relations), 2)
        
        # 验证关联关系
        relation_types = {rel["relation_type"] for rel in relations}
        self.assertIn("stop_loss", relation_types)
        self.assertIn("take_profit", relation_types)
    
    def test_get_related_lines(self) -> None:
        """测试获取入场线关联的止损/止盈线。"""
        # 先保存价格线
        self.db.save_line("entry_1", 25971.0, PriceLineType.ENTRY, "long", "MHImain.HKFE")
        self.db.save_line("stop_1", 25950.0, PriceLineType.STOP_LOSS, "long", "MHImain.HKFE")
        self.db.save_line("profit_1", 26000.0, PriceLineType.TAKE_PROFIT, "long", "MHImain.HKFE")
        
        # 保存关联关系
        self.db.save_relation("entry_1", "stop_1", "stop_loss")
        self.db.save_relation("entry_1", "profit_1", "take_profit")
        
        # 获取关联线
        related = self.db.get_related_lines("entry_1")
        self.assertEqual(related["stop_loss"], "stop_1")
        self.assertEqual(related["take_profit"], "profit_1")
    
    def test_delete_relation(self) -> None:
        """测试删除价格线关联关系。"""
        # 先保存价格线和关联关系
        self.db.save_line("entry_1", 25971.0, PriceLineType.ENTRY, "long", "MHImain.HKFE")
        self.db.save_line("stop_1", 25950.0, PriceLineType.STOP_LOSS, "long", "MHImain.HKFE")
        self.db.save_line("profit_1", 26000.0, PriceLineType.TAKE_PROFIT, "long", "MHImain.HKFE")
        self.db.save_relation("entry_1", "stop_1", "stop_loss")
        self.db.save_relation("entry_1", "profit_1", "take_profit")
        
        # 删除指定类型的关联
        result = self.db.delete_relation("entry_1", "stop_loss")
        self.assertTrue(result)
        
        # 验证删除
        relations = self.db.load_relations(entry_line_id="entry_1")
        self.assertEqual(len(relations), 1)
        self.assertEqual(relations[0]["relation_type"], "take_profit")
    
    def test_delete_all_relations(self) -> None:
        """测试删除入场线的所有关联关系。"""
        # 先保存价格线和关联关系
        self.db.save_line("entry_1", 25971.0, PriceLineType.ENTRY, "long", "MHImain.HKFE")
        self.db.save_line("stop_1", 25950.0, PriceLineType.STOP_LOSS, "long", "MHImain.HKFE")
        self.db.save_line("profit_1", 26000.0, PriceLineType.TAKE_PROFIT, "long", "MHImain.HKFE")
        self.db.save_relation("entry_1", "stop_1", "stop_loss")
        self.db.save_relation("entry_1", "profit_1", "take_profit")
        
        # 删除所有关联
        result = self.db.delete_relation("entry_1")
        self.assertTrue(result)
        
        # 验证删除
        relations = self.db.load_relations(entry_line_id="entry_1")
        self.assertEqual(len(relations), 0)
    
    def test_cascade_delete(self) -> None:
        """测试级联删除：删除入场线时，关联关系也应该被删除。"""
        # 先保存价格线和关联关系
        self.db.save_line("entry_1", 25971.0, PriceLineType.ENTRY, "long", "MHImain.HKFE")
        self.db.save_line("stop_1", 25950.0, PriceLineType.STOP_LOSS, "long", "MHImain.HKFE")
        self.db.save_relation("entry_1", "stop_1", "stop_loss")
        
        # 删除入场线
        self.db.delete_line("entry_1")
        
        # 验证关联关系也被删除（由于外键约束）
        relations = self.db.load_relations(entry_line_id="entry_1")
        self.assertEqual(len(relations), 0)
    
    def test_all_line_types(self) -> None:
        """测试所有价格线类型都能正确保存和加载。"""
        line_types = [
            PriceLineType.ENTRY,
            PriceLineType.PENDING,
            PriceLineType.STOP_LOSS,
            PriceLineType.TAKE_PROFIT,
            PriceLineType.PREVIEW
        ]
        
        for i, line_type in enumerate(line_types):
            self.db.save_line(
                f"line_{i}",
                25971.0 + i,
                line_type,
                "long",
                "MHImain.HKFE"
            )
        
        # 验证所有类型都能加载
        lines = self.db.load_lines()
        self.assertEqual(len(lines), len(line_types))
        
        loaded_types = {line["line_type"] for line in lines}
        self.assertEqual(loaded_types, set(line_types))
    
    def test_movable_flag(self) -> None:
        """测试可拖拽标志的保存和加载。"""
        # 保存可拖拽的价格线
        self.db.save_line(
            "line_1",
            25971.0,
            PriceLineType.STOP_LOSS,
            "long",
            "MHImain.HKFE",
            movable=True
        )
        
        # 保存不可拖拽的价格线
        self.db.save_line(
            "line_2",
            25980.0,
            PriceLineType.ENTRY,
            "long",
            "MHImain.HKFE",
            movable=False
        )
        
        # 验证
        lines = self.db.load_lines()
        self.assertTrue(lines[0]["movable"])
        self.assertFalse(lines[1]["movable"])
    
    def test_price_precision(self) -> None:
        """测试价格精度的保存和加载。"""
        # 保存不同精度的价格线
        self.db.save_line(
            "line_1",
            25971.0,
            PriceLineType.ENTRY,
            "long",
            "MHImain.HKFE",
            price_precision=0
        )
        
        self.db.save_line(
            "line_2",
            25971.123,
            PriceLineType.ENTRY,
            "long",
            "MHImain.HKFE",
            price_precision=3
        )
        
        # 验证
        lines = self.db.load_lines()
        self.assertEqual(lines[0]["price_precision"], 0)
        self.assertEqual(lines[1]["price_precision"], 3)


if __name__ == "__main__":
    unittest.main()

