#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1分钟K线数据完整性检查脚本
检查数据中的时间间隔、缺失数据和异常值
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

def parse_trading_hours():
    """
    定义HKFE交易时段
    根据香港期货交易所的交易时间
    """
    sessions = [
        # 夜盘
        ('17:15', '03:00'),  # 17:15 - 次日03:00
        # 日盘
        ('09:15', '12:00'),  # 09:15 - 12:00
        ('13:00', '16:30'),  # 13:00 - 16:30
    ]
    return sessions

def is_normal_market_break(prev_time, curr_time):
    """
    判断两个时间点之间的间隔是否是正常的休市时段

    HKFE正常休市时段：
    1. 日盘收盘到夜盘开盘: 16:30 - 17:15 (45分钟)
    2. 夜盘收盘到日盘开盘: 03:00 - 09:15 (约6小时15分钟)
    3. 午休时间: 12:00 - 13:00 (1小时)
    4. 周末和节假日
    """
    prev_hour = prev_time.hour
    prev_min = prev_time.minute
    curr_hour = curr_time.hour
    curr_min = curr_time.minute

    time_diff_minutes = (curr_time - prev_time).total_seconds() / 60
    time_diff_hours = time_diff_minutes / 60

    # 检查是否是日盘收盘到夜盘开盘 (16:30 - 17:15, 约45分钟)
    if (prev_hour == 16 and prev_min >= 29) and (curr_hour == 17 and curr_min <= 16):
        return True

    # 检查是否是夜盘收盘到日盘开盘 (03:00 - 09:15, 约6小时15分钟)
    # 前一时间应该在02:59-03:00左右，当前时间应该在09:15左右
    if (prev_hour >= 2 and prev_hour <= 3) and (curr_hour == 9 and curr_min <= 16):
        # 时间间隔应该在6-7小时之间
        if 6 <= time_diff_hours <= 7:
            return True

    # 检查是否是午休时间 (12:00 - 13:00, 约1小时)
    if (prev_hour == 11 and prev_min >= 59) or (prev_hour == 12 and prev_min <= 1):
        if curr_hour == 13 and curr_min <= 1:
            return True

    # 检查是否是周末 (周五收盘到周一开盘, 约54小时)
    if prev_time.weekday() == 4:  # 周五
        if curr_time.weekday() == 0:  # 周一
            # 周五夜盘最晚03:00结束，周一最早09:15开盘
            # 大约54小时左右的间隔
            if 52 <= time_diff_hours <= 58:
                return True

    return False

