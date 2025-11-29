"""
周期工具模块 - 提供时间划分和开盘价获取功能

该模块提供以下功能：
1. 周期时间划分：支持标准交易所和港期（HKFE）的特殊时间划分机制
2. 大周期开盘价获取：大周期K线的开盘价取该周期第一根分钟K线的开盘价

该模块被以下模块复用：
- K线图表模块 (vnpy/trader/ui/widget.py)
- DataRecorder模块 (vnpy_datarecorder/)
- DataManager模块 (vnpy_datamanager/)

使用示例：
    from vnpy.trader.period_utils import get_period_start, PeriodOpenPriceHelper
    
    # 获取周期起始时间
    period_start = get_period_start(dt, Interval.HOUR, Exchange.HKFE)
    
    # 获取开盘价
    helper = PeriodOpenPriceHelper()
    open_price = helper.get_period_open_price(period_start, Interval.HOUR, "MHI2511.HKFE", tick)
"""

from datetime import datetime, timedelta
from typing import Optional

from vnpy.trader.constant import Interval, Exchange
from vnpy.trader.object import BarData, TickData
from vnpy.trader.utility import extract_vt_symbol
from vnpy.trader.database import BaseDatabase, get_database


def is_hkfe_trading_time(bar_dt: datetime) -> bool:
    """
    判断给定时间是否在香港期货交易时段内
    
    香港期货交易时段：
    - 日盘：09:15 - 12:00, 13:00 - 16:30
    - 夜盘：17:15 - 03:00（次日凌晨）
    
    Args:
        bar_dt: K线时间（带时区信息）
    
    Returns:
        True 如果在交易时段内，否则 False
    """
    hour = bar_dt.hour
    minute = bar_dt.minute
    time_value = hour * 100 + minute  # 用于比较的时间值，如 09:15 = 915
    
    # 日盘早段：09:15 - 12:00
    if 915 <= time_value <= 1200:
        return True
    
    # 日盘午段：13:00 - 16:30
    if 1300 <= time_value <= 1630:
        return True
    
    # 夜盘：17:15 - 23:59
    if 1715 <= time_value <= 2359:
        return True
    
    # 夜盘：00:00 - 03:00（次日凌晨）
    if 0 <= time_value <= 300:
        return True
    
    return False


