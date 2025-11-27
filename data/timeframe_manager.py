#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多周期数据管理器
负责管理不同时间周期的K线数据和技术指标
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from collections import deque

from indicators import Minute1Indicators, Minute5Indicators, Hour1Indicators, Hour4Indicators


class TimeframeManager:
    """多周期数据管理器"""
    
    def __init__(self):
        """初始化多周期数据管理器"""
        # 初始化各周期指标计算器
        self.minute1_indicators = Minute1Indicators()
        self.minute5_indicators = Minute5Indicators()
        self.hour1_indicators = Hour1Indicators()
        self.hour4_indicators = Hour4Indicators()
        
        # 数据缓存（用于合成高周期K线）
        self.minute1_bars = deque(maxlen=1000)
        self.minute5_bars = deque(maxlen=500)
        self.hour1_bars = deque(maxlen=500)
        self.hour4_bars = deque(maxlen=500)
        
        # 最后更新的时间戳
        self.last_update_time = None
        
    def update_1m_bar(self, bar) -> Dict[str, Any]:
        """
        更新1分钟K线数据
        
        Args:
            bar: 1分钟K线数据对象
            
        Returns:
            dict: 包含所有周期指标的字典
        """
        self.minute1_bars.append(bar)
        self.last_update_time = bar.datetime if hasattr(bar, 'datetime') else datetime.now()
        
        # 计算1分钟指标
        indicators_1m = self.minute1_indicators.calculate_indicators(bar)
        
        # 尝试合成5分钟K线
        bar_5m = self._try_synthesize_5m_bar()
        indicators_5m = {}
        if bar_5m:
            self.minute5_bars.append(bar_5m)
            indicators_5m = self.minute5_indicators.calculate_indicators(bar_5m)
            
            # 尝试合成1小时K线
            bar_1h = self._try_synthesize_1h_bar()
            indicators_1h = {}
            if bar_1h:
                self.hour1_bars.append(bar_1h)
                indicators_1h = self.hour1_indicators.calculate_indicators(bar_1h)
                
                # 尝试合成4小时K线
                bar_4h = self._try_synthesize_4h_bar()
                indicators_4h = {}
                if bar_4h:
                    self.hour4_bars.append(bar_4h)
                    indicators_4h = self.hour4_indicators.calculate_indicators(bar_4h)
        
        # 汇总所有周期指标
        all_indicators = {
            '1m': indicators_1m,
            '5m': indicators_5m,
            '1h': indicators_1h if 'indicators_1h' in locals() else {},
            '4h': indicators_4h if 'indicators_4h' in locals() else {},
        }
        
        return all_indicators
    
    def _try_synthesize_5m_bar(self) -> Optional[Any]:
        """尝试合成5分钟K线"""
        if len(self.minute1_bars) < 5:
            return None
        
        # 检查是否到了5分钟周期
        recent_bars = list(self.minute1_bars)[-5:]
        if not self._is_timeframe_complete(recent_bars, minutes=5):
            return None
        
        # 合成5分钟K线
        return self._synthesize_bar(recent_bars)
    
    def _try_synthesize_1h_bar(self) -> Optional[Any]:
        """尝试合成1小时K线"""
        if len(self.minute5_bars) < 12:  # 12 * 5分钟 = 60分钟
            return None
        
        # 检查是否到了1小时周期
        recent_bars = list(self.minute5_bars)[-12:]
        if not self._is_timeframe_complete(recent_bars, minutes=60):
            return None
        
        # 合成1小时K线
        return self._synthesize_bar(recent_bars)
    
    def _try_synthesize_4h_bar(self) -> Optional[Any]:
        """尝试合成4小时K线"""
        if len(self.hour1_bars) < 4:
            return None
        
        # 检查是否到了4小时周期
        recent_bars = list(self.hour1_bars)[-4:]
        if not self._is_timeframe_complete(recent_bars, minutes=240):
            return None
        
        # 合成4小时K线
        return self._synthesize_bar(recent_bars)
    
    def _is_timeframe_complete(self, bars: list, minutes: int) -> bool:
        """检查时间周期是否完整"""
        if not bars:
            return False
        
        # 简化版：检查最后一个bar的时间是否对齐到周期边界
        last_bar = bars[-1]
        if hasattr(last_bar, 'datetime'):
            dt = last_bar.datetime
            # 检查分钟数是否能被周期整除
            if isinstance(dt, datetime):
                return dt.minute % minutes == 0
        
        # 如果没有datetime属性，简单检查数量
        return len(bars) >= minutes
    
    def _synthesize_bar(self, bars: list) -> Any:
        """合成高周期K线"""
        if not bars:
            return None
        
        # 提取数据
        opens = [b.open_price for b in bars]
        highs = [b.high_price for b in bars]
        lows = [b.low_price for b in bars]
        closes = [b.close_price for b in bars]
        volumes = [b.volume for b in bars if hasattr(b, 'volume')]
        
        # 创建合成的K线对象
        synthesized_bar = type(bars[0])(
            symbol=bars[0].symbol if hasattr(bars[0], 'symbol') else '',
            exchange=bars[0].exchange if hasattr(bars[0], 'exchange') else '',
            datetime=bars[-1].datetime if hasattr(bars[-1], 'datetime') else datetime.now(),
            open_price=opens[0],
            high_price=max(highs),
            low_price=min(lows),
            close_price=closes[-1],
            volume=sum(volumes) if volumes else 0
        )
        
        return synthesized_bar
    
    def get_all_indicators(self) -> Dict[str, Any]:
        """获取所有周期的指标"""
        return {
            '1m': self.minute1_indicators.calculate_indicators(
                self.minute1_bars[-1] if self.minute1_bars else None
            ),
            '5m': self.minute5_indicators.calculate_indicators(
                self.minute5_bars[-1] if self.minute5_bars else None
            ),
            '1h': self.hour1_indicators.calculate_indicators(
                self.hour1_bars[-1] if self.hour1_bars else None
            ),
            '4h': self.hour4_indicators.calculate_indicators(
                self.hour4_bars[-1] if self.hour4_bars else None
            ),
        }
    
    def clear(self):
        """清空所有数据"""
        self.minute1_bars.clear()
        self.minute5_bars.clear()
        self.hour1_bars.clear()
        self.hour4_bars.clear()
        
        self.minute1_indicators.clear()
        self.minute5_indicators.clear()
        self.hour1_indicators.clear()
        self.hour4_indicators.clear()


