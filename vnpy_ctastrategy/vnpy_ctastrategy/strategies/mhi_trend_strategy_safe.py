#!/usr/bin/env python3
"""
MHI期货趋势跟踪策略（安全版本）
基于双移动平均线和ATR止损的量化交易策略

优化点：
1. 提高了ATR止损倍数，减少止损频率
2. 加强了趋势过滤，减少交易频率
3. 降低了每日最大交易次数
4. 减少了连续亏损限制

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


class MHITrendStrategySafe(CtaTemplate):
    """MHI期货趋势跟踪策略（安全版本）"""

    author = "Claude Code"

    # 策略参数（优化的安全版本）
    fast_window: int = 8        # 快速均线周期
    slow_window: int = 15        # 慢速均线周期
    atr_window: int = 34         # ATR计算周期
    atr_multiplier: float = 3.0  # ATR止损倍数（从2.5提高到3.0）
    fixed_size: int = 1          # 固定手数

    # 趋势过滤参数（放宽过滤以增加交易频率）
    trend_filter_window: int = 60    # 趋势过滤均线周期
    min_trend_strength: float = 1  # 最小趋势强度（%）从1.0%降低到0.3%，增加交易机会
    enable_trend_ma_check: bool = False  # 是否检查趋势MA上升/下降（False=只检查价格与趋势MA的关系）

    # 风控参数（更严格）
    max_daily_trades: int = 6        # 每日最大交易次数（从10减少到5）
    max_consecutive_losses: int = 3  # 最大连续亏损次数（从3减少到2）

    # 策略变量（5分钟周期）
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
    last_trade_date: str = ""  # 上一次交易的日期（用于重置每日交易计数）

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
        "enable_trend_ma_check",
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
        
        # 初始化K线生成器（使用HKFE精确时间边界）
        # 1分钟BarGenerator：从tick聚合到1分钟K线
        # 当1分钟K线生成后，会先调用on_bar（传入1分钟K线），然后调用on_1min_bar
        # 注意：如果回测选择tick周期，on_tick会调用bg_1min.update_tick()
        #      如果回测选择1分钟周期，回测引擎直接调用on_bar（传入1分钟K线）
        self.bg_1min = create_bar_generator(
            on_bar=self.on_bar,
            window=1,
            on_window_bar=self.on_1min_bar,
            interval=Interval.MINUTE,
            exchange=exchange,
            symbol=symbol
        )
        
        # 5分钟BarGenerator：从1分钟K线聚合到5分钟K线
        # 当5分钟K线生成后，会调用on_5min_bar
        # 注意：on_bar中收到1分钟K线后，会更新这个聚合器
        self.bg_5min = create_bar_generator(
            on_bar=self.on_bar,
            window=5,
            on_window_bar=self.on_5min_bar,
            interval=Interval.MINUTE_5,
            exchange=exchange,
            symbol=symbol
        )

        # 初始化数组管理器（分别用于1分钟和5分钟）
        self.am_1min = ArrayManager()  # 1分钟周期数组管理器
        self.am_5min = ArrayManager()  # 5分钟周期数组管理器
        
        # 1分钟周期指标
        self.fast_ma_1min: float = 0.0
        self.slow_ma_1min: float = 0.0
        self.trend_ma_1min: float = 0.0
        self.atr_value_1min: float = 0.0
        self.trend_direction_1min: int = 0
        
        # 处理标记：用于避免on_bar和on_1min_bar重复处理
        self._processing_1min = False

    def on_init(self):
        """策略初始化"""
        self.write_log("MHI趋势跟踪策略（安全版本）初始化")

        # 加载历史数据（10天）
        self.load_bar(10)

        # 初始化统计变量
        self.daily_trade_count = 0
        self.consecutive_losses = 0
        self.total_trades = 0
        self.win_trades = 0
        self.last_trade_date = ""
        
        # 初始化风控日志标志
        self._loss_limit_logged = False
        self._daily_limit_logged = False

    def on_start(self):
        """策略启动"""
        self.write_log("MHI趋势跟踪策略（安全版本）启动")
        self.write_log(f"参数设置 - 快线:{self.fast_window}, 慢线:{self.slow_window}, "
                      f"ATR:{self.atr_window}, 止损倍数:{self.atr_multiplier}")
        self.write_log(f"趋势过滤 - 窗口:{self.trend_filter_window}, 强度:{self.min_trend_strength}%, "
                      f"MA检查:{self.enable_trend_ma_check}")
        self.put_event()

    def on_stop(self):
        """策略停止"""
        self.write_log("MHI趋势跟踪策略（安全版本）停止")

        # 输出策略统计
        if self.total_trades > 0:
            win_rate = self.win_trades / self.total_trades * 100
            self.write_log(f"策略统计 - 总交易:{self.total_trades}, 胜率:{win_rate:.1f}%")

    def on_tick(self, tick: TickData):
        """Tick数据推送"""
        # 更新1分钟BarGenerator（从tick聚合到1分钟K线）
        # 当1分钟K线生成后，会调用on_1min_bar，然后on_1min_bar内部会更新5分钟聚合器
        self.bg_1min.update_tick(tick)
        
        # 注意：5分钟的聚合会在on_1min_bar中通过bg_5min.update_bar完成

    def on_bar(self, bar: BarData):
        """K线推送回调（由BarGenerator或回测引擎调用）"""
        # 这个方法会被两种情况调用：
        # 1. 当数据源是tick时，bg_1min聚合生成1分钟K线后调用（传入1分钟K线）
        #    此时bg_1min会同时调用on_1min_bar，所以这里只需要更新5分钟聚合器
        # 2. 当回测选择1分钟周期时，回测引擎直接调用（传入1分钟K线）
        #    此时不会调用on_1min_bar，所以这里需要处理1分钟逻辑
        
        # 如果是由bg_1min调用的，on_1min_bar会被自动调用，这里只需要更新5分钟聚合器
        if self._processing_1min:
            # on_1min_bar正在处理，这里只更新5分钟聚合器
            self.bg_5min.update_bar(bar)
        else:
            # 回测引擎直接调用on_bar（1分钟周期回测），需要处理1分钟逻辑
            self.on_1min_bar(bar)
            # 同时更新5分钟聚合器
            self.bg_5min.update_bar(bar)

    def on_1min_bar(self, bar: BarData):
        """1分钟K线推送（1分钟周期策略逻辑）"""
        # 设置标记，避免on_bar重复处理
        self._processing_1min = True
        
        try:
            # 更新K线数据到1分钟数组管理器
            self.am_1min.update_bar(bar)
            if not self.am_1min.inited:
                return

            # 计算1分钟周期技术指标
            self.calculate_indicators_1min()

            # 风控检查（传入bar用于日期重置）
            if not self.risk_check(bar):
                return

            # 判断1分钟周期趋势方向
            self.update_trend_direction_1min()

            # 生成1分钟周期交易信号
            self.generate_signals_1min(bar)

            # 更新界面
            self.put_event()
        finally:
            # 重置标记
            self._processing_1min = False

    def on_5min_bar(self, bar: BarData):
        """5分钟K线推送（5分钟周期策略逻辑）"""
        # 更新K线数据到5分钟数组管理器
        self.am_5min.update_bar(bar)
        if not self.am_5min.inited:
            return

        # 先撤销所有挂单
        self.cancel_all()

        # 计算5分钟周期技术指标
        self.calculate_indicators()

        # 风控检查（传入bar用于日期重置）
        if not self.risk_check(bar):
            return

        # 判断5分钟周期趋势方向
        self.update_trend_direction()

        # 生成5分钟周期交易信号
        self.generate_signals(bar)

        # 更新界面
        self.put_event()

    def calculate_indicators_1min(self):
        """计算1分钟周期技术指标"""
        # 计算移动平均线
        self.fast_ma_1min = self.am_1min.sma(self.fast_window)
        self.slow_ma_1min = self.am_1min.sma(self.slow_window)
        self.trend_ma_1min = self.am_1min.sma(self.trend_filter_window)

        # 计算ATR
        self.atr_value_1min = self.am_1min.atr(self.atr_window)

    def calculate_indicators(self):
        """计算5分钟周期技术指标"""
        # 计算移动平均线
        self.fast_ma = self.am_5min.sma(self.fast_window)
        self.slow_ma = self.am_5min.sma(self.slow_window)
        self.trend_ma = self.am_5min.sma(self.trend_filter_window)

        # 计算ATR
        self.atr_value = self.am_5min.atr(self.atr_window)

    def update_trend_direction_1min(self):
        """更新1分钟周期趋势方向"""
        if len(self.am_1min.close_array) < self.trend_filter_window:
            self.trend_direction_1min = 0
            return

        # 获取当前价格和趋势MA的关系
        current_price = self.am_1min.close_array[-1]

        # 计算趋势MA数组，取前5根K线的值作为对比
        if len(self.am_1min.close_array) >= self.trend_filter_window + 5:
            trend_ma_array = talib.SMA(self.am_1min.close_array, self.trend_filter_window)
            trend_ma_prev = trend_ma_array[-6]  # 6根K线前的趋势MA（-1是当前，-6是前5根）
        else:
            trend_ma_prev = self.trend_ma_1min  # 数据不足时使用当前值

        # 计算趋势强度
        if self.trend_ma_1min > 0:
            trend_strength = abs(current_price - self.trend_ma_1min) / self.trend_ma_1min * 100

            if current_price > self.trend_ma_1min and trend_strength >= self.min_trend_strength:
                # 如果启用了趋势MA检查，需要趋势MA上升才认为是上升趋势
                if self.enable_trend_ma_check:
                    if self.trend_ma_1min > trend_ma_prev:  # 趋势MA上升
                        self.trend_direction_1min = 1  # 上升趋势
                    else:
                        self.trend_direction_1min = 0  # 趋势不明确
                else:
                    # 简化版：只要价格在趋势MA上方且偏离足够，就认为是上升趋势
                    self.trend_direction_1min = 1  # 上升趋势
            elif current_price < self.trend_ma_1min and trend_strength >= self.min_trend_strength:
                # 如果启用了趋势MA检查，需要趋势MA下降才认为是下降趋势
                if self.enable_trend_ma_check:
                    if self.trend_ma_1min < trend_ma_prev:  # 趋势MA下降
                        self.trend_direction_1min = -1  # 下降趋势
                    else:
                        self.trend_direction_1min = 0  # 趋势不明确
                else:
                    # 简化版：只要价格在趋势MA下方且偏离足够，就认为是下降趋势
                    self.trend_direction_1min = -1  # 下降趋势
            else:
                self.trend_direction_1min = 0  # 无明确趋势（趋势强度不足）

    def update_trend_direction(self):
        """更新5分钟周期趋势方向"""
        if len(self.am_5min.close_array) < self.trend_filter_window:
            self.trend_direction = 0
            return

        # 获取当前价格和趋势MA的关系
        current_price = self.am_5min.close_array[-1]

        # 计算趋势MA数组，取前5根K线的值作为对比
        if len(self.am_5min.close_array) >= self.trend_filter_window + 5:
            trend_ma_array = talib.SMA(self.am_5min.close_array, self.trend_filter_window)
            trend_ma_prev = trend_ma_array[-6]  # 6根K线前的趋势MA（-1是当前，-6是前5根）
        else:
            trend_ma_prev = self.trend_ma  # 数据不足时使用当前值

        # 计算趋势强度
        if self.trend_ma > 0:
            trend_strength = abs(current_price - self.trend_ma) / self.trend_ma * 100

            if current_price > self.trend_ma and trend_strength >= self.min_trend_strength:
                # 如果启用了趋势MA检查，需要趋势MA上升才认为是上升趋势
                if self.enable_trend_ma_check:
                    if self.trend_ma > trend_ma_prev:  # 趋势MA上升
                        self.trend_direction = 1  # 上升趋势
                    else:
                        self.trend_direction = 0  # 趋势不明确
                else:
                    # 简化版：只要价格在趋势MA上方且偏离足够，就认为是上升趋势
                    self.trend_direction = 1  # 上升趋势
            elif current_price < self.trend_ma and trend_strength >= self.min_trend_strength:
                # 如果启用了趋势MA检查，需要趋势MA下降才认为是下降趋势
                if self.enable_trend_ma_check:
                    if self.trend_ma < trend_ma_prev:  # 趋势MA下降
                        self.trend_direction = -1  # 下降趋势
                    else:
                        self.trend_direction = 0  # 趋势不明确
                else:
                    # 简化版：只要价格在趋势MA下方且偏离足够，就认为是下降趋势
                    self.trend_direction = -1  # 下降趋势
            else:
                self.trend_direction = 0  # 无明确趋势（趋势强度不足）

    def risk_check(self, bar: BarData = None):
        """风控检查"""
        # 检查连续亏损次数
        if self.consecutive_losses >= self.max_consecutive_losses:
            # 只在第一次触发时记录日志，避免重复日志
            if not self._loss_limit_logged:
                self.write_log(f"风控限制：连续亏损{self.consecutive_losses}次，达到上限{self.max_consecutive_losses}次，暂停交易")
                self._loss_limit_logged = True
            return False

        # 检查ATR有效性（使用1分钟或5分钟周期的ATR，哪个有值用哪个）
        atr_valid = (self.atr_value_1min > 0 or self.atr_value > 0)
        if not atr_valid:
            return False

        # 检查每日交易次数限制（需要在日期变化时重置）
        if bar is not None:
            current_date = bar.datetime.strftime("%Y-%m-%d")
            # 如果日期变化，重置每日交易计数和日志标志
            if self.last_trade_date != "" and current_date != self.last_trade_date:
                if self.daily_trade_count > 0:
                    self.write_log(f"日期变化：{self.last_trade_date} -> {current_date}，重置每日交易计数")
                self.daily_trade_count = 0
                self._daily_limit_logged = False  # 重置日志标志，新日期可以再次记录日志

        # 检查每日交易次数是否超过限制
        if self.daily_trade_count >= self.max_daily_trades:
            # 只在第一次触发时记录日志，避免重复日志
            if not self._daily_limit_logged:
                current_date = bar.datetime.strftime("%Y-%m-%d") if bar else "未知日期"
                self.write_log(f"风控限制：{current_date} 当日交易次数已达上限{self.max_daily_trades}次，暂停当日交易")
                self._daily_limit_logged = True
            return False

        return True

    def generate_signals_1min(self, bar: BarData):
        """生成1分钟周期交易信号"""
        # 检查均线交叉 - 计算前一根K线的快慢线值
        if len(self.am_1min.close_array) >= max(self.fast_window, self.slow_window) + 1:
            fast_ma_array = talib.SMA(self.am_1min.close_array, self.fast_window)
            slow_ma_array = talib.SMA(self.am_1min.close_array, self.slow_window)
            fast_ma_prev = fast_ma_array[-2]  # 前一根K线的快线
            slow_ma_prev = slow_ma_array[-2]  # 前一根K线的慢线
        else:
            # 数据不足时不产生信号
            return

        # 金叉：快线上穿慢线
        golden_cross = (fast_ma_prev <= slow_ma_prev and
                       self.fast_ma_1min > self.slow_ma_1min)

        # 死叉：快线下穿慢线
        death_cross = (fast_ma_prev >= slow_ma_prev and
                      self.fast_ma_1min < self.slow_ma_1min)

        current_time = bar.datetime.strftime("%H:%M:%S")
        
        # 诊断日志：记录信号和趋势状态（仅在关键时刻输出）
        if golden_cross or death_cross:
            if self.pos == 0:
                if golden_cross and self.trend_direction_1min != 1:
                    trend_desc = "无趋势" if self.trend_direction_1min == 0 else f"下降趋势(需上升)"
                    self.write_log(f"[1分钟][{current_time}] 金叉信号被趋势过滤 - 当前趋势:{trend_desc}, 快线:{self.fast_ma_1min:.0f}, 慢线:{self.slow_ma_1min:.0f}")
                elif death_cross and self.trend_direction_1min != -1:
                    trend_desc = "无趋势" if self.trend_direction_1min == 0 else f"上升趋势(需下降)"
                    self.write_log(f"[1分钟][{current_time}] 死叉信号被趋势过滤 - 当前趋势:{trend_desc}, 快线:{self.fast_ma_1min:.0f}, 慢线:{self.slow_ma_1min:.0f}")

        # 无持仓时的开仓逻辑
        if self.pos == 0:
            # 做多信号：金叉 + 上升趋势
            if golden_cross and self.trend_direction_1min == 1:
                signal_price = bar.close_price
                self.long_stop = signal_price - self.atr_value_1min * self.atr_multiplier

                self.buy(signal_price, self.fixed_size)
                self.last_signal = f"[1分钟]买入开仓@{signal_price:.0f}"
                self.signal_time = current_time

                self.write_log(f"[1分钟][{current_time}] 金叉做多信号 - 信号价:{signal_price:.0f}, "
                              f"止损价:{self.long_stop:.0f}, 趋势:上升")

            # 做空信号：死叉 + 下降趋势
            elif death_cross and self.trend_direction_1min == -1:
                signal_price = bar.close_price
                self.short_stop = signal_price + self.atr_value_1min * self.atr_multiplier

                self.short(signal_price, self.fixed_size)
                self.last_signal = f"[1分钟]卖出开仓@{signal_price:.0f}"
                self.signal_time = current_time

                self.write_log(f"[1分钟][{current_time}] 死叉做空信号 - 信号价:{signal_price:.0f}, "
                              f"止损价:{self.short_stop:.0f}, 趋势:下降")

        # 持有多仓时的平仓逻辑
        elif self.pos > 0:
            # 平多条件：死叉信号 或 ATR止损
            should_close_long = (death_cross or
                               bar.close_price <= self.long_stop)

            if should_close_long:
                self.sell(bar.close_price, abs(self.pos))
                close_reason = "死叉" if death_cross else "ATR止损"
                self.last_signal = f"[1分钟]平多@{bar.close_price:.0f}({close_reason})"
                self.signal_time = current_time

                self.write_log(f"[1分钟][{current_time}] {close_reason}平多 - 平仓价:{bar.close_price:.0f}")

        # 持有空仓时的平仓逻辑
        elif self.pos < 0:
            # 平空条件：金叉信号 或 ATR止损
            should_close_short = (golden_cross or
                                bar.close_price >= self.short_stop)

            if should_close_short:
                self.cover(bar.close_price, abs(self.pos))
                close_reason = "金叉" if golden_cross else "ATR止损"
                self.last_signal = f"[1分钟]平空@{bar.close_price:.0f}({close_reason})"
                self.signal_time = current_time

                self.write_log(f"[1分钟][{current_time}] {close_reason}平空 - 平仓价:{bar.close_price:.0f}")

    def generate_signals(self, bar: BarData):
        """生成5分钟周期交易信号"""
        # 检查均线交叉 - 计算前一根K线的快慢线值
        if len(self.am_5min.close_array) >= max(self.fast_window, self.slow_window) + 1:
            fast_ma_array = talib.SMA(self.am_5min.close_array, self.fast_window)
            slow_ma_array = talib.SMA(self.am_5min.close_array, self.slow_window)
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
        
        # 诊断日志：记录信号和趋势状态（仅在关键时刻输出）
        if golden_cross or death_cross:
            if self.pos == 0:
                if golden_cross and self.trend_direction != 1:
                    trend_desc = "无趋势" if self.trend_direction == 0 else f"下降趋势(需上升)"
                    self.write_log(f"[5分钟][{current_time}] 金叉信号被趋势过滤 - 当前趋势:{trend_desc}, 快线:{self.fast_ma:.0f}, 慢线:{self.slow_ma:.0f}")
                elif death_cross and self.trend_direction != -1:
                    trend_desc = "无趋势" if self.trend_direction == 0 else f"上升趋势(需下降)"
                    self.write_log(f"[5分钟][{current_time}] 死叉信号被趋势过滤 - 当前趋势:{trend_desc}, 快线:{self.fast_ma:.0f}, 慢线:{self.slow_ma:.0f}")

        # 无持仓时的开仓逻辑
        if self.pos == 0:
            # 做多信号：金叉 + 上升趋势
            if golden_cross and self.trend_direction == 1:
                signal_price = bar.close_price
                self.long_stop = signal_price - self.atr_value * self.atr_multiplier

                self.buy(signal_price, self.fixed_size)
                self.last_signal = f"[5分钟]买入开仓@{signal_price:.0f}"
                self.signal_time = current_time

                self.write_log(f"[5分钟][{current_time}] 金叉做多信号 - 信号价:{signal_price:.0f}, "
                              f"止损价:{self.long_stop:.0f}, 趋势:上升")

            # 做空信号：死叉 + 下降趋势
            elif death_cross and self.trend_direction == -1:
                signal_price = bar.close_price
                self.short_stop = signal_price + self.atr_value * self.atr_multiplier

                self.short(signal_price, self.fixed_size)
                self.last_signal = f"[5分钟]卖出开仓@{signal_price:.0f}"
                self.signal_time = current_time

                self.write_log(f"[5分钟][{current_time}] 死叉做空信号 - 信号价:{signal_price:.0f}, "
                              f"止损价:{self.short_stop:.0f}, 趋势:下降")

        # 持有多仓时的平仓逻辑
        elif self.pos > 0:
            # 平多条件：死叉信号 或 ATR止损
            should_close_long = (death_cross or
                               bar.close_price <= self.long_stop)

            if should_close_long:
                self.sell(bar.close_price, abs(self.pos))
                close_reason = "死叉" if death_cross else "ATR止损"
                self.last_signal = f"[5分钟]平多@{bar.close_price:.0f}({close_reason})"
                self.signal_time = current_time

                self.write_log(f"[5分钟][{current_time}] {close_reason}平多 - 平仓价:{bar.close_price:.0f}")

        # 持有空仓时的平仓逻辑
        elif self.pos < 0:
            # 平空条件：金叉信号 或 ATR止损
            should_close_short = (golden_cross or
                                bar.close_price >= self.short_stop)

            if should_close_short:
                self.cover(bar.close_price, abs(self.pos))
                close_reason = "金叉" if golden_cross else "ATR止损"
                self.last_signal = f"[5分钟]平空@{bar.close_price:.0f}({close_reason})"
                self.signal_time = current_time

                self.write_log(f"[5分钟][{current_time}] {close_reason}平空 - 平仓价:{bar.close_price:.0f}")

    def on_order(self, order: OrderData):
        """委托回报"""
        # 记录订单状态变化
        if order.status.value in ["已撤销", "拒单"]:
            self.write_log(f"订单{order.orderid} {order.status.value}: {order.direction.value} {order.volume}手")

    def on_trade(self, trade: TradeData):
        """成交回报"""
        self.write_log(f"成交回报: {trade.direction.value} {trade.volume}手 @ {trade.price:.0f}")

        # 开仓时记录开仓价格
        if trade.offset == Offset.OPEN:
            self.daily_trade_count += 1
            # 更新交易日期
            self.last_trade_date = trade.datetime.strftime("%Y-%m-%d") if trade.datetime else ""
            # 开仓时记录实际成交价作为开仓价（可能和信号价有差异）
            if trade.direction == Direction.LONG:  # 做多
                self.entry_price = trade.price
                self.write_log(f"做多开仓 - 实际成交价:{trade.price:.0f}, 止损价:{self.long_stop:.0f}, "
                              f"今日交易次数:{self.daily_trade_count}/{self.max_daily_trades}")
            else:  # 做空
                self.entry_price = trade.price
                self.write_log(f"做空开仓 - 实际成交价:{trade.price:.0f}, 止损价:{self.short_stop:.0f}, "
                              f"今日交易次数:{self.daily_trade_count}/{self.max_daily_trades}")

        # 平仓时计算盈亏并统计
        elif trade.offset == Offset.CLOSE:
            if self.entry_price > 0:
                # 计算盈亏（简化版，实际应该考虑手续费）
                if trade.direction == Direction.SHORT:  # 平多
                    pnl = (trade.price - self.entry_price) * trade.volume * 10  # MHI每跳10港币
                else:  # 平空
                    pnl = (self.entry_price - trade.price) * trade.volume * 10

                # 统计完整交易（开仓+平仓算一笔）
                self.total_trades += 1

                if pnl > 0:
                    self.win_trades += 1
                    self.consecutive_losses = 0
                    self._loss_limit_logged = False  # 盈利时重置连续亏损日志标志
                    self.write_log(f"平仓盈利: {pnl:.0f} 港币 (开仓价:{self.entry_price:.0f}, 平仓价:{trade.price:.0f})")
                else:
                    self.consecutive_losses += 1
                    self.write_log(f"平仓亏损: {pnl:.0f} 港币 (开仓价:{self.entry_price:.0f}, 平仓价:{trade.price:.0f})")
                    # 如果达到连续亏损上限，记录日志标志会在下次risk_check时设置

                # 重置开仓价
                self.entry_price = 0.0

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

