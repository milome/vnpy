#!/usr/bin/env python3
"""
实时多周期图表系统
支持4小时、1小时、5分钟、1分钟K线同时显示
包含交易信号、技术指标叠加功能
"""

import sys
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import pyqtgraph as pg
from pyqtgraph import PlotWidget, BarGraphItem, ScatterPlotItem

# 设置pyqtgraph的全局配置
pg.setConfigOptions(antialias=True, useOpenGL=True)


class CandlestickItem(pg.GraphicsObject):
    """K线图形项"""
    
    def __init__(self, data):
        pg.GraphicsObject.__init__(self)
        self.data = data
        self.generatePicture()
    
    def generatePicture(self):
        """生成K线图形"""
        self.picture = QPicture()
        p = QPainter(self.picture)
        
        w = 0.8  # K线宽度
        
        for i, (time, open_price, high, low, close) in enumerate(self.data):
            # 确定颜色
            if close > open_price:
                # 阳线 - 红色
                brush = QBrush(QColor(255, 0, 0))
                pen = QPen(QColor(255, 0, 0))
            else:
                # 阴线 - 绿色
                brush = QBrush(QColor(0, 255, 0))
                pen = QPen(QColor(0, 255, 0))
            
            p.setPen(pen)
            p.setBrush(brush)
            
            # 绘制影线
            p.drawLine(QPointF(i, low), QPointF(i, high))
            
            # 绘制实体
            if close != open_price:
                rect = QRectF(i - w/2, min(open_price, close), w, abs(close - open_price))
                p.drawRect(rect)
            else:
                # 十字星
                p.drawLine(QPointF(i - w/2, close), QPointF(i + w/2, close))
        
        p.end()
    
    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)
    
    def boundingRect(self):
        return QRectF(self.picture.boundingRect())


