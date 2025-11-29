import traceback
from threading import Thread
from queue import Queue, Empty
from copy import copy
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from vnpy.event import Event, EventEngine
from vnpy.trader.engine import BaseEngine, MainEngine
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import (
    SubscribeRequest,
    TickData,
    BarData,
    ContractData
)
from vnpy.trader.event import EVENT_TICK, EVENT_CONTRACT, EVENT_TIMER
from vnpy.trader.utility import load_json, save_json, BarGenerator
from vnpy.trader.hkfe_bar_generator import create_bar_generator
from vnpy.trader.database import BaseDatabase, get_database, DB_TZ
from vnpy_spreadtrading.base import EVENT_SPREAD_DATA, SpreadItem
from vnpy.trader.period_utils import (
    get_period_start,
    get_hkfe_4hour_period,
    PeriodOpenPriceHelper
)


APP_NAME = "DataRecorder"

EVENT_RECORDER_LOG = "eRecorderLog"
EVENT_RECORDER_UPDATE = "eRecorderUpdate"


class RecorderEngine(BaseEngine):
    """
    For running data recorder.
    """

    setting_filename: str = "data_recorder_setting.json"

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        """"""
        super().__init__(main_engine, event_engine, APP_NAME)

        self.queue: Queue = Queue()
        self.thread: Thread = Thread(target=self.run)
        self.active: bool = False

        self.tick_recordings: dict[str, dict] = {}
        self.bar_recordings: dict[str, dict] = {}
        # 1分钟BarGenerator（用于生成1分钟K线，作为合成大周期K线的基础）
        self.minute_bar_generators: dict[str, BarGenerator] = {}
        # 开盘价辅助类（用于获取大周期K线的开盘价）
        self.open_price_helpers: dict[str, PeriodOpenPriceHelper] = {}
        # 1分钟K线缓存（用于合成大周期K线）：{vt_symbol: list[BarData]}
        # 只保留最近一段时间的1分钟K线，用于在新周期开始时合成上一个周期
        self.minute_bars_cache: dict[str, list[BarData]] = defaultdict(list)
        # 上一个周期记录：{vt_symbol: {interval: datetime}}，用于检测周期切换
        self.last_periods: dict[str, dict[Interval, datetime]] = defaultdict(dict)
        
        # 以下变量已废弃，保留以避免破坏向后兼容性（但不再使用）
        # 多周期BarGenerator：{vt_symbol: {interval: BarGenerator}} - 已废弃，改用手动合成
        self.bar_generators: dict[str, dict[Interval, BarGenerator]] = {}
        # 当前正在生成的大周期K线：{vt_symbol: {interval: BarData}} - 已废弃，改用手动合成
        self.current_bars: dict[str, dict[Interval, BarData]] = defaultdict(dict)

        self.timer_count: int = 0
        self.timer_interval: int = 10

        self.ticks: dict[str, list[TickData]] = defaultdict(list)
        # 多周期K线存储：{vt_symbol: {interval: list[BarData]}}
        self.bars: dict[str, dict[Interval, list[BarData]]] = defaultdict(lambda: defaultdict(list))
        # 1分钟K线缓存（用于合成大周期K线）：{vt_symbol: list[BarData]}
        # 只缓存最近一段时间的1分钟K线，用于在新周期开始时合成上一个周期
        self.minute_bars_cache: dict[str, list[BarData]] = defaultdict(list)
        # 上一个周期记录：{vt_symbol: {interval: datetime}}，用于检测周期切换
        self.last_periods: dict[str, dict[Interval, datetime]] = defaultdict(dict)

        self.filter_dt: datetime = datetime.now(DB_TZ)      # Tick数据过滤的时间戳
        self.filter_window: int = 60                        # Tick数据过滤的时间窗口，默认60秒
        self.filter_delta: timedelta                        # Tick数据过滤的时间偏差对象

        self.database: BaseDatabase = get_database()
        
        # 用于记录最后一次更新的信息（用于UI反馈）
        self._last_update_info: dict = {}

        self.load_setting()
        self.register_event()
        self.start()
        self.put_event()

    def load_setting(self) -> None:
        """"""
        setting: dict = load_json(self.setting_filename)
        self.tick_recordings = setting.get("tick", {})
        self.bar_recordings = setting.get("bar", {})

        self.filter_window = setting.get("filter_window", 60)
        self.filter_delta = timedelta(seconds=self.filter_window)
        
        # 确保bar_recordings中的intervals格式正确（应该是字符串列表）
        for vt_symbol, config in self.bar_recordings.items():
            if "intervals" in config:
                intervals = config["intervals"]
                # 确保intervals是列表格式
                if isinstance(intervals, str):
                    config["intervals"] = [intervals]
                elif not isinstance(intervals, list):
                    config["intervals"] = [intervals] if intervals else [Interval.MINUTE.value]
                elif len(intervals) == 0:
                    config["intervals"] = [Interval.MINUTE.value]
            else:
                # 如果没有intervals字段，添加默认值（兼容旧配置）
                config["intervals"] = [Interval.MINUTE.value]
        
        # 初始化开盘价辅助类
        for vt_symbol in self.bar_recordings.keys():
            if vt_symbol not in self.open_price_helpers:
                self.open_price_helpers[vt_symbol] = PeriodOpenPriceHelper(self.database)

    def save_setting(self) -> None:
        """"""
        setting: dict = {
            "tick": self.tick_recordings,
            "bar": self.bar_recordings,
            "filter_window": self.filter_window
        }
        save_json(self.setting_filename, setting)

    def run(self) -> None:
        """"""
        while self.active:
            try:
                task: tuple[str, list] = self.queue.get(timeout=1)
                task_type, data = task

                if task_type == "tick":
                    result = self.database.save_tick_data(data, stream=True)
                    if result:
                        self.write_log(f"[DataRecorder] 成功保存 {len(data)} 条Tick数据")
                    else:
                        self.write_log(f"[DataRecorder] ⚠️ 保存Tick数据失败: {len(data)} 条")
                elif task_type == "bar":
                    # 统计各周期的数据量
                    interval_counts = {}
                    for bar in data:
                        interval = bar.interval
                        if interval:
                            interval_counts[interval] = interval_counts.get(interval, 0) + 1
                    
                    result = self.database.save_bar_data(data, stream=True)
                    if result:
                        interval_info = ", ".join([f"{interval.value}:{count}" for interval, count in interval_counts.items()])
                        self.write_log(f"[DataRecorder] 成功保存 {len(data)} 条K线数据 ({interval_info})")
                    else:
                        self.write_log(f"[DataRecorder] ⚠️ 保存K线数据失败: {len(data)} 条")

            except Empty:
                continue

            except Exception as e:
                # 不要因为一次异常就停止所有录制，记录错误并继续
                error_msg = str(e).replace("{", "{{").replace("}", "}}")
                self.write_log(f"[DataRecorder] ❌ 保存数据时发生异常: {error_msg}")
                import traceback
                traceback_info = traceback.format_exc().replace("{", "{{").replace("}", "}}")
                self.write_log(f"[DataRecorder] 异常详情:\n{traceback_info}")
                # 继续处理下一个任务，而不是停止整个录制
                continue

    def close(self) -> None:
        """"""
        self.active = False

        if self.thread.is_alive():
            self.thread.join()

    def start(self) -> None:
        """"""
        self.active = True
        self.thread.start()
        self.write_log(f"[DataRecorder] ✅ 数据录制已启动 (保存间隔: {self.timer_interval}秒)")
        self.write_log(f"[DataRecorder] 📊 当前录制任务: K线={len(self.bar_recordings)}, Tick={len(self.tick_recordings)}")
        if self.bar_recordings:
            bar_symbols = ", ".join(self.bar_recordings.keys())
            self.write_log(f"[DataRecorder] 📈 K线录制合约: {bar_symbols}")
        if self.tick_recordings:
            tick_symbols = ", ".join(self.tick_recordings.keys())
            self.write_log(f"[DataRecorder] 📊 Tick录制合约: {tick_symbols}")

    def add_bar_recording(
        self, 
        vt_symbol: str, 
        intervals: Optional[list[Interval]] = None
    ) -> None:
        """
        添加K线录制任务
        
        Args:
            vt_symbol: 合约代码
            intervals: 要录制的周期列表，如果为None则默认录制1分钟K线
        """
        if intervals is None:
            intervals = [Interval.MINUTE]
        
        if vt_symbol in self.bar_recordings:
            # 更新已存在的录制任务，添加新周期
            existing_intervals = self.bar_recordings[vt_symbol].get("intervals", [Interval.MINUTE.value])
            # 兼容旧格式：可能是字符串列表，也可能是Interval枚举列表
            if existing_intervals and isinstance(existing_intervals[0], str):
                # 字符串格式：转换为Interval枚举
                existing_intervals = [Interval(i) for i in existing_intervals]
            elif existing_intervals and not isinstance(existing_intervals[0], Interval):
                # 可能是空列表或其他格式，使用默认值
                existing_intervals = [Interval.MINUTE]
            elif not existing_intervals:
                # 空列表，使用默认值
                existing_intervals = [Interval.MINUTE]
            
            # 记录原有周期和新选择的周期
            old_intervals_set = set(existing_intervals)
            new_intervals_set = set(intervals)
            added_intervals = new_intervals_set - old_intervals_set
            removed_intervals = old_intervals_set - new_intervals_set
            
            # 合并周期（取并集）
            new_intervals = list(set(existing_intervals) | new_intervals_set)
            self.bar_recordings[vt_symbol]["intervals"] = [i.value for i in new_intervals]
            intervals = new_intervals
            
            # 记录更新信息（用于日志和反馈）
            self._last_update_info = {
                "is_update": True,
                "vt_symbol": vt_symbol,
                "old_intervals": list(old_intervals_set),
                "new_intervals": intervals,
                "added_intervals": list(added_intervals),
                "removed_intervals": list(removed_intervals)
            }
        else:
            # 新增合约录制
            self._last_update_info = {
                "is_update": False,
                "vt_symbol": vt_symbol,
                "new_intervals": intervals
            }
            
            if Exchange.LOCAL.value not in vt_symbol:
                contract: ContractData | None = self.main_engine.get_contract(vt_symbol)
                if not contract:
                    self.write_log(f"找不到合约：{vt_symbol}")
                    return

                self.bar_recordings[vt_symbol] = {
                    "symbol": contract.symbol,
                    "exchange": contract.exchange.value,
                    "gateway_name": contract.gateway_name,
                    "intervals": [i.value for i in intervals]
                }

                self.subscribe(contract)
            else:
                self.bar_recordings[vt_symbol] = {
                    "intervals": [i.value for i in intervals]
                }
        
        # 初始化开盘价辅助类
        if vt_symbol not in self.open_price_helpers:
            self.open_price_helpers[vt_symbol] = PeriodOpenPriceHelper(self.database)
        
        # 创建BarGenerator
        self._init_bar_generators(vt_symbol, intervals)

        self.save_setting()
        self.put_event()

        # 根据是新增还是更新，显示不同的日志信息
        interval_str = ", ".join([i.value for i in intervals])
        if hasattr(self, '_last_update_info') and self._last_update_info.get("is_update"):
            info = self._last_update_info
            old_str = ", ".join([i.value for i in info["old_intervals"]])
            if info["added_intervals"] or info["removed_intervals"]:
                # 有周期变化
                changes = []
                if info["added_intervals"]:
                    added_str = ", ".join([i.value for i in info["added_intervals"]])
                    changes.append(f"新增: {added_str}")
                if info["removed_intervals"]:
                    removed_str = ", ".join([i.value for i in info["removed_intervals"]])
                    changes.append(f"移除: {removed_str}")
                change_str = " | ".join(changes)
                self.write_log(f"更新K线记录成功：{vt_symbol} (原周期: {old_str} → 新周期: {interval_str} | {change_str})")
            else:
                # 没有变化，周期已包含
                self.write_log(f"更新K线记录：{vt_symbol} (周期: {interval_str}，无变化)")
        else:
            # 新增
            self.write_log(f"添加K线记录成功：{vt_symbol} (周期: {interval_str})")

    def add_tick_recording(self, vt_symbol: str) -> None:
        """"""
        if vt_symbol in self.tick_recordings:
            self.write_log(f"已在Tick记录列表中：{vt_symbol}")
            return

        # For normal contract
        if Exchange.LOCAL.value not in vt_symbol:
            contract: ContractData | None = self.main_engine.get_contract(vt_symbol)
            if not contract:
                self.write_log(f"找不到合约：{vt_symbol}")
                return

            self.tick_recordings[vt_symbol] = {
                "symbol": contract.symbol,
                "exchange": contract.exchange.value,
                "gateway_name": contract.gateway_name
            }

            self.subscribe(contract)
        # No need to subscribe for spread data
        else:
            self.tick_recordings[vt_symbol] = {}

        self.save_setting()
        self.put_event()

        self.write_log(f"添加Tick记录成功：{vt_symbol}")

    def remove_bar_recording(self, vt_symbol: str) -> None:
        """"""
        if vt_symbol not in self.bar_recordings:
            self.write_log(f"不在K线记录列表中：{vt_symbol}")
            return

        self.bar_recordings.pop(vt_symbol)
        self.save_setting()
        self.put_event()

        self.write_log(f"移除K线记录成功：{vt_symbol}")

    def remove_tick_recording(self, vt_symbol: str) -> None:
        """"""
        if vt_symbol not in self.tick_recordings:
            self.write_log(f"不在Tick记录列表中：{vt_symbol}")
            return

        self.tick_recordings.pop(vt_symbol)
        self.save_setting()
        self.put_event()

        self.write_log(f"移除Tick记录成功：{vt_symbol}")

    def register_event(self) -> None:
        """"""
        self.event_engine.register(EVENT_TIMER, self.process_timer_event)
        self.event_engine.register(EVENT_TICK, self.process_tick_event)
        self.event_engine.register(EVENT_CONTRACT, self.process_contract_event)
        self.event_engine.register(EVENT_SPREAD_DATA, self.process_spread_event)

    def update_tick(self, tick: TickData) -> None:
        """"""
        # 过滤偏离本地时间戳过大的Tick数据
        tick_delta: timedelta = abs(tick.datetime - self.filter_dt)
        if abs(tick_delta) >= self.filter_delta:
            # 记录被过滤的tick（每100个记录一次，避免日志过多）
            if not hasattr(self, '_filtered_tick_count'):
                self._filtered_tick_count = {}
            self._filtered_tick_count[tick.vt_symbol] = self._filtered_tick_count.get(tick.vt_symbol, 0) + 1
            if self._filtered_tick_count[tick.vt_symbol] % 100 == 0:
                self.write_log(f"[DataRecorder] ⚠️ Tick数据被过滤: {tick.vt_symbol} (时间偏差: {abs(tick_delta).total_seconds():.1f}秒, 已过滤{self._filtered_tick_count[tick.vt_symbol]}条)")
            return

        # 记录tick接收情况（每个合约每收到100个tick记录一次）
        if not hasattr(self, '_tick_count'):
            self._tick_count = {}
        self._tick_count[tick.vt_symbol] = self._tick_count.get(tick.vt_symbol, 0) + 1
        
        if tick.vt_symbol in self.tick_recordings or tick.vt_symbol in self.bar_recordings:
            if self._tick_count[tick.vt_symbol] % 100 == 0:
                self.write_log(f"[DataRecorder] 📥 收到Tick数据: {tick.vt_symbol} (已收到{self._tick_count[tick.vt_symbol]}条)")

        if tick.vt_symbol in self.tick_recordings:
            self.record_tick(copy(tick))

        if tick.vt_symbol in self.bar_recordings:
            # 获取要录制的周期列表
            intervals = self._get_recording_intervals(tick.vt_symbol)
            
            # 首先更新1分钟K线生成器（作为基准）
            minute_bg = self._get_minute_bar_generator(tick.vt_symbol)
            minute_bg.update_tick(copy(tick))
            
            # 大周期K线将在新周期开始时从数据库手动合成（在on_minute_bar中处理）

    def process_timer_event(self, event: Event) -> None:
        """"""
        self.filter_dt = datetime.now(DB_TZ)

        self.timer_count += 1
        if self.timer_count < self.timer_interval:
            return
        self.timer_count = 0

        # 统计待保存的数据量
        total_bars = sum(len(bars) for interval_bars in self.bars.values() for bars in interval_bars.values())
        total_ticks = sum(len(ticks) for ticks in self.ticks.values())
        
        # 添加调试日志（每10次保存记录一次，避免日志过多）
        if not hasattr(self, '_save_count'):
            self._save_count = 0
        self._save_count += 1
        
        if self._save_count % 10 == 0:  # 每100秒记录一次（10次 * 10秒）
            if total_bars == 0 and total_ticks == 0:
                self.write_log(f"[DataRecorder] ⏰ 定时保存检查：无数据需要保存 (bars: 0, ticks: 0)")
            else:
                self.write_log(f"[DataRecorder] ⏰ 定时保存检查：准备保存 (bars: {total_bars}, ticks: {total_ticks})")

        # 保存所有周期的K线数据
        for vt_symbol, interval_bars in self.bars.items():
            for interval, bars in interval_bars.items():
                if bars:
                    # 为每个K线设置正确的interval
                    for bar in bars:
                        bar.interval = interval
                    self.queue.put(("bar", bars))
        self.bars.clear()

        for ticks in self.ticks.values():
            if ticks:  # 只有当ticks不为空时才放入队列
                self.queue.put(("tick", ticks))
        self.ticks.clear()

    def process_tick_event(self, event: Event) -> None:
        """"""
        tick: TickData = event.data
        self.update_tick(tick)

    def process_contract_event(self, event: Event) -> None:
        """"""
        contract: ContractData = event.data
        vt_symbol: str = contract.vt_symbol

        if (vt_symbol in self.tick_recordings or vt_symbol in self.bar_recordings):
            self.subscribe(contract)

    def process_spread_event(self, event: Event) -> None:
        """"""
        spread_item: SpreadItem = event.data
        tick: TickData = TickData(
            symbol=spread_item.name,
            exchange=Exchange.LOCAL,
            datetime=spread_item.datetime,
            name=spread_item.name,
            last_price=(spread_item.bid_price + spread_item.ask_price) / 2,
            bid_price_1=spread_item.bid_price,
            ask_price_1=spread_item.ask_price,
            bid_volume_1=spread_item.bid_volume,
            ask_volume_1=spread_item.ask_volume,
            localtime=spread_item.datetime,
            gateway_name="SPREAD"
        )

        # Filter not inited spread data
        if tick.datetime:
            self.update_tick(tick)

    def write_log(self, msg: str) -> None:
        """"""
        event: Event = Event(
            EVENT_RECORDER_LOG,
            msg
        )
        self.event_engine.put(event)

    def put_event(self) -> None:
        """"""
        tick_symbols: list[str] = list(self.tick_recordings.keys())
        tick_symbols.sort()

        bar_symbols: list[str] = list(self.bar_recordings.keys())
        bar_symbols.sort()

        data: dict = {
            "tick": tick_symbols,
            "bar": bar_symbols
        }

        event: Event = Event(
            EVENT_RECORDER_UPDATE,
            data
        )
        self.event_engine.put(event)

    def record_tick(self, tick: TickData) -> None:
        """"""
        self.ticks[tick.vt_symbol].append(tick)

    def record_bar(self, bar: BarData, interval: Optional[Interval] = None) -> None:
        """
        记录K线数据
        
        Args:
            bar: K线数据
            interval: K线周期（如果bar.interval已设置则不需要）
        """
        if interval is None:
            interval = bar.interval
        self.bars[bar.vt_symbol][interval].append(bar)
        
        # 记录K线收集情况（每个合约每个周期每收集10根K线记录一次）
        if not hasattr(self, '_bar_count'):
            self._bar_count = {}
        key = f"{bar.vt_symbol}:{interval.value}"
        self._bar_count[key] = self._bar_count.get(key, 0) + 1
        if self._bar_count[key] % 10 == 0:
            self.write_log(f"[DataRecorder] 📈 已收集K线: {bar.vt_symbol} {interval.value} (已收集{self._bar_count[key]}根, 缓存中{len(self.bars[bar.vt_symbol][interval])}根)")
    
    def _get_recording_intervals(self, vt_symbol: str) -> list[Interval]:
        """获取要录制的周期列表"""
        if vt_symbol not in self.bar_recordings:
            return []
        
        intervals_str = self.bar_recordings[vt_symbol].get("intervals", [Interval.MINUTE.value])
        if isinstance(intervals_str, str):
            intervals_str = [intervals_str]
        return [Interval(i) for i in intervals_str]
    
    def _aggregate_period_bar(
        self,
        vt_symbol: str,
        interval: Interval,
        period_start: datetime
    ) -> Optional[BarData]:
        """
        从数据库或缓存中聚合指定周期的大周期K线
        
        在新周期开始时，从数据库或缓存加载上一个周期的1分钟K线，
        然后使用与DataManager相同的逻辑合成大周期K线。
        
        Args:
            vt_symbol: 合约代码
            interval: 大周期（MINUTE_5, HOUR, HOUR_4）
            period_start: 要合成的周期的起始时间
            
        Returns:
            合成的大周期K线，如果无法合成则返回None
        """
        from vnpy.trader.utility import extract_vt_symbol
        
        symbol, exchange = extract_vt_symbol(vt_symbol)
        
        # 计算周期的结束时间
        if interval == Interval.MINUTE_5:
            period_end = period_start + timedelta(minutes=5)
        elif interval == Interval.HOUR:
            period_end = period_start + timedelta(hours=1)
        elif interval == Interval.HOUR_4:
            period_end = period_start + timedelta(hours=4)
        else:
            return None
        
        # 从数据库加载该周期内的1分钟K线
        # 对于4小时周期，需要更大的查询范围（可能跨越多个时段）
        if interval == Interval.HOUR_4:
            query_start = period_start - timedelta(hours=1)
            query_end = period_start + timedelta(hours=5)
        else:
            query_start = period_start - timedelta(minutes=5)
            query_end = period_end + timedelta(minutes=5)
        
        minute_bars = self.database.load_bar_data(
            symbol, exchange, Interval.MINUTE,
            query_start,
            query_end
        )
        
        # 筛选出属于该周期的1分钟K线
        period_minute_bars = []
        for bar in minute_bars:
            bar_dt = bar.datetime.replace(tzinfo=DB_TZ) if not bar.datetime.tzinfo else bar.datetime
            # 对于4小时周期，使用get_hkfe_4hour_period以与DataManager保持一致
            if interval == Interval.HOUR_4 and exchange == Exchange.HKFE:
                bar_period_start, _ = get_hkfe_4hour_period(bar_dt)
            else:
                bar_period_start = get_period_start(bar_dt, interval, exchange)
            
            if bar_period_start == period_start:
                period_minute_bars.append(bar)
        
        # 如果数据库中没有数据，尝试从缓存中获取
        if not period_minute_bars and vt_symbol in self.minute_bars_cache:
            for bar in self.minute_bars_cache[vt_symbol]:
                bar_dt = bar.datetime.replace(tzinfo=DB_TZ) if not bar.datetime.tzinfo else bar.datetime
                # 使用相同的周期判断逻辑
                if interval == Interval.HOUR_4 and exchange == Exchange.HKFE:
                    bar_period_start, _ = get_hkfe_4hour_period(bar_dt)
                else:
                    bar_period_start = get_period_start(bar_dt, interval, exchange)
                
                if bar_period_start == period_start:
                    period_minute_bars.append(bar)
        
        if not period_minute_bars:
            self.write_log(
                f"[DataRecorder] ⚠️ 无法合成 {vt_symbol} {interval.value}K线 "
                f"({period_start.strftime('%Y-%m-%d %H:%M:%S')})，未找到1分钟K线数据"
            )
            return None
        
        # 确保bars按时间排序
        period_minute_bars.sort(key=lambda x: x.datetime)
        
        # 使用与DataManager相同的逻辑合成大周期K线
        # 使用第一根1分钟K线的开盘价
        first_bar = period_minute_bars[0]
        last_bar = period_minute_bars[-1]
        
        open_price = first_bar.open_price
        close_price = last_bar.close_price
        high_price = max(bar.high_price for bar in period_minute_bars)
        low_price = min(bar.low_price for bar in period_minute_bars)
        volume = sum(bar.volume for bar in period_minute_bars)
        turnover = sum(bar.turnover for bar in period_minute_bars)
        open_interest = last_bar.open_interest if last_bar.open_interest else 0
        
        # 创建大周期K线
        period_bar = BarData(
            symbol=symbol,
            exchange=exchange,
            datetime=period_start,
            interval=interval,
            open_price=open_price,
            high_price=high_price,
            low_price=low_price,
            close_price=close_price,
            volume=volume,
            turnover=turnover,
            open_interest=open_interest,
            gateway_name="DataRecorder"
        )
        
        self.write_log(
            f"[DataRecorder] ✓ 合成 {vt_symbol} {interval.value}K线 "
            f"({period_start.strftime('%Y-%m-%d %H:%M:%S')}): "
            f"开={open_price:.0f}, 收={close_price:.0f}, "
            f"使用{len(period_minute_bars)}根1分钟K线"
        )
        
        return period_bar
    
    def _check_and_aggregate_previous_period(
        self,
        vt_symbol: str,
        current_minute_bar: BarData
    ) -> None:
        """
        检查是否是新周期的开始，如果是，则合成上一个周期的大周期K线
        
        Args:
            vt_symbol: 合约代码
            current_minute_bar: 当前的1分钟K线
        """
        from vnpy.trader.utility import extract_vt_symbol
        
        _, exchange = extract_vt_symbol(vt_symbol)
        intervals = self._get_recording_intervals(vt_symbol)
        
        for interval in intervals:
            if interval == Interval.MINUTE:
                continue
            
            # 获取当前1分钟K线所属的大周期
            # 对于4小时周期，使用get_hkfe_4hour_period以与DataManager保持一致
            if interval == Interval.HOUR_4 and exchange == Exchange.HKFE:
                current_period, _ = get_hkfe_4hour_period(current_minute_bar.datetime)
            else:
                current_period = get_period_start(
                    current_minute_bar.datetime,
                    interval,
                    exchange
                )
            
            if not current_period:
                continue
            
            # 检查是否是新周期的开始
            last_period = self.last_periods[vt_symbol].get(interval)
            
            if last_period is None:
                # 第一次，记录当前周期
                self.last_periods[vt_symbol][interval] = current_period
                continue
            
            if current_period != last_period:
                # 新周期开始，合成上一个周期的大周期K线
                self.write_log(
                    f"[DataRecorder] 检测到 {vt_symbol} {interval.value} 周期切换: "
                    f"{last_period.strftime('%Y-%m-%d %H:%M:%S')} -> "
                    f"{current_period.strftime('%Y-%m-%d %H:%M:%S')}"
                )
                
                # 合成上一个周期的大周期K线
                previous_period_bar = self._aggregate_period_bar(
                    vt_symbol,
                    interval,
                    last_period
                )
                
                if previous_period_bar:
                    # 记录合成的大周期K线
                    self.record_bar(previous_period_bar, interval)
                
                # 更新记录的周期
                self.last_periods[vt_symbol][interval] = current_period
    
    def _get_minute_bar_generator(self, vt_symbol: str) -> BarGenerator:
        """获取1分钟K线生成器"""
        if vt_symbol not in self.minute_bar_generators:
            from vnpy.trader.utility import extract_vt_symbol
            
            symbol, exchange = extract_vt_symbol(vt_symbol)
            
            # 创建1分钟K线生成器回调
            def on_minute_bar(bar: BarData) -> None:
                bar.interval = Interval.MINUTE
                
                # 缓存1分钟K线用于开盘价获取和后续合成
                if vt_symbol in self.open_price_helpers:
                    self.open_price_helpers[vt_symbol].cache_minute_bar(bar)
                
                # 缓存1分钟K线到本地缓存（用于合成大周期K线）
                # 只保留最近1小时的数据，避免内存占用过大
                self.minute_bars_cache[vt_symbol].append(bar)
                cache_size_limit = 60  # 保留最近60根1分钟K线（约1小时）
                if len(self.minute_bars_cache[vt_symbol]) > cache_size_limit:
                    self.minute_bars_cache[vt_symbol].pop(0)
                
                # 检查是否是新周期的开始，如果是则合成上一个周期
                self._check_and_aggregate_previous_period(vt_symbol, bar)
                
                # 记录1分钟K线
                self.record_bar(bar, Interval.MINUTE)
            
            # 使用工厂函数创建BarGenerator，对于HKFE交易所会自动选择HKFEBarGenerator
            # 虽然1分钟K线生成不需要特殊的HKFE逻辑，但使用工厂函数保持一致性更好
            bg = create_bar_generator(
                on_minute_bar,
                window=0,
                on_window_bar=None,
                interval=Interval.MINUTE,
                exchange=exchange,
                symbol=symbol
            )
            self.minute_bar_generators[vt_symbol] = bg
        
        return self.minute_bar_generators[vt_symbol]
    
    def _init_bar_generators(self, vt_symbol: str, intervals: list[Interval]) -> None:
        """初始化BarGenerator"""
        # 只初始化1分钟生成器，大周期K线将在新周期开始时从数据库手动合成
        self._get_minute_bar_generator(vt_symbol)
    
    def _correct_bar_open_price(
        self, 
        vt_symbol: str, 
        bar: BarData, 
        interval: Interval
    ) -> None:
        """
        修正大周期K线的开盘价（使用该周期第一根分钟K线的开盘价）
        
        Args:
            vt_symbol: 合约代码
            bar: K线数据
            interval: K线周期
        """
        if interval == Interval.MINUTE:
            return
        
        if vt_symbol not in self.open_price_helpers:
            return
        
        helper = self.open_price_helpers[vt_symbol]
        minute_bg = self.minute_bar_generators.get(vt_symbol)
        
        # 获取周期开始时间
        period_start = get_period_start(bar.datetime, interval, bar.exchange)
        if not period_start:
            return
        
        # 获取正确的开盘价
        # 注意：这里tick可能为None，因为是在1分钟K线回调中调用
        open_price = helper.get_period_open_price(
            period_start,
            interval,
            vt_symbol,
            tick=None,
            minute_bar_generator=minute_bg
        )
        
        if open_price and open_price > 0:
            bar.open_price = open_price
    
    def _update_period_open_price_if_needed(
        self, 
        vt_symbol: str, 
        minute_bar: BarData
    ) -> None:
        """
        检查是否需要更新大周期K线的开盘价
        
        当第一根分钟K线完成时，如果当前有大周期K线正在生成，
        且该分钟K线是该周期的第一根，更新大周期K线的开盘价。
        
        Args:
            vt_symbol: 合约代码
            minute_bar: 完成的1分钟K线
        """
        if minute_bar.interval != Interval.MINUTE:
            return
        
        # 检查是否有正在生成的大周期K线
        if vt_symbol not in self.current_bars:
            return
        
        intervals = self._get_recording_intervals(vt_symbol)
        
        for interval in intervals:
            if interval == Interval.MINUTE:
                continue
            
            if interval not in self.current_bars[vt_symbol]:
                continue
            
            current_bar = self.current_bars[vt_symbol][interval]
            if not current_bar:
                continue
            
            # 获取该分钟K线所属的大周期
            minute_bar_period = get_period_start(
                minute_bar.datetime, 
                interval, 
                minute_bar.exchange
            )
            
            if not minute_bar_period:
                continue
            
            # 检查该分钟K线是否属于当前大周期K线的第一根
            if minute_bar_period == current_bar.datetime:
                # 获取该分钟K线的周期起始时间（应该是该分钟K线本身的时间）
                minute_period = get_period_start(
                    minute_bar.datetime, 
                    Interval.MINUTE, 
                    minute_bar.exchange
                )
                
                # 检查该分钟K线是否是该大周期的第一根
                if minute_period == current_bar.datetime:
                    # 如果当前大周期K线的开盘价不是该分钟K线的开盘价，需要更新
                    if (minute_bar.open_price and minute_bar.open_price > 0 and 
                        current_bar.open_price != minute_bar.open_price):
                        old_open_price = current_bar.open_price
                        current_bar.open_price = minute_bar.open_price
                        
                        self.write_log(
                            f"[开盘价更新] {vt_symbol} {interval.value}K线 "
                            f"({current_bar.datetime.strftime('%Y-%m-%d %H:%M')}) "
                            f"开盘价已更新: {old_open_price} -> {minute_bar.open_price} "
                            f"(来自{minute_bar.datetime.strftime('%H:%M')}分钟K线)"
                        )

    def subscribe(self, contract: ContractData) -> None:
        """"""
        req: SubscribeRequest = SubscribeRequest(
            symbol=contract.symbol,
            exchange=contract.exchange
        )
        self.main_engine.subscribe(req, contract.gateway_name)
        self.write_log(f"[DataRecorder] 📡 已订阅合约: {contract.vt_symbol} (网关: {contract.gateway_name})")
