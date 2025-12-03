"""
1小时K线聚合工具

从1分钟K线数据合成1小时K线，按照HKFE交易时段规则。
复用 vnpy.trader.period_utils.aggregate_to_1hour_from_minutes 共同逻辑。
"""

from typing import List

from vnpy.trader.object import BarData
from vnpy.trader.period_utils import aggregate_to_1hour_from_minutes


def aggregate_to_1hour(one_minute_bars: List[BarData]) -> List[BarData]:
    """
    从1分钟K线数据合成1小时K线（HKFE规则）
    
    该函数是对 period_utils.aggregate_to_1hour_from_minutes 的简单封装，
    保持向后兼容性。

    Args:
        one_minute_bars: 1分钟K线数据列表（已按时间排序）

    Returns:
        1小时K线数据列表
    """
    return aggregate_to_1hour_from_minutes(one_minute_bars)


