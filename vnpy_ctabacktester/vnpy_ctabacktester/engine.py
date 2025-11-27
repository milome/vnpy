import importlib
import traceback
from datetime import datetime
from threading import Thread
from pathlib import Path
from inspect import getfile
from glob import glob
from types import ModuleType
from pandas import DataFrame

from vnpy.event import Event, EventEngine
from vnpy.trader.engine import BaseEngine, MainEngine
from vnpy.trader.constant import Interval
from vnpy.trader.utility import extract_vt_symbol, TRADER_DIR, TRADER_DIR
from vnpy.trader.object import HistoryRequest, TickData, ContractData
from vnpy.trader.datafeed import BaseDatafeed, get_datafeed
from vnpy.trader.database import BaseDatabase, get_database

import vnpy_ctastrategy
from vnpy_ctastrategy import CtaTemplate, TargetPosTemplate
from vnpy_ctastrategy.backtesting import (
    BacktestingEngine,
    OptimizationSetting,
    BacktestingMode
)
from .locale import _

APP_NAME = "CtaBacktester"

EVENT_BACKTESTER_LOG = "eBacktesterLog"
EVENT_BACKTESTER_BACKTESTING_FINISHED = "eBacktesterBacktestingFinished"
EVENT_BACKTESTER_OPTIMIZATION_FINISHED = "eBacktesterOptimizationFinished"


