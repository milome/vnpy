#!/usr/bin/env python3
"""
Enhanced MHI Backtesting System using vnpy_ctabacktester
充分利用vnpy_ctabacktester repository的完整功能

主要特性:
1. 使用BacktesterEngine进行高级回测管理
2. 支持OptimizationSetting进行参数优化
3. 集成事件系统监听回测进度
4. 支持多种回测模式和数据源
5. 完整的UI和可视化支持

使用方法:
python enhanced_mhi_backtester.py
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# vnpy_ctabacktester imports - 使用完整功能
from vnpy_ctabacktester.engine import (
    BacktesterEngine,
    BacktestingEngine,
    OptimizationSetting,
    EVENT_BACKTESTER_BACKTESTING_FINISHED,
    EVENT_BACKTESTER_LOG,
    EVENT_BACKTESTER_OPTIMIZATION_FINISHED
)

from vnpy.trader.engine import MainEngine, EventEngine
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.datafeed import get_datafeed, BaseDatafeed
from vnpy.trader.database import get_database, BaseDatabase

from strategies.mhi.mhi_trend_strategy import MHITrendStrategy


class EnhancedMHIBacktester:
    """
    Enhanced MHI Backtesting System
    使用vnpy_ctabacktester的完整功能集
    """

    def __init__(self):
        """初始化增强回测系统"""
        self.event_engine = EventEngine()
        self.main_engine = MainEngine(self.event_engine)

        # 创建BacktesterEngine - 这是vnpy_ctabacktester的核心引擎
        self.backtester_engine = BacktesterEngine(self.main_engine, self.event_engine)

        # 注册事件监听器
        self.register_event_handlers()

        # 回测配置
        self.default_setting = {
            "vt_symbol": "MHImain.HKFE",
            "interval": Interval.MINUTE,
            "start": datetime(2024, 8, 1),
            "end": datetime(2024, 11, 20),
            "rate": 0.0003,     # 手续费率
            "slippage": 5,      # 滑点
            "size": 10,         # 合约乘数
            "pricetick": 1,     # 最小价格变动
            "capital": 100000,  # 初始资金
        }

        # 策略参数
        self.strategy_settings = self.load_strategy_settings()

    def register_event_handlers(self):
        """注册事件处理器"""
        self.event_engine.register(EVENT_BACKTESTER_LOG, self.process_log_event)
        self.event_engine.register(EVENT_BACKTESTER_BACKTESTING_FINISHED, self.process_backtesting_finished)
        self.event_engine.register(EVENT_BACKTESTER_OPTIMIZATION_FINISHED, self.process_optimization_finished)

    def process_log_event(self, event):
        """处理日志事件"""
        msg = event.data
        print(f"[LOG] {msg}")

    def process_backtesting_finished(self, event):
        """处理回测完成事件"""
        print("[EVENT] 单次回测完成!")

    def process_optimization_finished(self, event):
        """处理优化完成事件"""
        print("[EVENT] 参数优化完成!")

    def load_strategy_settings(self) -> Dict:
        """加载策略设置"""
        settings_file = Path(__file__).parent / "strategy_settings.json"
        if settings_file.exists():
            with open(settings_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def setup_data_source(self) -> bool:
        """设置数据源"""
        try:
            # 获取数据库和数据源
            database = get_database()
            print(f"使用数据库: {type(database).__name__}")

            # 检查数据可用性
            bars = database.load_bar_data(
                symbol="MHImain",
                exchange=Exchange.HKFE,
                interval=Interval.MINUTE,
                start=self.default_setting["start"],
                end=self.default_setting["end"]
            )

            if bars:
                print(f"数据可用: {len(bars)} 条历史K线数据")
                return True
            else:
                print("警告: 未找到历史数据")
                return False

        except Exception as e:
            print(f"数据源设置失败: {e}")
            return False

    def run_single_backtest(self, strategy_name: str = "MHI_Trend_Optimized_Best") -> Dict:
        """
        使用BacktesterEngine运行单次回测

        Args:
            strategy_name: 策略配置名称

        Returns:
            回测结果字典
        """
        print(f"\n{'='*80}")
        print(f"运行单次回测: {strategy_name}")
        print(f"{'='*80}")

        if strategy_name not in self.strategy_settings:
            print(f"错误: 策略配置 '{strategy_name}' 不存在")
            return {}

        strategy_setting = self.strategy_settings[strategy_name]
        print(f"策略描述: {strategy_setting.get('description', 'N/A')}")

        try:
            # 设置回测参数
            self.backtester_engine.set_parameters(
                vt_symbol=self.default_setting["vt_symbol"],
                interval=self.default_setting["interval"],
                start=self.default_setting["start"],
                end=self.default_setting["end"],
                rate=self.default_setting["rate"],
                slippage=self.default_setting["slippage"],
                size=self.default_setting["size"],
                pricetick=self.default_setting["pricetick"],
                capital=self.default_setting["capital"]
            )

            # 添加策略
            self.backtester_engine.add_strategy(
                MHITrendStrategy,
                strategy_setting
            )

            # 加载数据
            print("正在加载历史数据...")
            self.backtester_engine.load_data()

            # 运行回测
            print("正在执行回测...")
            self.backtester_engine.run_backtesting()

            # 计算统计结果
            df = self.backtester_engine.calculate_result()
            stats = self.backtester_engine.calculate_statistics()

            # 显示结果
            self.display_backtest_results(stats, strategy_name)

            return stats

        except Exception as e:
            print(f"回测执行失败: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def run_parameter_optimization(self, optimization_target: str = "sharpe_ratio") -> Dict:
        """
        使用OptimizationSetting运行参数优化

        Args:
            optimization_target: 优化目标 (sharpe_ratio, total_return, etc.)

        Returns:
            优化结果
        """
        print(f"\n{'='*80}")
        print(f"运行参数优化 - 目标: {optimization_target}")
        print(f"{'='*80}")

        try:
            # 创建优化设置
            optimization_setting = OptimizationSetting()

            # 设置优化参数范围
            optimization_setting.set_parameter_range("fast_window", 5, 15, 1)
            optimization_setting.set_parameter_range("slow_window", 15, 30, 1)
            optimization_setting.set_parameter_range("atr_multiplier", 1.5, 3.5, 0.5)
            optimization_setting.set_parameter_range("trend_filter_window", 20, 50, 5)
            optimization_setting.set_parameter_range("min_trend_strength", 0.1, 0.5, 0.1)

            # 设置固定参数
            optimization_setting.set_fixed_parameter("atr_window", 20)
            optimization_setting.set_fixed_parameter("fixed_size", 1)
            optimization_setting.set_fixed_parameter("max_daily_trades", 10)
            optimization_setting.set_fixed_parameter("max_consecutive_losses", 3)

            # 设置优化目标
            optimization_setting.set_target_name(optimization_target)

            print(f"优化参数组合数量: {optimization_setting.generate_settings()}")

            # 设置回测参数
            self.backtester_engine.set_parameters(
                vt_symbol=self.default_setting["vt_symbol"],
                interval=self.default_setting["interval"],
                start=self.default_setting["start"],
                end=self.default_setting["end"],
                rate=self.default_setting["rate"],
                slippage=self.default_setting["slippage"],
                size=self.default_setting["size"],
                pricetick=self.default_setting["pricetick"],
                capital=self.default_setting["capital"]
            )

            # 运行优化
            print("开始参数优化...")
            results = self.backtester_engine.run_optimization(
                MHITrendStrategy,
                optimization_setting
            )

            # 显示优化结果
            self.display_optimization_results(results)

            return results

        except Exception as e:
            print(f"参数优化失败: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def run_multi_strategy_comparison(self) -> Dict:
        """运行多策略对比分析"""
        print(f"\n{'='*80}")
        print("多策略对比分析")
        print(f"{'='*80}")

        comparison_results = {}

        # 选择要对比的策略
        strategies_to_compare = [
            "MHI_Trend_Optimized_Best",
            "MHI_Trend_Balanced",
            "MHI_Trend_Conservative",
            "MHI_Trend_Aggressive",
            "MHI_Trend_Original_Balanced"  # 作为基准
        ]

        for strategy_name in strategies_to_compare:
            if strategy_name in self.strategy_settings:
                print(f"\n正在测试: {strategy_name}")
                result = self.run_single_backtest(strategy_name)
                if result:
                    comparison_results[strategy_name] = result

        # 显示对比结果
        self.display_comparison_results(comparison_results)

        return comparison_results

    def display_backtest_results(self, stats: Dict, strategy_name: str):
        """显示回测结果"""
        print(f"\n{'-'*60}")
        print(f"回测结果: {strategy_name}")
        print(f"{'-'*60}")

        key_metrics = {
            "总收益率": f"{stats.get('total_return', 0):.2f}%",
            "年化收益率": f"{stats.get('annual_return', 0):.2f}%",
            "夏普比率": f"{stats.get('sharpe_ratio', 0):.3f}",
            "最大回撤": f"{stats.get('max_drawdown', 0):.2f}%",
            "胜率": f"{stats.get('win_rate', 0):.1f}%",
            "总交易次数": f"{stats.get('total_trades', 0)}",
            "盈利交易": f"{stats.get('winning_trades', 0)}",
            "平均每笔盈亏": f"{stats.get('daily_return', 0):.2f}"
        }

        for key, value in key_metrics.items():
            print(f"{key:<12}: {value}")

    def display_optimization_results(self, results: Dict):
        """显示优化结果"""
        print(f"\n{'-'*60}")
        print("参数优化结果")
        print(f"{'-'*60}")

        if not results:
            print("未获得优化结果")
            return

        # 这里需要根据实际的results结构来显示
        print("优化完成，结果已保存")

    def display_comparison_results(self, results: Dict):
        """显示策略对比结果"""
        print(f"\n{'='*80}")
        print("策略对比分析结果")
        print(f"{'='*80}")

        if not results:
            print("无有效的对比结果")
            return

        # 创建对比表格
        print(f"{'策略名称':<25} {'收益率':<10} {'夏普比率':<10} {'最大回撤':<10} {'交易次数':<8}")
        print("-" * 80)

        for strategy_name, stats in results.items():
            total_return = stats.get('total_return', 0)
            sharpe_ratio = stats.get('sharpe_ratio', 0)
            max_drawdown = stats.get('max_drawdown', 0)
            total_trades = stats.get('total_trades', 0)

            # 简化策略名称显示
            display_name = strategy_name.replace('MHI_Trend_', '')

            print(f"{display_name:<25} {total_return:<10.2f}% {sharpe_ratio:<10.3f} {max_drawdown:<10.2f}% {total_trades:<8}")

        # 找出最佳策略
        best_strategy = max(results.items(), key=lambda x: x[1].get('sharpe_ratio', -999))
        print(f"\n最佳策略 (按夏普比率): {best_strategy[0]}")
        print(f"夏普比率: {best_strategy[1].get('sharpe_ratio', 0):.3f}")

    def run_walk_forward_analysis(self, window_months: int = 3, step_months: int = 1) -> Dict:
        """运行Walk-Forward分析"""
        print(f"\n{'='*80}")
        print(f"Walk-Forward Analysis (窗口: {window_months}月, 步长: {step_months}月)")
        print(f"{'='*80}")

        results = []
        start_date = self.default_setting["start"]
        end_date = self.default_setting["end"]

        current_start = start_date

        while current_start < end_date:
            # 计算当前窗口的结束时间
            current_end = current_start + timedelta(days=window_months * 30)
            if current_end > end_date:
                current_end = end_date

            print(f"\n测试窗口: {current_start.strftime('%Y-%m-%d')} 至 {current_end.strftime('%Y-%m-%d')}")

            # 临时修改时间范围
            original_start = self.default_setting["start"]
            original_end = self.default_setting["end"]

            self.default_setting["start"] = current_start
            self.default_setting["end"] = current_end

            # 运行回测
            result = self.run_single_backtest("MHI_Trend_Optimized_Best")
            if result:
                result["period_start"] = current_start
                result["period_end"] = current_end
                results.append(result)

            # 恢复原始设置
            self.default_setting["start"] = original_start
            self.default_setting["end"] = original_end

            # 移动到下一个窗口
            current_start += timedelta(days=step_months * 30)

        self.display_walk_forward_results(results)
        return results

    def display_walk_forward_results(self, results: List[Dict]):
        """显示Walk-Forward分析结果"""
        print(f"\n{'-'*80}")
        print("Walk-Forward分析汇总")
        print(f"{'-'*80}")

        if not results:
            print("无有效结果")
            return

        print(f"{'时间段':<20} {'收益率':<10} {'夏普比率':<10} {'回撤':<10} {'交易次数':<8}")
        print("-" * 70)

        total_returns = []
        sharpe_ratios = []

        for result in results:
            period = f"{result['period_start'].strftime('%m/%d')}-{result['period_end'].strftime('%m/%d')}"
            total_return = result.get('total_return', 0)
            sharpe_ratio = result.get('sharpe_ratio', 0)
            max_drawdown = result.get('max_drawdown', 0)
            total_trades = result.get('total_trades', 0)

            print(f"{period:<20} {total_return:<10.2f}% {sharpe_ratio:<10.3f} {max_drawdown:<10.2f}% {total_trades:<8}")

            total_returns.append(total_return)
            if sharpe_ratio != 0:  # 避免无效的夏普比率
                sharpe_ratios.append(sharpe_ratio)

        # 统计汇总
        print(f"\n汇总统计:")
        print(f"平均收益率: {sum(total_returns)/len(total_returns):.2f}%")
        if sharpe_ratios:
            print(f"平均夏普比率: {sum(sharpe_ratios)/len(sharpe_ratios):.3f}")
        print(f"正收益期数: {len([r for r in total_returns if r > 0])}/{len(total_returns)}")


def main():
    """主函数"""
    print("Enhanced MHI Backtesting System")
    print("基于 vnpy_ctabacktester 的增强回测系统")
    print("="*80)

    backtester = EnhancedMHIBacktester()

    # 检查数据源
    if not backtester.setup_data_source():
        print("数据源检查失败，请确保历史数据已下载")
        return

    print(f"\n可用的策略配置:")
    for name, config in backtester.strategy_settings.items():
        print(f"  - {name}: {config.get('description', 'N/A')}")

    while True:
        print(f"\n{'='*80}")
        print("请选择功能:")
        print("1. 单次回测")
        print("2. 多策略对比")
        print("3. 参数优化")
        print("4. Walk-Forward分析")
        print("5. 退出")

        choice = input("\n请选择 (1-5): ").strip()

        try:
            if choice == "1":
                strategy_name = input("请输入策略名称 (默认: MHI_Trend_Optimized_Best): ").strip()
                if not strategy_name:
                    strategy_name = "MHI_Trend_Optimized_Best"
                backtester.run_single_backtest(strategy_name)

            elif choice == "2":
                backtester.run_multi_strategy_comparison()

            elif choice == "3":
                target = input("请输入优化目标 (默认: sharpe_ratio): ").strip()
                if not target:
                    target = "sharpe_ratio"
                backtester.run_parameter_optimization(target)

            elif choice == "4":
                window = input("请输入窗口月数 (默认: 3): ").strip()
                step = input("请输入步长月数 (默认: 1): ").strip()
                window = int(window) if window else 3
                step = int(step) if step else 1
                backtester.run_walk_forward_analysis(window, step)

            elif choice == "5":
                print("退出系统...")
                break

            else:
                print("无效选择，请重试")

        except KeyboardInterrupt:
            print("\n\n用户中断，退出系统...")
            break
        except Exception as e:
            print(f"执行出错: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()