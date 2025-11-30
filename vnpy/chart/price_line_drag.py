"""
Price line drag interaction module.

Handles mouse hover detection, drag state management, and ESC cancel mechanism
for draggable price lines.
"""

from typing import Optional

import pyqtgraph as pg  # type: ignore

from vnpy.trader.ui import QtCore, QtGui, QtWidgets

from .price_line import PriceLineItem, PriceLineType


# Default hover detection threshold (pixels)
DEFAULT_HOVER_THRESHOLD = 10


class PriceLineDragHandler:
    """
    Handler for price line drag interactions.
    
    Manages hover detection, drag state, and coordinate conversion.
    """

    def __init__(self, plot: pg.PlotItem) -> None:
        """
        Initialize drag handler.

        Args:
            plot: PlotItem where price lines are displayed
        """
        self._plot: pg.PlotItem = plot
        self._hover_threshold: float = DEFAULT_HOVER_THRESHOLD
        
        # Drag state
        self._is_dragging: bool = False
        self._dragging_line: Optional[PriceLineItem] = None
        self._drag_start_price: float = 0.0
        
        # Entry line drag state (for creating stop loss/take profit)
        self._is_dragging_from_entry: bool = False
        self._entry_line: Optional[PriceLineItem] = None
        self._preview_line: Optional[PriceLineItem] = None

    def set_hover_threshold(self, threshold: float) -> None:
        """
        Set hover detection threshold in pixels.

        Args:
            threshold: Distance in pixels to detect hover
        """
        self._hover_threshold = threshold

    def find_line_near_point(
        self,
        pos: QtCore.QPointF,
        lines: list[PriceLineItem],
        include_entry_lines: bool = False
    ) -> Optional[PriceLineItem]:
        """
        Find price line near the given point.

        Args:
            pos: Mouse position in scene coordinates
            lines: List of price lines to check
            include_entry_lines: If True, also check entry lines (even if not movable)

        Returns:
            PriceLineItem if found, None otherwise
        """
        view_box = self._plot.getViewBox()
        if view_box is None:
            return None

        # Convert scene position to view coordinates
        view_pos = view_box.mapSceneToView(pos)
        
        # Get Y coordinate (price)
        mouse_price = view_pos.y()

        # Find the closest line
        closest_line: Optional[PriceLineItem] = None
        min_distance = float('inf')

        for line in lines:
            # Check if line should be considered
            if not include_entry_lines and not line.movable:
                continue
            
            # If including entry lines, check if it's an entry line
            if include_entry_lines and not line.movable:
                if line.get_line_type() != PriceLineType.ENTRY:
                    continue

            line_price = line.get_price()
            distance = abs(mouse_price - line_price)

            # Convert price distance to pixels
            # Get view range to calculate pixel-to-price ratio
            view_range = view_box.viewRange()
            if view_range:
                y_range = view_range[1]  # (y_min, y_max)
                y_height = y_range[1] - y_range[0]
                
                # Get plot height in pixels
                plot_height = view_box.height()
                if plot_height > 0:
                    price_per_pixel = y_height / plot_height
                    distance_pixels = distance / price_per_pixel

                    if distance_pixels < self._hover_threshold and distance_pixels < min_distance:
                        min_distance = distance_pixels
                        closest_line = line

        return closest_line

    def start_drag(self, line: PriceLineItem) -> None:
        """
        Start dragging a price line.

        Args:
            line: Price line to drag
        """
        if not line.movable:
            return

        self._is_dragging = True
        self._dragging_line = line
        self._drag_start_price = line.get_price()
        line.set_original_price(self._drag_start_price)
    
    def start_drag_from_entry(self, entry_line: PriceLineItem) -> None:
        """
        Start dragging from an entry line to create stop loss/take profit line.

        Args:
            entry_line: Entry line to drag from
        """
        if entry_line.get_line_type() != PriceLineType.ENTRY:
            return
        
        self._is_dragging_from_entry = True
        self._entry_line = entry_line
        self._drag_start_price = entry_line.get_price()

    def update_drag(self, new_price: float) -> None:
        """
        Update drag position.

        Args:
            new_price: New price value
        """
        # Handle entry line drag
        if self._is_dragging_from_entry:
            if self._preview_line:
                self._preview_line.set_price(new_price)
            return
        
        # Handle normal drag
        if not self._is_dragging or self._dragging_line is None:
            return

        self._dragging_line.set_price(new_price)

    def end_drag(self) -> Optional[float]:
        """
        End dragging and return final price.

        Returns:
            Final price if drag was active, None otherwise
        """
        # Handle entry line drag
        if self._is_dragging_from_entry:
            final_price = None
            if self._preview_line:
                final_price = self._preview_line.get_price()
            
            # Clear preview line
            if self._preview_line:
                # Remove preview line from plot if it exists
                if self._preview_line.scene() is not None:
                    view_box = self._plot.getViewBox()
                    if view_box:
                        view_box.removeItem(self._preview_line)
                self._preview_line = None
            
            self._is_dragging_from_entry = False
            self._entry_line = None
            self._drag_start_price = 0.0
            
            return final_price
        
        # Handle normal drag
        if not self._is_dragging or self._dragging_line is None:
            return None

        final_price = self._dragging_line.get_price()
        self._is_dragging = False
        self._dragging_line = None
        self._drag_start_price = 0.0

        return final_price

    def cancel_drag(self) -> bool:
        """
        Cancel drag and restore original price.

        Returns:
            True if drag was cancelled, False if no drag was active
        """
        # Handle entry line drag cancellation
        if self._is_dragging_from_entry:
            # Remove preview line
            if self._preview_line:
                if self._preview_line.scene() is not None:
                    view_box = self._plot.getViewBox()
                    if view_box:
                        view_box.removeItem(self._preview_line)
                self._preview_line = None
            
            self._is_dragging_from_entry = False
            self._entry_line = None
            self._drag_start_price = 0.0
            return True
        
        # Handle normal drag cancellation
        if not self._is_dragging or self._dragging_line is None:
            return False

        # Restore original price
        original_price = self._dragging_line.get_original_price()
        self._dragging_line.set_price(original_price)

        # Clear drag state
        self._is_dragging = False
        self._dragging_line = None
        self._drag_start_price = 0.0

        return True

    def is_dragging(self) -> bool:
        """Check if currently dragging."""
        return self._is_dragging or self._is_dragging_from_entry
    
    def is_dragging_from_entry(self) -> bool:
        """Check if currently dragging from entry line."""
        return self._is_dragging_from_entry
    
    def get_entry_line(self) -> Optional[PriceLineItem]:
        """Get entry line being dragged from."""
        return self._entry_line
    
    def set_preview_line(self, preview_line: Optional[PriceLineItem]) -> None:
        """Set preview line for entry drag."""
        self._preview_line = preview_line
    
    def get_preview_line(self) -> Optional[PriceLineItem]:
        """Get preview line."""
        return self._preview_line

    def get_dragging_line(self) -> Optional[PriceLineItem]:
        """Get currently dragging line."""
        return self._dragging_line

    def convert_scene_to_price(self, scene_pos: QtCore.QPointF) -> Optional[float]:
        """
        Convert scene coordinates to price value.

        Args:
            scene_pos: Position in scene coordinates

        Returns:
            Price value or None if conversion fails
        """
        view_box = self._plot.getViewBox()
        if view_box is None:
            return None

        view_pos = view_box.mapSceneToView(scene_pos)
        return view_pos.y()

    def convert_price_to_scene(self, price: float) -> Optional[QtCore.QPointF]:
        """
        Convert price value to scene coordinates.

        Args:
            price: Price value

        Returns:
            Scene position or None if conversion fails
        """
        view_box = self._plot.getViewBox()
        if view_box is None:
            return None

        # Use current x position (middle of view)
        view_range = view_box.viewRange()
        if not view_range:
            return None

        x_range = view_range[0]
        x_center = (x_range[0] + x_range[1]) / 2

        view_pos = QtCore.QPointF(x_center, price)
        scene_pos = view_box.mapViewToScene(view_pos)

        return scene_pos

