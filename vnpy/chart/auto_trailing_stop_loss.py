"""
Auto trailing stop loss module.

Automatically adjusts stop loss line as price moves in favorable direction.
"""

from typing import Optional, Callable
from dataclasses import dataclass

from vnpy.trader.object import TickData, BarData

from .price_line import PriceLineItem, PriceLineManager, PriceLineType


@dataclass
class TrailingStopConfig:
    """Configuration for trailing stop loss."""
    
    trailing_percent: float = 1.0  # Trailing stop percentage (1%)
    trailing_points: float = 0.0    # Trailing stop in points (0 = use percentage)
    min_distance: float = 0.0      # Minimum distance before moving stop
    use_atr: bool = False           # Use ATR-based trailing stop
    atr_multiplier: float = 2.0     # ATR multiplier (if use_atr=True)
    atr_period: int = 14            # ATR period (if use_atr=True)


class AutoTrailingStopLoss:
    """
    Auto trailing stop loss manager.
    
    Automatically adjusts stop loss lines based on price movement.
    """

    def __init__(
        self,
        price_line_manager: PriceLineManager,
        config: Optional[TrailingStopConfig] = None
    ) -> None:
        """
        Initialize auto trailing stop loss.

        Args:
            price_line_manager: PriceLineManager instance
            config: Trailing stop configuration
        """
        self._price_line_manager = price_line_manager
        self._config = config or TrailingStopConfig()
        
        # Map: stop_loss_line_id -> entry_line_id
        self._stop_entry_map: dict[str, str] = {}
        
        # Track highest/lowest price for each stop loss
        self._highest_price: dict[str, float] = {}  # For long positions
        self._lowest_price: dict[str, float] = {}   # For short positions
        
        # ATR data (if using ATR-based trailing)
        self._atr_data: dict[str, list[float]] = {}  # Map: entry_line_id -> ATR values

    def register_trailing_stop(
        self,
        stop_loss_line_id: str,
        entry_line_id: str,
        entry_price: float,
        direction: str
    ) -> None:
        """
        Register a stop loss line for auto trailing.

        Args:
            stop_loss_line_id: Stop loss line ID
            entry_line_id: Entry line ID
            entry_price: Entry price
            direction: Trading direction ("long" or "short")
        """
        self._stop_entry_map[stop_loss_line_id] = entry_line_id

        if direction == "long":
            self._highest_price[stop_loss_line_id] = entry_price
        else:
            self._lowest_price[stop_loss_line_id] = entry_price

    def unregister_trailing_stop(self, stop_loss_line_id: str) -> None:
        """
        Unregister a stop loss line from auto trailing.

        Args:
            stop_loss_line_id: Stop loss line ID
        """
        self._stop_entry_map.pop(stop_loss_line_id, None)
        self._highest_price.pop(stop_loss_line_id, None)
        self._lowest_price.pop(stop_loss_line_id, None)

    def update_from_tick(
        self,
        tick: TickData,
        callback: Optional[Callable[[str, float], None]] = None
    ) -> None:
        """
        Update trailing stops from tick data.

        Args:
            tick: Tick data
            callback: Optional callback function(stop_loss_line_id, new_price)
        """
        current_price = tick.last_price
        if current_price <= 0:
            return

        for stop_loss_line_id, entry_line_id in self._stop_entry_map.items():
            stop_loss_line = self._price_line_manager.get_line(stop_loss_line_id)
            if stop_loss_line is None:
                continue

            # Determine direction from line direction
            direction = stop_loss_line.get_direction()
            current_stop_price = stop_loss_line.get_price()

            if direction == "long":
                # Long position: track highest price, move stop up
                if stop_loss_line_id not in self._highest_price:
                    self._highest_price[stop_loss_line_id] = current_price
                else:
                    self._highest_price[stop_loss_line_id] = max(
                        self._highest_price[stop_loss_line_id],
                        current_price
                    )

                # Calculate new stop price
                highest = self._highest_price[stop_loss_line_id]
                if self._config.trailing_points > 0:
                    new_stop_price = highest - self._config.trailing_points
                else:
                    new_stop_price = highest * (1 - self._config.trailing_percent / 100)

                # Only move up if new price is higher
                if new_stop_price > current_stop_price + self._config.min_distance:
                    stop_loss_line.set_price(new_stop_price)
                    if callback:
                        callback(stop_loss_line_id, new_stop_price)

            else:  # short
                # Short position: track lowest price, move stop down
                if stop_loss_line_id not in self._lowest_price:
                    self._lowest_price[stop_loss_line_id] = current_price
                else:
                    self._lowest_price[stop_loss_line_id] = min(
                        self._lowest_price[stop_loss_line_id],
                        current_price
                    )

                # Calculate new stop price
                lowest = self._lowest_price[stop_loss_line_id]
                if self._config.trailing_points > 0:
                    new_stop_price = lowest + self._config.trailing_points
                else:
                    new_stop_price = lowest * (1 + self._config.trailing_percent / 100)

                # Only move down if new price is lower
                if new_stop_price < current_stop_price - self._config.min_distance:
                    stop_loss_line.set_price(new_stop_price)
                    if callback:
                        callback(stop_loss_line_id, new_stop_price)

    def update_from_bar(
        self,
        bar: BarData,
        callback: Optional[Callable[[str, float], None]] = None
    ) -> None:
        """
        Update trailing stops from bar data.

        Args:
            bar: Bar data
            callback: Optional callback function(stop_loss_line_id, new_price)
        """
        for stop_loss_line_id, entry_line_id in self._stop_entry_map.items():
            stop_loss_line = self._price_line_manager.get_line(stop_loss_line_id)
            if stop_loss_line is None:
                continue

            direction = stop_loss_line.get_direction()
            current_stop_price = stop_loss_line.get_price()

            if direction == "long":
                # Long: use high price
                current_price = bar.high_price
                if current_price <= 0:
                    continue

                if stop_loss_line_id not in self._highest_price:
                    self._highest_price[stop_loss_line_id] = current_price
                else:
                    self._highest_price[stop_loss_line_id] = max(
                        self._highest_price[stop_loss_line_id],
                        current_price
                    )

                highest = self._highest_price[stop_loss_line_id]
                if self._config.trailing_points > 0:
                    new_stop_price = highest - self._config.trailing_points
                else:
                    new_stop_price = highest * (1 - self._config.trailing_percent / 100)

                if new_stop_price > current_stop_price + self._config.min_distance:
                    stop_loss_line.set_price(new_stop_price)
                    if callback:
                        callback(stop_loss_line_id, new_stop_price)

            else:  # short
                # Short: use low price
                current_price = bar.low_price
                if current_price <= 0:
                    continue

                if stop_loss_line_id not in self._lowest_price:
                    self._lowest_price[stop_loss_line_id] = current_price
                else:
                    self._lowest_price[stop_loss_line_id] = min(
                        self._lowest_price[stop_loss_line_id],
                        current_price
                    )

                lowest = self._lowest_price[stop_loss_line_id]
                if self._config.trailing_points > 0:
                    new_stop_price = lowest + self._config.trailing_points
                else:
                    new_stop_price = lowest * (1 + self._config.trailing_percent / 100)

                if new_stop_price < current_stop_price - self._config.min_distance:
                    stop_loss_line.set_price(new_stop_price)
                    if callback:
                        callback(stop_loss_line_id, new_stop_price)

    def clear_all(self) -> None:
        """Clear all trailing stop data."""
        self._stop_entry_map.clear()
        self._highest_price.clear()
        self._lowest_price.clear()
        self._atr_data.clear()

