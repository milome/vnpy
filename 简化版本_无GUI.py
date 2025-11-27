#!/usr/bin/env python3
"""
多周期策略系统 - 简化版本（无GUI）
适用于没有PyQt5环境的情况，使用matplotlib显示图表

运行要求：
- Python 3.7+
- numpy, pandas, matplotlib (通常已预装)
"""

import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import time
from typing import Dict, List, Optional
import warnings
warnings.filterwarnings('ignore')

# 设置matplotlib中文显示
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class SimpleBarData:
    """简化的K线数据结构"""
    def __init__(self, datetime, open_price, high_price, low_price, close_price, volume):
        self.datetime = datetime
        self.open_price = open_price
        self.high_price = high_price
        self.low_price = low_price
        self.close_price = close_price
        self.volume = volume

class SimpleIndicator:
    """简化的技术指标计算器"""
    
    def __init__(self, timeframe: str):
        self.timeframe = timeframe
        self.data_buffer = []
        self.max_size = 200
    
    def update_bar(self, bar: SimpleBarData) -> Dict:
        """更新K线数据并计算指标"""
        self.data_buffer.append(bar)
        
        # 保持缓冲区大小
        if len(self.data_buffer) > self.max_size:
            self.data_buffer.pop(0)
        
        if len(self.data_buffer) < 20:
            return {}
        
        return self.calculate_indicators()
    
    def calculate_indicators(self) -> Dict:
        """计算技术指标"""
        closes = np.array([bar.close_price for bar in self.data_buffer])
        highs = np.array([bar.high_price for bar in self.data_buffer])
        lows = np.array([bar.low_price for bar in self.data_buffer])
        volumes = np.array([bar.volume for bar in self.data_buffer])
        
        indicators = {}
        
        try:
            # 移动平均线
            if len(closes) >= 5:
                indicators['ma5'] = np.mean(closes[-5:])
            if len(closes) >= 20:
                indicators['ma20'] = np.mean(closes[-20:])
            
            # 简化的MACD
            if len(closes) >= 26:
                ema12 = self.ema(closes, 12)
                ema26 = self.ema(closes, 26)
                macd = ema12 - ema26
                indicators['macd'] = macd
                
                # MACD信号线
                if len(closes) >= 35:
                    macd_history = []
                    for i in range(9, len(closes)):
                        ema12_i = self.ema(closes[:i+1], 12)
                        ema26_i = self.ema(closes[:i+1], 26)
                        macd_history.append(ema12_i - ema26_i)
                    
                    if len(macd_history) >= 9:
                        macd_signal = self.ema(np.array(macd_history), 9)
                        indicators['macd_signal'] = macd_signal
                        indicators['macd_hist'] = macd - macd_signal
            
            # 简化的RSI
            if len(closes) >= 14:
                indicators['rsi'] = self.rsi(closes, 14)
            
            # 布林带
            if len(closes) >= 20:
                ma20 = np.mean(closes[-20:])
                std20 = np.std(closes[-20:])
                indicators['bb_upper'] = ma20 + 2 * std20
                indicators['bb_middle'] = ma20
                indicators['bb_lower'] = ma20 - 2 * std20
            
            # ATR
            if len(closes) >= 14:
                indicators['atr'] = self.atr(highs, lows, closes, 14)
            
            # 成交量指标
            if len(volumes) >= 20:
                indicators['volume_ma'] = np.mean(volumes[-20:])
                indicators['volume_ratio'] = volumes[-1] / np.mean(volumes[-20:])
            
            # 趋势判断
            if 'ma5' in indicators and 'ma20' in indicators:
                if indicators['ma5'] > indicators['ma20']:
                    indicators['trend'] = 1
                elif indicators['ma5'] < indicators['ma20']:
                    indicators['trend'] = -1
                else:
                    indicators['trend'] = 0
            
            # 综合信号
            signal = 0
            signal_strength = 0
            
            # 基于多个指标的简单信号
            bullish_signals = 0
            bearish_signals = 0
            
            # MACD信号
            if 'macd_hist' in indicators:
                if indicators['macd_hist'] > 0:
                    bullish_signals += 1
                else:
                    bearish_signals += 1
            
            # RSI信号
            if 'rsi' in indicators:
                rsi = indicators['rsi']
                if 30 < rsi < 70:
                    if rsi > 50:
                        bullish_signals += 1
                    else:
                        bearish_signals += 1
            
            # 趋势信号
            if 'trend' in indicators:
                if indicators['trend'] > 0:
                    bullish_signals += 1
                elif indicators['trend'] < 0:
                    bearish_signals += 1
            
            # 计算最终信号
            total_signals = bullish_signals + bearish_signals
            if total_signals > 0:
                signal_strength = (bullish_signals - bearish_signals) / total_signals
                if signal_strength > 0.3:
                    signal = 1
                elif signal_strength < -0.3:
                    signal = -1
            
            indicators['final_signal'] = signal
            indicators['signal_strength'] = signal_strength
            indicators['bullish_count'] = bullish_signals
            indicators['bearish_count'] = bearish_signals
            
        except Exception as e:
            print(f"指标计算错误 ({self.timeframe}): {e}")
        
        return indicators
    
    def ema(self, data, period):
        """指数移动平均"""
        alpha = 2.0 / (period + 1.0)
        result = data[0]
        for price in data[1:]:
            result = alpha * price + (1 - alpha) * result
        return result
    
    def rsi(self, closes, period):
        """RSI指标"""
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def atr(self, highs, lows, closes, period):
        """ATR指标"""
        if len(closes) < 2:
            return 0
        
        tr_list = []
        for i in range(1, len(closes)):
            tr1 = highs[i] - lows[i]
            tr2 = abs(highs[i] - closes[i-1])
            tr3 = abs(lows[i] - closes[i-1])
            tr_list.append(max(tr1, tr2, tr3))
        
        return np.mean(tr_list[-period:]) if len(tr_list) >= period else 0

