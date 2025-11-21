"""
MHImain合约简单策略示例
"""
from collections import defaultdict

from vnpy.trader.object import BarData, TradeData
from vnpy.trader.constant import Direction

from vnpy.alpha import AlphaStrategy


class SimpleMHImainStrategy(AlphaStrategy):
    """
    MHImain合约简单策略
    
    策略逻辑：
    1. 买入持有策略：开盘买入，收盘卖出
    2. 或简单趋势策略：收盘价高于开盘价买入，低于开盘价卖出
    """

    def on_init(self) -> None:
        """策略初始化"""
        self.write_log("MHImain简单策略初始化完成")
        # 可以在这里初始化指标、缓存变量等

    def on_bars(self, bars: dict[str, BarData]) -> None:
        """
        K线数据回调
        
        策略逻辑：如果收盘价高于开盘价，买入；如果收盘价低于开盘价，卖出
        """
        # 获取MHImain合约的K线数据
        bar = bars.get("MHImain.SEHK")
        if not bar:
            return

        # 获取当前持仓
        pos = self.get_pos("MHImain.SEHK")
        
        # 简单策略：收盘价高于开盘价时买入，低于开盘价时卖出
        if bar.close_price > bar.open_price:
            # 上涨趋势，买入或加仓
            if pos <= 0:
                # 如果没有多头持仓，买入
                self.buy("MHImain.SEHK", bar.close_price, 1)
                self.write_log(f"买入信号: 收盘价={bar.close_price}, 开盘价={bar.open_price}")
        elif bar.close_price < bar.open_price:
            # 下跌趋势，卖出或减仓
            if pos > 0:
                # 如果有多头持仓，卖出
                self.sell("MHImain.SEHK", bar.close_price, pos)
                self.write_log(f"卖出信号: 收盘价={bar.close_price}, 开盘价={bar.open_price}")

    def on_trade(self, trade: TradeData) -> None:
        """成交回调"""
        self.write_log(
            f"成交: {trade.vt_symbol} {trade.direction.value} "
            f"{trade.volume}手 @ {trade.price}"
        )


class BuyAndHoldStrategy(AlphaStrategy):
    """
    MHImain合约买入持有策略
    
    策略逻辑：第一个交易日买入，最后一个交易日卖出
    用于测试回测系统是否正常工作
    """

    def __init__(self, *args, **kwargs):
        """构造函数"""
        super().__init__(*args, **kwargs)
        self.has_position = False
        self.bought = False

    def on_init(self) -> None:
        """策略初始化"""
        self.write_log("MHImain买入持有策略初始化完成")
        self.has_position = False
        self.bought = False

    def on_bars(self, bars: dict[str, BarData]) -> None:
        """K线数据回调"""
        bar = bars.get("MHImain.SEHK")
        if not bar:
            return

        pos = self.get_pos("MHImain.SEHK")
        
        # 买入持有策略：第一次遇到K线就买入
        if not self.bought and pos == 0:
            self.buy("MHImain.SEHK", bar.close_price, 1)
            self.bought = True
            self.write_log(f"买入持有: 价格={bar.close_price}, 日期={bar.datetime}")

    def on_trade(self, trade: TradeData) -> None:
        """成交回调"""
        self.write_log(
            f"成交: {trade.vt_symbol} {trade.direction.value} "
            f"{trade.volume}手 @ {trade.price}"
        )

