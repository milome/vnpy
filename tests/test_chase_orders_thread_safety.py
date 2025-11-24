"""
测试 chase_orders 数据结构的线程安全性

测试覆盖：
1. 线程安全的访问方法
2. 订单号变更时的一致性保证
3. original_order_time 和 order_time 的正确使用
4. 多线程并发访问
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from threading import Thread
import time
from typing import List

from vnpy.trader.constant import Direction, Exchange, Offset, OrderType as VtOrderType, Status
from vnpy.trader.object import OrderData, OrderRequest, CancelRequest
from vnpy_futu.vnpy_futu.futu_gateway import FutuGateway, ChaseOrder, ChaseConfig
from vnpy.event import EventEngine


class TestChaseOrdersThreadSafety(unittest.TestCase):
    """测试 chase_orders 的线程安全性"""
    
    def setUp(self):
        """设置测试环境"""
        self.event_engine = Mock(spec=EventEngine)
        self.gateway = FutuGateway(self.event_engine, "FUTU")
        # 模拟连接状态，避免实际连接
        self.gateway.quote_ctx = None
        self.gateway.trade_ctx = None
    
    def test_chase_order_original_fields(self):
        """测试 ChaseOrder 的原始字段"""
        config = ChaseConfig("_Retry2")
        chase_order = ChaseOrder(
            orderid="ORDER001",
            original_price=100.0,
            config=config,
            symbol="MHI2511",
            exchange=Exchange.HKFE,
            direction=Direction.LONG,
            offset=Offset.OPEN,
            volume=1,
            reference="_Retry2"
        )
        
        # 验证原始字段
        self.assertEqual(chase_order.original_orderid, "ORDER001")
        self.assertEqual(chase_order.orderid, "ORDER001")
        self.assertIsNotNone(chase_order.original_order_time)
        self.assertEqual(chase_order.order_time, chase_order.original_order_time)
        
        # 模拟重委托
        original_time = chase_order.original_order_time
        time.sleep(0.01)  # 确保时间不同
        chase_order.orderid = "ORDER002"
        chase_order.order_time = time.time()
        
        # 验证原始字段不变
        self.assertEqual(chase_order.original_orderid, "ORDER001")
        self.assertNotEqual(chase_order.orderid, chase_order.original_orderid)
        self.assertEqual(chase_order.original_order_time, original_time)
        self.assertNotEqual(chase_order.order_time, chase_order.original_order_time)
    
    def test_thread_safe_access_methods(self):
        """测试线程安全的访问方法"""
        config = ChaseConfig("_Retry2")
        chase_order = ChaseOrder(
            orderid="ORDER001",
            original_price=100.0,
            config=config,
            symbol="MHI2511",
            exchange=Exchange.HKFE,
            direction=Direction.LONG,
            offset=Offset.OPEN,
            volume=1,
            reference="_Retry2"
        )
        
        # 测试添加
        self.gateway._safe_set_chase_order("ORDER001", chase_order)
        self.assertTrue(self.gateway._safe_has_chase_order("ORDER001"))
        
        # 测试获取
        retrieved = self.gateway._safe_get_chase_order("ORDER001")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.orderid, "ORDER001")
        
        # 测试删除
        result = self.gateway._safe_del_chase_order("ORDER001")
        self.assertTrue(result)
        self.assertFalse(self.gateway._safe_has_chase_order("ORDER001"))
        
        # 测试删除不存在的订单
        result = self.gateway._safe_del_chase_order("NONEXISTENT")
        self.assertFalse(result)
    
    def test_thread_safe_key_update(self):
        """测试线程安全的字典key更新"""
        config = ChaseConfig("_Retry2")
        chase_order = ChaseOrder(
            orderid="ORDER001",
            original_price=100.0,
            config=config,
            symbol="MHI2511",
            exchange=Exchange.HKFE,
            direction=Direction.LONG,
            offset=Offset.OPEN,
            volume=1,
            reference="_Retry2"
        )
        
        # 添加原始订单
        self.gateway._safe_set_chase_order("ORDER001", chase_order)
        self.assertTrue(self.gateway._safe_has_chase_order("ORDER001"))
        
        # 更新key（模拟重委托）
        chase_order.orderid = "ORDER002"
        self.gateway._safe_update_chase_order_key("ORDER001", "ORDER002", chase_order)
        
        # 验证旧key不存在，新key存在
        self.assertFalse(self.gateway._safe_has_chase_order("ORDER001"))
        self.assertTrue(self.gateway._safe_has_chase_order("ORDER002"))
        
        # 验证订单对象正确
        retrieved = self.gateway._safe_get_chase_order("ORDER002")
        self.assertEqual(retrieved.orderid, "ORDER002")
        self.assertEqual(retrieved.original_orderid, "ORDER001")  # 原始订单ID不变
    
    def test_concurrent_access(self):
        """测试多线程并发访问"""
        config = ChaseConfig("_Retry2")
        results: List[bool] = []
        errors: List[Exception] = []
        
        def add_orders(start_id: int, count: int):
            """添加订单"""
            try:
                for i in range(count):
                    orderid = f"ORDER{start_id + i}"
                    chase_order = ChaseOrder(
                        orderid=orderid,
                        original_price=100.0 + i,
                        config=config,
                        symbol="MHI2511",
                        exchange=Exchange.HKFE,
                        direction=Direction.LONG,
                        offset=Offset.OPEN,
                        volume=1,
                        reference="_Retry2"
                    )
                    self.gateway._safe_set_chase_order(orderid, chase_order)
                    results.append(True)
            except Exception as e:
                errors.append(e)
        
        def read_orders(start_id: int, count: int):
            """读取订单"""
            try:
                for i in range(count):
                    orderid = f"ORDER{start_id + i}"
                    if self.gateway._safe_has_chase_order(orderid):
                        order = self.gateway._safe_get_chase_order(orderid)
                        if order:
                            results.append(True)
            except Exception as e:
                errors.append(e)
        
        def delete_orders(start_id: int, count: int):
            """删除订单"""
            try:
                for i in range(count):
                    orderid = f"ORDER{start_id + i}"
                    self.gateway._safe_del_chase_order(orderid)
                    results.append(True)
            except Exception as e:
                errors.append(e)
        
        # 创建多个线程同时操作
        threads = []
        for i in range(5):
            t = Thread(target=add_orders, args=(i * 10, 10))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # 验证没有错误
        self.assertEqual(len(errors), 0, f"发现错误: {errors}")
        
        # 验证所有订单都已添加
        all_orders = self.gateway._safe_get_all_chase_orders()
        self.assertGreaterEqual(len(all_orders), 30)  # 至少应该有30个订单
    
    def test_statistics_use_original_time(self):
        """测试统计耗时使用 original_order_time"""
        config = ChaseConfig("_Retry2")
        chase_order = ChaseOrder(
            orderid="ORDER001",
            original_price=100.0,
            config=config,
            symbol="MHI2511",
            exchange=Exchange.HKFE,
            direction=Direction.LONG,
            offset=Offset.OPEN,
            volume=1,
            reference="_Retry2"
        )
        
        original_time = chase_order.original_order_time
        
        # 模拟重委托，更新 order_time
        time.sleep(0.1)
        chase_order.order_time = time.time()
        chase_order.orderid = "ORDER002"
        
        # 模拟订单成交
        time.sleep(0.1)
        chase_order.fill_time = time.time()
        
        # 计算耗时应该使用 original_order_time
        elapsed_ms = (chase_order.fill_time - chase_order.original_order_time) * 1000
        elapsed_from_current = (chase_order.fill_time - chase_order.order_time) * 1000
        
        # 验证总耗时应该大于从当前订单开始的耗时
        self.assertGreater(elapsed_ms, elapsed_from_current)
        self.assertGreater(elapsed_ms, 100)  # 至少应该大于100ms（包含两次sleep）
    
    def test_order_consistency_after_retry(self):
        """测试重委托后订单一致性"""
        config = ChaseConfig("_Retry2")
        chase_order = ChaseOrder(
            orderid="ORDER001",
            original_price=100.0,
            config=config,
            symbol="MHI2511",
            exchange=Exchange.HKFE,
            direction=Direction.LONG,
            offset=Offset.OPEN,
            volume=1,
            reference="_Retry2"
        )
        
        # 验证原始订单信息
        self.assertEqual(chase_order.symbol, "MHI2511")
        self.assertEqual(chase_order.exchange, Exchange.HKFE)
        self.assertEqual(chase_order.direction, Direction.LONG)
        self.assertEqual(chase_order.offset, Offset.OPEN)
        self.assertEqual(chase_order.volume, 1)
        self.assertEqual(chase_order.original_reference, "_Retry2")
        
        # 模拟重委托
        chase_order.orderid = "ORDER002"
        chase_order.retry_count = 1
        chase_order.order_time = time.time()
        
        # 验证原始订单信息不变
        self.assertEqual(chase_order.symbol, "MHI2511")
        self.assertEqual(chase_order.exchange, Exchange.HKFE)
        self.assertEqual(chase_order.direction, Direction.LONG)
        self.assertEqual(chase_order.offset, Offset.OPEN)
        self.assertEqual(chase_order.volume, 1)
        self.assertEqual(chase_order.original_reference, "_Retry2")
        self.assertEqual(chase_order.original_orderid, "ORDER001")
    
    def test_concurrent_key_update(self):
        """测试并发更新字典key"""
        config = ChaseConfig("_Retry2")
        chase_order = ChaseOrder(
            orderid="ORDER001",
            original_price=100.0,
            config=config,
            symbol="MHI2511",
            exchange=Exchange.HKFE,
            direction=Direction.LONG,
            offset=Offset.OPEN,
            volume=1,
            reference="_Retry2"
        )
        
        self.gateway._safe_set_chase_order("ORDER001", chase_order)
        
        errors: List[Exception] = []
        
        def update_key(new_id: str):
            """更新key"""
            try:
                chase_order.orderid = new_id
                self.gateway._safe_update_chase_order_key("ORDER001", new_id, chase_order)
            except Exception as e:
                errors.append(e)
        
        # 多个线程同时更新key（虽然实际场景中不应该这样，但测试线程安全性）
        threads = []
        for i in range(3):
            t = Thread(target=update_key, args=(f"ORDER00{i+2}",))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # 验证没有错误（虽然最终状态不确定，但不应该有异常）
        self.assertEqual(len(errors), 0, f"发现错误: {errors}")
    
    def test_clear_all_orders(self):
        """测试清空所有订单"""
        config = ChaseConfig("_Retry2")
        
        # 添加多个订单
        for i in range(10):
            orderid = f"ORDER{i:03d}"
            chase_order = ChaseOrder(
                orderid=orderid,
                original_price=100.0 + i,
                config=config,
                symbol="MHI2511",
                exchange=Exchange.HKFE,
                direction=Direction.LONG,
                offset=Offset.OPEN,
                volume=1,
                reference="_Retry2"
            )
            self.gateway._safe_set_chase_order(orderid, chase_order)
        
        # 验证订单已添加
        all_orders = self.gateway._safe_get_all_chase_orders()
        self.assertEqual(len(all_orders), 10)
        
        # 清空所有订单
        self.gateway._safe_clear_chase_orders()
        
        # 验证订单已清空
        all_orders = self.gateway._safe_get_all_chase_orders()
        self.assertEqual(len(all_orders), 0)
    
    def test_get_all_orders_returns_copy(self):
        """测试获取所有订单返回副本"""
        config = ChaseConfig("_Retry2")
        
        # 添加订单
        chase_order = ChaseOrder(
            orderid="ORDER001",
            original_price=100.0,
            config=config,
            symbol="MHI2511",
            exchange=Exchange.HKFE,
            direction=Direction.LONG,
            offset=Offset.OPEN,
            volume=1,
            reference="_Retry2"
        )
        self.gateway._safe_set_chase_order("ORDER001", chase_order)
        
        # 获取副本
        copy1 = self.gateway._safe_get_all_chase_orders()
        copy2 = self.gateway._safe_get_all_chase_orders()
        
        # 验证是副本（不同的字典对象）
        self.assertIsNot(copy1, copy2)
        
        # 验证内容相同
        self.assertEqual(len(copy1), len(copy2))
        self.assertEqual(copy1["ORDER001"].orderid, copy2["ORDER001"].orderid)
        
        # 注意：_safe_get_all_chase_orders() 返回的是字典的浅拷贝
        # 字典本身是副本，但字典中的对象（ChaseOrder）仍然是引用
        # 这是Python的正常行为，修改对象属性会影响原始对象
        # 但删除或添加字典项不会影响原始字典
        copy1["ORDER001"].orderid = "MODIFIED"
        original = self.gateway._safe_get_chase_order("ORDER001")
        # 由于是浅拷贝，对象引用相同，所以修改对象属性会影响原始对象
        # 这是预期的行为，因为我们需要访问的是同一个ChaseOrder对象
        self.assertEqual(original.orderid, "MODIFIED")
        
        # 但删除字典项不会影响原始字典
        del copy1["ORDER001"]
        self.assertTrue(self.gateway._safe_has_chase_order("ORDER001"))  # 原始字典中仍然存在


if __name__ == '__main__':
    unittest.main()

