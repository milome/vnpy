"""
Price line management module for vnpy chart.

This module provides price line functionality for drawing order trading,
including price line display, drag interaction, and order management.
"""

from enum import Enum
from typing import Optional

import pyqtgraph as pg  # type: ignore

from vnpy.trader.ui import QtGui, QtCore

from .base import UP_COLOR, DOWN_COLOR, PEN_WIDTH, NORMAL_FONT


class PriceLineType(Enum):
    """Price line type enumeration."""

    ENTRY = "entry"           # 入场线（已成交）
    PENDING = "pending"       # 挂单线（未成交）
    STOP_LOSS = "stop_loss"   # 止损线
    TAKE_PROFIT = "take_profit"  # 止盈线
    PREVIEW = "preview"       # 预览线（临时显示）


class PriceLineItem(pg.InfiniteLine):
    """
    Price line item based on pyqtgraph InfiniteLine.
    
    Supports horizontal price line display with customizable style.
    """

    def __init__(
        self,
        price: float,
        line_type: PriceLineType,
        direction: str = "long",
        movable: bool = False,
        parent: Optional[pg.GraphicsObject] = None
    ) -> None:
        """
        Initialize price line item.

        Args:
            price: Price value for the line
            line_type: Type of price line (ENTRY, PENDING, etc.)
            direction: Trading direction ("long" or "short")
            movable: Whether the line can be dragged
            parent: Parent graphics object
        """
        # Create pen based on line type and direction
        pen = self._create_pen(line_type, direction)
        
        # Create label text (默认整数显示，MHImain)
        label = self._create_label(price, line_type, price_precision=0)
        
        # Initialize InfiniteLine (angle=0 for horizontal line)
        # Note: labelOpts doesn't support 'font' parameter directly
        # Font can be set after creation if needed
        super().__init__(
            angle=0,
            pos=price,
            pen=pen,
            movable=movable,
            label=label,
            labelOpts={
                "position": 0.95,
                "color": pen.color()
            }
        )
        
        # Set font for label after creation
        if self.label is not None:
            self.label.setFont(NORMAL_FONT)
        
        self._price: float = price
        self._line_type: PriceLineType = line_type
        self._direction: str = direction
        self._original_price: float = price

    def _create_pen(
        self,
        line_type: PriceLineType,
        direction: str
    ) -> QtGui.QPen:
        """
        Create pen for price line based on type and direction.

        Args:
            line_type: Type of price line
            direction: Trading direction

        Returns:
            QPen object with appropriate style
        """
        # Determine color based on direction (红涨青跌，中国惯例)
        if direction == "long":
            base_color = UP_COLOR  # Red for long
        else:
            base_color = DOWN_COLOR  # Cyan for short

        # Determine line style and color based on type
        if line_type == PriceLineType.ENTRY:
            # Entry line: solid
            style = QtCore.Qt.PenStyle.SolidLine
            width = PEN_WIDTH + 1
            color = base_color
        elif line_type == PriceLineType.PENDING:
            # Pending order line: dotted
            style = QtCore.Qt.PenStyle.DotLine
            width = PEN_WIDTH
            color = base_color
        elif line_type == PriceLineType.STOP_LOSS:
            # Stop loss: dashed, orange color (警告色)
            style = QtCore.Qt.PenStyle.DashLine
            width = PEN_WIDTH
            color = (255, 165, 0)  # Orange color for stop loss
        elif line_type == PriceLineType.TAKE_PROFIT:
            # Take profit: dashed, green color (盈利色)
            style = QtCore.Qt.PenStyle.DashLine
            width = PEN_WIDTH
            color = (0, 255, 0)  # Green color for take profit
        elif line_type == PriceLineType.PREVIEW:
            # Preview line: dotted, semi-transparent
            style = QtCore.Qt.PenStyle.DotLine
            width = PEN_WIDTH
            # Make preview line semi-transparent
            color = (*base_color[:3], 128)  # Add alpha channel
            return pg.mkPen(color=color, width=width, style=style)
        else:
            style = QtCore.Qt.PenStyle.SolidLine
            width = PEN_WIDTH
            color = base_color

        return pg.mkPen(color=color, width=width, style=style)

    def _create_label(
        self,
        price: float,
        line_type: PriceLineType,
        price_precision: int = 0
    ) -> str:
        """
        Create label text for price line.

        Args:
            price: Price value
            line_type: Type of price line
            price_precision: Number of decimal places (0 for integer, default 0 for MHImain)

        Returns:
            Label text string
        """
        type_names = {
            PriceLineType.ENTRY: "入场",
            PriceLineType.PENDING: "挂单",
            PriceLineType.STOP_LOSS: "止损",
            PriceLineType.TAKE_PROFIT: "止盈",
            PriceLineType.PREVIEW: "预览"
        }
        
        type_name = type_names.get(line_type, "")
        # 根据精度格式化价格（0表示整数，MHImain默认显示整数）
        if price_precision == 0:
            return f"{type_name} {int(price)}"
        else:
            return f"{type_name} {price:.{price_precision}f}"

    def get_price(self) -> float:
        """Get current price of the line."""
        return self._price

    def set_price(self, price: float, price_precision: int = 0) -> None:
        """
        Update price of the line.

        Args:
            price: New price value
            price_precision: Number of decimal places (0 for integer, default 0 for MHImain)
        """
        self._price = price
        self.setPos(price)
        # Update label
        if self.label is not None:
            label_text = self._create_label(price, self._line_type, price_precision)
            self.label.setText(label_text)
    
    def set_price_precision(self, precision: int) -> None:
        """Set price precision and update label."""
        if self.label is not None:
            label_text = self._create_label(self._price, self._line_type, precision)
            self.label.setText(label_text)

    def get_line_type(self) -> PriceLineType:
        """Get line type."""
        return self._line_type

    def get_direction(self) -> str:
        """Get trading direction."""
        return self._direction

    def get_original_price(self) -> float:
        """Get original price (before drag)."""
        return self._original_price

    def set_original_price(self, price: float) -> None:
        """Set original price (for drag cancel)."""
        self._original_price = price


