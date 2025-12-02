import smtplib
import os
import time
import traceback
import atexit
from abc import ABC, abstractmethod
from email.message import EmailMessage
from queue import Empty, Queue
from threading import Thread
from typing import TypeVar
from collections.abc import Callable
from collections import deque
from copy import copy
import time

from vnpy.event import Event, EventEngine, EVENT_TIMER
from .app import BaseApp
from .event import (
    EVENT_TICK,
    EVENT_ORDER,
    EVENT_TRADE,
    EVENT_POSITION,
    EVENT_POSITION_VIEW,
    EVENT_ACCOUNT,
    EVENT_CONTRACT,
    EVENT_LOG,
    EVENT_QUOTE
)
from .gateway import BaseGateway
from .object import (
    CancelRequest,
    LogData,
    OrderRequest,
    QuoteData,
    QuoteRequest,
    SubscribeRequest,
    HistoryRequest,
    OrderData,
    BarData,
    TickData,
    TradeData,
    PositionData,
    AccountData,
    ContractData,
    Exchange
)
from .constant import Direction, Offset, Status
from .setting import SETTINGS
from .utility import TRADER_DIR
from .converter import OffsetConverter
from .logger import logger, DEBUG, INFO, WARNING, ERROR, CRITICAL
from .locale import _


EngineType = TypeVar("EngineType", bound="BaseEngine")


class BaseEngine(ABC):
    """
    Abstract class for implementing a function engine.
    """

    @abstractmethod
    def __init__(
        self,
        main_engine: "MainEngine",
        event_engine: EventEngine,
        engine_name: str,
    ) -> None:
        """"""
        self.main_engine: MainEngine = main_engine
        self.event_engine: EventEngine = event_engine
        self.engine_name: str = engine_name

    def close(self) -> None:
        """"""
        return


