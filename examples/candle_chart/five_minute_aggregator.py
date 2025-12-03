"""
5分钟K线聚合工具

从1分钟K线数据合成5分钟K线，按照 period_utils 中现有的5分钟规则：
- 使用 get_period_start(dt, Interval.MINUTE_5, exchange) 获取周期起始时间
- 仅在交易时段内的分钟K线会被聚合
"""

from typing import List, Optional, Dict
from datetime import datetime

from vnpy.trader.object import BarData
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.period_utils import get_period_start


def get_5min_period_start(dt: datetime, exchange: Optional[Exchange]) -> Optional[datetime]:
    """
    获取指定时间所属的5分钟周期开始时间。

    直接复用 period_utils.get_period_start 中对 Interval.MINUTE_5 的实现，
    保证与全局规则完全一致。
    """
    return get_period_start(dt, Interval.MINUTE_5, exchange)


def aggregate_to_5minutes(one_minute_bars: List[BarData]) -> List[BarData]:
    """
    从1分钟K线数据合成5分钟K线。

    Args:
        one_minute_bars: 1分钟K线列表（按时间升序）

    Returns:
        5分钟K线列表
    """
    if not one_minute_bars:
        return []

    period_groups: Dict[datetime, List[BarData]] = {}

    for bar in one_minute_bars:
        period_start = get_5min_period_start(bar.datetime, bar.exchange)
        if period_start is None:
            continue

        if period_start not in period_groups:
            period_groups[period_start] = []

        period_groups[period_start].append(bar)

    five_minute_bars: List[BarData] = []

    for period_start, bars in sorted(period_groups.items()):
        if not bars:
            continue

        first_bar = bars[0]
        open_price = first_bar.open_price
        high_price = max(b.high_price for b in bars)
        low_price = min(b.low_price for b in bars)
        close_price = bars[-1].close_price
        volume = sum(b.volume for b in bars)

        five_bar = BarData(
            symbol=first_bar.symbol,
            exchange=first_bar.exchange or Exchange.HKFE,
            datetime=period_start,
            interval=Interval.MINUTE_5,
            open_price=open_price,
            high_price=high_price,
            low_price=low_price,
            close_price=close_price,
            volume=volume,
            gateway_name=first_bar.gateway_name,
        )

        five_minute_bars.append(five_bar)

    return five_minute_bars


