#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多周期自定义指标管理器

用于在多个周期计算和存储自定义指标数据，支持长期历史数据存储和实时增量更新。
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Literal
from pathlib import Path
import json
import pickle
import numpy as np
from collections import deque
from concurrent.futures import ThreadPoolExecutor, Future
import threading

from vnpy.trader.object import BarData
from vnpy.trader.constant import Interval
from vnpy.trader.database import get_database, BaseDatabase
from vnpy.trader.utility import extract_vt_symbol

# 尝试导入polars（用于parquet格式）
try:
    import polars as pl
    POLARS_AVAILABLE = True
except ImportError:
    POLARS_AVAILABLE = False
    pl = None


class IndicatorManager:
    """
    多周期自定义指标管理器
    
    功能：
    1. 支持多个周期的指标计算和存储
    2. 支持长期历史数据存储（文件系统或数据库）
    3. 实时增量更新指标值
    4. 支持自定义指标计算函数
    """
    
    def __init__(
        self,
        vt_symbol: str,
        storage_path: Optional[str] = None,
        use_database: bool = False,
        storage_format: Literal["pkl", "parquet"] = "parquet"
    ):
        """
        初始化指标管理器
        
        参数:
            vt_symbol: 合约代码，如 "MHImain.HKFE"
            storage_path: 指标数据存储路径（文件系统），如果为None则使用默认路径
            use_database: 是否使用数据库存储（需要扩展数据库schema）
            storage_format: 存储格式，"pkl" 或 "parquet"，默认为 "parquet"
                - "pkl": Python pickle格式，简单但只能被Python读取
                - "parquet": 列式存储格式，压缩率高，跨语言兼容，推荐使用
        """
        self.vt_symbol = vt_symbol
        self.symbol, self.exchange = extract_vt_symbol(vt_symbol)
        self.use_database = use_database
        self.storage_format = storage_format
        
        # 检查parquet支持
        if storage_format == "parquet" and not POLARS_AVAILABLE:
            self.write_log("警告: polars未安装，无法使用parquet格式，将回退到pkl格式")
            self.storage_format = "pkl"
        
        # 指标数据存储（历史值：已完成的K线对应的指标值）
        # 结构: {interval: {indicator_name: deque([...])}}
        self.indicators: Dict[Interval, Dict[str, deque]] = {}
        
        # 指标对应的时间戳（用于parquet格式存储）
        # 结构: {interval: {indicator_name: deque([datetime, ...])}}
        self.indicator_timestamps: Dict[Interval, Dict[str, deque]] = {}
        
        # 运行时指标值（正在聚合的K线对应的指标值）
        # 结构: {interval: {indicator_name: value}}
        self.runtime_indicators: Dict[Interval, Dict[str, Any]] = {}
        
        # 运行时K线数据（正在聚合的K线）
        # 结构: {interval: BarData | None}
        self.runtime_bars: Dict[Interval, Optional[BarData]] = {}
        
        # 指标计算函数
        # 结构: {interval: {indicator_name: callable}}
        self.calculators: Dict[Interval, Dict[str, Callable]] = {}
        
        # 历史K线数据缓存（用于初始化计算）
        self.history_bars: Dict[Interval, List[BarData]] = {}
        
        # 文件系统存储路径
        if storage_path is None:
            # 默认存储路径：.vntrader/indicators/{vt_symbol}/
            base_path = Path.home() / ".vntrader" / "indicators" / vt_symbol.replace(".", "_")
        else:
            base_path = Path(storage_path)
        
        self.storage_path = base_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # 数据库实例（如果使用数据库）
        self.database: Optional[BaseDatabase] = get_database() if use_database else None
        
        # 异步初始化相关
        self._executor: Optional[ThreadPoolExecutor] = None
        self._init_futures: Dict[Interval, Future] = {}  # 每个周期的初始化Future
        self._init_status: Dict[Interval, bool] = {}  # 每个周期的初始化状态
        self._init_lock = threading.Lock()  # 保护初始化状态的锁
        
    def register_indicator(
        self,
        interval: Interval,
        indicator_name: str,
        calculator: Callable[[List[BarData]], Any],
        max_history: int = 10000
    ):
        """
        注册一个指标计算函数
        
        参数:
            interval: K线周期
            indicator_name: 指标名称
            calculator: 指标计算函数，接收BarData列表，返回指标值（可以是单个值或数组）
            max_history: 最大历史数据保存数量（使用deque限制内存）
        """
        if interval not in self.indicators:
            self.indicators[interval] = {}
            self.indicator_timestamps[interval] = {}
            self.runtime_indicators[interval] = {}
            self.runtime_bars[interval] = None
            self.calculators[interval] = {}
        
        # 创建deque用于存储指标值和时间戳
        self.indicators[interval][indicator_name] = deque(maxlen=max_history)
        self.indicator_timestamps[interval][indicator_name] = deque(maxlen=max_history)
        self.runtime_indicators[interval][indicator_name] = None
        self.calculators[interval][indicator_name] = calculator
        
        self.write_log(f"注册指标: {interval.value} - {indicator_name}")
    
    def load_history_bars(
        self,
        interval: Interval,
        days: int = 365,
        database: Optional[BaseDatabase] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None
    ) -> List[BarData]:
        """
        从数据库加载历史K线数据
        
        参数:
            interval: K线周期
            days: 加载天数（仅在start和end为None时使用）
            database: 数据库实例（如果为None则使用self.database）
            start: 开始时间（可选，如果提供则忽略days参数）
            end: 结束时间（可选，如果为None则使用当前时间）
        
        返回:
            BarData列表
        """
        db = database or self.database
        if not db:
            self.write_log(f"警告: 未配置数据库，无法加载历史数据")
            return []
        
        # 确定时间范围
        if end is None:
            end = datetime.now()
        if start is None:
            start = end - timedelta(days=days)
        
        try:
            # 先尝试直接从数据库加载指定周期的数据
            bars = db.load_bar_data(
                symbol=self.symbol,
                exchange=self.exchange,
                interval=interval,
                start=start,
                end=end
            )
            
            # 如果数据库中没有数据，且请求的是5分钟周期，则尝试从1分钟数据合成
            if not bars and interval == Interval.MINUTE_5:
                self.write_log(f"5分钟周期数据不存在，尝试从1分钟数据合成")
                # 从数据库加载1分钟数据
                minute_bars = db.load_bar_data(
                    symbol=self.symbol,
                    exchange=self.exchange,
                    interval=Interval.MINUTE,
                    start=start,
                    end=end
                )
                
                if minute_bars:
                    # 使用BarGenerator从1分钟数据合成5分钟数据
                    bars = self._synthesize_bars_from_minute(minute_bars, interval)
                    self.write_log(f"从1分钟数据合成了 {len(bars)} 根5分钟K线")
                else:
                    self.write_log(f"警告: 1分钟周期数据也不存在，无法合成5分钟数据")
            
            self.history_bars[interval] = bars
            self.write_log(f"加载历史K线: {interval.value}, 共 {len(bars)} 根")
            return bars
        except Exception as e:
            self.write_log(f"加载历史K线失败: {e}")
            return []
    
    def _synthesize_bars_from_minute(
        self,
        minute_bars: List[BarData],
        target_interval: Interval
    ) -> List[BarData]:
        """
        从1分钟K线数据合成目标周期的K线数据
        
        支持合成：5分钟、15分钟、30分钟等能被60整除的周期
        """
        if not minute_bars:
            return []
        
        # 确定合成周期（分钟数）
        if target_interval == Interval.MINUTE_5:
            window = 5
        else:
            # 不支持其他周期的合成
            self.write_log(f"警告: 不支持从1分钟数据合成 {target_interval.value} 周期")
            return []
        
        # 合成K线
        synthesized_bars: List[BarData] = []
        window_bar: Optional[BarData] = None
        
        for bar in minute_bars:
            # 计算窗口起始时间（向下取整到窗口倍数）
            # 例如：分钟0-4合成0分钟，分钟5-9合成5分钟
            bar_minute = bar.datetime.minute
            window_start_minute = (bar_minute // window) * window
            
            # 创建窗口时间戳（窗口的起始时间）
            window_datetime = bar.datetime.replace(minute=window_start_minute, second=0, microsecond=0)
            
            # 检查是否是新窗口的开始
            # 新窗口的条件：窗口起始分钟改变，或者小时改变，或者日期改变
            is_new_window = (
                window_bar is None or
                window_bar.datetime != window_datetime
            )
            
            if is_new_window:
                # 保存上一个完整的窗口K线
                if window_bar is not None:
                    synthesized_bars.append(window_bar)
                
                # 创建新的窗口K线
                window_bar = BarData(
                    symbol=self.symbol,
                    exchange=self.exchange,
                    datetime=window_datetime,
                    interval=target_interval,
                    open_price=bar.open_price,
                    high_price=bar.high_price,
                    low_price=bar.low_price,
                    close_price=bar.close_price,
                    volume=bar.volume,
                    turnover=bar.turnover,
                    open_interest=bar.open_interest,
                    gateway_name="SYNTHESIZED"
                )
            else:
                # 更新当前窗口K线
                if window_bar:
                    window_bar.high_price = max(window_bar.high_price, bar.high_price)
                    window_bar.low_price = min(window_bar.low_price, bar.low_price)
                    window_bar.close_price = bar.close_price
                    window_bar.volume += bar.volume
                    window_bar.turnover += bar.turnover
                    window_bar.open_interest = bar.open_interest
        
        # 添加最后一个窗口K线
        if window_bar is not None:
            synthesized_bars.append(window_bar)
        
        return synthesized_bars
    
    def initialize_indicators(
        self,
        interval: Interval,
        days: int = 365,
        database: Optional[BaseDatabase] = None,
        fast_mode: bool = False,
        fast_days: int = 30,
        preserve_existing: bool = False
    ):
        """
        初始化指标：优先从文件加载，如果文件不存在或数据不足，则从数据库加载K线数据并计算
        
        参数:
            interval: K线周期
            days: 加载历史数据的天数（仅在需要从数据库加载时使用）
            database: 数据库实例
            fast_mode: 快速模式，如果为True，先加载fast_days天的数据快速完成初始化，
                       然后在后台继续加载完整数据（days天）。适用于回测等需要快速启动的场景。
            fast_days: 快速模式下的初始加载天数（默认30天）
            preserve_existing: 是否保留现有数据（用于异步增量加载），如果为True，则不清空现有数据，
                               而是追加或合并新数据。默认为False，会清空现有数据。
        """
        # 确保indicator_timestamps被初始化
        if interval not in self.indicator_timestamps:
            self.indicator_timestamps[interval] = {}
        
        # 步骤1：先尝试从文件加载已保存的指标数据（仅在非增量模式下）
        if not preserve_existing:
            file_loaded = self._load_indicator_from_file(interval)
        else:
            # 增量模式下，跳过文件加载（保留现有数据）
            file_loaded = False
        
        # 步骤2：检查是否需要从数据库加载K线数据并计算
        need_recalculate = False
        
        if not file_loaded:
            # 文件不存在或增量模式，需要从数据库加载并计算
            need_recalculate = True
            if preserve_existing:
                self.write_log(f"增量加载模式：将从数据库加载K线数据并追加到现有指标数据")
            else:
                self.write_log(f"指标文件不存在，将从数据库加载K线数据并计算")
        elif interval in self.calculators:
            # 文件已加载，检查是否所有已注册的指标都有数据
            for indicator_name in self.calculators[interval].keys():
                if (interval not in self.indicators or 
                    indicator_name not in self.indicators[interval] or
                    len(self.indicators[interval][indicator_name]) == 0):
                    # 某个指标没有数据，需要重新计算
                    need_recalculate = True
                    self.write_log(f"指标 {indicator_name} 数据不完整，将从数据库加载K线数据并计算")
                    break
        
        # 步骤3：如果需要，从数据库加载K线数据并计算所有指标
        if need_recalculate:
            # 快速模式：先加载少量数据快速完成初始化
            if fast_mode and not preserve_existing:
                self.write_log(f"快速模式：先加载 {fast_days} 天数据快速初始化，然后在后台继续加载 {days} 天完整数据")
                # 先加载少量数据
                fast_bars = self.load_history_bars(interval, fast_days, database)
                if not fast_bars:
                    self.write_log(f"警告: {interval.value} 周期无历史数据，跳过初始化")
                    return
                
                # 使用少量数据快速计算指标
                if interval in self.calculators:
                    valid_data_count = {}  # 记录每个指标的有效数据数量（非NaN）
                    for indicator_name, calculator in self.calculators[interval].items():
                        try:
                            indicator_values = calculator(fast_bars)
                            
                            # 确定需要保存的数据量
                            if isinstance(indicator_values, (list, np.ndarray)):
                                data_count = len(indicator_values)
                                # 统计有效数据数量（非NaN）
                                valid_count = sum(1 for v in indicator_values if not (isinstance(v, (int, float)) and np.isnan(v)))
                                valid_data_count[indicator_name] = valid_count
                            else:
                                data_count = 1
                                # 检查单个值是否有效
                                if not (isinstance(indicator_values, (int, float)) and np.isnan(indicator_values)):
                                    valid_data_count[indicator_name] = 1
                                else:
                                    valid_data_count[indicator_name] = 0
                            
                            # 检查并调整deque的maxlen
                            indicator_deque = self.indicators[interval][indicator_name]
                            current_maxlen = indicator_deque.maxlen if indicator_deque.maxlen else float('inf')
                            
                            if data_count > current_maxlen:
                                new_maxlen = max(data_count, current_maxlen * 2) if current_maxlen != float('inf') else data_count
                                old_values = list(indicator_deque)
                                old_timestamps = list(self.indicator_timestamps[interval].get(indicator_name, deque()))
                                self.indicators[interval][indicator_name] = deque(old_values, maxlen=new_maxlen)
                                if indicator_name not in self.indicator_timestamps[interval]:
                                    self.indicator_timestamps[interval][indicator_name] = deque(old_timestamps, maxlen=new_maxlen)
                                else:
                                    self.indicator_timestamps[interval][indicator_name] = deque(old_timestamps, maxlen=new_maxlen)
                                indicator_deque = self.indicators[interval][indicator_name]
                            
                            # 确保时间戳deque存在
                            if indicator_name not in self.indicator_timestamps[interval]:
                                self.indicator_timestamps[interval][indicator_name] = deque(
                                    maxlen=indicator_deque.maxlen
                                )
                            timestamp_deque = self.indicator_timestamps[interval][indicator_name]
                            
                            # 清空现有数据
                            indicator_deque.clear()
                            timestamp_deque.clear()
                            
                            # 添加快速加载的数据
                            if isinstance(indicator_values, (list, np.ndarray)):
                                for i, val in enumerate(indicator_values):
                                    if i < len(fast_bars):
                                        bar_time = fast_bars[i].datetime
                                        indicator_deque.append(val)
                                        timestamp_deque.append(bar_time)
                            else:
                                if len(fast_bars) > 0:
                                    bar_time = fast_bars[-1].datetime
                                    indicator_deque.append(indicator_values)
                                    timestamp_deque.append(bar_time)
                            
                            # 验证数据：确保至少有2个有效值（对于REF(O,1)这样的指标，至少需要2根K线）
                            valid_count = valid_data_count.get(indicator_name, 0)
                            if valid_count < 2:
                                self.write_log(
                                    f"警告: 快速初始化 {interval.value} - {indicator_name}, "
                                    f"有效数据只有 {valid_count} 个（需要至少2个），可能影响指标计算"
                                )
                            
                            self.write_log(
                                f"快速初始化: {interval.value} - {indicator_name}, "
                                f"共 {len(indicator_deque)} 个值（其中 {valid_count} 个有效值，快速模式，{fast_days}天数据）"
                            )
                        except Exception as e:
                            self.write_log(f"快速初始化失败: {interval.value} - {indicator_name}, 错误: {e}")
                            valid_data_count[indicator_name] = 0
                
                # 验证：确保所有指标都有数据（至少有一些有效值）
                all_indicators_ready = True
                if interval in self.calculators:
                    for indicator_name in self.calculators[interval].keys():
                        if indicator_name not in self.indicators[interval]:
                            all_indicators_ready = False
                            self.write_log(f"警告: 快速初始化后，指标 {indicator_name} 未找到")
                            break
                        indicator_deque = self.indicators[interval][indicator_name]
                        if len(indicator_deque) == 0:
                            all_indicators_ready = False
                            self.write_log(f"警告: 快速初始化后，指标 {indicator_name} 数据为空")
                            break
                        # 检查是否有至少一个有效值（非NaN）
                        has_valid_value = False
                        for val in indicator_deque:
                            if not (isinstance(val, (int, float)) and np.isnan(val)):
                                has_valid_value = True
                                break
                        if not has_valid_value:
                            self.write_log(f"警告: 快速初始化后，指标 {indicator_name} 所有值都是NaN")
                            # 不阻止初始化，因为后续数据可能会更新
                
                # 保存快速数据到 history_bars（用于后续增量计算）
                self.history_bars[interval] = fast_bars.copy()
                
                # 标记快速初始化完成（允许回测开始）
                with self._init_lock:
                    self._init_status[interval] = True
                
                if all_indicators_ready:
                    self.write_log(f"快速初始化完成: {interval.value} 周期，所有指标已就绪")
                else:
                    self.write_log(f"快速初始化完成: {interval.value} 周期，但部分指标可能未就绪（将在后续更新）")
                
                # 在后台继续加载完整数据（使用增量模式）
                if days > fast_days:
                    self.write_log(f"后台继续加载完整数据: {interval.value} 周期，{days} 天（增量模式，保留现有数据）")
                    # 使用异步方式增量加载完整数据
                    self.initialize_indicators_async(
                        interval,
                        days=days,
                        database=database,
                        preserve_existing=True,  # 保留现有数据
                        callback=lambda intv, success: self.write_log(
                            f"完整数据加载{'完成' if success else '失败'}: {intv.value}"
                        )
                    )
                else:
                    # 如果请求的天数小于等于快速天数，不需要继续加载
                    self._save_indicator_to_file(interval)
                
                return
            
            # 非快速模式：正常加载完整数据
            # 加载历史K线数据
            bars = self.load_history_bars(interval, days, database)
            if not bars:
                self.write_log(f"警告: {interval.value} 周期无历史数据，跳过初始化")
                return
            
            # 如果是增量模式，需要合并现有数据和新增数据
            if preserve_existing and interval in self.history_bars and len(self.history_bars[interval]) > 0:
                # 获取现有数据的最后时间戳
                existing_bars = self.history_bars[interval]
                last_existing_time = existing_bars[-1].datetime if existing_bars else None
                
                # 过滤出新增的K线数据（时间戳大于现有数据的最后时间戳）
                new_bars = [bar for bar in bars if last_existing_time is None or bar.datetime > last_existing_time]
                
                if new_bars:
                    self.write_log(
                        f"增量加载: {interval.value} 周期，现有 {len(existing_bars)} 根K线，"
                        f"新增 {len(new_bars)} 根K线，合并后共 {len(existing_bars) + len(new_bars)} 根K线"
                    )
                    # 合并现有数据和新增数据
                    all_bars = existing_bars + new_bars
                else:
                    self.write_log(f"增量加载: {interval.value} 周期，没有新数据需要加载")
                    all_bars = existing_bars
            else:
                # 非增量模式，使用全部数据
                all_bars = bars
            
            # 计算所有已注册的指标
            if interval in self.calculators:
                for indicator_name, calculator in self.calculators[interval].items():
                    try:
                        # 使用历史数据计算指标
                        indicator_values = calculator(all_bars)
                        
                        # 确定需要保存的数据量
                        if isinstance(indicator_values, (list, np.ndarray)):
                            data_count = len(indicator_values)
                        else:
                            data_count = 1
                        
                        # 检查当前deque的maxlen是否足够
                        indicator_deque = self.indicators[interval][indicator_name]
                        current_maxlen = indicator_deque.maxlen if indicator_deque.maxlen else float('inf')
                        
                        # 如果数据量大于maxlen，需要调整deque的maxlen
                        if data_count > current_maxlen:
                            # 创建新的deque，maxlen设为数据量（或更大，留一些余量）
                            new_maxlen = max(data_count, current_maxlen * 2) if current_maxlen != float('inf') else data_count
                            self.write_log(
                                f"警告: {interval.value} - {indicator_name} 的数据量 ({data_count}) "
                                f"超过当前maxlen ({current_maxlen})，将调整为 {new_maxlen}"
                            )
                            
                            # 创建新的deque（保留现有数据）
                            old_values = list(indicator_deque)
                            old_timestamps = list(self.indicator_timestamps[interval].get(indicator_name, deque()))
                            
                            # 创建新的deque
                            self.indicators[interval][indicator_name] = deque(old_values, maxlen=new_maxlen)
                            if indicator_name not in self.indicator_timestamps[interval]:
                                self.indicator_timestamps[interval][indicator_name] = deque(old_timestamps, maxlen=new_maxlen)
                            else:
                                self.indicator_timestamps[interval][indicator_name] = deque(old_timestamps, maxlen=new_maxlen)
                            
                            indicator_deque = self.indicators[interval][indicator_name]
                        
                        # 确保时间戳deque存在
                        if indicator_name not in self.indicator_timestamps[interval]:
                            self.indicator_timestamps[interval][indicator_name] = deque(
                                maxlen=indicator_deque.maxlen
                            )
                        timestamp_deque = self.indicator_timestamps[interval][indicator_name]
                        
                        # 如果是增量模式，保留现有数据，只更新新增部分
                        if preserve_existing and len(indicator_deque) > 0:
                            # 增量模式：只更新新增的数据部分
                            existing_count = len(indicator_deque)
                            if isinstance(indicator_values, (list, np.ndarray)):
                                # 只添加新增的数据（从existing_count开始）
                                new_values = indicator_values[existing_count:] if len(indicator_values) > existing_count else []
                                for i, val in enumerate(new_values):
                                    idx = existing_count + i
                                    if idx < len(all_bars):
                                        bar_time = all_bars[idx].datetime
                                        indicator_deque.append(val)
                                        timestamp_deque.append(bar_time)
                            else:
                                # 单个值的情况，如果数据量增加了，更新最后一个值
                                if data_count > existing_count:
                                    if len(all_bars) > 0:
                                        bar_time = all_bars[-1].datetime
                                        # 如果deque已满，需要替换最后一个值
                                        if len(indicator_deque) >= indicator_deque.maxlen:
                                            indicator_deque.pop()
                                            timestamp_deque.pop()
                                        indicator_deque.append(indicator_values)
                                        timestamp_deque.append(bar_time)
                            
                            self.write_log(
                                f"增量更新指标: {interval.value} - {indicator_name}, "
                                f"现有 {existing_count} 个值，新增 {len(indicator_deque) - existing_count} 个值，"
                                f"共 {len(indicator_deque)} 个值"
                            )
                        else:
                            # 非增量模式：清空现有数据并重新填充
                            indicator_deque.clear()
                            timestamp_deque.clear()
                            
                            if isinstance(indicator_values, (list, np.ndarray)):
                                # 如果是数组，逐个添加（需要对应的时间戳）
                                for i, val in enumerate(indicator_values):
                                    # 使用对应bar的时间戳
                                    if i < len(all_bars):
                                        bar_time = all_bars[i].datetime
                                        indicator_deque.append(val)
                                        timestamp_deque.append(bar_time)
                            else:
                                # 如果是单个值，只添加最后一个（使用最后一个bar的时间戳）
                                if len(all_bars) > 0:
                                    bar_time = all_bars[-1].datetime
                                    indicator_deque.append(indicator_values)
                                    timestamp_deque.append(bar_time)
                            
                            self.write_log(
                                f"计算指标: {interval.value} - {indicator_name}, "
                                f"共 {len(indicator_deque)} 个值 (maxlen={indicator_deque.maxlen})"
                            )
                    except Exception as e:
                        self.write_log(f"计算指标失败: {interval.value} - {indicator_name}, 错误: {e}")
            
            # 更新 history_bars（用于后续增量计算）
            self.history_bars[interval] = all_bars.copy()
            
            # 保存指标数据到文件
            self._save_indicator_to_file(interval)
            
            # 标记初始化完成
            with self._init_lock:
                self._init_status[interval] = True
        else:
            # 文件加载成功，直接使用文件数据
            if interval in self.indicators:
                total_indicators = len(self.indicators[interval])
                total_values = sum(len(deq) for deq in self.indicators[interval].values())
                self.write_log(
                    f"从文件加载指标: {interval.value}, "
                    f"共 {total_indicators} 个指标, 总 {total_values} 个值"
                )
            
            # 标记初始化完成
            with self._init_lock:
                self._init_status[interval] = True
    
    def initialize_indicators_async(
        self,
        interval: Interval,
        days: int = 365,
        database: Optional[BaseDatabase] = None,
        preserve_existing: bool = False,
        callback: Optional[Callable[[Interval, bool], None]] = None
    ) -> Future:
        """
        异步初始化指标：在后台线程中执行，不阻塞主线程
        
        参数:
            interval: K线周期
            days: 加载历史数据的天数（仅在需要从数据库加载时使用）
            database: 数据库实例
            preserve_existing: 是否保留现有数据（用于增量加载），如果为True，则不清空现有数据
            callback: 初始化完成后的回调函数，接收 (interval, success) 参数
        
        返回:
            Future对象，可以通过 future.result() 等待完成，或通过 future.done() 检查状态
        
        使用示例:
            # 在策略的 on_init 中异步初始化
            future = manager.initialize_indicators_async(
                Interval.MINUTE_5,
                days=365,
                database=database
            )
            # 策略可以立即继续执行，不等待初始化完成
            # 如果需要等待，可以调用: future.result(timeout=60)
        """
        # 检查是否已经在初始化中
        with self._init_lock:
            if interval in self._init_futures and not self._init_futures[interval].done():
                self.write_log(f"警告: {interval.value} 周期已在初始化中，跳过重复初始化")
                return self._init_futures[interval]
            
            # 初始化线程池（如果还没有）
            if self._executor is None:
                self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="IndicatorInit")
            
            # 增量模式下不重置初始化状态（保持快速模式已完成的标记）
            if not preserve_existing:
                self._init_status[interval] = False
            
            # 提交初始化任务
            def _init_task():
                try:
                    if preserve_existing:
                        self.write_log(f"开始异步增量初始化指标: {interval.value}（保留现有数据）")
                    else:
                        self.write_log(f"开始异步初始化指标: {interval.value}")
                    self.initialize_indicators(interval, days, database, preserve_existing=preserve_existing)
                    success = True
                    if preserve_existing:
                        self.write_log(f"异步增量初始化完成: {interval.value}")
                    else:
                        self.write_log(f"异步初始化完成: {interval.value}")
                except Exception as e:
                    success = False
                    self.write_log(f"异步初始化失败: {interval.value}, 错误: {e}")
                finally:
                    # 调用回调函数
                    if callback:
                        try:
                            callback(interval, success)
                        except Exception as e:
                            self.write_log(f"回调函数执行失败: {e}")
                    return success
            
            future = self._executor.submit(_init_task)
            self._init_futures[interval] = future
        
        return future
    
    def is_initialized(self, interval: Interval) -> bool:
        """
        检查指定周期的指标是否已初始化完成
        
        参数:
            interval: K线周期
        
        返回:
            bool: True表示已初始化完成，False表示正在初始化或未初始化
        """
        with self._init_lock:
            return self._init_status.get(interval, False)
    
    def wait_for_initialization(
        self,
        interval: Interval,
        timeout: Optional[float] = None
    ) -> bool:
        """
        等待指定周期的指标初始化完成
        
        参数:
            interval: K线周期
            timeout: 超时时间（秒），None表示无限等待
        
        返回:
            bool: True表示初始化成功，False表示超时或失败
        """
        with self._init_lock:
            if interval not in self._init_futures:
                # 如果没有初始化任务，检查是否已初始化
                return self._init_status.get(interval, False)
            
            future = self._init_futures[interval]
        
        try:
            result = future.result(timeout=timeout)
            return result
        except Exception as e:
            self.write_log(f"等待初始化超时或失败: {interval.value}, 错误: {e}")
            return False
    
    def shutdown_executor(self):
        """关闭线程池执行器（在策略停止时调用）"""
        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None
    
    def update_indicator(
        self,
        interval: Interval,
        bar: BarData,
        is_runtime: bool = False
    ):
        """
        实时更新指标：当收到新的K线时，增量计算指标值
        
        参数:
            interval: K线周期
            bar: 新的K线数据
            is_runtime: 是否为运行时更新（正在聚合的K线），False表示K线已完成
        """
        if interval not in self.calculators:
            return
        
        if is_runtime:
            # 运行时更新：更新正在聚合的K线对应的指标值
            self._update_runtime_indicator(interval, bar)
        else:
            # 历史更新：K线已完成，更新历史指标值
            self._update_history_indicator(interval, bar)
    
    def _update_runtime_indicator(self, interval: Interval, bar: BarData):
        """更新运行时指标值（基于正在聚合的K线）"""
        # 保存运行时K线
        self.runtime_bars[interval] = bar
        
        # 获取该周期的历史K线（包括已完成的K线）
        history_bars = self.history_bars.get(interval, [])
        
        # 构建包含运行时K线的完整列表（用于计算指标）
        # 历史K线 + 运行时K线
        bars_for_calc = history_bars + [bar]
        
        # 限制历史数据长度（保留最近N根K线，用于指标计算）
        max_bars_for_calc = 1000  # 根据指标需求调整
        if len(bars_for_calc) > max_bars_for_calc:
            bars_for_calc = bars_for_calc[-max_bars_for_calc:]
        
        # 更新所有已注册的指标
        for indicator_name, calculator in self.calculators[interval].items():
            try:
                # 检查是否有足够的数据计算指标
                # 对于 REF(O,1) 这样的指标，至少需要2根K线
                if len(bars_for_calc) < 2:
                    # 数据不足，不更新运行时指标值
                    # 保持为 None，让 get_indicator_smart 回退到历史值
                    continue
                
                # 使用包含运行时K线的完整列表计算指标
                indicator_values = calculator(bars_for_calc)
                
                # 处理返回值，只取最后一个值（对应运行时K线）
                if isinstance(indicator_values, (list, np.ndarray)):
                    if len(indicator_values) > 0:
                        value = indicator_values[-1]
                        # 检查值是否有效（不是NaN）
                        if not (isinstance(value, (int, float)) and np.isnan(value)):
                            self.runtime_indicators[interval][indicator_name] = value
                        else:
                            # 值是NaN，不更新运行时指标值
                            self.runtime_indicators[interval][indicator_name] = None
                else:
                    # 单个值
                    if not (isinstance(indicator_values, (int, float)) and np.isnan(indicator_values)):
                        self.runtime_indicators[interval][indicator_name] = indicator_values
                    else:
                        # 值是NaN，不更新运行时指标值
                        self.runtime_indicators[interval][indicator_name] = None
                
            except Exception as e:
                self.write_log(f"更新运行时指标失败: {interval.value} - {indicator_name}, 错误: {e}")
                # 发生错误时，不更新运行时指标值
                self.runtime_indicators[interval][indicator_name] = None
    
    def _update_history_indicator(self, interval: Interval, bar: BarData):
        """更新历史指标值（K线已完成）"""
        # 获取该周期的历史K线（用于计算需要历史数据的指标）
        history_bars = self.history_bars.get(interval, [])
        
        # 添加新K线到历史数据
        history_bars.append(bar)
        
        # 限制历史数据长度（保留最近N根K线，用于指标计算）
        max_bars_for_calc = 1000  # 根据指标需求调整
        if len(history_bars) > max_bars_for_calc:
            history_bars = history_bars[-max_bars_for_calc:]
        
        self.history_bars[interval] = history_bars
        
        # 清空运行时K线（因为已经完成）
        self.runtime_bars[interval] = None
        
        # 更新所有已注册的指标
        for indicator_name, calculator in self.calculators[interval].items():
            try:
                # 使用历史K线计算指标（只取最后一个值）
                indicator_values = calculator(history_bars)
                
                indicator_deque = self.indicators[interval][indicator_name]
                # 确保时间戳deque存在
                if indicator_name not in self.indicator_timestamps[interval]:
                    self.indicator_timestamps[interval][indicator_name] = deque(
                        maxlen=indicator_deque.maxlen
                    )
                timestamp_deque = self.indicator_timestamps[interval][indicator_name]
                
                # 处理返回值
                if isinstance(indicator_values, (list, np.ndarray)):
                    # 如果是数组，只取最后一个值
                    if len(indicator_values) > 0:
                        indicator_deque.append(indicator_values[-1])
                        timestamp_deque.append(bar.datetime)
                else:
                    # 如果是单个值
                    indicator_deque.append(indicator_values)
                    timestamp_deque.append(bar.datetime)
                
                # 清空运行时指标值（因为已经转为历史值）
                self.runtime_indicators[interval][indicator_name] = None
                
            except Exception as e:
                self.write_log(f"更新历史指标失败: {interval.value} - {indicator_name}, 错误: {e}")
        
        # 定期保存指标数据到文件（每100根K线保存一次）
        if len(history_bars) % 100 == 0:
            self._save_indicator_to_file(interval)
    
    def get_indicator(
        self,
        interval: Interval,
        indicator_name: str,
        index: int = -1,
        use_runtime: bool = False
    ) -> Optional[Any]:
        """
        获取指标值
        
        参数:
            interval: K线周期
            indicator_name: 指标名称
            index: 索引，-1表示最新值，-2表示上一个值，以此类推（仅用于历史值）
                   注意：index是相对于interval参数的周期数，不是调用它的周期数
                   例如：在1分钟周期中获取5分钟指标，index=-201表示200根5分钟K线前
            use_runtime: 是否使用运行时值（正在聚合的K线对应的指标值）
        
        返回:
            指标值，如果不存在则返回None
        """
        if interval not in self.indicators:
            return None
        
        if indicator_name not in self.indicators[interval]:
            return None
        
        # 如果请求运行时值，优先返回运行时值
        if use_runtime:
            runtime_value = self.runtime_indicators[interval].get(indicator_name)
            if runtime_value is not None:
                return runtime_value
        
        # 返回历史值
        indicator_deque = self.indicators[interval][indicator_name]
        
        if len(indicator_deque) == 0:
            return None
        
        try:
            return indicator_deque[index]
        except IndexError:
            return None
    
    def get_indicator_smart(
        self,
        interval: Interval,
        indicator_name: str,
        prefer_runtime: bool = True,
        fallback_to_history: bool = True,
        history_index: int = -1,
        wait_if_not_ready: bool = False,
        wait_timeout: Optional[float] = 0.1
    ) -> Optional[Any]:
        """
        智能获取指标值：优先运行时值，回退到历史值
        
        参数:
            interval: K线周期
            indicator_name: 指标名称
            prefer_runtime: 是否优先使用运行时值（正在聚合的K线对应的指标值）
            fallback_to_history: 如果运行时值不存在，是否回退到历史值
            history_index: 历史值索引（-1=最新，-2=上一个，-201=200个周期前）
                          注意：index是相对于interval参数的周期数，不是调用它的周期数
            wait_if_not_ready: 如果指标未初始化完成，是否等待（默认False，立即返回None）
            wait_timeout: 等待超时时间（秒），仅在 wait_if_not_ready=True 时有效
        
        返回:
            指标值，如果不存在或未初始化完成则返回None
        
        使用场景:
            # 场景1：需要实时值（运行时值优先）
            value = manager.get_indicator_smart(
                Interval.MINUTE_5, "custom_wma",
                prefer_runtime=True, fallback_to_history=True, history_index=-1
            )
            
            # 场景2：需要稳定值（只使用历史值）
            value = manager.get_indicator_smart(
                Interval.MINUTE_5, "custom_wma",
                prefer_runtime=False, fallback_to_history=True, history_index=-1
            )
            
            # 场景3：需要N个周期前的值
            value = manager.get_indicator_smart(
                Interval.MINUTE_5, "custom_wma",
                prefer_runtime=False, fallback_to_history=True, history_index=-201
            )
            
            # 场景4：如果指标未初始化完成，等待最多0.1秒
            value = manager.get_indicator_smart(
                Interval.MINUTE_5, "custom_wma",
                wait_if_not_ready=True, wait_timeout=0.1
            )
        """
        # 检查初始化状态
        if not self.is_initialized(interval):
            if wait_if_not_ready:
                # 等待初始化完成（最多wait_timeout秒）
                if not self.wait_for_initialization(interval, timeout=wait_timeout):
                    return None  # 超时或失败，返回None
            else:
                # 不等待，直接返回None
                return None
        
        # 1. 如果优先运行时值，先尝试获取
        if prefer_runtime:
            runtime_value = self.get_runtime_indicator(interval, indicator_name)
            if runtime_value is not None and not (isinstance(runtime_value, (int, float)) and np.isnan(runtime_value)):
                return runtime_value
        
        # 2. 如果运行时值不存在或不需要运行时值，获取历史值
        if fallback_to_history:
            # 尝试获取指定索引的历史值
            value = self.get_indicator(interval, indicator_name, index=history_index)
            
            # 调试：检查数据状态
            if value is None:
                # 检查deque是否存在且有数据
                if interval in self.indicators and indicator_name in self.indicators[interval]:
                    deque_len = len(self.indicators[interval][indicator_name])
                    self.write_log(
                        f"调试: {interval.value} - {indicator_name} 在索引 {history_index} 处返回None，"
                        f"deque长度={deque_len}"
                    )
                else:
                    self.write_log(
                        f"调试: {interval.value} - {indicator_name} 不存在或未注册"
                    )
            
            # 如果获取到的值是NaN或None，尝试回退到更早的有效值（最多回退50个周期）
            if value is None or (isinstance(value, (int, float)) and np.isnan(value)):
                # 尝试从更早的周期获取有效值
                found_valid = False
                for offset in range(1, 51):  # 最多回退50个周期（对于5分钟K线，50个周期是约4小时）
                    try:
                        earlier_index = history_index - offset
                        earlier_value = self.get_indicator(interval, indicator_name, index=earlier_index)
                        if earlier_value is not None and not (isinstance(earlier_value, (int, float)) and np.isnan(earlier_value)):
                            # 找到有效值，返回它
                            self.write_log(
                                f"警告: {interval.value} - {indicator_name} 在索引 {history_index} 处为{'NaN' if value is not None else 'None'}，"
                                f"回退 {offset} 个周期找到有效值 {earlier_value:.2f}"
                            )
                            return earlier_value
                    except (IndexError, TypeError):
                        # 索引超出范围，继续尝试下一个
                        continue
                
                # 如果所有尝试都失败，记录警告并返回None
                if value is not None:  # 如果是NaN而不是None，说明数据存在但无效
                    # 检查deque中是否有任何有效值
                    if interval in self.indicators and indicator_name in self.indicators[interval]:
                        deque = self.indicators[interval][indicator_name]
                        valid_count = sum(1 for v in deque if not (isinstance(v, (int, float)) and np.isnan(v)))
                        self.write_log(
                            f"错误: {interval.value} - {indicator_name} 在索引 {history_index} 处为NaN，"
                            f"且回退50个周期后仍未找到有效值。deque总长度={len(deque)}, 有效值数量={valid_count}"
                        )
                    else:
                        self.write_log(
                            f"错误: {interval.value} - {indicator_name} 在索引 {history_index} 处为NaN，"
                            f"且回退50个周期后仍未找到有效值。指标未注册或不存在"
                        )
                else:
                    self.write_log(
                        f"错误: {interval.value} - {indicator_name} 在索引 {history_index} 处为None，"
                        f"且回退50个周期后仍未找到有效值"
                    )
                return None
            
            return value
        
        return None
    
    def get_runtime_indicator(
        self,
        interval: Interval,
        indicator_name: str
    ) -> Optional[Any]:
        """
        获取运行时指标值（正在聚合的K线对应的指标值）
        
        参数:
            interval: K线周期
            indicator_name: 指标名称
        
        返回:
            运行时指标值，如果不存在则返回None
        """
        if interval not in self.runtime_indicators:
            return None
        
        return self.runtime_indicators[interval].get(indicator_name)
    
    def get_indicator_array(
        self,
        interval: Interval,
        indicator_name: str,
        length: Optional[int] = None
    ) -> Optional[np.ndarray]:
        """
        获取指标数组（用于需要多个历史值的计算）
        
        参数:
            interval: K线周期
            indicator_name: 指标名称
            length: 返回数组长度，如果为None则返回所有值
        
        返回:
            指标数组，如果不存在则返回None
        """
        if interval not in self.indicators:
            return None
        
        if indicator_name not in self.indicators[interval]:
            return None
        
        indicator_deque = self.indicators[interval][indicator_name]
        
        if len(indicator_deque) == 0:
            return None
        
        values = list(indicator_deque)
        
        if length is not None:
            values = values[-length:]
        
        return np.array(values)
    
    def _save_indicator_to_file(self, interval: Interval):
        """保存指标数据到文件"""
        if interval not in self.indicators:
            return
        
        try:
            if self.storage_format == "parquet":
                self._save_indicator_to_parquet(interval)
            else:
                self._save_indicator_to_pkl(interval)
        except Exception as e:
            self.write_log(f"保存指标数据失败: {e}")
    
    def _save_indicator_to_pkl(self, interval: Interval):
        """使用pkl格式保存指标数据"""
        filename = f"{interval.value}_indicators.pkl"
        filepath = self.storage_path / filename
        
        # 将deque转换为list以便序列化
        data_to_save = {}
        for indicator_name, indicator_deque in self.indicators[interval].items():
            data_to_save[indicator_name] = list(indicator_deque)
        
        # 保存到文件
        with open(filepath, 'wb') as f:
            pickle.dump(data_to_save, f)
        
        self.write_log(f"保存指标数据(PKL): {interval.value}, 文件: {filepath}")
    
    def _save_indicator_to_parquet(self, interval: Interval):
        """使用parquet格式保存指标数据"""
        if not POLARS_AVAILABLE:
            raise ImportError("polars未安装，无法使用parquet格式")
        
        filename = f"{interval.value}_indicators.parquet"
        filepath = self.storage_path / filename
        
        # 准备数据：将指标数据转换为DataFrame格式
        # 结构：datetime, indicator_name, value
        data_rows = []
        
        for indicator_name, indicator_deque in self.indicators[interval].items():
            values = list(indicator_deque)
            timestamps = list(self.indicator_timestamps[interval].get(indicator_name, deque()))
            
            # 如果时间戳数量不匹配，使用索引作为时间参考
            for idx, value in enumerate(values):
                if idx < len(timestamps):
                    dt = timestamps[idx]
                else:
                    # 如果没有时间戳，使用当前时间（不推荐，但保持兼容性）
                    dt = datetime.now()
                
                data_rows.append({
                    "datetime": dt.replace(tzinfo=None) if dt.tzinfo else dt,
                    "indicator_name": indicator_name,
                    "value": float(value) if not np.isnan(value) else None
                })
        
        if not data_rows:
            return
        
        # 创建DataFrame
        df = pl.DataFrame(data_rows)
        
        # 按datetime和indicator_name排序
        df = df.sort(["indicator_name", "datetime"])
        
        # 保存到parquet文件（使用zstd压缩，压缩率更高）
        df.write_parquet(filepath, compression="zstd")
        
        self.write_log(f"保存指标数据(Parquet): {interval.value}, 文件: {filepath}, 行数: {len(data_rows)}")
    
    def _load_indicator_from_file(self, interval: Interval) -> bool:
        """
        从文件加载指标数据
        
        返回:
            bool: 是否成功加载了数据
        """
        try:
            # 优先尝试加载parquet格式，如果不存在则尝试pkl格式
            parquet_file = self.storage_path / f"{interval.value}_indicators.parquet"
            pkl_file = self.storage_path / f"{interval.value}_indicators.pkl"
            
            if parquet_file.exists() and POLARS_AVAILABLE:
                return self._load_indicator_from_parquet(interval)
            elif pkl_file.exists():
                return self._load_indicator_from_pkl(interval)
            else:
                # 文件不存在，跳过加载
                return False
        except Exception as e:
            self.write_log(f"加载指标数据失败: {e}")
            return False
    
    def _load_indicator_from_pkl(self, interval: Interval) -> bool:
        """
        从pkl文件加载指标数据
        
        返回:
            bool: 是否成功加载了数据
        """
        filename = f"{interval.value}_indicators.pkl"
        filepath = self.storage_path / filename
        
        if not filepath.exists():
            return False
        
        # 从文件加载
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
        
        # 恢复deque
        if interval not in self.indicators:
            self.indicators[interval] = {}
        
        loaded_count = 0
        for indicator_name, values in data.items():
            if indicator_name in self.indicators[interval]:
                indicator_deque = self.indicators[interval][indicator_name]
                
                # 检查数据量是否超过当前maxlen
                data_count = len(values)
                current_maxlen = indicator_deque.maxlen if indicator_deque.maxlen else float('inf')
                
                # 如果数据量大于maxlen，需要调整deque的maxlen
                if data_count > current_maxlen:
                    # 创建新的deque，maxlen设为数据量（或更大，留一些余量）
                    new_maxlen = max(data_count, current_maxlen * 2) if current_maxlen != float('inf') else data_count
                    self.write_log(
                        f"警告: {interval.value} - {indicator_name} 从文件加载的数据量 ({data_count}) "
                        f"超过当前maxlen ({current_maxlen})，将调整为 {new_maxlen}"
                    )
                    
                    # 创建新的deque（保留现有数据）
                    old_values = list(indicator_deque)
                    
                    # 创建新的deque
                    self.indicators[interval][indicator_name] = deque(old_values, maxlen=new_maxlen)
                    indicator_deque = self.indicators[interval][indicator_name]
                
                # 清空现有数据并加载历史数据
                indicator_deque.clear()
                for val in values:
                    indicator_deque.append(val)
                loaded_count += 1
        
        if loaded_count > 0:
            self.write_log(f"加载指标数据(PKL): {interval.value}, 共 {loaded_count} 个指标")
            return True
        else:
            return False
    
    def _load_indicator_from_parquet(self, interval: Interval) -> bool:
        """
        从parquet文件加载指标数据
        
        返回:
            bool: 是否成功加载了数据
        """
        if not POLARS_AVAILABLE:
            raise ImportError("polars未安装，无法使用parquet格式")
        
        filename = f"{interval.value}_indicators.parquet"
        filepath = self.storage_path / filename
        
        if not filepath.exists():
            return False
        
        # 从parquet文件加载
        df = pl.read_parquet(filepath)
        
        if df.is_empty():
            return False
        
        # 恢复deque
        if interval not in self.indicators:
            self.indicators[interval] = {}
            self.indicator_timestamps[interval] = {}
        
        # 按indicator_name分组，恢复数据
        loaded_count = 0
        file_indicator_names = df["indicator_name"].unique().to_list()
        self.write_log(f"从文件读取到 {len(file_indicator_names)} 个指标: {file_indicator_names}")
        
        for indicator_name in file_indicator_names:
            if indicator_name in self.indicators[interval]:
                indicator_data = df.filter(pl.col("indicator_name") == indicator_name)
                # 按datetime排序
                indicator_data = indicator_data.sort("datetime")
                
                indicator_deque = self.indicators[interval][indicator_name]
                timestamp_deque = self.indicator_timestamps[interval].get(indicator_name, deque())
                
                # 统计有效数据数量
                valid_count = sum(1 for row in indicator_data.iter_rows(named=True) if row["value"] is not None)
                self.write_log(
                    f"加载指标 {indicator_name}: 总行数={len(indicator_data)}, 有效值={valid_count}, NaN值={len(indicator_data) - valid_count}"
                )
                
                # 检查数据量是否超过当前maxlen
                data_count = len(indicator_data)
                current_maxlen = indicator_deque.maxlen if indicator_deque.maxlen else float('inf')
                
                # 如果数据量大于maxlen，需要调整deque的maxlen
                if data_count > current_maxlen:
                    # 创建新的deque，maxlen设为数据量（或更大，留一些余量）
                    new_maxlen = max(data_count, current_maxlen * 2) if current_maxlen != float('inf') else data_count
                    self.write_log(
                        f"警告: {interval.value} - {indicator_name} 从文件加载的数据量 ({data_count}) "
                        f"超过当前maxlen ({current_maxlen})，将调整为 {new_maxlen}"
                    )
                    
                    # 创建新的deque（保留现有数据）
                    old_values = list(indicator_deque)
                    old_timestamps = list(timestamp_deque)
                    
                    # 创建新的deque
                    self.indicators[interval][indicator_name] = deque(old_values, maxlen=new_maxlen)
                    self.indicator_timestamps[interval][indicator_name] = deque(old_timestamps, maxlen=new_maxlen)
                    
                    indicator_deque = self.indicators[interval][indicator_name]
                    timestamp_deque = self.indicator_timestamps[interval][indicator_name]
                
                indicator_deque.clear()
                timestamp_deque.clear()
                
                for row in indicator_data.iter_rows(named=True):
                    value = row["value"]
                    dt = row["datetime"]
                    
                    if value is not None:
                        indicator_deque.append(value)
                    else:
                        indicator_deque.append(np.nan)
                    
                    timestamp_deque.append(dt)
                
                # 确保时间戳deque也被保存
                if indicator_name not in self.indicator_timestamps[interval]:
                    self.indicator_timestamps[interval][indicator_name] = timestamp_deque
                
                loaded_count += 1
            else:
                self.write_log(f"警告: 文件中的指标 {indicator_name} 未注册，跳过加载")
        
        if loaded_count > 0:
            self.write_log(f"加载指标数据(Parquet): {interval.value}, 共 {loaded_count} 个指标, 总行数: {len(df)}")
            # 验证加载的数据
            for indicator_name in file_indicator_names:
                if indicator_name in self.indicators[interval]:
                    deque = self.indicators[interval][indicator_name]
                    valid_count = sum(1 for v in deque if not (isinstance(v, (int, float)) and np.isnan(v)))
                    self.write_log(
                        f"验证: {indicator_name} 加载后 deque长度={len(deque)}, 有效值={valid_count}"
                    )
            return True
        else:
            self.write_log(f"警告: 从文件加载失败，没有找到已注册的指标")
            return False
    
    def export_to_alphalab_format(
        self,
        interval: Interval,
        output_path: Optional[str] = None
    ) -> Optional[pl.DataFrame]:
        """
        将指标数据导出为AlphaLab可用的格式
        
        AlphaLab期望的格式：
        - DataFrame包含列：datetime, vt_symbol, {indicator_name1}, {indicator_name2}, ...
        - 每个指标作为一列，列名为指标名称
        - 需要与K线数据合并使用
        
        参数:
            interval: K线周期
            output_path: 输出文件路径（可选），如果提供则保存为parquet文件
        
        返回:
            polars DataFrame，格式为：datetime, vt_symbol, {indicator_name1}, {indicator_name2}, ...
            如果polars不可用或数据为空，返回None
        """
        if not POLARS_AVAILABLE:
            self.write_log("警告: polars未安装，无法导出为AlphaLab格式")
            return None
        
        if interval not in self.indicators:
            self.write_log(f"警告: {interval.value} 周期无指标数据")
            return None
        
        # 准备数据：将指标数据转换为宽格式（每个指标一列）
        data_dict = {
            "datetime": [],
            "vt_symbol": []
        }
        
        # 收集所有指标的时间戳和值
        indicator_data = {}
        max_length = 0
        
        for indicator_name, indicator_deque in self.indicators[interval].items():
            values = list(indicator_deque)
            timestamps = list(self.indicator_timestamps[interval].get(indicator_name, deque()))
            
            if len(values) > max_length:
                max_length = len(values)
            
            # 存储指标数据
            indicator_data[indicator_name] = {
                "values": values,
                "timestamps": timestamps
            }
        
        if max_length == 0:
            self.write_log(f"警告: {interval.value} 周期无指标数据")
            return None
        
        # 构建DataFrame：按时间对齐所有指标
        # 使用第一个指标的时间戳作为基准
        first_indicator = list(indicator_data.keys())[0]
        base_timestamps = indicator_data[first_indicator]["timestamps"]
        
        # 如果没有时间戳，无法导出
        if not base_timestamps:
            self.write_log(f"警告: {interval.value} 周期指标无时间戳信息，无法导出")
            return None
        
        # 为每个指标创建列
        for indicator_name in indicator_data.keys():
            data_dict[indicator_name] = []
        
        # 按时间对齐数据
        for idx, dt in enumerate(base_timestamps):
            data_dict["datetime"].append(dt)
            data_dict["vt_symbol"].append(self.vt_symbol)
            
            # 为每个指标填充值
            for indicator_name, ind_data in indicator_data.items():
                values = ind_data["values"]
                timestamps = ind_data["timestamps"]
                
                # 找到对应时间戳的值
                if idx < len(values) and idx < len(timestamps) and timestamps[idx] == dt:
                    value = values[idx]
                    data_dict[indicator_name].append(float(value) if not np.isnan(value) else None)
                else:
                    # 如果时间戳不匹配，尝试查找最接近的值
                    # 简化处理：如果索引超出范围，使用NaN
                    if idx < len(values):
                        value = values[idx]
                        data_dict[indicator_name].append(float(value) if not np.isnan(value) else None)
                    else:
                        data_dict[indicator_name].append(None)
        
        # 创建DataFrame
        df = pl.DataFrame(data_dict)
        
        # 按datetime排序
        df = df.sort("datetime")
        
        # 如果提供了输出路径，保存文件
        if output_path:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            df.write_parquet(output_file, compression="zstd")
            self.write_log(f"导出指标数据到AlphaLab格式: {output_file}, 行数: {len(df)}")
        
        return df
    
    def export_all_indicators_to_alphalab_format(
        self,
        output_dir: Optional[str] = None
    ) -> Dict[Interval, Optional[pl.DataFrame]]:
        """
        导出所有周期的指标数据为AlphaLab格式
        
        参数:
            output_dir: 输出目录（可选），如果提供则保存为parquet文件
        
        返回:
            字典，键为Interval，值为DataFrame
        """
        results = {}
        
        for interval in self.indicators.keys():
            if output_dir:
                output_path = Path(output_dir) / f"{interval.value}_indicators.parquet"
                df = self.export_to_alphalab_format(interval, str(output_path))
            else:
                df = self.export_to_alphalab_format(interval)
            
            results[interval] = df
        
        return results
    
    def write_log(self, msg: str):
        """写入日志（可以重写为实际的日志方法）"""
        print(f"[IndicatorManager] {self.vt_symbol} - {msg}")


