#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查数据库中的5分钟K线数据
"""
import sys
import io
# 设置标准输出编码为UTF-8
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from datetime import datetime
from vnpy.trader.database import get_database
from vnpy.trader.constant import Interval, Exchange

def check_5m_bar_data():
    """检查数据库中是否有5分钟K线数据"""
    print("=" * 60)
    print("检查数据库中的5分钟K线数据")
    print("=" * 60)
    
    # 获取数据库实例
    database = get_database()
    if not database:
        print("错误：无法获取数据库实例")
        return
    
    print("\n[1/3] 查询数据库中的所有K线数据概览...")
    
    # 获取所有K线数据概览
    try:
        bar_overviews = database.get_bar_overview()
        print(f"[OK] 成功查询数据库，共找到 {len(bar_overviews)} 条K线数据记录")
    except Exception as e:
        print(f"[ERROR] 查询数据库失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return
    
    if not bar_overviews:
        print("\n[WARNING] 数据库中没有任何K线数据")
        return
    
    # 统计各周期的数据
    interval_stats = {}
    for overview in bar_overviews:
        interval = overview.interval
        if interval:
            interval_value = interval.value
            if interval_value not in interval_stats:
                interval_stats[interval_value] = []
            interval_stats[interval_value].append(overview)
    
    print(f"\n[2/3] 统计各周期的K线数据:")
    print("-" * 60)
    
    # 按周期分组显示
    for interval_value in sorted(interval_stats.keys()):
        overviews = interval_stats[interval_value]
        total_count = sum(ov.count for ov in overviews)
        symbols = [f"{ov.symbol}.{ov.exchange.value}" if ov.exchange else ov.symbol 
                   for ov in overviews]
        print(f"\n周期: {interval_value}")
        print(f"  记录数: {len(overviews)} 个合约")
        print(f"  总K线数: {total_count:,} 条")
        
        # 显示每个合约的信息
        for overview in overviews[:5]:  # 只显示前5个合约
            symbol_str = f"{overview.symbol}.{overview.exchange.value}" if overview.exchange else overview.symbol
            start_str = overview.start.strftime("%Y-%m-%d") if overview.start else "未知"
            end_str = overview.end.strftime("%Y-%m-%d") if overview.end else "未知"
            print(f"    - {symbol_str}: {overview.count:,} 条 ({start_str} ~ {end_str})")
        
        if len(overviews) > 5:
            print(f"    ... 还有 {len(overviews) - 5} 个合约")
    
    print("\n" + "-" * 60)
    
    # 检查5分钟周期的数据
    print("\n[3/3] 检查5分钟周期的K线数据:")
    print("-" * 60)
    
    five_min_overviews = interval_stats.get("5m", [])
    
    if five_min_overviews:
        print(f"[OK] 找到 {len(five_min_overviews)} 个合约的5分钟K线数据:")
        total_5m_count = sum(ov.count for ov in five_min_overviews)
        print(f"  总K线数: {total_5m_count:,} 条")
        
        # 显示详细列表
        for overview in five_min_overviews:
            symbol_str = f"{overview.symbol}.{overview.exchange.value}" if overview.exchange else overview.symbol
            start_str = overview.start.strftime("%Y-%m-%d %H:%M") if overview.start else "未知"
            end_str = overview.end.strftime("%Y-%m-%d %H:%M") if overview.end else "未知"
            print(f"\n  合约: {symbol_str}")
            print(f"    K线数量: {overview.count:,} 条")
            print(f"    时间范围: {start_str} ~ {end_str}")
            
            # 检查MHImain的5分钟数据
            if "MHImain" in overview.symbol or "MHI" in overview.symbol:
                print(f"    [*] 这是MHI相关合约！")
    else:
        print("✗ 数据库中没有5分钟周期的K线数据")
        print("\n提示：")
        print("  1. 如果需要5分钟K线数据，可以在CTA回测界面下载")
        print("  2. 或者从1分钟K线数据合成5分钟K线")
        print("  3. 也可以使用数据服务直接下载5分钟K线数据")
    
    print("\n" + "=" * 60)
    
    # 检查是否有1分钟数据（可以从1分钟合成5分钟）
    one_min_overviews = interval_stats.get("1m", [])
    if not five_min_overviews and one_min_overviews:
        print("\n[建议]:")
        print(f"  数据库中有 {len(one_min_overviews)} 个合约的1分钟K线数据")
        print("  回测引擎可以从1分钟数据自动合成5分钟K线进行回测")
        
        # 显示有哪些合约有1分钟数据
        mhi_symbols = [ov for ov in one_min_overviews 
                      if "MHImain" in ov.symbol or "MHI" in ov.symbol]
        if mhi_symbols:
            print(f"\n  MHI相关合约的1分钟数据:")
            for overview in mhi_symbols:
                symbol_str = f"{overview.symbol}.{overview.exchange.value}" if overview.exchange else overview.symbol
                print(f"    - {symbol_str}: {overview.count:,} 条")
    
    print("=" * 60)


if __name__ == "__main__":
    check_5m_bar_data()

