#!/usr/bin/env python3
"""
MHI策略启动脚本
在VNPy CTA策略引擎中加载MHI趋势跟踪策略

使用方法：
1. 在VNPy主界面中启动CTA策略应用
2. 运行此脚本查看策略信息和使用指南

注意：此脚本主要用于查看策略信息，实际策略加载需要在VNPy中手动添加
"""

import sys
import json
from pathlib import Path


def load_strategy_settings():
    """加载策略配置"""
    settings_file = Path(__file__).parent / "strategy_settings.json"

    try:
        with open(settings_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载策略配置失败: {e}")
        return {}


def show_strategy_info():
    """显示策略信息"""
    print("\n" + "=" * 60)
    print("MHI趋势跟踪策略信息")
    print("=" * 60)

    print("\n策略特点:")
    print("- 基于双移动平均线交叉的趋势跟踪策略")
    print("- 使用ATR动态止损，风险控制严格")
    print("- 增加趋势过滤，避免震荡市场交易")
    print("- 支持多种参数配置（保守、平衡、激进、剥头皮）")
    print("- 实时统计胜率和风险指标")

    print("\n适用场景:")
    print("- 适合MHI期货(小恒指)的中长期趋势交易")
    print("- 5分钟K线级别，捕捉日内趋势")
    print("- 自动风控，限制每日交易次数和连续亏损")

    print("\n策略配置:")
    settings = load_strategy_settings()

    for name, config in settings.items():
        print(f"\n【{name}】- {config['description']}")
        print(f"  快线: {config['fast_window']}, 慢线: {config['slow_window']}, ATR倍数: {config['atr_multiplier']}")
        print(f"  每日最大交易: {config['max_daily_trades']}, 最大连续亏损: {config['max_consecutive_losses']}")

    print("\n" + "=" * 60)


def show_usage_guide():
    """显示使用指南"""
    print("\n使用指南:")
    print("=" * 60)

    print("\n方法1: VNPy界面手动添加")
    print("1. 启动VNPy主程序: examples/veighna_trader/run.py")
    print("2. 连接富途网关")
    print("3. 启动CTA策略应用")
    print("4. 在策略管理界面添加策略:")
    print("   - 策略类名: MHITrendStrategy")
    print("   - 策略实例名: MHI_Trend_Main (或自定义)")
    print("   - vt_symbol: MHImain.HKFE")
    print("   - 参数: 选择合适的配置组合")

    print("\n方法2: 导入策略模块")
    print("在VNPy中执行:")
    print("```python")
    print("from strategies.mhi.mhi_trend_strategy import MHITrendStrategy")
    print("```")

    print("\n注意事项:")
    print("- 确保富途网关已连接且MHImain合约可用")
    print("- 建议先在模拟环境中测试策略")
    print("- 根据市场情况选择合适的参数配置")
    print("- 定期监控策略表现和风险指标")

    print("\n风险提示:")
    print("- 期货交易有风险，投资需谨慎")
    print("- 策略仅供参考，不构成投资建议")
    print("- 实盘使用前请充分测试和优化")


def main():
    """主函数"""
    print("MHI趋势跟踪策略 - 启动脚本")

    # 显示策略信息
    show_strategy_info()

    # 显示使用指南
    show_usage_guide()

    print(f"\n策略开发完成!")
    print(f"文件位置: strategies/mhi/")
    print(f"配置文件: strategies/mhi/strategy_settings.json")


if __name__ == "__main__":
    main()