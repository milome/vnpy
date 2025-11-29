"""
检查数据库中的K线数据记录
用于分析5分钟K线开盘价问题
"""
import sys
from datetime import datetime, timedelta
from vnpy.trader.constant import Interval, Exchange
from vnpy.trader.database import get_database
from vnpy.trader.utility import extract_vt_symbol
from vnpy.trader.database import DB_TZ

def check_bar_data(vt_symbol: str, target_time: datetime):
    """检查指定时间点的K线数据"""
    database = get_database()
    symbol, exchange = extract_vt_symbol(vt_symbol)
    
    print(f"\n{'='*80}")
    print(f"检查合约: {vt_symbol}")
    print(f"目标时间: {target_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")
    
    # 1. 检查5分钟K线（使用更宽松的范围）
    start_5m = target_time.replace(second=0, microsecond=0) - timedelta(hours=1)
    end_5m = start_5m + timedelta(hours=2)
    
    print("1. 检查5分钟K线数据（扩展查询范围）:")
    print(f"   查询范围: {start_5m.strftime('%Y-%m-%d %H:%M:%S')} ~ {end_5m.strftime('%Y-%m-%d %H:%M:%S')}")
    bars_5m = database.load_bar_data(
        symbol, exchange, Interval.MINUTE_5,
        start_5m, end_5m
    )
    
    # 筛选出目标时间附近的5分钟K线
    target_5m_bars = []
    for bar in bars_5m:
        bar_dt = bar.datetime.replace(tzinfo=DB_TZ) if not bar.datetime.tzinfo else bar.datetime
        if abs((bar_dt - target_time).total_seconds()) < 300:  # 5分钟内
            target_5m_bars.append(bar)
    
    bars_5m = target_5m_bars
    
    if bars_5m:
        for bar in bars_5m:
            print(f"   时间: {bar.datetime.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   开盘价: {bar.open_price}")
            print(f"   最高价: {bar.high_price}")
            print(f"   最低价: {bar.low_price}")
            print(f"   收盘价: {bar.close_price}")
            print(f"   成交量: {bar.volume}")
            print()
    else:
        print("   未找到5分钟K线数据\n")
    
    # 2. 检查该5分钟周期内的所有1分钟K线（使用更宽松的范围）
    start_1m = target_time.replace(second=0, microsecond=0) - timedelta(hours=1)
    end_1m = start_1m + timedelta(hours=2)
    
    print("\n2. 检查该5分钟周期内的1分钟K线数据（扩展查询范围）:")
    print(f"   查询范围: {start_1m.strftime('%Y-%m-%d %H:%M:%S')} ~ {end_1m.strftime('%Y-%m-%d %H:%M:%S')}")
    bars_1m_all = database.load_bar_data(
        symbol, exchange, Interval.MINUTE,
        start_1m, end_1m
    )
    
    # 使用period_utils获取正确的5分钟周期起始时间
    from vnpy.trader.period_utils import get_period_start
    period_start = get_period_start(target_time, Interval.MINUTE_5, exchange)
    
    if period_start:
        print(f"   5分钟周期起始时间: {period_start.strftime('%Y-%m-%d %H:%M:%S')}")
        period_end = period_start + timedelta(minutes=5)
        
        # 筛选出属于该5分钟周期的1分钟K线
        bars_1m = []
        for bar in bars_1m_all:
            bar_dt = bar.datetime.replace(tzinfo=DB_TZ) if not bar.datetime.tzinfo else bar.datetime
            if bar_dt >= period_start and bar_dt < period_end:
                bars_1m.append(bar)
    else:
        bars_1m = []
        print("   无法确定5分钟周期起始时间")
    
    if bars_1m:
        print(f"   找到 {len(bars_1m)} 条1分钟K线:")
        for bar in bars_1m:
            print(f"   {bar.datetime.strftime('%Y-%m-%d %H:%M:%S')}: "
                  f"开={bar.open_price:.0f}, 高={bar.high_price:.0f}, "
                  f"低={bar.low_price:.0f}, 收={bar.close_price:.0f}, "
                  f"量={bar.volume}")
        
        # 分析开盘价
        first_bar = bars_1m[0]
        last_bar = bars_1m[-1]
        high_price = max(bar.high_price for bar in bars_1m)
        low_price = min(bar.low_price for bar in bars_1m)
        total_volume = sum(bar.volume for bar in bars_1m)
        
        print(f"\n   分析结果:")
        print(f"   第一根1分钟K线时间: {first_bar.datetime.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   第一根1分钟K线开盘价: {first_bar.open_price:.0f} (应该是5分钟开盘价)")
        print(f"   最后一根1分钟K线收盘价: {last_bar.close_price:.0f} (应该是5分钟收盘价)")
        print(f"   最高价: {high_price:.0f}")
        print(f"   最低价: {low_price:.0f}")
        print(f"   总成交量: {total_volume:.0f}")
        
        # 对比5分钟K线
        if bars_5m:
            bar_5m = bars_5m[0]
            print(f"\n   5分钟K线数据:")
            print(f"   开盘价: {bar_5m.open_price:.0f} {'✓' if bar_5m.open_price == first_bar.open_price else '✗ 应该是 ' + str(first_bar.open_price)}")
            print(f"   收盘价: {bar_5m.close_price:.0f} {'✓' if bar_5m.close_price == last_bar.close_price else '✗ 应该是 ' + str(last_bar.close_price)}")
            print(f"   最高价: {bar_5m.high_price:.0f} {'✓' if abs(bar_5m.high_price - high_price) < 0.01 else '✗ 应该是 ' + str(high_price)}")
            print(f"   最低价: {bar_5m.low_price:.0f} {'✓' if abs(bar_5m.low_price - low_price) < 0.01 else '✗ 应该是 ' + str(low_price)}")
    else:
        print("   未找到1分钟K线数据\n")
    
    # 3. 检查更早的1分钟K线（可能第一根1分钟K线不在查询范围内）
    print("\n3. 检查更早的1分钟K线（可能第一根K线时间不同）:")
    start_1m_extended = start_5m - timedelta(minutes=5)
    bars_1m_extended = database.load_bar_data(
        symbol, exchange, Interval.MINUTE,
        start_1m_extended, end_5m
    )
    
    if bars_1m_extended:
        # 过滤出属于该5分钟周期的1分钟K线
        period_bars = []
        for bar in bars_1m_extended:
            bar_dt = bar.datetime
            if bar_dt >= start_5m and bar_dt < end_5m:
                period_bars.append(bar)
        
        if period_bars:
            print(f"   在扩展范围内找到 {len(period_bars)} 条属于该5分钟周期的1分钟K线:")
            period_bars.sort(key=lambda x: x.datetime)
            for bar in period_bars:
                print(f"   {bar.datetime.strftime('%Y-%m-%d %H:%M:%S')}: "
                      f"开={bar.open_price:.0f}, 高={bar.high_price:.0f}, "
                      f"低={bar.low_price:.0f}, 收={bar.close_price:.0f}")
            
            first_bar_ext = period_bars[0]
            print(f"\n   扩展查询结果 - 第一根1分钟K线:")
            print(f"   时间: {first_bar_ext.datetime.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   开盘价: {first_bar_ext.open_price:.0f}")

if __name__ == "__main__":
    try:
        database = get_database()
        if not database:
            print("错误: 无法获取数据库实例，请确保已配置数据库")
            sys.exit(1)
        
        # 先检查数据库概览
        print("检查数据库概览...")
        overviews = database.get_bar_overview()
        print(f"数据库中共有 {len(overviews)} 条K线数据记录\n")
        
        # 查找MHImain.HKFE的数据
        mhi_overviews = [ov for ov in overviews if ov.symbol == "MHImain" and ov.exchange == Exchange.HKFE]
        print(f"找到 {len(mhi_overviews)} 条MHImain.HKFE的数据记录:")
        for ov in mhi_overviews:
            print(f"  {ov.interval.value}: {ov.start} ~ {ov.end}, {ov.count} 条")
        
        # 设置目标时间和合约
        target_time = datetime(2025, 11, 29, 1, 55, 0, tzinfo=DB_TZ)
        vt_symbol = "MHImain.HKFE"
        
        print("\n" + "="*80)
        check_bar_data(vt_symbol, target_time)
        
    except Exception as e:
        import traceback
        print(f"错误: {e}")
        traceback.print_exc()

