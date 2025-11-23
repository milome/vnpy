#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 test_period_based.py 策略的 CTA 回测
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import datetime
from vnpy_ctastrategy.backtesting import BacktestingEngine
from strategies.test_period_based import TestPeriodBased


def test_backtest_period_based():
    """测试 test_period_based.py 策略的回测"""
    print("=" * 60)
    print("测试 test_period_based.py 策略的 CTA 回测")
    print("=" * 60)
    
    # 创建回测引擎
    engine = BacktestingEngine()
    
    # 设置回测参数
    # 使用小恒指期货主连 MHImain，交易所 HKFE
    engine.set_parameters(
        vt_symbol="MHImain.HKFE",
        interval="1m",  # 1分钟K线
        start=datetime(2024, 1, 1),
        end=datetime(2024, 1, 31),
        rate=0.3/10000,  # 手续费率
        slippage=1.0,    # 滑点
        size=1,          # 合约大小
        pricetick=1.0,   # 价格跳动
        capital=1_000_000,  # 初始资金
    )
    
    # 添加策略
    print("\n添加策略: TestPeriodBased")
    engine.add_strategy(TestPeriodBased, {})
    
    # 加载历史数据
    print("\n正在加载历史数据...")
    try:
        engine.load_data()
        print("历史数据加载成功")
    except Exception as e:
        print(f"历史数据加载失败: {e}")
        print("提示: 需要先下载 MHImain.HKFE 的1分钟K线数据")
        return
    
    # 运行回测
    print("\n正在运行回测...")
    try:
        engine.run_backtesting()
        print("回测运行完成")
    except Exception as e:
        print(f"回测运行失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 计算结果
    print("\n正在计算结果...")
    try:
        df = engine.calculate_result()
        if df is None or df.empty:
            print("警告: 未生成回测结果，可能是没有成交记录")
            print("策略可能没有触发交易信号")
        else:
            print(f"回测结果数据行数: {len(df)}")
            print("\n回测结果预览:")
            print(df.head(10))
    except Exception as e:
        print(f"计算结果失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 计算统计指标
    print("\n正在计算统计指标...")
    try:
        engine.calculate_statistics()
        print("统计指标计算完成")
    except Exception as e:
        print(f"统计指标计算失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("回测测试完成")
    print("=" * 60)


if __name__ == "__main__":
    test_backtest_period_based()
