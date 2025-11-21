#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试持仓盈亏实时计算（TDD方法）

测试内容：
1. 多仓盈亏计算：使用卖一（ask_price_1）减去开仓价格
2. 空仓盈亏计算：使用开仓价格减去买一（bid_price_1）
3. 买一卖一价格缺失时的处理
4. 持仓为0时不计算盈亏
5. 开仓价格为0时不计算盈亏
6. 盈亏计算正确性验证

按照TDD方法：先写测试用例，再修改代码
"""

import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

import unittest
from unittest.mock import Mock, patch
from copy import copy

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vnpy.trader.engine import OmsEngine
from vnpy.trader.object import TickData, PositionData
from vnpy.event import Event
from vnpy.trader.event import EVENT_TICK, EVENT_POSITION
from vnpy.trader.constant import Direction, Exchange


class TestPositionPnLRealtimeCalculation(unittest.TestCase):
    """测试持仓盈亏实时计算（使用买一卖一价格）"""
    
    def setUp(self):
        self.main_engine = Mock()
        self.main_engine.write_log = Mock()
        self.event_engine = Mock()
        self.event_engine.put = Mock()
        
        self.oms_engine = OmsEngine(self.main_engine, self.event_engine)
    
    def test_long_position_pnl_with_ask_price(self):
        """测试多仓盈亏计算：使用卖一（ask_price_1）减去开仓价格"""
        # 创建多仓：1手，开仓价格20000.0
        long_position = PositionData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            direction=Direction.LONG,
            volume=1.0,
            price=20000.0,  # 开仓价格
            pnl=0.0,
            gateway_name="FUTU"
        )
        self.oms_engine.positions[long_position.vt_positionid] = long_position
        
        # 创建tick数据：卖一价格20100.0，买一价格20099.0，最新价20099.5
        tick = TickData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            datetime=None,
            gateway_name="FUTU",
            last_price=20099.5,
            ask_price_1=20100.0,  # 卖一价格（用于多仓盈亏计算）
            bid_price_1=20099.0  # 买一价格
        )
        
        # 处理tick事件
        event = Event(EVENT_TICK, tick)
        self.oms_engine.process_tick_event(event)
        
        # 验证盈亏计算：多仓 = (卖一价格 - 开仓价格) * 数量
        # 预期盈亏 = (20100.0 - 20000.0) * 1.0 = 100.0
        position = self.oms_engine.positions[long_position.vt_positionid]
        expected_pnl = (20100.0 - 20000.0) * 1.0
        self.assertAlmostEqual(position.pnl, expected_pnl, places=2)
        
        # 验证触发了EVENT_POSITION事件
        self.event_engine.put.assert_called()
        call_args = self.event_engine.put.call_args
        self.assertEqual(call_args[0][0].type, EVENT_POSITION)
        # 验证推送的持仓盈亏正确
        updated_position = call_args[0][0].data
        self.assertAlmostEqual(updated_position.pnl, expected_pnl, places=2)
    
    def test_short_position_pnl_with_bid_price(self):
        """测试空仓盈亏计算：使用开仓价格减去买一（bid_price_1）"""
        # 创建空仓：1手，开仓价格20100.0
        short_position = PositionData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            direction=Direction.SHORT,
            volume=1.0,
            price=20100.0,  # 开仓价格
            pnl=0.0,
            gateway_name="FUTU"
        )
        self.oms_engine.positions[short_position.vt_positionid] = short_position
        
        # 创建tick数据：卖一价格20100.0，买一价格20099.0，最新价20099.5
        tick = TickData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            datetime=None,
            gateway_name="FUTU",
            last_price=20099.5,
            ask_price_1=20100.0,  # 卖一价格
            bid_price_1=20099.0  # 买一价格（用于空仓盈亏计算）
        )
        
        # 处理tick事件
        event = Event(EVENT_TICK, tick)
        self.oms_engine.process_tick_event(event)
        
        # 验证盈亏计算：空仓 = (开仓价格 - 买一价格) * 数量
        # 预期盈亏 = (20100.0 - 20099.0) * 1.0 = 1.0
        position = self.oms_engine.positions[short_position.vt_positionid]
        expected_pnl = (20100.0 - 20099.0) * 1.0
        self.assertAlmostEqual(position.pnl, expected_pnl, places=2)
        
        # 验证触发了EVENT_POSITION事件
        self.event_engine.put.assert_called()
        call_args = self.event_engine.put.call_args
        self.assertEqual(call_args[0][0].type, EVENT_POSITION)
        # 验证推送的持仓盈亏正确
        updated_position = call_args[0][0].data
        self.assertAlmostEqual(updated_position.pnl, expected_pnl, places=2)
    
    def test_long_position_pnl_fallback_to_last_price(self):
        """测试多仓盈亏计算：卖一价格缺失时，使用最新价（last_price）"""
        # 创建多仓：1手，开仓价格20000.0
        long_position = PositionData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            direction=Direction.LONG,
            volume=1.0,
            price=20000.0,
            pnl=0.0,
            gateway_name="FUTU"
        )
        self.oms_engine.positions[long_position.vt_positionid] = long_position
        
        # 创建tick数据：卖一价格为0或缺失，使用最新价
        tick = TickData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            datetime=None,
            gateway_name="FUTU",
            last_price=20100.0,  # 最新价（作为fallback）
            ask_price_1=0.0,  # 卖一价格缺失
            bid_price_1=20099.0
        )
        
        # 处理tick事件
        event = Event(EVENT_TICK, tick)
        self.oms_engine.process_tick_event(event)
        
        # 验证盈亏计算：使用最新价作为fallback
        # 预期盈亏 = (20100.0 - 20000.0) * 1.0 = 100.0
        position = self.oms_engine.positions[long_position.vt_positionid]
        expected_pnl = (20100.0 - 20000.0) * 1.0
        self.assertAlmostEqual(position.pnl, expected_pnl, places=2)
    
    def test_short_position_pnl_fallback_to_last_price(self):
        """测试空仓盈亏计算：买一价格缺失时，使用最新价（last_price）"""
        # 创建空仓：1手，开仓价格20100.0
        short_position = PositionData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            direction=Direction.SHORT,
            volume=1.0,
            price=20100.0,
            pnl=0.0,
            gateway_name="FUTU"
        )
        self.oms_engine.positions[short_position.vt_positionid] = short_position
        
        # 创建tick数据：买一价格为0或缺失，使用最新价
        tick = TickData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            datetime=None,
            gateway_name="FUTU",
            last_price=20099.0,  # 最新价（作为fallback）
            ask_price_1=20100.0,
            bid_price_1=0.0  # 买一价格缺失
        )
        
        # 处理tick事件
        event = Event(EVENT_TICK, tick)
        self.oms_engine.process_tick_event(event)
        
        # 验证盈亏计算：使用最新价作为fallback
        # 预期盈亏 = (20100.0 - 20099.0) * 1.0 = 1.0
        position = self.oms_engine.positions[short_position.vt_positionid]
        expected_pnl = (20100.0 - 20099.0) * 1.0
        self.assertAlmostEqual(position.pnl, expected_pnl, places=2)
    
    def test_no_calculation_when_volume_zero(self):
        """测试持仓为0时不计算盈亏"""
        # 创建持仓为0的多仓
        long_position = PositionData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            direction=Direction.LONG,
            volume=0.0,  # 持仓为0
            price=20000.0,
            pnl=0.0,
            gateway_name="FUTU"
        )
        self.oms_engine.positions[long_position.vt_positionid] = long_position
        
        tick = TickData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            datetime=None,
            gateway_name="FUTU",
            last_price=20100.0,
            ask_price_1=20100.0,
            bid_price_1=20099.0
        )
        
        # 处理tick事件
        event = Event(EVENT_TICK, tick)
        self.oms_engine.process_tick_event(event)
        
        # 验证盈亏没有更新（应该保持为0）
        position = self.oms_engine.positions[long_position.vt_positionid]
        self.assertEqual(position.pnl, 0.0)
        # 验证没有触发EVENT_POSITION事件（因为持仓为0）
        self.event_engine.put.assert_not_called()
    
    def test_no_calculation_when_price_zero(self):
        """测试开仓价格为0时不计算盈亏"""
        # 创建开仓价格为0的多仓
        long_position = PositionData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            direction=Direction.LONG,
            volume=1.0,
            price=0.0,  # 开仓价格为0
            pnl=0.0,
            gateway_name="FUTU"
        )
        self.oms_engine.positions[long_position.vt_positionid] = long_position
        
        tick = TickData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            datetime=None,
            gateway_name="FUTU",
            last_price=20100.0,
            ask_price_1=20100.0,
            bid_price_1=20099.0
        )
        
        # 处理tick事件
        event = Event(EVENT_TICK, tick)
        self.oms_engine.process_tick_event(event)
        
        # 验证盈亏没有更新（应该保持为0）
        position = self.oms_engine.positions[long_position.vt_positionid]
        self.assertEqual(position.pnl, 0.0)
        # 验证没有触发EVENT_POSITION事件（因为开仓价格为0）
        self.event_engine.put.assert_not_called()
    
    def test_multiple_positions_same_symbol(self):
        """测试同一合约的多仓和空仓同时存在时的盈亏计算"""
        # 创建多仓：1手，开仓价格20000.0
        long_position = PositionData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            direction=Direction.LONG,
            volume=1.0,
            price=20000.0,
            pnl=0.0,
            gateway_name="FUTU"
        )
        self.oms_engine.positions[long_position.vt_positionid] = long_position
        
        # 创建空仓：1手，开仓价格20100.0
        short_position = PositionData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            direction=Direction.SHORT,
            volume=1.0,
            price=20100.0,
            pnl=0.0,
            gateway_name="FUTU"
        )
        self.oms_engine.positions[short_position.vt_positionid] = short_position
        
        # 创建tick数据
        tick = TickData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            datetime=None,
            gateway_name="FUTU",
            last_price=20050.0,
            ask_price_1=20050.5,  # 用于多仓计算
            bid_price_1=20049.5   # 用于空仓计算
        )
        
        # 处理tick事件
        event = Event(EVENT_TICK, tick)
        self.oms_engine.process_tick_event(event)
        
        # 验证多仓盈亏：使用卖一价格
        long_pnl = self.oms_engine.positions[long_position.vt_positionid].pnl
        expected_long_pnl = (20050.5 - 20000.0) * 1.0
        self.assertAlmostEqual(long_pnl, expected_long_pnl, places=2)
        
        # 验证空仓盈亏：使用买一价格
        short_pnl = self.oms_engine.positions[short_position.vt_positionid].pnl
        expected_short_pnl = (20100.0 - 20049.5) * 1.0
        self.assertAlmostEqual(short_pnl, expected_short_pnl, places=2)
        
        # 验证两个持仓都触发了EVENT_POSITION事件
        self.assertEqual(self.event_engine.put.call_count, 2)
    
    def test_pnl_calculation_accuracy(self):
        """测试盈亏计算精度（多仓和空仓的详细计算）"""
        # 测试多仓：2手，开仓价格20000.0
        long_position = PositionData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            direction=Direction.LONG,
            volume=2.0,  # 2手
            price=20000.0,
            pnl=0.0,
            gateway_name="FUTU"
        )
        self.oms_engine.positions[long_position.vt_positionid] = long_position
        
        tick = TickData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            datetime=None,
            gateway_name="FUTU",
            last_price=20100.0,
            ask_price_1=20100.5,  # 卖一价格
            bid_price_1=20099.5
        )
        
        event = Event(EVENT_TICK, tick)
        self.oms_engine.process_tick_event(event)
        
        # 验证多仓盈亏：(20100.5 - 20000.0) * 2.0 = 201.0
        position = self.oms_engine.positions[long_position.vt_positionid]
        expected_pnl = (20100.5 - 20000.0) * 2.0
        self.assertAlmostEqual(position.pnl, expected_pnl, places=2)
        self.assertEqual(position.pnl, 201.0)
        
        # 测试空仓：2手，开仓价格20100.0
        short_position = PositionData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            direction=Direction.SHORT,
            volume=2.0,  # 2手
            price=20100.0,
            pnl=0.0,
            gateway_name="FUTU"
        )
        self.oms_engine.positions[short_position.vt_positionid] = short_position
        
        # 重置event_engine
        self.event_engine.put.reset_mock()
        
        event = Event(EVENT_TICK, tick)
        self.oms_engine.process_tick_event(event)
        
        # 验证空仓盈亏：(20100.0 - 20099.5) * 2.0 = 1.0
        position = self.oms_engine.positions[short_position.vt_positionid]
        expected_pnl = (20100.0 - 20099.5) * 2.0
        self.assertAlmostEqual(position.pnl, expected_pnl, places=2)
        self.assertEqual(position.pnl, 1.0)

    @patch("vnpy.trader.engine.time")
    def test_pnl_logging_threshold_and_interval(self, mock_time):
        """测试盈亏日志输出的阈值与限流逻辑"""
        self.main_engine.write_log.reset_mock()
        self.oms_engine.pnl_log_threshold = 5.0
        self.oms_engine.pnl_log_interval = 2.0

        tick = TickData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            datetime=None,
            gateway_name="FUTU",
            last_price=20050.0,
            ask_price_1=20055.0,
            bid_price_1=20045.0
        )

        mock_time.return_value = 0.0
        self.oms_engine.process_tick_event(Event(EVENT_TICK, tick))
        first_log_count = len(self.main_engine.write_log.call_args_list)
        self.assertGreater(first_log_count, 0, "第一次tick应输出实时盈亏日志")

        # 在限流间隔内再次触发，不应再次打印日志
        mock_time.return_value = 0.5
        tick.ask_price_1 = 20060.0
        tick.bid_price_1 = 20050.0
        self.oms_engine.process_tick_event(Event(EVENT_TICK, tick))
        self.assertEqual(len(self.main_engine.write_log.call_args_list), first_log_count)

        # 超过限流间隔，应允许再次打印日志
        mock_time.return_value = 3.0
        tick.ask_price_1 = 20080.0
        tick.bid_price_1 = 20070.0
        self.oms_engine.process_tick_event(Event(EVENT_TICK, tick))
        self.assertGreater(len(self.main_engine.write_log.call_args_list), first_log_count)

        # 验证日志内容包含实时盈亏标识
        log_messages = [str(call) for call in self.main_engine.write_log.call_args_list]
        self.assertTrue(
            any("实时盈亏" in msg for msg in log_messages),
            f"应输出实时盈亏日志，实际日志：{log_messages}"
        )


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("开始测试持仓盈亏实时计算（TDD方法）")
    print("=" * 60)
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试用例
    suite.addTests(loader.loadTestsFromTestCase(TestPositionPnLRealtimeCalculation))
    
    print("\n测试覆盖范围：")
    print("  ✓ 多仓盈亏计算：使用卖一（ask_price_1）减去开仓价格")
    print("  ✓ 空仓盈亏计算：使用开仓价格减去买一（bid_price_1）")
    print("  ✓ 卖一价格缺失时，使用最新价（last_price）作为fallback")
    print("  ✓ 买一价格缺失时，使用最新价（last_price）作为fallback")
    print("  ✓ 持仓为0时不计算盈亏")
    print("  ✓ 开仓价格为0时不计算盈亏")
    print("  ✓ 同一合约的多仓和空仓同时存在时的盈亏计算")
    print("  ✓ 盈亏计算精度验证（多仓和空仓）")
    print("")
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出结果
    print("\n" + "=" * 60)
    print(f"测试完成: {result.testsRun} 个测试")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print("=" * 60)
    
    if result.failures:
        print("\n失败的测试：")
        for test, traceback in result.failures:
            print(f"  - {test}")
            print(f"    {traceback}")
    
    if result.errors:
        print("\n错误的测试：")
        for test, traceback in result.errors:
            print(f"  - {test}")
            print(f"    {traceback}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