class TechnicalIndicatorWidget(QWidget):
    """技术指标显示组件"""
    
    def __init__(self, timeframe: str):
        super().__init__()
        self.timeframe = timeframe
        self.setupUI()
        
    def setupUI(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        # 指标数值显示区域
        self.indicator_labels = {}
        
        # 创建指标显示网格
        grid_layout = QGridLayout()
        
        # 定义要显示的指标
        indicators = [
            ("MA5", "5日均线"), ("MA20", "20日均线"), ("MACD", "MACD"),
            ("RSI", "RSI"), ("KDJ_K", "KDJ-K"), ("ATR", "ATR"),
            ("成交量", "Volume"), ("信号", "Signal")
        ]
        
        for i, (key, name) in enumerate(indicators):
            row, col = i // 4, i % 4
            
            label = QLabel(f"{name}: --")
            label.setStyleSheet("font-size: 10px; color: white; padding: 2px;")
            label.setMinimumWidth(80)
            
            self.indicator_labels[key] = label
            grid_layout.addWidget(label, row, col)
        
        layout.addLayout(grid_layout)
        
    def update_indicators(self, indicators: Dict):
        """更新指标显示"""
        # 更新各个指标的显示
        indicator_mapping = {
            "MA5": "ma5",
            "MA20": "ma20", 
            "MACD": "macd_hist",
            "RSI": "rsi",
            "KDJ_K": "kdj_k",
            "ATR": "atr",
            "成交量": "volume_ratio",
            "信号": "final_signal"
        }
        
        for display_name, data_key in indicator_mapping.items():
            if display_name in self.indicator_labels:
                value = indicators.get(data_key, 0)
                
                if data_key == "final_signal":
                    # 信号特殊处理
                    if value > 0:
                        text = "买入"
                        color = "color: red;"
                    elif value < 0:
                        text = "卖出" 
                        color = "color: green;"
                    else:
                        text = "观望"
                        color = "color: gray;"
                    
                    self.indicator_labels[display_name].setText(f"信号: {text}")
                    self.indicator_labels[display_name].setStyleSheet(f"font-size: 10px; {color} padding: 2px;")
                else:
                    # 数值指标
                    if isinstance(value, float):
                        text = f"{display_name}: {value:.2f}"
                    else:
                        text = f"{display_name}: {value}"
                    
                    self.indicator_labels[display_name].setText(text)


class SingleTimeframeChart(QWidget):
    """单个时间周期的图表组件"""
    
    def __init__(self, timeframe: str):
        super().__init__()
        self.timeframe = timeframe
        self.max_bars = 200  # 最大显示K线数量
        
        # 数据存储
        self.ohlc_data = []  # [(time, open, high, low, close, volume), ...]
        self.indicator_data = {}
        self.signal_data = []  # [(time, price, signal_type), ...]
        
        self.setupUI()
        
    def setupUI(self):
        """设置UI界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 标题
        title_label = QLabel(f"{self.timeframe} 周期")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 14px; 
            font-weight: bold; 
            color: white; 
            background-color: #2b2b2b; 
            padding: 5px; 
            border-radius: 3px;
        """)
        layout.addWidget(title_label)
        
        # 主图表区域
        self.main_chart = PlotWidget()
        self.main_chart.setBackground('black')
        self.main_chart.showGrid(x=True, y=True, alpha=0.3)
        self.main_chart.setLabel('left', '价格', color='white')
        self.main_chart.setMinimumHeight(300)
        
        # 设置图表样式
        self.main_chart.getAxis('left').setPen('white')
        self.main_chart.getAxis('bottom').setPen('white')
        self.main_chart.getAxis('left').setTextPen('white')
        self.main_chart.getAxis('bottom').setTextPen('white')
        
        layout.addWidget(self.main_chart)
        
        # 成交量图表
        self.volume_chart = PlotWidget()
        self.volume_chart.setBackground('black')
        self.volume_chart.showGrid(x=True, y=True, alpha=0.3)
        self.volume_chart.setLabel('left', '成交量', color='white')
        self.volume_chart.setMaximumHeight(100)
        self.volume_chart.setXLink(self.main_chart)  # 链接X轴
        
        self.volume_chart.getAxis('left').setPen('white')
        self.volume_chart.getAxis('bottom').setPen('white')
        self.volume_chart.getAxis('left').setTextPen('white')
        self.volume_chart.getAxis('bottom').setTextPen('white')
        
        layout.addWidget(self.volume_chart)
        
        # 技术指标显示
        self.indicator_widget = TechnicalIndicatorWidget(self.timeframe)
        layout.addWidget(self.indicator_widget)
        
        # 设置布局比例
        layout.setStretchFactor(title_label, 0)
        layout.setStretchFactor(self.main_chart, 4)
        layout.setStretchFactor(self.volume_chart, 1)
        layout.setStretchFactor(self.indicator_widget, 0)
    
    def add_bar_data(self, timestamp: datetime, open_price: float, high: float, 
                     low: float, close: float, volume: float):
        """添加K线数据"""
        # 添加新数据
        self.ohlc_data.append((len(self.ohlc_data), open_price, high, low, close, volume))
        
        # 保持数据长度
        if len(self.ohlc_data) > self.max_bars:
            self.ohlc_data = self.ohlc_data[-self.max_bars:]
            # 重新编号
            self.ohlc_data = [(i, *data[1:]) for i, data in enumerate(self.ohlc_data)]
    
    def add_signal(self, signal_type: int, price: float):
        """添加交易信号"""
        if len(self.ohlc_data) > 0:
            time_index = len(self.ohlc_data) - 1
            self.signal_data.append((time_index, price, signal_type))
            
            # 保持信号数据长度
            if len(self.signal_data) > self.max_bars:
                self.signal_data = self.signal_data[-self.max_bars:]
    
    def update_indicators(self, indicators: Dict):
        """更新技术指标"""
        self.indicator_data = indicators
        self.indicator_widget.update_indicators(indicators)
    
    def refresh_chart(self):
        """刷新图表显示"""
        if len(self.ohlc_data) < 2:
            return
        
        # 清除旧的绘图项
        self.main_chart.clear()
        self.volume_chart.clear()
        
        # 绘制K线
        self.draw_candlesticks()
        
        # 绘制移动平均线
        self.draw_moving_averages()
        
        # 绘制交易信号
        self.draw_trading_signals()
        
        # 绘制成交量
        self.draw_volume()
        
        # 绘制技术指标线
        self.draw_technical_indicators()
    
    def draw_candlesticks(self):
        """绘制K线"""
        if len(self.ohlc_data) < 1:
            return
        
        # 准备K线数据
        candlestick_data = [(i, o, h, l, c) for i, o, h, l, c, v in self.ohlc_data]
        
        # 创建K线图形项
        candlestick_item = CandlestickItem(candlestick_data)
        self.main_chart.addItem(candlestick_item)
    
    def draw_moving_averages(self):
        """绘制移动平均线"""
        if len(self.ohlc_data) < 20:
            return
        
        # 提取收盘价
        closes = [c for _, _, _, _, c, _ in self.ohlc_data]
        x_data = list(range(len(closes)))
        
        # 绘制MA5
        if len(closes) >= 5:
            ma5 = pd.Series(closes).rolling(5).mean().values
            valid_indices = ~np.isnan(ma5)
            if np.any(valid_indices):
                self.main_chart.plot(
                    np.array(x_data)[valid_indices], 
                    ma5[valid_indices], 
                    pen=pg.mkPen(color='yellow', width=1),
                    name='MA5'
                )
        
        # 绘制MA20
        if len(closes) >= 20:
            ma20 = pd.Series(closes).rolling(20).mean().values
            valid_indices = ~np.isnan(ma20)
            if np.any(valid_indices):
                self.main_chart.plot(
                    np.array(x_data)[valid_indices], 
                    ma20[valid_indices], 
                    pen=pg.mkPen(color='cyan', width=1),
                    name='MA20'
                )
    
    def draw_trading_signals(self):
        """绘制交易信号"""
        if not self.signal_data:
            return
        
        # 分离买入和卖出信号
        buy_signals = [(t, p) for t, p, s in self.signal_data if s > 0]
        sell_signals = [(t, p) for t, p, s in self.signal_data if s < 0]
        
        # 绘制买入信号
        if buy_signals:
            buy_times, buy_prices = zip(*buy_signals)
            scatter_buy = ScatterPlotItem(
                pos=list(zip(buy_times, buy_prices)),
                symbol='t',  # 向上三角形
                size=12,
                brush=pg.mkBrush(color='red'),
                pen=pg.mkPen(color='red', width=2)
            )
            self.main_chart.addItem(scatter_buy)
        
        # 绘制卖出信号
        if sell_signals:
            sell_times, sell_prices = zip(*sell_signals)
            scatter_sell = ScatterPlotItem(
                pos=list(zip(sell_times, sell_prices)),
                symbol='t1',  # 向下三角形
                size=12,
                brush=pg.mkBrush(color='green'),
                pen=pg.mkPen(color='green', width=2)
            )
            self.main_chart.addItem(scatter_sell)
    
    def draw_volume(self):
        """绘制成交量"""
        if len(self.ohlc_data) < 1:
            return
        
        # 提取成交量数据
        volumes = [v for _, _, _, _, _, v in self.ohlc_data]
        x_data = list(range(len(volumes)))
        
        # 创建成交量柱状图
        volume_bars = BarGraphItem(
            x=x_data, 
            height=volumes, 
            width=0.8, 
            brush=pg.mkBrush(color='blue', alpha=0.7)
        )
        self.volume_chart.addItem(volume_bars)
        
        # 绘制成交量移动平均线
        if len(volumes) >= 20:
            volume_ma = pd.Series(volumes).rolling(20).mean().values
            valid_indices = ~np.isnan(volume_ma)
            if np.any(valid_indices):
                self.volume_chart.plot(
                    np.array(x_data)[valid_indices], 
                    volume_ma[valid_indices], 
                    pen=pg.mkPen(color='orange', width=2)
                )
    
    def draw_technical_indicators(self):
        """绘制技术指标线（如布林带等）"""
        if not self.indicator_data or len(self.ohlc_data) < 20:
            return
        
        x_data = list(range(len(self.ohlc_data)))
        
        # 绘制布林带（如果有数据）
        if all(key in self.indicator_data for key in ['bb_upper', 'bb_middle', 'bb_lower']):
            # 注意：这里简化处理，实际应该维护历史布林带数据
            bb_upper = self.indicator_data['bb_upper']
            bb_middle = self.indicator_data['bb_middle']
            bb_lower = self.indicator_data['bb_lower']
            
            # 绘制当前布林带位置（水平线）
            if len(x_data) > 0:
                last_x = x_data[-1]
                self.main_chart.plot([last_x-10, last_x], [bb_upper, bb_upper], 
                                   pen=pg.mkPen(color='purple', width=1, style=Qt.DashLine))
                self.main_chart.plot([last_x-10, last_x], [bb_middle, bb_middle], 
                                   pen=pg.mkPen(color='purple', width=1))
                self.main_chart.plot([last_x-10, last_x], [bb_lower, bb_lower], 
                                   pen=pg.mkPen(color='purple', width=1, style=Qt.DashLine))


