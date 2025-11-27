#!/usr/bin/env python3
"""
MHI期货趋势跟踪策略
基于双移动平均线和ATR止损的量化交易策略

策略逻辑：
1. 双均线系统：快线上穿慢线做多，快线下穿慢线做空
2. ATR止损：基于平均真实波幅设置动态止损
3. 趋势过滤：只在明确趋势下交易，避免震荡市场
4. 仓位管理：固定手数交易，严格风控

适用合约：MHImain.HKFE（小恒指期货主力合约）
开发时间：2024-11-21
"""

from vnpy_ctastrategy import (
    CtaTemplate,
    StopOrder,
    TickData,
    BarData,
    TradeData,
    OrderData,
    ArrayManager,
)
from vnpy.trader.constant import Direction, Offset, Interval, Exchange
from vnpy.trader.utility import create_bar_generator
import talib
import numpy as np


class MHITrendStrategy(CtaTemplate):
    """MHI期货趋势跟踪策略"""

    author = "Claude Code"

    # 策略参数
    fast_window: int = 8        # 快速均线周期
    slow_window: int = 15        # 慢速均线周期
    atr_window: int = 20         # ATR计算周期
    atr_multiplier: float = 3.0  # ATR止损倍数
    fixed_size: int = 1          # 固定手数


    # 趋势过滤参数
    trend_filter_window: int = 20    # 趋势过滤均线周期
    min_trend_strength: float = 0.1  # 最小趋势强度（%）

    # 风控参数
    max_daily_trades: int = 10       # 每日最大交易次数
    max_consecutive_losses: int = 3   # 最大连续亏损次数

    # 策略变量
    fast_ma: float = 0.0
    slow_ma: float = 0.0
    trend_ma: float = 0.0
    atr_value: float = 0.0

    # 持仓相关
    entry_price: float = 0.0
    long_stop: float = 0.0
    short_stop: float = 0.0

    # 统计变量
    daily_trade_count: int = 0
    consecutive_losses: int = 0
    total_trades: int = 0
    win_trades: int = 0

    # 交易状态
    trend_direction: int = 0  # 1: 上升趋势, -1: 下降趋势, 0: 无趋势
    last_signal: str = ""
    signal_time: str = ""

    parameters = [
        "fast_window",
        "slow_window",
        "atr_window",
        "atr_multiplier",
        "fixed_size",
        "trend_filter_window",
        "min_trend_strength",
        "max_daily_trades",
        "max_consecutive_losses"
    ]

    variables = [
        "fast_ma",
        "slow_ma",
        "trend_ma",
        "atr_value",
        "entry_price",
        "long_stop",
        "short_stop",
        "daily_trade_count",
        "consecutive_losses",
        "total_trades",
        "win_trades",
        "trend_direction",
        "last_signal"
    ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """构造函数"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        # 从vt_symbol中提取交易所和合约代码
        symbol, exchange_str = vt_symbol.split(".")
        exchange = Exchange(exchange_str)
        
        # 初始化K线生成器：1分钟K线 -> 5分钟K线（使用HKFE精确时间边界）
        self.bg = create_bar_generator(
            on_bar=self.on_bar,
            window=5,
            on_window_bar=self.on_5min_bar,
            interval=Interval.MINUTE_5,
            exchange=exchange,
            symbol=symbol
        )

        # 初始化数组管理器
        self.am = ArrayManager()

    def on_init(self):
        """策略初始化"""
        self.write_log("MHI趋势跟踪策略初始化")

        # 加载历史数据（10天）
        self.load_bar(10)

        # 初始化统计变量
        self.daily_trade_count = 0
        self.consecutive_losses = 0
        self.total_trades = 0
        self.win_trades = 0

    def on_start(self):
        """策略启动"""
        self.write_log("MHI趋势跟踪策略启动")
        self.write_log(f"参数设置 - 快线:{self.fast_window}, 慢线:{self.slow_window}, ATR:{self.atr_window}")
        self.put_event()

    def on_stop(self):
        """策略停止"""
        self.write_log("MHI趋势跟踪策略停止")

        # 输出策略统计
        if self.total_trades > 0:
            win_rate = self.win_trades / self.total_trades * 100
            self.write_log(f"策略统计 - 总交易:{self.total_trades}, 胜率:{win_rate:.1f}%")

    def on_tick(self, tick: TickData):
        """Tick数据推送"""
        self.bg.update_tick(tick)

    def on_bar(self, bar: BarData):
        """1分钟K线推送"""
        self.bg.update_bar(bar)

    def on_5min_bar(self, bar: BarData):
        """5分钟K线推送（策略主逻辑）"""
        # 先撤销所有挂单
        self.cancel_all()

        # 更新K线数据到数组管理器
        self.am.update_bar(bar)
        if not self.am.inited:
            return

        # 计算技术指标
        self.calculate_indicators()

        # 风控检查
        if not self.risk_check():
            return

        # 判断趋势方向
        self.update_trend_direction()

        # 生成交易信号
        self.generate_signals(bar)

        # 更新界面
        self.put_event()

    def calculate_indicators(self):
        """计算技术指标"""
        # 计算移动平均线
        self.fast_ma = self.am.sma(self.fast_window)
        self.slow_ma = self.am.sma(self.slow_window)
        self.trend_ma = self.am.sma(self.trend_filter_window)

        # 计算ATR
        self.atr_value = self.am.atr(self.atr_window)

    def update_trend_direction(self):
        """更新趋势方向"""
        if len(self.am.close_array) < self.trend_filter_window:
            self.trend_direction = 0
            return

        # 获取当前价格和趋势MA的关系
        current_price = self.am.close_array[-1]

        # 计算趋势MA数组，取前5根K线的值作为对比
        if len(self.am.close_array) >= self.trend_filter_window + 5:
            trend_ma_array = talib.SMA(self.am.close_array, self.trend_filter_window)
            trend_ma_prev = trend_ma_array[-6]  # 6根K线前的趋势MA（-1是当前，-6是前5根）
        else:
            trend_ma_prev = self.trend_ma  # 数据不足时使用当前值

        # 计算趋势强度
        if self.trend_ma > 0:
            trend_strength = abs(current_price - self.trend_ma) / self.trend_ma * 100

            if current_price > self.trend_ma and trend_strength >= self.min_trend_strength:
                if self.trend_ma > trend_ma_prev:  # 趋势MA上升
                    self.trend_direction = 1  # 上升趋势
                else:
                    self.trend_direction = 0  # 趋势不明确
            elif current_price < self.trend_ma and trend_strength >= self.min_trend_strength:
                if self.trend_ma < trend_ma_prev:  # 趋势MA下降
                    self.trend_direction = -1  # 下降趋势
                else:
                    self.trend_direction = 0  # 趋势不明确
            else:
                self.trend_direction = 0  # 无明确趋势

    def risk_check(self):
        """风控检查"""
        # 检查每日交易次数限制
        if self.daily_trade_count >= self.max_daily_trades:
            return False

        # 检查连续亏损次数
        if self.consecutive_losses >= self.max_consecutive_losses:
            return False

        # 检查ATR有效性
        if self.atr_value <= 0:
            return False

        return True

    def generate_signals(self, bar: BarData):
        """生成交易信号"""
        # 检查均线交叉 - 计算前一根K线的快慢线值
        if len(self.am.close_array) >= max(self.fast_window, self.slow_window) + 1:
            fast_ma_array = talib.SMA(self.am.close_array, self.fast_window)
            slow_ma_array = talib.SMA(self.am.close_array, self.slow_window)
            fast_ma_prev = fast_ma_array[-2]  # 前一根K线的快线
            slow_ma_prev = slow_ma_array[-2]  # 前一根K线的慢线
        else:
            # 数据不足时不产生信号
            return

        # 金叉：快线上穿慢线
        golden_cross = (fast_ma_prev <= slow_ma_prev and
                       self.fast_ma > self.slow_ma)

        # 死叉：快线下穿慢线
        death_cross = (fast_ma_prev >= slow_ma_prev and
                      self.fast_ma < self.slow_ma)

        current_time = bar.datetime.strftime("%H:%M:%S")

        # 无持仓时的开仓逻辑
        if self.pos == 0:
            # 做多信号：金叉 + 上升趋势
            if golden_cross and self.trend_direction == 1:
                self.entry_price = bar.close_price
                self.long_stop = self.entry_price - self.atr_value * self.atr_multiplier

                self.buy(self.entry_price, self.fixed_size)
                self.last_signal = f"买入开仓@{self.entry_price:.0f}"
                self.signal_time = current_time

                self.write_log(f"[{current_time}] 金叉做多信号 - 开仓价:{self.entry_price:.0f}, "
                              f"止损价:{self.long_stop:.0f}, 趋势:上升")

            # 做空信号：死叉 + 下降趋势
            elif death_cross and self.trend_direction == -1:
                self.entry_price = bar.close_price
                self.short_stop = self.entry_price + self.atr_value * self.atr_multiplier

                self.short(self.entry_price, self.fixed_size)
                self.last_signal = f"卖出开仓@{self.entry_price:.0f}"
                self.signal_time = current_time

                self.write_log(f"[{current_time}] 死叉做空信号 - 开仓价:{self.entry_price:.0f}, "
                              f"止损价:{self.short_stop:.0f}, 趋势:下降")

        # 持有多仓时的平仓逻辑
        elif self.pos > 0:
            # 平多条件：死叉信号 或 ATR止损
            should_close_long = (death_cross or
                               bar.close_price <= self.long_stop)

            if should_close_long:
                self.sell(bar.close_price, abs(self.pos))
                close_reason = "死叉" if death_cross else "ATR止损"
                self.last_signal = f"平多@{bar.close_price:.0f}({close_reason})"
                self.signal_time = current_time

                self.write_log(f"[{current_time}] {close_reason}平多 - 平仓价:{bar.close_price:.0f}")

        # 持有空仓时的平仓逻辑
        elif self.pos < 0:
            # 平空条件：金叉信号 或 ATR止损
            should_close_short = (golden_cross or
                                bar.close_price >= self.short_stop)

            if should_close_short:
                self.cover(bar.close_price, abs(self.pos))
                close_reason = "金叉" if golden_cross else "ATR止损"
                self.last_signal = f"平空@{bar.close_price:.0f}({close_reason})"
                self.signal_time = current_time

                self.write_log(f"[{current_time}] {close_reason}平空 - 平仓价:{bar.close_price:.0f}")

    def on_order(self, order: OrderData):
        """委托回报"""
        # 记录订单状态变化
        if order.status.value in ["已撤销", "拒单"]:
            self.write_log(f"订单{order.orderid} {order.status.value}: {order.direction.value} {order.volume}手")

    def on_trade(self, trade: TradeData):
        """成交回报"""
        self.daily_trade_count += 1
        self.total_trades += 1

        # 计算盈亏（简化版，实际应该考虑手续费）
        if trade.offset == Offset.CLOSE:
            if self.entry_price > 0:
                if trade.direction == Direction.SHORT:  # 平多
                    pnl = (trade.price - self.entry_price) * trade.volume * 10  # MHI每跳10港币
                else:  # 平空
                    pnl = (self.entry_price - trade.price) * trade.volume * 10

                if pnl > 0:
                    self.win_trades += 1
                    self.consecutive_losses = 0
                    self.write_log(f"平仓盈利: {pnl:.0f} 港币")
                else:
                    self.consecutive_losses += 1
                    self.write_log(f"平仓亏损: {pnl:.0f} 港币")

        self.write_log(f"成交回报: {trade.direction.value} {trade.volume}手 @ {trade.price:.0f}")
        self.put_event()

    def on_stop_order(self, stop_order: StopOrder):
        """停止单回报"""
        pass

    def get_strategy_stats(self) -> dict:
        """获取策略统计信息"""
        if self.total_trades > 0:
            win_rate = self.win_trades / self.total_trades * 100
        else:
            win_rate = 0

        return {
            "total_trades": self.total_trades,
            "win_trades": self.win_trades,
            "win_rate": win_rate,
            "daily_trades": self.daily_trade_count,
            "consecutive_losses": self.consecutive_losses,
            "trend_direction": self.trend_direction,
            "last_signal": self.last_signal,
            "signal_time": self.signal_time
        }

