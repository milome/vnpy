"""
Entry line drag handler for creating stop loss and take profit lines.

Allows dragging from entry line to create stop loss/take profit lines.
"""

from typing import Optional, Callable

import pyqtgraph as pg  # type: ignore

from vnpy.trader.ui import QtCore, QtGui

from .price_line import PriceLineItem, PriceLineManager, PriceLineType
from .price_line_drag import PriceLineDragHandler


class EntryLineDragHandler:
    """
    Handler for dragging from entry lines to create stop loss/take profit.
    
    When user drags from an entry line:
    - Drag down (for long) or up (for short): Create stop loss
    - Drag up (for long) or down (for short): Create take profit
    """

    def __init__(
        self,
        plot: pg.PlotItem,
        price_line_manager: PriceLineManager,
        drag_handler: PriceLineDragHandler
    ) -> None:
        """
        Initialize entry line drag handler.

        Args:
            plot: PlotItem where lines are displayed
            price_line_manager: PriceLineManager instance
            drag_handler: PriceLineDragHandler instance
        """
        self._plot = plot
        self._price_line_manager = price_line_manager
        self._drag_handler = drag_handler

        # Drag state
        self._is_dragging_from_entry: bool = False
        self._entry_line: Optional[PriceLineItem] = None
        self._entry_line_id: Optional[str] = None
        self._drag_start_price: float = 0.0
        self._preview_line: Optional[PriceLineItem] = None
        self._preview_line_id: Optional[str] = None

        # Callbacks
        self._on_stop_loss_created: Optional[Callable[[str, float], None]] = None
        self._on_take_profit_created: Optional[Callable[[str, float], None]] = None

    def set_callbacks(
        self,
        on_stop_loss_created: Optional[Callable[[str, float], None]] = None,
        on_take_profit_created: Optional[Callable[[str, float], None]] = None
    ) -> None:
        """
        Set callbacks for line creation.

        Args:
            on_stop_loss_created: Callback(stop_loss_line_id, price)
            on_take_profit_created: Callback(take_profit_line_id, price)
        """
        self._on_stop_loss_created = on_stop_loss_created
        self._on_take_profit_created = on_take_profit_created

    def start_drag_from_entry(
        self,
        entry_line: PriceLineItem,
        entry_line_id: str,
        start_price: float
    ) -> None:
        """
        Start dragging from entry line.

        Args:
            entry_line: Entry line item
            entry_line_id: Entry line ID
            start_price: Starting price (entry price)
        """
        if entry_line.get_line_type() != PriceLineType.ENTRY:
            return

        self._is_dragging_from_entry = True
        self._entry_line = entry_line
        self._entry_line_id = entry_line_id
        self._drag_start_price = start_price

    def update_drag(self, current_price: float) -> None:
        """
        Update drag position.

        Args:
            current_price: Current drag price
        """
        if not self._is_dragging_from_entry or self._entry_line is None:
            return

        direction = self._entry_line.get_direction()
        entry_price = self._entry_line.get_price()

        # Determine if creating stop loss or take profit
        if direction == "long":
            # Long: drag down = stop loss, drag up = take profit
            is_stop_loss = current_price < entry_price
        else:
            # Short: drag up = stop loss, drag down = take profit
            is_stop_loss = current_price > entry_price

        # Create or update preview line
        line_type = PriceLineType.STOP_LOSS if is_stop_loss else PriceLineType.TAKE_PROFIT

        if self._preview_line_id is None:
            # Create preview line
            self._preview_line_id = self._price_line_manager.create_line(
                price=current_price,
                line_type=line_type,
                direction=direction,
                movable=False
            )
            self._preview_line = self._price_line_manager.get_line(self._preview_line_id)
            if self._preview_line and self._plot:
                self._preview_line.setOpacity(0.5)  # Semi-transparent
                self._plot.addItem(self._preview_line)
        else:
            # Update preview line
            if self._preview_line:
                self._preview_line.set_price(current_price)
                # Update line type if changed
                if self._preview_line.get_line_type() != line_type:
                    # Need to recreate with new type
                    self._price_line_manager.delete_line(self._preview_line_id)
                    self._preview_line_id = self._price_line_manager.create_line(
                        price=current_price,
                        line_type=line_type,
                        direction=direction,
                        movable=False
                    )
                    self._preview_line = self._price_line_manager.get_line(self._preview_line_id)
                    if self._preview_line and self._plot:
                        self._preview_line.setOpacity(0.5)
                        self._plot.addItem(self._preview_line)

    def end_drag(self) -> Optional[tuple[str, float, str]]:
        """
        End drag and create the line.

        Returns:
            Tuple of (line_id, price, line_type) if created, None if cancelled
        """
        if not self._is_dragging_from_entry or self._entry_line is None:
            return None

        if self._preview_line is None:
            self._cancel_drag()
            return None

        # Get final price and type
        final_price = self._preview_line.get_price()
        line_type = self._preview_line.get_line_type()
        direction = self._entry_line.get_direction()

        # Remove preview line
        self._price_line_manager.delete_line(self._preview_line_id)
        self._preview_line_id = None
        self._preview_line = None

        # Create actual line
        line_id = self._price_line_manager.create_line(
            price=final_price,
            line_type=line_type,
            direction=direction,
            movable=True
        )

        # Add to plot
        line = self._price_line_manager.get_line(line_id)
        if line and self._plot:
            self._plot.addItem(line)

        # Reset drag state
        self._is_dragging_from_entry = False
        self._entry_line = None
        self._entry_line_id = None
        self._drag_start_price = 0.0

        # Call callbacks
        if line_type == PriceLineType.STOP_LOSS and self._on_stop_loss_created:
            self._on_stop_loss_created(line_id, final_price)
        elif line_type == PriceLineType.TAKE_PROFIT and self._on_take_profit_created:
            self._on_take_profit_created(line_id, final_price)

        return (line_id, final_price, line_type.value)

    def cancel_drag(self) -> None:
        """Cancel drag and remove preview line."""
        self._cancel_drag()

    def _cancel_drag(self) -> None:
        """Internal method to cancel drag."""
        if self._preview_line_id:
            self._price_line_manager.delete_line(self._preview_line_id)
            self._preview_line_id = None
            self._preview_line = None

        self._is_dragging_from_entry = False
        self._entry_line = None
        self._entry_line_id = None
        self._drag_start_price = 0.0

    def is_dragging_from_entry(self) -> bool:
        """Check if currently dragging from entry line."""
        return self._is_dragging_from_entry

    def get_entry_line_id(self) -> Optional[str]:
        """Get entry line ID being dragged from."""
        return self._entry_line_id

