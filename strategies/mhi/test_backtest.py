#!/usr/bin/env python3
"""
简化的MHI回测测试脚本
测试回测环境和策略基本功能

使用方法：
python test_backtest.py
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from vnpy_ctabacktester.engine import BacktestingEngine
from vnpy.trader.constant import Exchange, Interval
from strategies.mhi.mhi_trend_strategy import MHITrendStrategy


def test_simple_backtest():
    """测试简单回测功能"""
    print("=" * 60)
    print("MHI策略简单回测测试")
    print("=" * 60)

    # 创建回测引擎
    engine = BacktestingEngine()
    print(">> 回测引擎创建成功")

    # 设置回测参数（较短的时间周期用于快速测试）
    start_date = datetime(2024, 11, 15)  # 测试最近一周
    end_date = datetime(2024, 11, 20)

    print(f"\n配置回测参数:")
    print(f"  合约: MHImain.HKFE")
    print(f"  周期: 1分钟")
    print(f"  时间: {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}")
    print(f"  初始资金: 100,000 港币")

    try:
        engine.set_parameters(
            vt_symbol="MHImain.HKFE",
            interval=Interval.MINUTE,
            start=start_date,
            end=end_date,
            rate=0.0003,    # 手续费率
            slippage=5,     # 滑点
            size=10,        # 合约乘数
            pricetick=1,    # 最小价格变动
            capital=100000, # 初始资金
        )
        print(">> 回测参数设置成功")

        # 添加策略（使用平衡型配置）
        strategy_setting = {
            "fast_window": 12,
            "slow_window": 26,
            "atr_window": 20,
            "atr_multiplier": 2.5,
            "fixed_size": 1,
            "trend_filter_window": 50,
            "min_trend_strength": 0.5,
            "max_daily_trades": 10,
            "max_consecutive_losses": 3
        }

        engine.add_strategy(MHITrendStrategy, strategy_setting)
        print(">> 策略添加成功")

        # 尝试加载数据
        print(f"\n正在加载历史数据...")
        try:
            engine.load_data()
            print(">> 历史数据加载成功")

            # 运行回测
            print(f"\n正在运行回测...")
            engine.run_backtesting()
            print(">> 回测执行完成")

            # 计算结果
            print(f"\n正在计算回测结果...")
            df = engine.calculate_result()
            stats = engine.calculate_statistics()

            # 显示基本结果
            print(f"\n回测结果总结:")
            print(f"  总交易次数: {stats.get('total_trades', 0)}")
            print(f"  盈利交易: {stats.get('winning_trades', 0)}")
            print(f"  胜率: {stats.get('win_rate', 0):.2f}%")
            print(f"  总收益: {stats.get('total_pnl', 0):,.0f} 港币")
            print(f"  收益率: {stats.get('total_return', 0):.2f}%")
            print(f"  最大回撤: {stats.get('max_drawdown', 0):.2f}%")
            print(f"  夏普比率: {stats.get('sharpe_ratio', 0):.3f}")

            if stats.get('total_trades', 0) > 0:
                print(f"\n>> 回测测试成功!")
                print(f"策略在测试期间产生了交易信号，回测系统工作正常。")
            else:
                print(f"\n>> 回测测试完成，但无交易信号")
                print(f"这可能是由于:")
                print(f"1. 测试时间太短")
                print(f"2. 策略参数过于严格")
                print(f"3. 市场数据不足以产生信号")

            return True

        except Exception as data_error:
            print(f">> 数据加载或回测执行失败: {data_error}")
            print(f"\n可能的原因:")
            print(f"1. MHImain.HKFE 合约数据不可用")
            print(f"2. 数据库中没有相应的历史数据")
            print(f"3. 需要先下载历史数据")
            print(f"\n建议:")
            print(f"1. 运行 VNPy DataManager 下载 MHI 历史数据")
            print(f"2. 确保数据覆盖测试时间段")
            return False

    except Exception as e:
        print(f">> 回测配置失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_strategy_components():
    """测试策略组件"""
    print(f"\n" + "-" * 60)
    print("策略组件测试")
    print("-" * 60)

    try:
        # 创建策略实例
        strategy = MHITrendStrategy(
            cta_engine=None,
            strategy_name="Test_Strategy",
            vt_symbol="MHImain.HKFE",
            setting={
                "fast_window": 12,
                "slow_window": 26,
                "atr_window": 20,
                "atr_multiplier": 2.5,
                "fixed_size": 1
            }
        )

        print(">> 策略实例创建成功")

        # 测试策略方法
        strategy.atr_value = 100.0
        strategy.daily_trade_count = 0
        strategy.consecutive_losses = 0

        risk_ok = strategy.risk_check()
        print(f">> 风控检查: {'通过' if risk_ok else '未通过'}")

        stats = strategy.get_strategy_stats()
        print(f">> 策略统计: {len(stats)} 个指标")

        print(f">> 策略组件测试通过")
        return True

    except Exception as e:
        print(f">> 策略组件测试失败: {e}")
        return False


def check_data_availability():
    """检查数据可用性"""
    print(f"\n" + "-" * 60)
    print("数据可用性检查")
    print("-" * 60)

    try:
        # 尝试查询数据库中的MHI数据
        from vnpy.trader.database import get_database

        database = get_database()
        print(f">> 数据库引擎: {type(database).__name__}")

        # 查询最近的数据
        bars = database.load_bar_data(
            symbol="MHImain",
            exchange=Exchange.HKFE,
            interval=Interval.MINUTE,
            start=datetime(2024, 11, 1),
            end=datetime(2024, 11, 21)
        )

        if bars:
            print(f">> 找到 {len(bars)} 条MHI历史数据")
            print(f"   最早: {bars[0].datetime}")
            print(f"   最新: {bars[-1].datetime}")
            return True
        else:
            print(f">> 未找到MHI历史数据")
            print(f"需要先下载历史数据才能运行回测")
            return False

    except Exception as e:
        print(f">> 数据检查失败: {e}")
        return False


def main():
    """主函数"""
    print("MHI策略回测环境测试")

    # 测试1: 策略组件
    strategy_ok = test_strategy_components()

    # 测试2: 数据可用性
    data_ok = check_data_availability()

    # 测试3: 简单回测
    if strategy_ok and data_ok:
        backtest_ok = test_simple_backtest()
    else:
        print(f"\n跳过回测测试，因为依赖条件不满足")
        backtest_ok = False

    # 总结
    print(f"\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"  策略组件: {'通过' if strategy_ok else '失败'}")
    print(f"  数据可用性: {'通过' if data_ok else '失败'}")
    print(f"  回测功能: {'通过' if backtest_ok else '失败'}")

    if all([strategy_ok, data_ok, backtest_ok]):
        print(f"\n所有测试通过！可以运行完整回测。")
        print(f"建议下一步:")
        print(f"1. 运行 python backtest_mhi_strategy.py")
        print(f"2. 分析回测结果并优化策略参数")
    else:
        print(f"\n部分测试未通过")
        if not data_ok:
            print(f"建议: 先使用 VNPy DataManager 下载MHI历史数据")
        if not strategy_ok:
            print(f"建议: 检查策略代码和依赖")


if __name__ == "__main__":
    main()