class PriceLineManager:
    """
    Manager for all price lines in the chart.
    
    Handles creation, update, and deletion of price lines.
    """

    def __init__(self) -> None:
        """Initialize price line manager."""
        # Map: line_id -> PriceLineItem
        self._lines: dict[str, PriceLineItem] = {}
        
        # Counter for generating unique line IDs
        self._line_id_counter: int = 0

    def create_line(
        self,
        price: float,
        line_type: PriceLineType,
        direction: str = "long",
        movable: bool = False,
        line_id: Optional[str] = None,
        price_precision: Optional[int] = None
    ) -> str:
        """
        Create a new price line.

        Args:
            price: Price value
            line_type: Type of price line
            direction: Trading direction ("long" or "short")
            movable: Whether the line can be dragged
            line_id: Optional custom line ID. If None, auto-generate.

        Returns:
            Line ID string
        """
        if line_id is None:
            line_id = f"line_{self._line_id_counter}"
            self._line_id_counter += 1

        if line_id in self._lines:
            raise ValueError(f"Line ID {line_id} already exists")

        line = PriceLineItem(
            price=price,
            line_type=line_type,
            direction=direction,
            movable=movable
        )
        
        # 设置价格精度（如果提供了，否则使用默认值0）
        if price_precision is not None:
            line.set_price_precision(price_precision)
        else:
            line.set_price_precision(0)  # 默认整数显示

        self._lines[line_id] = line
        return line_id

    def get_line(self, line_id: str) -> Optional[PriceLineItem]:
        """
        Get price line by ID.

        Args:
            line_id: Line ID

        Returns:
            PriceLineItem or None if not found
        """
        return self._lines.get(line_id)

    def update_line_price(self, line_id: str, price: float) -> bool:
        """
        Update price of a line.

        Args:
            line_id: Line ID
            price: New price value

        Returns:
            True if successful, False if line not found
        """
        line = self._lines.get(line_id)
        if line is None:
            return False

        line.set_price(price)
        return True

    def delete_line(self, line_id: str) -> bool:
        """
        Delete a price line.

        Args:
            line_id: Line ID

        Returns:
            True if successful, False if line not found
        """
        line = self._lines.pop(line_id, None)
        if line is None:
            return False

        # Remove from plot if it has a parent
        if line.scene() is not None:
            plot = line.getViewBox()
            if plot is not None:
                plot.removeItem(line)

        return True

    def get_all_lines(self) -> dict[str, PriceLineItem]:
        """
        Get all price lines.

        Returns:
            Dictionary mapping line_id to PriceLineItem
        """
        return self._lines.copy()

    def get_lines_by_type(self, line_type: PriceLineType) -> list[PriceLineItem]:
        """
        Get all lines of a specific type.

        Args:
            line_type: Type of price line

        Returns:
            List of PriceLineItem objects
        """
        return [
            line for line in self._lines.values()
            if line.get_line_type() == line_type
        ]

    def clear_all(self) -> None:
        """Clear all price lines."""
        # Remove all lines from their plots
        for line in list(self._lines.values()):
            if line.scene() is not None:
                plot = line.getViewBox()
                if plot is not None:
                    plot.removeItem(line)

        self._lines.clear()

    def get_count(self) -> int:
        """Get total number of price lines."""
        return len(self._lines)

