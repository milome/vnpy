"""
4小时K线聚合工具

从1分钟K线数据合成4小时K线，按照HKFE交易时段规则
"""

from datetime import datetime

from vnpy.trader.object import BarData
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.period_utils import get_hkfe_4hour_period


def get_4h_period_start(dt: datetime) -> datetime | None:
    """
    获取指定时间所属的4小时周期开始时间（HKFE）

    完全复用 vnpy.trader.period_utils.get_hkfe_4hour_period，
    确保与全局4小时周期划分规则保持一致。
    """
    period_start, period_index = get_hkfe_4hour_period(dt)
    return period_start


def aggregate_to_4hours(one_minute_bars: list[BarData]) -> list[BarData]:
    """
    从1分钟K线数据合成4小时K线

    Args:
        one_minute_bars: 1分钟K线数据列表（已排序）

    Returns:
        4小时K线数据列表
    """
    if not one_minute_bars:
        return []

    # 按4小时周期分组（使用全局HKFE规则）
    period_groups: dict[datetime, list[BarData]] = {}

    for bar in one_minute_bars:
        period_start = get_4h_period_start(bar.datetime)
        if period_start is None:
            continue

        if period_start not in period_groups:
            period_groups[period_start] = []

        period_groups[period_start].append(bar)

    # 聚合每个周期
    four_hour_bars: list[BarData] = []

    for period_start, bars in sorted(period_groups.items()):
        if not bars:
            continue

        # 开盘价：第一个1分钟K线的开盘价
        first_bar = bars[0]
        open_price = first_bar.open_price

        # 最高价、最低价、收盘价
        high_price = max(bar.high_price for bar in bars)
        low_price = min(bar.low_price for bar in bars)
        close_price = bars[-1].close_price  # 最后一个1分钟K线的收盘价

        # 成交量
        volume = sum(bar.volume for bar in bars)

        # 创建4小时K线
        four_hour_bar = BarData(
            symbol=first_bar.symbol,
            exchange=first_bar.exchange or Exchange.HKFE,
            datetime=period_start,
            interval=Interval.HOUR_4,
            open_price=open_price,
            high_price=high_price,
            low_price=low_price,
            close_price=close_price,
            volume=volume,
            gateway_name=first_bar.gateway_name
        )

        four_hour_bars.append(four_hour_bar)

    return four_hour_bars

