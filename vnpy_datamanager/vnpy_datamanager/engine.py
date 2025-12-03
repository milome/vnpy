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
from vnpy.trader.period_utils import (
    get_period_start,
    get_hkfe_hour_period_start,
    get_hkfe_4hour_period,
    is_hkfe_trading_time,
    aggregate_to_1hour_from_minutes
)

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
        interval: Interval | str,
        start: datetime,
        output: Callable
    ) -> int:
        """
        Query bar data from datafeed.
        For 4-hour bars, aggregate from 1-hour or 1-minute data instead of downloading.
        
        Args:
            symbol: 合约代码
            exchange: 交易所
            interval: 数据周期，可以是 Interval 枚举或字符串（如 "1h"）
            start: 开始时间
            output: 输出回调函数
        
        Returns:
            下载/合成的数据条数
        """
        # 安全调用 output 回调
        def safe_output(msg: str):
            if callable(output):
                try:
                    output(msg)
                except:
                    pass
        
        # 统一转换 interval 为 Interval 枚举类型
        if isinstance(interval, Interval):
            interval_enum = interval
        else:
            interval_enum = Interval(interval)
        
        # 记录下载请求日志
        self.main_engine.write_log(f"[数据下载] 请求下载 {symbol}.{exchange.value} {interval_enum.value} 数据，开始时间: {start}")
        
        # 如果是5分钟数据，从已有1分钟数据合成
        if interval_enum == Interval.MINUTE_5:
            safe_output("开始合成5分钟K线数据...")
            self.main_engine.write_log(f"[5分钟数据合成] 开始合成 {symbol}.{exchange.value} 的5分钟K线数据")
            count = self.aggregate_5minute_bars(symbol, exchange, start, datetime.now(DB_TZ))
            safe_output(f"合成完成，共 {count} 条5分钟K线")
            self.main_engine.write_log(f"[5分钟数据合成] 合成完成，共 {count} 条数据")
            return count
        
        # 如果是1小时数据，从已有1分钟数据合成（禁止直接下载）
        if interval_enum == Interval.HOUR:
            safe_output("开始合成1小时K线数据...")
            self.main_engine.write_log(f"[1小时数据合成] 开始合成 {symbol}.{exchange.value} 的1小时K线数据")
            count = self.aggregate_hour_bars(symbol, exchange, start, datetime.now(DB_TZ))
            safe_output(f"合成完成，共 {count} 条1小时K线")
            self.main_engine.write_log(f"[1小时数据合成] 合成完成，共 {count} 条数据")
            return count
        
        # 如果是4小时数据，从已有数据合成
        if interval_enum == Interval.HOUR_4:
            safe_output("开始合成4小时K线数据...")
            self.main_engine.write_log(f"[4小时数据合成] 开始合成 {symbol}.{exchange.value} 的4小时K线数据")
            count = self.aggregate_4hour_bars(symbol, exchange, start, datetime.now(DB_TZ))
            safe_output(f"合成完成，共 {count} 条4小时K线")
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
            safe_output(f"正在从网关 {contract.gateway_name} 查询历史数据...")
            self.main_engine.write_log(f"[调试] 开始查询历史数据：{vt_symbol}，网关：{contract.gateway_name}")
            data: list[BarData] = self.main_engine.query_history(
                req, contract.gateway_name
            )
            data_count = len(data) if data else 0
            safe_output(f"K线数据获取完成，共 {data_count} 条")
            self.main_engine.write_log(f"[调试] 查询返回数据量：{data_count} 条")
        # Otherwise use datafeed to query data
        else:
            safe_output(f"正在从数据源查询历史数据...")
            self.main_engine.write_log(f"[调试] 使用datafeed查询历史数据：{vt_symbol}")
            data = self.datafeed.query_bar_history(req, output)
            data_count = len(data) if data else 0
            safe_output(f"K线数据获取完成，共 {data_count} 条")
            self.main_engine.write_log(f"[调试] datafeed返回数据量：{data_count} 条")

        if data:
            safe_output(f"开始保存 {len(data)} 条数据到数据库...")
            self.main_engine.write_log(f"[调试] 开始保存 {len(data)} 条数据到数据库")
            self.database.save_bar_data(data)
            count = len(data)
            safe_output(f"数据保存完成，共 {count} 条")
            self.main_engine.write_log(f"[调试] 数据保存完成，准备返回count={count}")
            return count

        safe_output("没有查询到数据")
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
        从1分钟数据合成5分钟K线数据（香港期货专用，过滤非交易时段）
        
        香港期货交易时段：
        - 日盘：09:15 - 12:00, 13:00 - 16:30
        - 夜盘：17:15 - 03:00（次日凌晨）
        
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
        
        self.main_engine.write_log(f"[5分钟数据合成] 加载了 {len(minute_bars)} 条1分钟数据，开始按港期时段合成...")
        
        # 按5分钟周期分组（过滤非交易时段）
        period_bars: dict[datetime, list[BarData]] = {}
        skipped_count = 0
        
        for i, bar in enumerate(minute_bars):
            # 每处理10000条数据，记录一次进度
            if i > 0 and i % 10000 == 0:
                self.main_engine.write_log(f"[5分钟数据合成] 已处理 {i}/{len(minute_bars)} 条1分钟数据...")
            
            # 统一时区处理
            if bar.datetime.tzinfo:
                bar_dt = bar.datetime
            else:
                bar_dt = bar.datetime.replace(tzinfo=DB_TZ)
            
            # 获取该K线所属的5分钟周期（会过滤非交易时段）
            period_start = get_period_start(bar_dt, Interval.MINUTE_5, exchange)
            
            if period_start is None:
                # 非交易时段数据，跳过
                skipped_count += 1
                continue
            
            # 添加到对应周期
            if period_start not in period_bars:
                period_bars[period_start] = []
            period_bars[period_start].append(bar)
        
        if skipped_count > 0:
            self.main_engine.write_log(f"[5分钟数据合成] 跳过非交易时段数据 {skipped_count} 条")
        
        # 合成5分钟K线
        aggregated_bars: list[BarData] = []
        
        for period_start in sorted(period_bars.keys()):
            bars = period_bars[period_start]
            if not bars:
                continue
            
            # 确保bars按时间排序，以便正确获取第一根和最后一根
            bars.sort(key=lambda x: x.datetime)
            
            # 计算OHLCV
            # 使用第一根1分钟K线的开盘价（已按时间排序）
            open_price = bars[0].open_price
            close_price = bars[-1].close_price
            high_price = max(bar.high_price for bar in bars)
            low_price = min(bar.low_price for bar in bars)
            volume = sum(bar.volume for bar in bars)
            turnover = sum(bar.turnover for bar in bars)
            open_interest = bars[-1].open_interest
            
            # 创建5分钟K线
            bar_5m = BarData(
                symbol=symbol,
                exchange=exchange,
                datetime=period_start,
                interval=Interval.MINUTE_5,
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                volume=volume,
                turnover=turnover,
                open_interest=open_interest,
                gateway_name="DB"
            )
            aggregated_bars.append(bar_5m)
        
        self.main_engine.write_log(f"[5分钟数据合成] 合成完成，共 {len(aggregated_bars)} 根5分钟K线")
        
        # 保存到数据库
        if aggregated_bars:
            self.database.save_bar_data(aggregated_bars)
            return len(aggregated_bars)
        
        return 0


    def aggregate_hour_bars(
        self,
        symbol: str,
        exchange: Exchange,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None
    ) -> int:
        """
        从1分钟数据合成1小时K线数据（香港期货专用）
        
        精确的1小时时间边界（闭区间）：
        1. 17:15-18:14：第一根1小时K线（时间戳：17:15）
        2. 18:15-19:14：第二根1小时K线（时间戳：18:15）
        3. 19:15-20:14：第三根1小时K线（时间戳：19:15）
        4. 20:15-21:14：第四根1小时K线（时间戳：20:15）
        5. 21:15-22:14：第五根1小时K线（时间戳：21:15）
        6. 22:15-23:14：第六根1小时K线（时间戳：22:15）
        7. 23:15-次日00:14：第七根1小时K线（时间戳：23:15）
        8. 00:15-01:14：第八根1小时K线（时间戳：00:15）
        9. 01:15-02:14：第九根1小时K线（时间戳：01:15）
        10. 02:15-09:29：第十根1小时K线（时间戳：02:15，跨休市）
        11. 09:30-10:29：第十一根1小时K线（时间戳：09:30）
        12. 10:30-11:29：第十二根1小时K线（时间戳：10:30）
        13. 11:30-12:00 + 13:00-13:29：第十三根1小时K线（时间戳：11:30，跨午休）
        14. 13:30-14:29：第十四根1小时K线（时间戳：13:30）
        15. 14:30-15:29：第十五根1小时K线（时间戳：14:30）
        16. 15:30-16:29：第十六根1小时K线（时间戳：15:30）
        
        特殊情况处理：
        1. 意外停盘：如果在16:29前意外停盘，当日最后一根1小时K线到停盘时间截止。次日开盘09:15到09:29算作一根1小时K线。
        2. 金融假期：如果在夜盘收盘后遇到金融假期，完整的1小时K线开始时间是开盘当日的02:15，结束时间是金融假期后开盘的早09:29。
        3. 周末：周六凌晨的02:15 - 周一09:29算一根1小时K线。
        
        Args:
            symbol: 合约代码
            exchange: 交易所
            start: 开始时间（可选，如果为None则从已有1小时数据的结束时间开始）
            end: 结束时间（可选，如果为None则到当前时间）
        
        Returns:
            合成的K线数量
        """
        # 确定时间范围
        if end is None:
            end = datetime.now(DB_TZ)
        elif end.tzinfo is None:
            end = end.replace(tzinfo=DB_TZ)
        
        # 检查是否已有1小时数据
        existing_1h_overview: Optional[BarOverview] = None
        overviews = self.database.get_bar_overview()
        for overview in overviews:
            if (overview.symbol == symbol and 
                overview.exchange == exchange and 
                overview.interval == Interval.HOUR):
                existing_1h_overview = overview
                break
        
        # 如果已有1小时数据，从结束时间开始合成
        if existing_1h_overview and start is None:
            start = existing_1h_overview.end
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
                # 没有1分钟数据，无法合成
                self.main_engine.write_log(f"[1小时数据合成] 未找到1分钟数据，无法合成: {symbol}.{exchange.value}")
                return 0
        
        # 只使用1分钟数据来合成1小时K线（确保精确性）
        self.main_engine.write_log(f"[1小时数据合成] 开始加载1分钟数据: {symbol}.{exchange.value}")
        minute_bars = self.database.load_bar_data(
            symbol, exchange, Interval.MINUTE, start, end
        )
        
        if not minute_bars:
            self.main_engine.write_log(f"[1小时数据合成] 未找到1分钟数据: {symbol}.{exchange.value}")
            return 0
        
        self.main_engine.write_log(f"[1小时数据合成] 加载了 {len(minute_bars)} 条1分钟数据，开始按港期时段合成...")
        
        # 统一时区处理：确保所有bar的datetime都有时区信息
        processed_bars = []
        skipped_count = 0
        
        for i, bar in enumerate(minute_bars):
            # 每处理10000条数据，记录一次进度
            if i > 0 and i % 10000 == 0:
                self.main_engine.write_log(f"[1小时数据合成] 已处理 {i}/{len(minute_bars)} 条数据...")
            
            # 统一时区处理
            if bar.datetime.tzinfo:
                bar_dt = bar.datetime
            else:
                bar_dt = bar.datetime.replace(tzinfo=DB_TZ)
                # 创建新的BarData对象，使用带时区的datetime
                bar = BarData(
                    symbol=bar.symbol,
                    exchange=bar.exchange,
                    datetime=bar_dt,
                    interval=bar.interval,
                    open_price=bar.open_price,
                    high_price=bar.high_price,
                    low_price=bar.low_price,
                    close_price=bar.close_price,
                    volume=bar.volume,
                    turnover=bar.turnover,
                    open_interest=bar.open_interest,
                    gateway_name=bar.gateway_name,
                )
            
            # 检查是否在交易时段内（非交易时段数据会被共同函数跳过）
            period_start = get_hkfe_hour_period_start(bar_dt)
            if period_start is None:
                skipped_count += 1
                continue
            
            processed_bars.append(bar)
        
        if skipped_count > 0:
            self.main_engine.write_log(f"[1小时数据合成] 跳过非交易时段数据 {skipped_count} 条")
        
        # 使用共同函数聚合
        aggregated_bars = aggregate_to_1hour_from_minutes(processed_bars, symbol, exchange)
        
        # 设置gateway_name为"DB"（数据库来源）
        for bar in aggregated_bars:
            bar.gateway_name = "DB"
        
        self.main_engine.write_log(f"[1小时数据合成] 合成完成，共 {len(aggregated_bars)} 根1小时K线")
        
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
        从1分钟数据合成4小时K线数据（香港期货专用）
        
        精确的4小时时间边界（闭区间）：
        1. 17:15-21:14：第一根4小时K线（时间戳：17:15，开盘价=17:15的1分钟开盘价，收盘价=21:14的1分钟收盘价）
        2. 21:15-次日01:14：第二根4小时K线（时间戳：21:15，开盘价=21:15的1分钟开盘价，收盘价=01:14的1分钟收盘价）
        3. 01:15-03:00 + 09:15-11:29：第三根4小时K线（时间戳：01:15，开盘价=01:15的1分钟开盘价，收盘价=11:29的1分钟收盘价）
        4. 11:30-12:00 + 13:00-16:29：第四根4小时K线（时间戳：11:30，开盘价=11:30的1分钟开盘价，收盘价=16:29的1分钟收盘价）
        
        特殊情况处理：
        1. 意外停盘：如果在16:29前意外停盘，当日最后一根4小时K线到停盘时间截止。次日开盘09:15到11:29算作一根独立的4小时K线。
        2. 金融假期：如果在夜盘收盘后遇到金融假期，完整的4小时K线开始时间是01:15，结束时间是金融假期后开盘的早11:29。
        
        Args:
            symbol: 合约代码
            exchange: 交易所
            start: 开始时间（可选，如果为None则从已有4小时数据的结束时间开始）
            end: 结束时间（可选，如果为None则到当前时间）
        
        Returns:
            合成的K线数量
        """
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
                # 没有1分钟数据，无法合成
                self.main_engine.write_log(f"[4小时数据合成] 未找到1分钟数据，无法合成: {symbol}.{exchange.value}")
                return 0
        
        # 只使用1分钟数据来合成4小时K线（确保精确性）
        self.main_engine.write_log(f"[4小时数据合成] 开始加载1分钟数据: {symbol}.{exchange.value}")
        minute_bars = self.database.load_bar_data(
            symbol, exchange, Interval.MINUTE, start, end
        )
        
        if not minute_bars:
            self.main_engine.write_log(f"[4小时数据合成] 未找到1分钟数据: {symbol}.{exchange.value}")
            return 0
        
        self.main_engine.write_log(f"[4小时数据合成] 加载了 {len(minute_bars)} 条1分钟数据，开始按港期时段合成...")
        
        # 按4小时周期分组
        period_bars: dict[datetime, list[BarData]] = {}
        skipped_count = 0
        
        for i, bar in enumerate(minute_bars):
            # 每处理10000条数据，记录一次进度
            if i > 0 and i % 10000 == 0:
                self.main_engine.write_log(f"[4小时数据合成] 已处理 {i}/{len(minute_bars)} 条数据...")
            
            # 统一时区处理
            if bar.datetime.tzinfo:
                bar_dt = bar.datetime
            else:
                bar_dt = bar.datetime.replace(tzinfo=DB_TZ)
            
            # 获取该K线所属的4小时周期
            period_start, period_index = get_hkfe_4hour_period(bar_dt)
            
            if period_start is None:
                # 非交易时段数据，跳过
                skipped_count += 1
                continue
            
            # 添加到对应周期
            if period_start not in period_bars:
                period_bars[period_start] = []
            period_bars[period_start].append(bar)
        
        if skipped_count > 0:
            self.main_engine.write_log(f"[4小时数据合成] 跳过非交易时段数据 {skipped_count} 条")
        
        # 合成4小时K线
        aggregated_bars: list[BarData] = []
        
        for period_start in sorted(period_bars.keys()):
            bars = period_bars[period_start]
            if not bars:
                continue
            
            # 确保bars按时间排序，以便正确获取第一根和最后一根
            bars.sort(key=lambda x: x.datetime)
            
            # 计算OHLCV
            # 使用第一根1分钟K线的开盘价（已按时间排序）
            open_price = bars[0].open_price
            close_price = bars[-1].close_price
            high_price = max(bar.high_price for bar in bars)
            low_price = min(bar.low_price for bar in bars)
            volume = sum(bar.volume for bar in bars)
            turnover = sum(bar.turnover for bar in bars)
            open_interest = bars[-1].open_interest
            
            # 创建4小时K线
            bar_4h = BarData(
                symbol=symbol,
                exchange=exchange,
                datetime=period_start,
                interval=Interval.HOUR_4,
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                volume=volume,
                turnover=turnover,
                open_interest=open_interest,
                gateway_name="DB"
            )
            aggregated_bars.append(bar_4h)
        
        self.main_engine.write_log(f"[4小时数据合成] 合成完成，共 {len(aggregated_bars)} 根4小时K线")
        
        # 保存到数据库
        if aggregated_bars:
            self.database.save_bar_data(aggregated_bars)
            return len(aggregated_bars)
        
        return 0