class MainEngine:
    """
    Acts as the core of the trading platform.
    """

    def __init__(self, event_engine: EventEngine | None = None) -> None:
        """"""
        if event_engine:
            self.event_engine: EventEngine = event_engine
        else:
            self.event_engine = EventEngine()
        self.event_engine.start()

        self.gateways: dict[str, BaseGateway] = {}
        self.engines: dict[str, BaseEngine] = {}
        self.apps: dict[str, BaseApp] = {}
        self.exchanges: list[Exchange] = []
        
        # 标记是否已关闭，避免重复关闭
        self._closed = False

        os.chdir(TRADER_DIR)    # Change working directory
        self.init_engines()     # Initialize function engines
        
        # 注册atexit清理函数，确保程序意外退出时也能清理资源
        atexit.register(self._cleanup_on_exit)

    def add_engine(self, engine_class: type[EngineType]) -> EngineType:
        """
        Add function engine.
        """
        engine: EngineType = engine_class(self, self.event_engine)      # type: ignore
        self.engines[engine.engine_name] = engine
        return engine

    def add_gateway(self, gateway_class: type[BaseGateway], gateway_name: str = "") -> BaseGateway:
        """
        Add gateway.
        """
        # Use default name if gateway_name not passed
        if not gateway_name:
            gateway_name = gateway_class.default_name

        gateway: BaseGateway = gateway_class(self.event_engine, gateway_name)
        self.gateways[gateway_name] = gateway

        # Add gateway supported exchanges into engine
        for exchange in gateway.exchanges:
            if exchange not in self.exchanges:
                self.exchanges.append(exchange)

        return gateway

    def add_app(self, app_class: type[BaseApp]) -> BaseEngine:
        """
        Add app.
        """
        app: BaseApp = app_class()
        self.apps[app.app_name] = app

        engine: BaseEngine = self.add_engine(app.engine_class)
        return engine

    def init_engines(self) -> None:
        """
        Init all engines.
        """
        self.add_engine(LogEngine)

        oms_engine: OmsEngine = self.add_engine(OmsEngine)
        self.get_tick: Callable[[str], TickData | None] = oms_engine.get_tick
        self.get_order: Callable[[str], OrderData | None] = oms_engine.get_order
        self.get_trade: Callable[[str], TradeData | None] = oms_engine.get_trade
        self.get_position: Callable[[str], PositionData | None] = oms_engine.get_position
        self.get_account: Callable[[str], AccountData | None] = oms_engine.get_account
        self.get_contract: Callable[[str], ContractData | None] = oms_engine.get_contract
        self.get_quote: Callable[[str], QuoteData | None] = oms_engine.get_quote
        self.get_all_ticks: Callable[[], list[TickData]] = oms_engine.get_all_ticks
        self.get_all_orders: Callable[[], list[OrderData]] = oms_engine.get_all_orders
        self.get_all_trades: Callable[[], list[TradeData]] = oms_engine.get_all_trades
        self.get_all_positions: Callable[[], list[PositionData]] = oms_engine.get_all_positions
        self.get_all_accounts: Callable[[], list[AccountData]] = oms_engine.get_all_accounts
        self.get_all_contracts: Callable[[], list[ContractData]] = oms_engine.get_all_contracts
        self.get_all_quotes: Callable[[], list[QuoteData]] = oms_engine.get_all_quotes
        self.get_all_active_orders: Callable[[], list[OrderData]] = oms_engine.get_all_active_orders
        self.get_all_active_quotes: Callable[[], list[QuoteData]] = oms_engine.get_all_active_quotes
        self.update_order_request: Callable[[OrderRequest, str, str], None] = oms_engine.update_order_request
        self.convert_order_request: Callable[[OrderRequest, str, bool, bool], list[OrderRequest]] = oms_engine.convert_order_request
        self.get_converter: Callable[[str], OffsetConverter | None] = oms_engine.get_converter

        email_engine: EmailEngine = self.add_engine(EmailEngine)
        self.send_email: Callable[[str, str, str | None], None] = email_engine.send_email

    def write_log(self, msg: str, source: str = "MainEngine") -> None:
        """
        Put log event with specific message.
        """
        log: LogData = LogData(msg=msg, gateway_name=source)
        event: Event = Event(EVENT_LOG, log)
        self.event_engine.put(event)

    def get_gateway(self, gateway_name: str) -> BaseGateway | None:
        """
        Return gateway object by name.
        """
        gateway: BaseGateway | None = self.gateways.get(gateway_name, None)
        if not gateway:
            self.write_log(_("找不到底层接口：{}").format(gateway_name))
        return gateway

    def get_engine(self, engine_name: str) -> BaseEngine | None:
        """
        Return engine object by name.
        """
        engine: BaseEngine | None = self.engines.get(engine_name, None)
        if not engine:
            self.write_log(_("找不到引擎：{}").format(engine_name))
        return engine

    def get_default_setting(self, gateway_name: str) -> dict[str, str | bool | int | float] | None:
        """
        Get default setting dict of a specific gateway.
        """
        gateway: BaseGateway | None = self.get_gateway(gateway_name)
        if gateway:
            return gateway.get_default_setting()
        return None

    def get_all_gateway_names(self) -> list[str]:
        """
        Get all names of gateway added in main engine.
        """
        return list(self.gateways.keys())

    def get_all_apps(self) -> list[BaseApp]:
        """
        Get all app objects.
        """
        return list(self.apps.values())

    def get_all_exchanges(self) -> list[Exchange]:
        """
        Get all exchanges.
        """
        return self.exchanges

    def connect(self, setting: dict, gateway_name: str) -> None:
        """
        Start connection of a specific gateway.
        """
        gateway: BaseGateway | None = self.get_gateway(gateway_name)
        if gateway:
            self.write_log(_("连接登录 -> {}").format(gateway_name))

            gateway.connect(setting)

    def subscribe(self, req: SubscribeRequest, gateway_name: str) -> None:
        """
        Subscribe tick data update of a specific gateway.
        """
        gateway: BaseGateway | None = self.get_gateway(gateway_name)
        if gateway:
            self.write_log(_("订阅行情 -> {}：{}").format(gateway_name, req))

            gateway.subscribe(req)

    def send_order(self, req: OrderRequest, gateway_name: str) -> str:
        """
        Send new order request to a specific gateway.
        """
        gateway: BaseGateway | None = self.get_gateway(gateway_name)
        if gateway:
            self.write_log(_("委托下单 -> {}：{}").format(gateway_name, req))

            return gateway.send_order(req)
        else:
            return ""

    def cancel_order(self, req: CancelRequest, gateway_name: str) -> None:
        """
        Send cancel order request to a specific gateway.
        """
        gateway: BaseGateway | None = self.get_gateway(gateway_name)
        if gateway:
            self.write_log(_("委托撤单 -> {}：{}").format(gateway_name, req))

            gateway.cancel_order(req)

    def send_quote(self, req: QuoteRequest, gateway_name: str) -> str:
        """
        Send new quote request to a specific gateway.
        """
        gateway: BaseGateway | None = self.get_gateway(gateway_name)
        if gateway:
            self.write_log(_("报价下单 -> {}：{}").format(gateway_name, req))

            return gateway.send_quote(req)
        else:
            return ""

    def cancel_quote(self, req: CancelRequest, gateway_name: str) -> None:
        """
        Send cancel quote request to a specific gateway.
        """
        gateway: BaseGateway | None = self.get_gateway(gateway_name)
        if gateway:
            self.write_log(_("报价撤单 -> {}：{}").format(gateway_name, req))

            gateway.cancel_quote(req)

    def query_history(self, req: HistoryRequest, gateway_name: str) -> list[BarData]:
        """
        Query bar history data from a specific gateway.
        """
        gateway: BaseGateway | None = self.get_gateway(gateway_name)
        if gateway:
            self.write_log(_("查询K线 -> {}：{}").format(gateway_name, req))

            return gateway.query_history(req)
        else:
            return []

    def close(self) -> None:
        """
        Make sure every gateway and app is closed properly before
        programme exit.
        """
        # 标记已关闭，避免重复关闭
        if hasattr(self, '_closed') and self._closed:
            return
        self._closed = True
        
        # Stop event engine first to prevent new timer event.
        try:
            self.event_engine.stop()
        except Exception as e:
            try:
                self.write_log(f"停止事件引擎时出错: {e}")
            except Exception:
                pass  # 如果write_log也失败，静默忽略

        # Close all gateway connections to prevent connection leaks
        for gateway_name, gateway in self.gateways.items():
            try:
                if gateway and hasattr(gateway, 'close'):
                    gateway.close()
                    try:
                        self.write_log(f"Gateway连接已关闭: {gateway_name}")
                    except Exception:
                        pass
            except Exception as e:
                try:
                    self.write_log(f"关闭Gateway连接时出错 ({gateway_name}): {e}")
                except Exception:
                    pass  # 如果write_log也失败，静默忽略

        # Close all engine connections
        for engine_name, engine in self.engines.items():
            try:
                if engine and hasattr(engine, 'close'):
                    engine.close()
            except Exception as e:
                try:
                    self.write_log(f"关闭Engine连接时出错 ({engine_name}): {e}")
                except Exception:
                    pass  # 如果write_log也失败，静默忽略

        # Close datafeed connection to prevent connection leaks
        try:
            from vnpy.trader.datafeed import get_datafeed
            datafeed = get_datafeed()
            if datafeed and hasattr(datafeed, 'close'):
                datafeed.close()
                try:
                    self.write_log("[MainEngine] 全局Datafeed连接已关闭")
                except Exception:
                    pass
        except Exception as e:
            try:
                self.write_log(f"关闭Datafeed连接时出错: {e}")
            except Exception:
                pass  # 如果write_log也失败，静默忽略

        # Close database connection if it has a close method
        try:
            from vnpy.trader.database import get_database
            database = get_database()
            if database and hasattr(database, 'close'):
                database.close()
                try:
                    self.write_log("数据库连接已关闭")
                except Exception:
                    pass
        except Exception as e:
            try:
                self.write_log(f"关闭数据库连接时出错: {e}")
            except Exception:
                pass  # 如果write_log也失败，静默忽略
    
    def _cleanup_on_exit(self) -> None:
        """
        程序退出时的清理函数（由atexit注册调用）。
        确保即使程序意外退出，也能清理所有资源。
        """
        # 如果已经正常关闭，不再重复清理
        if hasattr(self, '_closed') and self._closed:
            return
        
        # 静默清理，避免在退出时产生异常
        try:
            # 停止事件引擎
            if hasattr(self, 'event_engine') and self.event_engine:
                try:
                    self.event_engine.stop()
                except Exception:
                    pass
            
            # 关闭所有gateway连接
            if hasattr(self, 'gateways'):
                for gateway_name, gateway in self.gateways.items():
                    try:
                        if gateway and hasattr(gateway, 'close'):
                            gateway.close()
                    except Exception:
                        pass  # 静默忽略错误
            
            # 关闭所有engine连接
            if hasattr(self, 'engines'):
                for engine_name, engine in self.engines.items():
                    try:
                        if engine and hasattr(engine, 'close'):
                            engine.close()
                    except Exception:
                        pass  # 静默忽略错误
            
            # 关闭datafeed连接
            try:
                from vnpy.trader.datafeed import get_datafeed
                datafeed = get_datafeed()
                if datafeed and hasattr(datafeed, 'close'):
                    datafeed.close()
            except Exception:
                pass  # 静默忽略错误
            
            # 关闭数据库连接
            try:
                from vnpy.trader.database import get_database
                database = get_database()
                if database and hasattr(database, 'close'):
                    database.close()
            except Exception:
                pass  # 静默忽略错误
        except Exception:
            pass  # 静默忽略所有错误，确保程序能够正常退出


