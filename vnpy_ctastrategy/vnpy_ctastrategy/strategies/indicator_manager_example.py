#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用IndicatorManager的示例策略

展示如何在CTA策略中使用多周期自定义指标管理器
"""

from vnpy_ctastrategy import (
    CtaTemplate,
    StopOrder,
    TickData,
    BarData,
    TradeData,
    OrderData,
    BarGenerator,
    ArrayManager,
)

from vnpy.trader.constant import Interval
import numpy as np
from typing import List

# 导入指标管理器
from indicators import IndicatorManager


class IndicatorManagerExampleStrategy(CtaTemplate):
    """
    使用IndicatorManager的示例策略
    
    功能：
    1. 在多个周期（1分钟、5分钟）计算自定义指标
    2. 在实时tick和1分钟K线收盘时使用指标
    3. 支持长期历史数据存储
    """
    
    author = "IndicatorManager Example"
    
    # 策略参数
    fast_window: int = 10
    slow_window: int = 30
    fixed_size: int = 1
    
    parameters = ["fast_window", "slow_window", "fixed_size"]
    
    # 策略变量
    custom_wma_1min: float = 0.0
    custom_wma_5min: float = 0.0
    signal: int = 0
    
    variables = ["custom_wma_1min", "custom_wma_5min", "signal"]
    
    def on_init(self) -> None:
        """策略初始化"""
        self.write_log("策略初始化")
        
        # 创建指标管理器
        self.indicator_manager = IndicatorManager(
            vt_symbol=self.vt_symbol,
            storage_path=None,  # 使用默认路径 .vntrader/indicators/
            use_database=True  # 使用数据库加载历史数据
        )
        
        # 注册1分钟周期的自定义指标
        self.indicator_manager.register_indicator(
            interval=Interval.MINUTE,
            indicator_name="custom_wma",
            calculator=self._calculate_custom_wma,
            max_history=10000
        )
        
        # 注册5分钟周期的自定义指标
        self.indicator_manager.register_indicator(
            interval=Interval.MINUTE_5,
            indicator_name="custom_wma",
            calculator=self._calculate_custom_wma,
            max_history=10000
        )
        
        # 初始化指标（加载历史数据并计算）
        database = self.cta_engine.database
        self.indicator_manager.initialize_indicators(
            Interval.MINUTE,
            days=365,  # 加载1年历史数据
            database=database
        )
        self.indicator_manager.initialize_indicators(
            Interval.MINUTE_5,
            days=365,
            database=database
        )
        
        # 创建BarGenerator用于5分钟K线聚合
        self.bg5 = BarGenerator(self.on_bar, 5, self.on_5min_bar)
        self.am = ArrayManager()
        
        # 加载历史K线（用于ArrayManager初始化）
        self.load_bar(10)
    
    def on_start(self) -> None:
        """策略启动"""
        self.write_log("策略启动")
    
    def on_stop(self) -> None:
        """策略停止"""
        # 保存指标数据
        self.indicator_manager._save_indicator_to_file(Interval.MINUTE)
        self.indicator_manager._save_indicator_to_file(Interval.MINUTE_5)
        self.write_log("策略停止")
    
    def on_tick(self, tick: TickData) -> None:
        """Tick数据更新"""
        # 将tick数据推送到BarGenerator，用于聚合1分钟和5分钟K线
        self.bg5.update_tick(tick)
    
    def on_bar(self, bar: BarData) -> None:
        """1分钟K线更新"""
        # 更新ArrayManager
        self.am.update_bar(bar)
        if not self.am.inited:
            return
        
        # 更新1分钟周期的指标（历史值：1分钟K线已完成）
        self.indicator_manager.update_indicator(Interval.MINUTE, bar, is_runtime=False)
        
        # 获取1分钟周期的指标值（历史值）
        self.custom_wma_1min = self.indicator_manager.get_indicator(
            Interval.MINUTE,
            "custom_wma",
            index=-1
        ) or 0.0
        
        # 更新5分钟周期的运行时指标值（基于正在聚合的5分钟K线）
        # 需要从BarGenerator获取正在聚合的5分钟K线
        # BarGenerator在聚合过程中会维护window_bar，表示正在聚合的K线
        if hasattr(self.bg5, 'window_bar') and self.bg5.window_bar is not None:
            # 更新5分钟指标的运行时值（基于正在聚合的5分钟K线）
            self.indicator_manager.update_indicator(
                Interval.MINUTE_5,
                self.bg5.window_bar,
                is_runtime=True
            )
        
        # 获取5分钟周期的指标值（智能选择：优先运行时值，回退到历史值）
        # 使用智能选择方法，自动处理运行时值不存在的情况
        wma_5min_value = self.indicator_manager.get_indicator_smart(
            Interval.MINUTE_5,
            "custom_wma",
            prefer_runtime=True,      # 优先使用运行时值（正在聚合的5分钟K线）
            fallback_to_history=True, # 运行时值不存在时回退到历史值
            history_index=-1          # 回退时使用最新历史值（已完成的5分钟K线）
        )
        self.custom_wma_5min = wma_5min_value if wma_5min_value is not None else 0.0
        
        # 策略逻辑：使用1分钟和5分钟指标进行交易决策
        self._on_strategy_logic(bar)
        
        # 更新UI
        self.put_event()
    
    def on_5min_bar(self, bar: BarData) -> None:
        """5分钟K线更新（5分钟K线收盘时）"""
        # 更新5分钟周期的指标（历史值：5分钟K线已完成）
        self.indicator_manager.update_indicator(Interval.MINUTE_5, bar, is_runtime=False)
        
        # 获取5分钟周期的历史指标值（已完成的K线）
        self.custom_wma_5min = self.indicator_manager.get_indicator(
            Interval.MINUTE_5,
            "custom_wma",
            index=-1
        ) or 0.0
        
        self.write_log(f"5分钟K线收盘，历史指标更新: custom_wma_5min={self.custom_wma_5min:.2f}")
        
        # 如果需要基于5分钟指标进行交易决策，可以在这里调用策略逻辑
        # self._on_strategy_logic_5min(bar)
        
        # 更新UI
        self.put_event()
    
    def _on_strategy_logic(self, bar: BarData) -> None:
        """策略逻辑"""
        # 获取指标数组（用于需要多个历史值的计算）
        wma_1min_array = self.indicator_manager.get_indicator_array(
            Interval.MINUTE,
            "custom_wma",
            length=20
        )
        
        if wma_1min_array is None or len(wma_1min_array) < 2:
            return
        
        # 简单的交易逻辑示例
        current_wma = wma_1min_array[-1]
        prev_wma = wma_1min_array[-2]
        
        # 如果指标上升且当前价格高于指标，做多
        if current_wma > prev_wma and bar.close_price > current_wma:
            if self.pos == 0:
                self.buy(bar.close_price, self.fixed_size)
                self.write_log(f"买入信号: price={bar.close_price:.2f}, wma={current_wma:.2f}")
        
        # 如果指标下降且当前价格低于指标，做空
        elif current_wma < prev_wma and bar.close_price < current_wma:
            if self.pos == 0:
                self.short(bar.close_price, self.fixed_size)
                self.write_log(f"卖出信号: price={bar.close_price:.2f}, wma={current_wma:.2f}")
        
        # 平仓逻辑
        if self.pos > 0:
            if bar.close_price < current_wma:
                self.sell(bar.close_price, abs(self.pos))
                self.write_log(f"平多仓: price={bar.close_price:.2f}")
        elif self.pos < 0:
            if bar.close_price > current_wma:
                self.cover(bar.close_price, abs(self.pos))
                self.write_log(f"平空仓: price={bar.close_price:.2f}")
    
    def _calculate_custom_wma(self, bars: List[BarData]) -> np.ndarray:
        """
        自定义指标计算函数：加权移动平均
        
        参数:
            bars: BarData列表
        
        返回:
            指标值数组
        """
        if len(bars) < self.fast_window:
            return np.array([np.nan] * len(bars))
        
        closes = np.array([bar.close_price for bar in bars])
        
        # 加权移动平均：权重递减
        # 使用talib的WMA或自定义计算
        try:
            import talib
            wma = talib.WMA(closes, timeperiod=self.fast_window)
        except ImportError:
            # 如果没有talib，使用简单的加权平均
            wma = np.zeros(len(closes))
            for i in range(self.fast_window - 1, len(closes)):
                window = closes[i - self.fast_window + 1:i + 1]
                weights = np.arange(1, len(window) + 1)
                wma[i] = np.sum(window * weights) / np.sum(weights)
            wma[:self.fast_window - 1] = np.nan
        
        return wma
    
    def on_order(self, order: OrderData) -> None:
        """订单更新"""
        pass
    
    def on_trade(self, trade: TradeData) -> None:
        """成交更新"""
        self.put_event()
    
    def on_stop_order(self, stop_order: StopOrder) -> None:
        """停止单更新"""
        pass

