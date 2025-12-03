"""
港期（HKFE）专用的BarGenerator实现

使用DataManager的精确时间边界合成逻辑，替代标准的BarGenerator时间整除规则。
保持与BarGenerator完全兼容的接口，可以无缝替换。

复用period_utils.py中的周期判断函数，避免重复代码。
"""
from datetime import datetime, timedelta
from typing import Callable, Optional
from collections.abc import Callable as CallableType

from vnpy.trader.constant import Interval, Exchange
from vnpy.trader.object import BarData, TickData
from vnpy.trader.utility import BarGenerator
from vnpy.trader.database import DB_TZ
from vnpy.trader.period_utils import (
    get_period_start,
    get_hkfe_hour_period_start,
    get_hkfe_4hour_period,
    update_bar_ohlcv,
)


class HKFEBarGenerator(BarGenerator):
    """
    港期（HKFE）专用的BarGenerator
    
    继承自BarGenerator，但使用DataManager的精确时间边界合成逻辑：
    - 5分钟K线：遵循港期交易时段边界
    - 1小时K线：使用16个精确时间边界（17:15-18:14, 18:15-19:14, ...）
    - 4小时K线：使用4个精确时间边界（17:15-21:14, 21:15-01:14, ...）
    
    对于非HKFE交易所或非支持的周期，自动降级到标准BarGenerator逻辑。
    """
    
    def __init__(
        self,
        on_bar: Callable,
        window: int = 0,
        on_window_bar: Callable | None = None,
        interval: Interval = Interval.MINUTE,
        daily_end: Optional[datetime.time] = None,
        exchange: Exchange | None = None,
        symbol: str | None = None
    ) -> None:
        """
        构造函数
        
        Args:
            on_bar: 1分钟K线回调函数
            window: 窗口大小（对于分钟线是分钟数，对于小时线是小时数）
            on_window_bar: 合成K线回调函数
            interval: 目标周期
            daily_end: 日线收盘时间（仅用于日线合成）
            exchange: 交易所（用于判断是否使用HKFE精确逻辑）
            symbol: 合约代码（用于判断是否使用HKFE精确逻辑）
        """
        super().__init__(on_bar, window, on_window_bar, interval, daily_end)
        
        self.exchange = exchange
        self.symbol = symbol
        
        # 判断是否使用HKFE精确逻辑
        self.use_hkfe_logic = (
            exchange == Exchange.HKFE and
            interval in [Interval.MINUTE_5, Interval.HOUR, Interval.HOUR_4]
        )
        
        # 当前周期的起始时间（用于判断周期是否完成）
        self.current_period_start: Optional[datetime] = None
    
    def _get_hkfe_5minute_period(self, bar_dt: datetime) -> Optional[datetime]:
        """获取5分钟周期起始时间（复用period_utils）"""
        return get_period_start(bar_dt, Interval.MINUTE_5, Exchange.HKFE)
    
    def _get_hkfe_hour_period(self, bar_dt: datetime) -> Optional[datetime]:
        """获取1小时周期起始时间（复用period_utils）"""
        return get_hkfe_hour_period_start(bar_dt)
    
    def _get_hkfe_4hour_period(self, bar_dt: datetime) -> Optional[datetime]:
        """获取4小时周期起始时间（复用period_utils）"""
        period_start, _ = get_hkfe_4hour_period(bar_dt)
        return period_start
    
    def update_bar(self, bar: BarData) -> None:
        """
        重写update_bar方法，使用HKFE精确逻辑
        
        对于HKFE交易所和支持的周期，使用精确时间边界
        否则降级到标准BarGenerator逻辑
        """
        if not self.use_hkfe_logic:
            # 非HKFE或非支持周期，使用标准逻辑
            super().update_bar(bar)
            return
        
        # 对于HKFE，使用精确时间边界逻辑
        if self.interval == Interval.MINUTE:
            # 1分钟K线直接传递，不需要合成
            super().update_bar(bar)
        elif self.interval == Interval.MINUTE_5:
            self._update_bar_hkfe_5minute(bar)
        elif self.interval == Interval.HOUR:
            self._update_bar_hkfe_hour(bar)
        elif self.interval == Interval.HOUR_4:
            self._update_bar_hkfe_4hour(bar)
        else:
            # 其他周期使用标准逻辑
            super().update_bar(bar)
    
    def _update_bar_hkfe_5minute(self, bar: BarData) -> None:
        """使用HKFE精确逻辑合成5分钟K线"""
        # 获取该K线所属的5分钟周期
        period_start = self._get_hkfe_5minute_period(bar.datetime)
        
        if period_start is None:
            # 非交易时段，跳过
            return
        
        # 检查是否是新周期
        if self.current_period_start != period_start:
            # 完成上一个周期
            if self.window_bar and self.on_window_bar:
                self.on_window_bar(self.window_bar)
            
            # 开始新周期
            self.current_period_start = period_start
            self.window_bar = BarData(
                symbol=bar.symbol,
                exchange=bar.exchange,
                datetime=period_start,
                interval=Interval.MINUTE_5,
                gateway_name=bar.gateway_name,
                open_price=bar.open_price,
                high_price=bar.high_price,
                low_price=bar.low_price,
                close_price=bar.close_price,
                volume=bar.volume,
                turnover=bar.turnover,
                open_interest=bar.open_interest
            )
        else:
            # 更新当前周期（使用通用聚合函数）
            if self.window_bar:
                update_bar_ohlcv(self.window_bar, bar, is_new_period=False)
    
    def _update_bar_hkfe_hour(self, bar: BarData) -> None:
        """使用HKFE精确逻辑合成1小时K线"""
        # 获取该K线所属的1小时周期
        period_start = self._get_hkfe_hour_period(bar.datetime)
        
        if period_start is None:
            # 非交易时段，跳过
            return
        
        # 检查是否是新周期
        if self.current_period_start != period_start:
            # 完成上一个周期
            if self.hour_bar and self.on_window_bar:
                self.on_window_bar(self.hour_bar)
            
            # 开始新周期
            self.current_period_start = period_start
            self.hour_bar = BarData(
                symbol=bar.symbol,
                exchange=bar.exchange,
                datetime=period_start,
                interval=Interval.HOUR,
                gateway_name=bar.gateway_name,
                open_price=bar.open_price,
                high_price=bar.high_price,
                low_price=bar.low_price,
                close_price=bar.close_price,
                volume=bar.volume,
                turnover=bar.turnover,
                open_interest=bar.open_interest
            )
        else:
            # 更新当前周期（使用通用聚合函数）
            if self.hour_bar:
                update_bar_ohlcv(self.hour_bar, bar, is_new_period=False)
    
    def _update_bar_hkfe_4hour(self, bar: BarData) -> None:
        """使用HKFE精确逻辑合成4小时K线"""
        # 获取该K线所属的4小时周期
        period_start = self._get_hkfe_4hour_period(bar.datetime)
        
        if period_start is None:
            # 非交易时段，跳过
            return
        
        # 检查是否是新周期
        if self.current_period_start != period_start:
            # 完成上一个周期
            if self.window_bar and self.on_window_bar:
                self.on_window_bar(self.window_bar)
            
            # 开始新周期
            self.current_period_start = period_start
            self.window_bar = BarData(
                symbol=bar.symbol,
                exchange=bar.exchange,
                datetime=period_start,
                interval=Interval.HOUR_4,
                gateway_name=bar.gateway_name,
                open_price=bar.open_price,
                high_price=bar.high_price,
                low_price=bar.low_price,
                close_price=bar.close_price,
                volume=bar.volume,
                turnover=bar.turnover,
                open_interest=bar.open_interest
            )
        else:
            # 更新当前周期（使用通用聚合函数）
            if self.window_bar:
                update_bar_ohlcv(self.window_bar, bar, is_new_period=False)


def create_bar_generator(
    on_bar: Callable,
    window: int = 0,
    on_window_bar: Callable | None = None,
    interval: Interval = Interval.MINUTE,
    daily_end: Optional[datetime.time] = None,
    exchange: Exchange | None = None,
    symbol: str | None = None
) -> BarGenerator:
    """
    工厂函数：根据交易所自动创建合适的BarGenerator
    
    对于HKFE交易所和支持的周期（5分钟、1小时、4小时），返回HKFEBarGenerator
    否则返回标准BarGenerator
    
    Args:
        on_bar: 1分钟K线回调函数
        window: 窗口大小
        on_window_bar: 合成K线回调函数
        interval: 目标周期
        daily_end: 日线收盘时间
        exchange: 交易所
        symbol: 合约代码
    
    Returns:
        BarGenerator实例（HKFEBarGenerator或标准BarGenerator）
    """
    if exchange == Exchange.HKFE and interval in [Interval.MINUTE_5, Interval.HOUR, Interval.HOUR_4]:
        return HKFEBarGenerator(
            on_bar, window, on_window_bar, interval, daily_end, exchange, symbol
        )
    else:
        return BarGenerator(on_bar, window, on_window_bar, interval, daily_end)

