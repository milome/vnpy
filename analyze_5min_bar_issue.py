"""
分析5分钟K线开盘价问题
直接查询数据库中的01:55 5分钟K线记录，并分析其生成逻辑
"""
from datetime import datetime, timedelta
from vnpy.trader.constant import Interval, Exchange
from vnpy.trader.database import get_database, DB_TZ
from vnpy.trader.utility import extract_vt_symbol
from vnpy.trader.period_utils import get_period_start

def analyze_5min_bar(vt_symbol: str, target_datetime: datetime):
    """分析指定时间的5分钟K线数据"""
    database = get_database()
    symbol, exchange = extract_vt_symbol(vt_symbol)
    
    print(f"\n{'='*80}")
    print(f"分析5分钟K线问题")
    print(f"合约: {vt_symbol}")
    print(f"目标时间: {target_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")
    
    # 1. 获取正确的5分钟周期起始时间
    period_start = get_period_start(target_datetime, Interval.MINUTE_5, exchange)
    if not period_start:
        print(f"错误: 无法确定5分钟周期起始时间")
        return
    
    period_end = period_start + timedelta(minutes=5)
    print(f"5分钟周期: {period_start.strftime('%Y-%m-%d %H:%M:%S')} ~ {period_end.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 2. 查询数据库中的5分钟K线记录
    print("1. 查询数据库中的5分钟K线记录:")
    start_query = period_start - timedelta(hours=1)
    end_query = period_end + timedelta(hours=1)
    
    bars_5m = database.load_bar_data(
        symbol, exchange, Interval.MINUTE_5,
        start_query, end_query
    )
    
    print(f"   查询到 {len(bars_5m)} 条5分钟K线记录:")
    for bar in bars_5m[:20]:  # 显示前20条
        bar_dt = bar.datetime.replace(tzinfo=DB_TZ) if not bar.datetime.tzinfo else bar.datetime
        print(f"   {bar_dt.strftime('%Y-%m-%d %H:%M:%S')}: 开={bar.open_price:.0f}, 收={bar.close_price:.0f}")
    
    target_bar_5m = None
    for bar in bars_5m:
        bar_dt = bar.datetime.replace(tzinfo=DB_TZ) if not bar.datetime.tzinfo else bar.datetime
        # 使用更宽松的匹配（允许秒级差异）
        if abs((bar_dt - period_start).total_seconds()) < 60:
            target_bar_5m = bar
            break
    
    if target_bar_5m:
        print(f"   找到5分钟K线记录:")
        print(f"   时间: {target_bar_5m.datetime.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   开盘价: {target_bar_5m.open_price:.0f}")
        print(f"   最高价: {target_bar_5m.high_price:.0f}")
        print(f"   最低价: {target_bar_5m.low_price:.0f}")
        print(f"   收盘价: {target_bar_5m.close_price:.0f}")
        print(f"   成交量: {target_bar_5m.volume:.0f}\n")
    else:
        print(f"\n   ⚠️ 未找到01:55的5分钟K线记录")
        print(f"   可能是时区问题，或者数据库中确实没有这条记录\n")
        # 继续分析，查看1分钟数据情况
    
    # 3. 查询该5分钟周期内的所有1分钟K线
    print("2. 查询该5分钟周期内的1分钟K线:")
    bars_1m_all = database.load_bar_data(
        symbol, exchange, Interval.MINUTE,
        period_start - timedelta(minutes=10), period_end + timedelta(minutes=10)
    )
    
    # 筛选出属于该5分钟周期的1分钟K线
    period_bars_1m = []
    for bar in bars_1m_all:
        bar_dt = bar.datetime.replace(tzinfo=DB_TZ) if not bar.datetime.tzinfo else bar.datetime
        if bar_dt >= period_start and bar_dt < period_end:
            period_bars_1m.append(bar)
    
    period_bars_1m.sort(key=lambda x: x.datetime)
    
    if period_bars_1m:
        print(f"   找到 {len(period_bars_1m)} 条1分钟K线:")
        for bar in period_bars_1m:
            bar_dt = bar.datetime.replace(tzinfo=DB_TZ) if not bar.datetime.tzinfo else bar.datetime
            print(f"   {bar_dt.strftime('%Y-%m-%d %H:%M:%S')}: "
                  f"开={bar.open_price:.0f}, 高={bar.high_price:.0f}, "
                  f"低={bar.low_price:.0f}, 收={bar.close_price:.0f}, 量={bar.volume:.0f}")
        
        # 分析应该的值
        first_bar = period_bars_1m[0]
        last_bar = period_bars_1m[-1]
        high_price = max(bar.high_price for bar in period_bars_1m)
        low_price = min(bar.low_price for bar in period_bars_1m)
        total_volume = sum(bar.volume for bar in period_bars_1m)
        
        print(f"\n   根据1分钟K线计算的5分钟K线应该是:")
        print(f"   开盘价: {first_bar.open_price:.0f} (第一根1分钟K线的开盘价)")
        print(f"   收盘价: {last_bar.close_price:.0f} (最后一根1分钟K线的收盘价)")
        print(f"   最高价: {high_price:.0f}")
        print(f"   最低价: {low_price:.0f}")
        print(f"   成交量: {total_volume:.0f}\n")
        
        # 对比数据库中的值
        print("3. 对比分析:")
        print(f"   数据库中5分钟K线的开盘价: {target_bar_5m.open_price:.0f}")
        print(f"   应该是: {first_bar.open_price:.0f}")
        if target_bar_5m.open_price != first_bar.open_price:
            print(f"   ❌ 开盘价不匹配！差异: {abs(target_bar_5m.open_price - first_bar.open_price):.0f}")
        else:
            print(f"   ✓ 开盘价正确")
        
        print(f"\n   数据库中5分钟K线的收盘价: {target_bar_5m.close_price:.0f}")
        print(f"   应该是: {last_bar.close_price:.0f}")
        if target_bar_5m.close_price != last_bar.close_price:
            print(f"   ❌ 收盘价不匹配！差异: {abs(target_bar_5m.close_price - last_bar.close_price):.0f}")
        else:
            print(f"   ✓ 收盘价正确")
            
    else:
        print(f"   ❌ 未找到该5分钟周期内的1分钟K线数据！")
        print(f"   这说明数据库中缺少01:55-01:59的1分钟K线数据\n")
        
        # 查看前后的数据
        print("   查看前后时间点的1分钟K线数据:")
        nearby_bars = []
        for bar in bars_1m_all:
            bar_dt = bar.datetime.replace(tzinfo=DB_TZ) if not bar.datetime.tzinfo else bar.datetime
            if bar_dt < period_start and bar_dt >= period_start - timedelta(minutes=10):
                nearby_bars.append(("前", bar))
            elif bar_dt >= period_end and bar_dt < period_end + timedelta(minutes=10):
                nearby_bars.append(("后", bar))
        
        nearby_bars.sort(key=lambda x: x[1].datetime)
        print(f"   找到 {len(nearby_bars)} 条前后数据:")
        for label, bar in nearby_bars[:15]:  # 显示前后各15条
            bar_dt = bar.datetime.replace(tzinfo=DB_TZ) if not bar.datetime.tzinfo else bar.datetime
            print(f"   [{label}] {bar_dt.strftime('%Y-%m-%d %H:%M:%S')}: "
                  f"开={bar.open_price:.0f}, 收={bar.close_price:.0f}")
        
        print(f"\n   ⚠️ 问题分析:")
        if target_bar_5m:
            print(f"   数据库中存在01:55的5分钟K线记录（开盘价={target_bar_5m.open_price:.0f}, 收盘价={target_bar_5m.close_price:.0f}）")
            print(f"   但缺少对应的1分钟K线数据（01:55-01:59）")
        else:
            print(f"   数据库中缺少01:55的5分钟K线记录")
            print(f"   同时缺少对应的1分钟K线数据（01:55-01:59）")
        print(f"   这说明:")
        print(f"   1. 可能是在聚合时使用了错误的数据源")
        print(f"   2. 或者聚合后1分钟数据被删除了")
        print(f"   3. 或者聚合逻辑本身有问题，使用了其他周期的数据")
        print(f"   4. 或者在K线图表中看到的是实时合成的数据，而不是数据库中的数据")
        
        # 检查是否使用了其他周期的数据
        print(f"\n   检查是否使用了其他5分钟周期的数据:")
        prev_period_start = period_start - timedelta(minutes=5)
        prev_bars_1m = []
        for bar in bars_1m_all:
            bar_dt = bar.datetime.replace(tzinfo=DB_TZ) if not bar.datetime.tzinfo else bar.datetime
            if bar_dt >= prev_period_start and bar_dt < period_start:
                prev_bars_1m.append(bar)
        
        if prev_bars_1m:
            prev_bars_1m.sort(key=lambda x: x.datetime)
            last_prev_bar = prev_bars_1m[-1]
            print(f"   前一个5分钟周期（{prev_period_start.strftime('%H:%M')}）最后一根1分钟K线:")
            print(f"   时间: {last_prev_bar.datetime.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   收盘价: {last_prev_bar.close_price:.0f}")
            
            if target_bar_5m.open_price == last_prev_bar.close_price:
                print(f"   ⚠️ 5分钟K线的开盘价与前一个周期的收盘价相同！")
                print(f"   这说明可能使用了错误的数据源")

if __name__ == "__main__":
    try:
        target_time = datetime(2025, 11, 29, 1, 55, 0, tzinfo=DB_TZ)
        vt_symbol = "MHImain.HKFE"
        
        analyze_5min_bar(vt_symbol, target_time)
        
    except Exception as e:
        import traceback
        print(f"错误: {e}")
        traceback.print_exc()

