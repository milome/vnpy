#!/usr/bin/env python3
"""
多周期模块化策略完整集成示例
演示如何将麦语言转换的策略与实时可视化系统集成

使用方法:
1. 确保安装了所有依赖包
2. 运行此文件启动完整系统
3. 点击"启动策略"开始模拟交易
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

# 添加项目路径
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QMessageBox
from PyQt5.QtCore import QTimer, QThread, pyqtSignal

# 导入我们的模块
from indicators import Minute1Indicators, Minute5Indicators, Hour1Indicators, Hour4Indicators
from visualization.real_time_charts import MultiTimeframeChartWindow
from data.timeframe_manager import TimeframeManager

# 模拟VNPy的数据结构
class BarData:
    """模拟的K线数据结构"""
    def __init__(self, symbol, exchange, datetime, open_price, high_price, low_price, close_price, volume):
        self.symbol = symbol
        self.exchange = exchange
        self.datetime = datetime
        self.open_price = open_price
        self.high_price = high_price
        self.low_price = low_price
        self.close_price = close_price
        self.volume = volume
        self.turnover = close_price * volume


class StrategyDataGenerator(QThread):
    """策略数据生成器（模拟实时数据）"""
    
    # 信号定义
    new_bar_signal = pyqtSignal(object, dict)  # (bar_data, all_indicators)
    
    def __init__(self):
        super().__init__()
        self.running = False
        self.base_price = 25000.0
        self.current_time = datetime.now()
        
        # 初始化多周期管理器
        self.timeframe_manager = TimeframeManager()
        
        # 策略状态
        self.position = 0
        self.total_pnl = 0.0
        self.trade_count = 0
        
    def start_generation(self):
        """开始生成数据"""
        self.running = True
        self.start()
    
    def stop_generation(self):
        """停止生成数据"""
        self.running = False
        self.quit()
        self.wait()
    
    def run(self):
        """主运行循环"""
        while self.running:
            try:
                # 生成1分钟K线数据
                bar_data = self.generate_bar_data()
                
                # 更新多周期指标
                all_indicators = self.timeframe_manager.update_1m_bar(bar_data)
                
                # 生成交易信号
                trading_signals = self.generate_trading_signals(all_indicators)
                
                # 合并指标和信号
                combined_data = {
                    "indicators": all_indicators,
                    "signals": trading_signals,
                    "position": self.position,
                    "pnl": self.total_pnl
                }
                
                # 发送信号
                self.new_bar_signal.emit(bar_data, combined_data)
                
                # 等待1秒（模拟实时数据）
                self.msleep(1000)
                
            except Exception as e:
                print(f"数据生成错误: {e}")
                break
    
    def generate_bar_data(self) -> BarData:
        """生成模拟K线数据"""
        # 模拟价格波动
        price_change = np.random.normal(0, 20)  # 正态分布价格变动
        self.base_price += price_change
        
        # 确保价格在合理范围内
        self.base_price = max(20000, min(30000, self.base_price))
        
        # 生成OHLC数据
        open_price = self.base_price - price_change
        close_price = self.base_price
        
        # 生成高低价
        volatility = abs(np.random.normal(0, 30))
        high_price = max(open_price, close_price) + volatility * 0.7
        low_price = min(open_price, close_price) - volatility * 0.3
        
        # 生成成交量
        base_volume = 2000
        volume_factor = 1 + abs(price_change) / 50  # 价格变动越大，成交量越大
        volume = int(base_volume * volume_factor * np.random.uniform(0.5, 2.0))
        
        # 更新时间
        self.current_time += timedelta(minutes=1)
        
        return BarData(
            symbol="MHImain",
            exchange="HKFE", 
            datetime=self.current_time,
            open_price=open_price,
            high_price=high_price,
            low_price=low_price,
            close_price=close_price,
            volume=volume
        )
    
    def generate_trading_signals(self, all_indicators: Dict[str, Dict]) -> Dict[str, int]:
        """生成交易信号"""
        signals = {}
        
        # 为每个时间周期生成信号
        for timeframe, indicators in all_indicators.items():
            if not indicators:
                signals[timeframe] = 0
                continue
            
            signal = 0
            
            # 基于不同周期的不同策略
            if timeframe == "1m":
                # 1分钟：快速反转策略
                rsi = indicators.get('rsi', 50)
                macd_hist = indicators.get('macd_hist', 0)
                
                if rsi < 30 and macd_hist > 0:
                    signal = 1  # 买入
                elif rsi > 70 and macd_hist < 0:
                    signal = -1  # 卖出
                    
            elif timeframe == "5m":
                # 5分钟：综合信号
                final_signal = indicators.get('final_signal', 0)
                signal_strength = indicators.get('signal_strength', 0)
                
                if abs(signal_strength) > 0.3:
                    signal = final_signal
                    
            elif timeframe == "1h":
                # 1小时：趋势跟踪
                long_trend = indicators.get('long_trend', 0)
                macd_1h = indicators.get('macd_1h', 0)
                macd_signal_1h = indicators.get('macd_signal_1h', 0)
                
                if long_trend == 1 and macd_1h > macd_signal_1h:
                    signal = 1
                elif long_trend == -1 and macd_1h < macd_signal_1h:
                    signal = -1
                    
            elif timeframe == "4h":
                # 4小时：主要趋势
                major_trend = indicators.get('major_trend', 0)
                signal = major_trend
            
            signals[timeframe] = signal
        
        # 计算最终综合信号
        signal_weights = {"1m": 0.1, "5m": 0.2, "1h": 0.3, "4h": 0.4}
        weighted_sum = sum(signals.get(tf, 0) * weight for tf, weight in signal_weights.items())
        
        if weighted_sum > 0.3:
            final_signal = 1
        elif weighted_sum < -0.3:
            final_signal = -1
        else:
            final_signal = 0
        
        signals["final"] = final_signal
        
        # 模拟交易执行
        if final_signal != 0 and self.position == 0:
            self.position = final_signal
            self.trade_count += 1
        elif final_signal == 0 and self.position != 0:
            # 平仓，计算盈亏
            pnl = np.random.normal(0, 100)  # 模拟盈亏
            self.total_pnl += pnl
            self.position = 0
        
        return signals


class IntegratedStrategySystem(QMainWindow):
    """集成策略系统主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("多周期模块化策略系统 - 完整集成版")
        self.setGeometry(50, 50, 1900, 1300)
        
        # 初始化组件
        self.chart_window = None
        self.data_generator = None
        
        self.setupUI()
        self.setup_connections()
        
    def setupUI(self):
        """设置用户界面"""
        # 创建图表窗口
        self.chart_window = MultiTimeframeChartWindow()
        
        # 将图表窗口设置为中央部件
        self.setCentralWidget(self.chart_window.centralWidget())
        
        # 复制图表窗口的菜单栏和状态栏
        if self.chart_window.menuBar():
            self.setMenuBar(self.chart_window.menuBar())
        if self.chart_window.statusBar():
            self.setStatusBar(self.chart_window.statusBar())
    
    def setup_connections(self):
        """设置信号连接"""
        # 重写图表窗口的启动/停止方法
        original_start = self.chart_window.start_strategy
        original_stop = self.chart_window.stop_strategy
        
        def enhanced_start():
            original_start()
            self.start_data_generation()
        
        def enhanced_stop():
            original_stop()
            self.stop_data_generation()
        
        self.chart_window.start_strategy = enhanced_start
        self.chart_window.stop_strategy = enhanced_stop
    
    def start_data_generation(self):
        """启动数据生成"""
        try:
            # 创建数据生成器
            self.data_generator = StrategyDataGenerator()
            
            # 连接信号
            self.data_generator.new_bar_signal.connect(self.on_new_bar_data)
            
            # 启动数据生成
            self.data_generator.start_generation()
            
            print("数据生成器启动成功")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动数据生成器失败: {e}")
    
    def stop_data_generation(self):
        """停止数据生成"""
        if self.data_generator:
            self.data_generator.stop_generation()
            self.data_generator = None
            print("数据生成器已停止")
    
    def on_new_bar_data(self, bar_data: BarData, combined_data: Dict):
        """处理新的K线数据"""
        try:
            indicators = combined_data.get("indicators", {})
            signals = combined_data.get("signals", {})
            position = combined_data.get("position", 0)
            pnl = combined_data.get("pnl", 0.0)
            
            # 更新图表数据
            for timeframe in ["1m", "5m", "1h", "4h"]:
                if timeframe in indicators:
                    # 准备K线数据
                    bar_dict = {
                        "datetime": bar_data.datetime,
                        "open": bar_data.open_price,
                        "high": bar_data.high_price,
                        "low": bar_data.low_price,
                        "close": bar_data.close_price,
                        "volume": bar_data.volume
                    }
                    
                    # 获取信号
                    signal = signals.get(timeframe, 0)
                    
                    # 更新图表
                    self.chart_window.update_strategy_data(
                        timeframe, bar_dict, indicators[timeframe], signal
                    )
            
            # 更新策略状态显示
            self.update_strategy_status(position, pnl, signals.get("final", 0))
            
        except Exception as e:
            print(f"处理K线数据错误: {e}")
    
    def update_strategy_status(self, position: int, pnl: float, final_signal: int):
        """更新策略状态显示"""
        # 更新持仓显示
        self.chart_window.current_position = position
        self.chart_window.position_label.setText(f"持仓: {position}")
        
        # 更新盈亏显示
        self.chart_window.total_pnl = pnl
        self.chart_window.pnl_label.setText(f"盈亏: ¥{pnl:.2f}")
        
        # 根据盈亏设置颜色
        if pnl > 0:
            self.chart_window.pnl_label.setStyleSheet("color: red; font-size: 12px; padding: 4px;")
        elif pnl < 0:
            self.chart_window.pnl_label.setStyleSheet("color: green; font-size: 12px; padding: 4px;")
        else:
            self.chart_window.pnl_label.setStyleSheet("color: white; font-size: 12px; padding: 4px;")
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        # 停止数据生成
        self.stop_data_generation()
        
        # 关闭图表窗口
        if self.chart_window:
            self.chart_window.close()
        
        event.accept()