# ========== 使用示例 ==========

def example_custom_indicator(bars: List[BarData]) -> np.ndarray:
    """
    示例：自定义指标计算函数
    
    计算一个简单的自定义指标：收盘价的加权移动平均
    """
    if len(bars) < 10:
        return np.array([np.nan] * len(bars))
    
    closes = np.array([bar.close_price for bar in bars])
    
    # 简单的加权移动平均（权重递减）
    weights = np.arange(1, len(closes) + 1)
    wma = np.convolve(closes, weights / weights.sum(), mode='valid')
    
    # 补齐前面的NaN
    result = np.full(len(bars), np.nan)
    result[-len(wma):] = wma
    
    return result


def example_usage():
    """使用示例"""
    # 创建指标管理器
    manager = IndicatorManager(
        vt_symbol="MHImain.HKFE",
        storage_path=None,  # 使用默认路径
        use_database=True
    )
    
    # 注册指标
    manager.register_indicator(
        interval=Interval.MINUTE,
        indicator_name="custom_wma",
        calculator=example_custom_indicator,
        max_history=10000
    )
    
    manager.register_indicator(
        interval=Interval.MINUTE_5,
        indicator_name="custom_wma",
        calculator=example_custom_indicator,
        max_history=10000
    )
    
    # 初始化指标（加载历史数据并计算）
    database = get_database()
    manager.initialize_indicators(Interval.MINUTE, days=365, database=database)
    manager.initialize_indicators(Interval.MINUTE_5, days=365, database=database)
    
    # 在策略中使用：
    # 1. 在on_bar中更新指标
    # def on_bar(self, bar: BarData):
    #     manager.update_indicator(Interval.MINUTE, bar)
    #     # 获取最新指标值
    #     wma_value = manager.get_indicator(Interval.MINUTE, "custom_wma", -1)
    #     # 获取历史指标数组
    #     wma_array = manager.get_indicator_array(Interval.MINUTE, "custom_wma", length=20)
    
    # 2. 在on_tick中使用（需要先聚合为1分钟K线）
    # def on_tick(self, tick: TickData):
    #     # 使用BarGenerator聚合tick为1分钟K线
    #     # 当1分钟K线完成时，调用manager.update_indicator()


if __name__ == "__main__":
    example_usage()