def check_data_integrity(csv_path):
    """
    检查CSV数据的完整性
    """
    print(f"📊 正在读取数据文件: {csv_path}")
    df = pd.read_csv(csv_path)

    print(f"✅ 数据加载完成，共 {len(df)} 条记录\n")

    # 转换时间列
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('datetime')

    # 基本统计信息
    start_date = df['datetime'].min()
    end_date = df['datetime'].max()
    total_days = (end_date - start_date).days + 1

    print("=" * 80)
    print("📅 数据基本信息")
    print("=" * 80)
    print(f"开始时间: {start_date}")
    print(f"结束时间: {end_date}")
    print(f"时间跨度: {total_days} 天")
    print(f"总记录数: {len(df):,} 条")
    print()

    # 检查缺失的分钟数据
    print("=" * 80)
    print("🔍 检查缺失数据（已排除正常休市时段）")
    print("=" * 80)

    missing_gaps = []
    large_gaps = []
    normal_breaks = []  # 记录正常的休市时段

    sessions = parse_trading_hours()

    for i in range(1, len(df)):
        prev_time = df.iloc[i-1]['datetime']
        curr_time = df.iloc[i]['datetime']

        time_diff = (curr_time - prev_time).total_seconds() / 60

        # 如果间隔大于1分钟，说明有间隔
        if time_diff > 1:
            # 首先检查是否是正常的休市时段
            if is_normal_market_break(prev_time, curr_time):
                normal_breaks.append({
                    'prev_time': prev_time,
                    'curr_time': curr_time,
                    'gap_minutes': int(time_diff),
                    'break_type': 'normal_market_break'
                })
                continue  # 跳过正常休市时段，不计入缺失

            # 如果不是正常休市，则记录为缺失或大间隔
            if time_diff <= 60:  # 1小时内的间隔
                missing_gaps.append({
                    'prev_time': prev_time,
                    'curr_time': curr_time,
                    'gap_minutes': int(time_diff),
                    'missing_count': int(time_diff - 1)
                })
            elif time_diff > 60:  # 大于1小时的间隔
                large_gaps.append({
                    'prev_time': prev_time,
                    'curr_time': curr_time,
                    'gap_hours': time_diff / 60,
                    'gap_type': 'abnormal_large_gap'
                })

    print(f"发现 {len(missing_gaps)} 个异常小间隔缺失（1-60分钟）")
    print(f"发现 {len(large_gaps)} 个异常大间隔（>1小时）")
    print(f"已排除 {len(normal_breaks)} 个正常休市时段")
    print()

    # 显示前20个缺失间隔的详情
    if missing_gaps:
        print("-" * 80)
        print("⚠️  异常缺失详情（前20条，已排除正常休市）")
        print("-" * 80)
        print(f"{'序号':<6} {'前一时间':<22} {'当前时间':<22} {'间隔(分钟)':<12} {'缺失条数'}")
        print("-" * 80)

        for idx, gap in enumerate(missing_gaps[:20], 1):
            print(f"{idx:<6} {str(gap['prev_time']):<22} {str(gap['curr_time']):<22} "
                  f"{gap['gap_minutes']:<12} {gap['missing_count']}")

        if len(missing_gaps) > 20:
            print(f"\n... 还有 {len(missing_gaps) - 20} 个缺失间隔未显示")
        print()

    # 统计每日缺失数据
    print("=" * 80)
    print("📈 按日期统计缺失数据")
    print("=" * 80)

    daily_missing = {}
    for gap in missing_gaps:
        date = gap['prev_time'].date()
        if date not in daily_missing:
            daily_missing[date] = 0
        daily_missing[date] += gap['missing_count']

    if daily_missing:
        sorted_daily = sorted(daily_missing.items(), key=lambda x: x[1], reverse=True)
        print(f"{'日期':<15} {'缺失条数'}")
        print("-" * 30)
        for date, count in sorted_daily[:30]:  # 显示缺失最多的30天
            print(f"{date} {count:>10}")

        if len(sorted_daily) > 30:
            print(f"\n... 还有 {len(sorted_daily) - 30} 天有缺失数据")
    else:
        print("✅ 没有发现缺失数据")
    print()

    # 数据质量统计
    print("=" * 80)
    print("📊 数据质量统计")
    print("=" * 80)

    total_missing = sum(gap['missing_count'] for gap in missing_gaps)

    # 检查重复数据
    duplicate_times = df[df.duplicated(subset=['datetime'], keep=False)]

    # 检查异常值（价格为0或负数）
    zero_prices = df[(df['open'] <= 0) | (df['high'] <= 0) | (df['low'] <= 0) | (df['close'] <= 0)]

    # 检查成交量异常
    zero_volume_days = df[df['volume'] == 0]

    print(f"总记录数:           {len(df):>10,}")
    print(f"缺失记录数:         {total_missing:>10,}")
    print(f"重复时间戳:         {len(duplicate_times):>10,}")
    print(f"价格异常记录:       {len(zero_prices):>10,}")
    print(f"零成交量记录:       {len(zero_volume_days):>10,}")
    print(f"数据完整度:         {(len(df) / (len(df) + total_missing) * 100):>9.2f}%")
    print()

    # 生成汇总报告
    return {
        'file_path': csv_path,
        'start_date': start_date,
        'end_date': end_date,
        'total_days': total_days,
        'total_records': len(df),
        'missing_gaps': missing_gaps,
        'large_gaps': large_gaps,
        'normal_breaks': normal_breaks,
        'total_missing': total_missing,
        'duplicate_times': len(duplicate_times),
        'zero_prices': len(zero_prices),
        'zero_volume': len(zero_volume_days),
        'daily_missing': daily_missing,
        'completeness_rate': (len(df) / (len(df) + total_missing) * 100) if total_missing > 0 else 100.0
    }

