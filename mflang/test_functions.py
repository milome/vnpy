#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
麦语言函数测试
"""

import numpy as np
from mflang.functions import REF, BARSLAST


def test_ref_basic():
    """测试基本的REF功能"""
    print("=" * 50)
    print("测试1: 基本REF功能")
    print("=" * 50)
    
    close = np.array([100.0, 101.0, 102.0, 103.0, 104.0, 105.0])
    result = REF(close, 2)
    print(f"输入: {close}")
    print(f"REF(close, 2): {result}")
    print(f"预期: [nan, nan, 100., 101., 102., 103.]")
    print()


def test_ref_zero():
    """测试N=0的情况"""
    print("=" * 50)
    print("测试2: N=0的情况")
    print("=" * 50)
    
    close = np.array([100.0, 101.0, 102.0, 103.0])
    result = REF(close, 0)
    print(f"输入: {close}")
    print(f"REF(close, 0): {result}")
    print(f"预期: [100., 101., 102., 103.]")
    print(f"是否相等: {np.array_equal(result, close)}")
    print()


def test_ref_insufficient_data():
    """测试数据不足的情况"""
    print("=" * 50)
    print("测试3: 数据不足的情况")
    print("=" * 50)
    
    close = np.array([100.0, 101.0, 102.0])
    result = REF(close, 5)
    print(f"输入: {close}")
    print(f"REF(close, 5): {result}")
    print(f"预期: [nan, nan, nan]")
    print(f"是否全为NaN: {np.all(np.isnan(result))}")
    print()


def test_ref_none():
    """测试N为None的情况"""
    print("=" * 50)
    print("测试4: N为None的情况")
    print("=" * 50)
    
    close = np.array([100.0, 101.0, 102.0])
    result = REF(close, None)
    print(f"输入: {close}")
    print(f"REF(close, None): {result}")
    print(f"预期: [nan, nan, nan]")
    print(f"是否全为NaN: {np.all(np.isnan(result))}")
    print()


def test_ref_negative():
    """测试N为负数的情况"""
    print("=" * 50)
    print("测试5: N为负数的情况")
    print("=" * 50)
    
    close = np.array([100.0, 101.0, 102.0])
    result = REF(close, -1)
    print(f"输入: {close}")
    print(f"REF(close, -1): {result}")
    print(f"预期: [nan, nan, nan]")
    print(f"是否全为NaN: {np.all(np.isnan(result))}")
    print()


def test_ref_array_n():
    """测试N为数组的情况"""
    print("=" * 50)
    print("测试6: N为数组的情况")
    print("=" * 50)
    
    close = np.array([100.0, 101.0, 102.0, 103.0, 104.0, 105.0])
    N = np.array([0, 1, 2, 0, 1, 2])
    result = REF(close, N)
    print(f"输入X: {close}")
    print(f"输入N: {N}")
    print(f"REF(close, N): {result}")
    print(f"预期: [100., 100., 100., 103., 103., 103.]")
    print()


def test_ref_example():
    """测试示例：REF(CLOSE, 5)"""
    print("=" * 50)
    print("测试7: 示例 REF(CLOSE, 5)")
    print("=" * 50)
    
    # 模拟10个周期的收盘价
    close = np.array([100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0])
    result = REF(close, 5)
    print(f"收盘价序列: {close}")
    print(f"REF(CLOSE, 5): {result}")
    print()
    print("验证:")
    print(f"  位置5 (索引5): 当前值={close[5]}, 5周期前={result[5]} (应该是{close[0]})")
    print(f"  位置9 (索引9): 当前值={close[9]}, 5周期前={result[9]} (应该是{close[4]})")
    print()


def test_barslast_basic():
    """测试基本的BARSLAST功能"""
    print("=" * 50)
    print("测试8: 基本BARSLAST功能")
    print("=" * 50)
    
    # 条件数组：True表示条件成立
    cond = np.array([True, False, False, True, False, False, True])
    result = BARSLAST(cond)
    print(f"条件数组: {cond}")
    print(f"BARSLAST(cond): {result}")
    print(f"预期: [0., 0., 1., 0., 1., 2., 0.]")
    print()


def test_barslast_example1():
    """测试示例1: 上一根阴线到现在的周期数"""
    print("=" * 50)
    print("测试9: 示例1 - 上一根阴线到现在的周期数")
    print("=" * 50)
    
    # 模拟开盘价和收盘价（混合阳线和阴线）
    # 位置0: 阴线(100>99), 位置1: 阳线(101<102), 位置2: 阳线(102<103), 
    # 位置3: 阴线(103>102), 位置4: 阳线(104<105), 位置5: 阳线(105<106)
    open_price = np.array([100.0, 101.0, 102.0, 103.0, 104.0, 105.0])
    close_price = np.array([99.0, 102.0, 103.0, 102.0, 105.0, 106.0])
    
    # 阴线条件：开盘价 > 收盘价
    cond = open_price > close_price
    result = BARSLAST(cond)
    
    print(f"开盘价: {open_price}")
    print(f"收盘价: {close_price}")
    print(f"阴线条件 (OPEN>CLOSE): {cond}")
    print(f"BARSLAST(OPEN>CLOSE): {result}")
    print()
    print("验证:")
    print(f"  位置0: 当前是阴线，BARSLAST={result[0]} (应该是0)")
    print(f"  位置1: 不是阴线，上次阴线在位置0，BARSLAST={result[1]} (应该是1)")
    print(f"  位置2: 不是阴线，上次阴线在位置0，BARSLAST={result[2]} (应该是2)")
    print(f"  位置3: 当前是阴线，BARSLAST={result[3]} (应该是0)")
    print(f"  位置4: 不是阴线，上次阴线在位置3，BARSLAST={result[4]} (应该是1)")
    print(f"  位置5: 不是阴线，上次阴线在位置3，BARSLAST={result[5]} (应该是2)")
    print()


def test_barslast_never_true():
    """测试条件从未成立的情况"""
    print("=" * 50)
    print("测试10: 条件从未成立的情况")
    print("=" * 50)
    
    cond = np.array([False, False, False, False])
    result = BARSLAST(cond)
    print(f"条件数组: {cond}")
    print(f"BARSLAST(cond): {result}")
    print(f"预期: [nan, nan, nan, nan]")
    print(f"是否全为NaN: {np.all(np.isnan(result))}")
    print()


def test_barslast_all_true():
    """测试条件全部成立的情况"""
    print("=" * 50)
    print("测试11: 条件全部成立的情况")
    print("=" * 50)
    
    cond = np.array([True, True, True, True])
    result = BARSLAST(cond)
    print(f"条件数组: {cond}")
    print(f"BARSLAST(cond): {result}")
    print(f"预期: [0., 0., 0., 0.]")
    print(f"是否全为0: {np.all(result == 0)}")
    print()


def test_barslast_example2():
    """测试示例2: 当日k线数（模拟）"""
    print("=" * 50)
    print("测试12: 示例2 - 当日k线数（模拟）")
    print("=" * 50)
    
    # 模拟日期变化：True表示日期变化
    # 假设有10根k线，第0、5根是日期变化点
    date_changed = np.array([True, False, False, False, False, True, False, False, False, False])
    
    # DATE<>REF(DATE,1) 的模拟
    # 这里简化处理，直接使用date_changed
    cond = date_changed
    
    result = BARSLAST(cond)
    n = result + 1  # 当日k线数
    
    print(f"日期变化条件: {cond}")
    print(f"BARSLAST(DATE<>REF(DATE,1)): {result}")
    print(f"N = BARSLAST(...) + 1 (当日k线数): {n}")
    print()
    print("验证:")
    print(f"  位置0: 日期变化，BARSLAST={result[0]}, N={n[0]} (应该是1)")
    print(f"  位置1-4: 同一日，BARSLAST={result[1:5]}, N={n[1:5]} (应该是2,3,4,5)")
    print(f"  位置5: 日期变化，BARSLAST={result[5]}, N={n[5]} (应该是1)")
    print(f"  位置6-9: 同一日，BARSLAST={result[6:10]}, N={n[6:10]} (应该是2,3,4,5)")
    print()


def test_barslast_example2_complete():
    """测试示例2: 当日k线数（完整实现 DATE<>REF(DATE,1)）"""
    print("=" * 50)
    print("测试13: 示例2 - 当日k线数（完整实现）")
    print("=" * 50)
    print("测试公式: N:=BARSLAST(DATE<>REF(DATE,1))+1")
    print()
    
    # 模拟日期数组（分钟周期）
    # 假设有15根k线：
    # 位置0-4: 2024-01-01 (5根)
    # 位置5-9: 2024-01-02 (5根)
    # 位置10-14: 2024-01-03 (5根)
    date_array = np.array([
        20240101, 20240101, 20240101, 20240101, 20240101,  # 第1天
        20240102, 20240102, 20240102, 20240102, 20240102,  # 第2天
        20240103, 20240103, 20240103, 20240103, 20240103   # 第3天
    ])
    
    # 计算 REF(DATE, 1) - 1个周期前的日期
    ref_date = REF(date_array, 1)
    
    # 计算 DATE<>REF(DATE,1) - 日期是否变化
    date_changed = date_array != ref_date
    
    # 计算 BARSLAST(DATE<>REF(DATE,1))
    barslast_result = BARSLAST(date_changed)
    
    # 计算当日k线数: N = BARSLAST(...) + 1
    n = barslast_result + 1
    
    print(f"日期数组 (DATE): {date_array}")
    print(f"REF(DATE, 1): {ref_date}")
    print(f"日期变化条件 (DATE<>REF(DATE,1)): {date_changed}")
    print(f"BARSLAST(DATE<>REF(DATE,1)): {barslast_result}")
    print(f"N = BARSLAST(...) + 1 (当日k线数): {n}")
    print()
    print("验证:")
    print(f"  位置0: 日期变化点，BARSLAST={barslast_result[0]}, N={n[0]} (应该是1，第1根k线)")
    print(f"  位置1: 同一日，BARSLAST={barslast_result[1]}, N={n[1]} (应该是2，第2根k线)")
    print(f"  位置2: 同一日，BARSLAST={barslast_result[2]}, N={n[2]} (应该是3，第3根k线)")
    print(f"  位置3: 同一日，BARSLAST={barslast_result[3]}, N={n[3]} (应该是4，第4根k线)")
    print(f"  位置4: 同一日，BARSLAST={barslast_result[4]}, N={n[4]} (应该是5，第5根k线)")
    print(f"  位置5: 日期变化点，BARSLAST={barslast_result[5]}, N={n[5]} (应该是1，新一天的第1根k线)")
    print(f"  位置6-9: 同一日，N={n[6:10]} (应该是2,3,4,5)")
    print(f"  位置10: 日期变化点，BARSLAST={barslast_result[10]}, N={n[10]} (应该是1，新一天的第1根k线)")
    print(f"  位置11-14: 同一日，N={n[11:15]} (应该是2,3,4,5)")
    print()
    
    # 验证结果
    expected_n = np.array([1., 2., 3., 4., 5., 1., 2., 3., 4., 5., 1., 2., 3., 4., 5.])
    is_correct = np.allclose(n, expected_n, equal_nan=True)
    print(f"结果验证: {'通过' if is_correct else '失败'}")
    if not is_correct:
        print(f"  期望: {expected_n}")
        print(f"  实际: {n}")
    else:
        print("  所有值都正确！")
    print()


def test_barslast_example2_edge_cases():
    """测试示例2的边界情况：当日k线数计算的各种场景"""
    print("=" * 50)
    print("测试14: 示例2边界情况 - 当日k线数计算")
    print("=" * 50)
    print("测试公式: N:=BARSLAST(DATE<>REF(DATE,1))+1")
    print()
    
    # 场景1: 第一天只有1根k线
    print("场景1: 第一天只有1根k线")
    print("-" * 50)
    date_array_1 = np.array([
        20240101,  # 第1天，1根k线
        20240102, 20240102, 20240102,  # 第2天，3根k线
    ])
    ref_date_1 = REF(date_array_1, 1)
    date_changed_1 = date_array_1 != ref_date_1
    barslast_result_1 = BARSLAST(date_changed_1)
    n_1 = barslast_result_1 + 1
    print(f"日期数组: {date_array_1}")
    print(f"日期变化条件: {date_changed_1}")
    print(f"BARSLAST结果: {barslast_result_1}")
    print(f"当日k线数N: {n_1}")
    expected_1 = np.array([1., 1., 2., 3.])
    is_correct_1 = np.allclose(n_1, expected_1, equal_nan=True)
    print(f"验证: {'通过' if is_correct_1 else '失败'}")
    if not is_correct_1:
        print(f"  期望: {expected_1}")
        print(f"  实际: {n_1}")
    print()
    
    # 场景2: 每天k线数不同
    print("场景2: 每天k线数不同")
    print("-" * 50)
    date_array_2 = np.array([
        20240101, 20240101,  # 第1天，2根k线
        20240102, 20240102, 20240102, 20240102, 20240102,  # 第2天，5根k线
        20240103, 20240103, 20240103,  # 第3天，3根k线
    ])
    ref_date_2 = REF(date_array_2, 1)
    date_changed_2 = date_array_2 != ref_date_2
    barslast_result_2 = BARSLAST(date_changed_2)
    n_2 = barslast_result_2 + 1
    print(f"日期数组: {date_array_2}")
    print(f"日期变化条件: {date_changed_2}")
    print(f"BARSLAST结果: {barslast_result_2}")
    print(f"当日k线数N: {n_2}")
    expected_2 = np.array([1., 2., 1., 2., 3., 4., 5., 1., 2., 3.])
    is_correct_2 = np.allclose(n_2, expected_2, equal_nan=True)
    print(f"验证: {'通过' if is_correct_2 else '失败'}")
    if not is_correct_2:
        print(f"  期望: {expected_2}")
        print(f"  实际: {n_2}")
    print()
    
    # 场景3: 只有1天的数据
    print("场景3: 只有1天的数据")
    print("-" * 50)
    date_array_3 = np.array([
        20240101, 20240101, 20240101, 20240101,  # 只有1天，4根k线
    ])
    ref_date_3 = REF(date_array_3, 1)
    date_changed_3 = date_array_3 != ref_date_3
    barslast_result_3 = BARSLAST(date_changed_3)
    n_3 = barslast_result_3 + 1
    print(f"日期数组: {date_array_3}")
    print(f"REF(DATE, 1): {ref_date_3}")
    print(f"日期变化条件: {date_changed_3}")
    print(f"BARSLAST结果: {barslast_result_3}")
    print(f"当日k线数N: {n_3}")
    # 第一天第一根k线，REF(DATE,1)是NaN，所以DATE<>REF(DATE,1)是True
    # 后续k线，REF(DATE,1)是20240101，所以DATE<>REF(DATE,1)是False
    # 因此BARSLAST结果应该是[0, 1, 2, 3]，N应该是[1, 2, 3, 4]
    expected_3 = np.array([1., 2., 3., 4.])
    is_correct_3 = np.allclose(n_3, expected_3, equal_nan=True)
    print(f"验证: {'通过' if is_correct_3 else '失败'}")
    if not is_correct_3:
        print(f"  期望: {expected_3}")
        print(f"  实际: {n_3}")
    print()
    
    # 场景4: 更长的日期序列（模拟实际交易场景）
    print("场景4: 更长的日期序列（模拟实际交易场景）")
    print("-" * 50)
    # 模拟5个交易日，每天不同数量的k线
    date_array_4 = np.array([
        # 2024-01-01: 3根k线
        20240101, 20240101, 20240101,
        # 2024-01-02: 4根k线
        20240102, 20240102, 20240102, 20240102,
        # 2024-01-03: 2根k线
        20240103, 20240103,
        # 2024-01-04: 5根k线
        20240104, 20240104, 20240104, 20240104, 20240104,
        # 2024-01-05: 3根k线
        20240105, 20240105, 20240105,
    ])
    ref_date_4 = REF(date_array_4, 1)
    date_changed_4 = date_array_4 != ref_date_4
    barslast_result_4 = BARSLAST(date_changed_4)
    n_4 = barslast_result_4 + 1
    print(f"日期数组长度: {len(date_array_4)}")
    print(f"日期数组: {date_array_4}")
    print(f"日期变化条件: {date_changed_4}")
    print(f"BARSLAST结果: {barslast_result_4}")
    print(f"当日k线数N: {n_4}")
    expected_4 = np.array([
        1., 2., 3.,  # 第1天
        1., 2., 3., 4.,  # 第2天
        1., 2.,  # 第3天
        1., 2., 3., 4., 5.,  # 第4天
        1., 2., 3.,  # 第5天
    ])
    is_correct_4 = np.allclose(n_4, expected_4, equal_nan=True)
    print(f"验证: {'通过' if is_correct_4 else '失败'}")
    if not is_correct_4:
        print(f"  期望: {expected_4}")
        print(f"  实际: {n_4}")
    print()
    
    print("=" * 50)
    print("所有边界情况测试完成！")
    print("=" * 50)
    print()


def test_barslast_example2_additional_cases():
    """测试示例2的额外边界情况：更细致的场景测试"""
    print("=" * 50)
    print("测试15: 示例2额外边界情况 - 更细致的场景")
    print("=" * 50)
    print("测试公式: N:=BARSLAST(DATE<>REF(DATE,1))+1")
    print()
    
    # 场景5: 每天只有1根k线（极端情况）
    print("场景5: 每天只有1根k线（极端情况）")
    print("-" * 50)
    date_array_5 = np.array([
        20240101,  # 第1天
        20240102,  # 第2天
        20240103,  # 第3天
        20240104,  # 第4天
        20240105,  # 第5天
    ])
    ref_date_5 = REF(date_array_5, 1)
    date_changed_5 = date_array_5 != ref_date_5
    barslast_result_5 = BARSLAST(date_changed_5)
    n_5 = barslast_result_5 + 1
    print(f"日期数组: {date_array_5}")
    print(f"日期变化条件: {date_changed_5}")
    print(f"BARSLAST结果: {barslast_result_5}")
    print(f"当日k线数N: {n_5}")
    expected_5 = np.array([1., 1., 1., 1., 1.])
    is_correct_5 = np.allclose(n_5, expected_5, equal_nan=True)
    print(f"验证: {'通过' if is_correct_5 else '失败'}")
    if not is_correct_5:
        print(f"  期望: {expected_5}")
        print(f"  实际: {n_5}")
    print()
    
    # 场景6: 第一根k线REF(DATE,1)为NaN的明确测试
    print("场景6: 第一根k线REF(DATE,1)为NaN的明确测试")
    print("-" * 50)
    date_array_6 = np.array([
        20240101,  # 第1根k线，REF(DATE,1)应该是NaN
        20240101, 20240101,  # 继续第1天
        20240102, 20240102,  # 第2天
    ])
    ref_date_6 = REF(date_array_6, 1)
    date_changed_6 = date_array_6 != ref_date_6
    barslast_result_6 = BARSLAST(date_changed_6)
    n_6 = barslast_result_6 + 1
    print(f"日期数组: {date_array_6}")
    print(f"REF(DATE, 1): {ref_date_6}")
    print(f"日期变化条件 (DATE<>REF(DATE,1)): {date_changed_6}")
    print(f"BARSLAST结果: {barslast_result_6}")
    print(f"当日k线数N: {n_6}")
    # 第一根k线：REF(DATE,1)=NaN，所以DATE<>REF(DATE,1)=True（因为NaN != 任何值）
    # 因此BARSLAST=0，N=1
    expected_6 = np.array([1., 2., 3., 1., 2.])
    is_correct_6 = np.allclose(n_6, expected_6, equal_nan=True)
    print(f"验证: {'通过' if is_correct_6 else '失败'}")
    if not is_correct_6:
        print(f"  期望: {expected_6}")
        print(f"  实际: {n_6}")
    print()
    
    # 场景7: 模拟实际分钟K线场景（一天240根，分多天）
    print("场景7: 模拟实际分钟K线场景（一天多根k线，分多天）")
    print("-" * 50)
    # 模拟3个交易日，每天4根k线（简化版，实际可能是240根）
    date_array_7 = np.array([
        # 2024-01-01: 4根k线
        20240101, 20240101, 20240101, 20240101,
        # 2024-01-02: 4根k线
        20240102, 20240102, 20240102, 20240102,
        # 2024-01-03: 4根k线
        20240103, 20240103, 20240103, 20240103,
    ])
    ref_date_7 = REF(date_array_7, 1)
    date_changed_7 = date_array_7 != ref_date_7
    barslast_result_7 = BARSLAST(date_changed_7)
    n_7 = barslast_result_7 + 1
    print(f"日期数组长度: {len(date_array_7)}")
    print(f"日期数组: {date_array_7}")
    print(f"日期变化条件: {date_changed_7}")
    print(f"BARSLAST结果: {barslast_result_7}")
    print(f"当日k线数N: {n_7}")
    expected_7 = np.array([
        1., 2., 3., 4.,  # 第1天
        1., 2., 3., 4.,  # 第2天
        1., 2., 3., 4.,  # 第3天
    ])
    is_correct_7 = np.allclose(n_7, expected_7, equal_nan=True)
    print(f"验证: {'通过' if is_correct_7 else '失败'}")
    if not is_correct_7:
        print(f"  期望: {expected_7}")
        print(f"  实际: {n_7}")
    print()
    
    # 场景8: 测试公式的正确性验证（重点验证"+1"的必要性）
    print("场景8: 验证公式中'+1'的必要性")
    print("-" * 50)
    print("说明: 由于条件成立的当根k线上BARSLAST(COND)的返回值为0，")
    print("      所以'+1'才是当日k线根数。")
    print()
    date_array_8 = np.array([
        20240101, 20240101, 20240101,  # 第1天，3根k线
        20240102, 20240102,  # 第2天，2根k线
    ])
    ref_date_8 = REF(date_array_8, 1)
    date_changed_8 = date_array_8 != ref_date_8
    barslast_result_8 = BARSLAST(date_changed_8)
    n_8 = barslast_result_8 + 1
    print(f"日期数组: {date_array_8}")
    print(f"日期变化条件: {date_changed_8}")
    print(f"BARSLAST结果: {barslast_result_8}")
    print(f"不加1的结果: {barslast_result_8} (错误：第一根k线显示0)")
    print(f"加1后的结果N: {n_8} (正确：第一根k线显示1)")
    print()
    print("验证点:")
    print(f"  位置0: 日期变化点，BARSLAST={barslast_result_8[0]}, N={n_8[0]}")
    print(f"        如果不加1，第一根k线会显示0，这是错误的")
    print(f"        加1后，第一根k线正确显示1")
    print(f"  位置1: 同一日，BARSLAST={barslast_result_8[1]}, N={n_8[1]} (应该是2)")
    print(f"  位置2: 同一日，BARSLAST={barslast_result_8[2]}, N={n_8[2]} (应该是3)")
    print(f"  位置3: 日期变化点，BARSLAST={barslast_result_8[3]}, N={n_8[3]} (应该是1)")
    print(f"  位置4: 同一日，BARSLAST={barslast_result_8[4]}, N={n_8[4]} (应该是2)")
    expected_8 = np.array([1., 2., 3., 1., 2.])
    is_correct_8 = np.allclose(n_8, expected_8, equal_nan=True)
    print(f"验证: {'通过' if is_correct_8 else '失败'}")
    if not is_correct_8:
        print(f"  期望: {expected_8}")
        print(f"  实际: {n_8}")
    print()
    
    print("=" * 50)
    print("所有额外边界情况测试完成！")
    print("=" * 50)
    print()


if __name__ == "__main__":
    test_ref_basic()
    test_ref_zero()
    test_ref_insufficient_data()
    test_ref_none()
    test_ref_negative()
    test_ref_array_n()
    test_ref_example()
    
    test_barslast_basic()
    test_barslast_example1()
    test_barslast_never_true()
    test_barslast_all_true()
    test_barslast_example2()
    test_barslast_example2_complete()
    test_barslast_example2_edge_cases()
    test_barslast_example2_additional_cases()
    
    print("=" * 50)
    print("所有测试完成！")
    print("=" * 50)

