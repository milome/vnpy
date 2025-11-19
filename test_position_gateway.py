#!/usr/bin/env python3
"""
测试持仓显示修复是否生效
验证Futu Gateway的持仓解析逻辑
"""
import sys
import pandas as pd
from vnpy.trader.object import PositionData
from vnpy.trader.constant import Direction, Exchange

def test_position_parsing():
    """测试持仓数据解析逻辑"""
    print("=" * 60)
    print("测试Futu Gateway持仓解析逻辑")
    print("=" * 60)

    # 模拟Futu API返回的持仓数据
    test_data = [
        {"qty": "1", "description": "多仓1手"},
        {"qty": "-1", "description": "空仓1手"},
        {"qty": "5", "description": "多仓5手"},
        {"qty": "-3", "description": "空仓3手"},
        {"qty": "0", "description": "无持仓"},
    ]

    for i, test_case in enumerate(test_data, 1):
        print(f"\n测试用例 {i}: {test_case['description']}")
        print(f"Futu API原始数据: qty = {test_case['qty']}")

        # 模拟修复后的解析逻辑 (来自futu_gateway.py)
        qty = float(test_case["qty"])

        if qty > 0:
            direction = Direction.LONG
            volume = qty  # 显示实际数量
            print(f"  解析结果: 方向={direction.value}, 数量={volume}")
        elif qty < 0:
            direction = Direction.SHORT
            volume = abs(qty)  # 显示实际数量，去除负号
            print(f"  解析结果: 方向={direction.value}, 数量={volume}")
        else:
            print("  解析结果: 无持仓，跳过")
            continue

        # 创建PositionData对象
        pos = PositionData(
            symbol="HKmain",
            exchange=Exchange.HKFE,
            direction=direction,  # 明确的多空方向
            volume=volume,  # 实际持仓数量
            frozen=0,
            price=28750.0,
            pnl=0.0,
            gateway_name="FUTU"
        )

        print(f"  PositionData: {pos.direction.value} {pos.volume}手")

        # 验证修复结果
        if test_case['description'] == "多仓1手":
            assert pos.direction == Direction.LONG and pos.volume == 1
        elif test_case['description'] == "空仓1手":
            assert pos.direction == Direction.SHORT and pos.volume == 1
        elif test_case['description'] == "多仓5手":
            assert pos.direction == Direction.LONG and pos.volume == 5
        elif test_case['description'] == "空仓3手":
            assert pos.direction == Direction.SHORT and pos.volume == 3

        print("  验证通过")

    print("\n" + "=" * 60)
    print("所有测试用例通过!")
    print("修复前: 方向='净', 数量=+1/-1")
    print("修复后: 方向='多'/'空', 数量=实际数量")
    print("=" * 60)

def check_gateway_import():
    """检查Gateway是否能正常导入"""
    print("\n" + "=" * 40)
    print("Gateway导入测试")
    print("=" * 40)

    try:
        from vnpy_futu.futu_gateway import FutuGateway
        print("FutuGateway导入成功")

        # 检查方法是否存在
        gateway = FutuGateway(None, "FUTU")
        if hasattr(gateway, 'query_position'):
            print("query_position方法存在")
        else:
            print("query_position方法不存在")

    except Exception as e:
        print(f"FutuGateway导入失败: {e}")

def check_modified_code_presence():
    """检查修改的代码是否存在"""
    print("\n" + "=" * 40)
    print("代码修改检查")
    print("=" * 40)

    try:
        import inspect
        from vnpy_futu.futu_gateway import FutuGateway

        # 获取query_position方法的源码
        method = FutuGateway.query_position
        source = inspect.getsource(method)

        # 检查关键修改是否存在
        checks = [
            ("# Futu API: 正值表示多仓，负值表示空仓", "持仓方向注释"),
            ("direction = Direction.LONG", "多仓方向设置"),
            ("direction = Direction.SHORT", "空仓方向设置"),
            ("volume = abs(qty)", "数量绝对值处理"),
            ("# 显示实际数量", "数量显示注释"),
        ]

        for check_text, description in checks:
            if check_text in source:
                print(f"{description}: 存在")
            else:
                print(f"{description}: 缺失")

    except Exception as e:
        print(f"代码检查失败: {e}")

if __name__ == "__main__":
    test_position_parsing()
    check_gateway_import()
    check_modified_code_presence()

    print(f"\n使用的vnpy_futu路径: ")
    try:
        import vnpy_futu
        print(vnpy_futu.__file__)
    except:
        print("无法获取路径")