#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断脚本：检查数据库中1小时K线数据的存储情况
"""
import sys
import io

# 设置标准输出编码为UTF-8
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from datetime import datetime
from vnpy.trader.database import get_database, BarOverview
from vnpy.trader.constant import Interval, Exchange

def check_hour_data():
    """检查数据库中是否有1小时K线数据"""
    print("=" * 70)
    print("诊断：检查数据库中1小时K线数据的存储情况")
    print("=" * 70)
    
    # 获取数据库实例
    database = get_database()
    if not database:
        print("[ERROR] 无法获取数据库实例")
        return
    
    print("\n[1/4] 获取数据库类型...")
    print(f"  数据库类型: {type(database).__name__}")
    
    print("\n[2/4] 查询K线数据概览...")
    
    try:
        bar_overviews = database.get_bar_overview()
        print(f"  [OK] 成功查询数据库，共找到 {len(bar_overviews)} 条K线汇总记录")
    except Exception as e:
        print(f"  [ERROR] 查询数据库失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return
    
    if not bar_overviews:
        print("\n[WARNING] 数据库中没有任何K线汇总数据")
        return
    
    print("\n[3/4] 分析各周期的K线数据:")
    print("-" * 70)
    
    # 按周期分组统计
    interval_stats = {}
    for overview in bar_overviews:
        interval = overview.interval
        
        # 获取interval信息
        if interval is None:
            interval_key = "None"
            interval_value = None
        elif hasattr(interval, 'value'):
            interval_key = interval.value
            interval_value = interval
        elif isinstance(interval, str):
            interval_key = interval
            interval_value = interval
        else:
            interval_key = str(type(interval)) + ":" + str(interval)
            interval_value = interval
        
        if interval_key not in interval_stats:
            interval_stats[interval_key] = {
                'count': 0,
                'examples': [],
                'interval_type': type(interval).__name__,
                'interval_obj': interval_value
            }
        
        interval_stats[interval_key]['count'] += 1
        if len(interval_stats[interval_key]['examples']) < 2:
            interval_stats[interval_key]['examples'].append({
                'symbol': overview.symbol,
                'exchange': getattr(overview.exchange, 'value', str(overview.exchange)) if overview.exchange else None,
                'data_count': overview.count,
                'start': str(overview.start) if overview.start else None,
                'end': str(overview.end) if overview.end else None,
            })
    
    # 显示统计结果
    print(f"{'周期':<15} {'类型':<20} {'合约数':<10} {'示例'}")
    print("-" * 70)
    
    hour_found = False
    for interval_key, stats in sorted(interval_stats.items()):
        if interval_key == "1h":
            hour_found = True
            print(f"{'>>> ' + interval_key:<15} {stats['interval_type']:<20} {stats['count']:<10} {stats['examples'][0]['symbol'] if stats['examples'] else 'N/A'}")
        else:
            print(f"{interval_key:<15} {stats['interval_type']:<20} {stats['count']:<10} {stats['examples'][0]['symbol'] if stats['examples'] else 'N/A'}")
    
    print("\n[4/4] 验证Interval枚举匹配:")
    print("-" * 70)
    
    # 验证枚举匹配
    print(f"  Interval.HOUR = {Interval.HOUR}")
    print(f"  Interval.HOUR.value = '{Interval.HOUR.value}'")
    print(f"  Interval('1h') = {Interval('1h')}")
    print(f"  Interval.HOUR.value == '1h': {Interval.HOUR.value == '1h'}")
    
    # 检查数据库中是否有1小时数据
    print("\n" + "=" * 70)
    if hour_found:
        print("[结果] 数据库中存在 1小时 (1h) 的K线汇总数据")
        print(f"  共 {interval_stats['1h']['count']} 个合约有1小时数据")
        for ex in interval_stats['1h']['examples']:
            print(f"  - {ex['symbol']}.{ex['exchange']}: {ex['data_count']}条数据, {ex['start']} ~ {ex['end']}")
    else:
        print("[结果] 数据库中 没有找到 1小时 (1h) 的K线汇总数据")
        print("\n可能的原因:")
        print("  1. 数据下载失败 - 检查下载时的日志输出")
        print("  2. DbBarOverview表未正确更新 - 需检查save_bar_data逻辑")
        print("  3. interval值格式不匹配 - 数据库中可能存储了其他格式")
    
    # 检查实际数据表中的interval值
    print("\n[额外检查] 直接查询DbBarData表中的interval值...")
    try:
        from peewee import SqliteDatabase as PeeweeSqliteDatabase
        from vnpy.trader.utility import get_file_path
        
        path = str(get_file_path("database.db"))
        db = PeeweeSqliteDatabase(path)
        
        cursor = db.execute_sql("""
            SELECT DISTINCT interval, COUNT(*) as cnt 
            FROM dbbardata 
            GROUP BY interval
        """)
        
        print(f"  DbBarData表中的interval分布:")
        for row in cursor.fetchall():
            interval_val, cnt = row
            marker = " <<<" if interval_val == "1h" else ""
            print(f"    {interval_val}: {cnt}条记录{marker}")
            
        # 同时检查DbBarOverview表
        cursor2 = db.execute_sql("""
            SELECT DISTINCT interval, COUNT(*) as cnt 
            FROM dbbaroverview 
            GROUP BY interval
        """)
        
        print(f"\n  DbBarOverview表中的interval分布:")
        for row in cursor2.fetchall():
            interval_val, cnt = row
            marker = " <<<" if interval_val == "1h" else ""
            print(f"    {interval_val}: {cnt}条记录{marker}")
            
    except Exception as e:
        print(f"  [跳过] 无法直接查询数据库表: {e}")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    check_hour_data()

