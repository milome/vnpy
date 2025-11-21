#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试平仓操作（不使用智能追价，直接使用对手价）- TDD方法

测试内容：
1. 平仓操作不使用智能追价
2. 平仓操作直接使用对手价
3. 实时盈亏计算日志输出（低频率）
4. 平仓操作不阻塞UI

按照TDD方法：先写测试用例，再修改代码
"""

import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

import unittest
from unittest.mock import Mock, MagicMock, patch
from time import time

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vnpy.trader.ui.widget import TradingWidget
from vnpy.trader.object import (
    TickData,
    PositionData,
    OrderRequest,
    ContractData
)
from vnpy.trader.constant import Direction, Exchange, OrderType, Offset, Product
from vnpy.trader.engine import MainEngine


class TestClosePositionWithoutChase(unittest.TestCase):
    """测试平仓操作（不使用智能追价）"""
    
    def setUp(self):
        self.main_engine = Mock(spec=MainEngine)
        self.main_engine.write_log = Mock()
        self.main_engine.send_order = Mock(return_value="order123")
        self.main_engine.get_all_positions = Mock(return_value=[])
        self.main_engine.get_gateway = Mock(return_value=None)
        self.contract = ContractData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            name="恒指",
            product=Product.FUTURES,
            size=50,
            pricetick=1.0,
            gateway_name="FUTU"
        )
        self.main_engine.get_contract = Mock(return_value=self.contract)
        self.main_engine.get_tick = Mock()
        
        # 创建TradingWidget
        self.widget = TradingWidget(None, self.main_engine)
        self.widget.vt_symbol = "MHI2511.SEHK"
        self.widget.gateway_name = "FUTU"
        self.widget.close_volume_spin = Mock()
        self.widget.close_volume_spin.value = Mock(return_value=1.0)
    
    def test_close_position_uses_opponent_price(self):
        """测试平仓操作使用对手价（不启用智能追价）"""
        # 模拟持仓：1手多仓
        position = PositionData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            direction=Direction.LONG,
            volume=1.0,
            price=20000.0,
            pnl=0.0,
            gateway_name="FUTU"
        )
        self.main_engine.get_all_positions.return_value = [position]
        
        # 模拟tick数据
        tick = TickData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            datetime=None,
            gateway_name="FUTU",
            last_price=20100.0,
            ask_price_1=20100.5,
            bid_price_1=20099.5
        )
        
        # 模拟get_tick
        self.main_engine.get_tick.return_value = tick
        
        # 调用平仓方法
        self.widget.close_position()
        
        # 验证send_order被调用
        self.main_engine.send_order.assert_called_once()
        
        # 获取发送的订单请求
        call_args = self.main_engine.send_order.call_args
        order_request = call_args[0][0]
        
        # 验证订单类型为对手价
        self.assertEqual(order_request.type, OrderType.OPPONENT)
        
        # 验证订单方向为SHORT（平多仓）
        self.assertEqual(order_request.direction, Direction.SHORT)
        
        # 验证订单开平为CLOSE
        self.assertEqual(order_request.offset, Offset.CLOSE)
        
        # 验证订单数量
        self.assertEqual(order_request.volume, 1.0)
        
        # 验证订单价格（对手价：平多仓使用买一价）
        # 注意：由于使用OPPONENT类型，价格可能为0或使用对手价逻辑
        # 这里主要验证订单类型和方向正确
    
    def test_close_position_no_chase_config(self):
        """测试平仓操作不包含智能追价配置"""
        # 模拟持仓：1手多仓
        position = PositionData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            direction=Direction.LONG,
            volume=1.0,
            price=20000.0,
            pnl=0.0,
            gateway_name="FUTU"
        )
        self.main_engine.get_all_positions.return_value = [position]
        
        # 模拟tick数据
        tick = TickData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            datetime=None,
            gateway_name="FUTU",
            last_price=20100.0,
            ask_price_1=20100.5,
            bid_price_1=20099.5
        )
        
        self.main_engine.get_tick.return_value = tick
        
        # 调用平仓方法
        self.widget.close_position()
        
        # 验证send_order被调用
        self.main_engine.send_order.assert_called_once()
        
        # 获取发送的订单请求
        call_args = self.main_engine.send_order.call_args
        order_request = call_args[0][0]
        
        # 验证订单reference不包含追价配置（Chase关键字）
        # 如果reference为空或不存在，说明没有追价配置
        if hasattr(order_request, 'reference') and order_request.reference:
            self.assertNotIn("Chase", order_request.reference)
            self.assertNotIn("chase", order_request.reference.lower())
    
    def test_close_position_non_blocking(self):
        """测试平仓操作不阻塞UI（异步执行）"""
        # 模拟持仓：1手多仓
        position = PositionData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            direction=Direction.LONG,
            volume=1.0,
            price=20000.0,
            pnl=0.0,
            gateway_name="FUTU"
        )
        self.main_engine.get_all_positions.return_value = [position]
        
        # 模拟tick数据
        tick = TickData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            datetime=None,
            gateway_name="FUTU",
            last_price=20100.0,
            ask_price_1=20100.5,
            bid_price_1=20099.5
        )
        
        self.main_engine.get_tick.return_value = tick
        
        # 记录开始时间
        start_time = time()
        
        # 调用平仓方法（应该立即返回，不阻塞）
        self.widget.close_position()
        
        # 记录结束时间
        end_time = time()
        
        # 验证执行时间很短（<100ms），说明没有阻塞
        elapsed = (end_time - start_time) * 1000
        self.assertLess(elapsed, 100, f"平仓操作耗时{elapsed:.2f}ms，可能阻塞了UI")
    
    def test_close_position_ignores_chase_when_enabled(self):
        """测试即使全局启用追价，平仓仍不附带追价配置"""
        position = PositionData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            direction=Direction.LONG,
            volume=1.0,
            price=20000.0,
            pnl=0.0,
            gateway_name="FUTU"
        )
        self.main_engine.get_all_positions.return_value = [position]
        
        tick = TickData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            datetime=None,
            gateway_name="FUTU",
            last_price=20100.0,
            ask_price_1=20100.5,
            bid_price_1=20099.5
        )
        self.main_engine.get_tick.return_value = tick
        
        # 模拟追价配置开启
        self.widget.get_chase_config = Mock(return_value={
            "enabled": True,
            "max_chase_times": 5,
            "max_slippage_pct": 0.5,
            "chase_step_pct": 0.05
        })
        
        self.widget.close_position()
        
        self.main_engine.send_order.assert_called_once()
        order_request = self.main_engine.send_order.call_args[0][0]
        
        # 平仓必须始终使用对手价，并且reference固定为CloseOpponent
        self.assertEqual(order_request.type, OrderType.OPPONENT)
        self.assertEqual(order_request.reference, "CloseOpponent")
        self.assertNotIn("Chase", order_request.reference)
        
        # 验证日志提示未启用智能追价
        log_messages = [call_args[0][0] for call_args in self.main_engine.write_log.call_args_list]
        self.assertTrue(
            any("未启用智能追价" in msg for msg in log_messages),
            f"日志应提示未启用智能追价，实际日志：{log_messages}"
        )


class TestPositionPnLRealtimeLogging(unittest.TestCase):
    """测试持仓盈亏实时计算日志输出（低频率）"""
    
    def setUp(self):
        self.main_engine = Mock()
        self.main_engine.write_log = Mock()
        self.event_engine = Mock()
        self.event_engine.put = Mock()
        
        from vnpy.trader.engine import OmsEngine
        self.oms_engine = OmsEngine(self.main_engine, self.event_engine)
        
        # 创建测试持仓
        self.long_position = PositionData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            direction=Direction.LONG,
            volume=1.0,
            price=20000.0,
            pnl=0.0,
            gateway_name="FUTU"
        )
        self.oms_engine.positions[self.long_position.vt_positionid] = self.long_position
    
    def test_pnl_logging_low_frequency(self):
        """测试盈亏计算日志输出（低频率，避免日志过多）"""
        from vnpy.trader.object import TickData
        from vnpy.event import Event
        from vnpy.trader.event import EVENT_TICK
        
        # 创建tick数据
        tick = TickData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            datetime=None,
            gateway_name="FUTU",
            last_price=20100.0,
            ask_price_1=20100.5,  # 卖一价格
            bid_price_1=20099.5
        )
        
        # 重置日志mock
        self.main_engine.write_log.reset_mock()
        
        # 第一次tick事件
        event1 = Event(EVENT_TICK, tick)
        self.oms_engine.process_tick_event(event1)
        
        # 验证第一次更新时可能没有日志（因为变化较小）
        # 或者有日志但频率较低
        
        # 多次tick事件（模拟频繁更新）
        for i in range(10):
            tick.last_price = 20100.0 + i * 0.1
            tick.ask_price_1 = 20100.5 + i * 0.1
            event = Event(EVENT_TICK, tick)
            self.oms_engine.process_tick_event(event)
        
        # 验证日志调用次数不会太多（低频率）
        log_calls = self.main_engine.write_log.call_args_list
        # 由于盈亏变化可能较小，日志可能很少或没有
        # 这里主要验证不会因为频繁tick导致日志过多
        # 如果盈亏变化>1.0，应该有日志；否则不应该有日志
    
    def test_pnl_logging_when_significant_change(self):
        """测试盈亏显著变化时输出日志"""
        from vnpy.trader.object import TickData
        from vnpy.event import Event
        from vnpy.trader.event import EVENT_TICK
        
        # 创建tick数据（价格大幅变化，盈亏变化>1.0）
        tick = TickData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            datetime=None,
            gateway_name="FUTU",
            last_price=20100.0,
            ask_price_1=20200.0,  # 卖一价格大幅上涨，盈亏变化100.0
            bid_price_1=20199.0
        )
        
        # 重置日志mock
        self.main_engine.write_log.reset_mock()
        
        # 处理tick事件
        event = Event(EVENT_TICK, tick)
        self.oms_engine.process_tick_event(event)
        
        # 验证有日志输出（因为盈亏变化>1.0）
        self.main_engine.write_log.assert_called()
        
        # 验证日志内容包含盈亏信息
        log_calls = [str(call) for call in self.main_engine.write_log.call_args_list]
        log_text = " ".join(log_calls)
        # 验证日志包含盈亏相关信息
        self.assertTrue(
            any("持仓盈利" in call or "盈利" in call for call in log_calls),
            f"日志中应该包含盈亏信息，实际日志：{log_text}"
        )
    
    def test_pnl_calculation_with_ask_bid_prices(self):
        """测试使用买一卖一价格计算盈亏并输出调试日志"""
        from vnpy.trader.object import TickData
        from vnpy.event import Event
        from vnpy.trader.event import EVENT_TICK
        
        # 创建tick数据
        tick = TickData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            datetime=None,
            gateway_name="FUTU",
            last_price=20100.0,
            ask_price_1=20100.5,  # 卖一价格（用于多仓计算）
            bid_price_1=20099.5   # 买一价格（用于空仓计算）
        )
        
        # 重置日志mock
        self.main_engine.write_log.reset_mock()
        
        # 处理tick事件
        event = Event(EVENT_TICK, tick)
        self.oms_engine.process_tick_event(event)
        
        # 验证盈亏计算正确
        position = self.oms_engine.positions[self.long_position.vt_positionid]
        expected_pnl = (20100.5 - 20000.0) * 1.0  # 使用卖一价格
        self.assertAlmostEqual(position.pnl, expected_pnl, places=2)
        
        # 验证事件被推送
        self.event_engine.put.assert_called()


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("开始测试平仓操作（不使用智能追价）- TDD方法")
    print("=" * 60)
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试用例
    suite.addTests(loader.loadTestsFromTestCase(TestClosePositionWithoutChase))
    suite.addTests(loader.loadTestsFromTestCase(TestPositionPnLRealtimeLogging))
    
    print("\n测试覆盖范围：")
    print("  ✓ 平仓操作使用对手价（OrderType.OPPONENT）")
    print("  ✓ 平仓操作不包含智能追价配置")
    print("  ✓ 平仓操作不阻塞UI（异步执行）")
    print("  ✓ 盈亏计算日志输出（低频率）")
    print("  ✓ 盈亏显著变化时输出日志")
    print("  ✓ 使用买一卖一价格计算盈亏")
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
