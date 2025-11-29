"""
检查DataRecorder的数据保存情况
验证数据是否真的写入数据库
"""
from datetime import datetime, timedelta
from vnpy.trader.constant import Interval, Exchange
from vnpy.trader.database import get_database, DB_TZ
from vnpy.trader.utility import extract_vt_symbol

def check_datarecorder_save(vt_symbol: str = "MHImain.HKFE"):
    """检查DataRecorder最近保存的数据"""
    database = get_database()
    symbol, exchange = extract_vt_symbol(vt_symbol)
    
    print(f"\n{'='*80}")
    print(f"检查DataRecorder数据保存情况")
    print(f"合约: {vt_symbol}")
    print(f"{'='*80}\n")
    
    # 检查最近10分钟的数据
    now = datetime.now(DB_TZ)
    start_time = now - timedelta(minutes=10)
    
    print(f"检查时间范围: {start_time.strftime('%Y-%m-%d %H:%M:%S')} ~ {now.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 1. 检查1分钟K线数据
    print("1. 检查1分钟K线数据:")
    bars_1m = database.load_bar_data(
        symbol, exchange, Interval.MINUTE,
        start_time, now
    )
    
    if bars_1m:
        print(f"   找到 {len(bars_1m)} 条1分钟K线")
        print(f"   最新一条:")
        latest_bar = bars_1m[-1]
        latest_dt = latest_bar.datetime.replace(tzinfo=DB_TZ) if not latest_bar.datetime.tzinfo else latest_bar.datetime
        print(f"   时间: {latest_dt.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   开盘价: {latest_bar.open_price:.0f}")
        print(f"   收盘价: {latest_bar.close_price:.0f}")
        print(f"   与当前时间差: {(now - latest_dt).total_seconds():.0f} 秒")
        
        # 检查是否有时间间隔
        if len(bars_1m) > 1:
            intervals = []
            for i in range(1, len(bars_1m)):
                prev_dt = bars_1m[i-1].datetime.replace(tzinfo=DB_TZ) if not bars_1m[i-1].datetime.tzinfo else bars_1m[i-1].datetime
                curr_dt = bars_1m[i].datetime.replace(tzinfo=DB_TZ) if not bars_1m[i].datetime.tzinfo else bars_1m[i].datetime
                interval = (curr_dt - prev_dt).total_seconds()
                intervals.append(interval)
            
            print(f"\n   时间间隔分析:")
            print(f"   平均间隔: {sum(intervals)/len(intervals):.0f} 秒")
            print(f"   最小间隔: {min(intervals):.0f} 秒")
            print(f"   最大间隔: {max(intervals):.0f} 秒")
    else:
        print(f"   ❌ 未找到1分钟K线数据！")
    
    # 2. 检查5分钟K线数据
    print("\n2. 检查5分钟K线数据:")
    bars_5m = database.load_bar_data(
        symbol, exchange, Interval.MINUTE_5,
        start_time - timedelta(minutes=10), now
    )
    
    if bars_5m:
        print(f"   找到 {len(bars_5m)} 条5分钟K线")
        print(f"   最新一条:")
        latest_bar = bars_5m[-1]
        latest_dt = latest_bar.datetime.replace(tzinfo=DB_TZ) if not latest_bar.datetime.tzinfo else latest_bar.datetime
        print(f"   时间: {latest_dt.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   开盘价: {latest_bar.open_price:.0f}")
        print(f"   收盘价: {latest_bar.close_price:.0f}")
        print(f"   与当前时间差: {(now - latest_dt).total_seconds():.0f} 秒")
    else:
        print(f"   ⚠️ 未找到5分钟K线数据（可能最近没有新数据）")
    
    # 3. 检查数据库概览中的最新数据时间
    print("\n3. 检查数据库概览:")
    overviews = database.get_bar_overview()
    
    mhi_overviews = [ov for ov in overviews if ov.symbol == symbol and ov.exchange == exchange]
    if mhi_overviews:
        for ov in mhi_overviews:
            ov_end = ov.end.replace(tzinfo=DB_TZ) if not ov.end.tzinfo else ov.end
            time_diff = (now - ov_end).total_seconds()
            print(f"   {ov.interval.value}: 结束时间={ov_end.strftime('%Y-%m-%d %H:%M:%S')}, "
                  f"数据量={ov.count}, 与当前时间差={time_diff:.0f}秒")
    else:
        print(f"   ❌ 未找到该合约的数据概览")
    
    # 4. 分析结论
    print("\n4. 分析结论:")
    if bars_1m:
        latest_bar = bars_1m[-1]
        latest_dt = latest_bar.datetime.replace(tzinfo=DB_TZ) if not latest_bar.datetime.tzinfo else latest_bar.datetime
        time_diff = (now - latest_dt).total_seconds()
        
        if time_diff < 60:
            print(f"   ✓ 1分钟K线数据正在实时更新（最新数据与当前时间差 {time_diff:.0f} 秒）")
        elif time_diff < 300:
            print(f"   ⚠️ 1分钟K线数据更新有延迟（最新数据与当前时间差 {time_diff:.0f} 秒）")
        else:
            print(f"   ❌ 1分钟K线数据更新严重延迟或已停止（最新数据与当前时间差 {time_diff:.0f} 秒）")
    else:
        print(f"   ❌ 最近10分钟内没有1分钟K线数据，DataRecorder可能没有正常工作")

if __name__ == "__main__":
    try:
        check_datarecorder_save()
    except Exception as e:
        import traceback
        print(f"错误: {e}")
        traceback.print_exc()