class LogEngine(BaseEngine):
    """
    Provides log event output function.
    """

    level_map: dict[int, str] = {
        DEBUG: "DEBUG",
        INFO: "INFO",
        WARNING: "WARNING",
        ERROR: "ERROR",
        CRITICAL: "CRITICAL",
    }

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        """"""
        super().__init__(main_engine, event_engine, "log")

        self.active = SETTINGS["log.active"]

        self.register_log(EVENT_LOG)

    def process_log_event(self, event: Event) -> None:
        """Process log event"""
        if not self.active:
            return

        log: LogData = event.data
        level: str | int = self.level_map.get(log.level, log.level)
        logger.log(level, log.msg, gateway_name=log.gateway_name)

    def register_log(self, event_type: str) -> None:
        """Register log event handler"""
        self.event_engine.register(event_type, self.process_log_event)


class OmsEngine(BaseEngine):
    """
    Provides order management system function.
    """

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        """"""
        super().__init__(main_engine, event_engine, "oms")

        self.ticks: dict[str, TickData] = {}
        self.orders: dict[str, OrderData] = {}
        self.trades: dict[str, TradeData] = {}
        self.positions: dict[str, PositionData] = {}
        self.accounts: dict[str, AccountData] = {}
        self.contracts: dict[str, ContractData] = {}
        self.quotes: dict[str, QuoteData] = {}

        self.active_orders: dict[str, OrderData] = {}
        self.active_quotes: dict[str, QuoteData] = {}
        
        # Track previous order status to detect status changes
        self.previous_order_status: dict[str, Status] = {}

        self.offset_converters: dict[str, OffsetConverter] = {}

        self.refresh_queue: deque[str] = deque()
        self.refresh_symbols: set[str] = set()
        self.last_view_emit: dict[str, float] = {}
        self.refresh_batch_size: int = 5
        self.refresh_interval: float = 0.0
        self.close_offsets: set[Offset] = {
            Offset.CLOSE,
            Offset.CLOSETODAY,
            Offset.CLOSEYESTERDAY,
        }
        self.position_view_enabled: bool = SETTINGS.get("position.view.enabled", False)
        self.position_view_emit_legacy: bool = SETTINGS.get("position.view.emit_legacy", True)
        self.position_view_debug: bool = SETTINGS.get("position.view.debug", False)
        
        # Track removed positions to avoid processing gateway's repeated zero-volume events
        self.removed_positions: set[str] = set()
        
        # Low-frequency tick logging (every N seconds per symbol, only when position exists)
        self.tick_log_interval: float = 30.0  # Increased to 30 seconds to reduce log spam
        self.last_tick_log: dict[str, float] = {}
        self._last_timer_log: float = 0.0

        self.register_event()

    def register_event(self) -> None:
        """"""
        self.event_engine.register(EVENT_TICK, self.process_tick_event)
        self.event_engine.register(EVENT_ORDER, self.process_order_event)
        self.event_engine.register(EVENT_TRADE, self.process_trade_event)
        self.event_engine.register(EVENT_POSITION, self.process_position_event)
        self.event_engine.register(EVENT_ACCOUNT, self.process_account_event)
        self.event_engine.register(EVENT_CONTRACT, self.process_contract_event)
        self.event_engine.register(EVENT_QUOTE, self.process_quote_event)
        if self.position_view_enabled:
            self.event_engine.register(EVENT_TIMER, self.process_timer_event)

    def process_tick_event(self, event: Event) -> None:
        """"""
        tick: TickData = event.data
        self.ticks[tick.vt_symbol] = tick

        # Low-frequency tick logging (only when position exists, every N seconds per symbol)
        if self.position_view_enabled:
            has_position: bool = self._has_position_for_symbol(tick.vt_symbol)
            # Also check continuous contract mapping
            if not has_position:
                for position in self.positions.values():
                    if (position.volume > 0 and 
                        position.exchange == tick.exchange and
                        position.vt_symbol != tick.vt_symbol):
                        common_prefix_len = min(len(tick.symbol), len(position.symbol), 3)
                        if (tick.symbol[:common_prefix_len] == position.symbol[:common_prefix_len] and
                            (tick.symbol.startswith(position.symbol[:3]) or 
                             position.symbol.startswith(tick.symbol[:3]))):
                            has_position = True
                            break
            
            if has_position:
                current_time: float = time.time()
                last_log_time: float = self.last_tick_log.get(tick.vt_symbol, 0.0)
                if current_time - last_log_time >= self.tick_log_interval:
                    self.last_tick_log[tick.vt_symbol] = current_time
                    self.main_engine.write_log(
                        f"[Tick] {tick.vt_symbol} last={tick.last_price} ask1={tick.ask_price_1} bid1={tick.bid_price_1} volume={tick.volume}",
                        "OmsEngine"
                    )

        if not self.position_view_enabled:
            return

        # Check direct match
        if self._has_position_for_symbol(tick.vt_symbol):
            self._enqueue_refresh_symbol(tick.vt_symbol)
        
        # Check continuous contract mapping (bidirectional)
        # Case 1: MHI2511 tick -> MHImain position (tick is specific, position is continuous)
        # Case 2: MHImain tick -> MHI2511 position (tick is continuous, position is specific)
        for position in self.positions.values():
            if (position.volume > 0 and 
                position.exchange == tick.exchange and
                position.vt_symbol != tick.vt_symbol):
                # Check if symbols share common prefix (at least 3 characters)
                common_prefix_len = min(len(tick.symbol), len(position.symbol), 3)
                if (tick.symbol[:common_prefix_len] == position.symbol[:common_prefix_len] and
                    (tick.symbol.startswith(position.symbol[:3]) or 
                     position.symbol.startswith(tick.symbol[:3]))):
                    self._enqueue_refresh_symbol(position.vt_symbol)
                    if self.position_view_debug:
                        self.main_engine.write_log(
                            f"[PositionView] tick {tick.vt_symbol} triggers refresh for position {position.vt_symbol}",
                            "OmsEngine"
                        )

    def process_order_event(self, event: Event) -> None:
        """"""
        order: OrderData = event.data
        previous_status: Status | None = self.previous_order_status.get(order.vt_orderid)
        self.orders[order.vt_orderid] = order

        # Check if status changed to "全部成交" (only generate trade event on status change)
        status_changed_to_filled: bool = (
            order.status == Status.ALLTRADED and 
            previous_status is not None and 
            previous_status != Status.ALLTRADED
        )
        
        # Update previous status
        self.previous_order_status[order.vt_orderid] = order.status

        # Only log and generate trade event if status just changed to ALLTRADED (not historical orders)
        if status_changed_to_filled:
            # Log order status change to fully filled
            self.main_engine.write_log(
                f"[OmsEngine] 订单全部成交: {order.vt_symbol} {order.direction} {order.traded}/{order.volume} "
                f"orderid={order.orderid} status={order.status.value}",
                "OmsEngine"
            )
            
            # Check if we already have trade records for this order
            has_trade: bool = False
            for trade in self.trades.values():
                if trade.vt_orderid == order.vt_orderid:
                    has_trade = True
                    break
            
            # If no trade event received, create synthetic trade event
            if not has_trade and order.traded > 0 and order.direction:
                from datetime import datetime
                synthetic_trade: TradeData = TradeData(
                    symbol=order.symbol,
                    exchange=order.exchange,
                    orderid=order.orderid,
                    tradeid=f"{order.orderid}_filled",  # Synthetic tradeid
                    direction=order.direction,
                    offset=order.offset,
                    price=order.price,  # Use order price as average fill price
                    volume=order.traded,  # Use traded volume
                    datetime=order.datetime or datetime.now(),
                    gateway_name=order.gateway_name,
                )
                
                # Trigger trade event to update position
                trade_event: Event = Event(EVENT_TRADE, synthetic_trade)
                self.event_engine.put(trade_event)
                
                self.main_engine.write_log(
                    f"[OmsEngine] 自动生成成交事件: {synthetic_trade.vt_symbol} {synthetic_trade.direction} "
                    f"{synthetic_trade.volume}@{synthetic_trade.price}",
                    "OmsEngine"
                )

        # If order is active, then update data in dict.
        if order.is_active():
            self.active_orders[order.vt_orderid] = order
        # Otherwise, pop inactive order from in dict
        elif order.vt_orderid in self.active_orders:
            self.active_orders.pop(order.vt_orderid)

        # Update to offset converter
        converter: OffsetConverter | None = self.offset_converters.get(order.gateway_name, None)
        if converter:
            converter.update_order(order)

    def process_trade_event(self, event: Event) -> None:
        """"""
        trade: TradeData = event.data
        self.trades[trade.vt_tradeid] = trade

        # Always log trade event to confirm it's received
        self.main_engine.write_log(
            f"[OmsEngine] 收到成交事件: {trade.vt_symbol} {trade.direction} {trade.volume}@{trade.price} "
            f"orderid={trade.orderid} tradeid={trade.tradeid}",
            "OmsEngine"
        )

        # Update to offset converter
        converter: OffsetConverter | None = self.offset_converters.get(trade.gateway_name, None)
        if converter:
            converter.update_trade(trade)

        if self.position_view_enabled:
            self._apply_trade_to_position(trade)
        else:
            self.main_engine.write_log(
                f"[OmsEngine] position.view.enabled=False, 跳过持仓合并",
                "OmsEngine"
            )

    def process_position_event(self, event: Event) -> None:
        """"""
        position: PositionData = event.data
        
        old_position: PositionData | None = self.positions.get(position.vt_positionid)
        
        # If this position was already removed and gateway keeps pushing zero-volume events, ignore them
        if position.vt_positionid in self.removed_positions:
            if position.volume <= 0:
                # Already removed and still zero volume, ignore to avoid flickering
                return
            else:
                # Position was removed but gateway pushes volume > 0
                # This is likely a stale gateway update after we closed the position
                # Ignore it to avoid re-opening closed positions
                # Only allow if old_position exists and has volume > 0 (meaning it was never actually removed)
                if old_position and old_position.volume > 0:
                    # Position still exists with volume > 0, remove from removed set and process normally
                    self.removed_positions.discard(position.vt_positionid)
                else:
                    # This is a stale gateway update, ignore it
                    self.main_engine.write_log(
                        f"[OmsEngine] process_position_event: ignoring stale gateway update for {position.vt_positionid} "
                        f"(removed but gateway pushed volume={position.volume})",
                        "OmsEngine"
                    )
                    return
        
        # Update position data
        self.positions[position.vt_positionid] = position
        
        if self.position_view_enabled and old_position:
            # When position view is enabled, preserve our calculated PnL if it exists
            # Gateway may push outdated or incorrect PnL values
            gateway_pnl: float = position.pnl
            calculated_pnl: float = old_position.pnl
            
            # Check if we have a recently calculated PnL (within last 5 seconds)
            last_emit_time: float = self.last_view_emit.get(position.vt_positionid, 0.0)
            current_time: float = time.time()
            has_recent_calculation: bool = (current_time - last_emit_time) < 5.0
            
            # If we have a recent calculation and gateway PnL differs significantly, preserve calculated PnL
            if has_recent_calculation and abs(gateway_pnl - calculated_pnl) > 1e-6:
                self.positions[position.vt_positionid].pnl = calculated_pnl
                # 注释保留计算盈亏日志，减少日志输出（每秒触发多次）
                # self.main_engine.write_log(
                #     f"[OmsEngine] process_position_event: preserved calculated pnl={calculated_pnl} for {position.vt_positionid} "
                #     f"(gateway pushed pnl={gateway_pnl}, time_since_calc={current_time - last_emit_time:.1f}s)",
                #     "OmsEngine"
                # )

        if self.position_view_debug:
            self.main_engine.write_log(
                f"[PositionView] gateway push {position.vt_positionid} "
                f"volume={position.volume} price={position.price} pnl={position.pnl} frozen={position.frozen}",
                "OmsEngine"
            )

        if self.position_view_enabled:
            # Get the current position (may have preserved PnL)
            current_position: PositionData = self.positions[position.vt_positionid]
            
            # If position is already closed (volume = 0) and we've already processed it, skip to avoid spam
            if current_position.volume <= 0:
                # Check if we already removed this position (to avoid duplicate processing)
                if position.vt_positionid not in self.positions:
                    # Already removed, skip
                    return
                # Remove it and emit zero-volume event (only once)
                del self.positions[position.vt_positionid]
                self.removed_positions.add(position.vt_positionid)  # Mark as removed
                current_position.volume = 0.0
                current_position.frozen = 0.0  # Also clear frozen to avoid showing as frozen
                self._emit_position_view(current_position)
                return
            
            # Check if both LONG and SHORT positions exist for the same symbol (shouldn't happen in net position mode)
            # This might happen if gateway pushes incorrect position data
            long_positionid: str = f"{position.gateway_name}.{position.vt_symbol}.{Direction.LONG.value}"
            short_positionid: str = f"{position.gateway_name}.{position.vt_symbol}.{Direction.SHORT.value}"
            long_pos: PositionData | None = self.positions.get(long_positionid)
            short_pos: PositionData | None = self.positions.get(short_positionid)
            
            if long_pos and short_pos and long_pos.volume > 0 and short_pos.volume > 0:
                # Both positions exist - this shouldn't happen in net position mode
                # Check contract to see if it uses net position
                contract: ContractData | None = self.contracts.get(position.vt_symbol)
                if contract and contract.net_position:
                    # Net position mode: merge positions
                    net_volume: float = long_pos.volume - short_pos.volume
                    if abs(net_volume) < 1e-6:
                        # Net position is zero, remove both
                        if long_positionid in self.positions:
                            del self.positions[long_positionid]
                            self.removed_positions.add(long_positionid)
                        if short_positionid in self.positions:
                            del self.positions[short_positionid]
                            self.removed_positions.add(short_positionid)
                        self.main_engine.write_log(
                            f"[OmsEngine] process_position_event: removed both positions (net volume=0) for {position.vt_symbol}",
                            "OmsEngine"
                        )
                        # Emit zero-volume events
                        long_pos.volume = 0.0
                        long_pos.frozen = 0.0
                        short_pos.volume = 0.0
                        short_pos.frozen = 0.0
                        self._emit_position_view(long_pos)
                        self._emit_position_view(short_pos)
                        return
                    elif net_volume > 0:
                        # Net long position
                        long_pos.volume = net_volume
                        if short_positionid in self.positions:
                            del self.positions[short_positionid]
                            self.removed_positions.add(short_positionid)
                        self.main_engine.write_log(
                            f"[OmsEngine] process_position_event: merged positions to net LONG {net_volume} for {position.vt_symbol}",
                            "OmsEngine"
                        )
                        short_pos.volume = 0.0
                        short_pos.frozen = 0.0
                        self._emit_position_view(short_pos)
                        current_position = long_pos
                    else:
                        # Net short position
                        short_pos.volume = abs(net_volume)
                        if long_positionid in self.positions:
                            del self.positions[long_positionid]
                            self.removed_positions.add(long_positionid)
                        self.main_engine.write_log(
                            f"[OmsEngine] process_position_event: merged positions to net SHORT {abs(net_volume)} for {position.vt_symbol}",
                            "OmsEngine"
                        )
                        long_pos.volume = 0.0
                        long_pos.frozen = 0.0
                        self._emit_position_view(long_pos)
                        current_position = short_pos
                else:
                    # Not net position mode, but both exist - log warning
                    self.main_engine.write_log(
                        f"[OmsEngine] process_position_event: WARNING - both LONG and SHORT positions exist for {position.vt_symbol} "
                        f"(LONG={long_pos.volume}, SHORT={short_pos.volume})",
                        "OmsEngine"
                    )
            
            # Process normal position update (volume > 0)
                # Only emit view if data actually changed (to avoid flickering)
                should_emit: bool = True
                if old_position:
                    # Check if key fields changed
                    if (abs(old_position.volume - current_position.volume) < 1e-6 and
                        abs(old_position.price - current_position.price) < 1e-6 and
                        abs(old_position.frozen - current_position.frozen) < 1e-6 and
                        abs(old_position.pnl - current_position.pnl) < 1e-6):
                        should_emit = False
                        if self.position_view_debug:
                            self.main_engine.write_log(
                                f"[PositionView] skip emit (no change) for {position.vt_positionid}",
                                "OmsEngine"
                            )
                
                if should_emit:
                    self._emit_position_view(current_position)
                self._enqueue_refresh_symbol(position.vt_symbol)

        # Update to offset converter
        converter: OffsetConverter | None = self.offset_converters.get(position.gateway_name, None)
        if converter:
            converter.update_position(position)

    def process_account_event(self, event: Event) -> None:
        """"""
        account: AccountData = event.data
        self.accounts[account.vt_accountid] = account

    def process_contract_event(self, event: Event) -> None:
        """"""
        contract: ContractData = event.data
        self.contracts[contract.vt_symbol] = contract

        # Initialize offset converter for each gateway
        if contract.gateway_name not in self.offset_converters:
            self.offset_converters[contract.gateway_name] = OffsetConverter(self)

    def process_quote_event(self, event: Event) -> None:
        """"""
        quote: QuoteData = event.data
        self.quotes[quote.vt_quoteid] = quote

        # If quote is active, then update data in dict.
        if quote.is_active():
            self.active_quotes[quote.vt_quoteid] = quote
        # Otherwise, pop inactive quote from in dict
        elif quote.vt_quoteid in self.active_quotes:
            self.active_quotes.pop(quote.vt_quoteid)

    def process_timer_event(self, event: Event) -> None:
        """"""
        if self.position_view_enabled:
            self._refresh_positions()

    def get_tick(self, vt_symbol: str) -> TickData | None:
        """
        Get latest market tick data by vt_symbol.
        """
        return self.ticks.get(vt_symbol, None)

    def get_order(self, vt_orderid: str) -> OrderData | None:
        """
        Get latest order data by vt_orderid.
        """
        return self.orders.get(vt_orderid, None)

    def get_trade(self, vt_tradeid: str) -> TradeData | None:
        """
        Get trade data by vt_tradeid.
        """
        return self.trades.get(vt_tradeid, None)

    def get_position(self, vt_positionid: str) -> PositionData | None:
        """
        Get latest position data by vt_positionid.
        """
        return self.positions.get(vt_positionid, None)

    def get_account(self, vt_accountid: str) -> AccountData | None:
        """
        Get latest account data by vt_accountid.
        """
        return self.accounts.get(vt_accountid, None)

    def get_contract(self, vt_symbol: str) -> ContractData | None:
        """
        Get contract data by vt_symbol.
        """
        return self.contracts.get(vt_symbol, None)

    def get_quote(self, vt_quoteid: str) -> QuoteData | None:
        """
        Get latest quote data by vt_orderid.
        """
        return self.quotes.get(vt_quoteid, None)

    def get_all_ticks(self) -> list[TickData]:
        """
        Get all tick data.
        """
        return list(self.ticks.values())

    def get_all_orders(self) -> list[OrderData]:
        """
        Get all order data.
        """
        return list(self.orders.values())

    def get_all_trades(self) -> list[TradeData]:
        """
        Get all trade data.
        """
        return list(self.trades.values())

    def get_all_positions(self) -> list[PositionData]:
        """
        Get all position data.
        """
        return list(self.positions.values())

    def get_all_accounts(self) -> list[AccountData]:
        """
        Get all account data.
        """
        return list(self.accounts.values())

    def get_all_contracts(self) -> list[ContractData]:
        """
        Get all contract data.
        """
        return list(self.contracts.values())

    def get_all_quotes(self) -> list[QuoteData]:
        """
        Get all quote data.
        """
        return list(self.quotes.values())

    def get_all_active_orders(self) -> list[OrderData]:
        """
        Get all active orders.
        """
        return list(self.active_orders.values())

    def get_all_active_quotes(self) -> list[QuoteData]:
        """
        Get all active quotes.
        """
        return list(self.active_quotes.values())

    def update_order_request(self, req: OrderRequest, vt_orderid: str, gateway_name: str) -> None:
        """
        Update order request to offset converter.
        """
        converter: OffsetConverter | None = self.offset_converters.get(gateway_name, None)
        if converter:
            converter.update_order_request(req, vt_orderid)

    def convert_order_request(
        self,
        req: OrderRequest,
        gateway_name: str,
        lock: bool,
        net: bool = False
    ) -> list[OrderRequest]:
        """
        Convert original order request according to given mode.
        """
        converter: OffsetConverter | None = self.offset_converters.get(gateway_name, None)
        if not converter:
            return [req]

        reqs: list[OrderRequest] = converter.convert_order_request(req, lock, net)
        return reqs

    def get_converter(self, gateway_name: str) -> OffsetConverter | None:
        """
        Get offset converter object of specific gateway.
        """
        return self.offset_converters.get(gateway_name, None)

    def _enqueue_refresh_symbol(self, vt_symbol: str) -> None:
        """
        Put symbol into refresh queue for deferred pnl calculation.
        """
        if (
            not self.position_view_enabled
            or not vt_symbol
            or vt_symbol in self.refresh_symbols
        ):
            if self.position_view_debug:
                self.main_engine.write_log(
                    f"[PositionView] skip enqueue {vt_symbol} (enabled={self.position_view_enabled}, "
                    f"in_queue={vt_symbol in self.refresh_symbols})",
                    "OmsEngine"
                )
            return

        self.refresh_symbols.add(vt_symbol)
        self.refresh_queue.append(vt_symbol)
        
        if self.position_view_debug:
            self.main_engine.write_log(
                f"[PositionView] enqueued refresh for {vt_symbol} (queue_size={len(self.refresh_queue)})",
                "OmsEngine"
            )

    def _refresh_positions(self) -> None:
        """
        Batch refresh queued symbols to update position pnl.
        """
        if not self.position_view_enabled:
            return
            
        if not self.refresh_queue:
            return

        count: int = min(self.refresh_batch_size, len(self.refresh_queue))
        if self.position_view_debug and count > 0:
            self.main_engine.write_log(
                f"[PositionView] _refresh_positions processing {count} symbols from queue (total={len(self.refresh_queue)})",
                "OmsEngine"
            )
            
        for _ in range(count):
            vt_symbol: str = self.refresh_queue.popleft()
            self.refresh_symbols.discard(vt_symbol)
            self._refresh_symbol_positions(vt_symbol)

    def _find_tick_for_position(self, position: PositionData) -> TickData | None:
        """
        Find matching tick for position, supporting continuous contract mapping.
        Supports bidirectional mapping:
        - MHI2511.SEHK position -> MHImain.SEHK tick (specific to continuous)
        - MHImain.SEHK position -> MHI2511.SEHK tick (continuous to specific)
        """
        # First try direct match
        tick: TickData | None = self.ticks.get(position.vt_symbol)
        if tick:
            return tick
        
        # Try to find tick by product code prefix (bidirectional)
        symbol: str = position.symbol
        exchange: Exchange = position.exchange
        
        # Try to find tick that shares common prefix (at least 3 characters)
        # Case 1: position is specific (MHI2511), tick is continuous (MHImain)
        # Case 2: position is continuous (MHImain), tick is specific (MHI2511)
        for tick_vt_symbol, candidate_tick in self.ticks.items():
            if (candidate_tick.exchange == exchange and
                candidate_tick.vt_symbol != position.vt_symbol):
                # Check if symbols share common prefix
                common_prefix_len = min(len(symbol), len(candidate_tick.symbol), 3)
                prefix_match = symbol[:common_prefix_len] == candidate_tick.symbol[:common_prefix_len]
                startswith_match = (candidate_tick.symbol.startswith(symbol[:3]) or
                                   symbol.startswith(candidate_tick.symbol[:3]))
                
                if prefix_match and startswith_match:
                    if self.position_view_debug:
                        self.main_engine.write_log(
                            f"[PositionView] mapped {position.vt_symbol} -> {tick_vt_symbol}",
                            "OmsEngine"
                        )
                    return candidate_tick
        
        return None

    def _refresh_symbol_positions(self, vt_symbol: str) -> None:
        """
        Recalculate pnl for positions under specific symbol.
        Supports continuous contract mapping (e.g., MHImain -> MHI2511).
        """
        # Get tick that triggered this refresh
        trigger_tick: TickData | None = self.ticks.get(vt_symbol)
        
        if self.position_view_debug:
            self.main_engine.write_log(
                f"[PositionView] _refresh_symbol_positions called for {vt_symbol}, trigger_tick={trigger_tick.vt_symbol if trigger_tick else None}",
                "OmsEngine"
            )
        
        # Refresh all positions that match this symbol or can be mapped to the tick
        positions_checked: int = 0
        positions_matched: int = 0
        for vt_positionid, position in list(self.positions.items()):
            positions_checked += 1
            if position.volume <= 0:
                continue
                
            # Check if this position should be refreshed
            tick: TickData | None = None
            
            if position.vt_symbol == vt_symbol:
                # Direct match: use trigger tick if available, otherwise try to find mapped tick
                if trigger_tick:
                    tick = trigger_tick
                    positions_matched += 1
                else:
                    # No direct tick, try to find mapped tick (e.g., MHI2511 position -> MHImain tick)
                    tick = self._find_tick_for_position(position)
                    if not tick:
                        if self.position_view_debug:
                            self.main_engine.write_log(
                                f"[PositionView] no tick found for position {vt_positionid}, skipping",
                                "OmsEngine"
                            )
                        continue
                    positions_matched += 1
            elif trigger_tick:
                # Check if position symbol maps to trigger tick (continuous contract)
                # e.g., MHImain position with MHI2511 tick, or MHI2511 position with MHImain tick
                if (position.exchange == trigger_tick.exchange and
                    (trigger_tick.symbol.startswith(position.symbol[:3]) or
                     position.symbol.startswith(trigger_tick.symbol[:3]))):
                    tick = trigger_tick
                    positions_matched += 1
                else:
                    continue
            else:
                # No trigger tick, try to find tick for this position (e.g., MHI2511 position -> MHImain tick)
                tick = self._find_tick_for_position(position)
                if not tick:
                    if self.position_view_debug:
                        self.main_engine.write_log(
                            f"[PositionView] no tick found for position {vt_positionid}, skipping",
                            "OmsEngine"
                        )
                    continue
                positions_matched += 1
            
            if not tick:
                if self.position_view_debug:
                    self.main_engine.write_log(
                        f"[PositionView] no tick for position {vt_positionid} (symbol={position.vt_symbol})",
                        "OmsEngine"
                    )
                continue
            
            # 注释持仓处理日志，减少日志输出（持仓刷新每秒触发，日志过于频繁）
            # self.main_engine.write_log(
            #     f"[OmsEngine] _refresh_symbol_positions: processing position {vt_positionid} (symbol={position.vt_symbol}, volume={position.volume}, price={position.price}) with tick {tick.vt_symbol} (last={tick.last_price})",
            #     "OmsEngine"
            # )

            # Get contract size
            contract: ContractData | None = self.contracts.get(position.vt_symbol)
            if not contract:
                contract = self.contracts.get(tick.vt_symbol)
            size: float = contract.size if contract else 1
            
            if not contract:
                if self.position_view_debug:
                    self.main_engine.write_log(
                        f"[PositionView] WARNING - no contract found for {position.vt_symbol} or {tick.vt_symbol}, using default size=1",
                        "OmsEngine"
                    )

            pnl: float | None = self._calculate_position_pnl(position, tick, size)
            if pnl is None:
                if self.position_view_debug:
                    self.main_engine.write_log(
                        f"[PositionView] pnl calculation returned None for {vt_positionid}, "
                        f"volume={position.volume} price={position.price} tick_price={tick.last_price}",
                        "OmsEngine"
                    )
                continue

            if abs(pnl - position.pnl) < 1e-6:
                if self.position_view_debug:
                    self.main_engine.write_log(
                        f"[PositionView] pnl unchanged for {vt_positionid} (pnl={pnl})",
                        "OmsEngine"
                    )
                continue

            new_position: PositionData = copy(position)
            new_position.pnl = pnl
            self.positions[vt_positionid] = new_position

            self.last_view_emit[vt_positionid] = time.time()

            # 注释持仓更新日志，减少日志输出（每秒触发多次，日志过于频繁）
            # self.main_engine.write_log(
            #     f"[OmsEngine] _refresh_symbol_positions: updating position {vt_positionid} pnl={pnl}, calling _emit_position_view",
            #     "OmsEngine"
            # )

            if self.position_view_debug:
                self.main_engine.write_log(
                    f"[PositionView] refresh {vt_positionid} pnl={pnl} "
                    f"tick={tick.vt_symbol} price={tick.last_price} ask1={tick.ask_price_1} bid1={tick.bid_price_1}",
                    "OmsEngine"
                )

            self._emit_position_view(new_position, copy_data=False)
        
        if self.position_view_debug:
            self.main_engine.write_log(
                f"[PositionView] _refresh_symbol_positions completed for {vt_symbol}: checked={positions_checked}, matched={positions_matched}",
                "OmsEngine"
            )

    def _calculate_position_pnl(self, position: PositionData, tick: TickData, size: float) -> float | None:
        """
        Calculate pnl based on position direction and tick data.
        """
        if position.volume <= 0 or position.price <= 0:
            if self.position_view_debug:
                self.main_engine.write_log(
                    f"[PositionView] _calculate_position_pnl: invalid position data "
                    f"volume={position.volume} price={position.price}",
                    "OmsEngine"
                )
            return None

        price_src: float = 0.0

        if position.direction == Direction.LONG:
            price_src = tick.ask_price_1 or tick.last_price or 0.0
            if not price_src:
                if self.position_view_debug:
                    self.main_engine.write_log(
                        f"[PositionView] _calculate_position_pnl: no price for LONG position "
                        f"ask1={tick.ask_price_1} last={tick.last_price}",
                        "OmsEngine"
                    )
                return None
            pnl = (price_src - position.price) * position.volume * size
            if self.position_view_debug:
                self.main_engine.write_log(
                    f"[PositionView] _calculate_position_pnl LONG: price_src={price_src} "
                    f"position_price={position.price} volume={position.volume} size={size} "
                    f"pnl=({price_src} - {position.price}) * {position.volume} * {size} = {pnl}",
                    "OmsEngine"
                )
            return pnl

        if position.direction == Direction.SHORT:
            price_src = tick.bid_price_1 or tick.last_price or 0.0
            if not price_src:
                if self.position_view_debug:
                    self.main_engine.write_log(
                        f"[PositionView] _calculate_position_pnl: no price for SHORT position "
                        f"bid1={tick.bid_price_1} last={tick.last_price}",
                        "OmsEngine"
                    )
                return None
            pnl = (position.price - price_src) * position.volume * size
            if self.position_view_debug:
                self.main_engine.write_log(
                    f"[PositionView] _calculate_position_pnl SHORT: price_src={price_src} "
                    f"position_price={position.price} volume={position.volume} size={size} "
                    f"pnl=({position.price} - {price_src}) * {position.volume} * {size} = {pnl}",
                    "OmsEngine"
                )
            return pnl

        return None

    def _has_position_for_symbol(self, vt_symbol: str) -> bool:
        """
        Check if any position exists for given symbol.
        """
        for position in self.positions.values():
            if position.vt_symbol == vt_symbol and position.volume > 0:
                return True
        return False

    def _apply_trade_to_position(self, trade: TradeData) -> None:
        """
        Merge trade result into position snapshot for symbols without immediate gateway push.
        """
        if not trade.direction:
            if self.position_view_debug:
                self.main_engine.write_log(
                    f"[PositionView] _apply_trade_to_position: no direction, skipping",
                    "OmsEngine"
                )
            return

        # Check if contract uses net position mode
        contract: ContractData | None = self.contracts.get(trade.vt_symbol)
        is_net_position: bool = contract.net_position if contract else False
        
        target_direction: Direction = trade.direction
        sign: float = 1.0

        if is_net_position:
            # For net position mode (like Futu futures), ignore offset field
            # Determine target direction and sign based on existing positions and trade direction
            long_positionid: str = f"{trade.gateway_name}.{trade.vt_symbol}.{Direction.LONG.value}"
            short_positionid: str = f"{trade.gateway_name}.{trade.vt_symbol}.{Direction.SHORT.value}"
            long_pos: PositionData | None = self.positions.get(long_positionid)
            short_pos: PositionData | None = self.positions.get(short_positionid)
            long_volume: float = long_pos.volume if long_pos and long_pos.volume > 0 else 0.0
            short_volume: float = short_pos.volume if short_pos and short_pos.volume > 0 else 0.0
            
            if trade.direction == Direction.LONG:
                # BUY: increases long or decreases short
                if short_volume > 0:
                    # Decrease short position (closing short)
                    target_direction = Direction.SHORT
                    sign = -1.0
                else:
                    # Increase long position (opening long)
                    target_direction = Direction.LONG
                    sign = 1.0
            else:  # trade.direction == Direction.SHORT
                # SELL: increases short or decreases long
                if long_volume > 0:
                    # Decrease long position (closing long)
                    target_direction = Direction.LONG
                    sign = -1.0
                else:
                    # Increase short position (opening short)
                    target_direction = Direction.SHORT
                    sign = 1.0
            
            if self.position_view_debug:
                self.main_engine.write_log(
                    f"[PositionView] NET POSITION mode - "
                    f"trade.direction={trade.direction}, existing long={long_volume}, short={short_volume}, "
                    f"target_direction={target_direction}, sign={sign}",
                    "OmsEngine"
                )
        else:
            # For non-net position mode, use offset field
            if trade.offset in self.close_offsets:
                if trade.direction == Direction.LONG:
                    target_direction = Direction.SHORT
                elif trade.direction == Direction.SHORT:
                    target_direction = Direction.LONG
                sign = -1.0
                if self.position_view_debug:
                    self.main_engine.write_log(
                        f"[PositionView] CLOSE trade detected - "
                        f"trade.direction={trade.direction}, target_direction={target_direction}, sign={sign}",
                        "OmsEngine"
                    )

        vt_positionid: str = f"{trade.gateway_name}.{trade.vt_symbol}.{target_direction.value}"
        position: PositionData | None = self.positions.get(vt_positionid)

        if not position:
            position = PositionData(
                symbol=trade.symbol,
                exchange=trade.exchange,
                direction=target_direction,
                gateway_name=trade.gateway_name,
            )
        self.positions[vt_positionid] = position

        new_volume: float = max(position.volume + sign * trade.volume, 0.0)

        if sign > 0:
            total_cost: float = position.price * position.volume + trade.price * trade.volume
            if new_volume > 0:
                position.price = total_cost / new_volume
        else:
            if new_volume == 0:
                position.price = 0.0

        position.volume = new_volume
        position.pnl = 0.0

        if self.position_view_debug:
            self.main_engine.write_log(
                f"[PositionView] apply trade {trade.vt_symbol} dir={trade.direction} "
                f"offset={trade.offset} volume={position.volume} price={position.price} pnl={position.pnl}",
                "OmsEngine"
            )

        # If position is closed (volume = 0), remove it from positions dict
        if new_volume <= 0:
            if vt_positionid in self.positions:
                del self.positions[vt_positionid]
            self.removed_positions.add(vt_positionid)  # Mark as removed
            # Emit a zero-volume position event to notify UI to remove it
            position.volume = 0.0
            position.frozen = 0.0  # Clear frozen to avoid showing as frozen
            self._emit_position_view(position)
        else:
            # Only emit and refresh if position still exists
            self._emit_position_view(position)
            
            # Enqueue refresh for both trade symbol and position symbol (for continuous contract mapping)
            self._enqueue_refresh_symbol(trade.vt_symbol)
            self._enqueue_refresh_symbol(position.vt_symbol)
        
        if self.position_view_debug:
            self.main_engine.write_log(
                f"[PositionView] applied trade, enqueued refresh for {trade.vt_symbol} and {position.vt_symbol}",
                "OmsEngine"
            )

    def _emit_position_view(self, position: PositionData, copy_data: bool = True) -> None:
        """
        Emit position view event (and optional legacy event).
        """
        if not self.position_view_enabled:
            return

        data: PositionData = copy(position) if copy_data else position
        self.last_view_emit[position.vt_positionid] = time.time()

        if self.position_view_debug:
            self.main_engine.write_log(
                f"[PositionView] emit vt_positionid={position.vt_positionid} "
                f"volume={position.volume} price={position.price} pnl={position.pnl}",
                "OmsEngine"
            )

        view_event: Event = Event(EVENT_POSITION_VIEW, data)
        self.event_engine.put(view_event)

        if self.position_view_emit_legacy:
            legacy_event: Event = Event(EVENT_POSITION, data)
            self.event_engine.put(legacy_event)


