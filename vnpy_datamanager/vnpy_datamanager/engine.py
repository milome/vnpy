import csv
from datetime import datetime, timedelta
from collections.abc import Callable
from typing import Optional

from vnpy.trader.engine import BaseEngine, MainEngine, EventEngine
from vnpy.trader.constant import Interval, Exchange
from vnpy.trader.object import BarData, TickData, ContractData, HistoryRequest
from vnpy.trader.database import BaseDatabase, get_database, BarOverview, DB_TZ
from vnpy.trader.datafeed import BaseDatafeed, get_datafeed
from vnpy.trader.utility import ZoneInfo

APP_NAME = "DataManager"


class ManagerEngine(BaseEngine):
    """"""

    def __init__(
        self,
        main_engine: MainEngine,
        event_engine: EventEngine,
    ) -> None:
        """"""
        super().__init__(main_engine, event_engine, APP_NAME)

        self.database: BaseDatabase = get_database()
        self.datafeed: BaseDatafeed = get_datafeed()

    def import_data_from_csv(
        self,
        file_path: str,
        symbol: str,
        exchange: Exchange,
        interval: Interval,
        tz_name: str,
        datetime_head: str,
        open_head: str,
        high_head: str,
        low_head: str,
        close_head: str,
        volume_head: str,
        turnover_head: str,
        open_interest_head: str,
        datetime_format: str
    ) -> tuple:
        """"""
        with open(file_path) as f:
            buf: list = [line.replace("\0", "") for line in f]

        reader: csv.DictReader = csv.DictReader(buf, delimiter=",")

        bars: list[BarData] = []
        start: datetime | None = None
        count: int = 0
        tz: ZoneInfo = ZoneInfo(tz_name)

        for item in reader:
            if datetime_format:
                dt: datetime = datetime.strptime(item[datetime_head], datetime_format)
            else:
                dt = datetime.fromisoformat(item[datetime_head])
            dt = dt.replace(tzinfo=tz)

            turnover = item.get(turnover_head, 0)
            open_interest = item.get(open_interest_head, 0)

            bar: BarData = BarData(
                symbol=symbol,
                exchange=exchange,
                datetime=dt,
                interval=interval,
                volume=float(item[volume_head]),
                open_price=float(item[open_head]),
                high_price=float(item[high_head]),
                low_price=float(item[low_head]),
                close_price=float(item[close_head]),
                turnover=float(turnover),
                open_interest=float(open_interest),
                gateway_name="DB",
            )

            bars.append(bar)

            # do some statistics
            count += 1
            if not start:
                start = bar.datetime

        end: datetime = bar.datetime

        # insert into database
        self.database.save_bar_data(bars)

        return start, end, count

    def output_data_to_csv(
        self,
        file_path: str,
        symbol: str,
        exchange: Exchange,
        interval: Interval,
        start: datetime,
        end: datetime
    ) -> bool:
        """"""
        bars: list[BarData] = self.load_bar_data(symbol, exchange, interval, start, end)

        fieldnames: list = [
            "symbol",
            "exchange",
            "datetime",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "turnover",
            "open_interest"
        ]

        try:
            with open(file_path, "w") as f:
                writer: csv.DictWriter = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
                writer.writeheader()

                for bar in bars:
                    d: dict = {
                        "symbol": bar.symbol,
                        "exchange": bar.exchange.value,
                        "datetime": bar.datetime.strftime("%Y-%m-%d %H:%M:%S"),
                        "open": bar.open_price,
                        "high": bar.high_price,
                        "low": bar.low_price,
                        "close": bar.close_price,
                        "turnover": bar.turnover,
                        "volume": bar.volume,
                        "open_interest": bar.open_interest,
                    }
                    writer.writerow(d)

            return True
        except PermissionError:
            return False

    def get_bar_overview(self) -> list[BarOverview]:
        """"""
        overview: list[BarOverview] = self.database.get_bar_overview()
        return overview

    def load_bar_data(
        self,
        symbol: str,
        exchange: Exchange,
        interval: Interval,
        start: datetime,
        end: datetime
    ) -> list[BarData]:
        """"""
        bars: list[BarData] = self.database.load_bar_data(
            symbol,
            exchange,
            interval,
            start,
            end
        )

        return bars

    def delete_bar_data(
        self,
        symbol: str,
        exchange: Exchange,
        interval: Interval
    ) -> int:
        """"""
        count: int = self.database.delete_bar_data(
            symbol,
            exchange,
            interval
        )

        return count

    def download_bar_data(
        self,
        symbol: str,
        exchange: Exchange,
        interval: str,
        start: datetime,
        output: Callable
    ) -> int:
        """
        Query bar data from datafeed.
        For 4-hour bars, aggregate from 1-hour or 1-minute data instead of downloading.
        """
        interval_enum = Interval(interval)
        
        # 如果是5分钟数据，从已有1分钟数据合成
        if interval_enum == Interval.MINUTE_5:
            self.main_engine.write_log(f"[5分钟数据合成] 开始合成 {symbol}.{exchange.value} 的5分钟K线数据")
            count = self.aggregate_5minute_bars(symbol, exchange, start, datetime.now(DB_TZ))
            self.main_engine.write_log(f"[5分钟数据合成] 合成完成，共 {count} 条数据")
            return count
        
        # 如果是4小时数据，从已有数据合成
        if interval_enum == Interval.HOUR_4:
            self.main_engine.write_log(f"[4小时数据合成] 开始合成 {symbol}.{exchange.value} 的4小时K线数据")
            count = self.aggregate_4hour_bars(symbol, exchange, start, datetime.now(DB_TZ))
            self.main_engine.write_log(f"[4小时数据合成] 合成完成，共 {count} 条数据")
            return count
        
        req: HistoryRequest = HistoryRequest(
            symbol=symbol,
            exchange=exchange,
            interval=interval_enum,
            start=start,
            end=datetime.now(DB_TZ)
        )

        vt_symbol: str = f"{symbol}.{exchange.value}"
        contract: ContractData | None = self.main_engine.get_contract(vt_symbol)

        # If history data provided in gateway, then query
        if contract and contract.history_data:
            self.main_engine.write_log(f"[调试] 开始查询历史数据：{vt_symbol}，网关：{contract.gateway_name}")
            data: list[BarData] = self.main_engine.query_history(
                req, contract.gateway_name
            )
            self.main_engine.write_log(f"[调试] 查询返回数据量：{len(data) if data else 0} 条")
        # Otherwise use datafeed to query data
        else:
            self.main_engine.write_log(f"[调试] 使用datafeed查询历史数据：{vt_symbol}")
            data = self.datafeed.query_bar_history(req, output)
            self.main_engine.write_log(f"[调试] datafeed返回数据量：{len(data) if data else 0} 条")

        if data:
            self.main_engine.write_log(f"[调试] 开始保存 {len(data)} 条数据到数据库")
            self.database.save_bar_data(data)
            count = len(data)
            self.main_engine.write_log(f"[调试] 数据保存完成，准备返回count={count}")
            return count

        self.main_engine.write_log(f"[调试] 没有查询到数据，返回0")
        return 0

    def download_tick_data(
        self,
        symbol: str,
        exchange: Exchange,
        start: datetime,
        output: Callable
    ) -> int:
        """
        Query tick data from datafeed.
        """
        req: HistoryRequest = HistoryRequest(
            symbol=symbol,
            exchange=exchange,
            start=start,
            end=datetime.now(DB_TZ)
        )

        data: list[TickData] = self.datafeed.query_tick_history(req, output)

        if data:
            self.database.save_tick_data(data)
            return (len(data))

        return 0

    def aggregate_5minute_bars(
        self,
        symbol: str,
        exchange: Exchange,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None
    ) -> int:
        """
        从1分钟数据合成5分钟K线数据
        
        Args:
            symbol: 合约代码
            exchange: 交易所
            start: 开始时间（可选，如果为None则从已有5分钟数据的结束时间开始）
            end: 结束时间（可选，如果为None则到当前时间）
        
        Returns:
            合成的K线数量
        """
        # 确定时间范围
        if end is None:
            end = datetime.now(DB_TZ)
        elif end.tzinfo is None:
            end = end.replace(tzinfo=DB_TZ)
        
        # 检查是否已有5分钟数据
        existing_5m_overview: Optional[BarOverview] = None
        overviews = self.database.get_bar_overview()
        for overview in overviews:
            if (overview.symbol == symbol and 
                overview.exchange == exchange and 
                overview.interval == Interval.MINUTE_5):
                existing_5m_overview = overview
                break
        
        # 如果已有5分钟数据，从结束时间开始合成
        if existing_5m_overview and start is None:
            start = existing_5m_overview.end
            # 统一时区处理
            if start and start.tzinfo is None:
                start = start.replace(tzinfo=DB_TZ)
            # 如果已有数据已经是最新的，则不需要合成
            if start and start >= end:
                return 0
        
        # 如果没有指定开始时间，尝试从1分钟数据的开始时间开始
        if start is None:
            # 查找1分钟数据
            minute_start = None
            for overview in overviews:
                if (overview.symbol == symbol and 
                    overview.exchange == exchange and 
                    overview.interval == Interval.MINUTE):
                    minute_start = overview.start
                    break
            
            if minute_start:
                start = minute_start
                # 统一时区处理
                if start.tzinfo is None:
                    start = start.replace(tzinfo=DB_TZ)
            else:
                # 没有基础数据，无法合成
                return 0
        
        # 加载1分钟数据
        self.main_engine.write_log(f"[5分钟数据合成] 开始加载1分钟数据: {symbol}.{exchange.value}")
        minute_bars = self.database.load_bar_data(
            symbol, exchange, Interval.MINUTE, start, end
        )
        
        if not minute_bars:
            self.main_engine.write_log(f"[5分钟数据合成] 未找到1分钟数据: {symbol}.{exchange.value}")
            return 0
        
        self.main_engine.write_log(f"[5分钟数据合成] 加载了 {len(minute_bars)} 条1分钟数据，开始合成...")
        
        # 合成5分钟K线
        aggregated_bars: list[BarData] = []
        current_5m_bar: Optional[BarData] = None
        
        for i, bar in enumerate(minute_bars):
            # 每处理1000条数据，记录一次进度
            if i > 0 and i % 1000 == 0:
                self.main_engine.write_log(f"[5分钟数据合成] 已处理 {i}/{len(minute_bars)} 条1分钟数据...")
            # 统一时区处理
            if bar.datetime.tzinfo:
                bar_dt = bar.datetime
            else:
                bar_dt = bar.datetime.replace(tzinfo=DB_TZ)
            
            # 计算5分钟K线的起始时间（0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55分钟）
            minute = bar_dt.minute
            period_start_minute = (minute // 5) * 5
            # 保持时区信息
            period_start = bar_dt.replace(minute=period_start_minute, second=0, microsecond=0)
            
            # 如果是新的5分钟周期，保存上一个并创建新的
            if current_5m_bar is None or current_5m_bar.datetime != period_start:
                # 保存上一个5分钟K线
                if current_5m_bar is not None:
                    aggregated_bars.append(current_5m_bar)
                
                # 创建新的5分钟K线
                current_5m_bar = BarData(
                    symbol=bar.symbol,
                    exchange=bar.exchange,
                    datetime=period_start,
                    interval=Interval.MINUTE_5,
                    open_price=bar.open_price,
                    high_price=bar.high_price,
                    low_price=bar.low_price,
                    close_price=bar.close_price,
                    volume=bar.volume,
                    turnover=bar.turnover,
                    open_interest=bar.open_interest,
                    gateway_name="DB"
                )
            else:
                # 更新当前5分钟K线
                current_5m_bar.high_price = max(current_5m_bar.high_price, bar.high_price)
                current_5m_bar.low_price = min(current_5m_bar.low_price, bar.low_price)
                current_5m_bar.close_price = bar.close_price
                current_5m_bar.volume += bar.volume
                current_5m_bar.turnover += bar.turnover
                current_5m_bar.open_interest = bar.open_interest
        
        # 保存最后一个5分钟K线
        if current_5m_bar is not None:
            aggregated_bars.append(current_5m_bar)
        
        # 保存到数据库
        if aggregated_bars:
            self.database.save_bar_data(aggregated_bars)
            return len(aggregated_bars)
        
        return 0

    def aggregate_4hour_bars(
        self,
        symbol: str,
        exchange: Exchange,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None
    ) -> int:
        """
        从1小时或1分钟数据合成4小时K线数据
        
        Args:
            symbol: 合约代码
            exchange: 交易所
            start: 开始时间（可选，如果为None则从已有4小时数据的结束时间开始）
            end: 结束时间（可选，如果为None则到当前时间）
        
        Returns:
            合成的K线数量
        """
        from typing import Optional as Opt
        
        # 确定时间范围
        if end is None:
            end = datetime.now(DB_TZ)
        elif end.tzinfo is None:
            end = end.replace(tzinfo=DB_TZ)
        
        # 检查是否已有4小时数据
        existing_4h_overview: Optional[BarOverview] = None
        overviews = self.database.get_bar_overview()
        for overview in overviews:
            if (overview.symbol == symbol and 
                overview.exchange == exchange and 
                overview.interval == Interval.HOUR_4):
                existing_4h_overview = overview
                break
        
        # 如果已有4小时数据，从结束时间开始合成
        if existing_4h_overview and start is None:
            start = existing_4h_overview.end
            # 统一时区处理
            if start and start.tzinfo is None:
                start = start.replace(tzinfo=DB_TZ)
            # 如果已有数据已经是最新的，则不需要合成
            if start and start >= end:
                return 0
        
        # 如果没有指定开始时间，尝试从1小时或1分钟数据的开始时间开始
        if start is None:
            # 查找1小时数据
            hour_start = None
            for overview in overviews:
                if (overview.symbol == symbol and 
                    overview.exchange == exchange and 
                    overview.interval == Interval.HOUR):
                    hour_start = overview.start
                    break
            
            # 查找1分钟数据
            minute_start = None
            for overview in overviews:
                if (overview.symbol == symbol and 
                    overview.exchange == exchange and 
                    overview.interval == Interval.MINUTE):
                    minute_start = overview.start
                    break
            
            # 选择最早的时间
            if hour_start and minute_start:
                start = min(hour_start, minute_start)
            elif hour_start:
                start = hour_start
            elif minute_start:
                start = minute_start
            else:
                # 没有基础数据，无法合成
                return 0
            
            # 统一时区处理
            if start and start.tzinfo is None:
                start = start.replace(tzinfo=DB_TZ)
        
        # 优先使用1小时数据，如果没有则使用1分钟数据
        source_bars: list[BarData] = []
        source_interval: Optional[Interval] = None
        
        # 尝试加载1小时数据
        self.main_engine.write_log(f"[4小时数据合成] 开始加载数据: {symbol}.{exchange.value}")
        hour_bars = self.database.load_bar_data(
            symbol, exchange, Interval.HOUR, start, end
        )
        
        if hour_bars:
            source_bars = hour_bars
            source_interval = Interval.HOUR
            self.main_engine.write_log(f"[4小时数据合成] 使用1小时数据，共 {len(hour_bars)} 条")
        else:
            # 如果没有1小时数据，尝试使用1分钟数据
            minute_bars = self.database.load_bar_data(
                symbol, exchange, Interval.MINUTE, start, end
            )
            if minute_bars:
                source_bars = minute_bars
                source_interval = Interval.MINUTE
                self.main_engine.write_log(f"[4小时数据合成] 使用1分钟数据，共 {len(minute_bars)} 条")
        
        if not source_bars:
            self.main_engine.write_log(f"[4小时数据合成] 未找到基础数据: {symbol}.{exchange.value}")
            return 0
        
        self.main_engine.write_log(f"[4小时数据合成] 开始合成，共 {len(source_bars)} 条源数据...")
        
        # 合成4小时K线
        aggregated_bars: list[BarData] = []
        current_4h_bar: Optional[BarData] = None
        
        for i, bar in enumerate(source_bars):
            # 每处理1000条数据，记录一次进度
            if i > 0 and i % 1000 == 0:
                self.main_engine.write_log(f"[4小时数据合成] 已处理 {i}/{len(source_bars)} 条数据...")
            # 计算4小时K线的起始时间（0:00, 4:00, 8:00, 12:00, 16:00, 20:00）
            # 统一时区处理
            if bar.datetime.tzinfo:
                bar_dt = bar.datetime
            else:
                bar_dt = bar.datetime.replace(tzinfo=DB_TZ)
            
            hour = bar_dt.hour
            # 计算属于哪个4小时周期
            period_start_hour = (hour // 4) * 4
            # 保持时区信息
            period_start = bar_dt.replace(hour=period_start_hour, minute=0, second=0, microsecond=0)
            
            # 如果是新的4小时周期，保存上一个并创建新的
            if current_4h_bar is None or current_4h_bar.datetime != period_start:
                # 保存上一个4小时K线
                if current_4h_bar is not None:
                    aggregated_bars.append(current_4h_bar)
                
                # 创建新的4小时K线
                current_4h_bar = BarData(
                    symbol=bar.symbol,
                    exchange=bar.exchange,
                    datetime=period_start,
                    interval=Interval.HOUR_4,
                    open_price=bar.open_price,
                    high_price=bar.high_price,
                    low_price=bar.low_price,
                    close_price=bar.close_price,
                    volume=bar.volume,
                    turnover=bar.turnover,
                    open_interest=bar.open_interest,
                    gateway_name="DB"
                )
            else:
                # 更新当前4小时K线
                current_4h_bar.high_price = max(current_4h_bar.high_price, bar.high_price)
                current_4h_bar.low_price = min(current_4h_bar.low_price, bar.low_price)
                current_4h_bar.close_price = bar.close_price
                current_4h_bar.volume += bar.volume
                current_4h_bar.turnover += bar.turnover
                current_4h_bar.open_interest = bar.open_interest
        
        # 保存最后一个4小时K线
        if current_4h_bar is not None:
            aggregated_bars.append(current_4h_bar)
        
        # 保存到数据库
        if aggregated_bars:
            self.database.save_bar_data(aggregated_bars)
            return len(aggregated_bars)
        
        return 0