def get_period_start(dt: datetime, interval: Interval, exchange: Optional[Exchange] = None) -> Optional[datetime]:
    """
    根据周期获取K线的起始时间
    
    对于HKFE交易所：
    - 5分钟K线：按5分钟对齐，但会过滤非交易时段
    - 1小时K线按照港期交易时段边界（17:15-18:14, 18:15-19:14, ...）
    - 4小时K线按照HKFE交易时段边界：
      1. 17:15-21:14：第一根4小时K线（时间戳：17:15）
      2. 21:15-01:14：第二根4小时K线（时间戳：21:15）
      3. 01:15-03:00 + 09:15-11:29：第三根4小时K线（时间戳：01:15）
      4. 11:30-12:00 + 13:00-16:29：第四根4小时K线（时间戳：11:30）
    
    特殊情况：
    - 周末：周五夜盘01:15开始的周期，延续到周一11:29结束
    - 金融假期：假期前01:15开始的周期，延续到假期后第一个交易日11:29结束
    
    Args:
        dt: 时间
        interval: K线周期
        exchange: 交易所（可选，如果为None则根据时间判断是否为HKFE）
    
    Returns:
        周期起始时间，如果无法确定则返回None
    """
    is_hkfe = (exchange == Exchange.HKFE) if exchange else False
    
    hour = dt.hour
    minute = dt.minute
    time_value = hour * 100 + minute
    
    if interval == Interval.MINUTE_5:
        # 5分钟周期：按5分钟对齐
        if is_hkfe:
            # 港期：先检查是否在交易时段
            if not is_hkfe_trading_time(dt):
                return None
        aligned_minute = (minute // 5) * 5
        return dt.replace(minute=aligned_minute, second=0, microsecond=0)
    
    elif interval == Interval.HOUR:
        # 1小时周期
        if is_hkfe:
            # HKFE交易所：使用精确时间边界
            return get_hkfe_hour_period_start(dt)
        else:
            # 其他交易所：按小时对齐
            return dt.replace(minute=0, second=0, microsecond=0)
    
    elif interval == Interval.HOUR_4:
        # 4小时周期
        if is_hkfe:
            # HKFE交易所：使用精确时间边界
            if 1715 <= time_value <= 2114:
                # 时段1: 17:15-21:14
                return dt.replace(hour=17, minute=15, second=0, microsecond=0)
            
            elif 2115 <= time_value <= 2359:
                # 时段2前半: 21:15-23:59
                return dt.replace(hour=21, minute=15, second=0, microsecond=0)
            
            elif 0 <= time_value <= 114:
                # 时段2后半: 00:00-01:14（属于前一天21:15开始的周期）
                return (dt - timedelta(days=1)).replace(hour=21, minute=15, second=0, microsecond=0)
            
            elif 115 <= time_value <= 300:
                # 时段3前半: 01:15-03:00
                return dt.replace(hour=1, minute=15, second=0, microsecond=0)
            
            elif 915 <= time_value <= 1129:
                # 时段3后半: 09:15-11:29
                # 需要判断是否跨越周末或金融假期
                # 如果是周一（weekday=0），回溯到上周六的01:15
                weekday = dt.weekday()
                if weekday == 0:  # 周一
                    # 回溯到上周六（2天前）的01:15
                    return (dt - timedelta(days=2)).replace(hour=1, minute=15, second=0, microsecond=0)
                else:
                    # 非周一，使用当天的01:15
                    return dt.replace(hour=1, minute=15, second=0, microsecond=0)
            
            elif (1130 <= time_value <= 1200) or (1300 <= time_value <= 1629):
                # 时段4: 11:30-12:00 + 13:00-16:29
                return dt.replace(hour=11, minute=30, second=0, microsecond=0)
            
            else:
                # 非交易时段
                return None
        else:
            # 其他交易所：按4小时对齐（每4小时一根）
            aligned_hour = (hour // 4) * 4
            return dt.replace(hour=aligned_hour, minute=0, second=0, microsecond=0)
    
    elif interval == Interval.DAILY:
        # 日线：按日期对齐
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)
    
    else:
        # 默认按分钟对齐
        return dt.replace(second=0, microsecond=0)


def get_hkfe_hour_period_start(dt: datetime) -> Optional[datetime]:
    """
    获取HKFE交易所1小时K线的周期起始时间
    
    按照港期交易时段边界划分：
    - 夜盘：17:15-18:14, 18:15-19:14, 19:15-20:14, 20:15-21:14, 
            21:15-22:14, 22:15-23:14, 23:15-00:14, 00:15-01:14, 01:15-02:14
    - 跨休市：02:15-09:29（跨休市时段，需要特殊处理周末）
    - 日盘：09:30-10:29, 10:30-11:29, 11:30-12:00+13:00-13:29,
            13:30-14:29, 14:30-15:29, 15:30-16:29
    
    Args:
        dt: 时间
    
    Returns:
        1小时周期的起始时间，如果不在交易时段则返回None
    """
    hour = dt.hour
    minute = dt.minute
    time_value = hour * 100 + minute
    
    # 夜盘时段
    if 1715 <= time_value <= 1814:
        return dt.replace(hour=17, minute=15, second=0, microsecond=0)
    elif 1815 <= time_value <= 1914:
        return dt.replace(hour=18, minute=15, second=0, microsecond=0)
    elif 1915 <= time_value <= 2014:
        return dt.replace(hour=19, minute=15, second=0, microsecond=0)
    elif 2015 <= time_value <= 2114:
        return dt.replace(hour=20, minute=15, second=0, microsecond=0)
    elif 2115 <= time_value <= 2214:
        return dt.replace(hour=21, minute=15, second=0, microsecond=0)
    elif 2215 <= time_value <= 2314:
        return dt.replace(hour=22, minute=15, second=0, microsecond=0)
    elif 2315 <= time_value <= 2359:
        return dt.replace(hour=23, minute=15, second=0, microsecond=0)
    elif 0 <= time_value <= 14:
        # 00:00-00:14 属于前一天23:15开始的周期
        return (dt - timedelta(days=1)).replace(hour=23, minute=15, second=0, microsecond=0)
    elif 15 <= time_value <= 114:
        return dt.replace(hour=0, minute=15, second=0, microsecond=0)
    elif 115 <= time_value <= 214:
        return dt.replace(hour=1, minute=15, second=0, microsecond=0)
    elif 215 <= time_value <= 929:
        # 02:15-09:29 跨休市时段，需要特殊处理周末
        weekday = dt.weekday()
        if weekday == 0:  # 周一
            # 回溯到上周六（2天前）的02:15
            return (dt - timedelta(days=2)).replace(hour=2, minute=15, second=0, microsecond=0)
        elif weekday == 6:  # 周日
            # 回溯到前一天（周六）的02:15
            return (dt - timedelta(days=1)).replace(hour=2, minute=15, second=0, microsecond=0)
        else:
            return dt.replace(hour=2, minute=15, second=0, microsecond=0)
    # 日盘时段
    elif 930 <= time_value <= 1029:
        return dt.replace(hour=9, minute=30, second=0, microsecond=0)
    elif 1030 <= time_value <= 1129:
        return dt.replace(hour=10, minute=30, second=0, microsecond=0)
    elif (1130 <= time_value <= 1200) or (1300 <= time_value <= 1329):
        # 11:30-12:00 + 13:00-13:29 跨午休
        return dt.replace(hour=11, minute=30, second=0, microsecond=0)
    elif 1330 <= time_value <= 1429:
        return dt.replace(hour=13, minute=30, second=0, microsecond=0)
    elif 1430 <= time_value <= 1529:
        return dt.replace(hour=14, minute=30, second=0, microsecond=0)
    elif 1530 <= time_value <= 1629:
        return dt.replace(hour=15, minute=30, second=0, microsecond=0)
    else:
        # 09:15-09:29 特殊处理（属于跨休市时段）
        if 915 <= time_value <= 929:
            weekday = dt.weekday()
            if weekday == 0:  # 周一
                return (dt - timedelta(days=2)).replace(hour=2, minute=15, second=0, microsecond=0)
            elif weekday == 6:  # 周日
                return (dt - timedelta(days=1)).replace(hour=2, minute=15, second=0, microsecond=0)
            else:
                return dt.replace(hour=2, minute=15, second=0, microsecond=0)
        # 非交易时段
        return None


def get_hkfe_4hour_period(dt: datetime) -> tuple[Optional[datetime], int]:
    """
    获取HKFE交易所4小时K线的周期起始时间和周期索引
    
    精确的4小时时间边界（闭区间）：
    1. 17:15-21:14：第一根4小时K线（时间戳：17:15，索引：1）
    2. 21:15-01:14：第二根4小时K线（时间戳：21:15，索引：2）
    3. 01:15-03:00 + 09:15-11:29：第三根4小时K线（时间戳：01:15，索引：3）
    4. 11:30-12:00 + 13:00-16:29：第四根4小时K线（时间戳：11:30，索引：4）
    
    Args:
        dt: 时间
    
    Returns:
        (period_start, period_index): 周期起始时间和周期索引(1-4)，如果不在交易时段则返回(None, 0)
    """
    hour = dt.hour
    minute = dt.minute
    time_value = hour * 100 + minute
    
    # 判断属于哪个时段（闭区间）
    if 1715 <= time_value <= 2114:
        # 时段1: 17:15-21:14 → 时间戳 17:15
        period_start = dt.replace(hour=17, minute=15, second=0, microsecond=0)
        return (period_start, 1)
    
    elif 2115 <= time_value <= 2359:
        # 时段2前半: 21:15-23:59 → 时间戳 21:15（当日）
        period_start = dt.replace(hour=21, minute=15, second=0, microsecond=0)
        return (period_start, 2)
    
    elif 0 <= time_value <= 114:
        # 时段2后半: 00:00-01:14 → 时间戳 21:15（前一日）
        period_start = (dt - timedelta(days=1)).replace(hour=21, minute=15, second=0, microsecond=0)
        return (period_start, 2)
    
    elif 115 <= time_value <= 300:
        # 时段3前半: 01:15-03:00 → 时间戳 01:15（当日）
        period_start = dt.replace(hour=1, minute=15, second=0, microsecond=0)
        return (period_start, 3)
    
    elif 915 <= time_value <= 1129:
        # 时段3后半: 09:15-11:29
        # 需要判断是否跨越周末或金融假期
        weekday = dt.weekday()
        if weekday == 0:  # 周一
            # 回溯到上周六（2天前）的01:15
            period_start = (dt - timedelta(days=2)).replace(hour=1, minute=15, second=0, microsecond=0)
        else:
            # 非周一，使用当天的01:15
            period_start = dt.replace(hour=1, minute=15, second=0, microsecond=0)
        return (period_start, 3)
    
    elif (1130 <= time_value <= 1200) or (1300 <= time_value <= 1629):
        # 时段4: 11:30-12:00 + 13:00-16:29 → 时间戳 11:30
        period_start = dt.replace(hour=11, minute=30, second=0, microsecond=0)
        return (period_start, 4)
    
    else:
        # 非交易时段（03:01-09:14, 12:01-12:59, 16:30-17:14）
        return (None, 0)


class PeriodOpenPriceHelper:
    """
    大周期开盘价获取辅助类
    
    用于获取大周期K线的开盘价（取该周期第一根分钟K线的开盘价）
    
    使用示例：
        helper = PeriodOpenPriceHelper()
        open_price = helper.get_period_open_price(
            period_start,
            Interval.HOUR,
            "MHI2511.HKFE",
            tick=tick,
            minute_bar_generator=bg,
            history_data=history
        )
    """
    
    def __init__(self, database: Optional[BaseDatabase] = None):
        """
        初始化
        
        Args:
            database: 数据库实例，如果为None则使用get_database()
        """
        self.database: BaseDatabase = database or get_database()
        self._minute_bars_cache: dict[datetime, BarData] = {}
        self._warnings: set[str] = set()  # 防重复警告
        self._errors: set[str] = set()  # 防重复错误
    
    def get_period_open_price(
        self,
        period_start: datetime,
        interval: Interval,
        vt_symbol: str,
        tick: Optional[TickData] = None,
        minute_bar_generator: Optional[object] = None,
        history_data: Optional[list[BarData]] = None
    ) -> Optional[float]:
        """
        获取该周期第一根分钟K线的开盘价
        
        对于5分钟、1小时、4小时等大周期K线，开盘价应该是该周期第一根分钟K线的开盘价，
        而不是第一个tick的价格。
        
        查找优先级：
        1. 数据库查询（最高优先级）
        2. 1分钟K线缓存（_minute_bars_cache）
        3. 历史数据缓存（history_data，如果提供）
        4. BarGenerator（实时生成中的1分钟K线）
        5. Fallback（使用tick价格）
        
        Args:
            period_start: 周期开始时间
            interval: 周期类型
            vt_symbol: 合约代码
            tick: 当前tick数据（作为fallback）
            minute_bar_generator: 1分钟K线的BarGenerator实例（可选）
            history_data: 历史数据列表（可选，供K线图表模块使用）
        
        Returns:
            开盘价，如果无法获取则返回None
        """
        from vnpy.trader.constant import Interval as IntervalEnum
        from vnpy.trader.utility import extract_vt_symbol
        
        # 对于1分钟周期，直接使用tick价格
        if interval == IntervalEnum.MINUTE:
            return tick.last_price if tick else None
        
        # 获取周期内的第一根分钟K线
        # 对于5分钟K线，需要查找该5分钟周期内的第一根实际存在的分钟K线
        # 例如：18:30的5分钟K线，第一根分钟K线可能是18:30、18:31、18:32、18:33、18:34中的任意一个
        
        # 1. 优先从缓存查找（先尝试period_start本身）
        period_start_str = period_start.strftime('%Y-%m-%d %H:%M:%S') if hasattr(period_start, 'strftime') else str(period_start)
        # print(f"[DEBUG] get_period_open_price: 开始查找 | vt_symbol={vt_symbol}, interval={interval.value}, period_start={period_start_str}")
        
        if period_start in self._minute_bars_cache:
            cached_bar = self._minute_bars_cache[period_start]
            if cached_bar and cached_bar.open_price > 0:
                cached_dt = cached_bar.datetime.replace(tzinfo=None) if cached_bar.datetime.tzinfo else cached_bar.datetime
                period_start_dt = period_start.replace(tzinfo=None) if period_start.tzinfo else period_start
                
                # 归一化时间（只保留到分钟级别）
                cached_dt_normalized = cached_dt.replace(second=0, microsecond=0)
                period_start_dt_normalized = period_start_dt.replace(second=0, microsecond=0)
                
                cached_dt_str = cached_dt.strftime('%Y-%m-%d %H:%M:%S')
                
                # 验证缓存中的K线datetime是否等于period_start
                if (cached_dt_normalized.year == period_start_dt_normalized.year and
                    cached_dt_normalized.month == period_start_dt_normalized.month and
                    cached_dt_normalized.day == period_start_dt_normalized.day and
                    cached_dt_normalized.hour == period_start_dt_normalized.hour and
                    cached_dt_normalized.minute == period_start_dt_normalized.minute):
                    # print(f"[DEBUG] get_period_open_price: ✓ 从缓存找到（验证通过）| cached_dt={cached_dt_str}, open_price={cached_bar.open_price}")
                    return cached_bar.open_price
                else:
                    # 缓存中的K线datetime不等于period_start，清除缓存
                    # print(f"[DEBUG] get_period_open_price: ⚠ 缓存中的K线datetime不匹配，清除缓存 | cached_dt={cached_dt_str} != period_start={period_start_str}, 将重新查询")
                    del self._minute_bars_cache[period_start]
            else:
                # print(f"[DEBUG] get_period_open_price: ✗ 缓存中的K线无效 | cached_bar={cached_bar}, open_price={cached_bar.open_price if cached_bar else 'None'}")
                pass
        else:
            # print(f"[DEBUG] get_period_open_price: - 缓存未命中 | period_start={period_start_str}")
            pass
        
        # 2. 从数据库查询该周期内的所有分钟K线，找到第一根
        try:
            symbol, exchange = extract_vt_symbol(vt_symbol)
            
            # 计算周期结束时间（包含边界）
            # 注意：5分钟周期包含5根1分钟K线，例如09:55的5分钟K线包含09:55、09:56、09:57、09:58、09:59
            # 统一时区处理：先处理period_start的时区，再计算query范围
            from vnpy.trader.database import DB_TZ
            # 如果period_start没有时区信息，需要添加时区
            if period_start.tzinfo is None:
                period_start_with_tz = period_start.replace(tzinfo=DB_TZ)
            else:
                period_start_with_tz = period_start
            
            if interval == IntervalEnum.MINUTE_5:
                # 5分钟周期：查询period_start到period_start+5分钟（不包含）
                # 规则：分钟数对5取模，余数为0就是第一根K线，余数为4就是第五根K线
                # 例如：10:00的5分钟K线应该包含10:00(0%5=0), 10:01(1%5=1), 10:02(2%5=2), 10:03(3%5=3), 10:04(4%5=4)
                # 为了避免数据库查询边界问题，稍微扩大查询范围，然后在代码中严格过滤
                query_start = period_start_with_tz - timedelta(seconds=1)  # 从period_start前1秒开始，确保包含period_start
                query_end = period_start_with_tz + timedelta(minutes=5, seconds=1)  # 到period_start+5分钟+1秒，确保包含所有可能的K线
            elif interval == IntervalEnum.HOUR:
                # 1小时周期：查询period_start到period_start+60分钟（不包含）
                query_start = period_start_with_tz
                query_end = period_start_with_tz + timedelta(minutes=60)
            elif interval == IntervalEnum.HOUR_4:
                # 4小时周期：查询period_start到period_start+240分钟（不包含）
                query_start = period_start_with_tz
                query_end = period_start_with_tz + timedelta(minutes=240)
            else:
                # 其他周期：使用小范围查询
                query_start = period_start_with_tz
                query_end = period_start_with_tz + timedelta(minutes=1)
            
            # 确保query_start和query_end有时区信息
            if query_start.tzinfo is None:
                query_start = query_start.replace(tzinfo=DB_TZ)
            if query_end.tzinfo is None:
                query_end = query_end.replace(tzinfo=DB_TZ)
            
            # 调试日志：记录查询参数（已注释，避免刷屏）
            period_start_str = period_start_with_tz.strftime('%Y-%m-%d %H:%M:%S')
            query_start_str = query_start.strftime('%Y-%m-%d %H:%M:%S')
            query_end_str = query_end.strftime('%Y-%m-%d %H:%M:%S')
            # print(f"[DEBUG] get_period_open_price: 查询1分钟K线 | vt_symbol={vt_symbol}, interval={interval.value}")
            # print(f"[DEBUG] get_period_open_price: 原始period_start={period_start.strftime('%Y-%m-%d %H:%M:%S') if hasattr(period_start, 'strftime') else str(period_start)}, 时区={period_start.tzinfo}")
            # print(f"[DEBUG] get_period_open_price: 处理后period_start={period_start_str}, 时区={period_start_with_tz.tzinfo}")
            # print(f"[DEBUG] get_period_open_price: 查询范围 | query_start={query_start_str}, query_end={query_end_str}, 应该包含: {period_start_str}到{query_end_str}（不包含）")
            # print(f"[DEBUG] get_period_open_price: 查询参数详情 | symbol={symbol}, exchange={exchange}")
            
            minute_bars = self.database.load_bar_data(
                symbol,
                exchange,
                IntervalEnum.MINUTE,
                query_start,
                query_end
            )
            
            # print(f"[DEBUG] get_period_open_price: 数据库查询结果 | 找到 {len(minute_bars) if minute_bars else 0} 根1分钟K线")
            
            if minute_bars:
                # 按时间排序，找到该周期内的第一根分钟K线
                minute_bars.sort(key=lambda x: x.datetime)
                
                # 调试日志：列出所有查询到的1分钟K线（已注释，避免刷屏）
                # print(f"[DEBUG] get_period_open_price: 查询到的1分钟K线列表:")
                # for idx, mb in enumerate(minute_bars[:10]):  # 只显示前10根
                #     mb_dt = mb.datetime.replace(tzinfo=None) if mb.datetime.tzinfo else mb.datetime
                #     mb_dt_str = mb_dt.strftime('%Y-%m-%d %H:%M:%S')
                #     mb_dt_normalized = mb_dt.replace(second=0, microsecond=0)
                #     period_start_dt_normalized = period_start.replace(tzinfo=None).replace(second=0, microsecond=0) if period_start.tzinfo else period_start.replace(second=0, microsecond=0)
                #     mb_minute = mb_dt_normalized.minute
                #     period_start_minute = period_start_dt_normalized.minute
                #     mb_in_range = (period_start_minute <= mb_minute < period_start_minute + 5)
                #     print(f"  [{idx}] datetime={mb_dt_str}, minute={mb_minute}, period_start_minute={period_start_minute}, 在范围内={mb_in_range}, open_price={mb.open_price}")
                # if len(minute_bars) > 10:
                #     print(f"  ... (还有 {len(minute_bars) - 10} 根)")
                
                # 验证每根分钟K线是否属于该周期，找到第一根有效的
                period_start_dt = period_start.replace(tzinfo=None) if period_start.tzinfo else period_start
                query_end_dt = query_end.replace(tzinfo=None) if query_end.tzinfo else query_end
                
                for minute_bar in minute_bars:
                    minute_dt = minute_bar.datetime.replace(tzinfo=None) if minute_bar.datetime.tzinfo else minute_bar.datetime
                    
                    # 检查该分钟K线是否在该周期内（包含period_start，不包含query_end）
                    # 注意：需要精确匹配分钟，忽略秒和微秒
                    minute_dt_normalized = minute_dt.replace(second=0, microsecond=0)
                    period_start_dt_normalized = period_start_dt.replace(second=0, microsecond=0)
                    query_end_dt_normalized = query_end_dt.replace(second=0, microsecond=0)
                    
                    minute_dt_str = minute_dt.strftime('%Y-%m-%d %H:%M:%S')
                    period_start_str = period_start_dt.strftime('%Y-%m-%d %H:%M:%S')
                    
                    # 检查该分钟K线是否在该周期内
                    # 对于5分钟K线，使用取模运算判断：分钟数对5取模，余数为0-4属于同一个5分钟周期
                    # 例如：14:05的5分钟K线应该包含14:05(5%5=0), 14:06(6%5=1), 14:07(7%5=2), 14:08(8%5=3), 14:09(9%5=4)
                    # 规则：1) 日期和小时相同 2) 分钟数对5取模的基准值相同（都是0），且minute_dt的分钟数在period_start的分钟数+0到+4范围内
                    period_start_minute = period_start_dt_normalized.minute
                    minute_dt_minute = minute_dt_normalized.minute
                    
                    # 检查日期和小时是否相同
                    same_date_hour = (
                        minute_dt_normalized.year == period_start_dt_normalized.year and
                        minute_dt_normalized.month == period_start_dt_normalized.month and
                        minute_dt_normalized.day == period_start_dt_normalized.day and
                        minute_dt_normalized.hour == period_start_dt_normalized.hour
                    )
                    
                    # 检查是否属于同一个5分钟周期
                    # 规则：分钟数对5取模，余数为0-4属于同一个5分钟周期
                    # 例如：14:05的5分钟K线包含14:05(5%5=0第一根), 14:06(6%5=1第二根), 14:07(7%5=2第三根), 14:08(8%5=3第四根), 14:09(9%5=4第五根)
                    # 判断条件：
                    # 1. period_start的分钟数对5取模必须为0（例如14:05的分钟数5 % 5 = 0）
                    # 2. minute_dt的分钟数必须在period_start到period_start+4范围内（连续5分钟）
                    period_start_base = period_start_minute % 5  # period_start必须是5的倍数分钟，余数为0
                    minute_dt_base = minute_dt_minute % 5  # minute_dt的余数应该是0-4
                    same_5min_period = (
                        period_start_base == 0 and  # period_start必须是5的倍数分钟（0, 5, 10, 15, ...）
                        period_start_minute <= minute_dt_minute < period_start_minute + 5  # minute_dt在period_start到period_start+4范围内（连续5分钟）
                    )
                    
                    if same_date_hour and same_5min_period:
                        # print(f"[DEBUG] get_period_open_price: 检查1分钟K线 | minute_dt={minute_dt_str}, period_start={period_start_str}, 在周期范围内")
                        
                        # 进一步验证：该分钟K线的周期起始时间应该等于period_start
                        # 这样可以确保找到的是真正属于该周期的第一根分钟K线
                        minute_period_start = get_period_start(minute_dt, interval, exchange)
                        if minute_period_start:
                            minute_period_start_dt = minute_period_start.replace(tzinfo=None) if minute_period_start.tzinfo else minute_period_start
                            minute_period_start_dt_normalized = minute_period_start_dt.replace(second=0, microsecond=0)
                            minute_period_start_str = minute_period_start_dt.strftime('%Y-%m-%d %H:%M:%S')
                            
                            # print(f"[DEBUG] get_period_open_price: 验证周期归属 | minute_dt={minute_dt_str}, minute_period_start={minute_period_start_str}, period_start={period_start_str}")
                            
                            # 只有当该分钟K线属于该周期时，才使用它的开盘价
                            # 比较时忽略秒和微秒，只比较到分钟级别
                            # 注意：对于跨日的周期（如港期的夜盘），需要比较日期
                            if (minute_period_start_dt_normalized.year == period_start_dt_normalized.year and
                                minute_period_start_dt_normalized.month == period_start_dt_normalized.month and
                                minute_period_start_dt_normalized.day == period_start_dt_normalized.day and
                                minute_period_start_dt_normalized.hour == period_start_dt_normalized.hour and
                                minute_period_start_dt_normalized.minute == period_start_dt_normalized.minute):
                                if minute_bar.open_price > 0:
                                    # 关键修复：只有当该分钟K线的datetime正好等于period_start时，才返回并缓存它
                                    # 这样可以确保返回的是period_start对应的1分钟K线，而不是其他分钟K线
                                    if (minute_dt_normalized.year == period_start_dt_normalized.year and
                                        minute_dt_normalized.month == period_start_dt_normalized.month and
                                        minute_dt_normalized.day == period_start_dt_normalized.day and
                                        minute_dt_normalized.hour == period_start_dt_normalized.hour and
                                        minute_dt_normalized.minute == period_start_dt_normalized.minute):
                                        # print(f"[DEBUG] get_period_open_price: ✓ 找到匹配的1分钟K线（datetime正好等于period_start）| minute_dt={minute_dt_str}, open_price={minute_bar.open_price}, 返回此开盘价并缓存")
                                        # 缓存该分钟K线（使用period_start作为key）
                                        self._minute_bars_cache[period_start] = minute_bar
                                        return minute_bar.open_price
                                    else:
                                        # print(f"[DEBUG] get_period_open_price: ⚠ 找到属于该周期的1分钟K线，但datetime不等于period_start | minute_dt={minute_dt_str} != period_start={period_start_str}, open_price={minute_bar.open_price}, 说明period_start的1分钟K线不存在，返回None")
                                        # 如果period_start的1分钟K线不存在，返回None，而不是使用其他分钟K线的开盘价
                                        # 因为此时5分钟K线的开盘价可能已经是正确的（来自DataManager的合成逻辑）
                                        return None
                                else:
                                    # print(f"[DEBUG] get_period_open_price: ✗ 1分钟K线开盘价为0，跳过 | minute_dt={minute_dt_str}")
                                    pass
                            else:
                                # print(f"[DEBUG] get_period_open_price: ✗ 周期不匹配，跳过 | minute_period_start={minute_period_start_str} != period_start={period_start_str}")
                                pass
                        else:
                            # 如果get_period_start返回None，说明该分钟K线不在交易时段，跳过
                            # print(f"[DEBUG] get_period_open_price: ✗ get_period_start返回None（非交易时段），跳过 | minute_dt={minute_dt_str}")
                            continue
                    else:
                        # 不在周期范围内（已注释日志，避免刷屏）
                        # if minute_dt_normalized < period_start_dt_normalized:
                        #     print(f"[DEBUG] get_period_open_price: ✗ 1分钟K线时间早于周期起始，跳过 | minute_dt={minute_dt_str} < period_start={period_start_str}")
                        if minute_dt_normalized >= query_end_dt_normalized:
                            # print(f"[DEBUG] get_period_open_price: ✗ 1分钟K线时间超出周期范围，提前退出 | minute_dt={minute_dt_str} >= query_end")
                            break
                    
                    # 如果该分钟K线的时间已经超过query_end，说明后面的都不属于该周期，可以提前退出
                    if minute_dt_normalized >= query_end_dt_normalized:
                        break
        except Exception as e:
            warning_key = f"{vt_symbol}_{period_start}_db_error"
            if warning_key not in self._warnings:
                self._warnings.add(warning_key)
                # 这里不输出日志，由调用者决定是否记录
        
        # 3. 从历史数据缓存查找（如果提供）
        if history_data:
            # print(f"[DEBUG] get_period_open_price: 从历史数据查找 | history_data数量={len(history_data)}")
            # 查找该周期内的所有分钟K线，找到第一根
            period_minute_bars = []
            period_start_dt = period_start.replace(tzinfo=None) if period_start.tzinfo else period_start
            
            # 计算周期结束时间
            if interval == IntervalEnum.MINUTE_5:
                period_end_dt = period_start_dt + timedelta(minutes=4)
            elif interval == IntervalEnum.HOUR:
                period_end_dt = period_start_dt + timedelta(minutes=59)
            elif interval == IntervalEnum.HOUR_4:
                period_end_dt = period_start_dt + timedelta(minutes=239)
            else:
                period_end_dt = period_start_dt + timedelta(minutes=1)
            
            period_start_str = period_start_dt.strftime('%Y-%m-%d %H:%M:%S')
            period_end_str = period_end_dt.strftime('%Y-%m-%d %H:%M:%S')
            # print(f"[DEBUG] get_period_open_price: 历史数据查找范围 | period_start={period_start_str}, period_end={period_end_str}")
            
            for bar in history_data:
                if bar.interval == IntervalEnum.MINUTE:
                    bar_dt = bar.datetime.replace(tzinfo=None) if bar.datetime.tzinfo else bar.datetime
                    # 检查该分钟K线是否在该周期内
                    if period_start_dt <= bar_dt < period_end_dt:
                        period_minute_bars.append(bar)
            
            # print(f"[DEBUG] get_period_open_price: 历史数据中找到 | {len(period_minute_bars)} 根1分钟K线在周期范围内")
            
            if period_minute_bars:
                # 按时间排序，找到第一根
                period_minute_bars.sort(key=lambda x: x.datetime)
                first_minute_bar = period_minute_bars[0]
                first_dt_str = first_minute_bar.datetime.strftime('%Y-%m-%d %H:%M:%S')
                # print(f"[DEBUG] get_period_open_price: ✓ 从历史数据找到第一根 | datetime={first_dt_str}, open_price={first_minute_bar.open_price}")
                if first_minute_bar.open_price > 0:
                    # 更新缓存
                    self._minute_bars_cache[period_start] = first_minute_bar
                    return first_minute_bar.open_price
                else:
                    # print(f"[DEBUG] get_period_open_price: ✗ 历史数据第一根开盘价为0，跳过")
                    pass
        
        # 4. 从BarGenerator查找（如果提供）
        if minute_bar_generator and hasattr(minute_bar_generator, 'bar'):
            bg_bar = minute_bar_generator.bar
            if bg_bar:
                bg_bar_dt = bg_bar.datetime.replace(tzinfo=None) if bg_bar.datetime.tzinfo else bg_bar.datetime
                period_start_dt = period_start.replace(tzinfo=None) if period_start.tzinfo else period_start
                
                # 计算周期结束时间
                if interval == IntervalEnum.MINUTE_5:
                    period_end_dt = period_start_dt + timedelta(minutes=4)
                elif interval == IntervalEnum.HOUR:
                    period_end_dt = period_start_dt + timedelta(minutes=59)
                elif interval == IntervalEnum.HOUR_4:
                    period_end_dt = period_start_dt + timedelta(minutes=239)
                else:
                    period_end_dt = period_start_dt + timedelta(minutes=1)
                
                bg_bar_dt_str = bg_bar_dt.strftime('%Y-%m-%d %H:%M:%S')
                period_start_str = period_start_dt.strftime('%Y-%m-%d %H:%M:%S')
                period_end_str = period_end_dt.strftime('%Y-%m-%d %H:%M:%S')
                # print(f"[DEBUG] get_period_open_price: 从BarGenerator查找 | bg_bar_dt={bg_bar_dt_str}, period_range=[{period_start_str}, {period_end_str})")
                
                # 检查BarGenerator中的分钟K线是否在该周期内
                if period_start_dt <= bg_bar_dt < period_end_dt:
                    # print(f"[DEBUG] get_period_open_price: ✓ BarGenerator中的K线在周期范围内 | open_price={bg_bar.open_price}")
                    if bg_bar.open_price > 0:
                        return bg_bar.open_price
                    else:
                        # print(f"[DEBUG] get_period_open_price: ✗ BarGenerator中的K线开盘价为0，跳过")
                        pass
                else:
                    # print(f"[DEBUG] get_period_open_price: ✗ BarGenerator中的K线不在周期范围内")
                    pass
        
        # 5. Fallback：使用tick价格
        if tick and tick.last_price > 0:
            warning_key = f"{vt_symbol}_{period_start}_fallback"
            if warning_key not in self._warnings:
                self._warnings.add(warning_key)
            # print(f"[DEBUG] get_period_open_price: ⚠ Fallback使用tick价格 | tick.last_price={tick.last_price}")
            return tick.last_price
        
        # print(f"[DEBUG] get_period_open_price: ✗ 所有查找方式都失败，返回None")
        
        return None
    
    def cache_minute_bar(self, bar: BarData) -> None:
        """
        缓存1分钟K线
        
        Args:
            bar: 1分钟K线数据
        """
        from vnpy.trader.constant import Interval as IntervalEnum
        
        if bar.interval != IntervalEnum.MINUTE:
            return
        
        bar_period = get_period_start(bar.datetime, IntervalEnum.MINUTE, bar.exchange)
        if bar_period:
            self._minute_bars_cache[bar_period] = bar
    
    def clear_cache(self) -> None:
        """清空缓存"""
        self._minute_bars_cache.clear()
        self._warnings.clear()
        self._errors.clear()

