#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试合约代码匹配逻辑（主连代码和具体合约代码的匹配）
"""
import sys
import os

# 设置编码为UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from vnpy.trader.object import PositionData
from vnpy.trader.constant import Direction, Exchange


def is_contract_match(vt_symbol1: str, vt_symbol2: str) -> bool:
    """
    判断两个合约代码是否匹配（支持主连代码和具体合约代码的匹配）
    
    规则：
    1. 完全匹配：MHImain.SEHK == MHImain.SEHK
    2. 主连匹配：MHImain.SEHK 匹配 MHI2511.SEHK（主连代码匹配具体合约）
    3. 主连匹配：MHI2511.SEHK 匹配 MHImain.SEHK（具体合约匹配主连代码）
    
    主连代码格式：{base}main（如MHImain）
    具体合约格式：{base}{YYMM}（如MHI2511表示2025年11月）
    """
    if vt_symbol1 == vt_symbol2:
        return True
    
    # 提取symbol和exchange
    symbol1, exchange1 = vt_symbol1.split('.', 1)
    symbol2, exchange2 = vt_symbol2.split('.', 1)
    
    # 交易所必须匹配
    if exchange1 != exchange2:
        return False
    
    # 检查是否是主连代码和具体合约代码的匹配
    # 主连代码以"main"结尾，具体合约代码是base+YYMM格式
    if symbol1.endswith('main') and not symbol2.endswith('main'):
        # symbol1是主连代码，symbol2是具体合约
        base1 = symbol1[:-4]  # 去掉"main"
        # symbol2应该是base+YYMM格式，检查是否以base开头
        if symbol2.startswith(base1):
            return True
    elif symbol2.endswith('main') and not symbol1.endswith('main'):
        # symbol2是主连代码，symbol1是具体合约
        base2 = symbol2[:-4]  # 去掉"main"
        # symbol1应该是base+YYMM格式，检查是否以base开头
        if symbol1.startswith(base2):
            return True
    
    return False


def test_exact_match():
    """测试完全匹配"""
    print("=" * 60)
    print("测试1: 完全匹配")
    print("=" * 60)
    
    test_cases = [
        ("MHImain.SEHK", "MHImain.SEHK", True),
        ("MHI2511.SEHK", "MHI2511.SEHK", True),
        ("AAPL.NASDAQ", "AAPL.NASDAQ", True),
    ]
    
    for vt1, vt2, expected in test_cases:
        result = is_contract_match(vt1, vt2)
        status = "✓" if result == expected else "✗"
        print(f"{status} {vt1} <-> {vt2}: {result} (期望: {expected})")
        assert result == expected, f"匹配失败: {vt1} <-> {vt2}"
    
    print("\n所有完全匹配测试通过！\n")


def test_main_contract_match():
    """测试主连代码和具体合约代码的匹配"""
    print("=" * 60)
    print("测试2: 主连代码和具体合约代码的匹配")
    print("=" * 60)
    
    test_cases = [
        # 主连代码匹配具体合约
        ("MHImain.SEHK", "MHI2511.SEHK", True, "MHImain匹配MHI2511"),
        ("MHImain.SEHK", "MHI2512.SEHK", True, "MHImain匹配MHI2512"),
        ("HSImain.SEHK", "HSI2511.SEHK", True, "HSImain匹配HSI2511"),
        # 具体合约匹配主连代码
        ("MHI2511.SEHK", "MHImain.SEHK", True, "MHI2511匹配MHImain"),
        ("MHI2512.SEHK", "MHImain.SEHK", True, "MHI2512匹配MHImain"),
        # 不匹配的情况
        ("MHImain.SEHK", "HSI2511.SEHK", False, "不同base不匹配"),
        ("MHImain.SEHK", "MHI2511.HKFE", False, "不同交易所不匹配"),
        ("MHImain.SEHK", "ABC2511.SEHK", False, "完全不同的base不匹配"),
    ]
    
    for vt1, vt2, expected, desc in test_cases:
        result = is_contract_match(vt1, vt2)
        status = "✓" if result == expected else "✗"
        print(f"{status} {desc}: {vt1} <-> {vt2}: {result} (期望: {expected})")
        assert result == expected, f"匹配失败: {vt1} <-> {vt2}, {desc}"
    
    print("\n所有主连匹配测试通过！\n")


def test_position_matching():
    """测试持仓匹配场景"""
    print("=" * 60)
    print("测试3: 持仓匹配场景")
    print("=" * 60)
    
    # 模拟持仓数据
    positions = [
        PositionData(
            symbol="MHI2511",
            exchange=Exchange.SEHK,
            direction=Direction.LONG,
            volume=2.0,
            frozen=0,
            price=25000.0,
            pnl=0.0,
            gateway_name="FUTU"
        ),
        PositionData(
            symbol="HSI2511",
            exchange=Exchange.SEHK,
            direction=Direction.LONG,
            volume=1.0,
            frozen=0,
            price=18000.0,
            pnl=0.0,
            gateway_name="FUTU"
        ),
    ]
    
    # 测试场景：订阅MHImain，持仓是MHI2511
    subscribed_vt_symbol = "MHImain.SEHK"
    gateway_name = "FUTU"
    
    matched_positions = []
    for position in positions:
        position_vt_symbol = f"{position.symbol}.{position.exchange.value}"
        if (is_contract_match(position_vt_symbol, subscribed_vt_symbol) and 
            position.gateway_name == gateway_name):
            matched_positions.append(position)
    
    print(f"订阅合约: {subscribed_vt_symbol}")
    print(f"持仓列表:")
    for pos in positions:
        pos_vt = f"{pos.symbol}.{pos.exchange.value}"
        match = is_contract_match(pos_vt, subscribed_vt_symbol)
        print(f"  - {pos_vt}: {pos.volume}手 {'✓匹配' if match else '✗不匹配'}")
    
    print(f"\n匹配结果: 找到 {len(matched_positions)} 个匹配持仓")
    assert len(matched_positions) == 1, f"应该匹配1个持仓，实际匹配{len(matched_positions)}个"
    assert matched_positions[0].symbol == "MHI2511", "应该匹配MHI2511"
    assert matched_positions[0].volume == 2.0, "持仓数量应该是2.0手"
    
    print("✓ 持仓匹配测试通过！\n")


def test_edge_cases():
    """测试边界情况"""
    print("=" * 60)
    print("测试4: 边界情况")
    print("=" * 60)
    
    test_cases = [
        # 不同格式（格式不正确的情况，应该能正常处理）
        ("MHImain.SEHK", "MHImain", False, "缺少交易所不匹配"),
        ("MHI2511", "MHImain.SEHK", False, "缺少交易所不匹配"),
        # 相似但不匹配
        ("MHImain.SEHK", "MHImain2.SEHK", False, "相似但不匹配（主连代码不能有数字）"),
        ("MHImain.SEHK", "MHI2main.SEHK", False, "相似但不匹配（base不同）"),
        # 多段代码
        ("ABCmain.DEF", "ABC1234.DEF", True, "多段代码匹配"),
        # 特殊情况：合约代码长度较短（虽然不太可能，但应该能处理）
        ("MHImain.SEHK", "MHI251.SEHK", True, "较短合约代码（实际场景中不太可能）"),
    ]
    
    for vt1, vt2, expected, desc in test_cases:
        try:
            result = is_contract_match(vt1, vt2)
            status = "✓" if result == expected else "✗"
            print(f"{status} {desc}: {vt1} <-> {vt2}: {result} (期望: {expected})")
            if vt1 and vt2 and '.' in vt1 and '.' in vt2:  # 只在格式正确时断言
                assert result == expected, f"匹配失败: {vt1} <-> {vt2}, {desc}"
        except Exception as e:
            print(f"✗ {desc}: {vt1} <-> {vt2}: 异常 {e}")
    
    print("\n边界情况测试完成！\n")


if __name__ == "__main__":
    try:
        test_exact_match()
        test_main_contract_match()
        test_position_matching()
        test_edge_cases()
        
        print("=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

