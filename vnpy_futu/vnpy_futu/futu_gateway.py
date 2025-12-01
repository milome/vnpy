import pandas as pd
from copy import copy
from datetime import datetime
from threading import Thread, RLock
from time import sleep, time
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from futu import (
    ModifyOrderOp,
    TrdSide,
    TrdEnv,
    TrdMarket,
    KLType,
    OpenQuoteContext,
    OrderBookHandlerBase,
    OrderStatus,
    OrderType,
    RET_ERROR,
    RET_OK,
    StockQuoteHandlerBase,
    TradeDealHandlerBase,
    TradeOrderHandlerBase,
    OpenSecTradeContext,
    OpenFutureTradeContext
)

from vnpy.event import EventEngine
from vnpy.trader.constant import (
    Direction,
    Exchange,
    Offset,
    OrderType as VtOrderType,
    Product,
    Status,
    Interval
)
from vnpy.trader.gateway import BaseGateway
from vnpy.trader.object import (
    TickData,
    OrderData,
    TradeData,
    BarData,
    AccountData,
    ContractData,
    PositionData,
    SubscribeRequest,
    OrderRequest,
    CancelRequest,
    HistoryRequest,
    MainContractSwitchData
)
from vnpy.trader.event import EVENT_TIMER
from vnpy.trader.utility import ZoneInfo


# 委托状态映射
STATUS_FUTU2VT: Dict[OrderStatus, Status] = {
    OrderStatus.NONE: Status.SUBMITTING,
    OrderStatus.WAITING_SUBMIT: Status.SUBMITTING,
    OrderStatus.SUBMITTING: Status.SUBMITTING,
    OrderStatus.SUBMITTED: Status.NOTTRADED,
    OrderStatus.FILLED_PART: Status.PARTTRADED,
    OrderStatus.FILLED_ALL: Status.ALLTRADED,
    OrderStatus.CANCELLED_PART: Status.CANCELLED,
    OrderStatus.CANCELLED_ALL: Status.CANCELLED,
    OrderStatus.FAILED: Status.REJECTED,
    OrderStatus.DISABLED: Status.CANCELLED,
    OrderStatus.DELETED: Status.CANCELLED,
}

# 多空方向映射
DIRECTION_VT2FUTU: Dict[Direction, TrdSide] = {
    Direction.LONG: TrdSide.BUY,
    Direction.SHORT: TrdSide.SELL,
}
DIRECTION_FUTU2VT: Dict[TrdSide, Tuple] = {
    TrdSide.BUY: (Direction.LONG, Offset.OPEN),
    TrdSide.SELL: (Direction.SHORT, Offset.OPEN),
    TrdSide.BUY_BACK: (Direction.LONG, Offset.CLOSE),
    TrdSide.SELL_SHORT: (Direction.SHORT, Offset.CLOSE),
}

# 委托类型映射
ORDERTYPE_VT2FUTU: Dict[VtOrderType, str] = {
    VtOrderType.LIMIT: "NORMAL",       # 限价单
    VtOrderType.MARKET: "MARKET",      # 市价单（不推荐使用）
    VtOrderType.OPPONENT: "NORMAL",    # 对手价（买用卖一，卖用买一）
    VtOrderType.OVER: "NORMAL",        # 超价（对手价基础上加价）
}

# 特殊价格类型 - 已重构为对手价和超价订单类型
# 不再使用特殊价格标记，所有价格均由UI计算并传入

# 追价功能配置类
class ChaseConfig:
    """智能追价配置"""
    def __init__(self, reference: str):
        """从reference字符串解析追价配置"""
        self.enabled = False
        self.max_chase_times = 10  # 使用较大的默认值（不再在UI中显示）
        self.chase_interval = 0.5
        
        # 超时配置
        self.timeout_seconds = 3.0  # 单次超时阈值（秒）
        self.enable_timeout_cancel = True  # 是否启用超时撤单
        self.max_retry_times = 2  # 最大重委托次数
        
        # 整体超时配置（从首次下单开始计算）
        self.overall_timeout_seconds = 30.0  # 整体超时阈值（秒），超过后强制停止追价

        # 解析reference中的追价配置
        # 检查是否有追价相关参数（Retry表示启用了追价）
        if "_Retry" in reference:
            self.enabled = True
            try:
                parts = reference.split("_")
                for part in parts:
                    if part.startswith("Chase"):
                        # 兼容旧格式，但不再使用（已移除UI控件）
                        self.max_chase_times = int(part.replace("Chase", ""))
                    elif part.startswith("Slip"):
                        # 兼容旧格式，但不再使用（已移除滑点限制）
                        pass
                    elif part.startswith("Retry"):
                        self.max_retry_times = int(part.replace("Retry", ""))
            except:
                # 解析失败，使用默认值
                pass

# 追价订单状态追踪
class ChaseOrder:
    """追价订单状态"""
    def __init__(self, orderid: str, original_price: float, config: ChaseConfig,
                 symbol: str, exchange, direction, offset, volume: int, reference: str):
        # 标记是否刚刚撤单成功，用于区分"已取消的旧订单"和"刚撤单成功的订单"
        self.just_cancelled: bool = False
        self.original_orderid = orderid  # 保存第一次下单的订单ID（不更新）
        self.orderid = orderid  # 当前订单ID（重委托后会更新）
        self.original_price = original_price
        self.current_price = original_price
        self.chase_count = 0
        self.config = config
        self.last_chase_time = 0.0
        self.is_chasing = False
        
        # 保存原始订单信息（用于重委托）
        self.symbol = symbol
        self.exchange = exchange
        self.direction = direction  # 保持原始方向
        self.offset = offset  # 保持原始offset
        self.volume = volume
        self.original_reference = reference
        self.vt_symbol = f"{symbol}.{exchange.value}"
        
        # 时间戳
        current_time = time()
        self.original_order_time = current_time  # 保存第一次下单时间（不更新，用于统计总耗时）
        self.order_time = current_time  # 当前订单的委托时间（重委托后会更新，用于超时判断）
        self.first_trade_time = None
        self.fill_time = None
        
        # 重委托计数
        self.retry_count = 0

# 交易所映射
EXCHANGE_VT2FUTU: Dict[Exchange, str] = {
    Exchange.SMART: "US",
    Exchange.SEHK: "HK",
    Exchange.HKFE: "HK_FUTURE",
}
EXCHANGE_FUTU2VT: Dict[str, Exchange] = {v: k for k, v in EXCHANGE_VT2FUTU.items()}

# 产品类型映射
PRODUCT_VT2FUTU: Dict[Product, str] = {
    Product.EQUITY: "STOCK",
    Product.INDEX: "IDX",
    Product.ETF: "ETF",
    Product.WARRANT: "WARRANT",
    Product.BOND: "BOND",
    Product.FUTURES: "FUTURE"
}


# 其他常量
CHINA_TZ = ZoneInfo("Asia/Shanghai")


