"""
Dual stop loss controller module.

Implements dual stop loss protection logic:
- Fixed stop loss: Based on entry price with fixed percentage/points
- Trailing stop loss: Moves with price in favorable direction
"""

from typing import Optional
from dataclasses import dataclass

from vnpy.trader.object import TickData, BarData

from .price_line import PriceLineItem, PriceLineManager, PriceLineType


@dataclass
class StopLossConfig:
    """Configuration for stop loss."""
    
    fixed_stop_percent: float = 2.0  # Fixed stop loss percentage (2%)
    trailing_stop_percent: float = 1.0  # Trailing stop loss percentage (1%)
    use_fixed_stop: bool = True  # Enable fixed stop loss
    use_trailing_stop: bool = True  # Enable trailing stop loss
    min_trailing_distance: float = 0.0  # Minimum distance for trailing stop to move


class DualStopLossController:
    """
    Controller for dual stop loss protection.
    
    Manages both fixed and trailing stop loss lines for entry positions.
    """

    def __init__(
        self,
        price_line_manager: PriceLineManager,
        config: Optional[StopLossConfig] = None
    ) -> None:
        """
        Initialize dual stop loss controller.

        Args:
            price_line_manager: PriceLineManager instance
            config: Stop loss configuration
        """
        self._price_line_manager = price_line_manager
        self._config = config or StopLossConfig()
        
        # Map: entry_line_id -> (fixed_stop_line_id, trailing_stop_line_id)
        self._entry_stop_map: dict[str, tuple[str, str]] = {}
        
        # Track highest/lowest price for trailing stop
        self._trailing_high: dict[str, float] = {}  # For long positions
        self._trailing_low: dict[str, float] = {}   # For short positions

    def create_stop_loss_for_entry(
        self,
        entry_line_id: str,
        entry_price: float,
        direction: str,
        plot: object
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Create stop loss lines for an entry line.

        Args:
            entry_line_id: Entry line ID
            entry_price: Entry price
            direction: Trading direction ("long" or "short")
            plot: PlotItem to add lines to

        Returns:
            Tuple of (fixed_stop_line_id, trailing_stop_line_id)
        """
        fixed_stop_id: Optional[str] = None
        trailing_stop_id: Optional[str] = None

        # Calculate stop loss prices
        if direction == "long":
            # Long position: stop loss below entry
            if self._config.use_fixed_stop:
                fixed_stop_price = entry_price * (1 - self._config.fixed_stop_percent / 100)
                fixed_stop_id = self._price_line_manager.create_line(
                    price=fixed_stop_price,
                    line_type=PriceLineType.STOP_LOSS,
                    direction=direction,
                    movable=True,
                    line_id=f"{entry_line_id}_fixed_stop"
                )
                line = self._price_line_manager.get_line(fixed_stop_id)
                if line and plot:
                    plot.addItem(line)

            if self._config.use_trailing_stop:
                trailing_stop_price = entry_price * (1 - self._config.trailing_stop_percent / 100)
                trailing_stop_id = self._price_line_manager.create_line(
                    price=trailing_stop_price,
                    line_type=PriceLineType.STOP_LOSS,
                    direction=direction,
                    movable=True,
                    line_id=f"{entry_line_id}_trailing_stop"
                )
                line = self._price_line_manager.get_line(trailing_stop_id)
                if line and plot:
                    plot.addItem(line)
                
                # Initialize trailing high
                self._trailing_high[entry_line_id] = entry_price

        else:  # short
            # Short position: stop loss above entry
            if self._config.use_fixed_stop:
                fixed_stop_price = entry_price * (1 + self._config.fixed_stop_percent / 100)
                fixed_stop_id = self._price_line_manager.create_line(
                    price=fixed_stop_price,
                    line_type=PriceLineType.STOP_LOSS,
                    direction=direction,
                    movable=True,
                    line_id=f"{entry_line_id}_fixed_stop"
                )
                line = self._price_line_manager.get_line(fixed_stop_id)
                if line and plot:
                    plot.addItem(line)

            if self._config.use_trailing_stop:
                trailing_stop_price = entry_price * (1 + self._config.trailing_stop_percent / 100)
                trailing_stop_id = self._price_line_manager.create_line(
                    price=trailing_stop_price,
                    line_type=PriceLineType.STOP_LOSS,
                    direction=direction,
                    movable=True,
                    line_id=f"{entry_line_id}_trailing_stop"
                )
                line = self._price_line_manager.get_line(trailing_stop_id)
                if line and plot:
                    plot.addItem(line)
                
                # Initialize trailing low
                self._trailing_low[entry_line_id] = entry_price

        # Store mapping
        self._entry_stop_map[entry_line_id] = (fixed_stop_id, trailing_stop_id)

        return (fixed_stop_id, trailing_stop_id)

    def update_trailing_stop(
        self,
        entry_line_id: str,
        current_price: float,
        direction: str
    ) -> bool:
        """
        Update trailing stop loss based on current price.

        Args:
            entry_line_id: Entry line ID
            current_price: Current market price
            direction: Trading direction ("long" or "short")

        Returns:
            True if trailing stop was updated, False otherwise
        """
        if entry_line_id not in self._entry_stop_map:
            return False

        _, trailing_stop_id = self._entry_stop_map[entry_line_id]
        if trailing_stop_id is None:
            return False

        trailing_stop_line = self._price_line_manager.get_line(trailing_stop_id)
        if trailing_stop_line is None:
            return False

        current_trailing_price = trailing_stop_line.get_price()

        if direction == "long":
            # Long: update trailing high, move stop loss up
            if entry_line_id not in self._trailing_high:
                self._trailing_high[entry_line_id] = current_price
            else:
                self._trailing_high[entry_line_id] = max(
                    self._trailing_high[entry_line_id],
                    current_price
                )

            # Calculate new trailing stop price
            new_trailing_price = self._trailing_high[entry_line_id] * (
                1 - self._config.trailing_stop_percent / 100
            )

            # Only move up if new price is higher than current
            if new_trailing_price > current_trailing_price + self._config.min_trailing_distance:
                trailing_stop_line.set_price(new_trailing_price)
                return True

        else:  # short
            # Short: update trailing low, move stop loss down
            if entry_line_id not in self._trailing_low:
                self._trailing_low[entry_line_id] = current_price
            else:
                self._trailing_low[entry_line_id] = min(
                    self._trailing_low[entry_line_id],
                    current_price
                )

            # Calculate new trailing stop price
            new_trailing_price = self._trailing_low[entry_line_id] * (
                1 + self._config.trailing_stop_percent / 100
            )

            # Only move down if new price is lower than current
            if new_trailing_price < current_trailing_price - self._config.min_trailing_distance:
                trailing_stop_line.set_price(new_trailing_price)
                return True

        return False

    def update_from_tick(self, tick: TickData, entry_line_id: str, direction: str) -> bool:
        """
        Update trailing stop from tick data.

        Args:
            tick: Tick data
            entry_line_id: Entry line ID
            direction: Trading direction

        Returns:
            True if updated
        """
        current_price = tick.last_price
        if current_price <= 0:
            return False

        return self.update_trailing_stop(entry_line_id, current_price, direction)

    def update_from_bar(self, bar: BarData, entry_line_id: str, direction: str) -> bool:
        """
        Update trailing stop from bar data.

        Args:
            bar: Bar data
            entry_line_id: Entry line ID
            direction: Trading direction

        Returns:
            True if updated
        """
        if direction == "long":
            current_price = bar.high_price  # Use high for long positions
        else:
            current_price = bar.low_price    # Use low for short positions

        if current_price <= 0:
            return False

        return self.update_trailing_stop(entry_line_id, current_price, direction)

    def get_stop_loss_lines(self, entry_line_id: str) -> tuple[Optional[str], Optional[str]]:
        """
        Get stop loss line IDs for an entry line.

        Args:
            entry_line_id: Entry line ID

        Returns:
            Tuple of (fixed_stop_line_id, trailing_stop_line_id)
        """
        return self._entry_stop_map.get(entry_line_id, (None, None))

    def remove_stop_loss(self, entry_line_id: str) -> bool:
        """
        Remove stop loss lines for an entry line.

        Args:
            entry_line_id: Entry line ID

        Returns:
            True if successful, False if entry not found
        """
        if entry_line_id not in self._entry_stop_map:
            return False

        fixed_stop_id, trailing_stop_id = self._entry_stop_map[entry_line_id]

        if fixed_stop_id:
            self._price_line_manager.delete_line(fixed_stop_id)
        if trailing_stop_id:
            self._price_line_manager.delete_line(trailing_stop_id)

        # Clean up tracking data
        self._entry_stop_map.pop(entry_line_id, None)
        self._trailing_high.pop(entry_line_id, None)
        self._trailing_low.pop(entry_line_id, None)

        return True

    def check_stop_loss_triggered(
        self,
        entry_line_id: str,
        current_price: float,
        direction: str
    ) -> Optional[str]:
        """
        Check if stop loss is triggered.

        Args:
            entry_line_id: Entry line ID
            current_price: Current market price
            direction: Trading direction

        Returns:
            "fixed" if fixed stop triggered, "trailing" if trailing stop triggered, None otherwise
        """
        if entry_line_id not in self._entry_stop_map:
            return None

        fixed_stop_id, trailing_stop_id = self._entry_stop_map[entry_line_id]

        if direction == "long":
            # Long: triggered if price goes below stop loss
            if fixed_stop_id:
                fixed_stop_line = self._price_line_manager.get_line(fixed_stop_id)
                if fixed_stop_line and current_price <= fixed_stop_line.get_price():
                    return "fixed"

            if trailing_stop_id:
                trailing_stop_line = self._price_line_manager.get_line(trailing_stop_id)
                if trailing_stop_line and current_price <= trailing_stop_line.get_price():
                    return "trailing"

        else:  # short
            # Short: triggered if price goes above stop loss
            if fixed_stop_id:
                fixed_stop_line = self._price_line_manager.get_line(fixed_stop_id)
                if fixed_stop_line and current_price >= fixed_stop_line.get_price():
                    return "fixed"

            if trailing_stop_id:
                trailing_stop_line = self._price_line_manager.get_line(trailing_stop_id)
                if trailing_stop_line and current_price >= trailing_stop_line.get_price():
                    return "trailing"

        return None

    def clear_all(self) -> None:
        """Clear all stop loss data."""
        self._entry_stop_map.clear()
        self._trailing_high.clear()
        self._trailing_low.clear()

