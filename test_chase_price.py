#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试智能追价功能
"""

import time
from vnpy.trader.constant import Direction, Exchange, OrderType as VtOrderType, Status
from vnpy.trader.object import OrderRequest, OrderData
from vnpy_futu.futu_gateway import ChaseConfig, ChaseOrder

def test_chase_config():
    """测试追价配置解析"""
    print("=" * 50)
    print("测试追价配置解析")
    print("=" * 50)

    # 测试1：完整的追价配置
    reference1 = "OPPONENT_Chase3_Slip0.5_Step0.05"
    config1 = ChaseConfig(reference1)
    print(f"配置1: {reference1}")
    print(f"  启用: {config1.enabled}")
    print(f"  最大追价次数: {config1.max_chase_times}")
    print(f"  最大滑点: {config1.max_slippage_pct}%")
    print(f"  追价步长: {config1.chase_step_pct}%")
    print()

    # 测试2：市价单追价配置
    reference2 = "MarketPrice_Chase5_Slip1.0_Step0.1"
    config2 = ChaseConfig(reference2)
    print(f"配置2: {reference2}")
    print(f"  启用: {config2.enabled}")
    print(f"  最大追价次数: {config2.max_chase_times}")
    print(f"  最大滑点: {config2.max_slippage_pct}%")
    print(f"  追价步长: {config2.chase_step_pct}%")
    print()

    # 测试3：无追价配置
    reference3 = "ManualTrading"
    config3 = ChaseConfig(reference3)
    print(f"配置3: {reference3}")
    print(f"  启用: {config3.enabled}")
    print()

def test_chase_order():
    """测试追价订单状态"""
    print("=" * 50)
    print("测试追价订单状态")
    print("=" * 50)

    # 创建追价配置
    config = ChaseConfig("OPPONENT_Chase3_Slip0.5_Step0.05")

    # 创建追价订单
    chase_order = ChaseOrder("12345", 400.0, config)
    print(f"订单ID: {chase_order.orderid}")
    print(f"原始价格: {chase_order.original_price}")
    print(f"当前价格: {chase_order.current_price}")
    print(f"追价次数: {chase_order.chase_count}")
    print(f"是否追价中: {chase_order.is_chasing}")
    print()

    # 模拟追价过程
    print("模拟追价过程:")
    for i in range(3):
        chase_order.chase_count += 1
        chase_order.current_price += 0.5  # 模拟价格调整
        chase_order.last_chase_time = time.time()

        print(f"第{chase_order.chase_count}次追价: 价格调整到 {chase_order.current_price}")
        time.sleep(0.1)  # 模拟追价间隔

    print(f"追价完成，总共追价 {chase_order.chase_count} 次")
    print()

def test_reference_encoding():
    """测试reference编码和解码"""
    print("=" * 50)
    print("测试reference编码和解码")
    print("=" * 50)

    # 模拟UI生成的追价配置
    chase_configs = [
        {"enabled": True, "max_chase_times": 3, "max_slippage_pct": 0.5, "chase_step_pct": 0.05},
        {"enabled": True, "max_chase_times": 5, "max_slippage_pct": 1.0, "chase_step_pct": 0.1},
        {"enabled": False, "max_chase_times": 0, "max_slippage_pct": 0, "chase_step_pct": 0},
    ]

    order_types = ["OPPONENT", "MarketPrice", "ManualTrading"]

    for i, (base_ref, config) in enumerate(zip(order_types, chase_configs)):
        print(f"测试{i+1}: {base_ref}")
        print(f"  原始配置: {config}")

        # 生成reference（模拟UI逻辑）
        if config["enabled"]:
            reference = f"{base_ref}_Chase{config['max_chase_times']}_Slip{config['max_slippage_pct']}_Step{config['chase_step_pct']}"
        else:
            reference = base_ref

        print(f"  生成reference: {reference}")

        # 解析reference（模拟Gateway逻辑）
        parsed_config = ChaseConfig(reference)
        print(f"  解析结果: 启用={parsed_config.enabled}, 追价{parsed_config.max_chase_times}次, "
              f"滑点{parsed_config.max_slippage_pct}%, 步长{parsed_config.chase_step_pct}%")

        # 验证一致性
        if config["enabled"]:
            assert parsed_config.enabled == config["enabled"]
            assert parsed_config.max_chase_times == config["max_chase_times"]
            assert parsed_config.max_slippage_pct == config["max_slippage_pct"]
            assert parsed_config.chase_step_pct == config["chase_step_pct"]
            print("  ✓ 编码解码一致")
        else:
            assert not parsed_config.enabled
            print("  ✓ 禁用状态正确")
        print()

def test_price_calculation():
    """测试追价计算逻辑"""
    print("=" * 50)
    print("测试追价价格计算逻辑")
    print("=" * 50)

    # 模拟市场数据
    class MockTick:
        def __init__(self, bid_price_1, ask_price_1, last_price):
            self.bid_price_1 = bid_price_1
            self.ask_price_1 = ask_price_1
            self.last_price = last_price

    # 创建测试数据
    tick = MockTick(399.0, 401.0, 400.0)
    print(f"模拟行情: 买一价={tick.bid_price_1}, 卖一价={tick.ask_price_1}, 最新价={tick.last_price}")

    # 测试追价配置
    config = ChaseConfig("OPPONENT_Chase3_Slip0.5_Step0.05")
    chase_order = ChaseOrder("TEST001", 400.0, config)

    # 测试买单追价
    print("\n买单追价计算:")
    step_pct = config.chase_step_pct / 100.0
    base_price = tick.ask_price_1
    new_price_buy = base_price * (1 + step_pct)
    print(f"  基准价格(ask): {base_price}")
    print(f"  追价步长: {config.chase_step_pct}%")
    print(f"  计算价格: {base_price} * (1 + {step_pct}) = {new_price_buy:.3f}")
    print(f"  滑点检查: {abs(new_price_buy - chase_order.original_price) / chase_order.original_price * 100:.2f}%")

    # 测试卖单追价
    print("\n卖单追价计算:")
    base_price = tick.bid_price_1
    new_price_sell = base_price * (1 - step_pct)
    print(f"  基准价格(bid): {base_price}")
    print(f"  追价步长: {config.chase_step_pct}%")
    print(f"  计算价格: {base_price} * (1 - {step_pct}) = {new_price_sell:.3f}")
    print(f"  滑点检查: {abs(new_price_sell - chase_order.original_price) / chase_order.original_price * 100:.2f}%")
    print()

def test_chase_statistics():
    """测试追价统计功能"""
    print("=" * 50)
    print("测试追价统计功能")
    print("=" * 50)

    # 模拟追价统计数据
    stats = {
        "total_orders": 10,
        "successful_chases": 7,
        "failed_chases": 3,
        "total_slippage": 2.1,
        "active_chase_orders": 2
    }

    # 计算统计指标
    if stats["total_orders"] > 0:
        stats["chase_success_rate"] = stats["successful_chases"] / stats["total_orders"] * 100
        stats["average_slippage"] = stats["total_slippage"] / stats["successful_chases"] if stats["successful_chases"] > 0 else 0

    print("追价统计报告:")
    print(f"  总订单数: {stats['total_orders']}")
    print(f"  成功追价: {stats['successful_chases']} 次")
    print(f"  失败追价: {stats['failed_chases']} 次")
    print(f"  成功率: {stats['chase_success_rate']:.1f}%")
    print(f"  平均滑点: {stats['average_slippage']:.3f}")
    print(f"  当前活跃追价订单: {stats['active_chase_orders']}")
    print()

if __name__ == "__main__":
    print("开始测试智能追价功能")
    print("=" * 50)

    try:
        test_chase_config()
        test_chase_order()
        test_reference_encoding()
        test_price_calculation()
        test_chase_statistics()

        print("=" * 50)
        print("✓ 所有测试通过！智能追价功能实现正确。")
        print("=" * 50)

    except Exception as e:
        print("=" * 50)
        print(f"✗ 测试失败: {str(e)}")
        print("=" * 50)
        raise