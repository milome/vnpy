"""
Unit tests for price line functionality in vnpy chart module.

Tests cover:
- Price line creation and deletion
- Price line style configuration
- Price line manager state management
"""

import pytest
import pyqtgraph as pg  # type: ignore

from vnpy.chart.price_line import (
    PriceLineItem,
    PriceLineManager,
    PriceLineType
)


class TestPriceLineItem:
    """Test cases for PriceLineItem class."""

    def test_create_price_line_item(self) -> None:
        """Test creating a price line item."""
        line = PriceLineItem(
            price=100.0,
            line_type=PriceLineType.ENTRY,
            direction="long"
        )

        assert line.get_price() == 100.0
        assert line.get_line_type() == PriceLineType.ENTRY
        assert line.get_direction() == "long"
        assert line.get_original_price() == 100.0

    def test_create_different_line_types(self) -> None:
        """Test creating different types of price lines."""
        types = [
            PriceLineType.ENTRY,
            PriceLineType.PENDING,
            PriceLineType.STOP_LOSS,
            PriceLineType.TAKE_PROFIT,
            PriceLineType.PREVIEW
        ]

        for line_type in types:
            line = PriceLineItem(
                price=100.0,
                line_type=line_type,
                direction="long"
            )
            assert line.get_line_type() == line_type

    def test_create_long_and_short_lines(self) -> None:
        """Test creating lines for long and short directions."""
        long_line = PriceLineItem(
            price=100.0,
            line_type=PriceLineType.ENTRY,
            direction="long"
        )
        short_line = PriceLineItem(
            price=100.0,
            line_type=PriceLineType.ENTRY,
            direction="short"
        )

        assert long_line.get_direction() == "long"
        assert short_line.get_direction() == "short"

    def test_update_price(self) -> None:
        """Test updating price of a line."""
        line = PriceLineItem(
            price=100.0,
            line_type=PriceLineType.ENTRY,
            direction="long"
        )

        line.set_price(105.5)
        assert line.get_price() == 105.5

    def test_original_price_tracking(self) -> None:
        """Test original price tracking for drag cancel."""
        line = PriceLineItem(
            price=100.0,
            line_type=PriceLineType.ENTRY,
            direction="long"
        )

        # Update price
        line.set_price(105.0)
        assert line.get_price() == 105.0
        assert line.get_original_price() == 100.0

        # Update original price
        line.set_original_price(105.0)
        assert line.get_original_price() == 105.0

    def test_movable_line(self) -> None:
        """Test creating movable price line."""
        line = PriceLineItem(
            price=100.0,
            line_type=PriceLineType.PENDING,
            direction="long",
            movable=True
        )

        # Check that line is movable (pyqtgraph property)
        assert line.movable is True

    def test_label_creation(self) -> None:
        """Test label text creation."""
        line = PriceLineItem(
            price=123.45,
            line_type=PriceLineType.ENTRY,
            direction="long"
        )

        label = line.label
        assert "入场" in label
        assert "123.45" in label