class MultiTimeframeChartWindow(QMainWindow):
    """多周期图表主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("多周期策略实时监控系统")
        self.setGeometry(100, 100, 1800, 1200)
        
        # 时间周期配置
        self.timeframes = ["4h", "1h", "5m", "1m"]
        self.charts = {}
        
        # 策略状态
        self.strategy_running = False
        self.current_position = 0
        self.total_pnl = 0.0
        
        self.setupUI()
        self.setupTimer()
        
    def setupUI(self):
        """设置用户界面"""
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建顶部控制面板
        self.create_control_panel(main_layout)
        
        # 创建图表区域
        self.create_chart_area(main_layout)
        
        # 创建底部状态栏
        self.create_status_bar(main_layout)
        
        # 设置样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QWidget {
                background-color: #1e1e1e;
                color: white;
            }
            QPushButton {
                background-color: #3c3c3c;
                border: 1px solid #555;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #4c4c4c;
            }
            QPushButton:pressed {
                background-color: #2c2c2c;
            }
            QLabel {
                font-size: 12px;
                padding: 4px;
            }
        """)
    
    def create_control_panel(self, main_layout):
        """创建控制面板"""
        control_panel = QWidget()
        control_panel.setMaximumHeight(80)
        control_layout = QHBoxLayout(control_panel)
        
        # 策略控制按钮
        self.start_btn = QPushButton("启动策略")
        self.start_btn.clicked.connect(self.start_strategy)
        self.start_btn.setStyleSheet("QPushButton { background-color: #2d5a2d; }")
        
        self.stop_btn = QPushButton("停止策略")
        self.stop_btn.clicked.connect(self.stop_strategy)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("QPushButton { background-color: #5a2d2d; }")
        
        # 状态显示
        self.status_label = QLabel("状态: 未启动")
        self.position_label = QLabel("持仓: 0")
        self.pnl_label = QLabel("盈亏: ¥0.00")
        
        # 添加到布局
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        control_layout.addStretch()
        control_layout.addWidget(self.status_label)
        control_layout.addWidget(self.position_label)
        control_layout.addWidget(self.pnl_label)
        
        main_layout.addWidget(control_panel)
    
    def create_chart_area(self, main_layout):
        """创建图表区域"""
        # 创建2x2网格布局
        chart_widget = QWidget()
        chart_layout = QGridLayout(chart_widget)
        chart_layout.setSpacing(10)
        
        # 创建各个时间周期的图表
        positions = [(0, 0), (0, 1), (1, 0), (1, 1)]
        
        for timeframe, pos in zip(self.timeframes, positions):
            chart = SingleTimeframeChart(timeframe)
            self.charts[timeframe] = chart
            chart_layout.addWidget(chart, pos[0], pos[1])
        
        main_layout.addWidget(chart_widget)
    
    def create_status_bar(self, main_layout):
        """创建状态栏"""
        status_widget = QWidget()
        status_widget.setMaximumHeight(40)
        status_layout = QHBoxLayout(status_widget)
        
        self.time_label = QLabel(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.connection_label = QLabel("连接状态: 未连接")
        
        status_layout.addWidget(self.time_label)
        status_layout.addStretch()
        status_layout.addWidget(self.connection_label)
        
        main_layout.addWidget(status_widget)
    
    def setupTimer(self):
        """设置定时器"""
        # 图表更新定时器
        self.chart_timer = QTimer()
        self.chart_timer.timeout.connect(self.update_charts)
        self.chart_timer.start(1000)  # 每秒更新
        
        # 时间显示定时器
        self.time_timer = QTimer()
        self.time_timer.timeout.connect(self.update_time)
        self.time_timer.start(1000)
    
    def start_strategy(self):
        """启动策略"""
        self.strategy_running = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("状态: 运行中")
        self.connection_label.setText("连接状态: 已连接")
        
        # 开始模拟数据
        self.start_simulation()
    
    def stop_strategy(self):
        """停止策略"""
        self.strategy_running = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("状态: 已停止")
        self.connection_label.setText("连接状态: 未连接")
    
    def start_simulation(self):
        """开始数据模拟（用于演示）"""
        # 模拟数据生成定时器
        self.simulation_timer = QTimer()
        self.simulation_timer.timeout.connect(self.generate_simulation_data)
        self.simulation_timer.start(2000)  # 每2秒生成一次数据
        
        # 初始化模拟数据
        self.base_price = 25000.0
        self.simulation_time = datetime.now()
    
    def generate_simulation_data(self):
        """生成模拟数据"""
        if not self.strategy_running:
            return
        
        # 生成随机价格变动
        price_change = np.random.normal(0, 50)  # 正态分布的价格变动
        self.base_price += price_change
        
        # 生成OHLC数据
        open_price = self.base_price
        high_price = open_price + abs(np.random.normal(0, 30))
        low_price = open_price - abs(np.random.normal(0, 30))
        close_price = open_price + price_change
        volume = np.random.randint(1000, 5000)
        
        # 更新时间
        self.simulation_time += timedelta(minutes=1)
        
        # 添加数据到1分钟图表
        self.charts["1m"].add_bar_data(
            self.simulation_time, open_price, high_price, low_price, close_price, volume
        )
        
        # 模拟技术指标数据
        indicators = {
            "ma5": close_price + np.random.normal(0, 10),
            "ma20": close_price + np.random.normal(0, 20),
            "macd_hist": np.random.normal(0, 5),
            "rsi": np.random.uniform(30, 70),
            "kdj_k": np.random.uniform(20, 80),
            "atr": abs(np.random.normal(50, 10)),
            "volume_ratio": np.random.uniform(0.5, 2.0),
            "bb_upper": close_price + 100,
            "bb_middle": close_price,
            "bb_lower": close_price - 100,
            "final_signal": np.random.choice([-1, 0, 1], p=[0.1, 0.8, 0.1])
        }
        
        self.charts["1m"].update_indicators(indicators)
        
        # 生成交易信号
        if indicators["final_signal"] != 0:
            self.charts["1m"].add_signal(indicators["final_signal"], close_price)
            
            # 更新持仓
            if indicators["final_signal"] > 0:
                self.current_position += 1
            else:
                self.current_position -= 1
            
            self.position_label.setText(f"持仓: {self.current_position}")
        
        # 模拟其他周期数据（简化处理）
        for timeframe in ["5m", "1h", "4h"]:
            if np.random.random() < 0.3:  # 30%概率更新其他周期
                self.charts[timeframe].add_bar_data(
                    self.simulation_time, open_price, high_price, low_price, close_price, volume
                )
                self.charts[timeframe].update_indicators(indicators)
    
    def update_charts(self):
        """更新所有图表"""
        for chart in self.charts.values():
            chart.refresh_chart()
    
    def update_time(self):
        """更新时间显示"""
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.time_label.setText(f"当前时间: {current_time}")
    
    def update_strategy_data(self, timeframe: str, bar_data: Dict, indicators: Dict, signal: int):
        """更新策略数据（外部调用接口）"""
        if timeframe in self.charts:
            chart = self.charts[timeframe]
            
            # 添加K线数据
            chart.add_bar_data(
                bar_data.get("datetime", datetime.now()),
                bar_data.get("open", 0),
                bar_data.get("high", 0),
                bar_data.get("low", 0),
                bar_data.get("close", 0),
                bar_data.get("volume", 0)
            )
            
            # 更新指标
            chart.update_indicators(indicators)
            
            # 添加信号
            if signal != 0:
                chart.add_signal(signal, bar_data.get("close", 0))
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        if hasattr(self, 'simulation_timer'):
            self.simulation_timer.stop()
        self.chart_timer.stop()
        self.time_timer.stop()
        event.accept()


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 创建主窗口
    window = MultiTimeframeChartWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

