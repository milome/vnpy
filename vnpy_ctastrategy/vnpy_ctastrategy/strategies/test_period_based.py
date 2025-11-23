#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动生成的策略文件
基于模型文件: TEST_IMPORT
"""

from vnpy_ctastrategy import (
    CtaTemplate,
    StopOrder,
    TickData,
    BarData,
    TradeData,
    OrderData,
    BarGenerator,
    ArrayManager
)

from mflang import REF, BARSLAST, SUMBARS, BARPOS, HHV
from mflang.import_parser import ImportParser, PeriodType
from mflang.model_loader import load_model
from vnpy.trader.constant import Direction, Offset
import numpy as np

class TestPeriodBased(CtaTemplate):
    """基于模型文件 TEST_IMPORT 生成的策略"""

    author = "MFLang Generator"

    # 策略参数
    parameters = [
        "fixed_size",      # 固定交易手数
        "stop_loss_pct",   # 止损百分比（如0.02表示2%）
        "take_profit_pct", # 止盈百分比（如0.04表示4%）
        "max_daily_trades", # 每日最大交易次数
        "max_consecutive_losses", # 最大连续亏损次数
    ]

    # 策略变量
    variables = ["CC", "ISBUYTREND", "entry_price", "long_stop", "short_stop", 
                 "daily_trade_count", "consecutive_losses", "total_trades", "win_trades"]

    # 参数默认值
    fixed_size: int = 1
    stop_loss_pct: float = 0.02  # 2%止损
    take_profit_pct: float = 0.04  # 4%止盈
    max_daily_trades: int = 10
    max_consecutive_losses: int = 5

    # 策略变量
    CC = 0.0
    ISBUYTREND = 0.0
    entry_price = 0.0
    long_stop = 0.0
    short_stop = 0.0
    daily_trade_count = 0
    consecutive_losses = 0
    total_trades = 0
    win_trades = 0
    last_trade_date = None

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """初始化策略"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        
        # K线管理器
        self.bg = BarGenerator(self.on_bar)
        self.am = ArrayManager()
        
        # 跨周期数据管理器
        # 使用BarGenerator合成5分钟K线
        self.bg_5min = BarGenerator(self.on_bar, 5, self.on_5min_bar)
        # 根据 PERIOD 和 N 的组合创建 ArrayManager，相同周期的引用共享同一个 ArrayManager
        self.min_5_am = ArrayManager()  # MIN5周期数据（共享）
        
        # 跨周期变量缓存（每个 var_name 有独立的缓存）
        self.min5_vars = {}  # MIN5 的变量缓存
        
        # 解析 #IMPORT 语句
        self.import_statements = ImportParser.parse_code("""
        #IMPORT[MIN,5,MIN5_OPEN] AS MIN5
        """)
        
        # 加载被引用的模型文件
        self.min5_model = load_model("MIN5_OPEN")
        
        # 用于追踪ISBUYTREND变化的变量
        self._last_isbuytrend = None

    def on_init(self):
        """策略初始化回调"""
        self.write_log("策略初始化")
        self.load_bar(10)  # 加载10根K线

    def on_start(self):
        """策略启动回调"""
        self.write_log("策略启动")

    def on_stop(self):
        """策略停止回调"""
        self.write_log("策略停止")

    def on_tick(self, tick: TickData):
        """Tick数据回调"""
        self.bg.update_tick(tick)
        self.bg_5min.update_tick(tick)

    def on_bar(self, bar: BarData):
        """1分钟K线数据回调"""
        self.am.update_bar(bar)
        
        # 将1分钟K线推送到5分钟BarGenerator，用于合成5分钟K线
        self.bg_5min.update_bar(bar)
        
        if not self.am.inited:
            return
        
        # 重置每日交易计数（如果是新的一天）
        current_date = bar.datetime.date()
        if self.last_trade_date != current_date:
            self.daily_trade_count = 0
            self.last_trade_date = current_date
        
        # 注意：跨周期变量的计算在on_5min_bar中进行
        # 这里使用缓存的跨周期变量值
        
        # 计算策略变量
        # 计算 CC: C
        self.CC = self._calculate_variable_cc()
        # 计算 ISBUYTREND: C > MIN5.PREV_OPEN
        self.ISBUYTREND = self._calculate_variable_isbuytrend()
        
        # 添加调试日志（每100根K线记录一次，避免日志过多）
        if len(self.am.close) % 100 == 0:
            min5_vars = getattr(self, "min5_vars", {})
            prev_open_value = min5_vars.get("PREV_OPEN", np.nan)
            current_close = self.am.close[-1] if len(self.am.close) > 0 else np.nan
            log_msg = (
                f"状态: 时间={bar.datetime.strftime('%Y-%m-%d %H:%M')}, "
                f"收盘价={current_close:.2f}, MIN5.PREV_OPEN={prev_open_value:.2f}, "
                f"ISBUYTREND={self.ISBUYTREND}, 持仓={self.pos}"
            )
            if self.pos == 0:
                log_msg += (
                    f", 每日交易次数={self.daily_trade_count}/{self.max_daily_trades}, "
                    f"连续亏损={self.consecutive_losses}/{self.max_consecutive_losses}"
                )
            else:
                current_pnl_pct = ((bar.close_price - self.entry_price) / self.entry_price * 100) if self.entry_price > 0 else 0.0
                log_msg += f", 开仓价={self.entry_price:.0f}, 浮动盈亏={current_pnl_pct:.2f}%"
            self.write_log(log_msg)
        
        # 检查止损止盈
        self._check_stop_loss_take_profit(bar)
        
        # 策略逻辑
        self._on_strategy_logic(bar)
        
        # 更新UI显示
        self.put_event()
    
    def on_5min_bar(self, bar: BarData):
        """5分钟K线数据回调（由BarGenerator合成）"""
        # 更新5分钟ArrayManager
        self.min_5_am.update_bar(bar)
        
        if not self.min_5_am.inited:
            return
        
        # 计算跨周期变量
        for stmt in self.import_statements:
            if stmt.period.value == "MIN" and stmt.n == 5:
                self._calculate_cross_period_vars(stmt.var_name, stmt.formula, stmt.period.value, stmt.n)
                self.write_log(f"跨周期变量已更新: {stmt.var_name}, 数据条数: {len(self.min_5_am.close)}")

    def _is_period_bar(self, bar: BarData, period_type: str, n: int) -> bool:
        """
        判断是否是目标周期的K线
        
        参数:
            period_type: 周期类型（来自 #IMPORT 语句的 PERIOD，如 "MIN", "HOUR", "DAY"）
            n: 周期参数（来自 #IMPORT 语句的 N，如 5 表示5分钟）
        
        说明:
            根据 #IMPORT 语句中的 PERIOD 和 N 来判断当前K线是否为目标周期
            例如：#IMPORT[MIN,5,MIN5_OPEN] AS MIN5
                 PERIOD=MIN, N=5，表示需要5分钟周期的数据
                 判断条件：bar.datetime.minute % 5 == 0
        """
        if period_type == "MIN":
            # 分钟周期：判断分钟数是否能被N整除
            # 例如：N=5 表示5分钟周期，分钟数 % 5 == 0 时是5分钟K线
            return bar.datetime.minute % n == 0
        elif period_type == "HOUR":
            # 小时周期：判断小时数是否能被N整除，且分钟数为0
            # 例如：N=2 表示2小时周期，小时数 % 2 == 0 且分钟数为0时是2小时K线
            return bar.datetime.hour % n == 0 and bar.datetime.minute == 0
        elif period_type == "CUSHOUR":
            # 自定义小时周期：判断小时数是否能被N整除，且分钟数为0
            return bar.datetime.hour % n == 0 and bar.datetime.minute == 0
        elif period_type == "DAY":
            # 日周期：判断是否是交易日开始（小时数为0，分钟数为0）
            return bar.datetime.hour == 0 and bar.datetime.minute == 0
        elif period_type == "WEEK":
            # 周周期：判断是否是周一且小时数为0，分钟数为0
            return bar.datetime.weekday() == 0 and bar.datetime.hour == 0 and bar.datetime.minute == 0
        elif period_type == "MONTH":
            # 月周期：判断是否是月初且小时数为0，分钟数为0
            return bar.datetime.day == 1 and bar.datetime.hour == 0 and bar.datetime.minute == 0
        elif period_type == "QUARTER":
            # 季度周期：判断是否是季度初且小时数为0，分钟数为0
            # 季度初：1月、4月、7月、10月的1号
            return (bar.datetime.month in [1, 4, 7, 10] and 
                    bar.datetime.day == 1 and 
                    bar.datetime.hour == 0 and 
                    bar.datetime.minute == 0)
        elif period_type == "YEAR":
            # 年周期：判断是否是年初且小时数为0，分钟数为0
            return (bar.datetime.month == 1 and 
                    bar.datetime.day == 1 and 
                    bar.datetime.hour == 0 and 
                    bar.datetime.minute == 0)
        else:
            # 其他周期类型，需要根据实际情况实现
            return False

    def _calculate_cross_period_vars(self, var_name: str, model_name: str, period_type: str, period_n: int):
        """
        计算跨周期变量
        
        参数:
            var_name: 跨周期变量名（如 "MIN5"），来自 #IMPORT 语句的 VAR
            model_name: 模型文件名（如 "MIN5_OPEN"），来自 #IMPORT 语句的 FORMULA
            period_type: 周期类型（如 "MIN"），来自 #IMPORT 语句的 PERIOD
            period_n: 周期参数（如 5），来自 #IMPORT 语句的 N
        
        说明:
            通过 PERIOD 和 N 来确定 ArrayManager，而不是通过 var_name
            - 相同 PERIOD 和 N 的 #IMPORT 语句共享同一个 ArrayManager
            - ArrayManager 命名规则：{period_type.lower()}_{period_n}_am（如 min_5_am）
            - 每个 var_name 有独立的变量缓存（vars_cache）
        """
        # 加载模型文件
        model = load_model(model_name)
        
        # 根据 PERIOD 和 N 获取对应的 ArrayManager
        # 命名规则：{period_type.lower()}_{period_n}_am（如 min_5_am）
        # 相同周期的引用共享同一个 ArrayManager
        period_key = f"{period_type.lower()}_{period_n}"
        am = getattr(self, f"{period_key}_am")
        
        # 计算模型中的变量
        vars_cache = {}
        for var_name_in_model, var_expr in model.items():
            # 解析并计算变量
            # 这里需要根据表达式类型执行相应的计算
            # 示例：处理 REF(O,1)
            if "REF(O,1)" in var_expr:
                open_prices = am.open
                if len(open_prices) >= 2:  # 至少需要2根K线才能计算REF(O,1)
                    result = REF(open_prices, 1)
                    vars_cache[var_name_in_model] = result[-1] if len(result) > 0 else np.nan
                else:
                    vars_cache[var_name_in_model] = np.nan
            elif "REF(C,1)" in var_expr:
                close_prices = am.close
                if len(close_prices) >= 2:  # 至少需要2根K线才能计算REF(C,1)
                    result = REF(close_prices, 1)
                    vars_cache[var_name_in_model] = result[-1] if len(result) > 0 else np.nan
                else:
                    vars_cache[var_name_in_model] = np.nan
            elif var_expr.strip() == "C":
                vars_cache[var_name_in_model] = am.close[-1] if len(am.close) > 0 else np.nan
            elif var_expr.strip() == "O":
                vars_cache[var_name_in_model] = am.open[-1] if len(am.open) > 0 else np.nan
            # 可以添加更多表达式类型的处理
        
        # 缓存结果
        setattr(self, f"{var_name.lower()}_vars", vars_cache)
        
        # 添加调试日志，记录计算的变量值
        for var_name_in_model, var_value in vars_cache.items():
            if not np.isnan(var_value):
                self.write_log(f"跨周期变量 {var_name}.{var_name_in_model} = {var_value:.2f}")

    def _calculate_variable_cc(self) -> float:
        """计算变量 CC: C"""
        return self.am.close[-1] if len(self.am.close) > 0 else 0.0

    def _calculate_variable_isbuytrend(self) -> float:
        """计算变量 ISBUYTREND: C > MIN5.PREV_OPEN"""
        # 获取跨周期引用 MIN5.PREV_OPEN
        min5_vars = getattr(self, "min5_vars", {})
        prev_open_value = min5_vars.get("PREV_OPEN", np.nan)
        
        current_close = self.am.close[-1] if len(self.am.close) > 0 else np.nan
        if np.isnan(current_close) or np.isnan(prev_open_value):
            # 添加调试日志（只在第一次或偶尔记录，避免日志过多）
            if np.isnan(prev_open_value) and len(self.am.close) % 50 == 0:
                self.write_log(f"警告: MIN5.PREV_OPEN 为 NaN, 当前收盘价: {current_close:.2f}, min5_vars keys: {list(min5_vars.keys())}")
            return 0.0
        result = current_close > prev_open_value
        isbuytrend_value = 1.0 if result else 0.0
        # 当ISBUYTREND变化时记录日志
        if hasattr(self, '_last_isbuytrend') and self._last_isbuytrend != isbuytrend_value:
            self.write_log(f"ISBUYTREND变化: {self._last_isbuytrend} -> {isbuytrend_value}, 当前收盘价={current_close:.2f}, MIN5.PREV_OPEN={prev_open_value:.2f}")
        self._last_isbuytrend = isbuytrend_value
        return isbuytrend_value

    def _risk_check(self) -> bool:
        """风控检查"""
        # 检查每日交易次数限制
        if self.daily_trade_count >= self.max_daily_trades:
            if len(self.am.close) % 100 == 0:  # 每100根K线记录一次，避免日志过多
                self.write_log(f"风控限制: 每日交易次数已达上限 {self.max_daily_trades}")
            return False
        
        # 检查连续亏损次数
        if self.consecutive_losses >= self.max_consecutive_losses:
            if len(self.am.close) % 100 == 0:  # 每100根K线记录一次，避免日志过多
                self.write_log(f"风控限制: 连续亏损次数已达上限 {self.max_consecutive_losses}")
            return False
        
        return True
    
    def _check_stop_loss_take_profit(self, bar: BarData):
        """检查止损止盈"""
        current_price = bar.close_price
        
        # 持有多仓时的止损止盈检查
        if self.pos > 0 and self.entry_price > 0:
            # 止损检查
            if self.long_stop > 0 and current_price <= self.long_stop:
                self.sell(bar.close_price, abs(self.pos))
                pnl_pct = ((bar.close_price - self.entry_price) / self.entry_price * 100) if self.entry_price > 0 else 0.0
                self.write_log(f"止损平多 - 开仓价:{self.entry_price:.0f}, 平仓价:{bar.close_price:.0f}, 亏损:{pnl_pct:.2f}%")
                self.entry_price = 0.0
                self.long_stop = 0.0
            # 止盈检查
            elif self.take_profit_pct > 0:
                take_profit_price = self.entry_price * (1 + self.take_profit_pct)
                if current_price >= take_profit_price:
                    self.sell(bar.close_price, abs(self.pos))
                    pnl_pct = ((bar.close_price - self.entry_price) / self.entry_price * 100) if self.entry_price > 0 else 0.0
                    self.write_log(f"止盈平多 - 开仓价:{self.entry_price:.0f}, 平仓价:{bar.close_price:.0f}, 盈利:{pnl_pct:.2f}%")
                    self.entry_price = 0.0
                    self.long_stop = 0.0
        
        # 持有空仓时的止损止盈检查
        elif self.pos < 0 and self.entry_price > 0:
            # 止损检查
            if self.short_stop > 0 and current_price >= self.short_stop:
                self.cover(bar.close_price, abs(self.pos))
                pnl_pct = ((self.entry_price - bar.close_price) / self.entry_price * 100) if self.entry_price > 0 else 0.0
                self.write_log(f"止损平空 - 开仓价:{self.entry_price:.0f}, 平仓价:{bar.close_price:.0f}, 亏损:{pnl_pct:.2f}%")
                self.entry_price = 0.0
                self.short_stop = 0.0
            # 止盈检查
            elif self.take_profit_pct > 0:
                take_profit_price = self.entry_price * (1 - self.take_profit_pct)
                if current_price <= take_profit_price:
                    self.cover(bar.close_price, abs(self.pos))
                    pnl_pct = ((self.entry_price - bar.close_price) / self.entry_price * 100) if self.entry_price > 0 else 0.0
                    self.write_log(f"止盈平空 - 开仓价:{self.entry_price:.0f}, 平仓价:{bar.close_price:.0f}, 盈利:{pnl_pct:.2f}%")
                    self.entry_price = 0.0
                    self.short_stop = 0.0
    
    def _on_strategy_logic(self, bar: BarData):
        """策略逻辑"""
        # 风控检查（平仓不受风控限制，只有开仓才受限制）
        current_price = bar.close_price
        
        # 持有空仓时的平仓逻辑（策略只做多，不应该有空仓，如果出现空仓立即平掉）
        if self.pos < 0:
            # 添加持仓状态日志（每100根K线记录一次）
            if len(self.am.close) % 100 == 0:
                current_pnl_pct = ((self.entry_price - bar.close_price) / self.entry_price * 100) if self.entry_price > 0 else 0.0
                self.write_log(
                    f"持仓状态(空仓): 时间={bar.datetime.strftime('%Y-%m-%d %H:%M')}, "
                    f"持仓={self.pos}, 开仓价={self.entry_price:.0f}, 当前价={bar.close_price:.0f}, "
                    f"浮动盈亏={current_pnl_pct:.2f}%, ISBUYTREND={self.ISBUYTREND}"
                )
            
            # 策略只做多，不应该有空仓，立即平掉空仓
            if self.entry_price > 0:
                pnl_pct = ((self.entry_price - bar.close_price) / self.entry_price) * 100
                self.write_log(f"[{bar.datetime.strftime('%Y-%m-%d %H:%M:%S')}] 警告: 策略只做多，发现空仓立即平仓 - 开仓价:{self.entry_price:.0f}, 平仓价:{bar.close_price:.0f}, 盈亏:{pnl_pct:.2f}%")
            else:
                self.write_log(f"[{bar.datetime.strftime('%Y-%m-%d %H:%M:%S')}] 警告: 策略只做多，发现空仓立即平仓(entry_price=0) - 平仓价:{bar.close_price:.0f}")
            
            self.cover(bar.close_price, abs(self.pos))
            self.entry_price = 0.0
            self.short_stop = 0.0
            return  # 平掉空仓后返回，等待下一根K线再处理
        
        # 持有多仓时的平仓逻辑（平仓不受风控限制）
        if self.pos > 0:
            # 添加持仓状态日志（每100根K线记录一次）
            if len(self.am.close) % 100 == 0:
                current_pnl_pct = ((bar.close_price - self.entry_price) / self.entry_price * 100) if self.entry_price > 0 else 0.0
                self.write_log(
                    f"持仓状态(多仓): 时间={bar.datetime.strftime('%Y-%m-%d %H:%M')}, "
                    f"持仓={self.pos}, 开仓价={self.entry_price:.0f}, 当前价={bar.close_price:.0f}, "
                    f"浮动盈亏={current_pnl_pct:.2f}%, ISBUYTREND={self.ISBUYTREND}"
                )
            
            # 平多条件：ISBUYTREND == 0（趋势反转）
            # 注意：如果entry_price为0但持仓还在，说明之前可能有问题，也应该平仓
            if self.ISBUYTREND == 0:
                if self.entry_price > 0:
                    pnl_pct = ((bar.close_price - self.entry_price) / self.entry_price) * 100
                    self.write_log(f"[{bar.datetime.strftime('%Y-%m-%d %H:%M:%S')}] 趋势反转平多 - 开仓价:{self.entry_price:.0f}, 平仓价:{bar.close_price:.0f}, 盈亏:{pnl_pct:.2f}%")
                else:
                    # entry_price为0但持仓还在，可能是之前的问题，强制平仓
                    self.write_log(f"[{bar.datetime.strftime('%Y-%m-%d %H:%M:%S')}] 警告: entry_price为0但持仓存在，强制平仓 - 平仓价:{bar.close_price:.0f}")
                
                self.sell(bar.close_price, abs(self.pos))
                self.entry_price = 0.0
                self.long_stop = 0.0
            return  # 有持仓时，只处理平仓逻辑，不处理开仓
        
        # 无持仓时的开仓逻辑（开仓需要风控检查）
        if self.pos == 0:
            # 风控检查
            if not self._risk_check():
                return
            
            # 做多信号：ISBUYTREND > 0（当前收盘价 > 5分钟周期前一个开盘价）
            if self.ISBUYTREND > 0:
                self.entry_price = current_price
                self.long_stop = self.entry_price * (1 - self.stop_loss_pct)
                
                # 使用bar.close_price而不是entry_price，确保使用当前K线的收盘价
                self.buy(bar.close_price, self.fixed_size)
                self.write_log(f"[{bar.datetime.strftime('%Y-%m-%d %H:%M:%S')}] 做多开仓 - 开仓价:{self.entry_price:.0f}, 止损价:{self.long_stop:.0f}, 止盈价:{self.entry_price * (1 + self.take_profit_pct):.0f}")
    
    def on_trade(self, trade: TradeData):
        """成交回报"""
        self.daily_trade_count += 1
        self.total_trades += 1
        
        # 添加详细的交易信息日志，用于调试图表显示问题
        trade_info = (
            f"成交回报: {trade.direction.value} {trade.offset.value} "
            f"{trade.volume}手 @ {trade.price:.0f}, "
            f"时间:{trade.datetime.strftime('%Y-%m-%d %H:%M:%S')}, "
            f"持仓:{self.pos}"
        )
        self.write_log(trade_info)
        
        # 如果是开仓，更新entry_price（防止entry_price丢失）
        if trade.offset == Offset.OPEN:
            if self.entry_price == 0:  # 如果entry_price为0，从成交价恢复
                self.entry_price = trade.price
                if trade.direction == Direction.LONG:
                    self.long_stop = self.entry_price * (1 - self.stop_loss_pct)
                else:
                    self.short_stop = self.entry_price * (1 + self.stop_loss_pct)
                self.write_log(f"恢复entry_price: {self.entry_price:.0f} (从成交价恢复)")
        
        # 计算盈亏（平仓时）
        if trade.offset == Offset.CLOSE:
            if self.entry_price > 0:
                if trade.direction == Direction.SHORT:  # 平多
                    pnl = (trade.price - self.entry_price) * trade.volume * 10  # MHI每跳10港币
                    pnl_pct = ((trade.price - self.entry_price) / self.entry_price) * 100
                else:  # 平空
                    pnl = (self.entry_price - trade.price) * trade.volume * 10
                    pnl_pct = ((self.entry_price - trade.price) / self.entry_price) * 100
                
                if pnl > 0:
                    self.win_trades += 1
                    self.consecutive_losses = 0
                    self.write_log(f"平仓盈利: {pnl:.0f} 港币 ({pnl_pct:.2f}%)")
                else:
                    self.consecutive_losses += 1
                    self.write_log(f"平仓亏损: {pnl:.0f} 港币 ({pnl_pct:.2f}%)")
        
        self.put_event()
