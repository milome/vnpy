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

    def on_bar(self, bar: BarData):
        """K线数据回调"""
        self.am.update_bar(bar)
        
        if not self.am.inited:
            return
        
        # 重置每日交易计数（如果是新的一天）
        current_date = bar.datetime.date()
        if self.last_trade_date != current_date:
            self.daily_trade_count = 0
            self.last_trade_date = current_date
        
        # 处理跨周期数据
        # 从 #IMPORT 语句中获取 PERIOD 和 N，确定需要加载哪个周期的数据
        # 遍历所有 #IMPORT 语句，根据 PERIOD 和 N 判断当前K线是否为目标周期
        for stmt in self.import_statements:
            # 从 #IMPORT 语句中获取周期信息：PERIOD 和 N
            # 例如：#IMPORT[MIN,5,MIN5_OPEN] AS MIN5
            #      PERIOD = MIN, N = 5，表示需要5分钟周期的数据
            period_type = stmt.period.value  # 周期类型（MIN, HOUR, DAY等）
            period_n = stmt.n  # 周期参数（如5表示5分钟）
            
            # 判断当前K线是否是目标周期的K线
            if self._is_period_bar(bar, period_type, period_n):
                # 根据 PERIOD 和 N 获取对应的 ArrayManager（相同周期共享）
                period_key = f"{period_type.lower()}_{period_n}"
                am = getattr(self, f"{period_key}_am")
                am.update_bar(bar)
                
                # 如果数据已初始化，计算跨周期变量
                if am.inited:
                    self._calculate_cross_period_vars(stmt.var_name, stmt.formula, period_type, period_n)
        
        # 注意：如果当前K线不是目标周期，跨周期变量使用上一次计算的值
        
        # 计算策略变量
        # 计算 CC: C
        self.CC = self._calculate_variable_cc()
        # 计算 ISBUYTREND: C > MIN5.PREV_OPEN
        self.ISBUYTREND = self._calculate_variable_isbuytrend()
        
        # 检查止损止盈
        self._check_stop_loss_take_profit(bar)
        
        # 策略逻辑
        self._on_strategy_logic(bar)

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
                result = REF(open_prices, 1)
                vars_cache[var_name_in_model] = result[-1] if len(result) > 0 else np.nan
            elif "REF(C,1)" in var_expr:
                close_prices = am.close
                result = REF(close_prices, 1)
                vars_cache[var_name_in_model] = result[-1] if len(result) > 0 else np.nan
            elif var_expr.strip() == "C":
                vars_cache[var_name_in_model] = am.close[-1] if len(am.close) > 0 else np.nan
            elif var_expr.strip() == "O":
                vars_cache[var_name_in_model] = am.open[-1] if len(am.open) > 0 else np.nan
            # 可以添加更多表达式类型的处理
        
        # 缓存结果
        setattr(self, f"{var_name.lower()}_vars", vars_cache)

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
            return 0.0
        result = current_close > prev_open_value
        return 1.0 if result else 0.0

    def _risk_check(self) -> bool:
        """风控检查"""
        # 检查每日交易次数限制
        if self.daily_trade_count >= self.max_daily_trades:
            return False
        
        # 检查连续亏损次数
        if self.consecutive_losses >= self.max_consecutive_losses:
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
        # 风控检查
        if not self._risk_check():
            return
        
        current_price = bar.close_price
        
        # 无持仓时的开仓逻辑
        if self.pos == 0:
            # 做多信号：ISBUYTREND > 0（当前收盘价 > 5分钟周期前一个开盘价）
            if self.ISBUYTREND > 0:
                self.entry_price = current_price
                self.long_stop = self.entry_price * (1 - self.stop_loss_pct)
                
                self.buy(self.entry_price, self.fixed_size)
                self.write_log(f"[{bar.datetime.strftime('%H:%M:%S')}] 做多开仓 - 开仓价:{self.entry_price:.0f}, 止损价:{self.long_stop:.0f}, 止盈价:{self.entry_price * (1 + self.take_profit_pct):.0f}")
        
        # 持有多仓时的平仓逻辑
        elif self.pos > 0:
            # 平多条件：ISBUYTREND == 0（趋势反转）
            if self.ISBUYTREND == 0 and self.entry_price > 0:
                self.sell(bar.close_price, abs(self.pos))
                pnl_pct = ((bar.close_price - self.entry_price) / self.entry_price) * 100 if self.entry_price > 0 else 0.0
                self.write_log(f"[{bar.datetime.strftime('%H:%M:%S')}] 趋势反转平多 - 开仓价:{self.entry_price:.0f}, 平仓价:{bar.close_price:.0f}, 盈亏:{pnl_pct:.2f}%")
                self.entry_price = 0.0
                self.long_stop = 0.0
    
    def on_trade(self, trade: TradeData):
        """成交回报"""
        self.daily_trade_count += 1
        self.total_trades += 1
        
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
        
        self.write_log(f"成交回报: {trade.direction.value} {trade.volume}手 @ {trade.price:.0f}, 持仓:{self.pos}")
        self.put_event()