def generate_markdown_report(report, output_path):
    """
    生成Markdown格式的报告
    """
    md_content = f"""# 1分钟K线数据完整性检查报告

**生成时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 📊 数据概览

| 项目 | 值 |
|------|-----|
| 数据文件 | `{os.path.basename(report['file_path'])}` |
| 开始时间 | {report['start_date']} |
| 结束时间 | {report['end_date']} |
| 时间跨度 | {report['total_days']} 天 |
| 总记录数 | {report['total_records']:,} 条 |

---

## 🔍 数据完整性分析（已排除正常休市时段）

### 缺失数据统计

| 指标 | 数量 |
|------|------|
| 异常小间隔缺失 (1-60分钟) | {len(report['missing_gaps'])} 个 |
| 异常大间隔 (>1小时) | {len(report['large_gaps'])} 个 |
| 正常休市时段（已排除） | {len(report['normal_breaks'])} 个 |
| 总缺失记录数 | {report['total_missing']:,} 条 |
| **数据完整度** | **{report['completeness_rate']:.2f}%** |

### 数据质量统计

| 指标 | 数量 |
|------|------|
| 重复时间戳 | {report['duplicate_times']} 条 |
| 价格异常记录 | {report['zero_prices']} 条 |
| 零成交量记录 | {report['zero_volume']:,} 条 |

---

## ⚠️ 缺失数据详情

### 异常缺失详情（前30条，已排除正常休市）

| 序号 | 前一时间 | 当前时间 | 间隔(分钟) | 缺失条数 |
|------|----------|----------|-----------|---------|
"""

    # 添加缺失间隔详情
    for idx, gap in enumerate(report['missing_gaps'][:30], 1):
        md_content += f"| {idx} | {gap['prev_time']} | {gap['curr_time']} | {gap['gap_minutes']} | {gap['missing_count']} |\n"

    if len(report['missing_gaps']) > 30:
        md_content += f"\n*... 还有 {len(report['missing_gaps']) - 30} 个缺失间隔未显示*\n"

    # 添加按日期统计
    if report['daily_missing']:
        md_content += "\n---\n\n## 📅 按日期统计缺失数据（缺失最多的前30天）\n\n"
        md_content += "| 日期 | 缺失条数 |\n"
        md_content += "|------|----------|\n"

        sorted_daily = sorted(report['daily_missing'].items(), key=lambda x: x[1], reverse=True)
        for date, count in sorted_daily[:30]:
            md_content += f"| {date} | {count} |\n"

        if len(sorted_daily) > 30:
            md_content += f"\n*... 还有 {len(sorted_daily) - 30} 天有缺失数据*\n"

    # 添加大间隔详情
    if report['large_gaps']:
        md_content += "\n---\n\n## 📊 异常大间隔详情（>1小时）\n\n"
        md_content += "| 序号 | 前一时间 | 当前时间 | 间隔(小时) | 类型 |\n"
        md_content += "|------|----------|----------|-----------|------|\n"

        for idx, gap in enumerate(report['large_gaps'][:20], 1):
            md_content += f"| {idx} | {gap['prev_time']} | {gap['curr_time']} | {gap['gap_hours']:.2f} | {gap['gap_type']} |\n"

        if len(report['large_gaps']) > 20:
            md_content += f"\n*... 还有 {len(report['large_gaps']) - 20} 个异常大间隔未显示*\n"

    # 添加建议
    md_content += """
---

## 💡 建议

"""

    if report['completeness_rate'] >= 99:
        md_content += "✅ 数据完整性良好（≥99%），可以正常使用。\n"
    elif report['completeness_rate'] >= 95:
        md_content += "⚠️ 数据完整性尚可（≥95%），建议补充缺失数据以提高准确性。\n"
    else:
        md_content += "❌ 数据完整性较差（<95%），强烈建议补充缺失数据。\n"

    if report['duplicate_times'] > 0:
        md_content += f"- ⚠️ 发现 {report['duplicate_times']} 条重复时间戳，建议清理。\n"

    if report['zero_prices'] > 0:
        md_content += f"- ⚠️ 发现 {report['zero_prices']} 条价格异常记录，建议检查数据源。\n"

    md_content += """
---

## 📝 说明

- **异常缺失**: 指在正常交易时段内相邻两条记录之间的时间间隔异常，可能是数据采集故障或系统问题
- **异常大间隔**: 指超过1小时的异常间隔，通常不应出现在已排除正常休市时段的数据中
- **正常休市时段（已排除）**: 以下时段的数据间隔被视为正常，不计入缺失：
  - 日盘收盘到夜盘开盘: 16:30 - 17:15 (45分钟)
  - 夜盘收盘到日盘开盘: 03:00 - 09:15 (约6小时)
  - 午休时间: 12:00 - 13:00 (1小时)
  - 周末休市: 周五收盘至周一开盘 (约54小时)
- **数据完整度**: 计算公式为 `实际记录数 / (实际记录数 + 缺失记录数) × 100%`

### HKFE交易时段

- 夜盘: 17:15 - 次日03:00
- 日盘上午: 09:15 - 12:00
- 日盘下午: 13:00 - 16:30

---

*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

    # 写入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(md_content)

    print(f"✅ Markdown报告已保存至: {output_path}")

if __name__ == '__main__':
    # 数据文件路径
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
    csv_path = os.path.join(data_dir, '1min_MHImain_HKFE.csv')

    # 输出报告路径
    report_path = os.path.join(data_dir, 'data_integrity_report.md')

    # 执行检查
    report = check_data_integrity(csv_path)

    # 生成Markdown报告
    generate_markdown_report(report, report_path)

    print("\n" + "=" * 80)
    print("✅ 数据完整性检查完成")
    print("=" * 80)
