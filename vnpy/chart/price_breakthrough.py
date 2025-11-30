"""
Price breakthrough detection module.

Monitors price movements and triggers callbacks when price breaks through
price lines (e.g., pending orders).
"""

from typing import Optional, Callable
from dataclasses import dataclass, field

from vnpy.trader.object import TickData, BarData
from vnpy.trader.constant import Direction

from .price_line import PriceLineItem, PriceLineType


@dataclass
class BreakthroughEvent:
    """Event data for price breakthrough."""
    
    line_id: str
    line_type: PriceLineType
    price: float
    direction: str
    current_price: float
    breakthrough_direction: str  # "up" or "down"
    tick: Optional[TickData] = None  # Tick数据（可选，用于触发下单时获取价格信息）


class PriceBreakthroughMonitor:
    """
    Monitor for price breakthrough events.
    
    Tracks price lines and detects when price breaks through them.
    """

    def __init__(self) -> None:
        """Initialize price breakthrough monitor."""
        # Map: line_id -> callback function
        self._callbacks: dict[str, Callable[[BreakthroughEvent], None]] = {}
        
        # Track last price for each line to detect breakthrough
        self._last_prices: dict[str, float] = {}

    def register_line(
        self,
        line_id: str,
        line: PriceLineItem,
        callback: Callable[[BreakthroughEvent], None]
    ) -> None:
        """
        Register a price line for breakthrough monitoring.

        Args:
            line_id: Line ID
            line: PriceLineItem instance
            callback: Callback function to call when breakthrough occurs
        """
        self._callbacks[line_id] = callback
        # Initialize last price (use line price as initial value)
        self._last_prices[line_id] = line.get_price()

    def unregister_line(self, line_id: str) -> None:
        """
        Unregister a price line from monitoring.

        Args:
            line_id: Line ID
        """
        self._callbacks.pop(line_id, None)
        self._last_prices.pop(line_id, None)

    def update_tick(self, tick: TickData, lines: dict[str, PriceLineItem]) -> None:
        """
        Update with tick data and check for breakthroughs.

        Args:
            tick: Tick data
            lines: Dictionary mapping line_id to PriceLineItem
        """
        current_price = tick.last_price
        if current_price <= 0:
            return

        for line_id, line in lines.items():
            if line_id not in self._callbacks:
                continue

            # Only monitor pending order lines
            if line.get_line_type() != PriceLineType.PENDING:
                continue

            line_price = line.get_price()
            last_price = self._last_prices.get(line_id, line_price)
            direction = line.get_direction()

            # Check for breakthrough
            breakthrough = self._check_breakthrough(
                current_price=current_price,
                last_price=last_price,
                line_price=line_price,
                direction=direction
            )

            if breakthrough:
                event = BreakthroughEvent(
                    line_id=line_id,
                    line_type=line.get_line_type(),
                    price=line_price,
                    direction=direction,
                    current_price=current_price,
                    breakthrough_direction=breakthrough,
                    tick=tick  # 传递tick数据
                )

                # Call callback
                callback = self._callbacks[line_id]
                if callback:
                    callback(event)

            # Update last price
            self._last_prices[line_id] = current_price

    def update_bar(self, bar: BarData, lines: dict[str, PriceLineItem]) -> None:
        """
        Update with bar data and check for breakthroughs.

        Args:
            bar: Bar data
            lines: Dictionary mapping line_id to PriceLineItem
        """
        # Use close price for bar data
        current_price = bar.close_price
        if current_price <= 0:
            return

        for line_id, line in lines.items():
            if line_id not in self._callbacks:
                continue

            # Only monitor pending order lines
            if line.get_line_type() != PriceLineType.PENDING:
                continue

            line_price = line.get_price()
            last_price = self._last_prices.get(line_id, line_price)
            direction = line.get_direction()

            # Check for breakthrough
            breakthrough = self._check_breakthrough(
                current_price=current_price,
                last_price=last_price,
                line_price=line_price,
                direction=direction
            )

            if breakthrough:
                # 对于bar数据，创建基于bar的模拟tick
                from datetime import datetime
                
                bar_tick = TickData(
                    symbol=bar.symbol,
                    exchange=bar.exchange,
                    datetime=bar.datetime,
                    gateway_name=bar.gateway_name,
                    last_price=current_price,
                    bid_price_1=current_price - 1.0,
                    ask_price_1=current_price + 1.0,
                    bid_volume_1=100,
                    ask_volume_1=100,
                    volume=bar.volume,
                    open_interest=bar.open_interest,
                )
                
                event = BreakthroughEvent(
                    line_id=line_id,
                    line_type=line.get_line_type(),
                    price=line_price,
                    direction=direction,
                    current_price=current_price,
                    breakthrough_direction=breakthrough,
                    tick=bar_tick  # 传递基于bar的tick数据
                )

                # Call callback
                callback = self._callbacks[line_id]
                if callback:
                    callback(event)

            # Update last price
            self._last_prices[line_id] = current_price

    def _check_breakthrough(
        self,
        current_price: float,
        last_price: float,
        line_price: float,
        direction: str
    ) -> Optional[str]:
        """
        Check if price has broken through the line.

        Args:
            current_price: Current market price
            last_price: Previous market price
            line_price: Price line value
            direction: Trading direction ("long" or "short")

        Returns:
            "up" if price broke upward, "down" if downward, None if no breakthrough
        """
        # For long orders: trigger when price goes up through the line
        if direction == "long":
            if last_price < line_price <= current_price:
                return "up"
        
        # For short orders: trigger when price goes down through the line
        elif direction == "short":
            if last_price > line_price >= current_price:
                return "down"

        return None

    def clear(self) -> None:
        """Clear all registered lines."""
        self._callbacks.clear()
        self._last_prices.clear()

