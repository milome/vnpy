"""
MHImain合约策略回测脚本
"""
from datetime import datetime
from pathlib import Path
import polars as pl

from vnpy.trader.constant import Interval, Exchange
from vnpy.trader.object import BarData
from vnpy.trader.datafeed import get_datafeed

from vnpy.alpha import AlphaLab, BacktestingEngine
from simple_strategy import SimpleMHImainStrategy, BuyAndHoldStrategy


def download_mhimain_data(
    lab: AlphaLab,
    start: datetime,
    end: datetime,
    interval: Interval = Interval.DAILY
) -> bool:
    """
    下载MHImain历史数据
    
    Args:
        lab: AlphaLab实例
        start: 开始日期
        end: 结束日期
        interval: K线周期
    
    Returns:
        是否成功下载
    """
    print("=" * 50)
    print("开始下载MHImain历史数据...")
    print(f"合约: MHImain.SEHK")
    print(f"周期: {interval.value}")
    print(f"时间范围: {start.date()} 至 {end.date()}")
    print("=" * 50)

    # 获取数据服务
    datafeed = get_datafeed()
    if not datafeed:
        print("错误: 未配置数据服务，请先配置数据源")
        print("提示: 可以配置富途(futu)等数据服务")
        return False

    # 初始化数据服务
    if not datafeed.init():
        print("错误: 数据服务初始化失败")
        return False

    # 构建历史数据请求
    from vnpy.trader.object import HistoryRequest
    
    req = HistoryRequest(
        symbol="MHImain",
        exchange=Exchange.SEHK,
        interval=interval,
        start=start,
        end=end
    )

    # 查询历史数据
    bars = datafeed.query_bar_history(req)
    
    if not bars:
        print("错误: 未获取到历史数据")
        return False

    print(f"成功获取 {len(bars)} 条K线数据")

    # 保存数据
    lab.save_bar_data(bars)
    print(f"数据已保存到: {lab.lab_path}")
    
    # 关闭数据服务
    datafeed.close()
    
    return True


def setup_contract_config(lab: AlphaLab):
    """
    配置MHImain合约信息
    
    Args:
        lab: AlphaLab实例
    """
    print("=" * 50)
    print("配置MHImain合约信息...")
    print("=" * 50)

    # MHImain合约配置
    # 注意：以下参数需要根据实际情况调整
    lab.add_contract_setting(
        vt_symbol="MHImain.SEHK",
        long_rate=0.0003,      # 做多手续费率（万分之3）
        short_rate=0.0003,     # 做空手续费率（万分之3）
        size=50,               # 合约乘数（需要根据实际情况调整）
        pricetick=1.0          # 价格跳动单位（需要根据实际情况调整）
    )

    print("合约配置完成:")
    print("  - 合约代码: MHImain.SEHK")
    print("  - 做多手续费率: 0.03%")
    print("  - 做空手续费率: 0.03%")
    print("  - 合约乘数: 50")
    print("  - 价格跳动: 1.0")


