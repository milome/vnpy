"""
准备测试数据脚本

如果没有真实的历史数据，可以使用此脚本生成模拟数据进行测试
"""
from datetime import datetime, timedelta
import random
from pathlib import Path

import polars as pl

from vnpy.trader.constant import Interval, Exchange
from vnpy.trader.object import BarData

from vnpy.alpha import AlphaLab


def generate_test_data(
    lab: AlphaLab,
    start: datetime,
    end: datetime,
    interval: Interval = Interval.DAILY,
    base_price: float = 20000.0,
    volatility: float = 0.02
) -> None:
    """
    生成测试用的模拟K线数据
    
    Args:
        lab: AlphaLab实例
        start: 开始日期
        end: 结束日期
        interval: K线周期
        base_price: 基础价格
        volatility: 波动率（日波动率）
    """
    print("=" * 50)
    print("生成测试数据...")
    print(f"合约: MHImain.SEHK")
    print(f"周期: {interval.value}")
    print(f"时间范围: {start.date()} 至 {end.date()}")
    print(f"基础价格: {base_price}")
    print(f"波动率: {volatility * 100}%")
    print("=" * 50)

    bars: list[BarData] = []
    current_date = start
    current_price = base_price

    # 生成每日K线数据
    while current_date <= end:
        # 跳过周末
        if current_date.weekday() >= 5:  # 周六、周日
            current_date += timedelta(days=1)
            continue

        # 生成随机涨跌幅
        change = random.uniform(-volatility, volatility)
        
        # 计算OHLC
        open_price = current_price
        close_price = open_price * (1 + change)
        high_price = max(open_price, close_price) * (1 + abs(random.uniform(0, volatility / 2)))
        low_price = min(open_price, close_price) * (1 - abs(random.uniform(0, volatility / 2)))
        
        # 生成成交量
        volume = random.randint(100, 1000)
        turnover = volume * close_price * 50  # 假设合约乘数为50

        # 创建BarData
        bar = BarData(
            symbol="MHImain",
            exchange=Exchange.SEHK,
            datetime=current_date,
            interval=interval,
            open_price=round(open_price, 2),
            high_price=round(high_price, 2),
            low_price=round(low_price, 2),
            close_price=round(close_price, 2),
            volume=volume,
            turnover=turnover,
            open_interest=0,
            gateway_name="TEST"
        )
        
        bars.append(bar)
        current_price = close_price
        current_date += timedelta(days=1)

    # 保存数据
    lab.save_bar_data(bars)
    print(f"\n成功生成 {len(bars)} 条测试数据")
    print(f"数据已保存到: {lab.lab_path}")


def main():
    """主函数"""
    # 数据路径
    lab_path = "./lab/mhimain"
    lab = AlphaLab(lab_path)

    # 生成测试数据
    start = datetime(2023, 1, 1)
    end = datetime(2023, 12, 31)
    
    generate_test_data(
        lab=lab,
        start=start,
        end=end,
        interval=Interval.DAILY,
        base_price=20000.0,
        volatility=0.02
    )

    print("\n测试数据准备完成！")
    print("现在可以运行 backtest_mhimain.py 进行回测了")


if __name__ == "__main__":
    main()