def check_dependencies():
    """检查依赖包"""
    # 包名到导入名的映射（安装名: 导入名）
    package_mapping = {
        "PyQt5": "PyQt5",  # 安装名和导入名相同（大写）
        "pyqtgraph": "pyqtgraph",
        "numpy": "numpy",
        "pandas": "pandas",
        "talib": "talib",  # 安装名是 ta-lib，但导入名是 talib
    }
    
    missing_packages = []
    
    for install_name, import_name in package_mapping.items():
        try:
            # 尝试导入模块
            if '.' in import_name:
                # 对于像 PyQt5.QtWidgets 这样的模块，只检查顶层包
                top_level = import_name.split('.')[0]
                __import__(top_level)
            else:
                __import__(import_name)
        except ImportError:
            missing_packages.append(install_name)
    
    if missing_packages:
        print("缺少以下依赖包:")
        for package in missing_packages:
            print(f"  - {package}")
        print("\n请运行以下命令安装:")
        # talib 的安装名是 ta-lib
        install_commands = [pkg if pkg != "talib" else "TA-Lib" for pkg in missing_packages]
        print(f"pip install {' '.join(install_commands)}")
        return False
    
    return True


def create_project_structure():
    """创建项目目录结构"""
    directories = [
        "indicators",
        "visualization", 
        "data",
        "strategy",
        "config",
        "tests"
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        
        # 创建__init__.py文件
        init_file = Path(directory) / "__init__.py"
        if not init_file.exists():
            init_file.write_text("# 自动生成的__init__.py文件\n")
    
    print("项目目录结构创建完成")


def main():
    """主函数"""
    print("=" * 60)
    print("多周期模块化策略系统 - 完整集成版")
    print("=" * 60)
    
    # 检查依赖
    if not check_dependencies():
        return
    
    # 创建项目结构
    create_project_structure()
    
    # 创建Qt应用
    app = QApplication(sys.argv)
    
    try:
        # 创建主窗口
        main_window = IntegratedStrategySystem()
        main_window.show()
        
        print("\n系统启动成功!")
        print("使用说明:")
        print("1. 点击'启动策略'开始模拟交易")
        print("2. 观察4个时间周期的实时图表")
        print("3. 查看技术指标和交易信号")
        print("4. 监控持仓和盈亏变化")
        print("5. 点击'停止策略'结束交易")
        
        # 运行应用
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"系统启动失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
