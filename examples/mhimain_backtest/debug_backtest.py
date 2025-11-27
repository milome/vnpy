"""
MHImain CTA回测调试脚本
用于分析回测中的爆仓原因
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime
import pandas as pd

# 假设你已经运行过CTA回测，这里我们需要从数据库或日志中分析
# 由于无法直接访问CTA回测引擎的内部数据，我们创建一个分析工具


def analyze_backtest_failure():
    """
    分析CTA回测爆仓的原因
    
    可能的原因：
    1. 手续费率设置过高
    2. 滑点设置过大
    3. 策略交易过于频繁
    4. 初始资金不足
    5. 止损设置不当
    """
    print("=" * 60)
    print("CTA回测爆仓原因分析")
    print("=" * 60)
    
    print("\n常见爆仓原因及解决方案：")
    print("\n1. 【手续费率过高】")
    print("   - 问题：手续费率设置不合理，累积成本过高")
    print("   - 检查：在CTA回测界面查看'手续费'参数")
    print("   - 建议：")
    print("     * 小恒指(MHI)通常手续费率：0.0001-0.0003 (万分之一到万分之三)")
    print("     * 建议从0.0002开始测试")
    
    print("\n2. 【滑点设置过大】")
    print("   - 问题：滑点设置不合理，每次交易都有较大成本")
    print("   - 检查：在CTA回测界面查看'滑点'参数")
    print("   - 建议：")
    print("     * 小恒指通常滑点：0-2个点")
    print("     * 建议从0.5或1开始测试")
    
    print("\n3. 【策略交易过于频繁】")
    print("   - 问题：策略频繁开平仓，累积手续费和滑点成本")
    print("   - 检查：查看回测日志中的成交记录数量")
    print("   - 建议：")
    print("     * 添加趋势过滤，减少交易频率")
    print("     * 增加持仓时间，避免频繁交易")
    
    print("\n4. 【初始资金不足】")
    print("   - 问题：初始资金太小，无法承受正常的回撤")
    print("   - 检查：在CTA回测界面查看'初始资金'参数")
    print("   - 建议：")
    print("     * 小恒指1手约需要保证金：20,000-30,000港币")
    print("     * 建议初始资金至少：100,000港币（3-5倍保证金）")
    print("     * 更安全的配置：200,000-500,000港币")
    
    print("\n5. 【止损设置不当】")
    print("   - 问题：ATR止损倍数太小，止损触发频繁")
    print("   - 检查：查看策略中的atr_multiplier参数")
    print("   - 建议：")
    print("     * 当前策略默认：atr_multiplier = 2.5")
    print("     * 可以尝试增加到3.0或3.5，减少止损频率")
    
    print("\n6. 【策略逻辑问题】")
    print("   - 问题：策略在不利市场环境下持续亏损")
    print("   - 检查：查看回测日志中的交易信号")
    print("   - 建议：")
    print("     * 加强趋势过滤条件")
    print("     * 增加风控限制（如连续亏损停止交易）")
    
    print("\n" + "=" * 60)
    print("推荐的回测参数设置（小恒指MHImain）")
    print("=" * 60)
    print("\n【基本参数】")
    print("  - 初始资金：200,000 港币（或更高）")
    print("  - 合约代码：MHImain.HKFE 或 MHImain.SEHK")
    print("  - K线周期：1m（1分钟）")
    print("  - 开始日期：根据数据可用性设置")
    print("  - 结束日期：根据数据可用性设置")
    
    print("\n【交易成本】")
    print("  - 手续费率：0.0002 (万分之二)")
    print("  - 滑点：0.5 或 1.0 点")
    
    print("\n【策略参数优化建议】")
    print("  - 增加ATR止损倍数：atr_multiplier = 3.0 或 3.5")
    print("  - 加强趋势过滤：min_trend_strength = 1.0% (从0.5%提高到1.0%)")
    print("  - 减少交易频率：trend_filter_window = 60 (从50增加到60)")
    
    print("\n" + "=" * 60)


def create_safe_backtest_config():
    """
    创建安全的回测配置示例
    """
    config = {
        "vt_symbol": "MHImain.HKFE",  # 或 MHImain.SEHK
        "interval": "1m",
        "start": datetime(2024, 1, 1),
        "end": datetime(2024, 11, 20),
        "rate": 0.0002,      # 手续费率：万分之二
        "slippage": 1.0,     # 滑点：1个点
        "size": 50,          # 合约乘数（小恒指）
        "pricetick": 1.0,    # 价格跳动
        "capital": 500_000   # 初始资金：50万港币（更安全）
    }
    
    strategy_setting = {
        "fast_window": 12,
        "slow_window": 26,
        "atr_window": 20,
        "atr_multiplier": 3.0,          # 增加到3.0，减少止损频率
        "fixed_size": 1,
        "trend_filter_window": 60,      # 增加到60，加强趋势过滤
        "min_trend_strength": 1.0,      # 提高到1.0%，减少交易频率
        "max_daily_trades": 5,          # 减少每日最大交易次数
        "max_consecutive_losses": 2     # 减少连续亏损限制
    }
    
    print("\n推荐的回测配置：")
    print("=" * 60)
    print("\n【回测参数】")
    for key, value in config.items():
        print(f"  {key}: {value}")
    
    print("\n【策略参数】")
    for key, value in strategy_setting.items():
        print(f"  {key}: {value}")
    
    return config, strategy_setting


if __name__ == "__main__":
    analyze_backtest_failure()
    print("\n")
    create_safe_backtest_config()

