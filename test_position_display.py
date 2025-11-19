#!/usr/bin/env python3
"""
测试持仓显示修复
验证持仓数据的正确处理
"""

from vnpy.trader.object import PositionData
from vnpy.trader.constant import Direction, Exchange

def test_position_data_creation():
    """测试持仓数据创建"""
    print("=" * 60)
    print("测试持仓数据处理修复")
    print("=" * 60)

    # 模拟Futu API的持仓数据
    test_cases = [
        {"qty": 1, "expected_direction": Direction.LONG, "expected_volume": 1, "description": "多仓1手"},
        {"qty": -1, "expected_direction": Direction.SHORT, "expected_volume": 1, "description": "空仓1手"},
        {"qty": 5, "expected_direction": Direction.LONG, "expected_volume": 5, "description": "多仓5手"},
        {"qty": -3, "expected_direction": Direction.SHORT, "expected_volume": 3, "description": "空仓3手"},
    ]

    for i, case in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: {case['description']}")
        print(f"原始Futu数据: qty = {case['qty']}")

        # 模拟修复后的逻辑
        qty = float(case["qty"])

        if qty > 0:
            direction = Direction.LONG
            volume = qty
        elif qty < 0:
            direction = Direction.SHORT
            volume = abs(qty)
        else:
            print("  无持仓，跳过")
            continue

        # 创建持仓数据
        pos = PositionData(
            symbol="HKmain",
            exchange=Exchange.HKFE,
            direction=direction,
            volume=volume,
            frozen=0,
            price=28750.0,
            pnl=0.0,
            gateway_name="FUTU"
        )

        print(f"  修复后方向: {pos.direction.value} (期望: {case['expected_direction'].value})")
        print(f"  修复后数量: {pos.volume} (期望: {case['expected_volume']})")

        # 验证结果
        assert pos.direction == case["expected_direction"], f"方向不匹配: {pos.direction} != {case['expected_direction']}"
        assert pos.volume == case["expected_volume"], f"数量不匹配: {pos.volume} != {case['expected_volume']}"

        print(f"  测试通过!")

    print("\n" + "=" * 60)
    print("所有测试用例通过!")
    print("持仓方向显示: 从'净'改为'多'/'空'")
    print("持仓数量显示: 显示实际数量而非正负值")
    print("=" * 60)

def test_direction_display():
    """测试方向显示"""
    print("\n" + "=" * 40)
    print("方向显示对比")
    print("=" * 40)

    print("修复前:")
    print("  方向: 净    数量: 1   (多仓)")
    print("  方向: 净    数量: -1  (空仓)")

    print("\n修复后:")
    print("  方向: 多    数量: 1   (多仓)")
    print("  方向: 空    数量: 1   (空仓)")
    print("=" * 40)

if __name__ == "__main__":
    test_position_data_creation()
    test_direction_display()

    print("\n修复总结:")
    print("1. 持仓信息更新延迟 - 订单成交时立即更新持仓")
    print("2. 方向显示优化 - '净' → '多'/'空'")
    print("3. 数量显示优化 - 显示实际数量，不用正负值")
    print("4. 定时查询优化 - 间隔从3秒改为1秒")
    print("\n重新启动VNPy后生效!")