import pandas as pd
from copy import copy
from datetime import datetime
from threading import Thread
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
    HistoryRequest
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
        self.timeout_seconds = 3.0  # 超时阈值（秒）
        self.enable_timeout_cancel = True  # 是否启用超时撤单
        self.max_retry_times = 2  # 最大重委托次数

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
        self.orderid = orderid
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
        
        # 时间戳（用于耗时统计）
        self.order_time = time()
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
        self.chase_enabled: bool = True  # 全局追价开关
        
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
    
    def _normalize_orderid(self, orderid: Optional[str]) -> Optional[str]:
        """去除网关前缀，统一使用富途实际订单ID"""
        if not orderid:
            return orderid
        orderid = str(orderid).strip()
        prefix = f"{self.gateway_name}."
        if orderid.startswith(prefix):
            return orderid[len(prefix):]
        return orderid
    
    def _check_timeout_orders(self) -> None:
        """检查超时订单并执行撤单重委托"""
        if not self.chase_enabled:
            return
        
        current_time = time()
        timeout_orders = []
        
        # 清理过期的撤单时间记录（保留最近30秒的）
        self.cancel_times = [t for t in self.cancel_times if current_time - t < 30.0]
        
        # 查找超时的未成交订单
        for orderid, chase_order in list(self.chase_orders.items()):
            normalized_orderid = self._normalize_orderid(orderid)
            if not normalized_orderid:
                self.write_log(f"订单{orderid}无法规范化订单ID，跳过超时检查")
                continue
            if normalized_orderid != orderid:
                # 更新字典key，确保后续逻辑统一使用富途原始订单ID
                del self.chase_orders[orderid]
                self.chase_orders[normalized_orderid] = chase_order
                orderid = normalized_orderid
            chase_order.orderid = normalized_orderid
            # 检查是否启用超时撤单
            if not chase_order.config.enable_timeout_cancel:
                continue
            
            # 检查是否超过超时阈值
            elapsed = current_time - chase_order.order_time
            if elapsed >= chase_order.config.timeout_seconds:
                # 检查订单状态：如果订单已经成交，立即移除，不再继续追价
                order_status = self._get_order_status(orderid)
                if order_status == Status.ALLTRADED:
                    # 订单已完全成交，立即移除，停止所有追价操作
                    self.write_log(f"订单{orderid}已完全成交，从追价列表中移除（超时检查中发现）")
                    if orderid in self.chase_orders:
                        del self.chase_orders[orderid]
                    continue
                
                # 如果状态查询返回None，可能是订单已成交但查询不到，检查是否还在chase_orders中
                # 如果不在，说明已经被移除了（可能已成交），跳过处理
                if order_status is None:
                    # 再次检查订单是否还在chase_orders中（可能在其他线程中已被移除）
                    if orderid not in self.chase_orders:
                        self.write_log(f"订单{orderid}状态无法查询且已不在追价列表中（可能已成交），跳过处理")
                        continue
                    
                    # 如果订单还在chase_orders中但查询不到状态，可能是订单已成交但状态更新有延迟
                    # 为了安全起见，如果订单不是刚刚撤单的（just_cancelled=False），应该保守处理：
                    # 如果查询不到状态，通常意味着订单已经不存在（已成交或已取消），应该移除
                    if not chase_order.just_cancelled:
                        # 订单不是刚刚撤单的，查询不到状态通常意味着已成交或已取消
                        # 为了安全，直接移除，避免继续追价导致超仓
                        self.write_log(f"订单{orderid}状态无法查询且不是刚刚撤单的订单，可能已成交，从追价列表中移除")
                        if orderid in self.chase_orders:
                            del self.chase_orders[orderid]
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
                    if orderid in self.chase_orders:
                        del self.chase_orders[orderid]
                    continue
                
                timeout_orders.append((orderid, chase_order, elapsed))
        
        # 处理超时订单
        for orderid, chase_order, elapsed in timeout_orders:
            # 在处理前再次检查订单是否还在chase_orders中（可能在其他线程中已被移除，如已成交）
            if orderid not in self.chase_orders:
                self.write_log(f"订单{orderid}已不在追价列表中（可能已成交），跳过处理")
                continue
            
            # 检查撤单频率限制
            if len(self.cancel_times) >= self.max_cancel_per_30s:
                self.write_log(f"订单{orderid}超时{elapsed:.1f}秒，但撤单频率已达上限（30秒内{self.max_cancel_per_30s}次），延迟处理")
                continue
            
            self.write_log(f"订单{orderid}超时{elapsed:.1f}秒，执行撤单重委托")
            self._retry_order_with_latest_price(chase_order)
    
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
            if original_orderid not in self.chase_orders:
                self.write_log(f"订单{original_orderid}已不在追价列表中（可能已成交），停止重委托")
                return
            
            # 1. 先查询订单状态，如果已经取消或已成交，直接移除
            # 注意：如果刚刚撤单成功（just_cancelled=True），即使状态是CANCELLED也应该继续重新委托
            order_status = self._get_order_status(original_orderid)
            
            if order_status is None:
                # 无法查询状态，可能是订单不存在或已取消/成交
                # 再次检查订单是否还在chase_orders中，如果不在，说明已经被移除了（可能已成交），直接返回
                if original_orderid not in self.chase_orders:
                    self.write_log(f"订单{original_orderid}状态无法查询且已不在追价列表中（可能已成交），停止重委托")
                    return
                
                # 如果订单还在chase_orders中但查询不到状态，可能是订单已成交但状态更新有延迟
                # 为了安全起见，如果订单不是刚刚撤单的（just_cancelled=False），应该保守处理：
                # 如果查询不到状态，通常意味着订单已经不存在（已成交或已取消），应该移除
                if not chase_order.just_cancelled:
                    # 订单不是刚刚撤单的，查询不到状态通常意味着已成交或已取消
                    # 为了安全，直接移除，避免继续追价导致超仓
                    self.write_log(f"订单{original_orderid}状态无法查询且不是刚刚撤单的订单，可能已成交，从追价列表中移除")
                    if original_orderid in self.chase_orders:
                        del self.chase_orders[original_orderid]
                    return
                
                # 如果订单刚刚撤单成功（just_cancelled=True），查询不到状态是正常的（订单已从活跃列表中移除）
                # 这种情况下应该继续尝试重新委托
                self.write_log(f"订单{original_orderid}状态无法查询，但刚刚撤单成功，继续尝试重新委托")
            elif order_status == Status.ALLTRADED:
                # 订单已完全成交，移除
                self.write_log(f"订单{original_orderid}已完全成交，停止重委托并从追价列表中移除")
                # 使用原始订单ID和当前订单ID都尝试移除，确保移除成功
                if original_orderid in self.chase_orders:
                    del self.chase_orders[original_orderid]
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
                    if original_orderid in self.chase_orders:
                        del self.chase_orders[original_orderid]
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
                    if original_orderid in self.chase_orders:
                        del self.chase_orders[original_orderid]
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
                    if original_orderid in self.chase_orders:
                        del self.chase_orders[original_orderid]
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
                    if original_orderid in self.chase_orders:
                        del self.chase_orders[original_orderid]
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
                        if original_orderid in self.chase_orders:
                            del self.chase_orders[original_orderid]
                        elif chase_order.orderid in self.chase_orders:
                            del self.chase_orders[chase_order.orderid]
                        return
                
                # 如果无法获取tick且订单状态无法查询，可能是订单不存在或已取消
                # 为了安全起见，如果重试次数较多，直接移除；否则增加重试计数并等待
                if final_status is None:
                    chase_order.retry_count += 1
                    self.write_log(f"订单{original_orderid}重委托失败：无法获取最新tick，状态无法查询（第{chase_order.retry_count}次重试）")
                    # 如果重试次数达到上限，从追价列表中移除
                    if chase_order.retry_count >= chase_order.config.max_retry_times:
                        self.write_log(f"订单{original_orderid}已达到最大重试次数，从追价列表中移除")
                        if original_orderid in self.chase_orders:
                            del self.chase_orders[original_orderid]
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
                        if original_orderid in self.chase_orders:
                            del self.chase_orders[original_orderid]
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
                chase_order.order_time = time()  # 更新委托时间
                chase_order.orderid = normalized_new_orderid
                # 更新chase_orders字典的key
                if normalized_new_orderid != old_orderid:
                    self.chase_orders[normalized_new_orderid] = chase_order
                    # 使用原始订单ID和旧订单ID都尝试移除，确保移除成功
                    if old_orderid in self.chase_orders:
                        del self.chase_orders[old_orderid]
                    if original_orderid in self.chase_orders and original_orderid != old_orderid:
                        del self.chase_orders[original_orderid]
                
                self.write_log(f"订单{original_orderid}重委托成功：新订单{normalized_new_orderid}，价格{new_price:.3f}，第{chase_order.retry_count}次重试")
            else:
                self.write_log(f"订单{original_orderid}重委托失败：发送新订单失败")
                # 如果重试次数未达上限，保留在追价列表中
                # 如果已达到上限，从追价列表中移除
                if chase_order.retry_count >= chase_order.config.max_retry_times - 1:
                    self.write_log(f"订单{original_orderid}已达到最大重试次数，从追价列表中移除")
                    if original_orderid in self.chase_orders:
                        del self.chase_orders[original_orderid]
                    elif chase_order.orderid in self.chase_orders:
                        del self.chase_orders[chase_order.orderid]
                
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
                if original_orderid in self.chase_orders:
                    del self.chase_orders[original_orderid]
                    return
            except NameError:
                pass  # original_orderid未定义，继续使用chase_order.orderid
            except KeyError:
                pass  # 订单不在列表中，继续尝试使用chase_order.orderid
            
            # 如果original_orderid移除失败或未定义，使用chase_order.orderid
            try:
                if hasattr(chase_order, 'orderid') and chase_order.orderid in self.chase_orders:
                    del self.chase_orders[chase_order.orderid]
            except (KeyError, AttributeError):
                pass  # 订单可能已经不在列表中，忽略错误

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
                if original_orderid in self.chase_orders:
                    del self.chase_orders[original_orderid]
                elif chase_order.orderid in self.chase_orders:
                    del self.chase_orders[chase_order.orderid]
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
                chase_order.order_time = time()  # 更新委托时间为新订单的实际委托时间
                chase_order.just_cancelled = False  # 重置标志，因为已经重新委托成功
                chase_order.orderid = normalized_new_orderid
                # 更新chase_orders字典的key
                if normalized_new_orderid != old_orderid:
                    self.chase_orders[normalized_new_orderid] = chase_order
                    # 使用原始订单ID和旧订单ID都尝试移除，确保移除成功
                    if old_orderid in self.chase_orders:
                        del self.chase_orders[old_orderid]
                    if original_orderid in self.chase_orders and original_orderid != old_orderid:
                        del self.chase_orders[original_orderid]
                
                self.write_log(f"订单{original_orderid}等待tick后重委托成功：新订单{normalized_new_orderid}，价格{new_price:.3f}，第{chase_order.retry_count}次重试")
            else:
                self.write_log(f"订单{original_orderid}等待tick后重委托失败：发送新订单失败")
                # 如果重试次数未达上限，保留在追价列表中
                # 如果已达到上限，从追价列表中移除
                if chase_order.retry_count >= chase_order.config.max_retry_times - 1:
                    self.write_log(f"订单{original_orderid}已达到最大重试次数，从追价列表中移除")
                    if original_orderid in self.chase_orders:
                        del self.chase_orders[original_orderid]
                    elif chase_order.orderid in self.chase_orders:
                        del self.chase_orders[chase_order.orderid]
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

    def _resolve_main_contract(self, vt_symbol: str, futu_symbol: str) -> str:
        """
        解析主力合约为实际月份合约

        例如：MHImain -> HK_FUTURE.MHI2511

        Args:
            vt_symbol: VNPy合约代码（如MHImain）
            futu_symbol: Futu合约代码（如HK_FUTURE.MHImain）

        Returns:
            实际合约代码（如HK_FUTURE.MHI2511），如果解析失败返回None
        """
        try:
            # 提取基础代码（去掉main后缀）
            base_symbol = vt_symbol.replace("main", "")  # MHI

            # 尝试通过查询行情快照获取实际合约信息
            # 注意：get_market_snapshot使用HK格式，但我们最终返回HK_FUTURE格式
            code, data = self.quote_ctx.get_market_snapshot([f"HK.{vt_symbol}"])
            if code == 0 and not data.empty:
                # 从名称中提取合约月份：如"小恒指期货 (2511)" -> 2511
                name = data['name'].values[0]
                if '(' in name and ')' in name:
                    month_code = name.split('(')[1].split(')')[0].strip()
                    if month_code.isdigit() and len(month_code) == 4:
                        # 构造实际合约代码，使用HK前缀（富途API期望格式）
                        actual_code = f"HK.{base_symbol}{month_code}"
                        return actual_code

            self.write_log(f"无法解析主力合约 {vt_symbol}：查询失败或数据格式异常")
            return None

        except Exception as e:
            self.write_log(f"解析主力合约异常 {vt_symbol}: {str(e)}")
            return None

    def send_order(self, req: OrderRequest) -> str:
        """委托下单"""
        side: TrdSide = DIRECTION_VT2FUTU[req.direction]

        # 确定订单价格和类型
        order_price = req.price
        futu_order_type: OrderType = OrderType.NORMAL  # 默认限价单

        # 根据VNpy订单类型决定实际执行方式
        if req.reference == "OVER":
            # 超价订单：UI已计算超价，直接使用
            futu_order_type = OrderType.NORMAL
            order_price = req.price
            self.write_log(f"超价订单：{req.direction.value} -> 使用UI计算的超价 {order_price}")

        elif req.reference == "OPPONENT" or req.type == VtOrderType.OPPONENT:
            # 对手价订单：UI已计算对手价，直接使用
            futu_order_type = OrderType.NORMAL
            order_price = req.price
            self.write_log(f"对手价订单：{req.direction.value} -> 使用UI计算的对手价 {order_price}")

        elif req.type == VtOrderType.OVER:
            # 超价类型：UI已计算超价，直接使用
            futu_order_type = OrderType.NORMAL
            order_price = req.price
            self.write_log(f"超价类型：{req.direction.value} -> 使用UI计算的超价 {order_price}")

        elif req.type == VtOrderType.MARKET:
            # 市价单处理：UI已经计算了实际对手价，直接使用（不推荐使用）
            futu_order_type = OrderType.NORMAL
            order_price = req.price
            self.write_log(f"市价单处理（不推荐）：使用UI计算的对手价 {order_price}")

        elif req.type == VtOrderType.LIMIT:
            # 限价单：使用用户指定价格
            futu_order_type = OrderType.NORMAL
            order_price = req.price
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

        # 处理主力合约：MHImain需要转换为实际月份合约
        if req.symbol.endswith("main") and req.exchange == Exchange.HKFE:
            actual_symbol = self._resolve_main_contract(req.symbol, futu_symbol)
            if actual_symbol:
                self.write_log(f"主力合约 {req.symbol} 转换为实际合约 {actual_symbol}")
                futu_symbol = actual_symbol
            else:
                self.write_log(f"警告：无法解析主力合约 {req.symbol}，使用原代码")

        self.write_log(f"转换后的富途合约代码: {futu_symbol}")
        self.write_log(f"当前市场设置: {self.market}")
        self.write_log(f"交易上下文类型: {type(self.trade_ctx).__name__}")
        
        # 尝试查询可用的期货合约
        if req.symbol == "MHImain":
            try:
                ret, contract_data = self.quote_ctx.get_stock_basicinfo("HK", "FUTURE")
                if ret == 0:
                    mhi_contracts = contract_data[contract_data['code'].str.contains('MHI', na=False)]
                    if not mhi_contracts.empty:
                        self.write_log(f"可用的MHI期货合约: {mhi_contracts['code'].tolist()}")
                    else:
                        self.write_log("未找到MHI期货合约")
                else:
                    self.write_log(f"查询期货合约失败: {contract_data}")
            except Exception as e:
                self.write_log(f"查询期货合约异常: {str(e)}")
        
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
            self.chase_orders[orderid] = chase_order
            self.chase_stats["total_orders"] += 1

            self.write_log(f"启用智能追价: {req.symbol} 订单{orderid} - "
                          f"重试{chase_config.max_retry_times}次")

        return order.vt_orderid

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
        for orderid, chase_order in list(self.chase_orders.items()):
            # 检查当前订单ID或原始订单ID是否匹配
            if (orderid == normalized_req_orderid or orderid == req.orderid or
                    chase_order.orderid == normalized_req_orderid or chase_order.orderid == req.orderid):
                orderid_to_remove = orderid
                self.write_log(f"订单{req.orderid}通过公共接口撤单，从追价列表中移除（无视智能追价选项）")
                break
        
        # 从追价列表中移除（如果存在）
        if orderid_to_remove:
            del self.chase_orders[orderid_to_remove]
        
        # 执行撤单操作（无视智能追价配置，直接撤单）
        self._cancel_order_internal(req)  # 忽略返回值，保持接口兼容
    
    def cancel_all_chase_orders(self) -> None:
        """取消所有追价订单（包括等待tick数据的订单）
        
        此方法用于全撤时清理所有追价列表中的订单，即使它们不在active_orders中。
        """
        if not self.chase_orders:
            return
        
        self.write_log(f"全撤：清理所有追价订单（共{len(self.chase_orders)}个）")
        # 清理所有追价订单
        for orderid, chase_order in list(self.chase_orders.items()):
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
        
        # 清空追价列表
        self.chase_orders.clear()
        self.write_log("全撤：所有追价订单已清理完成")

    def start_chase_order(self, orderid: str, vt_symbol: str, direction: Direction) -> None:
        """开始追价订单处理"""
        normalized_orderid = self._normalize_orderid(orderid) or orderid
        if normalized_orderid not in self.chase_orders:
            return

        chase_order = self.chase_orders[normalized_orderid]
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
        if orderid in self.chase_orders:
            chase_order = self.chase_orders[orderid]
            
            # 记录完全成交时间（用于耗时统计）
            if order.status == Status.ALLTRADED and chase_order.fill_time is None:
                chase_order.fill_time = time()
                # 计算委托到完全成交耗时
                elapsed_ms = (chase_order.fill_time - chase_order.order_time) * 1000
                self.chase_stats["order_to_fill_times"].append(elapsed_ms)
                # 更新统计
                self._update_time_statistics()
                self.write_log(f"订单{orderid}完全成交耗时: {elapsed_ms:.1f}ms")

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
                if orderid in self.chase_orders:
                    del self.chase_orders[orderid]
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
        stats["active_chase_orders"] = len(self.chase_orders)

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

        contract: ContractData = self.contracts.get(tick.vt_symbol, None)
        if contract:
            tick.name = contract.name

        return tick
    
    def _get_tick_for_chase(self, symbol: str, exchange) -> Optional[TickData]:
        """为追价逻辑获取tick数据，支持主力合约到实际合约的映射
        
        Args:
            symbol: VNPy合约代码（如MHImain或MHI2511）
            exchange: 交易所
            
        Returns:
            TickData对象，如果找不到则返回None
        """
        # 1. 首先尝试使用原始symbol查找
        futu_code = convert_symbol_vt2futu(symbol, exchange)
        tick = self.ticks.get(futu_code)
        if tick and tick.last_price > 0:
            return tick
        
        # 2. 如果symbol是主力合约（以"main"结尾），尝试解析并查找实际合约的tick数据
        if symbol.endswith("main"):
            try:
                # 解析主力合约
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
        interval_mapping = {
            Interval.MINUTE: KLType.K_1M,
            Interval.HOUR: KLType.K_60M,
            Interval.DAILY: KLType.K_DAY,
            Interval.WEEKLY: KLType.K_WEEK,
        }

        if req.interval not in interval_mapping:
            self.write_log(f"获取K线数据失败，FUTU接口暂不提供{req.interval.value}级别历史数据")
            return bars

        futu_ktype = interval_mapping[req.interval]

        symbol: str = convert_symbol_vt2futu(req.symbol, req.exchange)

        # 处理主力合约：MHImain需要转换为实际月份合约
        if req.symbol.endswith("main") and req.exchange == Exchange.HKFE:
            actual_symbol = self._resolve_main_contract(req.symbol, symbol)
            if actual_symbol:
                self.write_log(f"查询历史数据：主力合约 {req.symbol} 转换为实际合约 {actual_symbol}")
                symbol = actual_symbol
            else:
                self.write_log(f"警告：无法解析主力合约 {req.symbol}，历史数据查询可能失败")
                return bars

        start_date: str = req.start.replace(tzinfo=None).strftime("%Y-%m-%d")
        end_date: str = req.end.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")

        ret, history_df, page_req_key = self.quote_ctx.request_history_kline(
            code=symbol,
            start=start_date,
            end=end_date,
            ktype=futu_ktype
        )
        if ret != RET_OK:
            self.write_log(f"获取K线数据失败，原因：{history_df}")
            return bars

        self.write_log(f"首次查询成功，获取 {len(history_df)} 条数据，page_req_key={page_req_key}")

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
                self.write_log(f"第 {page_count + 1} 页获取成功，新增 {len(data)} 条，累计 {len(history_df)} 条，page_req_key={page_req_key}")
                page_count += 1
            else:
                self.write_log(f"第 {page_count + 1} 页获取失败：{data}")
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
                interval=Interval.MINUTE,
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

            self.on_trade(trade)
            
            # 记录首次成交时间（用于耗时统计）
            if orderid in self.chase_orders:
                chase_order = self.chase_orders[orderid]
                if chase_order.first_trade_time is None:
                    chase_order.first_trade_time = time()
                    # 计算委托到首次成交耗时
                    elapsed_ms = (chase_order.first_trade_time - chase_order.order_time) * 1000
                    self.chase_stats["order_to_first_trade_times"].append(elapsed_ms)
                    # 更新统计
                    self._update_time_statistics()
                    self.write_log(f"订单{orderid}首次成交耗时: {elapsed_ms:.1f}ms")


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
