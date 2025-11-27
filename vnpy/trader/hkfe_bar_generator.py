"""
港期（HKFE）专用的BarGenerator实现

使用DataManager的精确时间边界合成逻辑，替代标准的BarGenerator时间整除规则。
保持与BarGenerator完全兼容的接口，可以无缝替换。
"""
from datetime import datetime, timedelta
from typing import Callable, Optional
from collections.abc import Callable as CallableType

from vnpy.trader.constant import Interval, Exchange
from vnpy.trader.object import BarData, TickData
from vnpy.trader.utility import BarGenerator
from vnpy.trader.database import DB_TZ


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
        """获取5分钟周期起始时间（复制自ManagerEngine的逻辑）"""
        # 检查是否在交易时段
        hour = bar_dt.hour
        minute = bar_dt.minute
        time_value = hour * 100 + minute
        
        # 港期交易时段：09:15-12:00, 13:00-16:30, 17:15-03:00
        if not (915 <= time_value <= 1200 or 
                1300 <= time_value <= 1630 or 
                1715 <= time_value <= 2359 or
                0 <= time_value <= 300):
            return None
        
        # 计算5分钟K线的起始时间（在交易时段内）
        period_start_minute = (minute // 5) * 5
        period_start = bar_dt.replace(minute=period_start_minute, second=0, microsecond=0)
        
        return period_start
    
    def _get_hkfe_hour_period(self, bar_dt: datetime) -> Optional[datetime]:
        """获取1小时周期起始时间（复制自ManagerEngine的逻辑）"""
        hour = bar_dt.hour
        minute = bar_dt.minute
        time_value = hour * 100 + minute
        
        # 夜盘时段
        if 1715 <= time_value <= 1814:
            return bar_dt.replace(hour=17, minute=15, second=0, microsecond=0)
        elif 1815 <= time_value <= 1914:
            return bar_dt.replace(hour=18, minute=15, second=0, microsecond=0)
        elif 1915 <= time_value <= 2014:
            return bar_dt.replace(hour=19, minute=15, second=0, microsecond=0)
        elif 2015 <= time_value <= 2114:
            return bar_dt.replace(hour=20, minute=15, second=0, microsecond=0)
        elif 2115 <= time_value <= 2214:
            return bar_dt.replace(hour=21, minute=15, second=0, microsecond=0)
        elif 2215 <= time_value <= 2314:
            return bar_dt.replace(hour=22, minute=15, second=0, microsecond=0)
        elif 2315 <= time_value <= 2359:
            return bar_dt.replace(hour=23, minute=15, second=0, microsecond=0)
        elif 0 <= time_value <= 14:
            return (bar_dt - timedelta(days=1)).replace(hour=23, minute=15, second=0, microsecond=0)
        elif 15 <= time_value <= 114:
            return bar_dt.replace(hour=0, minute=15, second=0, microsecond=0)
        elif 115 <= time_value <= 214:
            return bar_dt.replace(hour=1, minute=15, second=0, microsecond=0)
        elif 215 <= time_value <= 929:
            weekday = bar_dt.weekday()
            if weekday == 0:  # 周一
                return (bar_dt - timedelta(days=2)).replace(hour=2, minute=15, second=0, microsecond=0)
            elif weekday == 6:  # 周日
                return (bar_dt - timedelta(days=1)).replace(hour=2, minute=15, second=0, microsecond=0)
            else:
                return bar_dt.replace(hour=2, minute=15, second=0, microsecond=0)
        # 日盘时段
        elif 930 <= time_value <= 1029:
            return bar_dt.replace(hour=9, minute=30, second=0, microsecond=0)
        elif 1030 <= time_value <= 1129:
            return bar_dt.replace(hour=10, minute=30, second=0, microsecond=0)
        elif (1130 <= time_value <= 1200) or (1300 <= time_value <= 1329):
            return bar_dt.replace(hour=11, minute=30, second=0, microsecond=0)
        elif 1330 <= time_value <= 1429:
            return bar_dt.replace(hour=13, minute=30, second=0, microsecond=0)
        elif 1430 <= time_value <= 1529:
            return bar_dt.replace(hour=14, minute=30, second=0, microsecond=0)
        elif 1530 <= time_value <= 1629:
            return bar_dt.replace(hour=15, minute=30, second=0, microsecond=0)
        else:
            if 915 <= time_value <= 929:
                weekday = bar_dt.weekday()
                if weekday == 0:  # 周一
                    return (bar_dt - timedelta(days=2)).replace(hour=2, minute=15, second=0, microsecond=0)
                elif weekday == 6:  # 周日
                    return (bar_dt - timedelta(days=1)).replace(hour=2, minute=15, second=0, microsecond=0)
                else:
                    return bar_dt.replace(hour=2, minute=15, second=0, microsecond=0)
            return None
    
    def _get_hkfe_4hour_period(self, bar_dt: datetime) -> Optional[datetime]:
        """获取4小时周期起始时间（复制自ManagerEngine的逻辑）"""
        hour = bar_dt.hour
        minute = bar_dt.minute
        time_value = hour * 100 + minute
        
        if 1715 <= time_value <= 2114:
            return bar_dt.replace(hour=17, minute=15, second=0, microsecond=0)
        elif 2115 <= time_value <= 2359:
            return bar_dt.replace(hour=21, minute=15, second=0, microsecond=0)
        elif 0 <= time_value <= 114:
            return (bar_dt - timedelta(days=1)).replace(hour=21, minute=15, second=0, microsecond=0)
        elif 115 <= time_value <= 300:
            return bar_dt.replace(hour=1, minute=15, second=0, microsecond=0)
        elif 915 <= time_value <= 1129:
            weekday = bar_dt.weekday()
            if weekday == 0:  # 周一
                return (bar_dt - timedelta(days=2)).replace(hour=1, minute=15, second=0, microsecond=0)
            else:
                return bar_dt.replace(hour=1, minute=15, second=0, microsecond=0)
        elif (1130 <= time_value <= 1200) or (1300 <= time_value <= 1629):
            return bar_dt.replace(hour=11, minute=30, second=0, microsecond=0)
        else:
            return None
    
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
            # 更新当前周期
            if self.window_bar:
                self.window_bar.high_price = max(self.window_bar.high_price, bar.high_price)
                self.window_bar.low_price = min(self.window_bar.low_price, bar.low_price)
                self.window_bar.close_price = bar.close_price
                self.window_bar.volume += bar.volume
                self.window_bar.turnover += bar.turnover
                self.window_bar.open_interest = bar.open_interest
    
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
            # 更新当前周期
            if self.hour_bar:
                self.hour_bar.high_price = max(self.hour_bar.high_price, bar.high_price)
                self.hour_bar.low_price = min(self.hour_bar.low_price, bar.low_price)
                self.hour_bar.close_price = bar.close_price
                self.hour_bar.volume += bar.volume
                self.hour_bar.turnover += bar.turnover
                self.hour_bar.open_interest = bar.open_interest
    
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
            # 更新当前周期
            if self.window_bar:
                self.window_bar.high_price = max(self.window_bar.high_price, bar.high_price)
                self.window_bar.low_price = min(self.window_bar.low_price, bar.low_price)
                self.window_bar.close_price = bar.close_price
                self.window_bar.volume += bar.volume
                self.window_bar.turnover += bar.turnover
                self.window_bar.open_interest = bar.open_interest


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

