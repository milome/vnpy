#!/usr/bin/env python3
"""
多周期MACD趋势策略
从麦语言转换而来的复杂趋势跟踪策略

策略特点：
1. 多周期MACD分析（9个不同周期）
2. 主趋势线跟踪（双重EMA平滑）
3. 主力资金监控（CONTROLLEVEL指标）
4. 8状态趋势状态机
5. 布林通道和瀑布线辅助

转换日期：2024-11-21
原始麦语言代码行数：约800行
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
from vnpy.trader.constant import Direction, Offset
import talib
import numpy as np
from typing import Dict, List
from enum import Enum


class TrendState(Enum):
    """趋势状态枚举"""
    STRONG_SHORT = -4      # 空
    WEAK_SHORT = -3.5      # 空等
    WAIT_SHORT = -3        # 空等白
    SHORT_FLAT_WAIT = -2   # 空平等
    SHORT_FLAT = -1        # 空平
    LONG_FLAT = 1          # 多平
    LONG_FLAT_WAIT = 2     # 多平等
    WAIT_LONG = 3          # 多等白
    WEAK_LONG = 3.5        # 多等
    STRONG_LONG = 4        # 多


class MultiMACDTrendStrategy(CtaTemplate):
    """多周期MACD趋势策略"""

    author = "麦语言转换器"

    # 策略参数
    fixed_size: int = 1              # 固定手数
    control_average: float = 100.0   # 主力监控平均线
    n_param: int = 14               # KDJ参数N
    m_param: int = 3                # KDJ参数M
    n1_param: int = 20              # 控制水平参数

    # 成交量相关变量
    totalvol: float = 0.0
    scalebuy: float = 0.0
    scalesale: float = 0.0
    scalebuyvol: float = 0.0
    scalesalevol: float = 0.0

    # MACD相关变量（9个周期）
    diff1: float = 0.0
    dea1: float = 0.0
    macd1: float = 0.0
    diff3: float = 0.0
    dea3: float = 0.0
    macd3: float = 0.0
    diff5: float = 0.0
    dea5: float = 0.0
    macd5: float = 0.0
    diff9: float = 0.0
    dea9: float = 0.0
    macd9: float = 0.0
    diff15: float = 0.0
    dea15: float = 0.0
    macd15: float = 0.0
    diff25: float = 0.0
    dea25: float = 0.0
    macd25: float = 0.0
    diff30: float = 0.0
    dea30: float = 0.0
    macd30: float = 0.0
    diff45: float = 0.0
    dea45: float = 0.0
    macd45: float = 0.0
    diff60: float = 0.0
    dea60: float = 0.0
    macd60: float = 0.0

    # 趋势相关变量
    maintrend1m: float = 0.0
    uptrend: float = 0.0
    downtrend: float = 0.0
    uptrend10: float = 0.0
    downtrend10: float = 0.0

    # 趋势状态变量
    is_uptrend: int = 0
    is_uptrendover: int = 0
    is_downtrend: int = 0
    is_downtrendover: int = 0
    is_weak_uptrend: int = 0
    is_weak_downtrend: int = 0
    current_trend: float = 0.0
    current_indicator: int = 0

    # 布林通道变量
    mid_line: float = 0.0
    top_line: float = 0.0
    bottom_line: float = 0.0

    # 主力监控变量
    controllevel: float = 0.0

    # 瀑布线变量
    pb6: float = 0.0

    # K线数据变量
    total_k_data_num: int = 0

    # 历史数据缓存
    maintrend_history: List[float] = []
    macd1_history: List[float] = []
    controllevel_history: List[float] = []

    parameters = [
        "fixed_size",
        "control_average", 
        "n_param",
        "m_param",
        "n1_param"
    ]

    variables = [
        "totalvol",
        "scalebuy",
        "scalesale",
        "maintrend1m",
        "current_trend",
        "current_indicator",
        "macd1",
        "macd3",
        "macd5",
        "macd9",
        "controllevel",
        "is_uptrend",
        "is_downtrend",
        "total_k_data_num"
    ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """构造函数"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        # 初始化K线生成器：Tick -> 1分钟K线
        self.bg = BarGenerator(self.on_bar)

        # 初始化数组管理器（需要更大的缓存用于多周期计算）
        self.am = ArrayManager(size=2000)

        # 初始化历史数据缓存
        self.maintrend_history = []
        self.macd1_history = []
        self.controllevel_history = []

        # MACD参数配置
        self.macd_params = {
            'macd1': (12, 26, 9),
            'macd3': (36, 78, 27),
            'macd5': (60, 130, 45),
            'macd9': (108, 234, 81),
            'macd15': (180, 390, 135),
            'macd25': (288, 624, 216),
            'macd30': (360, 780, 270),
            'macd45': (540, 1170, 405),
            'macd60': (708, 1534, 531),
        }

    def on_init(self):
        """策略初始化"""
        self.write_log("多周期MACD趋势策略初始化")
        
        # 加载足够的历史数据用于多周期计算
        self.load_bar(30)  # 加载30天历史数据
        
        # 初始化计数器
        self.total_k_data_num = 0

    def on_start(self):
        """策略启动"""
        self.write_log("多周期MACD趋势策略启动")
        self.write_log(f"参数设置 - 固定手数:{self.fixed_size}, 控制平均线:{self.control_average}")

    def on_stop(self):
        """策略停止"""
        self.write_log("多周期MACD趋势策略停止")
        self.write_log(f"总K线数据: {self.total_k_data_num}")

    def on_tick(self, tick: TickData):
        """Tick数据推送"""
        self.bg.update_tick(tick)

    def on_bar(self, bar: BarData):
        """1分钟K线推送（策略主逻辑）"""
        # 先撤销所有挂单
        self.cancel_all()

        # 更新K线数据到数组管理器
        self.am.update_bar(bar)
        if not self.am.inited:
            return

        # 增加K线计数
        self.total_k_data_num += 1

        # 计算成交量相关指标
        self.calculate_volume_indicators(bar)

        # 计算主趋势线
        self.calculate_main_trend()

        # 计算多周期MACD
        self.calculate_multi_macd()

        # 计算布林通道
        self.calculate_bollinger_bands()

        # 计算主力监控指标
        self.calculate_control_level()

        # 计算瀑布线
        self.calculate_waterfall_line()

        # 判断趋势状态
        self.update_trend_states()

        # 更新当前趋势
        self.update_current_trend()

        # 生成交易信号
        self.generate_trading_signals(bar)

        # 更新历史数据缓存
        self.update_history_cache()

        # 更新界面
        self.put_event()

    def calculate_volume_indicators(self, bar: BarData):
        """计算成交量相关指标"""
        self.totalvol = bar.volume
        
        # 注意：麦语言中的SCALE在VNPy中没有直接对应
        # 这里使用简化的买卖力度估算
        if len(self.am.close_array) >= 2:
            if bar.close_price > self.am.close_array[-2]:
                self.scalebuy = 0.6  # 上涨时假设买盘占60%
                self.scalesale = 0.4
            elif bar.close_price < self.am.close_array[-2]:
                self.scalebuy = 0.4  # 下跌时假设买盘占40%
                self.scalesale = 0.6
            else:
                self.scalebuy = 0.5  # 平盘时假设各占50%
                self.scalesale = 0.5
        else:
            self.scalebuy = 0.5
            self.scalesale = 0.5

        self.scalebuyvol = self.scalebuy * bar.volume + 4
        self.scalesalevol = self.scalesale * bar.volume - 4

    def calculate_main_trend(self):
        """计算主趋势线：EMA(EMA(CLOSE,3),3)"""
        if len(self.am.close_array) >= 6:  # 需要足够的数据计算双重EMA
            # 第一次EMA平滑
            ema1 = talib.EMA(self.am.close_array, 3)
            # 第二次EMA平滑
            if len(ema1[~np.isnan(ema1)]) >= 3:
                ema2 = talib.EMA(ema1[~np.isnan(ema1)], 3)
                if len(ema2[~np.isnan(ema2)]) > 0:
                    self.maintrend1m = ema2[-1]

    def calculate_multi_macd(self):
        """计算多周期MACD指标"""
        if len(self.am.close_array) < 100:  # 数据不足
            return

        close_array = self.am.close_array

        # 计算各周期MACD
        for macd_name, (fast, slow, signal) in self.macd_params.items():
            if len(close_array) >= slow + signal:
                try:
                    # 计算DIFF
                    ema_fast = talib.EMA(close_array, fast)
                    ema_slow = talib.EMA(close_array, slow)
                    diff = ema_fast - ema_slow
                    
                    # 计算DEA
                    dea = talib.EMA(diff, signal)
                    
                    # 计算MACD
                    macd = 30 * (diff - dea)
                    
                    # 存储到对应变量
                    if macd_name == 'macd1':
                        self.diff1 = diff[-1] if not np.isnan(diff[-1]) else 0
                        self.dea1 = dea[-1] if not np.isnan(dea[-1]) else 0
                        self.macd1 = macd[-1] if not np.isnan(macd[-1]) else 0
                    elif macd_name == 'macd3':
                        self.diff3 = diff[-1] if not np.isnan(diff[-1]) else 0
                        self.dea3 = dea[-1] if not np.isnan(dea[-1]) else 0
                        self.macd3 = macd[-1] if not np.isnan(macd[-1]) else 0
                    elif macd_name == 'macd5':
                        self.diff5 = diff[-1] if not np.isnan(diff[-1]) else 0
                        self.dea5 = dea[-1] if not np.isnan(dea[-1]) else 0
                        self.macd5 = macd[-1] if not np.isnan(macd[-1]) else 0
                    elif macd_name == 'macd9':
                        self.diff9 = diff[-1] if not np.isnan(diff[-1]) else 0
                        self.dea9 = dea[-1] if not np.isnan(dea[-1]) else 0
                        self.macd9 = macd[-1] if not np.isnan(macd[-1]) else 0
                    elif macd_name == 'macd15':
                        self.diff15 = diff[-1] if not np.isnan(diff[-1]) else 0
                        self.dea15 = dea[-1] if not np.isnan(dea[-1]) else 0
                        self.macd15 = macd[-1] if not np.isnan(macd[-1]) else 0
                    elif macd_name == 'macd25':
                        self.diff25 = diff[-1] if not np.isnan(diff[-1]) else 0
                        self.dea25 = dea[-1] if not np.isnan(dea[-1]) else 0
                        self.macd25 = macd[-1] if not np.isnan(macd[-1]) else 0
                    elif macd_name == 'macd30':
                        self.diff30 = diff[-1] if not np.isnan(diff[-1]) else 0
                        self.dea30 = dea[-1] if not np.isnan(dea[-1]) else 0
                        self.macd30 = macd[-1] if not np.isnan(macd[-1]) else 0
                    elif macd_name == 'macd45':
                        self.diff45 = diff[-1] if not np.isnan(diff[-1]) else 0
                        self.dea45 = dea[-1] if not np.isnan(dea[-1]) else 0
                        self.macd45 = macd[-1] if not np.isnan(macd[-1]) else 0
                    elif macd_name == 'macd60':
                        self.diff60 = diff[-1] if not np.isnan(diff[-1]) else 0
                        self.dea60 = dea[-1] if not np.isnan(dea[-1]) else 0
                        self.macd60 = macd[-1] if not np.isnan(macd[-1]) else 0
                        
                except Exception as e:
                    self.write_log(f"计算{macd_name}时出错: {e}")

    def calculate_bollinger_bands(self):
        """计算布林通道（300周期）"""
        if len(self.am.close_array) >= 300:
            self.mid_line = self.am.sma(300)
            std_dev = np.std(self.am.close_array[-300:])
            self.top_line = self.mid_line + 2 * std_dev
            self.bottom_line = self.mid_line - 2 * std_dev

    def calculate_control_level(self):
        """计算主力监控指标（基于KDJ变形）"""
        if len(self.am.high_array) >= self.n_param and len(self.am.low_array) >= self.n_param:
            try:
                # 计算HHV和LLV
                hhv_high = np.max(self.am.high_array[-self.n_param:])
                llv_low = np.min(self.am.low_array[-self.n_param:])
                
                if hhv_high != llv_low:
                    # B1计算
                    b1 = (hhv_high - self.am.close_array[-1]) / (hhv_high - llv_low) * 100 - self.m_param
                    
                    # B2计算（简化SMA）
                    b2 = b1 + 100  # 简化处理
                    
                    # B3计算
                    b3 = (self.am.close_array[-1] - llv_low) / (hhv_high - llv_low) * 100
                    
                    # B4和B5计算（简化）
                    b4 = b3  # 简化处理
                    b5 = b4 + 100
                    
                    # B6计算
                    b6 = b5 - b2
                    
                    # CONTROLLEVEL计算
                    if b6 > self.n1_param:
                        self.controllevel = (b6 - self.n1_param) * 2.5
                    else:
                        self.controllevel = 0.0
                else:
                    self.controllevel = 0.0
                    
            except Exception as e:
                self.write_log(f"计算主力监控指标时出错: {e}")
                self.controllevel = 0.0

    def calculate_waterfall_line(self):
        """计算瀑布线PB6"""
        if len(self.am.close_array) >= 96:  # 24*4 = 96
            try:
                ema24 = talib.EMA(self.am.close_array, 24)
                ma48 = talib.SMA(self.am.close_array, 48)
                ma96 = talib.SMA(self.am.close_array, 96)
                
                if (not np.isnan(ema24[-1]) and 
                    not np.isnan(ma48[-1]) and 
                    not np.isnan(ma96[-1])):
                    self.pb6 = (ema24[-1] + ma48[-1] + ma96[-1]) / 3
                    
            except Exception as e:
                self.write_log(f"计算瀑布线时出错: {e}")
                self.pb6 = 0.0

    def update_trend_states(self):
        """更新趋势状态"""
        if len(self.maintrend_history) < 6:
            return

        current_trend = self.maintrend1m
        prev_trend_1 = self.get_ref_value(self.maintrend_history, 1)
        prev_trend_5 = self.get_ref_value(self.maintrend_history, 5)

        # 计算HHV和LLV
        if len(self.maintrend_history) >= 5:
            hhv_5 = max(self.maintrend_history[-5:])
            llv_5 = min(self.maintrend_history[-5:])
            
            # ISUPTREND条件
            self.is_uptrend = 0
            if (current_trend >= prev_trend_5 and 
                current_trend == hhv_5 and 
                current_trend > prev_trend_1 and 
                current_trend - prev_trend_1 >= 0.618 and
                self.am.close_array[-1] > max(self.am.close_array[-3:])):
                self.is_uptrend = 1

            # ISUPTRENDOVER条件
            self.is_uptrendover = 0
            if (current_trend >= prev_trend_5 and 
                current_trend <= prev_trend_1 and 
                current_trend <= self.get_ref_value(self.maintrend_history, 3) and
                prev_trend_1 - current_trend > 0.618):
                self.is_uptrendover = 1

            # ISDOWNTREND条件
            self.is_downtrend = 0
            if (current_trend < prev_trend_5 and 
                current_trend == llv_5 and 
                current_trend <= prev_trend_1 and 
                prev_trend_1 - current_trend > 0.618 and
                self.am.close_array[-1] < min(self.am.close_array[-3:])):
                self.is_downtrend = 1

            # ISDOWNTRENDOVER条件
            self.is_downtrendover = 0
            if (current_trend < prev_trend_5 and 
                current_trend > prev_trend_1 and 
                current_trend > self.get_ref_value(self.maintrend_history, 3) and
                current_trend - prev_trend_1 > 0.618):
                self.is_downtrendover = 1

    def update_current_trend(self):
        """更新当前趋势状态（状态机核心逻辑）"""
        prev_trend = self.current_trend

        # 数据充足性检查
        if self.total_k_data_num >= 88:
            # 空头信号
            if (self.is_downtrend == 1 and 
                (1 <= prev_trend <= 2 or -4 <= prev_trend <= -1)):
                self.current_trend = -4
                self.current_indicator = -1

            # 多头信号
            elif (self.is_uptrend == 1 and 
                  (-2 <= prev_trend <= -1 or 1 <= prev_trend <= 4)):
                self.current_trend = 4
                self.current_indicator = 1

            # 多等状态
            elif (self.is_uptrend == 0 and self.is_uptrendover == 0 and 
                  self.is_downtrend == 0 and self.is_downtrendover == 0 and
                  self.bars_since_uptrend() < self.bars_since_downtrend() and
                  self.bars_since_uptrendover() > self.bars_since_uptrend() and
                  self.is_weak_uptrend == 1):
                self.current_trend = 3.5

            # 多等白状态
            elif (self.is_uptrend == 0 and self.is_uptrendover == 0 and 
                  self.is_downtrend == 0 and self.is_downtrendover == 0 and
                  self.bars_since_uptrend() < self.bars_since_downtrend() and
                  self.bars_since_uptrendover() > self.bars_since_uptrend() and
                  self.is_weak_uptrend == 0):
                self.current_trend = 3

            # 多平状态
            elif (self.is_uptrend == 0 and self.is_uptrendover == 1 and 
                  1 <= prev_trend <= 4):
                self.current_trend = 1

            # 多平等状态
            elif (self.is_uptrend == 0 and self.is_uptrendover == 0 and 
                  self.is_downtrend == 0 and self.is_downtrendover == 0 and
                  prev_trend == 1 and
                  self.bars_since_uptrendover() < self.bars_since_uptrend() and
                  self.bars_since_uptrendover() < self.bars_since_downtrend() and
                  1 <= prev_trend <= 2):
                self.current_trend = 2

            # 空等状态
            elif (self.is_uptrend == 0 and self.is_uptrendover == 0 and 
                  self.is_downtrend == 0 and self.is_downtrendover == 0 and
                  self.bars_since_downtrendover() > self.bars_since_downtrend() and
                  self.bars_since_uptrend() > self.bars_since_downtrend() and
                  self.is_weak_downtrend == 1):
                self.current_trend = -3.5

            # 空等白状态
            elif (self.is_uptrend == 0 and self.is_uptrendover == 0 and 
                  self.is_downtrend == 0 and self.is_downtrendover == 0 and
                  self.bars_since_downtrendover() > self.bars_since_downtrend() and
                  self.bars_since_uptrend() > self.bars_since_downtrend() and
                  self.is_weak_downtrend == 0):
                self.current_trend = -3

            # 空平状态
            elif (self.is_downtrend == 0 and self.is_downtrendover == 1 and 
                  -4 <= prev_trend <= -1):
                self.current_trend = -1

            # 空平等状态
            elif (self.is_uptrend == 0 and self.is_uptrendover == 0 and 
                  self.is_downtrend == 0 and self.is_downtrendover == 0 and
                  prev_trend == -1 and
                  self.bars_since_downtrendover() < self.bars_since_downtrend() and
                  self.bars_since_uptrend() > self.bars_since_downtrend() and
                  -2 <= prev_trend <= -1):
                self.current_trend = -2

    def generate_trading_signals(self, bar: BarData):
        """生成交易信号"""
        # 基于当前趋势状态和主力监控指标生成信号
        
        # 强多头信号
        if (self.current_trend == 4 and 
            self.controllevel >= self.control_average and
            self.pos == 0):
            self.buy(bar.close_price, self.fixed_size)
            self.write_log(f"强多头买入信号 - 趋势:{self.current_trend}, 控制水平:{self.controllevel:.2f}")

        # 强空头信号
        elif (self.current_trend == -4 and 
              self.controllevel < self.control_average and
              self.pos == 0):
            self.short(bar.close_price, self.fixed_size)
            self.write_log(f"强空头卖出信号 - 趋势:{self.current_trend}, 控制水平:{self.controllevel:.2f}")

        # 多头平仓信号
        elif (self.pos > 0 and 
              (self.current_trend <= -1 or 
               (self.current_trend <= 2 and self.controllevel < self.control_average))):
            self.sell(bar.close_price, abs(self.pos))
            self.write_log(f"多头平仓信号 - 趋势:{self.current_trend}, 控制水平:{self.controllevel:.2f}")

        # 空头平仓信号
        elif (self.pos < 0 and 
              (self.current_trend >= 1 or 
               (self.current_trend >= -2 and self.controllevel >= self.control_average))):
            self.cover(bar.close_price, abs(self.pos))
            self.write_log(f"空头平仓信号 - 趋势:{self.current_trend}, 控制水平:{self.controllevel:.2f}")

    def update_history_cache(self):
        """更新历史数据缓存"""
        # 保持历史数据缓存大小
        max_history = 500
        
        # 更新主趋势线历史
        self.maintrend_history.append(self.maintrend1m)
        if len(self.maintrend_history) > max_history:
            self.maintrend_history.pop(0)

        # 更新MACD1历史
        self.macd1_history.append(self.macd1)
        if len(self.macd1_history) > max_history:
            self.macd1_history.pop(0)

        # 更新控制水平历史
        self.controllevel_history.append(self.controllevel)
        if len(self.controllevel_history) > max_history:
            self.controllevel_history.pop(0)

    # 辅助函数
    def get_ref_value(self, data_list: List[float], periods: int) -> float:
        """获取N周期前的值（模拟REF函数）"""
        if len(data_list) > periods:
            return data_list[-(periods + 1)]
        return 0.0

    def bars_since_condition(self, condition_history: List[int]) -> int:
        """计算自上次条件成立以来的周期数（模拟BARSLAST函数）"""
        for i in range(len(condition_history) - 1, -1, -1):
            if condition_history[i] == 1:
                return len(condition_history) - 1 - i
        return 999  # 如果没有找到，返回一个大数

    def bars_since_uptrend(self) -> int:
        """计算自上次上升趋势以来的周期数"""
        # 简化实现，实际应该维护趋势状态历史
        return 10  # 占位符

    def bars_since_downtrend(self) -> int:
        """计算自上次下降趋势以来的周期数"""
        # 简化实现，实际应该维护趋势状态历史
        return 15  # 占位符

    def bars_since_uptrendover(self) -> int:
        """计算自上次上升趋势结束以来的周期数"""
        # 简化实现，实际应该维护趋势状态历史
        return 8  # 占位符

    def bars_since_downtrendover(self) -> int:
        """计算自上次下降趋势结束以来的周期数"""
        # 简化实现，实际应该维护趋势状态历史
        return 12  # 占位符

    def on_order(self, order: OrderData):
        """委托回报"""
        if order.status.value in ["已撤销", "拒单"]:
            self.write_log(f"订单{order.orderid} {order.status.value}: {order.direction.value} {order.volume}手")

    def on_trade(self, trade: TradeData):
        """成交回报"""
        self.write_log(f"成交回报: {trade.direction.value} {trade.volume}手 @ {trade.price:.2f}")
        self.write_log(f"当前趋势状态: {self.current_trend}, 控制水平: {self.controllevel:.2f}")
        self.put_event()

    def on_stop_order(self, stop_order: StopOrder):
        """停止单回报"""
        pass

    def get_strategy_stats(self) -> Dict:
        """获取策略统计信息"""
        return {
            "total_k_data": self.total_k_data_num,
            "current_trend": self.current_trend,
            "maintrend1m": round(self.maintrend1m, 3),
            "macd1": round(self.macd1, 2),
            "macd3": round(self.macd3, 2),
            "macd5": round(self.macd5, 2),
            "macd9": round(self.macd9, 2),
            "controllevel": round(self.controllevel, 2),
            "is_uptrend": self.is_uptrend,
            "is_downtrend": self.is_downtrend,
            "current_indicator": self.current_indicator
        }

