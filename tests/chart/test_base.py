"""测试基类和工具函数"""

from typing import Any
from unittest.mock import Mock
from vnpy.trader.object import PositionData, OrderData, BarData, TickData
from vnpy.trader.constant import Direction, Offset, Status, Exchange


class TestBase:
    """测试基类，提供通用测试辅助方法"""
    
    @staticmethod
    def create_position_data(
        symbol: str = "MHI2512",
        exchange: Exchange = Exchange.HKFE,
        direction: Direction = Direction.LONG,
        volume: float = 10.0,
        frozen: float = 0.0,
        price: float = 20000.0,
        pnl: float = 0.0,
        gateway_name: str = "FUTU"
    ) -> PositionData:
        """创建测试用的持仓数据"""
        position = PositionData(
            symbol=symbol,
            exchange=exchange,
            direction=direction,
            volume=volume,
            frozen=frozen,
            price=price,
            pnl=pnl,
            gateway_name=gateway_name
        )
        return position
    
    @staticmethod
    def create_order_data(
        symbol: str = "MHI2512",
        exchange: Exchange = Exchange.HKFE,
        orderid: str = "12345",
        direction: Direction = Direction.LONG,
        offset: Offset = Offset.OPEN,
        price: float = 20000.0,
        volume: float = 10.0,
        traded: float = 10.0,
        status: Status = Status.ALLTRADED,
        gateway_name: str = "TEST"
    ) -> OrderData:
        """创建测试用的订单数据"""
        order = OrderData(
            symbol=symbol,
            exchange=exchange,
            orderid=orderid,
            direction=direction,
            offset=offset,
            price=price,
            volume=volume,
            traded=traded,
            status=status,
            gateway_name=gateway_name
        )
        return order
    
    @staticmethod
    def create_bar_data(
        symbol: str = "MHI2512",
        exchange: Exchange = Exchange.HKFE,
        datetime: Any = None,
        interval: Any = None,
        open_price: float = 20000.0,
        high_price: float = 20050.0,
        low_price: float = 19950.0,
        close_price: float = 20025.0,
        volume: float = 1000.0,
        gateway_name: str = "TEST"
    ) -> BarData:
        """创建测试用的K线数据"""
        from datetime import datetime as dt
        if datetime is None:
            datetime = dt.now()
        
        bar = BarData(
            symbol=symbol,
            exchange=exchange,
            datetime=datetime,
            interval=interval,
            open_price=open_price,
            high_price=high_price,
            low_price=low_price,
            close_price=close_price,
            volume=volume,
            gateway_name=gateway_name
        )
        return bar
    
    @staticmethod
    def create_tick_data(
        symbol: str = "MHI2512",
        exchange: Exchange = Exchange.HKFE,
        datetime: Any = None,
        last_price: float = 20000.0,
        bid_price_1: float = 19999.0,
        ask_price_1: float = 20001.0,
        volume: float = 1000.0,
        gateway_name: str = "TEST"
    ) -> TickData:
        """创建测试用的Tick数据"""
        from datetime import datetime as dt
        if datetime is None:
            datetime = dt.now()
        
        tick = TickData(
            symbol=symbol,
            exchange=exchange,
            datetime=datetime,
            last_price=last_price,
            bid_price_1=bid_price_1,
            ask_price_1=ask_price_1,
            volume=volume,
            gateway_name=gateway_name
        )
        return tick