class FutuGateway(BaseGateway):
    """
    veighna用于对接富途证券的交易接口。
    """
    default_name: str = "FUTU"

    default_setting: Dict[str, Any] = {
        "密码": "",
        "地址": "127.0.0.1",
        "端口": 11111,
        "市场": ["HK", "US", "HK_FUTURE"],
        "环境": [TrdEnv.REAL, TrdEnv.SIMULATE],
    }

    exchanges: List[str] = list(EXCHANGE_FUTU2VT.values())

    def __init__(self, event_engine: EventEngine, gateway_name: str) -> None:
        """构造函数"""
        super().__init__(event_engine, gateway_name)

        self.quote_ctx: OpenQuoteContext = None
        self.trade_ctx: Union[OpenSecTradeContext, OpenFutureTradeContext] = None

        self.host: str = ""
        self.port: int = 0
        self.market: str = ""
        self.password: str = ""
        self.env: TrdEnv = TrdEnv.SIMULATE

        self.ticks: Dict[str, TickData] = {}
        self.trades: Set = set()
        self.contracts: Dict[str, ContractData] = {}

        # 追价功能相关
        self.chase_orders: Dict[str, ChaseOrder] = {}  # 追价订单追踪
        self.chase_orders_lock = RLock()  # 线程安全锁
        self.chase_enabled: bool = True  # 全局追价开关
        
        # 主力合约映射缓存（主力合约代码 -> 实际合约代码）
        # 例如：{"MHImain": "MHI2511", "HSImain": "HSI2511"}
        self.main_contract_mapping: Dict[str, str] = {}
        self.main_contract_check_interval: int = 60  # 主力合约检查间隔（秒）
        self.main_contract_check_count: int = 0  # 主力合约检查计数器
        self.main_contract_initialized: Set[str] = set()  # 记录已进行过初始化检查的主力合约
        
        # ✅ 性能优化：tick数据缓存（用于下单时的价格计算）
        # 缓存格式：symbol -> (tick_data, timestamp)
        # TTL: 100ms（确保数据新鲜度）
        self._tick_cache: Dict[str, Tuple[TickData, float]] = {}
        
        # 撤单频率限制（避免触发API限制：每30秒最多20次）
        self.cancel_times: List[float] = []  # 记录撤单时间戳
        self.max_cancel_per_30s: int = 18  # 30秒内最多撤单次数（留2次余量）

        # 追价统计
        self.chase_stats = {
            "total_orders": 0,          # 总追价订单数
            "successful_chases": 0,     # 成功追价次数
            "failed_chases": 0,         # 失败追价次数
            "total_slippage": 0.0,      # 累计滑点
            # 耗时统计
            "order_to_first_trade_times": [],  # 委托到首次成交耗时列表（毫秒）
            "order_to_fill_times": [],  # 委托到完全成交耗时列表（毫秒）
            "avg_order_to_first_trade_ms": 0.0,  # 平均首次成交耗时
            "avg_order_to_fill_ms": 0.0,  # 平均完全成交耗时
            "max_order_to_first_trade_ms": 0.0,  # 最大首次成交耗时
            "max_order_to_fill_ms": 0.0,  # 最大完全成交耗时
            "min_order_to_first_trade_ms": 0.0,  # 最小首次成交耗时
            "min_order_to_fill_ms": 0.0,  # 最小完全成交耗时
        }

        self.thread: Thread = Thread(target=self.query_data)

        self.count: int = 0
        self.interval: int = 1  # 改为1秒间隔，更及时地更新持仓和账户信息
        self.query_funcs: list = [self.query_account, self.query_position]

    def connect(self, setting: dict) -> None:
        """连接交易接口"""
        self.host: str = setting["地址"]
        self.port: int = setting["端口"]
        self.market: str = setting["市场"]
        self.password: str = setting["密码"]
        self.env: TrdEnv = setting["环境"]

        self.connect_quote()
        self.connect_trade()

        # 如果线程已经启动过，创建新的线程对象
        if self.thread.is_alive():
            self.thread = Thread(target=self.query_data)
        elif hasattr(self.thread, '_started') and self.thread._started.is_set():
            self.thread = Thread(target=self.query_data)
            
        self.thread.start()


    def query_data(self) -> None:
        """查询数据"""
        sleep(2.0)  # 等待两秒直到连接成功

        self.query_contract()
        self.query_trade()
        self.query_order()
        self.query_position()
        self.query_account()
        
        # 初始化主力合约映射
        self._check_main_contract_switch()

        # 初始化定时查询任务
        self.event_engine.register(EVENT_TIMER, self.process_timer_event)


 
    def process_timer_event(self, event) -> None:
        """定时事件处理"""
        self.count += 1
        if self.count < self.interval:
            return
        self.count = 0
        func = self.query_funcs.pop(0)
        func()
        self.query_funcs.append(func)
        
        # 检查超时订单（每1秒检查一次）
        self._check_timeout_orders()
        
        # 检查主力合约切换（根据配置的间隔检查）
        self.main_contract_check_count += 1
        if self.main_contract_check_count >= self.main_contract_check_interval:
            self.main_contract_check_count = 0
            self._check_main_contract_switch()
    
    def _normalize_orderid(self, orderid: Optional[str]) -> Optional[str]:
        """去除网关前缀，统一使用富途实际订单ID"""
        if not orderid:
            return orderid
        orderid = str(orderid).strip()
        prefix = f"{self.gateway_name}."
        if orderid.startswith(prefix):
            return orderid[len(prefix):]
        return orderid
    
    # ========== 线程安全的 chase_orders 访问方法 ==========
    
    def _safe_has_chase_order(self, orderid: str) -> bool:
        """线程安全地检查订单是否存在"""
        with self.chase_orders_lock:
            return orderid in self.chase_orders
    
    def _safe_get_chase_order(self, orderid: str) -> Optional[ChaseOrder]:
        """线程安全地获取追价订单"""
        with self.chase_orders_lock:
            return self.chase_orders.get(orderid)
    
    def _safe_set_chase_order(self, orderid: str, chase_order: ChaseOrder) -> None:
        """线程安全地设置追价订单"""
        with self.chase_orders_lock:
            self.chase_orders[orderid] = chase_order
    
    def _safe_del_chase_order(self, orderid: str) -> bool:
        """线程安全地删除追价订单，返回是否成功删除"""
        with self.chase_orders_lock:
            if orderid in self.chase_orders:
                del self.chase_orders[orderid]
                return True
            return False
    
    def _safe_get_all_chase_orders(self) -> Dict[str, ChaseOrder]:
        """线程安全地获取所有追价订单的副本"""
        with self.chase_orders_lock:
            return dict(self.chase_orders)  # 返回副本
    
    def _safe_update_chase_order_key(self, old_key: str, new_key: str, chase_order: ChaseOrder) -> None:
        """线程安全地更新订单key"""
        with self.chase_orders_lock:
            if new_key != old_key:
                # 先添加新key，确保新订单能立即被找到
                self.chase_orders[new_key] = chase_order
                # 再删除旧key
                if old_key in self.chase_orders:
                    del self.chase_orders[old_key]
    
    def _safe_clear_chase_orders(self) -> None:
        """线程安全地清空所有追价订单"""
        with self.chase_orders_lock:
            self.chase_orders.clear()
    
    def _check_timeout_orders(self) -> None:
        """检查超时订单并执行撤单重委托"""
        if not self.chase_enabled:
            return
        
        current_time = time()
        timeout_orders = []
        
        # 清理过期的撤单时间记录（保留最近30秒的）
        self.cancel_times = [t for t in self.cancel_times if current_time - t < 30.0]
        
        # 查找超时的未成交订单（使用线程安全的副本）
        for orderid, chase_order in list(self._safe_get_all_chase_orders().items()):
            normalized_orderid = self._normalize_orderid(orderid)
            if not normalized_orderid:
                self.write_log(f"订单{orderid}无法规范化订单ID，跳过超时检查")
                continue
            if normalized_orderid != orderid:
                # 更新字典key，确保后续逻辑统一使用富途原始订单ID（线程安全）
                self._safe_update_chase_order_key(orderid, normalized_orderid, chase_order)
                orderid = normalized_orderid
            chase_order.orderid = normalized_orderid
            # 检查是否启用超时撤单
            if not chase_order.config.enable_timeout_cancel:
                continue
            
            # 🛡️ 检查整体超时（从首次下单开始计算）
            overall_elapsed = current_time - chase_order.original_order_time
            if overall_elapsed >= chase_order.config.overall_timeout_seconds:
                self.write_log(f"⚠️ 订单{orderid}整体超时！从首次下单已等待{overall_elapsed:.1f}秒，超过阈值{chase_order.config.overall_timeout_seconds}秒")
                self.write_log(f"订单详情: symbol={chase_order.symbol}, direction={chase_order.direction}, volume={chase_order.volume}, 重试次数={chase_order.retry_count}")
                
                # 尝试撤销当前订单（如果还未撤销）
                order_status = self._get_order_status(orderid)
                if order_status and order_status not in [Status.ALLTRADED, Status.CANCELLED, Status.REJECTED]:
                    cancel_req = CancelRequest(
                        orderid=orderid,
                        symbol=chase_order.symbol,
                        exchange=chase_order.exchange
                    )
                    self._cancel_order_internal(cancel_req)
                    self.write_log(f"订单{orderid}整体超时，已发送撤单请求")
                
                # 从追价列表中移除
                self._safe_del_chase_order(orderid)
                if chase_order.orderid != orderid:
                    self._safe_del_chase_order(chase_order.orderid)
                if chase_order.original_orderid != orderid:
                    self._safe_del_chase_order(chase_order.original_orderid)
                
                # 推送订单失败事件，触发UI弹窗通知
                self._notify_chase_timeout_failure(chase_order, overall_elapsed)
                continue
            
            # 检查是否超过单次超时阈值
            elapsed = current_time - chase_order.order_time
            if elapsed >= chase_order.config.timeout_seconds:
                # 检查订单状态：如果订单已经成交，立即移除，不再继续追价
                order_status = self._get_order_status(orderid)
                if order_status == Status.ALLTRADED:
                    # 订单已完全成交，立即移除，停止所有追价操作
                    self.write_log(f"订单{orderid}已完全成交，从追价列表中移除（超时检查中发现）")
                    self._safe_del_chase_order(orderid)
                    continue
                
                # 如果状态查询返回None，可能是订单已成交但查询不到，检查是否还在chase_orders中
                # 如果不在，说明已经被移除了（可能已成交），跳过处理
                if order_status is None:
                    # 再次检查订单是否还在chase_orders中（可能在其他线程中已被移除）
                    if not self._safe_has_chase_order(orderid):
                        self.write_log(f"订单{orderid}状态无法查询且已不在追价列表中（可能已成交），跳过处理")
                        continue
                    
                    # 如果订单还在chase_orders中但查询不到状态，可能是订单已成交但状态更新有延迟
                    # 为了安全起见，如果订单不是刚刚撤单的（just_cancelled=False），应该保守处理：
                    # 如果查询不到状态，通常意味着订单已经不存在（已成交或已取消），应该移除
                    if not chase_order.just_cancelled:
                        # 订单不是刚刚撤单的，查询不到状态通常意味着已成交或已取消
                        # 为了安全，直接移除，避免继续追价导致超仓
                        self.write_log(f"订单{orderid}状态无法查询且不是刚刚撤单的订单，可能已成交，从追价列表中移除")
                        self._safe_del_chase_order(orderid)
                        continue
                    
                    # 如果订单刚刚撤单成功（just_cancelled=True），查询不到状态是正常的（订单已从活跃列表中移除）
                    # 这种情况下应该继续等待tick数据或重新委托，不应该添加到timeout_orders
                    # 但这里已经在CANCELLED分支处理了，所以这里应该不会到达
                    # 为了安全，仍然跳过，避免重复处理
                    self.write_log(f"订单{orderid}状态无法查询，但刚刚撤单成功，跳过超时处理（等待tick数据）")
                    continue
                
                # 检查订单状态：如果订单已经撤单成功且正在等待tick数据，应该持续更新order_time而不是触发撤单
                if order_status == Status.CANCELLED and chase_order.just_cancelled:
                    # 订单已撤单成功，正在等待tick数据，更新order_time避免触发撤单
                    self.write_log(f"订单{orderid}已撤单成功，等待tick数据中（已等待{elapsed:.1f}秒），更新order_time避免触发撤单")
                    chase_order.order_time = current_time
                    # 尝试获取tick并重新委托
                    self._try_reorder_with_tick(chase_order, orderid)
                    continue
                
                # 检查重委托次数限制
                if chase_order.retry_count >= chase_order.config.max_retry_times:
                    self.write_log(f"订单{orderid}超时但已达到最大重委托次数{chase_order.config.max_retry_times}，停止重试并从追价列表中移除")
                    # 从追价列表中移除
                    self._safe_del_chase_order(orderid)
                    continue
                
                timeout_orders.append((orderid, chase_order, elapsed))
        
        # 处理超时订单
        for orderid, chase_order, elapsed in timeout_orders:
            # 在处理前再次检查订单是否还在chase_orders中（可能在其他线程中已被移除，如已成交）
            if not self._safe_has_chase_order(orderid):
                self.write_log(f"订单{orderid}已不在追价列表中（可能已成交），跳过处理")
                continue
            
            # 检查撤单频率限制
            if len(self.cancel_times) >= self.max_cancel_per_30s:
                self.write_log(f"订单{orderid}超时{elapsed:.1f}秒，但撤单频率已达上限（30秒内{self.max_cancel_per_30s}次），延迟处理")
                continue
            
            self.write_log(f"订单{orderid}超时{elapsed:.1f}秒，执行撤单重委托")
            self._retry_order_with_latest_price(chase_order)
    
    def _check_main_contract_switch(self) -> None:
        """
        检查主力合约是否发生切换。
        
        遍历所有已订阅的主力合约，查询当前实际合约代码，
        如果与缓存中的映射不同，则触发主力合约切换事件。
        """
        # 只监控MHImain的主力合约切换（其他合约如需监控可添加到列表）
        main_contracts = [
            ("MHImain", Exchange.HKFE),   # 小恒指
            # ("HSImain", Exchange.HKFE),   # 大恒指（暂不监控）
            # ("MCHmain", Exchange.HKFE),   # 小国指（暂不监控）
            # ("HHImain", Exchange.HKFE),   # 大国指（暂不监控）
        ]
        
        for main_symbol, exchange in main_contracts:
            try:
                # 构造富途格式的合约代码
                futu_symbol = convert_symbol_vt2futu(main_symbol, exchange)
                self.write_log(f"[主力合约检查] 开始检查 {main_symbol} (富途代码: {futu_symbol})")
                
                # 解析当前实际合约
                actual_code = self._resolve_main_contract(main_symbol, futu_symbol)
                if not actual_code:
                    self.write_log(f"[主力合约检查] ⚠️ 无法解析 {main_symbol} 的实际合约代码，跳过检查")
                    continue
                
                # 从富途格式提取实际合约代码（如 "HK.MHI2511" -> "MHI2511"）
                if "." in actual_code:
                    actual_symbol = actual_code.split(".")[-1]
                else:
                    actual_symbol = actual_code
                
                self.write_log(f"[主力合约检查] {main_symbol} 当前实际合约: {actual_symbol}")
                
                # 获取缓存中的旧映射
                old_actual_symbol = self.main_contract_mapping.get(main_symbol)
                
                # 如果是首次查询（连接初始化时）或尚未进行过初始化检查
                # 注意：即使 main_contract_mapping 在订阅时被预初始化了，我们仍然需要检查提前切换
                if main_symbol not in self.main_contract_initialized:
                    # 更新映射（如果还没有的话）
                    if old_actual_symbol is None:
                        self.main_contract_mapping[main_symbol] = actual_symbol
                        self.write_log(f"[主力合约检查] 初始化主力合约映射: {main_symbol} -> {actual_symbol}")
                    else:
                        self.write_log(f"[主力合约检查] 主力合约映射已存在: {main_symbol} -> {old_actual_symbol}，当前实际合约: {actual_symbol}")
                    
                    # 标记为已初始化
                    self.main_contract_initialized.add(main_symbol)
                    
                    # 连接初始化时检查是否提前切换（即使当前主力合约没发生切换，但如果日期早于当前主力合约的日期，仍然判定提前切换）
                    # 这样的检查只在初始化时做一次
                    is_early_switch = self._is_early_switch(actual_symbol)
                    self.write_log(f"[主力合约检查] 初始化时提前切换检查结果: {is_early_switch} (合约: {actual_symbol})")
                    
                    if is_early_switch:
                        self.write_log(f"⚠️ 检测到当前主力合约{actual_symbol}是提前切换状态！")
                        
                        # 创建切换事件数据（old_actual_symbol用空字符串表示首次初始化）
                        switch_data = MainContractSwitchData(
                            gateway_name=self.gateway_name,
                            main_symbol=main_symbol,
                            exchange=exchange,
                            old_actual_symbol="(首次连接)",
                            new_actual_symbol=actual_symbol,
                            switch_time=datetime.now(CHINA_TZ),
                            is_early_switch=True
                        )
                        
                        self.write_log(f"[主力合约检查] 触发提前切换事件: {main_symbol} -> {actual_symbol}")
                        # 触发主力合约切换事件，通知UI显示提前切换提示
                        self.on_main_contract_switch(switch_data)
                        self.write_log(f"[主力合约检查] 事件已发送: EVENT_MAIN_CONTRACT_SWITCH")
                    
                    continue
                
                # 检查是否发生切换
                if actual_symbol != old_actual_symbol:
                    self.write_log(f"检测到主力合约切换: {main_symbol} 从 {old_actual_symbol} 切换到 {actual_symbol}")
                    
                    # 更新缓存
                    self.main_contract_mapping[main_symbol] = actual_symbol
                    
                    # 判断是否提前切换（当前月份 < 新合约月份）
                    is_early_switch = self._is_early_switch(actual_symbol)
                    self.write_log(f"[主力合约检查] 提前切换检查结果: {is_early_switch} (合约: {actual_symbol})")
                    
                    if is_early_switch:
                        self.write_log(f"⚠️ 检测到提前切换！当前日期早于新主力合约{actual_symbol}的月份")
                    
                    # 创建切换事件数据
                    switch_data = MainContractSwitchData(
                        gateway_name=self.gateway_name,
                        main_symbol=main_symbol,
                        exchange=exchange,
                        old_actual_symbol=old_actual_symbol,
                        new_actual_symbol=actual_symbol,
                        switch_time=datetime.now(CHINA_TZ),
                        is_early_switch=is_early_switch
                    )
                    
                    self.write_log(f"[主力合约检查] 触发切换事件: {main_symbol} {old_actual_symbol} -> {actual_symbol} (提前切换: {is_early_switch})")
                    # 触发主力合约切换事件
                    self.on_main_contract_switch(switch_data)
                    self.write_log(f"[主力合约检查] 事件已发送: EVENT_MAIN_CONTRACT_SWITCH")
                    
                    # 更新tick订阅：订阅新的实际合约
                    self._handle_main_contract_switch(main_symbol, exchange, old_actual_symbol, actual_symbol)
                else:
                    # 未发生切换，不检查提前切换（只在初始化时检查一次）
                    self.write_log(f"[主力合约检查] {main_symbol} 未发生切换，当前合约: {actual_symbol}")
            
            except Exception as e:
                import traceback
                self.write_log(f"检查主力合约{main_symbol}切换时发生异常: {str(e)}")
                self.write_log(f"异常堆栈: {traceback.format_exc()}")
    
    def _is_early_switch(self, actual_symbol: str) -> bool:
        """
        判断是否提前切换主力合约。
        
        如果当前日期的年月 < 新主力合约的年月，说明是提前切换。
        例如：当前是2025年11月，新主力是MHI2512（2025年12月），则是提前切换。
        
        Args:
            actual_symbol: 新的实际合约代码（如MHI2512）
            
        Returns:
            True表示提前切换，False表示正常切换
        """
        try:
            # 提取合约年月代码（最后4位数字，格式YYMM）
            if len(actual_symbol) < 4:
                self.write_log(f"[提前切换检查] 合约代码长度不足: {actual_symbol}")
                return False
            
            year_month_code = actual_symbol[-4:]
            if not year_month_code.isdigit():
                self.write_log(f"[提前切换检查] 合约代码格式错误（最后4位不是数字）: {actual_symbol}")
                return False
            
            # 解析合约年月
            contract_year = int(year_month_code[:2]) + 2000  # 25 -> 2025
            contract_month = int(year_month_code[2:])  # 12
            
            # 获取当前年月
            now = datetime.now(CHINA_TZ)
            current_year = now.year
            current_month = now.month
            
            self.write_log(f"[提前切换检查] 合约: {actual_symbol}, 合约年月: {contract_year}-{contract_month:02d}, 当前年月: {current_year}-{current_month:02d}")
            
            # 比较：如果当前年月 < 合约年月，说明是提前切换
            if current_year < contract_year:
                self.write_log(f"[提前切换检查] ✅ 提前切换: 当前年份 {current_year} < 合约年份 {contract_year}")
                return True
            elif current_year == contract_year and current_month < contract_month:
                self.write_log(f"[提前切换检查] ✅ 提前切换: 当前月份 {current_month} < 合约月份 {contract_month}")
                return True
            
            self.write_log(f"[提前切换检查] ❌ 正常切换: 当前年月 >= 合约年月")
            return False
            
        except Exception as e:
            self.write_log(f"判断提前切换异常: {str(e)}")
            import traceback
            self.write_log(f"异常堆栈: {traceback.format_exc()}")
            return False
    
    def _handle_main_contract_switch(self, main_symbol: str, exchange: Exchange, 
                                      old_actual_symbol: str, new_actual_symbol: str) -> None:
        """
        处理主力合约切换后的相关更新操作。
        
        更新内容：
        1. 更新合约信息（名称显示新的实际合约）
        2. 更新tick缓存
        3. 推送tick事件让UI立即刷新
        
        注意：不需要单独订阅新的实际合约行情，因为订阅MHImain后
        富途API会自动将行情映射到当前主力合约。
        
        Args:
            main_symbol: 主力合约代码（如MHImain）
            exchange: 交易所
            old_actual_symbol: 旧的实际合约代码
            new_actual_symbol: 新的实际合约代码
        """
        try:
            main_vt_symbol = f"{main_symbol}.{exchange.value}"
            new_vt_symbol = f"{new_actual_symbol}.{exchange.value}"
            main_futu_code = convert_symbol_vt2futu(main_symbol, exchange)
            new_futu_code = convert_symbol_vt2futu(new_actual_symbol, exchange)
            
            # 注意：不需要单独订阅新合约，MHImain的行情会自动切换到新主力
            self.write_log(f"主力合约已切换: {main_symbol} -> {new_actual_symbol}")
            
            # 1. 更新合约信息缓存（名称中包含实际合约代码，方便用户识别）
            # 尝试获取新合约的基础信息
            base_name = main_symbol  # 默认名称
            product = Product.FUTURES
            size = 10  # 默认合约乘数
            pricetick = 0.001
            
            if new_vt_symbol in self.contracts:
                new_contract = self.contracts[new_vt_symbol]
                base_name = new_contract.name
                product = new_contract.product
                size = new_contract.size
                pricetick = new_contract.pricetick
            
            # 创建/更新主力合约信息，名称格式："小恒指期货 (主力→MHI2512)"
            main_contract = ContractData(
                symbol=main_symbol,
                exchange=exchange,
                name=f"{base_name} (主力→{new_actual_symbol})",
                product=product,
                size=size,
                pricetick=pricetick,
                history_data=True,
                net_position=True,
                gateway_name=self.gateway_name,
            )
            self.contracts[main_vt_symbol] = main_contract
            # 推送合约更新事件
            self.on_contract(main_contract)
            self.write_log(f"已更新主力合约信息: {main_vt_symbol} -> {main_contract.name}")
            
            # 3. 更新ticks缓存中的主力合约数据
            # 如果新实际合约已有tick数据，复制并更新名称
            # 注意：富途API推送的行情数据使用"HK.xxx"格式而非"HK_FUTURE.xxx"
            # 需要同时检查两种格式
            new_tick = self.ticks.get(new_futu_code)
            if not new_tick and new_futu_code.startswith("HK_FUTURE."):
                alt_new_futu_code = new_futu_code.replace("HK_FUTURE.", "HK.", 1)
                new_tick = self.ticks.get(alt_new_futu_code)
                if new_tick:
                    self.write_log(f"使用备用格式找到新合约tick: {alt_new_futu_code}")
            
            if new_tick:
                # 创建主力合约的tick副本，使用主力合约的symbol
                # 注意：需要使用与富途推送一致的格式（HK.xxx而非HK_FUTURE.xxx）
                actual_main_futu_code = main_futu_code
                if main_futu_code.startswith("HK_FUTURE."):
                    actual_main_futu_code = main_futu_code.replace("HK_FUTURE.", "HK.", 1)
                main_tick = self.get_tick(actual_main_futu_code)
                # 复制价格数据
                main_tick.last_price = new_tick.last_price
                main_tick.open_price = new_tick.open_price
                main_tick.high_price = new_tick.high_price
                main_tick.low_price = new_tick.low_price
                main_tick.pre_close = new_tick.pre_close
                main_tick.volume = new_tick.volume
                main_tick.bid_price_1 = new_tick.bid_price_1
                main_tick.bid_volume_1 = new_tick.bid_volume_1
                main_tick.ask_price_1 = new_tick.ask_price_1
                main_tick.ask_volume_1 = new_tick.ask_volume_1
                main_tick.datetime = new_tick.datetime
                # 更新名称以反映实际合约
                main_tick.name = main_contract.name
                
                self.write_log(f"已更新主力合约tick缓存: {actual_main_futu_code}")
                
                # 4. 推送tick事件，让UI立即刷新显示
                self.on_tick(copy(main_tick))
                self.write_log(f"已推送主力合约tick更新事件，UI将立即刷新")
            else:
                self.write_log(f"新实际合约{new_futu_code}暂无tick数据，等待行情推送后更新")
                
        except Exception as e:
            self.write_log(f"处理主力合约切换时发生异常: {str(e)}")
    
    def get_main_contract_mapping(self) -> Dict[str, str]:
        """
        获取当前主力合约映射关系。
        
        Returns:
            Dict[str, str]: 主力合约代码 -> 实际合约代码的映射
        """
        return self.main_contract_mapping.copy()
    
    def get_actual_symbol(self, main_symbol: str) -> Optional[str]:
        """
        获取主力合约对应的实际合约代码。
        
        Args:
            main_symbol: 主力合约代码（如MHImain）
            
        Returns:
            实际合约代码（如MHI2511），如果未找到返回None
        """
        return self.main_contract_mapping.get(main_symbol)

    def _get_order_status(self, orderid: str) -> Optional[Status]:
        """查询订单状态
        
        Returns:
            Status: 订单状态，如果无法查询则返回None
        """
        try:
            orderid = self._normalize_orderid(orderid)
            if not orderid:
                return None
            if not self.trade_ctx:
                return None
            
            # 查询订单列表
            code, data = self.trade_ctx.order_list_query("", trd_env=self.env)
            if code != RET_OK:
                return None
            
            # 查找指定订单
            for ix, row in data.iterrows():
                if str(row["order_id"]) == orderid:
                    return STATUS_FUTU2VT.get(row["order_status"], None)
            
            # 订单不存在，可能已取消或成交
            return None
        except Exception as e:
            self.write_log(f"查询订单{orderid}状态异常：{str(e)}")
            return None
    
    def _retry_order_with_latest_price(self, chase_order: ChaseOrder) -> None:
        """超时后撤单并重新委托 - 保持原始方向"""
        try:
            # 保存原始订单ID，防止在重试过程中订单ID变化导致无法正确移除
            original_orderid = self._normalize_orderid(chase_order.orderid)
            if not original_orderid:
                self.write_log("重委托失败：无法识别原始订单ID")
                return
            chase_order.orderid = original_orderid
            
            # 0. 首先检查订单是否还在chase_orders中（可能在其他线程中已被移除，如已成交）
            if not self._safe_has_chase_order(original_orderid):
                self.write_log(f"订单{original_orderid}已不在追价列表中（可能已成交），停止重委托")
                return
            
            # 1. 先查询订单状态，如果已经取消或已成交，直接移除
            # 注意：如果刚刚撤单成功（just_cancelled=True），即使状态是CANCELLED也应该继续重新委托
            order_status = self._get_order_status(original_orderid)
            
            if order_status is None:
                # 无法查询状态，可能是订单不存在或已取消/成交
                # 再次检查订单是否还在chase_orders中，如果不在，说明已经被移除了（可能已成交），直接返回
                if not self._safe_has_chase_order(original_orderid):
                    self.write_log(f"订单{original_orderid}状态无法查询且已不在追价列表中（可能已成交），停止重委托")
                    return
                
                # 如果订单还在chase_orders中但查询不到状态，可能是订单已成交但状态更新有延迟
                # 为了安全起见，如果订单不是刚刚撤单的（just_cancelled=False），应该保守处理：
                # 如果查询不到状态，通常意味着订单已经不存在（已成交或已取消），应该移除
                if not chase_order.just_cancelled:
                    # 订单不是刚刚撤单的，查询不到状态通常意味着已成交或已取消
                    # 为了安全，直接移除，避免继续追价导致超仓
                    self.write_log(f"订单{original_orderid}状态无法查询且不是刚刚撤单的订单，可能已成交，从追价列表中移除")
                    self._safe_del_chase_order(original_orderid)
                    return
                
                # 如果订单刚刚撤单成功（just_cancelled=True），查询不到状态是正常的（订单已从活跃列表中移除）
                # 这种情况下应该继续尝试重新委托
                self.write_log(f"订单{original_orderid}状态无法查询，但刚刚撤单成功，继续尝试重新委托")
            elif order_status == Status.ALLTRADED:
                # 订单已完全成交，移除
                self.write_log(f"订单{original_orderid}已完全成交，停止重委托并从追价列表中移除")
                # 使用原始订单ID和当前订单ID都尝试移除，确保移除成功
                self._safe_del_chase_order(original_orderid)
                return
            elif order_status == Status.CANCELLED:
                # 订单已取消
                if chase_order.just_cancelled:
                    # 这是我们刚刚撤单成功的订单，应该直接尝试重新委托，不需要再次撤单
                    self.write_log(f"订单{original_orderid}已撤单成功，跳过撤单步骤，直接尝试重新委托")
                    # 重置标志，避免下次检查时再次进入此分支
                    chase_order.just_cancelled = False
                    # 跳过撤单步骤，直接进入获取tick和重新委托的流程
                    # 不需要等待，直接获取tick
                else:
                    # 这是之前就已经取消的订单，移除（不再尝试重新委托）
                    self.write_log(f"订单{original_orderid}已取消，从追价列表中移除")
                    # 使用原始订单ID和当前订单ID都尝试移除，确保移除成功
                    self._safe_del_chase_order(original_orderid)
                    return
            else:
                # 订单状态不是CANCELLED，需要执行撤单操作
                # 2. 执行撤单操作
                self.write_log(f"订单{original_orderid}开始执行撤单操作")
                cancel_req = CancelRequest(
                    orderid=original_orderid,
                    symbol=chase_order.symbol,
                    exchange=chase_order.exchange
                )
                cancel_success, already_cancelled, is_rate_limit = self._cancel_order_internal(cancel_req)
                
                # 如果订单在撤单前就已经取消，直接移除，不再重试
                if already_cancelled:
                    self.write_log(f"订单{original_orderid}在撤单前已取消，停止重委托并从追价列表中移除")
                    # 使用原始订单ID和当前订单ID都尝试移除，确保移除成功
                    self._safe_del_chase_order(original_orderid)
                    return
                
                # 如果撤单因频率限制失败，停止重试，等待下次超时检查
                if is_rate_limit:
                    self.write_log(f"订单{original_orderid}撤单失败（频率限制），停止重委托，等待下次超时检查")
                    # 记录撤单时间（频率限制的尝试也算一次API调用）
                    self.cancel_times.append(time())
                    return  # 不继续重新委托
                
                # 如果撤单失败（且不是已取消或频率限制的情况），记录日志但继续尝试
                if not cancel_success:
                    self.write_log(f"订单{original_orderid}撤单失败，但继续尝试重新委托")
                
                # 记录撤单时间（用于频率限制）
                # 只有在实际尝试撤单时才记录（即使失败也算一次尝试）
                self.cancel_times.append(time())
                
                # 如果撤单成功，标记为刚刚撤单成功，这样在后续检查时即使状态是CANCELLED也会继续重新委托
                if cancel_success:
                    chase_order.just_cancelled = True
                    self.write_log(f"订单{original_orderid}撤单成功，标记为刚刚撤单，准备重新委托")
                
                # 重新查询订单状态，确认是否已成交（撤单成功后状态应该是CANCELLED，这是正常的）
                sleep(0.1)  # 短暂等待让撤单生效
                new_status = self._get_order_status(original_orderid)
                if new_status == Status.ALLTRADED:
                    # 订单已成交，移除（撤单前订单已经成交）
                    self.write_log(f"订单{original_orderid}已完全成交，停止重委托并从追价列表中移除")
                    self._safe_del_chase_order(original_orderid)
                    return
                elif new_status == Status.CANCELLED:
                    # 订单已取消（是我们刚才撤单成功的，这是正常情况，继续重新委托）
                    # 注意：just_cancelled 标志已经在上面设置，所以后续检查时会继续执行
                    self.write_log(f"订单{original_orderid}撤单成功，继续重新委托")
                elif new_status is None:
                    # 无法查询状态，可能是订单不存在，继续尝试重新委托
                    self.write_log(f"订单{original_orderid}状态无法查询，继续尝试重新委托")
                
                # 等待撤单完成
                sleep(0.1)
            
            # 3. 获取最新tick（支持主力合约到实际合约的映射）
            tick = self._get_tick_for_chase(chase_order.symbol, chase_order.exchange)
            if not tick or tick.last_price <= 0:
                # 如果无法获取tick，再次检查订单状态
                # 注意：如果撤单成功，订单状态应该是CANCELLED，这是正常的，不应该移除订单
                final_status = self._get_order_status(original_orderid)
                if final_status == Status.ALLTRADED:
                    # 订单已成交，移除
                    self.write_log(f"订单{original_orderid}状态为{final_status}，无法获取tick，从追价列表中移除")
                    # 使用原始订单ID和当前订单ID都尝试移除，确保移除成功
                    self._safe_del_chase_order(original_orderid)
                    return
                elif final_status == Status.CANCELLED:
                    # 订单已取消（撤单成功），这是正常的，应该继续等待tick或重试
                    # 判断标准：如果刚刚撤单成功（just_cancelled=True），应该等待tick更新后重新委托
                    # 如果重试次数未达上限，保留在追价列表中，等待下次tick更新或下次超时检查
                    if chase_order.just_cancelled:
                        self.write_log(f"订单{original_orderid}撤单成功但无法获取tick，等待tick更新后重新委托")
                        # 更新order_time为当前时间，避免立即再次触发超时检查
                        # 这样下次超时检查时，会等待timeout_seconds后才再次尝试
                        chase_order.order_time = time()
                        # 保留在追价列表中，等待tick更新
                        # 下次超时检查时会再次尝试，或者tick更新时会触发重新委托
                        return
                    else:
                        # 这不是刚刚撤单的订单，可能是之前就取消的，移除
                        self.write_log(f"订单{original_orderid}已取消且不是刚刚撤单，从追价列表中移除")
                        self._safe_del_chase_order(original_orderid)
                        if chase_order.orderid != original_orderid:
                            self._safe_del_chase_order(chase_order.orderid)
                        return
                
                # 如果无法获取tick且订单状态无法查询，可能是订单不存在或已取消
                # 为了安全起见，如果重试次数较多，直接移除；否则增加重试计数并等待
                if final_status is None:
                    chase_order.retry_count += 1
                    self.write_log(f"订单{original_orderid}重委托失败：无法获取最新tick，状态无法查询（第{chase_order.retry_count}次重试）")
                    # 如果重试次数达到上限，从追价列表中移除
                    if chase_order.retry_count >= chase_order.config.max_retry_times:
                        self.write_log(f"订单{original_orderid}已达到最大重试次数，从追价列表中移除")
                        self._safe_del_chase_order(original_orderid)
                    return
                else:
                    # 订单状态正常但无法获取tick，记录日志并检查重试次数
                    self.write_log(f"订单{original_orderid}重委托失败：无法获取最新tick（状态：{final_status}，symbol={chase_order.symbol}）")
                    # 记录当前可用的tick keys用于调试
                    available_keys = [k for k, t in self.ticks.items() if t.last_price > 0]
                    if available_keys:
                        self.write_log(f"当前可用的tick keys: {available_keys[:5]}...")  # 只显示前5个
                    # 如果重试次数未达上限，保留在追价列表中，等待下次tick更新
                    # 如果已达到上限，从追价列表中移除
                    if chase_order.retry_count >= chase_order.config.max_retry_times - 1:
                        self.write_log(f"订单{original_orderid}已达到最大重试次数，从追价列表中移除")
                        self._safe_del_chase_order(original_orderid)
                    return
            
            # 4. 计算新价格（使用买一/卖一）
            new_price = self.calculate_chase_price(chase_order, tick, chase_order.direction)
            if new_price <= 0:
                self.write_log(f"订单{original_orderid}重委托失败：无效价格")
                return
            
            # 5. 重新委托 - 保持原始direction和offset，只修改价格
            new_order_req = OrderRequest(
                symbol=chase_order.symbol,
                exchange=chase_order.exchange,
                direction=chase_order.direction,  # 保持原始方向
                offset=chase_order.offset,  # 保持原始offset
                type=VtOrderType.LIMIT,
                price=new_price,  # 只修改价格
                volume=chase_order.volume,  # 保持原始数量
                reference=chase_order.original_reference
            )
            
            # 发送新订单
            old_orderid = chase_order.orderid
            new_orderid = self.send_order(new_order_req)
            if new_orderid:
                normalized_new_orderid = self._normalize_orderid(new_orderid)
                if not normalized_new_orderid:
                    self.write_log(f"订单{original_orderid}重委托成功但无法识别新订单ID，停止追价")
                    return
                chase_order.retry_count += 1
                chase_order.order_time = time()  # 更新委托时间（用于下次超时判断）
                chase_order.orderid = normalized_new_orderid
                # 更新chase_orders字典的key（线程安全）
                if normalized_new_orderid != old_orderid:
                    self._safe_update_chase_order_key(old_orderid, normalized_new_orderid, chase_order)
                    # 如果原始订单ID不同，也尝试删除
                    if original_orderid != old_orderid and original_orderid != normalized_new_orderid:
                        self._safe_del_chase_order(original_orderid)
                
                self.write_log(f"订单{chase_order.original_orderid}重委托成功：新订单{normalized_new_orderid}，价格{new_price:.3f}，第{chase_order.retry_count}次重试")
            else:
                self.write_log(f"订单{original_orderid}重委托失败：发送新订单失败")
                # 如果重试次数未达上限，保留在追价列表中
                # 如果已达到上限，从追价列表中移除
                if chase_order.retry_count >= chase_order.config.max_retry_times - 1:
                    self.write_log(f"订单{original_orderid}已达到最大重试次数，从追价列表中移除")
                    self._safe_del_chase_order(original_orderid)
                    if chase_order.orderid != original_orderid:
                        self._safe_del_chase_order(chase_order.orderid)
                
        except Exception as e:
            # 异常情况下，original_orderid可能未定义，使用chase_order.orderid作为后备
            try:
                orderid_for_log = original_orderid
            except NameError:
                orderid_for_log = getattr(chase_order, 'orderid', 'UNKNOWN')
            
            self.write_log(f"订单{orderid_for_log}重委托异常：{str(e)}")
            # 异常情况下也尝试移除订单，避免订单卡在追价列表中
            # 尝试使用original_orderid移除（如果已定义）
            try:
                self._safe_del_chase_order(original_orderid)
            except NameError:
                pass  # original_orderid未定义，继续使用chase_order.orderid
            
            # 如果original_orderid移除失败或未定义，使用chase_order.orderid
            try:
                if hasattr(chase_order, 'orderid'):
                    self._safe_del_chase_order(chase_order.orderid)
            except AttributeError:
                pass  # chase_order.orderid不存在，忽略错误

    def _try_reorder_with_tick(self, chase_order: ChaseOrder, original_orderid: str) -> None:
        """尝试获取tick并重新委托（用于撤单成功后等待tick的场景）
        
        这个方法专门用于处理撤单成功后等待tick数据的场景。
        在等待期间，会持续更新order_time避免触发撤单，直到获取到tick并成功重新委托。
        """
        try:
            original_orderid = self._normalize_orderid(original_orderid)
            if not original_orderid:
                self.write_log("等待tick重委托失败：无法识别原始订单ID")
                return
            chase_order.orderid = original_orderid
            # 首先检查订单状态，如果已经成交，立即移除，不再重新委托
            order_status = self._get_order_status(original_orderid)
            if order_status == Status.ALLTRADED:
                # 订单已完全成交，立即移除，停止所有追价操作
                self.write_log(f"订单{original_orderid}已完全成交，从追价列表中移除（等待tick时发现）")
                self._safe_del_chase_order(original_orderid)
                if chase_order.orderid != original_orderid:
                    self._safe_del_chase_order(chase_order.orderid)
                return
            
            # 获取最新tick（支持主力合约到实际合约的映射）
            tick = self._get_tick_for_chase(chase_order.symbol, chase_order.exchange)
            if not tick or tick.last_price <= 0:
                # 无法获取tick，保留在追价列表中，等待下次检查
                self.write_log(f"订单{original_orderid}等待tick数据中，暂时无法获取（symbol={chase_order.symbol}），保留在追价列表中")
                # 记录当前可用的tick keys用于调试
                available_keys = [k for k, t in self.ticks.items() if t.last_price > 0]
                if available_keys:
                    self.write_log(f"当前可用的tick keys: {available_keys[:5]}...")  # 只显示前5个
                return
            
            # 计算新价格（使用买一/卖一）
            new_price = self.calculate_chase_price(chase_order, tick, chase_order.direction)
            if new_price <= 0:
                self.write_log(f"订单{original_orderid}重委托失败：无效价格")
                return
            
            # 重新委托 - 保持原始direction和offset，只修改价格
            new_order_req = OrderRequest(
                symbol=chase_order.symbol,
                exchange=chase_order.exchange,
                direction=chase_order.direction,  # 保持原始方向
                offset=chase_order.offset,  # 保持原始offset
                type=VtOrderType.LIMIT,
                price=new_price,  # 只修改价格
                volume=chase_order.volume,  # 保持原始数量
                reference=chase_order.original_reference
            )
            
            # 发送新订单
            old_orderid = chase_order.orderid
            new_orderid = self.send_order(new_order_req)
            if new_orderid:
                normalized_new_orderid = self._normalize_orderid(new_orderid)
                if not normalized_new_orderid:
                    self.write_log(f"订单{original_orderid}等待tick后重委托成功但无法识别新订单ID，停止追价")
                    return
                chase_order.retry_count += 1
                chase_order.order_time = time()  # 更新委托时间为新订单的实际委托时间（用于下次超时判断）
                chase_order.just_cancelled = False  # 重置标志，因为已经重新委托成功
                chase_order.orderid = normalized_new_orderid
                # 更新chase_orders字典的key（线程安全）
                if normalized_new_orderid != old_orderid:
                    self._safe_update_chase_order_key(old_orderid, normalized_new_orderid, chase_order)
                    # 如果原始订单ID不同，也尝试删除
                    if original_orderid != old_orderid and original_orderid != normalized_new_orderid:
                        self._safe_del_chase_order(original_orderid)
                
                self.write_log(f"订单{chase_order.original_orderid}等待tick后重委托成功：新订单{normalized_new_orderid}，价格{new_price:.3f}，第{chase_order.retry_count}次重试")
            else:
                self.write_log(f"订单{original_orderid}等待tick后重委托失败：发送新订单失败")
                # 如果重试次数未达上限，保留在追价列表中
                # 如果已达到上限，从追价列表中移除
                if chase_order.retry_count >= chase_order.config.max_retry_times - 1:
                    self.write_log(f"订单{original_orderid}已达到最大重试次数，从追价列表中移除")
                    self._safe_del_chase_order(original_orderid)
                    if chase_order.orderid != original_orderid:
                        self._safe_del_chase_order(chase_order.orderid)
        except Exception as e:
            self.write_log(f"订单{original_orderid}尝试重新委托异常：{str(e)}")

    def connect_quote(self) -> None:
        """连接行情服务端"""
        self.quote_ctx: OpenQuoteContext = OpenQuoteContext(self.host, self.port)

        class QuoteHandler(StockQuoteHandlerBase):
            gateway: FutuGateway = self

            def on_recv_rsp(self, rsp_str):
                ret_code, content = super(QuoteHandler, self).on_recv_rsp(
                    rsp_str
                )
                if ret_code != RET_OK:
                    return RET_ERROR, content
                self.gateway.process_quote(content)
                return RET_OK, content

        class OrderBookHandler(OrderBookHandlerBase):
            gateway: FutuGateway = self

            def on_recv_rsp(self, rsp_str):
                ret_code, content = super(OrderBookHandler, self).on_recv_rsp(
                    rsp_str
                )
                if ret_code != RET_OK:
                    return RET_ERROR, content
                self.gateway.process_orderbook(content)
                return RET_OK, content

        self.quote_ctx.set_handler(QuoteHandler())
        self.quote_ctx.set_handler(OrderBookHandler())
        self.quote_ctx.start()
        print("开始订阅 MHImain")
        self.write_log("行情接口连接成功!!!")

        req = SubscribeRequest(symbol="MHImain", exchange=Exchange.HKFE)
        self.subscribe(req)


    def connect_trade(self) -> None:
        """连接交易服务端"""
        if self.market == "HK":
            self.trade_ctx = OpenSecTradeContext(filter_trdmarket=TrdMarket.HK, host=self.host, port=self.port,)
        elif self.market == "US":
            self.trade_ctx = OpenSecTradeContext(filter_trdmarket=TrdMarket.US, host=self.host, port=self.port,)
        elif self.market == "HK_FUTURE":
            self.trade_ctx = OpenFutureTradeContext(host=self.host, port=self.port)

        class OrderHandler(TradeOrderHandlerBase):
            gateway: FutuGateway = self

            def on_recv_rsp(self, rsp_str):
                ret_code, content = super(OrderHandler, self).on_recv_rsp(
                    rsp_str
                )
                if ret_code != RET_OK:
                    return RET_ERROR, content
                self.gateway.process_order(content)
                return RET_OK, content

        class DealHandler(TradeDealHandlerBase):
            gateway: FutuGateway = self

            def on_recv_rsp(self, rsp_str):
                ret_code, content = super(DealHandler, self).on_recv_rsp(
                    rsp_str
                )
                if ret_code != RET_OK:
                    return RET_ERROR, content
                self.gateway.process_deal(content)
                return RET_OK, content

        # 交易接口解锁
        code, data = self.trade_ctx.unlock_trade(self.password)
        if code == RET_OK:
            self.write_log("交易接口解锁成功")
        else:
            self.write_log(f"交易接口解锁失败，原因：{data}")

        # 连接交易接口
        self.trade_ctx.set_handler(OrderHandler())
        self.trade_ctx.set_handler(DealHandler())
        self.trade_ctx.start()
        self.write_log("交易接口连接成功")

    def subscribe(self, req: SubscribeRequest) -> None:
        """订阅行情"""
        self.write_log(f"订阅行情入口 {convert_symbol_vt2futu(req.symbol, req.exchange)}")

        for data_type in ["QUOTE", "ORDER_BOOK"]:
            futu_symbol: str = convert_symbol_vt2futu(req.symbol, req.exchange)
            code, data = self.quote_ctx.subscribe(futu_symbol, data_type, True)

            if code:
                self.write_log(f"订阅行情失败：{data}")
        
        # ✅ 性能优化：订阅主力合约时，预初始化主力合约映射缓存
        # 避免用户第一次下单时才初始化，导致226ms延迟
        if req.symbol.endswith("main") and req.exchange == Exchange.HKFE:
            # 检查缓存是否已存在，如果不存在则立即初始化
            if req.symbol not in self.main_contract_mapping:
                self.write_log(f"检测到订阅主力合约 {req.symbol}，预初始化主力合约映射缓存...")
                try:
                    # 调用解析方法，会自动更新缓存
                    actual_code = self._resolve_main_contract(req.symbol, futu_symbol)
                    if actual_code:
                        self.write_log(f"✅ 主力合约映射缓存已预初始化: {req.symbol} -> {actual_code} (避免首次下单延迟)")
                    else:
                        self.write_log(f"⚠️ 主力合约映射缓存初始化失败: {req.symbol}，首次下单时可能需要等待")
                except Exception as e:
                    self.write_log(f"预初始化主力合约映射缓存异常: {str(e)}")
            else:
                cached_symbol = self.main_contract_mapping.get(req.symbol)
                self.write_log(f"主力合约 {req.symbol} 映射缓存已存在: {cached_symbol}，无需初始化")

    def _resolve_main_contract(self, vt_symbol: str, futu_symbol: str) -> str:
        """
        解析主力合约为实际月份合约

        例如：MHImain -> HK.MHI2511

        判断主力合约的策略（按优先级）：
        1. 使用缓存（最快，避免重复API调用）
        2. 使用 get_future_info API 的 origin_code 字段（最可靠）
        3. 从主力合约名称中提取月份代码（如"小恒指期货 (2511)"）
        4. 通过成交量/持仓量比较所有可用月份合约
        5. 选择最近到期的月份合约

        Args:
            vt_symbol: VNPy合约代码（如MHImain）
            futu_symbol: Futu合约代码（如HK_FUTURE.MHImain）

        Returns:
            实际合约代码（如HK.MHI2511），如果解析失败返回None
        """
        try:
            # ✅ 优化：先检查缓存，避免重复API调用（可降低延迟99.5%）
            cached_actual_symbol = self.main_contract_mapping.get(vt_symbol)
            if cached_actual_symbol:
                # 缓存中存储的是实际合约代码（如"MHI2511"），需要转换为完整的富途格式
                cached_code = f"HK.{cached_actual_symbol}"
                self.write_log(f"使用缓存的主力合约映射: {vt_symbol} -> {cached_code} (缓存命中，跳过API调用)")
                return cached_code
            
            # 提取基础代码（去掉main后缀）
            base_symbol = vt_symbol.replace("main", "")  # MHI
            futu_main_code = f"HK.{vt_symbol}"  # HK.MHImain

            # 策略1（最可靠）：使用 get_future_info API 的 origin_code 字段
            # origin_code 是富途官方的主力合约指向，直接返回具体合约代码
            # 这是唯一能准确反映主力切换的方法（不依赖成交量/持仓量比较）
            try:
                ret, data = self.quote_ctx.get_future_info([futu_main_code])
                if ret == 0 and not data.empty:
                    # 打印返回的所有字段，用于调试
                    self.write_log(f"get_future_info 返回字段: {list(data.columns)}")
                    
                    if 'origin_code' in data.columns:
                        origin_code = data.loc[0, 'origin_code']
                        if origin_code and isinstance(origin_code, str) and origin_code.strip():
                            origin_code = origin_code.strip()
                            # origin_code 格式应该是 HK.MHI2512
                            self.write_log(f"★ 主力合约解析成功（策略1-origin_code，最可靠）: {vt_symbol} -> {origin_code}")
                            # ✅ 优化：更新缓存，避免下次重复查询
                            if "." in origin_code:
                                actual_symbol = origin_code.split(".")[-1]
                                self.main_contract_mapping[vt_symbol] = actual_symbol
                                self.write_log(f"已缓存主力合约映射: {vt_symbol} -> {actual_symbol}")
                            return origin_code
                        else:
                            self.write_log(f"策略1: origin_code 字段为空或无效: '{origin_code}'")
                    else:
                        self.write_log(f"策略1: 返回数据中没有 origin_code 字段")
                else:
                    self.write_log(f"策略1: get_future_info 查询失败, ret={ret}")
            except Exception as e:
                self.write_log(f"策略1(origin_code)查询异常: {str(e)}")

            # 策略2：尝试通过查询主力合约行情快照，从名称中提取月份
            code, data = self.quote_ctx.get_market_snapshot([futu_main_code])
            if code == 0 and not data.empty:
                # 从名称中提取合约月份：如"小恒指期货 (2511)" -> 2511
                name = data['name'].values[0]
                if '(' in name and ')' in name:
                    month_code = name.split('(')[1].split(')')[0].strip()
                    if month_code.isdigit() and len(month_code) == 4:
                        actual_code = f"HK.{base_symbol}{month_code}"
                        self.write_log(f"主力合约解析成功（策略2-名称提取）: {vt_symbol} -> {actual_code}")
                        # ✅ 优化：更新缓存
                        actual_symbol = f"{base_symbol}{month_code}"
                        self.main_contract_mapping[vt_symbol] = actual_symbol
                        self.write_log(f"已缓存主力合约映射: {vt_symbol} -> {actual_symbol}")
                        return actual_code

            # 策略3：通过成交量/持仓量比较确定主力合约
            actual_code = self._resolve_main_by_volume(base_symbol)
            if actual_code:
                self.write_log(f"主力合约解析成功（策略3-成交量比较）: {vt_symbol} -> {actual_code}")
                # ✅ 优化：更新缓存
                if "." in actual_code:
                    actual_symbol = actual_code.split(".")[-1]
                    self.main_contract_mapping[vt_symbol] = actual_symbol
                    self.write_log(f"已缓存主力合约映射: {vt_symbol} -> {actual_symbol}")
                return actual_code

            # 策略4：选择最近到期的月份合约
            actual_code = self._resolve_main_by_nearest_expiry(base_symbol)
            if actual_code:
                self.write_log(f"主力合约解析成功（策略4-最近到期）: {vt_symbol} -> {actual_code}")
                # ✅ 优化：更新缓存
                if "." in actual_code:
                    actual_symbol = actual_code.split(".")[-1]
                    self.main_contract_mapping[vt_symbol] = actual_symbol
                    self.write_log(f"已缓存主力合约映射: {vt_symbol} -> {actual_symbol}")
                return actual_code

            self.write_log(f"无法解析主力合约 {vt_symbol}：所有策略均失败")
            return None

        except Exception as e:
            self.write_log(f"解析主力合约异常 {vt_symbol}: {str(e)}")
            return None
    
    def _resolve_main_by_volume(self, base_symbol: str) -> Optional[str]:
        """
        通过成交量比较确定主力合约（后备方案，不够可靠）。
        
        注意：此方法仅作为后备方案！
        持仓量和成交量在主力切换当天可能不准确，因为移仓是渐进的。
        例如：切换日当天旧主力持仓量仍然可能大于新主力。
        
        应优先使用 get_future_info 的 origin_code 字段。
        
        Args:
            base_symbol: 基础合约代码（如MHI）
            
        Returns:
            成交量最大的合约代码（如HK.MHI2512），失败返回None
        """
        try:
            # 获取所有可用的期货合约
            ret, contract_data = self.quote_ctx.get_stock_basicinfo("HK", "FUTURE")
            if ret != 0 or contract_data.empty:
                return None
            
            # 过滤出该品种的月份合约（排除价差合约和虚拟合约）
            # 月份合约格式：HK.MHI2511（基础代码+4位数字）
            month_contracts = []
            for _, row in contract_data.iterrows():
                code = row['code']  # HK.MHI2511
                if '.' in code:
                    symbol = code.split('.')[-1]  # MHI2511
                else:
                    symbol = code
                
                # 检查是否是该品种的月份合约
                if (symbol.startswith(base_symbol) and 
                    len(symbol) == len(base_symbol) + 4 and
                    symbol[-4:].isdigit() and
                    '/' not in code):  # 排除价差合约
                    month_contracts.append(code)
            
            if not month_contracts:
                return None
            
            # 查询所有月份合约的快照数据
            code, snapshot_data = self.quote_ctx.get_market_snapshot(month_contracts)
            if code != 0 or snapshot_data.empty:
                return None
            
            # 记录各合约的成交量，用于日志（仅供参考，不作为主力判断依据）
            self.write_log(f"[后备方案] 各月份合约成交量对比（仅供参考）:")
            for _, row in snapshot_data.iterrows():
                contract_code = row['code']
                volume = row.get('volume', 0)
                open_interest = row.get('open_interest', row.get('position', 0))
                self.write_log(f"  - {contract_code}: 成交量={volume}, 持仓量={open_interest}")
            
            # 只按成交量排序（持仓量在切换日不准确）
            snapshot_data = snapshot_data.sort_values('volume', ascending=False)
            best_contract = snapshot_data.iloc[0]['code']
            volume = snapshot_data.iloc[0]['volume']
            self.write_log(f"[后备方案] 成交量最大: {best_contract} (成交量: {volume})")
            self.write_log(f"[警告] 此结果可能不准确，建议检查 get_future_info 是否可用")
            
            return best_contract
            
        except Exception as e:
            self.write_log(f"通过成交量解析主力合约异常: {str(e)}")
            return None
    
    def _resolve_main_by_nearest_expiry(self, base_symbol: str) -> Optional[str]:
        """
        选择最近到期的月份合约作为主力合约。
        
        对于香港期货，合约代码格式为：MHI2511（YYMM格式）
        
        Args:
            base_symbol: 基础合约代码（如MHI）
            
        Returns:
            最近到期的合约代码（如HK.MHI2511），失败返回None
        """
        try:
            # 获取所有可用的期货合约
            ret, contract_data = self.quote_ctx.get_stock_basicinfo("HK", "FUTURE")
            if ret != 0 or contract_data.empty:
                return None
            
            # 过滤并排序月份合约
            month_contracts = []
            for _, row in contract_data.iterrows():
                code = row['code']  # HK.MHI2511
                if '.' in code:
                    symbol = code.split('.')[-1]  # MHI2511
                else:
                    symbol = code
                
                # 检查是否是该品种的月份合约
                if (symbol.startswith(base_symbol) and 
                    len(symbol) == len(base_symbol) + 4 and
                    symbol[-4:].isdigit() and
                    '/' not in code):  # 排除价差合约
                    # 提取年月代码用于排序
                    year_month = symbol[-4:]  # 2511
                    month_contracts.append((code, year_month))
            
            if not month_contracts:
                return None
            
            # 按年月排序（最近的在前）
            # 注意：年月格式为YYMM，可以直接字符串排序
            month_contracts.sort(key=lambda x: x[1])
            
            # 获取当前年月
            now = datetime.now()
            current_ym = f"{now.year % 100:02d}{now.month:02d}"
            
            # 选择大于等于当前年月的最近合约
            for code, ym in month_contracts:
                if ym >= current_ym:
                    self.write_log(f"最近到期合约: {code} (到期: {ym})")
                    return code
            
            # 如果没有找到，返回第一个（最近的）
            if month_contracts:
                return month_contracts[0][0]
            
            return None
            
        except Exception as e:
            self.write_log(f"通过最近到期解析主力合约异常: {str(e)}")
            return None

    def send_order(self, req: OrderRequest) -> str:
        """委托下单"""
        side: TrdSide = DIRECTION_VT2FUTU[req.direction]

        # ✅ 性能优化：统一设置订单类型（所有类型都是NORMAL）
        futu_order_type: OrderType = OrderType.NORMAL
        
        # ✅ 默认设置：限价单（ManualTrading）自动转换为对手价并启用智能追价
        order_price = req.price
        is_default_opponent = False
        
        # 如果reference是"ManualTrading"（限价单），自动转换为对手价并启用智能追价
        if req.reference == "ManualTrading" or (req.reference == "" and req.type == VtOrderType.LIMIT):
            is_default_opponent = True
            # 获取tick数据计算对手价
            tick_data = self._get_tick_for_chase(req.symbol, req.exchange)
            if tick_data and tick_data.last_price > 0:
                # 计算对手价：买用卖一，卖用买一
                if req.direction == Direction.LONG:
                    order_price = tick_data.ask_price_1 if tick_data.ask_price_1 > 0 else tick_data.last_price
                else:
                    order_price = tick_data.bid_price_1 if tick_data.bid_price_1 > 0 else tick_data.last_price
                
                # 更新reference，启用智能追价（重试2次）
                req.reference = "OPPONENT_Retry2"
                self.write_log(f"默认对手价订单（启用智能追价）：{req.direction.value} -> 对手价 {order_price} (原限价: {req.price})")
            else:
                # 无法获取tick数据，使用原价格，但仍启用追价
                req.reference = "OPPONENT_Retry2"
                self.write_log(f"默认对手价订单（启用智能追价，但无法获取tick，使用原价格）：{req.direction.value} -> {order_price}")
        else:
            # 已指定订单类型（对手价、超价等），使用UI计算的价格
            order_price = req.price

        # 根据订单类型记录日志（保留日志用于调试）
        if req.reference == "OVER":
            self.write_log(f"超价订单：{req.direction.value} -> 使用UI计算的超价 {order_price}")
        elif req.reference == "OPPONENT" or req.type == VtOrderType.OPPONENT or is_default_opponent:
            if is_default_opponent:
                # 日志已在上面输出
                pass
            else:
                self.write_log(f"对手价订单：{req.direction.value} -> 使用UI计算的对手价 {order_price}")
        elif req.type == VtOrderType.OVER:
            self.write_log(f"超价类型：{req.direction.value} -> 使用UI计算的超价 {order_price}")
        elif req.type == VtOrderType.MARKET:
            self.write_log(f"市价单处理（不推荐）：使用UI计算的对手价 {order_price}")
        elif req.type == VtOrderType.LIMIT:
            self.write_log(f"限价单处理：使用用户价格 {order_price}")
        else:
            # 其他订单类型暂不支持
            self.write_log(f"不支持的订单类型：{req.type}")
            return ""

        # 设置调整价格限制（用于风控）
        if req.direction is Direction.LONG:
            adjust_limit: float = 0.05
        else:
            adjust_limit: float = -0.05

        # 转换合约代码
        futu_symbol: str = convert_symbol_vt2futu(req.symbol, req.exchange)

        # ✅ 性能优化：处理主力合约时，先检查缓存，避免不必要的函数调用
        if req.symbol.endswith("main") and req.exchange == Exchange.HKFE:
            # 先检查缓存
            if hasattr(self, 'main_contract_mapping') and req.symbol in self.main_contract_mapping:
                cached_actual_symbol = self.main_contract_mapping[req.symbol]
                if cached_actual_symbol:
                    actual_symbol = f"HK.{cached_actual_symbol}"
                    self.write_log(f"主力合约 {req.symbol} 转换为实际合约 {actual_symbol} (缓存)")
                    futu_symbol = actual_symbol
                else:
                    # 缓存未命中，调用解析函数
                    actual_symbol = self._resolve_main_contract(req.symbol, futu_symbol)
                    if actual_symbol:
                        self.write_log(f"主力合约 {req.symbol} 转换为实际合约 {actual_symbol}")
                        futu_symbol = actual_symbol
                    else:
                        self.write_log(f"警告：无法解析主力合约 {req.symbol}，使用原代码")
            else:
                # 缓存未命中，调用解析函数
                actual_symbol = self._resolve_main_contract(req.symbol, futu_symbol)
                if actual_symbol:
                    self.write_log(f"主力合约 {req.symbol} 转换为实际合约 {actual_symbol}")
                    futu_symbol = actual_symbol
                else:
                    self.write_log(f"警告：无法解析主力合约 {req.symbol}，使用原代码")

        self.write_log(f"转换后的富途合约代码: {futu_symbol}")
        self.write_log(f"当前市场设置: {self.market}")
        self.write_log(f"交易上下文类型: {type(self.trade_ctx).__name__}")
        
        # ⚠️ 已移除调试代码：查询可用期货合约的操作（耗时约500ms，影响性能）
        # 如需调试，可临时取消注释以下代码
        # if req.symbol == "MHImain":
        #     try:
        #         ret, contract_data = self.quote_ctx.get_stock_basicinfo("HK", "FUTURE")
        #         if ret == 0:
        #             mhi_contracts = contract_data[contract_data['code'].str.contains('MHI', na=False)]
        #             if not mhi_contracts.empty:
        #                 self.write_log(f"可用的MHI期货合约: {mhi_contracts['code'].tolist()}")
        #             else:
        #                 self.write_log("未找到MHI期货合约")
        #         else:
        #             self.write_log(f"查询期货合约失败: {contract_data}")
        #     except Exception as e:
        #         self.write_log(f"查询期货合约异常: {str(e)}")
        
        code, data = self.trade_ctx.place_order(
            order_price,  # 使用计算后的价格
            req.volume,
            futu_symbol,
            side,
            futu_order_type,
            trd_env=self.env,
            adjust_limit=adjust_limit,
        )

        if code:
            self.write_log(f"委托失败：{data}")
            return ""

        for ix, row in data.iterrows():
            orderid: str = self._normalize_orderid(str(row["order_id"])) or str(row["order_id"])

        # 创建订单对象
        order: OrderData = req.create_order_data(orderid, self.gateway_name)
        self.on_order(order)

        # 检查是否需要启用追价功能
        chase_config = ChaseConfig(req.reference)
        if chase_config.enabled and self.chase_enabled:
            # 创建追价订单追踪（保存原始订单信息）
            chase_order = ChaseOrder(
                orderid, req.price, chase_config,
                req.symbol, req.exchange, req.direction, req.offset, req.volume, req.reference
            )
            self._safe_set_chase_order(orderid, chase_order)
            self.chase_stats["total_orders"] += 1

            self.write_log(f"启用智能追价: {req.symbol} 订单{orderid} - "
                          f"重试{chase_config.max_retry_times}次")

        return order.vt_orderid

    def _notify_chase_timeout_failure(self, chase_order: ChaseOrder, elapsed_seconds: float) -> None:
        """
        推送追价整体超时失败事件，通知UI显示错误
        
        Args:
            chase_order: 超时的追价订单
            elapsed_seconds: 已等待的秒数
        """
        from datetime import datetime as dt
        
        # 创建一个REJECTED状态的订单事件
        order = OrderData(
            symbol=chase_order.symbol,
            exchange=chase_order.exchange,
            orderid=chase_order.original_orderid,
            direction=chase_order.direction,
            offset=chase_order.offset,
            price=chase_order.original_price,
            volume=chase_order.volume,
            traded=0,
            status=Status.REJECTED,
            datetime=dt.now(CHINA_TZ),
            gateway_name=self.gateway_name,
            reference=f"追价超时({elapsed_seconds:.1f}秒)"
        )
        
        # 推送订单事件
        self.on_order(order)
        
        # 写入醒目的错误日志
        self.write_log(f"❌ 追价委托失败！订单{chase_order.original_orderid} "
                      f"({chase_order.symbol} {chase_order.direction.value} {chase_order.volume}手) "
                      f"等待{elapsed_seconds:.1f}秒后超时，无法获取有效tick数据完成委托")

    def _cancel_order_internal(self, req: CancelRequest) -> Tuple[bool, bool, bool]:
        """
        内部撤单方法，返回详细的撤单结果
        
        Returns:
            (success, already_cancelled, is_rate_limit): 
            - success: 撤单是否成功（包括订单已取消的情况）
            - already_cancelled: 订单是否在撤单前就已经取消
            - is_rate_limit: 是否因频率限制失败
        """
        try:
            futu_orderid = self._normalize_orderid(req.orderid)
            if not futu_orderid:
                self.write_log(f"订单{req.orderid}撤单失败：无法识别订单ID")
                return False, False, False
            if not self.trade_ctx:
                self.write_log(f"订单{req.orderid}撤单失败：交易接口未连接")
                return False, False, False
            
            self.write_log(f"订单{req.orderid}调用撤单API")
            code, data = self.trade_ctx.modify_order(
                ModifyOrderOp.CANCEL, futu_orderid, 0, 0, trd_env=self.env
            )
            
            self.write_log(f"订单{req.orderid}撤单API返回：code={code}, data={data}")

            if code != RET_OK:
                # 检查是否是订单已取消的错误（这种情况下不算失败）
                error_msg = str(data) if data else ""
                error_upper = error_msg.upper()
                # 检查多种可能的已取消订单错误消息格式
                is_already_cancelled = (
                    "CANCELLED" in error_upper or 
                    "不支持撤单" in error_msg or
                    "不支持撤单操作" in error_msg or
                    "当前状态为CANCELLED" in error_upper
                )
                if is_already_cancelled:
                    # 订单已取消，这是正常情况，不记录为错误
                    self.write_log(f"订单{req.orderid}已取消，无需撤单")
                    return True, True, False  # 成功（因为订单已取消），且之前就已取消
                # 检查是否是频率限制错误
                elif "频率" in error_msg or "频率太高" in error_msg or "最多" in error_msg:
                    # 频率限制错误，记录但不继续处理
                    self.write_log(f"订单{req.orderid}撤单失败（频率限制）：{data}")
                    return False, False, True
                else:
                    self.write_log(f"订单{req.orderid}撤单失败：code={code}, data={data}")
                    return False, False, False
            else:
                self.write_log(f"订单{req.orderid}撤单成功")
                # 注意：这里不设置 just_cancelled，因为我们在 _retry_order_with_latest_price 中设置
                return True, False, False  # 成功，且是刚刚取消的
        except Exception as e:
            self.write_log(f"订单{req.orderid}撤单异常：{str(e)}")
            import traceback
            self.write_log(f"订单{req.orderid}撤单异常堆栈：{traceback.format_exc()}")
            return False, False, False

    def cancel_order(self, req: CancelRequest) -> None:
        """委托撤单（公共接口，保持与BaseGateway兼容）
        
        注意：此接口无视智能追价选项，直接执行撤单操作。
        如果订单在追价列表中，会从列表中移除，停止所有追价相关操作。
        """
        normalized_req_orderid = self._normalize_orderid(req.orderid)
        # 检查订单是否在追价列表中（需要检查所有可能的订单ID）
        # 因为订单ID可能会在重委托过程中发生变化
        orderid_to_remove = None
        for orderid, chase_order in list(self._safe_get_all_chase_orders().items()):
            # 检查当前订单ID或原始订单ID是否匹配
            if (orderid == normalized_req_orderid or orderid == req.orderid or
                    chase_order.orderid == normalized_req_orderid or chase_order.orderid == req.orderid or
                    chase_order.original_orderid == normalized_req_orderid or chase_order.original_orderid == req.orderid):
                orderid_to_remove = orderid
                self.write_log(f"订单{req.orderid}通过公共接口撤单，从追价列表中移除（无视智能追价选项）")
                break
        
        # 从追价列表中移除（如果存在）
        if orderid_to_remove:
            self._safe_del_chase_order(orderid_to_remove)
        
        # 执行撤单操作（无视智能追价配置，直接撤单）
        self._cancel_order_internal(req)  # 忽略返回值，保持接口兼容
    
    def cancel_all_chase_orders(self) -> None:
        """取消所有追价订单（包括等待tick数据的订单）
        
        此方法用于全撤时清理所有追价列表中的订单，即使它们不在active_orders中。
        """
        chase_orders_copy = self._safe_get_all_chase_orders()
        if not chase_orders_copy:
            return
        
        self.write_log(f"全撤：清理所有追价订单（共{len(chase_orders_copy)}个）")
        # 清理所有追价订单
        for orderid, chase_order in list(chase_orders_copy.items()):
            # 使用chase_order.orderid作为实际要撤单的订单ID（重委托后可能已更新）
            actual_orderid = self._normalize_orderid(chase_order.orderid) or chase_order.orderid
            chase_order.orderid = actual_orderid
            self.write_log(f"全撤：从追价列表中移除订单{actual_orderid}（symbol={chase_order.symbol}）")
            # 尝试撤单（即使订单可能已经取消）
            try:
                cancel_req = CancelRequest(
                    orderid=actual_orderid,
                    symbol=chase_order.symbol,
                    exchange=chase_order.exchange
                )
                self._cancel_order_internal(cancel_req)
            except Exception as e:
                self.write_log(f"全撤：撤单{actual_orderid}时发生异常：{str(e)}")
        
        # 清空追价列表（线程安全）
        self._safe_clear_chase_orders()
        self.write_log("全撤：所有追价订单已清理完成")

    def start_chase_order(self, orderid: str, vt_symbol: str, direction: Direction) -> None:
        """开始追价订单处理"""
        normalized_orderid = self._normalize_orderid(orderid) or orderid
        chase_order = self._safe_get_chase_order(normalized_orderid)
        if not chase_order:
            return
        if chase_order.is_chasing or chase_order.chase_count >= chase_order.config.max_chase_times:
            return

        # 获取当前市场价格（支持主力合约到实际合约的映射）
        symbol, exchange_str = vt_symbol.split(".")
        exchange = Exchange(exchange_str)
        current_tick = self._get_tick_for_chase(symbol, exchange)
        if not current_tick or current_tick.last_price <= 0:
            return

        # 计算新的追价
        new_price = self.calculate_chase_price(chase_order, current_tick, direction)
        if new_price <= 0:
            return

        # 移除滑点检查（使用买一/卖一价格时滑点限制无意义）

        # 检查追价间隔
        current_time = time()
        if current_time - chase_order.last_chase_time < chase_order.config.chase_interval:
            return

        # 执行追价
        self.execute_chase_order(normalized_orderid, new_price, chase_order)

    def calculate_chase_price(self, chase_order: ChaseOrder, tick: TickData, direction: Direction) -> float:
        """计算追价的新价格 - 直接使用买一/卖一，最快成交"""
        if direction == Direction.LONG:
            # 买单：直接使用卖一价格（对手价）
            return tick.ask_price_1 if tick.ask_price_1 > 0 else tick.last_price
        else:  # Direction.SHORT
            # 卖单：直接使用买一价格（对手价）
            return tick.bid_price_1 if tick.bid_price_1 > 0 else tick.last_price

    def execute_chase_order(self, orderid: str, new_price: float, chase_order: ChaseOrder) -> None:
        """执行追价操作"""
        try:
            orderid = self._normalize_orderid(orderid)
            if not orderid:
                self.write_log("追价失败：无法识别订单ID")
                return
            chase_order.is_chasing = True
            chase_order.chase_count += 1
            chase_order.last_chase_time = time()

            # 修改订单价格
            code, data = self.trade_ctx.modify_order(
                ModifyOrderOp.MODIFY,
                orderid,
                new_price,
                0,  # 不修改数量
                trd_env=self.env
            )

            if code == 0:  # 成功
                chase_order.current_price = new_price
                chase_order.is_chasing = False
                self.chase_stats["successful_chases"] += 1

                slippage = abs(new_price - chase_order.original_price)
                self.chase_stats["total_slippage"] += slippage

                self.write_log(f"追价成功: 订单{orderid} 价格 {chase_order.current_price} -> {new_price} "
                              f"(第{chase_order.chase_count}次追价)")
            else:
                chase_order.is_chasing = False
                self.chase_stats["failed_chases"] += 1
                self.write_log(f"追价失败: 订单{orderid} - {data}")

        except Exception as e:
            chase_order.is_chasing = False
            self.chase_stats["failed_chases"] += 1
            self.write_log(f"追价异常: 订单{orderid} - {str(e)}")

    def on_order_update(self, order: OrderData) -> None:
        """订单状态更新处理"""
        orderid = self._normalize_orderid(order.orderid) or order.orderid

        # 检查订单完全成交时立即更新持仓信息
        if order.status == Status.ALLTRADED:
            # 订单完全成交后立即查询最新持仓
            self.write_log(f"订单 {orderid} 完全成交，立即更新持仓信息")
            self.query_position()

        # 检查是否是追价订单
        chase_order = self._safe_get_chase_order(orderid)
        if chase_order:
            
            # 记录完全成交时间（用于耗时统计）
            if order.status == Status.ALLTRADED and chase_order.fill_time is None:
                chase_order.fill_time = time()
                # 计算委托到完全成交耗时（使用原始下单时间，统计总耗时）
                elapsed_ms = (chase_order.fill_time - chase_order.original_order_time) * 1000
                self.chase_stats["order_to_fill_times"].append(elapsed_ms)
                # 更新统计
                self._update_time_statistics()
                self.write_log(f"订单{orderid}完全成交耗时: {elapsed_ms:.1f}ms（从原始下单开始）")

            # 如果订单被拒绝且还能继续追价，则启动追价
            if (order.status in [Status.REJECTED, Status.CANCELLED] and
                not chase_order.is_chasing and
                chase_order.chase_count < chase_order.config.max_chase_times):

                # 延迟一下再追价
                def delayed_chase():
                    sleep(chase_order.config.chase_interval)
                    self.start_chase_order(orderid, order.vt_symbol, order.direction)

                Thread(target=delayed_chase).start()

            # 如果订单完全成交或取消，清除追价记录
            elif order.status in [Status.ALLTRADED, Status.CANCELLED]:
                # 立即从追价列表中移除，防止继续追价
                if self._safe_del_chase_order(orderid):
                    self.write_log(f"订单{orderid}状态为{order.status.value}，已从追价列表中移除")
                else:
                    # 订单不在chase_orders中，可能是重委托后的新订单，或者已经被移除了
                    # 遍历所有chase_orders，查找是否有相同symbol、direction、offset的订单（可能是重委托前的旧订单）
                    # 注意：这里不删除，因为可能误删其他订单，只记录日志
                    self.write_log(f"订单{orderid}状态为{order.status.value}，但不在追价列表中（可能已被移除或已重委托）")
            
            # 检查未成交超时触发追价（订单状态为NOTTRADED或PARTTRADED且超过阈值）
            elif (order.status in [Status.NOTTRADED, Status.PARTTRADED] and
                  not chase_order.is_chasing and
                  chase_order.chase_count < chase_order.config.max_chase_times):
                # 检查是否超时（使用chase_interval作为触发间隔）
                current_time = time()
                if current_time - chase_order.last_chase_time >= chase_order.config.chase_interval:
                    # 触发追价
                    def delayed_chase():
                        sleep(0.1)  # 短暂延迟
                        self.start_chase_order(orderid, order.vt_symbol, order.direction)
                    Thread(target=delayed_chase).start()

    def _update_time_statistics(self) -> None:
        """更新耗时统计指标"""
        # 更新首次成交耗时统计
        first_trade_times = self.chase_stats["order_to_first_trade_times"]
        if first_trade_times:
            self.chase_stats["avg_order_to_first_trade_ms"] = sum(first_trade_times) / len(first_trade_times)
            self.chase_stats["max_order_to_first_trade_ms"] = max(first_trade_times)
            self.chase_stats["min_order_to_first_trade_ms"] = min(first_trade_times)
        
        # 更新完全成交耗时统计
        fill_times = self.chase_stats["order_to_fill_times"]
        if fill_times:
            self.chase_stats["avg_order_to_fill_ms"] = sum(fill_times) / len(fill_times)
            self.chase_stats["max_order_to_fill_ms"] = max(fill_times)
            self.chase_stats["min_order_to_fill_ms"] = min(fill_times)

    def get_chase_statistics(self) -> dict:
        """获取追价统计信息"""
        stats = self.chase_stats.copy()
        stats["active_chase_orders"] = len(self._safe_get_all_chase_orders())

        if stats["total_orders"] > 0:
            stats["chase_success_rate"] = stats["successful_chases"] / stats["total_orders"] * 100
            stats["average_slippage"] = stats["total_slippage"] / stats["successful_chases"] if stats["successful_chases"] > 0 else 0

        return stats

    def query_contract(self) -> None:
        """查询合约"""
        # get_stock_basicinfo 是没有区分future的， 区分了地区
        if self.market in ["HK", "HK_FUTURE"]:
            market = "HK"
        else:
            market = self.market

        for product, futu_product in PRODUCT_VT2FUTU.items():
            code, data = self.quote_ctx.get_stock_basicinfo(
                market, futu_product
            )

            if code:
                self.write_log(f"查询合约信息失败：{data}")
                return

            for ix, row in data.iterrows():
                symbol, exchange = convert_symbol_futu2vt(row["code"])
                
                # Determine contract size based on symbol
                # For Hong Kong futures:
                # - MHI (小恒指): 10 HKD per point
                # - HSI (大恒指): 50 HKD per point
                # - MCH (小国指): 10 HKD per point
                # - HHI (大国指): 50 HKD per point
                # Default to 1 for other contracts
                size = 1
                # 注意：期货合约使用 Exchange.HKFE（香港期货交易所），不是 Exchange.SEHK（股票交易所）
                if exchange == Exchange.HKFE:
                    symbol_upper = symbol.upper()
                    if symbol_upper.startswith("MHI") or symbol_upper.startswith("MCH"):
                        size = 10  # 小恒指/小国指：每跳 10 港币
                    elif symbol_upper.startswith("HSI") or symbol_upper.startswith("HHI"):
                        size = 50  # 大恒指/大国指：每跳 50 港币
                
                contract: ContractData = ContractData(
                    symbol=symbol,
                    exchange=exchange,
                    name=row["name"],
                    product=product,
                    size=size,
                    pricetick=0.001,
                    history_data=True,
                    net_position=True,
                    gateway_name=self.gateway_name,
                )
                self.on_contract(contract)
                self.contracts[contract.vt_symbol] = contract

        self.write_log("合约信息查询成功")

    def query_account(self) -> None:
        """查询资金"""
        code, data = self.trade_ctx.accinfo_query(trd_env=self.env, acc_id=0)

        if code:
            self.write_log(f"查询账户资金失败：{data}")
            return

        for ix, row in data.iterrows():
            account: AccountData = AccountData(
                accountid=f"{self.gateway_name}_{self.market}",
                balance=float(row["total_assets"]),
                frozen=(float(row["total_assets"]) - float(row["avl_withdrawal_cash"])),
                gateway_name=self.gateway_name,
            )
            self.on_account(account)

    def query_position(self) -> None:
        """查询持仓"""
        code, data = self.trade_ctx.position_list_query(
            trd_env=self.env, acc_id=0
        )

        if code:
            self.write_log(f"查询持仓失败：{data}")
            return

        for ix, row in data.iterrows():
            symbol, exchange = convert_symbol_futu2vt(row["code"])

            # 解析持仓量和方向
            qty = float(row["qty"])

            # Futu API: 正值表示多仓，负值表示空仓
            if qty > 0:
                direction = Direction.LONG
                volume = qty  # 显示实际数量
            elif qty < 0:
                direction = Direction.SHORT
                volume = abs(qty)  # 显示实际数量，去除负号
            else:
                # 无持仓时跳过
                continue

            pos: PositionData = PositionData(
                symbol=symbol,
                exchange=exchange,
                direction=direction,  # 明确的多空方向
                volume=volume,  # 实际持仓数量
                frozen=abs(float(row["qty"]) - float(row["can_sell_qty"])),  # 冻结数量也取绝对值
                price=float(row["cost_price"]),
                pnl=float(row["pl_val"]),
                gateway_name=self.gateway_name,
            )

            self.on_position(pos)

    def query_order(self) -> None:
        """查询未成交委托"""
        code, data = self.trade_ctx.order_list_query("", trd_env=self.env)

        if code:
            self.write_log(f"查询委托失败：{data}")
            return

        self.process_order(data)
        self.write_log("委托查询成功")

    def query_trade(self) -> None:
        """查询成交"""
        code, data = self.trade_ctx.deal_list_query("", trd_env=self.env)

        if code:
            self.write_log(f"查询成交失败：{data}")
            return

        self.process_deal(data)
        self.write_log("成交查询成功")

    def close(self) -> None:
        """关闭接口"""
        if self.quote_ctx:
            self.quote_ctx.close()

        if self.trade_ctx:
            self.trade_ctx.close()
            
        # 等待线程结束并重置线程对象
        if self.thread and self.thread.is_alive():
            # 线程会在查询循环中自然结束，因为连接已关闭
            self.thread.join(timeout=5.0)  # 最多等待5秒
        
        # 重置线程对象，为下次连接做准备
        self.thread = Thread(target=self.query_data)

    def get_tick(self, code) -> TickData:
        """查询Tick数据"""
        tick: TickData = self.ticks.get(code, None)
        symbol, exchange = convert_symbol_futu2vt(code)
        if not tick:
            tick: TickData = TickData(
                symbol=symbol,
                exchange=exchange,
                datetime=datetime.now(CHINA_TZ),
                gateway_name=self.gateway_name,
            )
            self.ticks[code] = tick

        # 获取合约名称
        contract: ContractData = self.contracts.get(tick.vt_symbol, None)
        if contract:
            tick.name = contract.name
        else:
            # 如果是主力合约，尝试显示实际合约信息
            if symbol.endswith("main"):
                actual_symbol = self.main_contract_mapping.get(symbol)
                if actual_symbol:
                    tick.name = f"{symbol} (→{actual_symbol})"
                else:
                    tick.name = symbol

        return tick
    
    def _get_tick_for_chase(self, symbol: str, exchange) -> Optional[TickData]:
        """为追价逻辑获取tick数据，支持主力合约到实际合约的映射
        
        Args:
            symbol: VNPy合约代码（如MHImain或MHI2511）
            exchange: 交易所
            
        Returns:
            TickData对象，如果找不到则返回None
        """
        # ✅ 性能优化：添加tick缓存，避免重复查询
        cache_key = f"{symbol}.{exchange.value}"
        current_time = time()
        
        # 检查缓存（100ms有效期）
        if cache_key in self._tick_cache:
            tick, timestamp = self._tick_cache[cache_key]
            if current_time - timestamp < 0.1:  # 100ms缓存有效期
                return tick  # 缓存命中
        
        # 1. 首先尝试使用原始symbol查找
        futu_code = convert_symbol_vt2futu(symbol, exchange)
        tick = self.ticks.get(futu_code)
        if tick and tick.last_price > 0:
            # 更新缓存
            self._tick_cache[cache_key] = (tick, current_time)
            return tick
        
        # 1.5 富途API返回的行情数据使用"HK.xxx"格式而非"HK_FUTURE.xxx"
        # 如果futu_code是"HK_FUTURE.xxx"格式，也尝试"HK.xxx"格式查找
        if futu_code.startswith("HK_FUTURE."):
            alt_futu_code = futu_code.replace("HK_FUTURE.", "HK.", 1)
            tick = self.ticks.get(alt_futu_code)
            if tick and tick.last_price > 0:
                return tick
        
        # 2. 如果symbol是主力合约（以"main"结尾），尝试解析并查找实际合约的tick数据
        if symbol.endswith("main"):
            try:
                # ✅ 性能优化：先检查缓存，避免调用_resolve_main_contract
                if hasattr(self, 'main_contract_mapping') and symbol in self.main_contract_mapping:
                    cached_actual_symbol = self.main_contract_mapping[symbol]
                    if cached_actual_symbol:
                        actual_code = f"HK.{cached_actual_symbol}"
                    else:
                        actual_code = None
                else:
                    # 缓存未命中，调用解析函数
                    actual_code = self._resolve_main_contract(symbol, futu_code)
                
                if actual_code:
                    # 尝试使用解析出的实际合约代码查找tick
                    tick = self.ticks.get(actual_code)
                    if tick and tick.last_price > 0:
                        self.write_log(f"追价逻辑：使用实际合约{actual_code}的tick数据（原始symbol={symbol}）")
                        return tick
                    
                    # 如果actual_code是"HK.xxx"格式，也尝试"HK_FUTURE.xxx"格式
                    if actual_code.startswith("HK."):
                        alt_code = actual_code.replace("HK.", "HK_FUTURE.", 1)
                        tick = self.ticks.get(alt_code)
                        if tick and tick.last_price > 0:
                            self.write_log(f"追价逻辑：使用实际合约{alt_code}的tick数据（原始symbol={symbol}）")
                            return tick
            except Exception as e:
                self.write_log(f"追价逻辑：解析主力合约{symbol}时异常：{str(e)}")
        
        # 3. 尝试在所有tick数据中查找匹配的合约（通过vt_symbol匹配）
        # 如果symbol是"MHImain"，查找所有以"MHI"开头且以4位数字结尾的合约
        if symbol.endswith("main"):
            base_symbol = symbol.replace("main", "")
            for tick_code, tick_data in self.ticks.items():
                try:
                    tick_symbol, tick_exchange = convert_symbol_futu2vt(tick_code)
                    # 检查是否是同一基础合约且是实际月份合约
                    if (tick_exchange == exchange and 
                        tick_symbol.startswith(base_symbol) and 
                        len(tick_symbol) == len(base_symbol) + 4 and
                        tick_symbol[-4:].isdigit() and
                        tick_data.last_price > 0):
                        self.write_log(f"追价逻辑：通过vt_symbol匹配找到tick数据 {tick_code}（原始symbol={symbol}）")
                        return tick_data
                except:
                    continue
        
        return None

    def query_history(self, req: HistoryRequest) -> List[BarData]:
        """查询历史数据"""
        bars: List[BarData] = []

        # 映射VNPy周期到富途API周期
        # 注意：1小时数据禁止直接从富途API下载，必须从1分钟数据合成
        interval_mapping = {
            Interval.MINUTE: KLType.K_1M,
            # Interval.HOUR: KLType.K_60M,  # 禁止：1小时数据必须从1分钟数据合成
            Interval.DAILY: KLType.K_DAY,
            Interval.WEEKLY: KLType.K_WEEK,
        }

        if req.interval not in interval_mapping:
            if req.interval == Interval.HOUR:
                self.write_log(f"获取K线数据失败，FUTU接口不支持直接下载{req.interval.value}级别历史数据，请从1分钟数据合成")
            else:
                self.write_log(f"获取K线数据失败，FUTU接口暂不提供{req.interval.value}级别历史数据")
            return bars

        futu_ktype = interval_mapping[req.interval]

        symbol: str = convert_symbol_vt2futu(req.symbol, req.exchange)

        # 处理主力合约历史数据查询
        # 说明：查询历史数据时，直接使用主连代码（如HK.MHImain），不转换为当前实际合约
        # 这样返回的是主连历史数据，自动包含各时段的主力合约数据，避免以下问题：
        # - 当提前切换主力合约后（如当前是11月但主力已切换到12月合约MHI2512）
        # - 如果转换为当前主力合约查询历史数据，会查到MHI2512在11月的数据
        # - 但MHI2512在11月时还不活跃，成交量很少，不能真实反映当时的成交情况
        # - 直接使用主连代码查询，富途会返回各时段真正的主力合约数据
        if req.symbol.endswith("main") and req.exchange == Exchange.HKFE:
            # 尝试使用HK.MHImain格式（富途API对主连合约可能使用此格式）
            main_symbol_hk = f"HK.{req.symbol}"
            self.write_log(f"查询历史数据：使用主连代码 {main_symbol_hk}（包含各时段主力合约数据）")
            symbol = main_symbol_hk

        start_date: str = req.start.replace(tzinfo=None).strftime("%Y-%m-%d")
        end_date: str = req.end.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")

        ret, history_df, page_req_key = self.quote_ctx.request_history_kline(
            code=symbol,
            start=start_date,
            end=end_date,
            ktype=futu_ktype
        )
        if ret != RET_OK:
            # 转义花括号避免loguru格式化错误
            error_msg = str(history_df).replace("{", "{{").replace("}", "}}")
            self.write_log(f"获取K线数据失败，原因：{error_msg}")
            return bars

        self.write_log(f"首次查询成功，获取 {len(history_df)} 条数据，还有更多页待获取")

        page_count = 1
        while page_req_key != None:  # 请求后面的所有结果
            self.write_log(f"正在获取第 {page_count + 1} 页数据...")
            ret, data, page_req_key = self.quote_ctx.request_history_kline(
                code=symbol,
                start=start_date,
                end=end_date,
                ktype=futu_ktype,
                page_req_key=page_req_key
            )   # 请求翻页后的数据
            if ret == RET_OK:
                history_df = pd.concat([history_df, data], ignore_index=True)
                has_more = "是" if page_req_key else "否"
                self.write_log(f"第 {page_count + 1} 页获取成功，新增 {len(data)} 条，累计 {len(history_df)} 条，还有更多: {has_more}")
                page_count += 1
            else:
                # 转义花括号避免loguru格式化错误
                error_msg = str(data).replace("{", "{{").replace("}", "}}")
                self.write_log(f"第 {page_count + 1} 页获取失败：{error_msg}")
                break

        self.write_log(f"K线数据获取完成，共 {len(history_df)} 条，正在转换为BarData...")

        history_df["time_key"] = pd.to_datetime(history_df["time_key"])
        history_df["time_key"] = history_df["time_key"] - pd.Timedelta(1, "m")
        history_df["time_key"] = history_df["time_key"].dt.strftime("%Y-%m-%d %H:%M:%S")

        for ix, row in history_df.iterrows():
            bar: BarData = BarData(
                gateway_name=self.gateway_name,
                symbol=req.symbol,
                exchange=req.exchange,
                datetime=generate_datetime(row["time_key"]),
                interval=req.interval,  # 使用请求中指定的周期，而不是硬编码为 MINUTE
                volume=row["volume"],
                turnover=row["turnover"],
                open_interest=0,
                open_price=row["open"],
                high_price=row["high"],
                low_price=row["low"],
                close_price=row["close"]
            )
            bars.append(bar)

        self.write_log(f"K线数据查询成功，返回 {len(bars)} 条K线数据")
        return bars

    def process_quote(self, data) -> None:
        """报价推送"""
        for ix, row in data.iterrows():
            symbol: str = row["code"]

            date: str = row["data_date"].replace("-", "")
            time: str = row["data_time"]
            dt = generate_datetime(f"{row['data_date']} {row['data_time']}")
            dt: datetime = dt.replace(tzinfo=CHINA_TZ)

            tick: TickData = self.get_tick(symbol)
            tick.datetime = dt
            tick.open_price = row["open_price"]
            tick.high_price = row["high_price"]
            tick.low_price = row["low_price"]
            tick.pre_close = row["prev_close_price"]
            tick.last_price = row["last_price"]
            tick.volume = row["volume"]

            if "price_spread" in row:
                spread = row["price_spread"]
                tick.limit_up = tick.last_price + spread * 10
                tick.limit_down = tick.last_price - spread * 10

            self.on_tick(copy(tick))

    def on_tick(self, tick: TickData) -> None:
        super().on_tick(tick)

    def process_orderbook(self, data) -> None:
        """行情信息处理推送"""
        symbol: str = data["code"]
        tick: TickData = self.get_tick(symbol)

        d: dict = tick.__dict__
        if len(data) < 5:
            return

        for i in range(5):
            bid_data = data["Bid"][i]
            ask_data = data["Ask"][i]
            n = i + 1

            d["bid_price_%s" % n] = bid_data[0]
            d["bid_volume_%s" % n] = bid_data[1]
            d["ask_price_%s" % n] = ask_data[0]
            d["ask_volume_%s" % n] = ask_data[1]

        if tick.datetime:
            self.on_tick(copy(tick))

    def process_order(self, data) -> None:
        """委托信息处理推送"""
        for ix, row in data.iterrows():
            if row["order_status"] == OrderStatus.DELETED:
                continue

            direction, offset = DIRECTION_FUTU2VT[row["trd_side"]]
            symbol, exchange = convert_symbol_futu2vt(row["code"])
            orderid = self._normalize_orderid(str(row["order_id"])) or str(row["order_id"])
            order: OrderData = OrderData(
                symbol=symbol,
                exchange=exchange,
                orderid=orderid,
                direction=direction,
                offset=offset,
                price=float(row["price"]),
                volume=row["qty"],
                traded=row["dealt_qty"],
                status=STATUS_FUTU2VT[row["order_status"]],
                datetime=generate_datetime(row["create_time"]),
                gateway_name=self.gateway_name,
            )

            self.on_order(order)

            # 追价逻辑处理
            self.on_order_update(order)

    def process_deal(self, data) -> None:
        """成交信息处理推送"""
        for ix, row in data.iterrows():
            tradeid: str = str(row["deal_id"])
            if tradeid in self.trades:
                continue
            self.trades.add(tradeid)

            direction, offset = DIRECTION_FUTU2VT[row["trd_side"]]
            symbol, exchange = convert_symbol_futu2vt(row["code"])
            orderid = self._normalize_orderid(str(row["order_id"])) or str(row["order_id"])
            
            trade: TradeData = TradeData(
                symbol=symbol,
                exchange=exchange,
                direction=direction,
                offset=offset,
                tradeid=tradeid,
                orderid=orderid,
                price=float(row["price"]),
                volume=row["qty"],
                datetime=generate_datetime(row["create_time"]),
                gateway_name=self.gateway_name,
            )
            
            # 提取交易费用信息（如果富途API返回了费用字段）
            # 富途API可能返回的费用相关字段：commission（佣金）、fee（费用）、cost（成本）等
            if trade.extra is None:
                trade.extra = {}
            
            # 尝试从返回数据中提取费用信息
            fee_fields = ["commission", "fee", "cost", "手续费", "佣金", "费用"]
            for field in fee_fields:
                if field in row:
                    try:
                        trade.extra[field] = float(row[field])
                    except (ValueError, TypeError):
                        pass
            
            # 如果找到了费用信息，记录日志
            if trade.extra:
                fee_info = ", ".join([f"{k}={v}" for k, v in trade.extra.items()])
                self.write_log(f"成交{tradeid}费用信息: {fee_info}")

            self.on_trade(trade)
            
            # 记录首次成交时间（用于耗时统计）
            chase_order = self._safe_get_chase_order(orderid)
            if chase_order and chase_order.first_trade_time is None:
                chase_order.first_trade_time = time()
                # 计算委托到首次成交耗时（使用原始下单时间，统计总耗时）
                elapsed_ms = (chase_order.first_trade_time - chase_order.original_order_time) * 1000
                self.chase_stats["order_to_first_trade_times"].append(elapsed_ms)
                # 更新统计
                self._update_time_statistics()
                self.write_log(f"订单{orderid}首次成交耗时: {elapsed_ms:.1f}ms（从原始下单开始）")


