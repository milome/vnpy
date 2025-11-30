"""
Four hour K-line overlay module.

Overlays 4-hour K-line data on the main chart for trend analysis.
"""

from typing import Optional, Callable
from datetime import datetime

import pyqtgraph as pg  # type: ignore

from vnpy.trader.ui import QtGui, QtCore
from vnpy.trader.object import BarData
from vnpy.trader.constant import Interval
from vnpy.trader.database import get_database

from .manager import BarManager
from .item import ChartItem
from .base import UP_COLOR, DOWN_COLOR, PEN_WIDTH, BAR_WIDTH


class FourHourOverlayItem(ChartItem):
    """
    Chart item for displaying 4-hour K-line overlay.
    
    Uses a different style (e.g., thicker lines, different colors) to distinguish
    from main K-line.
    """

    def __init__(self, manager: BarManager) -> None:
        """Initialize 4-hour overlay item."""
        super().__init__(manager)

        # Use different colors for overlay (lighter/more transparent)
        overlay_up_color = (*UP_COLOR[:3], 180)  # Add alpha
        overlay_down_color = (*DOWN_COLOR[:3], 180)

        self._overlay_up_pen: QtGui.QPen = pg.mkPen(
            color=overlay_up_color, width=PEN_WIDTH + 1
        )
        self._overlay_up_brush: QtGui.QBrush = pg.mkBrush(color=overlay_up_color)

        self._overlay_down_pen: QtGui.QPen = pg.mkPen(
            color=overlay_down_color, width=PEN_WIDTH + 1
        )
        self._overlay_down_brush: QtGui.QBrush = pg.mkBrush(color=overlay_down_color)

    def _draw_bar_picture(self, ix: int, bar: BarData) -> QtGui.QPicture:
        """Draw 4-hour bar picture."""
        # Create objects
        candle_picture: QtGui.QPicture = QtGui.QPicture()
        painter: QtGui.QPainter = QtGui.QPainter(candle_picture)

        # Set painter color (use overlay colors)
        if bar.close_price >= bar.open_price:
            painter.setPen(self._overlay_up_pen)
            painter.setBrush(self._overlay_up_brush)
        else:
            painter.setPen(self._overlay_down_pen)
            painter.setBrush(self._overlay_down_brush)

        # Draw candle shadow (thicker for 4-hour)
        if bar.high_price > bar.low_price:
            painter.drawLine(
                QtCore.QPointF(ix, bar.high_price),
                QtCore.QPointF(ix, bar.low_price)
            )

        # Draw candle body (wider for 4-hour)
        overlay_bar_width = BAR_WIDTH * 1.5
        if bar.open_price == bar.close_price:
            painter.drawLine(
                QtCore.QPointF(ix - overlay_bar_width, bar.open_price),
                QtCore.QPointF(ix + overlay_bar_width, bar.open_price),
            )
        else:
            rect: QtCore.QRectF = QtCore.QRectF(
                ix - overlay_bar_width,
                bar.open_price,
                overlay_bar_width * 2,
                bar.close_price - bar.open_price
            )
            painter.drawRect(rect)

        # Finish
        painter.end()
        return candle_picture

    def boundingRect(self) -> QtCore.QRectF:
        """Get bounding rectangle."""
        min_price, max_price = self._manager.get_price_range()
        rect: QtCore.QRectF = QtCore.QRectF(
            0,
            min_price,
            len(self._bar_picutures),
            max_price - min_price
        )
        return rect

    def get_y_range(self, min_ix: int | None = None, max_ix: int | None = None) -> tuple[float, float]:
        """Get Y-axis range."""
        return self._manager.get_price_range()

    def get_info_text(self, ix: int) -> str:
        """Get info text for cursor."""
        bar = self._manager.get_bar(ix)
        if bar is None:
            return ""

        return f"4H: O:{bar.open_price:.2f} H:{bar.high_price:.2f} L:{bar.low_price:.2f} C:{bar.close_price:.2f}"


class FourHourOverlay:
    """
    Manager for 4-hour K-line overlay.
    
    Loads and displays 4-hour K-line data on the main chart.
    """

    def __init__(
        self,
        widget: "ChartWidget",
        plot: pg.PlotItem,
        main_bar_manager: BarManager
    ) -> None:
        """
        Initialize 4-hour overlay.

        Args:
            widget: ChartWidget instance
            plot: PlotItem to add overlay to
            main_bar_manager: Main BarManager for time alignment
        """
        self._widget = widget
        self._plot = plot
        self._main_bar_manager = main_bar_manager

        # 4-hour bar manager and item
        self._four_hour_manager: BarManager = BarManager()
        self._four_hour_item: Optional[FourHourOverlayItem] = None

        # VT symbol
        self._vt_symbol: Optional[str] = None

        # Callback for data loading
        self._on_data_loaded: Optional[Callable[[int], None]] = None

    def set_vt_symbol(self, vt_symbol: str) -> None:
        """
        Set VT symbol for overlay.

        Args:
            vt_symbol: VT symbol (e.g., "MHI2512.HKFE")
        """
        self._vt_symbol = vt_symbol

    def set_on_data_loaded(self, callback: Callable[[int], None]) -> None:
        """
        Set callback for when data is loaded.

        Args:
            callback: Callback function(count) called with number of bars loaded
        """
        self._on_data_loaded = callback

    def load_four_hour_data(
        self,
        start: datetime,
        end: datetime
    ) -> bool:
        """
        Load 4-hour K-line data from database.

        Args:
            start: Start datetime
            end: End datetime

        Returns:
            True if successful, False otherwise
        """
        if not self._vt_symbol:
            return False

        try:
            from vnpy.trader.utility import extract_vt_symbol
            symbol, exchange = extract_vt_symbol(self._vt_symbol)

            # Get database
            database = get_database()

            # Load 4-hour bars
            bars = database.load_bar_data(
                symbol=symbol,
                exchange=exchange,
                interval=Interval.HOUR_4,
                start=start,
                end=end
            )

            if not bars:
                return False

            # Update 4-hour manager
            self._four_hour_manager.update_history(bars)

            # Create or update overlay item
            if self._four_hour_item is None:
                self._four_hour_item = FourHourOverlayItem(self._four_hour_manager)
                self._plot.addItem(self._four_hour_item)
            else:
                self._four_hour_item.update_history(bars)

            # Call callback
            if self._on_data_loaded:
                self._on_data_loaded(len(bars))

            return True

        except Exception as e:
            print(f"Error loading 4-hour data: {e}")
            return False

    def update_four_hour_bar(self, bar: BarData) -> None:
        """
        Update with new 4-hour bar.

        Args:
            bar: New 4-hour bar data
        """
        if self._four_hour_item is None:
            return

        self._four_hour_manager.update_bar(bar)
        self._four_hour_item.update_bar(bar)

    def show(self) -> None:
        """Show 4-hour overlay."""
        if self._four_hour_item:
            self._four_hour_item.setVisible(True)

    def hide(self) -> None:
        """Hide 4-hour overlay."""
        if self._four_hour_item:
            self._four_hour_item.setVisible(False)

    def is_visible(self) -> bool:
        """Check if overlay is visible."""
        if self._four_hour_item:
            return self._four_hour_item.isVisible()
        return False

    def toggle(self) -> None:
        """Toggle overlay visibility."""
        if self.is_visible():
            self.hide()
        else:
            self.show()

    def clear(self) -> None:
        """Clear 4-hour overlay data."""
        if self._four_hour_item:
            self._four_hour_item.clear_all()
        self._four_hour_manager.clear_all()

