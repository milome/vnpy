#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1分钟K线数据聚合为4小时K线脚本
按照精确的HKFE交易时段边界进行聚合
"""

import sys
import io
import pandas as pd
from datetime import datetime, timedelta
import os

# 设置输出编码为UTF-8
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def get_4hour_period(dt):
    """
    根据时间戳确定属于哪个4小时K线周期

    返回: (period_start, period_index, bar_name)
    - period_start: 该4小时K线的开始时间
    - period_index: 周期索引 (1-4)
    - bar_name: K线名称

    4小时K线划分规则（精确边界）：
    1. 17:15-21:14：第一根4小时K线（时间戳：17:15，开盘价=17:15的1分钟开盘价，收盘价=21:14的1分钟收盘价）
    2. 21:15-次日01:14：第二根4小时K线（时间戳：21:15，开盘价=21:15的1分钟开盘价，收盘价=01:14的1分钟收盘价）
    3. 01:15-03:00 + 09:15-11:29：第三根4小时K线（时间戳：01:15，开盘价=01:15的1分钟开盘价，收盘价=11:29的1分钟收盘价）
    4. 11:30-12:00 + 13:00-16:29：第四根4小时K线（时间戳：11:30，开盘价=11:30的1分钟开盘价，收盘价=16:29的1分钟收盘价）
    
    特殊情况处理：
    1. 意外停盘：如果在16:29前意外停盘，当日最后一根4小时K线到停盘时间截止。次日开盘09:15到11:29算作一根独立的4小时K线。
    2. 金融假期：如果在夜盘收盘后遇到金融假期，完整的4小时K线开始时间是01:15，结束时间是金融假期后开盘的早11:29。
    """
    hour = dt.hour
    minute = dt.minute
    date = dt.date()

    # 第一根4小时K线: 17:15-21:14（闭区间，包含21:14）
    if (hour == 17 and minute >= 15) or (hour >= 18 and hour < 21) or (hour == 21 and minute <= 14):
        period_start = datetime.combine(date, datetime.strptime('17:15', '%H:%M').time())
        return period_start, 1, '17:15-21:14'

    # 第二根4小时K线: 21:15-次日01:14（闭区间）
    if (hour == 21 and minute >= 15) or (hour >= 22 and hour <= 23) or (hour == 0) or (hour == 1 and minute <= 14):
        # 如果是21:15之后到23:59，period_start是当天21:15
        if hour >= 21:
            period_start = datetime.combine(date, datetime.strptime('21:15', '%H:%M').time())
        else:
            # 如果是00:00-01:14，period_start是前一天21:15
            prev_date = date - timedelta(days=1)
            period_start = datetime.combine(prev_date, datetime.strptime('21:15', '%H:%M').time())
        return period_start, 2, '21:15-01:14'

    # 第三根4小时K线: 01:15-03:00 + 09:15-11:29（闭区间）
    if (hour == 1 and minute >= 15) or (hour == 2) or (hour == 3 and minute == 0) or \
       (hour == 9 and minute >= 15) or (hour == 10) or (hour == 11 and minute <= 29):
        # 如果是01:15-03:00，period_start是当天01:15
        if hour <= 3:
            period_start = datetime.combine(date, datetime.strptime('01:15', '%H:%M').time())
        else:
            # 如果是09:15-11:29，需要判断是否跨越周末
            # 周一（weekday=0）需要回溯到上周六的01:15
            weekday = dt.weekday()
            if weekday == 0:  # 周一
                # 回溯到上周六（2天前）的01:15
                sat_date = date - timedelta(days=2)
                period_start = datetime.combine(sat_date, datetime.strptime('01:15', '%H:%M').time())
            else:
                period_start = datetime.combine(date, datetime.strptime('01:15', '%H:%M').time())
        return period_start, 3, '01:15-11:29'

    # 第四根4小时K线: 11:30-12:00 + 13:00-16:29（闭区间）
    if (hour == 11 and minute >= 30) or (hour == 12) or \
       (hour >= 13 and hour < 16) or (hour == 16 and minute <= 29):
        period_start = datetime.combine(date, datetime.strptime('11:30', '%H:%M').time())
        return period_start, 4, '11:30-16:29'

    # 如果不在交易时段内，返回None
    return None, None, None

def aggregate_to_4hour(input_csv, output_csv):
    """
    将1分钟K线数据聚合为4小时K线
    """
    print("=" * 80)
    print("📊 1分钟K线聚合为4小时K线")
    print("=" * 80)
    print(f"\n正在读取数据: {input_csv}")

    # 读取1分钟数据
    df = pd.read_csv(input_csv)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('datetime')

    print(f"✅ 读取完成，共 {len(df):,} 条1分钟数据")
    print(f"时间范围: {df['datetime'].min()} 至 {df['datetime'].max()}")

    # 为每条记录分配4小时周期
    print("\n🔄 正在分配4小时周期...")
    df['period_start'] = None
    df['period_index'] = None
    df['bar_name'] = None

    for idx, row in df.iterrows():
        period_start, period_index, bar_name = get_4hour_period(row['datetime'])
        df.at[idx, 'period_start'] = period_start
        df.at[idx, 'period_index'] = period_index
        df.at[idx, 'bar_name'] = bar_name

    # 移除不在交易时段的数据
    df_trading = df[df['period_start'].notna()].copy()
    excluded_count = len(df) - len(df_trading)
    print(f"✅ 周期分配完成，排除非交易时段数据 {excluded_count:,} 条")

    # 处理跨夜盘的第三根K线（01:15-03:00 + 09:15-11:29）
    print("\n🔧 处理跨时段的第三根4小时K线...")

    # 按日期和period_index分组
    df_trading['date'] = df_trading['datetime'].dt.date

    # 聚合数据
    print("\n📈 正在聚合4小时K线数据...")

    four_hour_bars = []

    # 按period_start分组进行聚合
    for period_start, group in df_trading.groupby('period_start'):
        if len(group) == 0:
            continue

        # K线聚合规则：
        # open: 第一条记录的open
        # high: 所有记录的high最大值
        # low: 所有记录的low最小值
        # close: 最后一条记录的close
        # volume: 所有记录的volume总和
        # turnover: 所有记录的turnover总和

        bar = {
            'symbol': group.iloc[0]['symbol'],
            'exchange': group.iloc[0]['exchange'],
            'datetime': period_start,
            'open': group.iloc[0]['open'],
            'high': group['high'].max(),
            'low': group['low'].min(),
            'close': group.iloc[-1]['close'],
            'volume': group['volume'].sum(),
            'turnover': group['turnover'].sum(),
            'open_interest': group.iloc[-1]['open_interest'],  # 使用最后一条的持仓量
            'bar_name': group.iloc[0]['bar_name'],
            'record_count': len(group),  # 记录该K线包含了多少条1分钟数据
        }

        four_hour_bars.append(bar)

    # 创建4小时K线DataFrame
    df_4hour = pd.DataFrame(four_hour_bars)
    df_4hour = df_4hour.sort_values('datetime')

    print(f"✅ 聚合完成，生成 {len(df_4hour):,} 根4小时K线")

    # 显示统计信息
    print("\n📊 4小时K线统计:")
    print(f"时间范围: {df_4hour['datetime'].min()} 至 {df_4hour['datetime'].max()}")
    print(f"每根K线平均包含 {df_4hour['record_count'].mean():.1f} 条1分钟数据")
    print(f"最少包含 {df_4hour['record_count'].min()} 条1分钟数据")
    print(f"最多包含 {df_4hour['record_count'].max()} 条1分钟数据")

    # 按bar_name统计数量
    print("\n各时段4小时K线数量:")
    bar_counts = df_4hour['bar_name'].value_counts().sort_index()
    for bar_name, count in bar_counts.items():
        print(f"  {bar_name}: {count:,} 根")

    # 保存结果
    output_df = df_4hour[['symbol', 'exchange', 'datetime', 'open', 'high', 'low', 'close',
                           'volume', 'turnover', 'open_interest']].copy()

    output_df.to_csv(output_csv, index=False)
    print(f"\n✅ 4小时K线数据已保存至: {output_csv}")

    return df_4hour

def check_4hour_integrity(df_4hour):
    """
    检查4小时K线数据的完整性
    """
    print("\n" + "=" * 80)
    print("🔍 4小时K线数据完整性检查")
    print("=" * 80)

    # 检查时间连续性
    missing_periods = []

    for i in range(1, len(df_4hour)):
        prev_time = df_4hour.iloc[i-1]['datetime']
        curr_time = df_4hour.iloc[i]['datetime']
        prev_bar = df_4hour.iloc[i-1]['bar_name']
        curr_bar = df_4hour.iloc[i]['bar_name']

        time_diff_hours = (curr_time - prev_time).total_seconds() / 3600

        # 正常情况下，相邻两根4小时K线的时间间隔应该是：
        # 1. 同一交易日内：约4小时
        # 2. 跨日：取决于具体时段

        # 第一根到第二根：3小时59分（17:15 -> 21:15）
        # 第二根到第三根：跨夜盘和日盘，间隔较大
        # 第三根到第四根：约4小时（包含午休）
        # 第四根到下一个第一根：约1小时（16:30 -> 17:15）

        # 简化检查：如果间隔超过72小时（3天），可能是缺失或节假日
        if time_diff_hours > 72:
            missing_periods.append({
                'prev_time': prev_time,
                'prev_bar': prev_bar,
                'curr_time': curr_time,
                'curr_bar': curr_bar,
                'gap_hours': time_diff_hours
            })

    if missing_periods:
        print(f"\n⚠️  发现 {len(missing_periods)} 个异常大间隔（>72小时）:")
        print("-" * 80)
        print(f"{'序号':<6} {'前一时间':<22} {'前一K线':<18} {'当前时间':<22} {'当前K线':<18} {'间隔(小时)'}")
        print("-" * 80)

        for idx, gap in enumerate(missing_periods[:20], 1):
            print(f"{idx:<6} {str(gap['prev_time']):<22} {gap['prev_bar']:<18} "
                  f"{str(gap['curr_time']):<22} {gap['curr_bar']:<18} {gap['gap_hours']:.2f}")

        if len(missing_periods) > 20:
            print(f"\n... 还有 {len(missing_periods) - 20} 个异常间隔未显示")
    else:
        print("\n✅ 未发现异常大间隔")

    # 检查每根K线包含的1分钟数据数量
    print("\n📊 K线数据量分布:")

    # 理论上（精确边界）：
    # 17:15-21:14: 3小时59分 = 239分钟（240根1分钟K线）
    # 21:15-01:14: 3小时59分 = 239分钟（240根1分钟K线，跨午夜）
    # 01:15-03:00 + 09:15-11:29: 1小时45分 + 2小时14分 = 239分钟（240根1分钟K线，跨休市）
    # 11:30-12:00 + 13:00-16:29: 30分 + 3小时29分 = 239分钟（240根1分钟K线，跨午休）

    for bar_name in df_4hour['bar_name'].unique():
        bar_data = df_4hour[df_4hour['bar_name'] == bar_name]
        avg_count = bar_data['record_count'].mean()
        min_count = bar_data['record_count'].min()
        max_count = bar_data['record_count'].max()

        print(f"\n{bar_name}:")
        print(f"  平均包含: {avg_count:.1f} 条1分钟数据")
        print(f"  最少: {min_count} 条")
        print(f"  最多: {max_count} 条")

        # 检查是否有异常少的K线（可能是意外停盘）
        abnormal = bar_data[bar_data['record_count'] < 100]
        if len(abnormal) > 0:
            print(f"  ⚠️  发现 {len(abnormal)} 根K线数据量异常少（<100条），可能是意外停盘:")
            for idx, row in abnormal.head(10).iterrows():
                print(f"    - {row['datetime']}: {row['record_count']} 条1分钟数据")

    print("\n" + "=" * 80)
    print("✅ 4小时K线完整性检查完成")
    print("=" * 80)

if __name__ == '__main__':
    # 数据文件路径
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
    input_csv = os.path.join(data_dir, '1min_MHImain_HKFE.csv')
    output_csv = os.path.join(data_dir, '4hour_MHImain_HKFE_new.csv')

    # 执行聚合
    df_4hour = aggregate_to_4hour(input_csv, output_csv)

    # 检查完整性
    check_4hour_integrity(df_4hour)

    print("\n✅ 所有任务完成！")