def run_backtest(
    lab: AlphaLab,
    strategy_class,
    strategy_setting: dict = None,
    start: datetime = None,
    end: datetime = None,
    interval: Interval = Interval.DAILY,
    capital: float = 1_000_000
):
    """
    运行回测
    
    Args:
        lab: AlphaLab实例
        strategy_class: 策略类
        strategy_setting: 策略参数
        start: 开始日期
        end: 结束日期
        interval: K线周期
        capital: 初始资金
    """
    if strategy_setting is None:
        strategy_setting = {}
    
    if start is None:
        start = datetime(2023, 1, 1)
    
    if end is None:
        end = datetime(2023, 12, 31)

    print("=" * 50)
    print("开始回测...")
    print(f"策略: {strategy_class.__name__}")
    print(f"时间范围: {start.date()} 至 {end.date()}")
    print(f"初始资金: {capital:,.0f}")
    print("=" * 50)

    # 创建回测引擎
    engine = BacktestingEngine(lab)

    # 设置回测参数
    engine.set_parameters(
        vt_symbols=["MHImain.SEHK"],
        interval=interval,
        start=start,
        end=end,
        capital=capital,
        risk_free=0.02,           # 无风险利率（年化2%）
        annual_days=240           # 年交易日数
    )

    # 添加策略
    # 注意：Alpha策略回测需要信号DataFrame，如果策略不使用信号，传入空的DataFrame
    signal_df = pl.DataFrame()
    engine.add_strategy(strategy_class, strategy_setting, signal_df)

    # 加载历史数据
    print("\n正在加载历史数据...")
    engine.load_data()

    # 运行回测
    print("\n正在运行回测...")
    engine.run_backtesting()

    # 计算结果
    print("\n正在计算结果...")
    df = engine.calculate_result()
    
    if df is None or df.is_empty():
        print("警告: 未生成回测结果，可能是没有成交记录")
        return None

    # 计算统计指标
    statistics = engine.calculate_statistics()

    # 显示结果
    print("\n" + "=" * 50)
    print("回测统计结果")
    print("=" * 50)
    print(f"起始日期: {statistics.get('start_date', 'N/A')}")
    print(f"结束日期: {statistics.get('end_date', 'N/A')}")
    print(f"总交易日: {statistics.get('total_days', 0)}")
    print(f"起始资金: {statistics.get('capital', 0):,.2f}")
    print(f"结束资金: {statistics.get('end_balance', 0):,.2f}")
    print(f"总收益率: {statistics.get('total_return', 0):.2f}%")
    print(f"年化收益: {statistics.get('annual_return', 0):.2f}%")
    print(f"最大回撤: {statistics.get('max_drawdown', 0):,.2f}")
    print(f"百分比最大回撤: {statistics.get('max_ddpercent', 0):.2f}%")
    print(f"Sharpe Ratio: {statistics.get('sharpe_ratio', 0):.2f}")
    print(f"总盈亏: {statistics.get('total_net_pnl', 0):,.2f}")
    print(f"总手续费: {statistics.get('total_commission', 0):,.2f}")
    print(f"总成交笔数: {statistics.get('total_trade_count', 0)}")
    print("=" * 50)

    # 显示图表（可选）
    try:
        print("\n正在生成图表...")
        engine.show_chart()
    except Exception as e:
        print(f"图表生成失败: {e}")

    return statistics


def main():
    """主函数"""
    # 数据路径
    lab_path = "./lab/mhimain"
    lab = AlphaLab(lab_path)

    # 配置合约信息
    setup_contract_config(lab)

    # 回测参数
    start = datetime(2023, 1, 1)
    end = datetime(2023, 12, 31)
    interval = Interval.DAILY
    capital = 1_000_000

    # 检查数据是否存在
    daily_path = Path(lab_path) / "daily" / "MHImain.SEHK.parquet"
    if not daily_path.exists():
        print(f"\n数据文件不存在: {daily_path}")
        print("正在尝试下载数据...")
        
        # 下载数据
        if not download_mhimain_data(lab, start, end, interval):
            print("\n数据下载失败，请检查:")
            print("1. 是否配置了数据服务（如富途）")
            print("2. 数据服务是否正常运行")
            print("3. 网络连接是否正常")
            return
    
    # 选择策略
    # 选项1: 买入持有策略（用于测试）
    # strategy_class = BuyAndHoldStrategy
    
    # 选项2: 简单趋势策略
    strategy_class = SimpleMHImainStrategy

    # 运行回测
    statistics = run_backtest(
        lab=lab,
        strategy_class=strategy_class,
        strategy_setting={},
        start=start,
        end=end,
        interval=interval,
        capital=capital
    )

    if statistics:
        print("\n回测完成！")
    else:
        print("\n回测失败，请检查数据是否完整。")


if __name__ == "__main__":
    main()

