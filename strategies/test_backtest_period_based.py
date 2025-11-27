#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 test_period_based.py 策略的回测脚本
使用 vnpy_ctastrategy 的回测引擎
"""

from datetime import datetime
from vnpy_ctastrategy.backtesting import BacktestingEngine
from strategies.test_period_based import TestPeriodBased


def main():
    """主函数"""
    print("=" * 60)
    print("测试 TestPeriodBased 策略回测")
    print("=" * 60)
    
    # 创建回测引擎
    engine = BacktestingEngine()
    
    # 设置回测参数
    # 注意：策略使用 MHImain.HKFE，需要确保数据库中有对应的历史数据
    engine.set_parameters(
        vt_symbol="MHImain.HKFE",  # 小恒指期货主连
        interval="1m",              # 1分钟K线
        start=datetime(2024, 1, 1), # 回测开始日期
        end=datetime(2024, 1, 31),  # 回测结束日期（先用一个月测试）
        rate=0.0003,                # 手续费率 (每边0.03%)
        slippage=5,                 # 滑点 (5港币)
        size=10,                    # 合约乘数 (小恒指为10)
        pricetick=1,                # 最小价格变动 (1港币)
        capital=1_000_000,          # 初始资金 (100万港币)
    )
    
    print("\n回测参数设置:")
    print(f"  合约: MHImain.HKFE")
    print(f"  周期: 1分钟")
    print(f"  时间: 2024-01-01 到 2024-01-31")
    print(f"  初始资金: 1,000,000 港币")
    print(f"  手续费: 0.03% (每边)")
    print(f"  滑点: 5 港币")
    
    # 添加策略
    print("\n添加策略: TestPeriodBased")
    engine.add_strategy(TestPeriodBased, {})
    
    try:
        # 加载历史数据
        print("\n正在加载历史数据...")
        engine.load_data()
        print("历史数据加载完成")
        
        # 运行回测
        print("\n正在运行回测...")
        engine.run_backtesting()
        print("回测运行完成")
        
        # 计算结果
        print("\n正在计算结果...")
        df = engine.calculate_result()
        
        if df is None or df.empty:
            print("\n警告: 未生成回测结果，可能是:")
            print("  1. 数据库中没有对应的历史数据")
            print("  2. 策略没有产生任何交易信号")
            print("  3. 数据时间范围不匹配")
            return
        
        # 计算统计指标
        print("\n正在计算统计指标...")
        statistics = engine.calculate_statistics(df, output=True)
        
        # 显示图表（可选）
        print("\n是否显示回测图表? (需要安装 plotly)")
        # engine.show_chart(df)
        
        print("\n" + "=" * 60)
        print("回测完成！")
        print("=" * 60)
        
        return df, statistics
        
    except Exception as e:
        print(f"\n回测过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return None, None


if __name__ == "__main__":
    main()
