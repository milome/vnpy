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
from mflang.functions import BP, BPK, SPK
from mflang.import_parser import ImportParser, PeriodType
from mflang.model_loader import load_model
from vnpy.trader.constant import Interval, Direction, Offset
from vnpy.trader.database import get_database
from indicators import IndicatorManager
from typing import List
import numpy as np

class TestImportStrategy(CtaTemplate):
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

    # 参数默认值
    fixed_size: int = 1
    stop_loss_pct: float = 0.02  # 2%止损
    take_profit_pct: float = 0.04  # 4%止盈
    max_daily_trades: int = 10
    max_consecutive_losses: int = 5

    # 策略变量
    variables = [
        "CC", "ISBUYTREND", "BPK_SIGNAL", "SPK_SIGNAL",
        "entry_price",      # 开仓价格
        "long_stop",        # 多头止损价
        "short_stop",       # 空头止损价
        "daily_trade_count", # 每日交易次数
        "consecutive_losses", # 连续亏损次数
        "total_trades",     # 总交易次数
        "win_trades",       # 盈利交易次数
        "last_trade_date",  # 上次交易日期
    ]

    CC = 0.0
    ISBUYTREND = 0.0
    BPK_SIGNAL = 0.0
    SPK_SIGNAL = 0.0

    # 风控相关变量
    entry_price = 0.0
    long_stop = 0.0
    short_stop = 0.0
    daily_trade_count = 0
    consecutive_losses = 0
    total_trades = 0
    win_trades = 0
    last_trade_date = None

    # T_COMMAND 设置的手数: 1
    t_command_volume = 1

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """初始化策略"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        
        # K线管理器（1分钟K线）
        self.bg = BarGenerator(self.on_bar)
        self.am = ArrayManager()
        
        # 创建 IndicatorManager 用于管理跨周期指标
        self.indicator_manager = IndicatorManager(
            vt_symbol=self.vt_symbol,
            storage_path=None,  # 使用默认路径 .vntrader/indicators/
            use_database=True  # 使用数据库加载历史数据
        )
        
        # 跨周期数据管理器
        # 根据 PERIOD 和 N 的组合创建 BarGenerator 和 ArrayManager，相同周期的引用共享
        # MIN5周期 BarGenerator 和 ArrayManager
        self.bg_min_5 = BarGenerator(self.on_bar, 5, self.on_min_5_bar)
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
        
        # 注册 MIN5.PREV_OPEN 指标（MIN5周期）
        self.indicator_manager.register_indicator(
            interval=Interval.MINUTE_5,
            indicator_name="MIN5.PREV_OPEN",
            calculator=self._calculate_min5_open_prev_open,
            max_history=10000
        )
        
        # 初始化指标（加载历史数据并计算）
        # 获取数据库（兼容回测和实盘环境）
        try:
            # 实盘环境：从 cta_engine 获取数据库
            database = self.cta_engine.database
            # 实盘环境不使用快速模式，直接加载完整数据
            is_backtesting = False
        except AttributeError:
            # 回测环境：使用 get_database() 函数
            database = get_database()
            # 回测环境使用快速模式：先加载30天数据快速初始化，然后在后台继续加载完整数据
            is_backtesting = True
        self.indicator_manager.initialize_indicators(
            Interval.MINUTE_5,
            days=365,  # 加载1年历史数据
            database=database,
            fast_mode=is_backtesting,  # 回测环境使用快速模式
            fast_days=30  # 快速模式先加载30天数据
        )
        
        self.load_bar(10)  # 加载10根K线

    def on_start(self):
        """策略启动回调"""
        self.write_log("策略启动")

    def on_stop(self):
        """策略停止回调"""
        self.write_log("策略停止")
        
        # 保存MIN5周期的指标数据
        self.indicator_manager._save_indicator_to_file(Interval.MINUTE_5)
        
        # 输出交易统计
        if self.total_trades > 0:
            win_rate = self.win_trades / self.total_trades * 100
            self.write_log(f"交易统计: 总交易次数={self.total_trades}, 盈利次数={self.win_trades}, 胜率={win_rate:.2f}%")
        
        # 更新UI显示
        self.put_event()

    def on_trade(self, trade: TradeData):
        """成交回调"""
        # 更新交易统计
        if self.entry_price > 0:
            # 计算盈亏
            if trade.direction == Direction.LONG:
                # 买入成交（开仓或平空）
                if trade.offset == Offset.OPEN:
                    # 买入开仓，记录开仓价格
                    self.entry_price = trade.price
                elif trade.offset == Offset.CLOSE:
                    # 买入平仓，计算盈亏
                    if self.entry_price > 0:
                        pnl = (self.entry_price - trade.price) * trade.volume
                        self.total_trades += 1
                        if pnl > 0:
                            self.win_trades += 1
                            self.consecutive_losses = 0
                        else:
                            self.consecutive_losses += 1
                        self.entry_price = 0.0  # 重置开仓价格
            elif trade.direction == Direction.SHORT:
                # 卖出成交（开仓或平多）
                if trade.offset == Offset.OPEN:
                    # 卖出开仓，记录开仓价格
                    self.entry_price = trade.price
                elif trade.offset == Offset.CLOSE:
                    # 卖出平仓，计算盈亏
                    if self.entry_price > 0:
                        pnl = (trade.price - self.entry_price) * trade.volume
                        self.total_trades += 1
                        if pnl > 0:
                            self.win_trades += 1
                            self.consecutive_losses = 0
                        else:
                            self.consecutive_losses += 1
                        self.entry_price = 0.0  # 重置开仓价格
        
        # 更新UI显示
        self.put_event()

    def on_tick(self, tick: TickData):
        """Tick数据回调"""
        self.bg.update_tick(tick)
        self.bg_min_5.update_tick(tick)

    def on_bar(self, bar: BarData):
        """1分钟K线数据回调"""
        self.am.update_bar(bar)
        
        # 将1分钟K线推送到MIN5周期BarGenerator
        self.bg_min_5.update_bar(bar)
        
        if not self.am.inited:
            return
        
        # 重置每日交易计数和连续亏损计数（如果是新的一天）
        current_date = bar.datetime.date()
        if self.last_trade_date != current_date:
            self.daily_trade_count = 0
            self.consecutive_losses = 0  # 每日重置连续亏损计数
            self.last_trade_date = current_date
        
        # 更新MIN5周期的运行时指标值（基于正在聚合的K线）
        if hasattr(self.bg_min_5, 'window_bar') and self.bg_min_5.window_bar is not None:
            # 更新指标 MIN5.PREV_OPEN
            self.indicator_manager.update_indicator(
                Interval.MINUTE_5,
                self.bg_min_5.window_bar,
                is_runtime=True
            )
        
        # 计算策略变量
        # 计算 CC: C
        self.CC = self._calculate_variable_cc()
        # 计算 ISBUYTREND: C > MIN5.PREV_OPEN
        self.ISBUYTREND = self._calculate_variable_isbuytrend()
        # 计算 BPK_SIGNAL: ISBUYTREND>0
        self.BPK_SIGNAL = self._calculate_variable_bpk_signal()
        # 计算 SPK_SIGNAL: ISBUYTREND<=0
        self.SPK_SIGNAL = self._calculate_variable_spk_signal()
        
        # 调试日志：输出关键变量值（每10根K线输出一次）
        if len(self.am.close) % 10 == 0:
            # 获取跨周期变量 MIN5.PREV_OPEN（通过 IndicatorManager）
            prev_open_value = self.indicator_manager.get_indicator_smart(
                Interval.MINUTE_5,
                "MIN5.PREV_OPEN",
                prefer_runtime=True,
                fallback_to_history=True,
                history_index=-1,
                wait_if_not_ready=True,   # 如果指标未初始化完成，等待
                wait_timeout=1.0          # 最多等待1秒
            )
            prev_open_str = f"{prev_open_value:.2f}" if prev_open_value is not None and not np.isnan(prev_open_value) else "NaN"
            self.write_log(f"调试: C={self.CC:.2f}, ISBUYTREND={self.ISBUYTREND}, MIN5.PREV_OPEN={prev_open_str}, BPK_SIGNAL={self.BPK_SIGNAL}, SPK_SIGNAL={self.SPK_SIGNAL}, pos={self.pos}")
        
        # 检查止损止盈（风控逻辑）
        self._check_risk_control(bar)
        
        # 策略逻辑
        self._on_strategy_logic(bar)
        
        # 更新UI显示
        self.put_event()

    def on_min_5_bar(self, bar: BarData):
        """MIN5周期K线数据回调（由BarGenerator合成）"""
        # 更新MIN5周期ArrayManager
        self.min_5_am.update_bar(bar)
        
        if not self.min_5_am.inited:
            return
        
        # 更新MIN5周期的历史指标值（K线已完成）
        self.indicator_manager.update_indicator(
            Interval.MINUTE_5,
            bar,
            is_runtime=False  # 历史值：K线已完成
        )

    def _check_risk_control(self, bar: BarData):
        """
        默认风控逻辑
        后续可以在模型文件中定义自定义风控逻辑来覆盖此方法
        """
        if self.pos == 0:
            return
        
        # 计算当前浮动盈亏百分比
        if self.entry_price > 0:
            if self.pos > 0:  # 多头持仓
                pnl_pct = (bar.close_price - self.entry_price) / self.entry_price
                # 止损检查
                if pnl_pct <= -self.stop_loss_pct:
                    self.write_log(f"触发止损: 浮动盈亏={pnl_pct*100:.2f}%, 止损比例={self.stop_loss_pct*100:.2f}%")
                    if bar.close_price is not None and not np.isnan(bar.close_price) and bar.close_price > 0:
                        self.sell(bar.close_price, abs(self.pos))
                    return
                # 止盈检查
                if pnl_pct >= self.take_profit_pct:
                    self.write_log(f"触发止盈: 浮动盈亏={pnl_pct*100:.2f}%, 止盈比例={self.take_profit_pct*100:.2f}%")
                    if bar.close_price is not None and not np.isnan(bar.close_price) and bar.close_price > 0:
                        self.sell(bar.close_price, abs(self.pos))
                    return
            elif self.pos < 0:  # 空头持仓
                pnl_pct = (self.entry_price - bar.close_price) / self.entry_price
                # 止损检查
                if pnl_pct <= -self.stop_loss_pct:
                    self.write_log(f"触发止损: 浮动盈亏={pnl_pct*100:.2f}%, 止损比例={self.stop_loss_pct*100:.2f}%")
                    if bar.close_price is not None and not np.isnan(bar.close_price) and bar.close_price > 0:
                        self.cover(bar.close_price, abs(self.pos))
                    return
                # 止盈检查
                if pnl_pct >= self.take_profit_pct:
                    self.write_log(f"触发止盈: 浮动盈亏={pnl_pct*100:.2f}%, 止盈比例={self.take_profit_pct*100:.2f}%")
                    if bar.close_price is not None and not np.isnan(bar.close_price) and bar.close_price > 0:
                        self.cover(bar.close_price, abs(self.pos))
                    return

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
            var_expr_clean = var_expr.strip()
            if "REF(O,1)" in var_expr_clean or "REF(O, 1)" in var_expr_clean:
                if len(am.open) < 2:
                    vars_cache[var_name_in_model] = np.nan
                else:
                    open_prices = am.open
                    result = REF(open_prices, 1)
                    vars_cache[var_name_in_model] = result[-1] if len(result) > 0 else np.nan
            elif "REF(C,1)" in var_expr_clean or "REF(C, 1)" in var_expr_clean:
                if len(am.close) < 2:
                    vars_cache[var_name_in_model] = np.nan
                else:
                    close_prices = am.close
                    result = REF(close_prices, 1)
                    vars_cache[var_name_in_model] = result[-1] if len(result) > 0 else np.nan
            elif var_expr_clean == "C":
                vars_cache[var_name_in_model] = am.close[-1] if len(am.close) > 0 else np.nan
            elif var_expr_clean == "O":
                vars_cache[var_name_in_model] = am.open[-1] if len(am.open) > 0 else np.nan
            else:
                # 默认返回 NaN，避免未处理的表达式导致错误
                vars_cache[var_name_in_model] = np.nan
        
        # 缓存结果
        setattr(self, f"{var_name.lower()}_vars", vars_cache)
        
        # 调试日志：输出跨周期变量值
        if vars_cache:
            for k, v in vars_cache.items():
                if not np.isnan(v):
                    self.write_log(f"跨周期变量 {var_name}.{k} = {v:.2f}")

    def _calculate_min5_open_prev_open(self, bars: List[BarData]) -> np.ndarray:
        """计算指标 PREV_OPEN: REF(O,1)"""
        if len(bars) < 2:
            return np.array([np.nan] * len(bars))
        
        # 提取开盘价
        opens = np.array([bar.open_price for bar in bars])
        # 计算 REF(O, 1)
        result = REF(opens, 1)
        return result

    def _calculate_variable_cc(self) -> float:
        """计算变量 CC: C"""
        return self.am.close[-1] if len(self.am.close) > 0 else 0.0

    def _calculate_variable_isbuytrend(self) -> float:
        """计算变量 ISBUYTREND: C > MIN5.PREV_OPEN"""
        # 获取跨周期引用 MIN5.PREV_OPEN（通过 IndicatorManager）
        prev_open_value = self.indicator_manager.get_indicator_smart(
            Interval.MINUTE_5,
            "MIN5.PREV_OPEN",
            prefer_runtime=True,      # 优先使用运行时值（正在聚合的K线）
            fallback_to_history=True, # 运行时值不存在时回退到历史值
            history_index=-1,         # 回退时使用最新历史值
            wait_if_not_ready=True,   # 如果指标未初始化完成，等待
            wait_timeout=1.0          # 最多等待1秒
        )
        if prev_open_value is None:
            prev_open_value = np.nan
        
        current_close = self.am.close[-1] if len(self.am.close) > 0 else np.nan
        if np.isnan(current_close) or np.isnan(prev_open_value):
            return 0.0
        result = current_close > prev_open_value
        return 1.0 if result else 0.0

    def _calculate_variable_bpk_signal(self) -> float:
        """计算变量 BPK_SIGNAL: ISBUYTREND>0"""
        left_val = self.ISBUYTREND
        if np.isnan(left_val) or np.isnan(0):
            return 0.0
        result = left_val > 0
        return 1.0 if result else 0.0

    def _calculate_variable_spk_signal(self) -> float:
        """计算变量 SPK_SIGNAL: ISBUYTREND<=0"""
        left_val = self.ISBUYTREND
        if np.isnan(left_val) or np.isnan(0):
            return 0.0
        result = left_val <= 0
        return 1.0 if result else 0.0

    def _on_strategy_logic(self, bar: BarData):
        """策略逻辑"""
        # 检查价格有效性
        if bar.close_price is None or np.isnan(bar.close_price) or bar.close_price <= 0:
            self.write_log(f"价格无效，跳过交易: close_price={bar.close_price}")
            return
        
        # 强制持仓限制：严格遵守只有一手持仓
        # 如果持仓超过1手，强制平仓到1手
        current_pos = self.pos
        if current_pos > 1:
            # 多仓超过1手，强制平仓到1手
            excess_volume = current_pos - 1
            if bar.close_price is not None and not np.isnan(bar.close_price) and bar.close_price > 0:
                self.sell(bar.close_price, excess_volume)
                self.write_log(f"强制平仓：多仓超过1手，平掉多余 {excess_volume} 手")
        elif current_pos < -1:
            # 空仓超过1手，强制平仓到1手
            excess_volume = abs(current_pos) - 1
            if bar.close_price is not None and not np.isnan(bar.close_price) and bar.close_price > 0:
                self.cover(bar.close_price, excess_volume)
                self.write_log(f"强制平仓：空仓超过1手，平掉多余 {excess_volume} 手")
        
        # 在这里实现策略的交易逻辑
        # 可以使用计算好的变量进行判断
        # CC = self.CC
        # ISBUYTREND = self.ISBUYTREND
        # BPK_SIGNAL = self.BPK_SIGNAL
        # SPK_SIGNAL = self.SPK_SIGNAL
        
        # 处理交易指令
        # BPK_SIGNAL: ISBUYTREND>0, BPK
        # BPK指令，买平后买开
        if self.BPK_SIGNAL > 0:  # 条件满足
            # 风控检查：每日交易次数限制
            if self.daily_trade_count >= self.max_daily_trades:
                return  # 静默跳过，避免日志刷屏
            
            # 风控检查：连续亏损限制
            if self.consecutive_losses >= self.max_consecutive_losses:
                return  # 静默跳过，避免日志刷屏
            
            # 获取当前持仓
            pos = self.pos
            
            # 持仓检查：严格遵守只有一手持仓
            # BPK指令允许：空头持仓转多头持仓，或空仓开多
            if pos > 0:  # 如果已有多头持仓，不允许再次开仓
                return  # 静默跳过，避免日志刷屏
            
            # BPK指令：买平后买开，空单转多单
            # 强制限制最终持仓只有1手
            target_volume = 1
            
            if pos < 0:  # 如果有空头持仓
                # 先买入平仓，平掉所有空头持仓
                cover_volume = abs(pos)  # 平仓数量为当前空头持仓的绝对值
                if bar.close_price is not None and not np.isnan(bar.close_price) and bar.close_price > 0:
                    self.cover(bar.close_price, cover_volume)
                    self.write_log("BPK指令触发: 买入平仓 %d 手" % cover_volume)
                    # 平仓后，计算需要开仓的数量（确保最终持仓为1手）
                    # 平仓后持仓变为0，所以需要开1手
                    open_volume = target_volume
                else:
                    return  # 价格无效，跳过
            else:
                # 空仓，直接开1手
                open_volume = target_volume
            
            # 买入开仓（确保只有1手）
            if bar.close_price is not None and not np.isnan(bar.close_price) and bar.close_price > 0:
                if open_volume > 0:
                    # 开仓前再次检查持仓，防止同一根K线上多个信号重复开仓
                    current_pos = self.pos
                    if current_pos >= 1:  # 如果已有多头持仓，不再开仓
                        return  # 静默跳过，避免重复开仓
                    # 计算实际需要开仓的数量（确保最终持仓不超过1手）
                    actual_open_volume = min(open_volume, max(0, 1 - current_pos))
                    if actual_open_volume > 0:
                        self.buy(bar.close_price, actual_open_volume)
                        # 记录开仓价格
                        self.entry_price = bar.close_price
                        self.daily_trade_count += 1
                        self.write_log("BPK指令触发: 买入开仓 %d 手, 开仓价=%.2f" % (actual_open_volume, self.entry_price))
        
        # SPK_SIGNAL: ISBUYTREND<=0, SPK
        # SPK指令，卖平后卖开
        if self.SPK_SIGNAL > 0:  # 条件满足
            # 风控检查：每日交易次数限制
            if self.daily_trade_count >= self.max_daily_trades:
                return  # 静默跳过，避免日志刷屏
            
            # 风控检查：连续亏损限制
            if self.consecutive_losses >= self.max_consecutive_losses:
                return  # 静默跳过，避免日志刷屏
            
            # 获取当前持仓
            pos = self.pos
            
            # 持仓检查：严格遵守只有一手持仓
            # SPK指令允许：多头持仓转空头持仓，或多仓开空
            if pos < 0:  # 如果已有空头持仓，不允许再次开仓
                return  # 静默跳过，避免日志刷屏
            
            # SPK指令：卖平后卖开，多单转空单
            # 强制限制最终持仓只有1手
            target_volume = 1
            
            if pos > 0:  # 如果有多头持仓
                # 先卖出平仓，平掉所有多头持仓
                sell_volume = pos  # 平仓数量为当前多头持仓
                if bar.close_price is not None and not np.isnan(bar.close_price) and bar.close_price > 0:
                    self.sell(bar.close_price, sell_volume)
                    self.write_log("SPK指令触发: 卖出平仓 %d 手" % sell_volume)
                    # 平仓后，计算需要开仓的数量（确保最终持仓为1手）
                    # 平仓后持仓变为0，所以需要开1手空仓
                    open_volume = target_volume
                else:
                    return  # 价格无效，跳过
            else:
                # 空仓，直接开1手空仓
                open_volume = target_volume
            
            # 卖出开仓（确保只有1手）
            if bar.close_price is not None and not np.isnan(bar.close_price) and bar.close_price > 0:
                if open_volume > 0:
                    # 开仓前再次检查持仓，防止同一根K线上多个信号重复开仓
                    current_pos = self.pos
                    if current_pos <= -1:  # 如果已有空头持仓，不再开仓
                        return  # 静默跳过，避免重复开仓
                    # 计算实际需要开仓的数量（确保最终持仓不超过1手）
                    actual_open_volume = min(open_volume, max(0, 1 + current_pos))  # current_pos可能是正数，需要先平多再开空
                    if actual_open_volume > 0:
                        self.short(bar.close_price, actual_open_volume)
                        # 记录开仓价格
                        self.entry_price = bar.close_price
                        self.daily_trade_count += 1
                        self.write_log("SPK指令触发: 卖出开仓 %d 手, 开仓价=%.2f" % (actual_open_volume, self.entry_price))
        