class SimpleMultiTimeframeStrategy:
    """简化的多周期策略"""
    
    def __init__(self):
        self.indicators = {
            "1m": SimpleIndicator("1m"),
            "5m": SimpleIndicator("5m"),
            "1h": SimpleIndicator("1h"),
            "4h": SimpleIndicator("4h")
        }
        
        # 数据存储
        self.chart_data = {
            "1m": {"time": [], "ohlc": [], "volume": [], "signals": [], "indicators": []},
            "5m": {"time": [], "ohlc": [], "volume": [], "signals": [], "indicators": []},
            "1h": {"time": [], "ohlc": [], "volume": [], "signals": [], "indicators": []},
            "4h": {"time": [], "ohlc": [], "volume": [], "signals": [], "indicators": []}
        }
        
        # 策略状态
        self.position = 0
        self.total_pnl = 0.0
        self.trade_count = 0
        
        # 信号权重
        self.signal_weights = {"1m": 0.1, "5m": 0.2, "1h": 0.3, "4h": 0.4}
        
    def update_data(self, timeframe: str, bar: SimpleBarData):
        """更新数据"""
        # 计算指标
        indicators = self.indicators[timeframe].update_bar(bar)
        
        # 存储数据
        data = self.chart_data[timeframe]
        data["time"].append(bar.datetime)
        data["ohlc"].append([bar.open_price, bar.high_price, bar.low_price, bar.close_price])
        data["volume"].append(bar.volume)
        data["indicators"].append(indicators)
        
        # 生成信号
        signal = indicators.get('final_signal', 0)
        data["signals"].append(signal)
        
        # 保持数据长度
        max_length = 100
        for key in data:
            if len(data[key]) > max_length:
                data[key] = data[key][-max_length:]
        
        return indicators, signal
    
    def calculate_final_signal(self) -> int:
        """计算最终信号"""
        weighted_sum = 0
        total_weight = 0
        
        for timeframe, weight in self.signal_weights.items():
            data = self.chart_data[timeframe]
            if data["signals"]:
                signal = data["signals"][-1]
                weighted_sum += signal * weight
                total_weight += weight
        
        if total_weight > 0:
            weighted_signal = weighted_sum / total_weight
            if weighted_signal > 0.3:
                return 1
            elif weighted_signal < -0.3:
                return -1
        
        return 0
    
    def execute_trade(self, final_signal: int, current_price: float):
        """执行交易"""
        if final_signal != 0 and self.position == 0:
            # 开仓
            self.position = final_signal
            self.trade_count += 1
            action = "买入" if final_signal > 0 else "卖出"
            print(f"🔔 交易信号: {action} @ {current_price:.2f}")
            
        elif final_signal == 0 and self.position != 0:
            # 平仓
            pnl = np.random.normal(0, 50)  # 模拟盈亏
            self.total_pnl += pnl
            action = "平多" if self.position > 0 else "平空"
            print(f"💰 平仓: {action} @ {current_price:.2f}, 盈亏: {pnl:.2f}")
            self.position = 0