def convert_symbol_futu2vt(code) -> str:
    """
    富途合约名称转换

    注意：Futu API在返回期货数据时可能使用 "HK.MHImain" 格式
    而不是 "HK_FUTURE.MHImain"，需要根据合约代码判断实际交易所
    """
    code_list = code.split(".")
    futu_exchange = code_list[0]
    futu_symbol = ".".join(code_list[1:])

    # 检查是否为期货合约（根据合约代码特征判断）
    symbol_upper = futu_symbol.upper()
    is_futures = False

    # 港股期货合约代码特征：
    # MHI: 小恒指 (Mini HSI)
    # HSI: 大恒指 (Hang Seng Index)
    # MCH: 小国指 (Mini H-shares)
    # HHI: 大国指 (H-shares Index)
    futures_prefixes = ["MHI", "HSI", "MCH", "HHI", "CUS"]  # CUS = China A50

    for prefix in futures_prefixes:
        if symbol_upper.startswith(prefix):
            is_futures = True
            break

    # 如果是期货合约且exchange是HK，则强制转换为HKFE
    if is_futures and futu_exchange == "HK":
        exchange = Exchange.HKFE
    else:
        exchange = EXCHANGE_FUTU2VT.get(futu_exchange, Exchange.SEHK)

    return futu_symbol, exchange


def convert_symbol_vt2futu(symbol, exchange) -> str:
    """veighna合约名称转换"""
    futu_exchange: str = EXCHANGE_VT2FUTU[exchange]
    return f"{futu_exchange}.{symbol}"


def generate_datetime(s: str) -> datetime:
    """生成时间戳"""
    if "." in s:
        dt: datetime = datetime.strptime(s, "%Y-%m-%d %H:%M:%S.%f")
    else:
        dt: datetime = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")

    dt: datetime = dt.replace(tzinfo=CHINA_TZ)
    return dt
