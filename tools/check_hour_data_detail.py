#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细诊断脚本：检查最近保存的数据和 interval 类型
"""
import sys
import io

# 设置标准输出编码为UTF-8
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from datetime import datetime, timedelta
from vnpy.trader.utility import get_file_path

def check_recent_data():
    """检查最近保存的数据"""
    print("=" * 70)
    print("详细诊断：检查最近保存的K线数据")
    print("=" * 70)
    
    from peewee import SqliteDatabase as PeeweeSqliteDatabase
    
    path = str(get_file_path("database.db"))
    print(f"\n数据库路径: {path}")
    
    db = PeeweeSqliteDatabase(path)
    
    # 1. 检查所有 interval 值和数量
    print("\n[1/4] 检查 DbBarData 表中所有 interval 值:")
    print("-" * 70)
    cursor = db.execute_sql("""
        SELECT interval, symbol, exchange, COUNT(*) as cnt,
               MIN(datetime) as min_dt, MAX(datetime) as max_dt
        FROM dbbardata 
        GROUP BY interval, symbol, exchange
        ORDER BY interval, symbol
    """)
    
    for row in cursor.fetchall():
        interval_val, symbol, exchange, cnt, min_dt, max_dt = row
        marker = " <<< 目标" if interval_val == "1h" else ""
        print(f"  {interval_val:8} | {symbol:12} | {exchange:10} | {cnt:>10,}条 | {min_dt} ~ {max_dt}{marker}")
    
    # 2. 检查 MHImain 合约的所有数据
    print("\n[2/4] 检查 MHImain 合约的数据分布:")
    print("-" * 70)
    cursor2 = db.execute_sql("""
        SELECT interval, COUNT(*) as cnt
        FROM dbbardata 
        WHERE symbol = 'MHImain'
        GROUP BY interval
        ORDER BY interval
    """)
    
    for row in cursor2.fetchall():
        interval_val, cnt = row
        marker = " <<< 应该有1h数据" if interval_val == "1h" else ""
        print(f"  {interval_val}: {cnt:,}条{marker}")
    
    # 3. 检查最近24小时内保存的数据
    print("\n[3/4] 检查最近保存的数据（按 datetime 排序前20条）:")
    print("-" * 70)
    cursor3 = db.execute_sql("""
        SELECT symbol, exchange, interval, datetime, close_price
        FROM dbbardata 
        WHERE symbol = 'MHImain'
        ORDER BY datetime DESC
        LIMIT 20
    """)
    
    print(f"  {'symbol':12} | {'exchange':10} | {'interval':8} | {'datetime':20} | {'close'}")
    print("-" * 70)
    for row in cursor3.fetchall():
        symbol, exchange, interval, dt, close = row
        print(f"  {symbol:12} | {exchange:10} | {interval:8} | {dt:20} | {close}")
    
    # 4. 检查是否有任何 1h 数据
    print("\n[4/4] 直接搜索 interval='1h' 的数据:")
    print("-" * 70)
    cursor4 = db.execute_sql("""
        SELECT COUNT(*) as cnt
        FROM dbbardata 
        WHERE interval = '1h'
    """)
    count_1h = cursor4.fetchone()[0]
    
    if count_1h > 0:
        print(f"  找到 {count_1h} 条 1h 数据!")
        # 显示一些示例
        cursor5 = db.execute_sql("""
            SELECT symbol, exchange, datetime, close_price
            FROM dbbardata 
            WHERE interval = '1h'
            ORDER BY datetime DESC
            LIMIT 5
        """)
        for row in cursor5.fetchall():
            print(f"    {row}")
    else:
        print("  没有找到任何 interval='1h' 的数据!")
        print("\n  可能原因分析:")
        print("  - 数据下载时 interval 被错误地设置为其他值")
        print("  - 让我们检查 BarData 对象的 interval 属性...")
    
    # 5. 检查 DbBarOverview 表
    print("\n[5/5] 检查 DbBarOverview 表:")
    print("-" * 70)
    cursor6 = db.execute_sql("""
        SELECT symbol, exchange, interval, count, start, end
        FROM dbbaroverview 
        ORDER BY interval, symbol
    """)
    
    print(f"  {'symbol':12} | {'exchange':10} | {'interval':8} | {'count':>10} | {'start':20} | {'end':20}")
    print("-" * 70)
    for row in cursor6.fetchall():
        symbol, exchange, interval, count, start, end = row
        marker = " <<<" if interval == "1h" else ""
        print(f"  {symbol:12} | {exchange:10} | {interval:8} | {count:>10,} | {start:20} | {end:20}{marker}")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    check_recent_data()

