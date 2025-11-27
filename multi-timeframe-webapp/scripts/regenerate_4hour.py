#!/usr/bin/env python3
"""
Regenerate 4-hour K-line data with correct HKFE trading session alignment.

精确的4小时时间边界：
1. 17:15-21:14：第一根4小时K线（时间戳：17:15，开盘价=17:15的1分钟开盘价，收盘价=21:14的1分钟收盘价）
2. 21:15-01:14：第二根4小时K线（时间戳：21:15，开盘价=21:15的1分钟开盘价，收盘价=01:14的1分钟收盘价，跨午夜）
3. 01:15-03:00 + 09:15-11:29：第三根4小时K线（时间戳：01:15，开盘价=01:15的1分钟开盘价，收盘价=11:29的1分钟收盘价，跨休市）
4. 11:30-12:00 + 13:00-16:29：第四根4小时K线（时间戳：11:30，开盘价=11:30的1分钟开盘价，收盘价=16:29的1分钟收盘价，跨午休）

特殊情况处理：
1. 意外停盘：如果在16:29前意外停盘，当日最后一根4小时K线到停盘时间截止。次日开盘09:15到11:29算作一根独立的4小时K线。
2. 金融假期：如果在夜盘收盘后遇到金融假期，完整的4小时K线开始时间是01:15，结束时间是金融假期后开盘的早11:29。
"""

import pandas as pd
from datetime import datetime, timedelta
import sys
from pathlib import Path

def determine_4hour_period(dt):
    """
    Determine which 4-hour period a timestamp belongs to.
    Returns the period start timestamp.

    精确的4小时时间边界（闭区间）：
    1. 17:15-21:14：第一根4小时K线（时间戳：17:15）
    2. 21:15-01:14：第二根4小时K线（时间戳：21:15，跨午夜）
    3. 01:15-03:00 + 09:15-11:29：第三根4小时K线（时间戳：01:15，跨休市）
    4. 11:30-12:00 + 13:00-16:29：第四根4小时K线（时间戳：11:30，跨午休）
    """
    time = dt.time()
    hour = time.hour
    minute = time.minute

    # Convert to minutes since midnight for easier comparison
    minutes_since_midnight = hour * 60 + minute

    # Define period boundaries (in minutes since midnight)
    # Period 1: 17:15-21:14 (1035-1274 minutes)
    # Period 2: 21:15-01:14 next day (1275-1439 + 0-74 minutes)
    # Period 3: 01:15-03:00 + 09:15-11:29 (75-180 + 555-689 minutes)
    # Period 4: 11:30-12:00 + 13:00-16:29 (690-720 + 780-989 minutes)

    if 1035 <= minutes_since_midnight <= 1274:  # 17:15-21:14
        # Period 1
        return dt.replace(hour=17, minute=15, second=0, microsecond=0)

    elif 1275 <= minutes_since_midnight <= 1439:  # 21:15-23:59
        # Period 2 (first part, same day)
        return dt.replace(hour=21, minute=15, second=0, microsecond=0)

    elif 0 <= minutes_since_midnight <= 74:  # 00:00-01:14
        # Period 2 (second part, crosses midnight)
        # The period started on previous day at 21:15
        period_start = dt.replace(hour=21, minute=15, second=0, microsecond=0) - timedelta(days=1)
        return period_start

    elif 75 <= minutes_since_midnight <= 180:  # 01:15-03:00
        # Period 3 (late night part)
        return dt.replace(hour=1, minute=15, second=0, microsecond=0)

    elif 555 <= minutes_since_midnight <= 689:  # 09:15-11:29
        # Period 3 (morning session part, same period as late night)
        # 需要判断是否跨越周末：周一需要回溯到上周六的01:15
        weekday = dt.weekday()
        if weekday == 0:  # Monday
            # Go back to Saturday's 01:15 (2 days ago)
            return (dt - timedelta(days=2)).replace(hour=1, minute=15, second=0, microsecond=0)
        else:
            return dt.replace(hour=1, minute=15, second=0, microsecond=0)

    elif 690 <= minutes_since_midnight <= 720:  # 11:30-12:00
        # Period 4 (late morning part)
        return dt.replace(hour=11, minute=30, second=0, microsecond=0)

    elif 780 <= minutes_since_midnight <= 989:  # 13:00-16:29
        # Period 4 (afternoon session part, same period as late morning)
        # The period timestamp should be from the same day 11:30
        return dt.replace(hour=11, minute=30, second=0, microsecond=0)

    else:
        # Outside trading hours, return None
        return None

def aggregate_to_4hour(df_1min):
    """
    Aggregate 1-minute K-line data to 4-hour with HKFE session alignment.
    """
    # Parse datetime
    df_1min['datetime'] = pd.to_datetime(df_1min['datetime'])

    # Determine period for each row
    df_1min['period_start'] = df_1min['datetime'].apply(determine_4hour_period)

    # Remove rows outside trading hours
    df_1min = df_1min[df_1min['period_start'].notna()].copy()

    # Group by period and aggregate
    df_4hour = df_1min.groupby('period_start').agg({
        'symbol': 'first',
        'exchange': 'first',
        'open': 'first',      # First open in the period
        'high': 'max',        # Highest high
        'low': 'min',         # Lowest low
        'close': 'last',      # Last close
        'volume': 'sum',      # Total volume
        'turnover': 'sum',    # Total turnover
        'open_interest': 'last'  # Last open interest
    }).reset_index()

    # Rename period_start to datetime
    df_4hour.rename(columns={'period_start': 'datetime'}, inplace=True)

    # Sort by datetime
    df_4hour.sort_values('datetime', inplace=True)

    return df_4hour

def main():
    # Paths
    project_root = Path(__file__).parent.parent
    input_file = project_root / 'data' / '1min_MHImain_HKFE.csv'
    output_file = project_root / 'data' / '4hour_MHImain_HKFE_correct.csv'

    print(f"Reading 1-minute data from: {input_file}")

    # Read 1-minute CSV
    df_1min = pd.read_csv(input_file)
    print(f"Loaded {len(df_1min)} 1-minute candles")

    # Aggregate to 4-hour
    print("Aggregating to 4-hour periods with HKFE session alignment...")
    df_4hour = aggregate_to_4hour(df_1min)

    print(f"Generated {len(df_4hour)} 4-hour candles")

    # Save to CSV
    df_4hour.to_csv(output_file, index=False)
    print(f"Saved to: {output_file}")

    # Show sample
    print("\nFirst 10 rows:")
    print(df_4hour.head(10).to_string())

    print("\nLast 10 rows:")
    print(df_4hour.tail(10).to_string())

    # Verify period distribution
    print("\nVerifying period distribution...")
    df_4hour['hour'] = pd.to_datetime(df_4hour['datetime']).dt.hour
    df_4hour['minute'] = pd.to_datetime(df_4hour['datetime']).dt.minute
    print("\nPeriod start times distribution:")
    print(df_4hour.groupby(['hour', 'minute']).size())

if __name__ == '__main__':
    main()
