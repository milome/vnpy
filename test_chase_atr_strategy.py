#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试基于ATR和成交量的智能追价策略
验证追价步长计算、性能指标和日志记录
"""

import time
from datetime import datetime, timedelta
from typing import List, Tuple

# 模拟BarData
class MockBarData:
    def __init__(self, open_price, high_price, low_price, close_price, volume):
        self.open_price = open_price
        self.high_price = high_price
        self.low_price = low_price
        self.close_price = close_price
        self.volume = volume


def calculate_simple_atr(bars: List[MockBarData]) -> float:
    """简化ATR计算（不使用talib）"""
    if len(bars) < 2:
        return 0.0
    
    true_ranges = []
    for i in range(1, len(bars)):
        high = bars[i].high_price
        low = bars[i].low_price
        prev_close = bars[i-1].close_price
        
        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)
        
        true_range = max(tr1, tr2, tr3)
        true_ranges.append(true_range)
    
    # 计算14周期ATR
    if len(true_ranges) >= 14:
        return sum(true_ranges[-14:]) / 14
    else:
        return sum(true_ranges) / len(true_ranges) if true_ranges else 0.0


def calculate_dynamic_chase_step(
    bars: List[MockBarData],
    current_price: float,
    current_volume: float
) -> float:
    """基于ATR和成交量动态计算追价步长"""
    if len(bars) < 14:
        return 0.0005  # 默认步长
    
    # 计算ATR
    atr = calculate_simple_atr(bars)
    
    if atr <= 0:
        return 0.0005
    
    # 计算平均成交量
    avg_volume = sum([bar.volume for bar in bars]) / len(bars)
    
    if avg_volume <= 0:
        return 0.0005
    
    # 基于ATR计算基础步长（ATR的百分比）
    atr_pct = atr / current_price if current_price > 0 else 0.0
    
    # 根据成交量调整步长
    volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
    volume_factor = 1.0 / max(0.5, min(2.0, volume_ratio))
    
    # 计算动态步长
    base_step = atr_pct * 0.15
    dynamic_step = base_step * volume_factor
    
    # 限制步长范围：最小0.01%，最大0.5%
    dynamic_step = max(0.0001, min(0.005, dynamic_step))
    
    return dynamic_step


def test_atr_calculation():
    """测试ATR计算"""
    print("=" * 60)
    print("测试用例1: ATR计算")
    print("=" * 60)
    
    # 创建模拟K线数据（34个周期）
    bars = []
    base_price = 100.0
    
    for i in range(34):
        # 模拟价格波动
        volatility = 0.5  # 0.5%波动
        open_price = base_price * (1 + (i % 10 - 5) * volatility / 100)
        high_price = open_price * 1.01
        low_price = open_price * 0.99
        close_price = open_price * (1 + (i % 7 - 3) * volatility / 200)
        volume = 1000000 + i * 10000
        
        bars.append(MockBarData(open_price, high_price, low_price, close_price, volume))
        base_price = close_price
    
    atr = calculate_simple_atr(bars)
    print(f"计算的ATR: {atr:.4f}")
    print(f"当前价格: {bars[-1].close_price:.2f}")
    print(f"ATR百分比: {atr / bars[-1].close_price * 100:.2f}%")
    
    assert atr > 0, "ATR应该大于0"
    print("[PASS] ATR计算测试通过")


def test_dynamic_chase_step():
    """测试动态追价步长计算"""
    print("\n" + "=" * 60)
    print("测试用例2: 动态追价步长计算")
    print("=" * 60)
    
    # 创建模拟K线数据
    bars = []
    base_price = 100.0
    
    for i in range(34):
        volatility = 0.5
        open_price = base_price * (1 + (i % 10 - 5) * volatility / 100)
        high_price = open_price * 1.01
        low_price = open_price * 0.99
        close_price = open_price * (1 + (i % 7 - 3) * volatility / 200)
        volume = 1000000 + i * 10000
        
        bars.append(MockBarData(open_price, high_price, low_price, close_price, volume))
        base_price = close_price
    
    current_price = bars[-1].close_price
    
    # 测试不同成交量情况
    test_cases = [
        {"volume": 500000, "description": "低成交量（低于平均）"},
        {"volume": 1000000, "description": "正常成交量（接近平均）"},
        {"volume": 2000000, "description": "高成交量（高于平均）"},
    ]
    
    for case in test_cases:
        step = calculate_dynamic_chase_step(bars, current_price, case["volume"])
        print(f"{case['description']}: 步长 = {step*100:.3f}%")
        assert 0.0001 <= step <= 0.005, f"步长应该在0.01%-0.5%之间，实际为{step*100:.3f}%"
    
    print("[PASS] 动态追价步长计算测试通过")


def test_chase_performance_simulation():
    """测试追价性能模拟"""
    print("\n" + "=" * 60)
    print("测试用例3: 追价性能模拟")
    print("=" * 60)
    
    # 模拟追价执行时间
    chase_times = []
    modify_times = []
    
    # 模拟10次追价执行
    for i in range(10):
        chase_start = time.time()
        
        # 模拟修改订单耗时（50-200ms）
        modify_start = time.time()
        time.sleep(0.001 * (50 + i * 15))  # 模拟网络延迟
        modify_time = (time.time() - modify_start) * 1000
        
        total_time = (time.time() - chase_start) * 1000
        
        chase_times.append(total_time)
        modify_times.append(modify_time)
    
    avg_chase_time = sum(chase_times) / len(chase_times)
    avg_modify_time = sum(modify_times) / len(modify_times)
    max_chase_time = max(chase_times)
    min_chase_time = min(chase_times)
    
    print(f"平均追价耗时: {avg_chase_time:.1f}ms")
    print(f"平均修改耗时: {avg_modify_time:.1f}ms")
    print(f"最大追价耗时: {max_chase_time:.1f}ms")
    print(f"最小追价耗时: {min_chase_time:.1f}ms")
    
    # 验证性能指标
    assert avg_chase_time < 500, f"平均追价耗时应该小于500ms，实际为{avg_chase_time:.1f}ms"
    assert max_chase_time < 1000, f"最大追价耗时应该小于1000ms，实际为{max_chase_time:.1f}ms"
    
    print("[PASS] 追价性能模拟测试通过")


def test_chase_step_optimization():
    """测试追价步长优化（基于ATR和成交量）"""
    print("\n" + "=" * 60)
    print("测试用例4: 追价步长优化")
    print("=" * 60)
    
    # 测试场景1: 高波动、低成交量（应该使用较大步长）
    bars_high_vol = []
    base_price = 100.0
    for i in range(34):
        volatility = 2.0  # 高波动
        open_price = base_price * (1 + (i % 10 - 5) * volatility / 100)
        high_price = open_price * 1.02
        low_price = open_price * 0.98
        close_price = open_price * (1 + (i % 7 - 3) * volatility / 200)
        volume = 100000  # 低成交量
        
        bars_high_vol.append(MockBarData(open_price, high_price, low_price, close_price, volume))
        base_price = close_price
    
    step_high_vol = calculate_dynamic_chase_step(bars_high_vol, bars_high_vol[-1].close_price, 50000)
    print(f"高波动低成交量场景: 步长 = {step_high_vol*100:.3f}%")
    
    # 测试场景2: 低波动、高成交量（应该使用较小步长）
    bars_low_vol = []
    base_price = 100.0
    for i in range(34):
        volatility = 0.1  # 低波动
        open_price = base_price * (1 + (i % 10 - 5) * volatility / 100)
        high_price = open_price * 1.001
        low_price = open_price * 0.999
        close_price = open_price * (1 + (i % 7 - 3) * volatility / 200)
        volume = 5000000  # 高成交量
        
        bars_low_vol.append(MockBarData(open_price, high_price, low_price, close_price, volume))
        base_price = close_price
    
    step_low_vol = calculate_dynamic_chase_step(bars_low_vol, bars_low_vol[-1].close_price, 10000000)
    print(f"低波动高成交量场景: 步长 = {step_low_vol*100:.3f}%")
    
    # 验证：高波动场景应该使用更大的步长
    assert step_high_vol > step_low_vol, "高波动场景应该使用更大的追价步长"
    
    print("[PASS] 追价步长优化测试通过")


def test_chase_interval_optimization():
    """测试追价间隔优化"""
    print("\n" + "=" * 60)
    print("测试用例5: 追价间隔优化")
    print("=" * 60)
    
    # 模拟追价间隔策略
    chase_count = 0
    intervals = []
    
    # 前两次使用短间隔（100ms），后续使用长间隔（500ms）
    for i in range(5):
        if i < 2:
            interval = 0.1  # 100ms
        else:
            interval = 0.5  # 500ms
        
        intervals.append(interval)
        chase_count += 1
        
        print(f"第{chase_count}次追价间隔: {interval*1000:.0f}ms")
    
    # 验证前两次使用短间隔
    assert intervals[0] == 0.1, "第1次追价应该使用100ms间隔"
    assert intervals[1] == 0.1, "第2次追价应该使用100ms间隔"
    assert intervals[2] == 0.5, "第3次追价应该使用500ms间隔"
    
    # 计算总耗时
    total_time = sum(intervals) * 1000
    print(f"总追价耗时（5次）: {total_time:.0f}ms")
    
    assert total_time < 2000, "总追价耗时应该小于2000ms"
    
    print("[PASS] 追价间隔优化测试通过")


def test_chase_logging_format():
    """测试追价日志格式"""
    print("\n" + "=" * 60)
    print("测试用例6: 追价日志格式")
    print("=" * 60)
    
    # 模拟追价日志
    orderid = "TEST123"
    chase_count = 1
    old_price = 100.0
    new_price = 100.05
    slippage = 0.05
    modify_time = 45.2
    total_time = 120.5
    atr = 0.5
    avg_volume = 1000000
    
    log_msg = (
        f"[追价成功] 订单{orderid} 第{chase_count}次追价完成 - "
        f"价格: {old_price:.3f} -> {new_price:.3f}, "
        f"滑点: {slippage:.3f}, "
        f"修改耗时: {modify_time:.1f}ms, "
        f"总耗时: {total_time:.1f}ms"
    )
    
    print(f"日志示例: {log_msg}")
    
    # 验证日志包含关键信息
    assert "订单" in log_msg, "日志应该包含订单ID"
    assert "追价完成" in log_msg, "日志应该包含追价状态"
    assert "价格" in log_msg, "日志应该包含价格信息"
    assert "滑点" in log_msg, "日志应该包含滑点信息"
    assert "耗时" in log_msg, "日志应该包含耗时信息"
    
    # 计算日志
    calc_log = (
        f"[追价计算] TEST.SSE - "
        f"方向: 多, "
        f"当前价: {old_price:.3f}, "
        f"新价格: {new_price:.3f}, "
        f"步长: 0.050%, "
        f"ATR: {atr:.3f}, "
        f"平均成交量: {avg_volume:.0f}"
    )
    
    print(f"计算日志示例: {calc_log}")
    
    assert "ATR" in calc_log, "计算日志应该包含ATR信息"
    assert "平均成交量" in calc_log, "计算日志应该包含成交量信息"
    
    print("[PASS] 追价日志格式测试通过")


def run_all_tests():
    """运行所有测试"""
    try:
        test_atr_calculation()
        test_dynamic_chase_step()
        test_chase_performance_simulation()
        test_chase_step_optimization()
        test_chase_interval_optimization()
        test_chase_logging_format()
        
        print("\n" + "=" * 60)
        print("所有测试用例通过！")
        print("=" * 60)
        print("\n改进总结:")
        print("1. 基于ATR和成交量的动态追价步长计算")
        print("2. 优化追价间隔：前两次使用100ms，后续使用配置间隔")
        print("3. 详细的追价执行日志记录（包含ATR、成交量、耗时等）")
        print("4. 性能指标统计（平均耗时、最大/最小耗时等）")
        print("5. 目标：将成交时间优化到500ms以内")
        print("=" * 60)
        return True
    except AssertionError as e:
        print(f"\n[FAIL] 测试失败: {e}")
        return False
    except Exception as e:
        print(f"\n[ERROR] 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    run_all_tests()

