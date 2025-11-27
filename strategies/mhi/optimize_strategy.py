#!/usr/bin/env python3
"""
MHI策略参数优化工具
使用网格搜索优化策略参数，以提高策略表现

使用方法：
python optimize_strategy.py

功能：
1. 多参数网格搜索优化
2. 并行回测加速
3. 综合评分排序
4. 最优参数推荐
"""

import sys
import itertools
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any
import pandas as pd
import numpy as np

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from vnpy_ctabacktester.engine import BacktestingEngine
from vnpy.trader.constant import Exchange, Interval
from strategies.mhi.mhi_trend_strategy import MHITrendStrategy


class StrategyOptimizer:
    """策略参数优化器"""

    def __init__(self):
        self.engine = None
        self.results = []

    def setup_backtest_engine(self):
        """设置回测引擎"""
        self.engine = BacktestingEngine()

        # 回测参数
        self.engine.set_parameters(
            vt_symbol="MHImain.HKFE",
            interval=Interval.MINUTE,
            start=datetime(2024, 8, 1),
            end=datetime(2024, 11, 20),
            rate=0.0003,    # 手续费率
            slippage=5,     # 滑点
            size=10,        # 合约乘数
            pricetick=1,    # 最小价格变动
            capital=100000, # 初始资金
        )

    def get_optimization_parameters(self) -> Dict[str, List]:
        """定义优化参数范围"""
        return {
            "fast_window": [5, 8, 10, 12, 15],              # 快线周期
            "slow_window": [15, 20, 26, 30, 35],            # 慢线周期
            "atr_multiplier": [1.5, 2.0, 2.5, 3.0],        # ATR倍数
            "trend_filter_window": [20, 30, 40, 50, 60],    # 趋势过滤周期
            "min_trend_strength": [0.1, 0.2, 0.3, 0.5],    # 最小趋势强度
        }

    def generate_parameter_combinations(self) -> List[Dict]:
        """生成参数组合"""
        param_ranges = self.get_optimization_parameters()

        # 参数约束：确保快线 < 慢线
        combinations = []
        for values in itertools.product(*param_ranges.values()):
            param_dict = dict(zip(param_ranges.keys(), values))

            # 约束条件
            if param_dict["fast_window"] < param_dict["slow_window"]:
                # 添加固定参数
                param_dict.update({
                    "atr_window": 20,
                    "fixed_size": 1,
                    "max_daily_trades": 20,
                    "max_consecutive_losses": 5
                })
                combinations.append(param_dict)

        return combinations

    def run_single_backtest(self, parameters: Dict) -> Dict:
        """运行单次回测"""
        try:
            # 清理之前的策略
            self.engine.clear_data()

            # 添加策略
            self.engine.add_strategy(MHITrendStrategy, parameters)

            # 加载数据
            self.engine.load_data()

            # 运行回测
            self.engine.run_backtesting()

            # 计算统计
            df = self.engine.calculate_result()
            stats = self.engine.calculate_statistics()

            return {
                "parameters": parameters.copy(),
                "total_return": stats.get("total_return", 0),
                "max_drawdown": stats.get("max_drawdown", 0),
                "sharpe_ratio": stats.get("sharpe_ratio", 0),
                "total_trades": stats.get("total_trades", 0),
                "win_rate": stats.get("win_rate", 0),
                "profit_trades": stats.get("winning_trades", 0),
                "avg_return": stats.get("daily_return", 0),
                "annual_return": stats.get("annual_return", 0),
                "max_ddpercent": stats.get("max_ddpercent", 0),
                "return_vol": stats.get("return_std", 0),
                "success": True
            }

        except Exception as e:
            return {
                "parameters": parameters.copy(),
                "error": str(e),
                "success": False
            }

    def calculate_composite_score(self, result: Dict) -> float:
        """计算综合评分"""
        if not result["success"]:
            return -1000

        # 如果没有交易，返回低分
        if result["total_trades"] == 0:
            return -100

        # 综合评分公式 (可调整权重)
        total_return = result["total_return"]
        max_drawdown = result["max_drawdown"]
        sharpe_ratio = result["sharpe_ratio"]
        win_rate = result["win_rate"]
        total_trades = result["total_trades"]

        # 基础分数
        score = 0.0

        # 收益率权重 (40%)
        score += total_return * 0.4

        # 回撤控制权重 (30%) - 回撤越小越好
        if abs(max_drawdown) > 0:
            score -= abs(max_drawdown) * 0.3

        # 夏普比率权重 (20%)
        score += sharpe_ratio * 20 * 0.2  # 放大夏普比率

        # 胜率权重 (10%)
        score += win_rate * 0.1

        # 交易次数奖励 - 有交易信号才有意义
        if total_trades > 0:
            score += min(total_trades / 50, 1) * 10  # 最多加10分

        return score

    def run_optimization(self) -> pd.DataFrame:
        """运行参数优化"""
        print("开始MHI策略参数优化...")

        # 设置回测引擎
        self.setup_backtest_engine()

        # 生成参数组合
        parameter_combinations = self.generate_parameter_combinations()
        print(f"生成 {len(parameter_combinations)} 个参数组合")

        # 运行回测
        self.results = []
        for i, params in enumerate(parameter_combinations):
            print(f"\r进度: {i+1}/{len(parameter_combinations)} ({(i+1)/len(parameter_combinations)*100:.1f}%)", end="")

            result = self.run_single_backtest(params)
            result["combo_id"] = i + 1
            result["score"] = self.calculate_composite_score(result)
            self.results.append(result)

        print("\n优化完成!")

        # 转换为DataFrame
        results_df = pd.DataFrame(self.results)

        # 排序
        results_df = results_df.sort_values("score", ascending=False)

        return results_df

    def display_top_results(self, results_df: pd.DataFrame, top_n: int = 10):
        """显示最优结果"""
        print(f"\n{'='*80}")
        print(f"TOP {top_n} 最优参数组合")
        print(f"{'='*80}")

        # 筛选有交易的结果
        trading_results = results_df[results_df["total_trades"] > 0]

        if len(trading_results) == 0:
            print(">> 所有参数组合都没有产生交易信号!")
            print("\n建议:")
            print("1. 降低 min_trend_strength 参数 (当前最小: 0.1)")
            print("2. 缩短趋势过滤周期 trend_filter_window")
            print("3. 调整快慢均线周期组合")
            print("4. 检查数据时间段是否有明显趋势")

            # 显示评分最高的几个（即使没有交易）
            print(f"\n评分最高的 {min(5, len(results_df))} 个参数组合:")
            top_no_trades = results_df.head(5)
            self._print_result_table(top_no_trades)
            return

        print(f"找到 {len(trading_results)} 个产生交易信号的参数组合")

        # 显示Top结果
        top_results = trading_results.head(top_n)
        self._print_result_table(top_results)

        # 显示最优参数
        if len(top_results) > 0:
            best_result = top_results.iloc[0]
            print(f"\n{'='*80}")
            print(">> 最优参数组合详情")
            print(f"{'='*80}")
            print(f"综合评分: {best_result['score']:.2f}")
            print(f"总收益率: {best_result['total_return']:.2f}%")
            print(f"最大回撤: {best_result['max_drawdown']:.2f}%")
            print(f"夏普比率: {best_result['sharpe_ratio']:.3f}")
            print(f"胜率: {best_result['win_rate']:.1f}%")
            print(f"总交易次数: {best_result['total_trades']}")

            print("\n最优参数:")
            params = best_result['parameters']
            for key, value in params.items():
                print(f"  {key}: {value}")

    def _print_result_table(self, results_df: pd.DataFrame):
        """打印结果表格"""
        print(f"\n{'排名':<4} {'评分':<8} {'总收益':<8} {'最大回撤':<10} {'夏普比率':<10} {'胜率':<8} {'交易次数':<8} {'参数组合'}")
        print("-" * 120)

        for idx, (_, row) in enumerate(results_df.iterrows(), 1):
            params = row['parameters']
            param_str = f"F{params['fast_window']}/S{params['slow_window']}/ATR{params['atr_multiplier']}/TF{params['trend_filter_window']}/TS{params['min_trend_strength']}"

            print(f"{idx:<4} {row['score']:<8.1f} {row['total_return']:<8.2f}% {row['max_drawdown']:<10.2f}% {row['sharpe_ratio']:<10.3f} {row['win_rate']:<8.1f}% {row['total_trades']:<8} {param_str}")

    def save_results(self, results_df: pd.DataFrame, filename: str = None):
        """保存结果到CSV"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"optimization_results_{timestamp}.csv"

        filepath = Path(__file__).parent / filename
        results_df.to_csv(filepath, index=False, encoding='utf-8-sig')
        print(f"\n结果已保存到: {filepath}")


def main():
    """主函数"""
    optimizer = StrategyOptimizer()

    try:
        # 运行优化
        results = optimizer.run_optimization()

        # 显示结果
        optimizer.display_top_results(results, top_n=15)

        # 保存结果
        optimizer.save_results(results)

    except Exception as e:
        print(f"优化过程出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()