class SimpleDataGenerator:
    """简化的数据生成器"""
    
    def __init__(self):
        self.base_price = 25000.0
        self.current_time = datetime.now()
        
    def generate_bar(self) -> SimpleBarData:
        """生成一根K线"""
        # 价格波动
        price_change = np.random.normal(0, 20)
        self.base_price += price_change
        self.base_price = max(20000, min(30000, self.base_price))
        
        # OHLC
        open_price = self.base_price - price_change
        close_price = self.base_price
        volatility = abs(np.random.normal(0, 30))
        high_price = max(open_price, close_price) + volatility * 0.7
        low_price = min(open_price, close_price) - volatility * 0.3
        
        # 成交量
        volume = int(np.random.uniform(1000, 5000))
        
        # 时间
        self.current_time += timedelta(minutes=1)
        
        return SimpleBarData(
            datetime=self.current_time,
            open_price=open_price,
            high_price=high_price,
            low_price=low_price,
            close_price=close_price,
            volume=volume
        )

def plot_charts(strategy: SimpleMultiTimeframeStrategy):
    """绘制图表"""
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('多周期策略监控系统', fontsize=16, fontweight='bold')
    
    timeframes = ["4h", "1h", "5m", "1m"]
    positions = [(0, 0), (0, 1), (1, 0), (1, 1)]
    colors = ['red', 'blue', 'green', 'orange']
    
    for i, (timeframe, pos) in enumerate(zip(timeframes, positions)):
        ax = axes[pos[0], pos[1]]
        data = strategy.chart_data[timeframe]
        
        if not data["time"]:
            ax.set_title(f'{timeframe} - 无数据')
            continue
        
        # 提取数据
        times = data["time"][-50:]  # 最近50根K线
        ohlc = data["ohlc"][-50:]
        signals = data["signals"][-50:]
        indicators = data["indicators"][-50:]
        
        if not ohlc:
            continue
        
        # 绘制价格线
        closes = [bar[3] for bar in ohlc]  # 收盘价
        x_range = range(len(closes))
        
        ax.plot(x_range, closes, color=colors[i], linewidth=2, label='价格')
        
        # 绘制移动平均线
        ma5_values = []
        ma20_values = []
        
        for ind in indicators:
            ma5_values.append(ind.get('ma5', np.nan))
            ma20_values.append(ind.get('ma20', np.nan))
        
        if ma5_values:
            ax.plot(x_range, ma5_values, color='yellow', linewidth=1, alpha=0.7, label='MA5')
        if ma20_values:
            ax.plot(x_range, ma20_values, color='cyan', linewidth=1, alpha=0.7, label='MA20')
        
        # 绘制交易信号
        buy_points = []
        sell_points = []
        buy_x = []
        sell_x = []
        
        for j, signal in enumerate(signals):
            if signal > 0:
                buy_points.append(closes[j])
                buy_x.append(j)
            elif signal < 0:
                sell_points.append(closes[j])
                sell_x.append(j)
        
        if buy_points:
            ax.scatter(buy_x, buy_points, color='red', marker='^', s=100, label='买入', zorder=5)
        if sell_points:
            ax.scatter(sell_x, sell_points, color='green', marker='v', s=100, label='卖出', zorder=5)
        
        # 设置图表
        ax.set_title(f'{timeframe} 周期')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)
        
        # 显示最新指标值
        if indicators and indicators[-1]:
            latest = indicators[-1]
            info_text = f"RSI: {latest.get('rsi', 0):.1f}\n"
            info_text += f"信号: {latest.get('final_signal', 0)}"
            ax.text(0.02, 0.98, info_text, transform=ax.transAxes, 
                   verticalalignment='top', fontsize=8,
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    plt.tight_layout()
    return fig

def run_simple_strategy():
    """运行简化策略"""
    print("🚀 启动多周期策略系统 (简化版)")
    print("=" * 50)
    
    # 初始化组件
    strategy = SimpleMultiTimeframeStrategy()
    data_generator = SimpleDataGenerator()
    
    print("📊 开始生成模拟数据...")
    print("💡 按 Ctrl+C 停止运行")
    
    try:
        # 生成初始数据
        for i in range(50):
            bar = data_generator.generate_bar()
            
            # 更新1分钟数据
            indicators_1m, signal_1m = strategy.update_data("1m", bar)
            
            # 模拟其他周期数据（简化处理）
            if i % 5 == 0:  # 每5分钟更新5分钟数据
                strategy.update_data("5m", bar)
            if i % 60 == 0:  # 每小时更新1小时数据
                strategy.update_data("1h", bar)
            if i % 240 == 0:  # 每4小时更新4小时数据
                strategy.update_data("4h", bar)
        
        print("✅ 初始数据生成完成")
        
        # 主循环
        update_count = 0
        while True:
            # 生成新数据
            bar = data_generator.generate_bar()
            
            # 更新策略
            indicators_1m, signal_1m = strategy.update_data("1m", bar)
            
            # 模拟其他周期更新
            if update_count % 5 == 0:
                strategy.update_data("5m", bar)
            if update_count % 60 == 0:
                strategy.update_data("1h", bar)
            if update_count % 240 == 0:
                strategy.update_data("4h", bar)
            
            # 计算最终信号
            final_signal = strategy.calculate_final_signal()
            
            # 执行交易
            strategy.execute_trade(final_signal, bar.close_price)
            
            # 显示状态
            if update_count % 10 == 0:
                print(f"⏰ 时间: {bar.datetime.strftime('%H:%M:%S')} | "
                      f"价格: {bar.close_price:.2f} | "
                      f"信号: {final_signal} | "
                      f"持仓: {strategy.position} | "
                      f"盈亏: {strategy.total_pnl:.2f}")
            
            # 每30次更新绘制一次图表
            if update_count % 30 == 0:
                plt.ion()  # 开启交互模式
                fig = plot_charts(strategy)
                plt.show()
                plt.pause(0.1)
                plt.close(fig)
            
            update_count += 1
            time.sleep(0.5)  # 暂停0.5秒
            
    except KeyboardInterrupt:
        print("\n⏹️ 用户停止策略")
        
        # 最终图表
        print("📊 显示最终图表...")
        fig = plot_charts(strategy)
        plt.show()
        
        # 显示统计
        print("\n📈 策略统计:")
        print(f"   总交易次数: {strategy.trade_count}")
        print(f"   当前持仓: {strategy.position}")
        print(f"   累计盈亏: {strategy.total_pnl:.2f}")
        
    except Exception as e:
        print(f"💥 运行错误: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主函数"""
    print("🔧 多周期策略系统 - 简化版本")
    print("📝 说明: 本版本使用matplotlib显示图表，无需PyQt5")
    print("=" * 60)
    
    # 检查基础依赖
    required_modules = ['numpy', 'pandas', 'matplotlib']
    missing_modules = []
    
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    if missing_modules:
        print(f"❌ 缺少依赖包: {', '.join(missing_modules)}")
        print(f"💡 安装命令: pip install {' '.join(missing_modules)}")
        return
    
    print("✅ 依赖检查通过")
    
    # 运行策略
    run_simple_strategy()

if __name__ == "__main__":
    main()