class EmailEngine(BaseEngine):
    """
    Provides email sending function.
    """

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        """"""
        super().__init__(main_engine, event_engine, "email")

        self.thread: Thread = Thread(target=self.run)
        self.queue: Queue = Queue()
        self.active: bool = False

    def send_email(self, subject: str, content: str, receiver: str | None = None) -> None:
        """"""
        # Start email engine when sending first email.
        if not self.active:
            self.start()

        # Use default receiver if not specified.
        if not receiver:
            receiver = SETTINGS["email.receiver"]

        msg: EmailMessage = EmailMessage()
        msg["From"] = SETTINGS["email.sender"]
        msg["To"] = receiver
        msg["Subject"] = subject
        msg.set_content(content)

        self.queue.put(msg)

    def run(self) -> None:
        """"""
        server: str = SETTINGS["email.server"]
        port: int = SETTINGS["email.port"]
        username: str = SETTINGS["email.username"]
        password: str = SETTINGS["email.password"]

        while self.active:
            try:
                msg: EmailMessage = self.queue.get(block=True, timeout=1)

                try:
                    with smtplib.SMTP_SSL(server, port) as smtp:
                        smtp.login(username, password)
                        smtp.send_message(msg)
                        smtp.close()
                except Exception:
                    log_msg: str = _("邮件发送失败: {}").format(traceback.format_exc())
                    self.main_engine.write_log(log_msg, "EmailEngine")
            except Empty:
                pass

    def start(self) -> None:
        """"""
        self.active = True
        self.thread.start()

    def close(self) -> None:
        """"""
        if not self.active:
            return

        self.active = False
        self.thread.join()
