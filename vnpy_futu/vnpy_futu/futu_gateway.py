import pandas as pd
from copy import copy
from datetime import datetime
from threading import Thread
from time import sleep, time
from typing import Any, Dict, List, Set, Tuple, Union

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
        self.max_chase_times = 3
        self.max_slippage_pct = 0.5
        self.chase_step_pct = 0.05
        self.chase_interval = 0.5

        # 解析reference中的追价配置
        if "_Chase" in reference:
            try:
                parts = reference.split("_")
                for part in parts:
                    if part.startswith("Chase"):
                        self.enabled = True
                        self.max_chase_times = int(part.replace("Chase", ""))
                    elif part.startswith("Slip"):
                        self.max_slippage_pct = float(part.replace("Slip", ""))
                    elif part.startswith("Step"):
                        self.chase_step_pct = float(part.replace("Step", ""))
            except:
                # 解析失败，使用默认值
                self.enabled = True

# 追价订单状态追踪
class ChaseOrder:
    """追价订单状态"""
    def __init__(self, orderid: str, original_price: float, config: ChaseConfig):
        self.orderid = orderid
        self.original_price = original_price
        self.current_price = original_price
        self.chase_count = 0
        self.config = config
        self.last_chase_time = 0.0
        self.is_chasing = False

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

        # 追价统计
        self.chase_stats = {
            "total_orders": 0,          # 总追价订单数
            "successful_chases": 0,     # 成功追价次数
            "failed_chases": 0,         # 失败追价次数
            "total_slippage": 0.0,      # 累计滑点
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

        futu_symbol: str = convert_symbol_vt2futu(req.symbol, req.exchange)
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
            orderid: str = str(row["order_id"])

        # 创建订单对象
        order: OrderData = req.create_order_data(orderid, self.gateway_name)
        self.on_order(order)

        # 检查是否需要启用追价功能
        chase_config = ChaseConfig(req.reference)
        if chase_config.enabled and self.chase_enabled:
            # 创建追价订单追踪
            chase_order = ChaseOrder(orderid, req.price, chase_config)
            self.chase_orders[orderid] = chase_order
            self.chase_stats["total_orders"] += 1

            self.write_log(f"启用智能追价: {req.symbol} 订单{orderid} - "
                          f"追价{chase_config.max_chase_times}次, "
                          f"最大滑点{chase_config.max_slippage_pct}%, "
                          f"步长{chase_config.chase_step_pct}%")

        return order.vt_orderid

    def cancel_order(self, req: CancelRequest) -> None:
        """委托撤单"""
        code, data = self.trade_ctx.modify_order(
            ModifyOrderOp.CANCEL, req.orderid, 0, 0, trd_env=self.env
        )

        if code:
            self.write_log(f"撤单失败：{data}")

    def start_chase_order(self, orderid: str, vt_symbol: str, direction: Direction) -> None:
        """开始追价订单处理"""
        if orderid not in self.chase_orders:
            return

        chase_order = self.chase_orders[orderid]
        if chase_order.is_chasing or chase_order.chase_count >= chase_order.config.max_chase_times:
            return

        # 获取当前市场价格
        current_tick = self.ticks.get(vt_symbol)
        if not current_tick:
            return

        # 计算新的追价
        new_price = self.calculate_chase_price(chase_order, current_tick, direction)
        if new_price <= 0:
            return

        # 检查滑点限制
        slippage_pct = abs(new_price - chase_order.original_price) / chase_order.original_price * 100
        if slippage_pct > chase_order.config.max_slippage_pct:
            self.write_log(f"订单{orderid}滑点超过限制: {slippage_pct:.2f}% > {chase_order.config.max_slippage_pct}%")
            self.chase_stats["failed_chases"] += 1
            return

        # 检查追价间隔
        current_time = time()
        if current_time - chase_order.last_chase_time < chase_order.config.chase_interval:
            return

        # 执行追价
        self.execute_chase_order(orderid, new_price, chase_order)

    def calculate_chase_price(self, chase_order: ChaseOrder, tick: TickData, direction: Direction) -> float:
        """计算追价的新价格"""
        step_pct = chase_order.config.chase_step_pct / 100.0

        if direction == Direction.LONG:
            # 买单：使用ask价格 + 步长
            base_price = tick.ask_price_1 if tick.ask_price_1 > 0 else tick.last_price
            new_price = base_price * (1 + step_pct)
        else:
            # 卖单：使用bid价格 - 步长
            base_price = tick.bid_price_1 if tick.bid_price_1 > 0 else tick.last_price
            new_price = base_price * (1 - step_pct)

        return new_price

    def execute_chase_order(self, orderid: str, new_price: float, chase_order: ChaseOrder) -> None:
        """执行追价操作"""
        try:
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
                              f"(第{chase_order.chase_count}次追价, 滑点{slippage:.3f})")
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
        orderid = order.orderid

        # 检查订单完全成交时立即更新持仓信息
        if order.status == Status.ALLTRADED:
            # 订单完全成交后立即查询最新持仓
            self.write_log(f"订单 {orderid} 完全成交，立即更新持仓信息")
            self.query_position()

        # 检查是否是追价订单
        if orderid in self.chase_orders:
            chase_order = self.chase_orders[orderid]

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
                if orderid in self.chase_orders:
                    del self.chase_orders[orderid]

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
                contract: ContractData = ContractData(
                    symbol=symbol,
                    exchange=exchange,
                    name=row["name"],
                    product=product,
                    size=1,
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

    def query_history(self, req: HistoryRequest) -> List[BarData]:
        """查询历史数据"""
        bars: List[BarData] = []

        if req.interval != Interval.MINUTE:
            self.write_log(f"获取K线数据失败，FUTU接口暂不提供{req.interval.value}级别历史数据")
            return bars

        symbol: str = convert_symbol_vt2futu(req.symbol, req.exchange)
        start_date: str = req.start.replace(tzinfo=None).strftime("%Y-%m-%d")
        end_date: str = req.end.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")

        ret, history_df, page_req_key = self.quote_ctx.request_history_kline(code=symbol, start=start_date, end=end_date, ktype=KLType.K_1M)  # 每页5个，请求第一页
        if ret != RET_OK:
            self.write_log(f"获取K线数据失败，原因：{history_df}")
            return bars

        while page_req_key != None:  # 请求后面的所有结果
            ret, data, page_req_key = self.quote_ctx.request_history_kline(code=symbol, start=start_date, end=end_date, ktype=KLType.K_1M, page_req_key=page_req_key)   # 请求翻页后的数据
            if ret == RET_OK:
                history_df = history_df.append(data, ignore_index=True)
            else:
                self.write_log(f"{data}")

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
        if tick.symbol == "MHImain" and tick.exchange == Exchange.HKFE:
            self.write_log(f"[{tick.datetime}] MHImain last={tick.last_price} volume={tick.volume}")

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
            order: OrderData = OrderData(
                symbol=symbol,
                exchange=exchange,
                orderid=str(row["order_id"]),
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
            trade: TradeData = TradeData(
                symbol=symbol,
                exchange=exchange,
                direction=direction,
                offset=offset,
                tradeid=tradeid,
                orderid=row["order_id"],
                price=float(row["price"]),
                volume=row["qty"],
                datetime=generate_datetime(row["create_time"]),
                gateway_name=self.gateway_name,
            )

            self.on_trade(trade)


def convert_symbol_futu2vt(code) -> str:
    """富途合约名称转换"""
    code_list = code.split(".")
    futu_exchange = code_list[0]
    futu_symbol = ".".join(code_list[1:])
    exchange = EXCHANGE_FUTU2VT[futu_exchange]
    return futu_symbol, exchange


def convert_symbol_vt2futu(symbol, exchange) -> str:
    """veighna合约名称转换"""
    futu_exchange: Exchange = EXCHANGE_VT2FUTU[exchange]
    return f"{futu_exchange}.{symbol}"


def generate_datetime(s: str) -> datetime:
    """生成时间戳"""
    if "." in s:
        dt: datetime = datetime.strptime(s, "%Y-%m-%d %H:%M:%S.%f")
    else:
        dt: datetime = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")

    dt: datetime = dt.replace(tzinfo=CHINA_TZ)
    return dt