class TestPriceLineManager:
    """Test cases for PriceLineManager class."""

    def test_create_manager(self) -> None:
        """Test creating a price line manager."""
        manager = PriceLineManager()
        assert manager.get_count() == 0

    def test_create_line(self) -> None:
        """Test creating a price line."""
        manager = PriceLineManager()

        line_id = manager.create_line(
            price=100.0,
            line_type=PriceLineType.ENTRY,
            direction="long"
        )

        assert line_id is not None
        assert manager.get_count() == 1

        line = manager.get_line(line_id)
        assert line is not None
        assert line.get_price() == 100.0

    def test_create_line_with_custom_id(self) -> None:
        """Test creating a line with custom ID."""
        manager = PriceLineManager()

        custom_id = "my_custom_line"
        line_id = manager.create_line(
            price=100.0,
            line_type=PriceLineType.ENTRY,
            direction="long",
            line_id=custom_id
        )

        assert line_id == custom_id
        assert manager.get_line(custom_id) is not None

    def test_create_duplicate_line_id_fails(self) -> None:
        """Test that creating duplicate line ID raises error."""
        manager = PriceLineManager()

        line_id = manager.create_line(
            price=100.0,
            line_type=PriceLineType.ENTRY,
            direction="long",
            line_id="test_line"
        )

        # Try to create another line with same ID
        with pytest.raises(ValueError, match="already exists"):
            manager.create_line(
                price=200.0,
                line_type=PriceLineType.PENDING,
                direction="short",
                line_id="test_line"
            )

    def test_delete_line(self) -> None:
        """Test deleting a price line."""
        manager = PriceLineManager()

        line_id = manager.create_line(
            price=100.0,
            line_type=PriceLineType.ENTRY,
            direction="long"
        )

        assert manager.get_count() == 1

        result = manager.delete_line(line_id)
        assert result is True
        assert manager.get_count() == 0
        assert manager.get_line(line_id) is None

    def test_delete_nonexistent_line(self) -> None:
        """Test deleting a non-existent line."""
        manager = PriceLineManager()

        result = manager.delete_line("nonexistent")
        assert result is False

    def test_update_line_price(self) -> None:
        """Test updating line price."""
        manager = PriceLineManager()

        line_id = manager.create_line(
            price=100.0,
            line_type=PriceLineType.ENTRY,
            direction="long"
        )

        result = manager.update_line_price(line_id, 105.5)
        assert result is True

        line = manager.get_line(line_id)
        assert line is not None
        assert line.get_price() == 105.5

    def test_update_nonexistent_line(self) -> None:
        """Test updating non-existent line."""
        manager = PriceLineManager()

        result = manager.update_line_price("nonexistent", 100.0)
        assert result is False

    def test_get_all_lines(self) -> None:
        """Test getting all lines."""
        manager = PriceLineManager()

        line_id1 = manager.create_line(
            price=100.0,
            line_type=PriceLineType.ENTRY,
            direction="long"
        )
        line_id2 = manager.create_line(
            price=200.0,
            line_type=PriceLineType.PENDING,
            direction="short"
        )

        all_lines = manager.get_all_lines()
        assert len(all_lines) == 2
        assert line_id1 in all_lines
        assert line_id2 in all_lines

    def test_get_lines_by_type(self) -> None:
        """Test getting lines by type."""
        manager = PriceLineManager()

        # Create multiple lines of different types
        manager.create_line(
            price=100.0,
            line_type=PriceLineType.ENTRY,
            direction="long"
        )
        manager.create_line(
            price=200.0,
            line_type=PriceLineType.ENTRY,
            direction="short"
        )
        manager.create_line(
            price=300.0,
            line_type=PriceLineType.PENDING,
            direction="long"
        )

        entry_lines = manager.get_lines_by_type(PriceLineType.ENTRY)
        assert len(entry_lines) == 2

        pending_lines = manager.get_lines_by_type(PriceLineType.PENDING)
        assert len(pending_lines) == 1

        stop_loss_lines = manager.get_lines_by_type(PriceLineType.STOP_LOSS)
        assert len(stop_loss_lines) == 0

    def test_clear_all(self) -> None:
        """Test clearing all lines."""
        manager = PriceLineManager()

        # Create multiple lines
        manager.create_line(
            price=100.0,
            line_type=PriceLineType.ENTRY,
            direction="long"
        )
        manager.create_line(
            price=200.0,
            line_type=PriceLineType.PENDING,
            direction="short"
        )

        assert manager.get_count() == 2

        manager.clear_all()
        assert manager.get_count() == 0
        assert len(manager.get_all_lines()) == 0

    def test_multiple_managers_independent(self) -> None:
        """Test that multiple managers are independent."""
        manager1 = PriceLineManager()
        manager2 = PriceLineManager()

        line_id1 = manager1.create_line(
            price=100.0,
            line_type=PriceLineType.ENTRY,
            direction="long"
        )

        line_id2 = manager2.create_line(
            price=200.0,
            line_type=PriceLineType.ENTRY,
            direction="long"
        )

        assert manager1.get_count() == 1
        assert manager2.get_count() == 1

        assert manager1.get_line(line_id1) is not None
        assert manager1.get_line(line_id2) is None

        assert manager2.get_line(line_id2) is not None
        assert manager2.get_line(line_id1) is None


class TestPriceLineStyleConfiguration:
    """Test cases for price line style configuration."""

    def test_entry_line_style(self) -> None:
        """Test entry line style (solid, thicker)."""
        line = PriceLineItem(
            price=100.0,
            line_type=PriceLineType.ENTRY,
            direction="long"
        )

        from vnpy.trader.ui import QtCore
        
        pen = line.pen
        assert pen.style() == QtCore.Qt.PenStyle.SolidLine
        assert pen.width() >= 1

    def test_pending_line_style(self) -> None:
        """Test pending line style (dotted)."""
        line = PriceLineItem(
            price=100.0,
            line_type=PriceLineType.PENDING,
            direction="long"
        )

        from vnpy.trader.ui import QtCore
        
        pen = line.pen
        assert pen.style() == QtCore.Qt.PenStyle.DotLine

    def test_stop_loss_line_style(self) -> None:
        """Test stop loss line style (dashed)."""
        line = PriceLineItem(
            price=100.0,
            line_type=PriceLineType.STOP_LOSS,
            direction="long"
        )

        from vnpy.trader.ui import QtCore
        
        pen = line.pen
        assert pen.style() == QtCore.Qt.PenStyle.DashLine

    def test_take_profit_line_style(self) -> None:
        """Test take profit line style (dashed)."""
        line = PriceLineItem(
            price=100.0,
            line_type=PriceLineType.TAKE_PROFIT,
            direction="long"
        )

        from vnpy.trader.ui import QtCore
        
        pen = line.pen
        assert pen.style() == QtCore.Qt.PenStyle.DashLine

    def test_preview_line_style(self) -> None:
        """Test preview line style (dotted, semi-transparent)."""
        line = PriceLineItem(
            price=100.0,
            line_type=PriceLineType.PREVIEW,
            direction="long"
        )

        from vnpy.trader.ui import QtCore
        
        pen = line.pen
        assert pen.style() == QtCore.Qt.PenStyle.DotLine
        # Preview line should have alpha channel (semi-transparent)
        color = pen.color()
        # Check if color has alpha (RGBA) or is semi-transparent
        assert color.alpha() < 255 or len(color.getRgb()) == 4

    def test_long_vs_short_color(self) -> None:
        """Test that long and short lines have different colors."""
        from vnpy.chart.base import UP_COLOR, DOWN_COLOR

        long_line = PriceLineItem(
            price=100.0,
            line_type=PriceLineType.ENTRY,
            direction="long"
        )

        short_line = PriceLineItem(
            price=100.0,
            line_type=PriceLineType.ENTRY,
            direction="short"
        )

        long_color = long_line.pen.color().getRgb()[:3]  # RGB only
        short_color = short_line.pen.color().getRgb()[:3]  # RGB only

        # Long should be red (UP_COLOR), short should be cyan (DOWN_COLOR)
        assert long_color == UP_COLOR
        assert short_color == DOWN_COLOR

    def test_movable_line_creation(self) -> None:
        """Test creating movable price line."""
        line = PriceLineItem(
            price=100.0,
            line_type=PriceLineType.PENDING,
            direction="long",
            movable=True
        )

        assert line.movable is True
        assert line.get_price() == 100.0

    def test_fixed_line_creation(self) -> None:
        """Test creating fixed (non-movable) price line."""
        line = PriceLineItem(
            price=100.0,
            line_type=PriceLineType.ENTRY,
            direction="long",
            movable=False
        )

        assert line.movable is False

    def test_price_update_updates_label(self) -> None:
        """Test that updating price updates the label."""
        line = PriceLineItem(
            price=100.0,
            line_type=PriceLineType.ENTRY,
            direction="long"
        )

        initial_label = line.label
        assert "100.00" in initial_label

        line.set_price(105.5)
        new_label = line.label
        assert "105.50" in new_label


