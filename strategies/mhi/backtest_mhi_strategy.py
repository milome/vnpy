#!/usr/bin/env python3
"""
MHI期货策略回测系统
使用VNPy的CTA回测引擎验证策略历史表现

主要功能：
1. 加载历史数据
2. 运行策略回测
3. 计算收益指标
4. 生成报告图表

使用方法：
python backtest_mhi_strategy.py
"""

import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from vnpy_ctabacktester.engine import BacktestingEngine
from vnpy.trader.constant import Exchange, Interval
from strategies.mhi.mhi_trend_strategy import MHITrendStrategy


class MHIBacktester:
    """MHI策略回测器"""

    def __init__(self):
        """初始化回测引擎"""
        self.engine = BacktestingEngine()
        self.strategy_settings = self.load_strategy_settings()

    def load_strategy_settings(self):
        """加载策略配置"""
        settings_file = Path(__file__).parent / "strategy_settings.json"
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载策略配置失败: {e}")
            return {}

    def setup_backtest_engine(self, capital=100000):
        """配置回测引擎"""
        print("配置回测引擎...")

        # 设置回测参数
        self.engine.set_parameters(
            vt_symbol="MHImain.HKFE",
            interval=Interval.MINUTE,
            start=datetime(2024, 8, 1),      # 回测开始日期
            end=datetime(2024, 11, 20),     # 回测结束日期
            rate=0.0003,                    # 手续费率 (每边0.03%)
            slippage=5,                     # 滑点 (5港币)
            size=10,                        # 合约乘数 (小恒指为10)
            pricetick=1,                    # 最小价格变动 (1港币)
            capital=capital,                # 初始资金
        )

        print(f"回测配置:")
        print(f"  合约: MHImain.HKFE")
        print(f"  周期: 1分钟")
        print(f"  时间: 2024-08-01 到 2024-11-20")
        print(f"  初始资金: {capital:,} 港币")
        print(f"  手续费: 0.03% (每边)")
        print(f"  滑点: 5 港币")

    def run_single_backtest(self, strategy_name="MHI_Trend_Balanced"):
        """运行单次回测"""
        print(f"\n{'='*60}")
        print(f"运行回测: {strategy_name}")
        print(f"{'='*60}")

        # 获取策略配置
        if strategy_name not in self.strategy_settings:
            print(f"错误: 找不到策略配置 {strategy_name}")
            return None

        setting = self.strategy_settings[strategy_name].copy()
        description = setting.pop('description', '')

        print(f"策略描述: {description}")
        print(f"策略参数: {setting}")

        # 添加策略
        self.engine.add_strategy(MHITrendStrategy, setting)

        try:
            # 加载历史数据
            print("\n正在加载历史数据...")
            self.engine.load_data()
            print("历史数据加载完成")

            # 运行回测
            print("\n正在运行回测...")
            self.engine.run_backtesting()
            print("回测运行完成")

            # 计算结果
            print("\n正在计算回测指标...")
            df = self.engine.calculate_result()
            stats = self.engine.calculate_statistics()

            return {
                'strategy_name': strategy_name,
                'description': description,
                'setting': setting,
                'trades_df': df,
                'statistics': stats
            }

        except Exception as e:
            print(f"回测失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def show_backtest_results(self, result):
        """显示回测结果"""
        if not result:
            return

        print(f"\n{'='*60}")
        print(f"回测结果: {result['strategy_name']}")
        print(f"{'='*60}")

        stats = result['statistics']

        # 基本统计
        print(f"\n基本统计:")
        print(f"  总交易次数: {stats.get('total_trades', 0)}")
        print(f"  盈利交易: {stats.get('winning_trades', 0)}")
        print(f"  亏损交易: {stats.get('losing_trades', 0)}")
        print(f"  胜率: {stats.get('win_rate', 0):.2f}%")

        # 收益统计
        print(f"\n收益统计:")
        print(f"  总收益: {stats.get('total_pnl', 0):,.0f} 港币")
        print(f"  总收益率: {stats.get('total_return', 0):.2f}%")
        print(f"  年化收益率: {stats.get('annual_return', 0):.2f}%")
        print(f"  最大回撤: {stats.get('max_drawdown', 0):.2f}%")

        # 风险指标
        print(f"\n风险指标:")
        print(f"  夏普比率: {stats.get('sharpe_ratio', 0):.3f}")
        print(f"  收益回撤比: {stats.get('return_drawdown_ratio', 0):.3f}")
        print(f"  日均收益: {stats.get('daily_return', 0):.2f}%")
        print(f"  收益波动率: {stats.get('return_std', 0):.2f}%")

        # 交易统计
        if stats.get('total_trades', 0) > 0:
            print(f"\n交易统计:")
            print(f"  平均每笔盈亏: {stats.get('average_pnl', 0):,.0f} 港币")
            print(f"  最大单笔盈利: {stats.get('max_winning_pnl', 0):,.0f} 港币")
            print(f"  最大单笔亏损: {stats.get('max_losing_pnl', 0):,.0f} 港币")
            print(f"  盈亏比: {stats.get('pnl_ratio', 0):.3f}")

    def run_comparison_backtest(self):
        """运行多策略对比回测"""
        print(f"\n{'='*80}")
        print("MHI策略对比回测")
        print(f"{'='*80}")

        results = {}

        # 测试所有预设策略
        for strategy_name in self.strategy_settings.keys():
            print(f"\n正在测试策略: {strategy_name}")

            # 重新初始化回测引擎
            self.engine = BacktestingEngine()
            self.setup_backtest_engine()

            result = self.run_single_backtest(strategy_name)
            if result:
                results[strategy_name] = result
                self.show_backtest_results(result)
            else:
                print(f"策略 {strategy_name} 回测失败")

        return results

    def generate_comparison_report(self, results):
        """生成对比报告"""
        if not results:
            print("没有可用的回测结果")
            return

        print(f"\n{'='*80}")
        print("策略对比报告")
        print(f"{'='*80}")

        # 创建对比表格
        print(f"\n{'策略名称':<20} {'年化收益':<10} {'最大回撤':<10} {'夏普比率':<10} {'胜率':<8} {'交易次数':<8}")
        print("-" * 80)

        for name, result in results.items():
            stats = result['statistics']
            annual_return = stats.get('annual_return', 0)
            max_drawdown = stats.get('max_drawdown', 0)
            sharpe_ratio = stats.get('sharpe_ratio', 0)
            win_rate = stats.get('win_rate', 0)
            total_trades = stats.get('total_trades', 0)

            print(f"{name:<20} {annual_return:>9.2f}% {max_drawdown:>9.2f}% {sharpe_ratio:>9.3f} {win_rate:>7.2f}% {total_trades:>8}")

        # 找出最佳策略
        best_sharpe = max(results.items(), key=lambda x: x[1]['statistics'].get('sharpe_ratio', 0))
        best_return = max(results.items(), key=lambda x: x[1]['statistics'].get('annual_return', 0))
        min_drawdown = min(results.items(), key=lambda x: x[1]['statistics'].get('max_drawdown', 100))

        print(f"\n最佳策略推荐:")
        print(f"  最高夏普比率: {best_sharpe[0]} (夏普比率: {best_sharpe[1]['statistics'].get('sharpe_ratio', 0):.3f})")
        print(f"  最高年化收益: {best_return[0]} (年化收益: {best_return[1]['statistics'].get('annual_return', 0):.2f}%)")
        print(f"  最小回撤: {min_drawdown[0]} (最大回撤: {min_drawdown[1]['statistics'].get('max_drawdown', 0):.2f}%)")

    def show_charts(self, strategy_name="MHI_Trend_Balanced"):
        """显示策略回测图表"""
        print(f"\n正在生成 {strategy_name} 回测图表...")

        # 重新运行回测以显示图表
        self.engine = BacktestingEngine()
        self.setup_backtest_engine()

        if strategy_name in self.strategy_settings:
            setting = self.strategy_settings[strategy_name].copy()
            setting.pop('description', '')
            self.engine.add_strategy(MHITrendStrategy, setting)

            try:
                self.engine.load_data()
                self.engine.run_backtesting()
                self.engine.calculate_result()
                self.engine.show_chart()
                print("图表已生成并显示")
            except Exception as e:
                print(f"图表生成失败: {e}")


def main():
    """主函数"""
    print("MHI期货策略回测系统")
    print("="*60)

    # 创建回测器
    backtester = MHIBacktester()
    backtester.setup_backtest_engine()

    # 运行对比回测
    results = backtester.run_comparison_backtest()

    # 生成对比报告
    backtester.generate_comparison_report(results)

    # 询问是否显示图表
    if results:
        print(f"\n是否显示最佳策略的回测图表？")
        best_strategy = max(results.items(), key=lambda x: x[1]['statistics'].get('sharpe_ratio', 0))
        choice = input(f"按 Enter 显示 {best_strategy[0]} 的图表，或输入其他策略名称，或 'n' 跳过: ").strip()

        if choice.lower() != 'n':
            strategy_to_show = choice if choice and choice in results else best_strategy[0]
            backtester.show_charts(strategy_to_show)

    print(f"\n回测完成!")
    print(f"建议下一步:")
    print(f"1. 分析最佳策略的详细交易记录")
    print(f"2. 进行参数优化以进一步提升表现")
    print(f"3. 在更长的历史数据上验证策略稳定性")
    print(f"4. 准备模拟交易测试")


if __name__ == "__main__":
    main()