class BacktesterEngine(BaseEngine):
    """
    For running CTA strategy backtesting.
    """

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        """"""
        super().__init__(main_engine, event_engine, APP_NAME)

        self.classes: dict = {}
        self.backtesting_engine: BacktestingEngine = None
        self.thread: Thread | None = None

        self.datafeed: BaseDatafeed = get_datafeed()
        self.database: BaseDatabase = get_database()

        # Backtesting reuslt
        self.result_df: DataFrame | None = None
        self.result_statistics: dict | None = None

        # Optimization result
        self.result_values: list | None = None

    def init_engine(self) -> None:
        """"""
        self.write_log(_("初始化CTA回测引擎"))

        self.backtesting_engine = BacktestingEngine()
        # Redirect log from backtesting engine outside.
        self.backtesting_engine.output = self.write_log

        self.write_log("=" * 60)
        self.write_log("开始加载策略类...")
        
        # 获取运行时目录和工作目录信息
        cwd = Path.cwd()
        self.write_log(f"当前工作目录: {cwd}")
        self.write_log(f"VeighNa运行时目录: {TRADER_DIR}")
        
        self.load_strategy_class()
        
        loaded_count = len(self.classes)
        strategy_names = ", ".join(sorted(self.classes.keys())) if loaded_count > 0 else "无"
        self.write_log(f"策略文件加载完成 - 共加载 {loaded_count} 个策略类: {strategy_names}")
        self.write_log("=" * 60)

        self.init_datafeed()

    def init_datafeed(self) -> None:
        """
        Init datafeed client.
        """
        result: bool = self.datafeed.init(self.write_log)
        if result:
            self.write_log(_("数据服务初始化成功"))

    def write_log(self, msg: str) -> None:
        """"""
        # 同时输出到终端和UI日志窗口，方便调试
        print(f"[CTA回测] {msg}")
        event: Event = Event(EVENT_BACKTESTER_LOG)
        event.data = msg
        self.event_engine.put(event)

    def load_strategy_class(self) -> None:
        """
        Load strategy class from source code.
        """
        app_path: Path = Path(vnpy_ctastrategy.__file__).parent
        path1: Path = app_path.joinpath("strategies")
        self.write_log(f"[1/2] 扫描包内策略目录: {path1}")
        if path1.exists():
            self.write_log(f"      ✓ 目录存在，开始加载...")
            self.load_strategy_class_from_folder(path1, "vnpy_ctastrategy.strategies")
        else:
            self.write_log(f"      ✗ 目录不存在")

        # 使用VeighNa的运行时目录（TRADER_DIR），而不是当前工作目录
        # 这样可以确保从正确的位置加载用户自定义策略
        path2: Path = TRADER_DIR.joinpath("strategies")
        self.write_log(f"[2/2] 扫描运行时策略目录: {path2}")
        if path2.exists():
            self.write_log(f"      ✓ 目录存在，开始加载...")
            self.load_strategy_class_from_folder(path2, "strategies")
        else:
            self.write_log(f"      ✗ 目录不存在")

    def load_strategy_class_from_folder(self, path: Path, module_name: str = "") -> None:
        """
        Load strategy class from certain folder.
        """
        if not path.exists():
            self.write_log(f"      策略目录不存在，跳过: {path}")
            return
            
        file_count = 0
        found_files = []
        for suffix in ["py", "pyd", "so"]:
            pathname: str = str(path.joinpath(f"*.{suffix}"))
            for filepath in glob(pathname):
                filename: str = Path(filepath).stem
                # 跳过__init__.py文件
                if filename == "__init__":
                    continue
                file_count += 1
                found_files.append(filename)
                name: str = f"{module_name}.{filename}"
                self.write_log(f"      → 发现策略文件: {filename}.{suffix} (模块: {name})")
                self.load_strategy_class_from_module(name)
        
        if file_count == 0:
            self.write_log(f"      ⚠ 目录中未找到策略文件: {path}")
        else:
            self.write_log(f"      共发现 {file_count} 个策略文件: {', '.join(found_files)}")

    def load_strategy_class_from_module(self, module_name: str) -> None:
        """
        Load strategy class from module file.
        """
        try:
            module: ModuleType = importlib.import_module(module_name)
            self.write_log(f"        ✓ 模块导入成功: {module_name}")

            # 重载模块，确保如果策略文件中有任何修改，能够立即生效。
            importlib.reload(module)
            self.write_log(f"        ✓ 模块重载成功: {module_name}")

            strategy_found = False
            for name in dir(module):
                try:
                    value = getattr(module, name)
                    if (
                        isinstance(value, type)
                        and issubclass(value, CtaTemplate)
                        and value not in {CtaTemplate, TargetPosTemplate}
                    ):
                        self.classes[value.__name__] = value
                        self.write_log(f"        ✓✓ 成功加载策略类: {value.__name__} (来自模块 {module_name})")
                        strategy_found = True
                except Exception as e:
                    # 忽略某些属性访问错误（如属性不是类，或无法判断是否为子类）
                    pass
            
            if not strategy_found:
                self.write_log(f"        ⚠ 模块 {module_name} 中未找到策略类（继承自CtaTemplate）")
                
        except ImportError as e:
            msg = f"        ✗ 策略模块 {module_name} 导入失败 (ImportError): {str(e)}"
            self.write_log(msg)
        except Exception as e:  # noqa
            msg = f"        ✗ 策略文件 {module_name} 加载失败，触发异常：\n{traceback.format_exc()}"
            self.write_log(msg)

    def reload_strategy_class(self) -> None:
        """"""
        separator = "=" * 60
        self.write_log(separator)
        self.write_log("开始重载策略类...")
        
        # 获取运行时目录和工作目录信息
        cwd = Path.cwd()
        self.write_log(f"当前工作目录: {cwd}")
        self.write_log(f"VeighNa运行时目录: {TRADER_DIR}")
        
        self.classes.clear()
        self.load_strategy_class()
        
        loaded_count = len(self.classes)
        strategy_names = ", ".join(sorted(self.classes.keys())) if loaded_count > 0 else "无"
        self.write_log(f"策略文件重载刷新完成 - 共加载 {loaded_count} 个策略类: {strategy_names}")
        self.write_log(separator)

    def get_strategy_class_names(self) -> list:
        """"""
        return list(self.classes.keys())

    def run_backtesting(
        self,
        class_name: str,
        vt_symbol: str,
        interval: str,
        start: datetime,
        end: datetime,
        rate: float,
        slippage: float,
        size: int,
        pricetick: float,
        capital: int,
        setting: dict
    ) -> None:
        """"""
        self.result_df = None
        self.result_statistics = None

        engine: BacktestingEngine = self.backtesting_engine
        engine.clear_data()

        if interval == Interval.TICK.value:
            mode: BacktestingMode = BacktestingMode.TICK
        else:
            mode = BacktestingMode.BAR

        engine.set_parameters(
            vt_symbol=vt_symbol,
            interval=interval,
            start=start,
            end=end,
            rate=rate,
            slippage=slippage,
            size=size,
            pricetick=pricetick,
            capital=capital,
            mode=mode
        )

        strategy_class: type[CtaTemplate] = self.classes[class_name]
        engine.add_strategy(
            strategy_class,
            setting
        )

        engine.load_data()
        if not engine.history_data:
            self.write_log(_("策略回测失败，历史数据为空"))
            self.thread = None
            return

        try:
            engine.run_backtesting()
        except Exception:
            msg: str = _("策略回测失败，触发异常：\n{}").format(traceback.format_exc())
            self.write_log(msg)

            self.thread = None
            return

        self.result_df = engine.calculate_result()
        self.result_statistics = engine.calculate_statistics(output=False)

        # Clear thread object handler.
        self.thread = None

        # Put backtesting done event
        event: Event = Event(EVENT_BACKTESTER_BACKTESTING_FINISHED)
        self.event_engine.put(event)

    def start_backtesting(
        self,
        class_name: str,
        vt_symbol: str,
        interval: str,
        start: datetime,
        end: datetime,
        rate: float,
        slippage: float,
        size: int,
        pricetick: float,
        capital: int,
        setting: dict
    ) -> bool:
        if self.thread:
            self.write_log(_("已有任务在运行中，请等待完成"))
            return False

        self.write_log("-" * 40)
        self.thread = Thread(
            target=self.run_backtesting,
            args=(
                class_name,
                vt_symbol,
                interval,
                start,
                end,
                rate,
                slippage,
                size,
                pricetick,
                capital,
                setting
            )
        )
        self.thread.start()

        return True

    def get_result_df(self) -> DataFrame:
        """"""
        return self.result_df

    def get_result_statistics(self) -> dict | None:
        """"""
        return self.result_statistics

    def get_result_values(self) -> list | None:
        """"""
        return self.result_values

    def get_default_setting(self, class_name: str) -> dict:
        """"""
        strategy_class: type[CtaTemplate] = self.classes[class_name]
        setting: dict = strategy_class.get_class_parameters()
        return setting

    def run_optimization(
        self,
        class_name: str,
        vt_symbol: str,
        interval: str,
        start: datetime,
        end: datetime,
        rate: float,
        slippage: float,
        size: int,
        pricetick: float,
        capital: int,
        optimization_setting: OptimizationSetting,
        use_ga: bool,
        max_workers: int | None = None
    ) -> None:
        """"""
        self.result_values = None

        engine: BacktestingEngine = self.backtesting_engine
        engine.clear_data()

        if interval == Interval.TICK.value:
            mode: BacktestingMode = BacktestingMode.TICK
        else:
            mode = BacktestingMode.BAR

        engine.set_parameters(
            vt_symbol=vt_symbol,
            interval=interval,
            start=start,
            end=end,
            rate=rate,
            slippage=slippage,
            size=size,
            pricetick=pricetick,
            capital=capital,
            mode=mode
        )

        strategy_class: type[CtaTemplate] = self.classes[class_name]
        engine.add_strategy(
            strategy_class,
            {}
        )

        # 0则代表不限制
        if max_workers == 0:
            max_workers = None

        if use_ga:
            self.result_values = engine.run_ga_optimization(
                optimization_setting,
                output=False,
                max_workers=max_workers
            )
        else:
            self.result_values = engine.run_bf_optimization(
                optimization_setting,
                output=False,
                max_workers=max_workers
            )

        # Clear thread object handler.
        self.thread = None
        self.write_log(_("多进程参数优化完成"))

        # Put optimization done event
        event: Event = Event(EVENT_BACKTESTER_OPTIMIZATION_FINISHED)
        self.event_engine.put(event)

    def start_optimization(
        self,
        class_name: str,
        vt_symbol: str,
        interval: str,
        start: datetime,
        end: datetime,
        rate: float,
        slippage: float,
        size: int,
        pricetick: float,
        capital: int,
        optimization_setting: OptimizationSetting,
        use_ga: bool,
        max_workers: int
    ) -> bool:
        if self.thread:
            self.write_log(_("已有任务在运行中，请等待完成"))
            return False

        self.write_log("-" * 40)
        self.thread = Thread(
            target=self.run_optimization,
            args=(
                class_name,
                vt_symbol,
                interval,
                start,
                end,
                rate,
                slippage,
                size,
                pricetick,
                capital,
                optimization_setting,
                use_ga,
                max_workers
            )
        )
        self.thread.start()

        return True

    def run_downloading(
        self,
        vt_symbol: str,
        interval: str,
        start: datetime,
        end: datetime
    ) -> None:
        """
        执行下载任务
        """
        self.write_log(_("{}-{}开始下载历史数据").format(vt_symbol, interval))

        try:
            symbol, exchange = extract_vt_symbol(vt_symbol)
        except ValueError:
            self.write_log(_("{}解析失败，请检查交易所后缀").format(vt_symbol))
            self.thread = None
            return

        req: HistoryRequest = HistoryRequest(
            symbol=symbol,
            exchange=exchange,
            interval=Interval(interval),
            start=start,
            end=end
        )

        try:
            if interval == "tick":
                data: list[TickData] = self.datafeed.query_tick_history(req, self.write_log)
            else:
                contract: ContractData | None = self.main_engine.get_contract(vt_symbol)

                # If history data provided in gateway, then query
                if contract and contract.history_data:
                    data = self.main_engine.query_history(
                        req, contract.gateway_name
                    )
                # Otherwise use RQData to query data
                else:
                    data = self.datafeed.query_bar_history(req, self.write_log)

            if data:
                if interval == "tick":
                    self.database.save_tick_data(data)
                else:
                    self.database.save_bar_data(data)

                self.write_log(_("{}-{}历史数据下载完成").format(vt_symbol, interval))
            else:
                self.write_log(_("数据下载失败，无法获取{}的历史数据").format(vt_symbol))
        except Exception:
            msg: str = _("数据下载失败，触发异常：\n{}").format(traceback.format_exc())
            self.write_log(msg)

        # Clear thread object handler.
        self.thread = None

    def start_downloading(
        self,
        vt_symbol: str,
        interval: str,
        start: datetime,
        end: datetime
    ) -> bool:
        if self.thread:
            self.write_log(_("已有任务在运行中，请等待完成"))
            return False

        self.write_log("-" * 40)
        self.thread = Thread(
            target=self.run_downloading,
            args=(
                vt_symbol,
                interval,
                start,
                end
            )
        )
        self.thread.start()

        return True

    def get_all_trades(self) -> list:
        """"""
        trades: list = self.backtesting_engine.get_all_trades()
        return trades

    def get_all_orders(self) -> list:
        """"""
        orders: list = self.backtesting_engine.get_all_orders()
        return orders

    def get_all_daily_results(self) -> list:
        """"""
        results: list = self.backtesting_engine.get_all_daily_results()
        return results

    def get_history_data(self) -> list:
        """"""
        history_data: list = self.backtesting_engine.history_data
        return history_data

    def get_strategy_class_file(self, class_name: str) -> str:
        """"""
        strategy_class: type[CtaTemplate] = self.classes[class_name]
        file_path: str = getfile(strategy_class)
        return file_path
