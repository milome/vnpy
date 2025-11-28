#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查BarGenerator合成5分钟、1小时、4小时的时间边界
"""
from datetime import datetime, timedelta
from vnpy.trader.constant import Interval
from vnpy.trader.object import BarData
from vnpy.trader.utility import BarGenerator
from zoneinfo import ZoneInfo

# 使用数据库时区
DB_TZ = ZoneInfo("Asia/Shanghai")

def test_bar_generator_periods():
    """测试BarGenerator的时间边界"""
    print("=" * 80)
    print("检查BarGenerator合成5分钟、1小时、4小时的时间边界")
    print("=" * 80)
    
    # 创建测试用的1分钟K线数据
    test_minute_bars = []
    base_time = datetime(2025, 11, 28, 17, 15, 0, tzinfo=DB_TZ)
    
    # 生成一些1分钟K线数据（从17:15到18:30）
    for i in range(75):  # 75分钟
        dt = base_time + timedelta(minutes=i)
        bar = BarData(
            symbol="MHImain",
            exchange=None,  # 简化测试
            datetime=dt,
            interval=Interval.MINUTE,
            open_price=100.0 + i * 0.1,
            high_price=100.0 + i * 0.1 + 0.5,
            low_price=100.0 + i * 0.1 - 0.5,
            close_price=100.0 + i * 0.1 + 0.2,
            volume=1000.0,
            turnover=100000.0,
            open_interest=0.0,
            gateway_name="TEST"
        )
        test_minute_bars.append(bar)
    
    print(f"\n生成了 {len(test_minute_bars)} 根1分钟K线")
    print(f"时间范围: {test_minute_bars[0].datetime} ~ {test_minute_bars[-1].datetime}")
    
    # 测试5分钟合成
    print("\n" + "=" * 80)
    print("1. 测试5分钟K线合成（window=5）")
    print("-" * 80)
    five_min_bars = []
    
    def on_5min_bar(bar):
        five_min_bars.append(bar)
    
    bg_5m = BarGenerator(on_5min_bar, window=5, on_window_bar=on_5min_bar)
    
    for bar in test_minute_bars:
        bg_5m.update_bar(bar)
    
    print(f"合成了 {len(five_min_bars)} 根5分钟K线:")
    for bar in five_min_bars:
        print(f"  时间戳: {bar.datetime.strftime('%Y-%m-%d %H:%M:%S')}, "
              f"开盘: {bar.open_price:.2f}, 收盘: {bar.close_price:.2f}")
    
    # 测试1小时合成
    print("\n" + "=" * 80)
    print("2. 测试1小时K线合成（interval=HOUR, window=1）")
    print("-" * 80)
    hour_bars = []
    
    def on_hour_bar(bar):
        hour_bars.append(bar)
    
    bg_1h = BarGenerator(on_hour_bar, window=1, on_window_bar=on_hour_bar, interval=Interval.HOUR)
    
    for bar in test_minute_bars:
        bg_1h.update_bar(bar)
    
    print(f"合成了 {len(hour_bars)} 根1小时K线:")
    for bar in hour_bars:
        print(f"  时间戳: {bar.datetime.strftime('%Y-%m-%d %H:%M:%S')}, "
              f"开盘: {bar.open_price:.2f}, 收盘: {bar.close_price:.2f}")
    
    # 测试4小时合成
    print("\n" + "=" * 80)
    print("3. 测试4小时K线合成（interval=HOUR, window=4）")
    print("-" * 80)
    four_hour_bars = []
    
    def on_4h_bar(bar):
        four_hour_bars.append(bar)
    
    bg_4h = BarGenerator(on_hour_bar, window=4, on_window_bar=on_4h_bar, interval=Interval.HOUR)
    
    # 生成更多数据用于4小时测试（需要至少4小时的数据）
    extended_bars = []
    for i in range(240):  # 4小时 = 240分钟
        dt = base_time + timedelta(minutes=i)
        bar = BarData(
            symbol="MHImain",
            exchange=None,
            datetime=dt,
            interval=Interval.MINUTE,
            open_price=100.0 + i * 0.1,
            high_price=100.0 + i * 0.1 + 0.5,
            low_price=100.0 + i * 0.1 - 0.5,
            close_price=100.0 + i * 0.1 + 0.2,
            volume=1000.0,
            turnover=100000.0,
            open_interest=0.0,
            gateway_name="TEST"
        )
        extended_bars.append(bar)
    
    for bar in extended_bars:
        bg_4h.update_bar(bar)
    
    print(f"合成了 {len(four_hour_bars)} 根4小时K线:")
    for bar in four_hour_bars:
        print(f"  时间戳: {bar.datetime.strftime('%Y-%m-%d %H:%M:%S')}, "
              f"开盘: {bar.open_price:.2f}, 收盘: {bar.close_price:.2f}")
    
    # 分析时间边界
    print("\n" + "=" * 80)
    print("时间边界分析:")
    print("-" * 80)
    
    print("\n5分钟K线时间边界规则:")
    print("  - BarGenerator使用: (minute + 1) % window == 0 来判断是否完成")
    print("  - 例如: window=5时，在分钟数为4, 9, 14, 19, ... 时完成")
    print("  - 时间戳: 使用第一根1分钟K线的时间，但将秒和微秒设为0")
    print("  - 问题: 不遵循港期交易时段边界")
    
    print("\n1小时K线时间边界规则:")
    print("  - BarGenerator使用: minute == 59 或 hour 变化来判断是否完成")
    print("  - 时间戳: 使用 hour:00:00 (例如 17:00:00)")
    print("  - 问题: 不遵循港期交易时段边界（应该是17:15-18:14等）")
    
    print("\n4小时K线时间边界规则:")
    print("  - BarGenerator使用: window=4，每4小时完成一次")
    print("  - 时间戳: 使用 hour:00:00，且hour是4的倍数 (例如 16:00:00, 20:00:00)")
    print("  - 问题: 不遵循港期交易时段边界（应该是17:15-21:14等）")
    
    print("\n" + "=" * 80)
    print("结论:")
    print("-" * 80)
    print("BarGenerator使用简单的时间整除规则，不适用于港期交易时段边界。")
    print("因此，对于港期数据，必须使用DataManager的精确合成逻辑。")

if __name__ == "__main__":
    test_bar_generator_periods()

