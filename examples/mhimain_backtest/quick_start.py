"""
快速启动脚本 - 最简单的MHImain回测示例

使用方法：
1. 如果有真实数据，确保数据在 ./lab/mhimain/daily/MHImain.SEHK.parquet
2. 如果没有数据，先运行 prepare_test_data.py 生成测试数据
3. 然后运行此脚本：python quick_start.py
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime
import polars as pl

from vnpy.trader.constant import Interval
from vnpy.alpha import AlphaLab, BacktestingEngine
try:
    from simple_strategy import BuyAndHoldStrategy
except ImportError:
    # 如果直接运行此文件，需要添加当前目录到路径
    import sys
    from pathlib import Path
    current_dir = Path(__file__).parent
    sys.path.insert(0, str(current_dir))
    from simple_strategy import BuyAndHoldStrategy


def main():
    """快速启动回测"""
    print("=" * 60)
    print("MHImain合约策略回测 - 快速启动")
    print("=" * 60)
    
    # 1. 初始化AlphaLab
    lab_path = "./lab/mhimain"
    lab = AlphaLab(lab_path)
    print(f"\n[OK] AlphaLab初始化完成: {lab_path}")
    
    # 2. 配置合约（如果没有配置过）
    contract_path = lab.contract_path
    if not contract_path.exists():
        print("\n配置合约信息...")
        lab.add_contract_setting(
            vt_symbol="MHImain.SEHK",
            long_rate=0.0003,
            short_rate=0.0003,
            size=50,
            pricetick=1.0
        )
        print("[OK] 合约配置完成")
    else:
        print("[OK] 合约配置已存在")
    
    # 3. 检查数据是否存在
    daily_file = lab.daily_path / "MHImain.SEHK.parquet"
    if not daily_file.exists():
        print(f"\n[ERROR] 数据文件不存在: {daily_file}")
        print("\n请先准备数据：")
        print("  1. 运行 prepare_test_data.py 生成测试数据")
        print("  2. 或运行 backtest_mhimain.py 自动下载数据")
        return
    else:
        print(f"[OK] 数据文件存在: {daily_file}")
    
    # 4. 设置回测参数
    engine = BacktestingEngine(lab)
    engine.set_parameters(
        vt_symbols=["MHImain.SEHK"],
        interval=Interval.DAILY,
        start=datetime(2023, 1, 1),
        end=datetime(2023, 12, 31),
        capital=1_000_000,
        risk_free=0.02,
        annual_days=240
    )
    print("\n[OK] 回测参数设置完成")
    
    # 5. 添加策略（买入持有策略 - 最简单）
    strategy_setting = {}
    signal_df = pl.DataFrame()
    engine.add_strategy(BuyAndHoldStrategy, strategy_setting, signal_df)
    print("[OK] 策略添加完成 (买入持有策略)")
    
    # 6. 加载数据
    print("\n正在加载历史数据...")
    engine.load_data()
    print("[OK] 数据加载完成")
    
    # 7. 运行回测
    print("\n正在运行回测...")
    engine.run_backtesting()
    print("[OK] 回测执行完成")
    
    # 8. 计算结果
    print("\n正在计算结果...")
    df = engine.calculate_result()
    
    if df is None or df.is_empty():
        print("[ERROR] 未生成回测结果（可能没有成交记录）")
        return
    
    statistics = engine.calculate_statistics()
    
    # 9. 显示结果
    print("\n" + "=" * 60)
    print("回测结果")
    print("=" * 60)
    print(f"起始日期: {statistics.get('start_date', 'N/A')}")
    print(f"结束日期: {statistics.get('end_date', 'N/A')}")
    print(f"总交易日: {statistics.get('total_days', 0)}")
    print(f"起始资金: {statistics.get('capital', 0):,.2f}")
    print(f"结束资金: {statistics.get('end_balance', 0):,.2f}")
    print(f"总收益率: {statistics.get('total_return', 0):.2f}%")
    print(f"年化收益: {statistics.get('annual_return', 0):.2f}%")
    print(f"最大回撤: {statistics.get('max_drawdown', 0):,.2f}")
    print(f"Sharpe Ratio: {statistics.get('sharpe_ratio', 0):.2f}")
    print(f"总盈亏: {statistics.get('total_net_pnl', 0):,.2f}")
    print(f"总手续费: {statistics.get('total_commission', 0):,.2f}")
    print(f"总成交笔数: {statistics.get('total_trade_count', 0)}")
    print("=" * 60)
    
    # 10. 尝试显示图表（如果可能）
    try:
        print("\n正在生成图表...")
        engine.show_chart()
    except Exception as e:
        print(f"[WARNING] 图表生成失败（可以忽略）: {e}")
    
    print("\n[OK] 回测完成！")


if __name__ == "__main__":
    main()