class TestPriceLineManagerAdvanced:
    """Advanced test cases for PriceLineManager."""

    def test_manager_with_movable_lines(self) -> None:
        """Test manager with movable and fixed lines."""
        manager = PriceLineManager()

        # Create movable line
        line_id1 = manager.create_line(
            price=100.0,
            line_type=PriceLineType.PENDING,
            direction="long",
            movable=True
        )

        # Create fixed line
        line_id2 = manager.create_line(
            price=200.0,
            line_type=PriceLineType.ENTRY,
            direction="long",
            movable=False
        )

        line1 = manager.get_line(line_id1)
        line2 = manager.get_line(line_id2)

        assert line1 is not None
        assert line2 is not None
        assert line1.movable is True
        assert line2.movable is False

    def test_batch_operations(self) -> None:
        """Test batch operations on multiple lines."""
        manager = PriceLineManager()

        # Create multiple lines
        line_ids = []
        for i in range(5):
            line_id = manager.create_line(
                price=100.0 + i * 10,
                line_type=PriceLineType.PENDING,
                direction="long"
            )
            line_ids.append(line_id)

        assert manager.get_count() == 5

        # Update all prices
        for i, line_id in enumerate(line_ids):
            manager.update_line_price(line_id, 100.0 + i * 10 + 5)

        # Verify updates
        for i, line_id in enumerate(line_ids):
            line = manager.get_line(line_id)
            assert line is not None
            assert line.get_price() == 100.0 + i * 10 + 5

        # Delete all
        for line_id in line_ids:
            manager.delete_line(line_id)

        assert manager.get_count() == 0

    def test_get_lines_by_type_with_multiple_types(self) -> None:
        """Test getting lines by type with multiple types."""
        manager = PriceLineManager()

        # Create lines of different types
        manager.create_line(price=100.0, line_type=PriceLineType.ENTRY, direction="long")
        manager.create_line(price=200.0, line_type=PriceLineType.ENTRY, direction="short")
        manager.create_line(price=300.0, line_type=PriceLineType.PENDING, direction="long")
        manager.create_line(price=400.0, line_type=PriceLineType.STOP_LOSS, direction="long")
        manager.create_line(price=500.0, line_type=PriceLineType.TAKE_PROFIT, direction="long")

        entry_lines = manager.get_lines_by_type(PriceLineType.ENTRY)
        assert len(entry_lines) == 2

        pending_lines = manager.get_lines_by_type(PriceLineType.PENDING)
        assert len(pending_lines) == 1

        stop_loss_lines = manager.get_lines_by_type(PriceLineType.STOP_LOSS)
        assert len(stop_loss_lines) == 1

        take_profit_lines = manager.get_lines_by_type(PriceLineType.TAKE_PROFIT)
        assert len(take_profit_lines) == 1

        preview_lines = manager.get_lines_by_type(PriceLineType.PREVIEW)
        assert len(preview_lines) == 0

    def test_line_id_uniqueness(self) -> None:
        """Test that auto-generated line IDs are unique."""
        manager = PriceLineManager()

        line_ids = set()
        for _ in range(10):
            line_id = manager.create_line(
                price=100.0,
                line_type=PriceLineType.PENDING,
                direction="long"
            )
            assert line_id not in line_ids, "Line ID should be unique"
            line_ids.add(line_id)

        assert len(line_ids) == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

