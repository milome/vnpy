"""
Integration tests for ChartWidget with price line functionality.

Tests cover:
- ChartWidget integration with price lines
- Price line addition and removal
- Plot integration
- Widget-level operations
"""

import pytest
import pyqtgraph as pg  # type: ignore

from vnpy.trader.ui import QtWidgets
from vnpy.trader.object import BarData
from datetime import datetime

from vnpy.chart.widget import ChartWidget
from vnpy.chart.price_line import PriceLineType


class TestChartWidgetPriceLineIntegration:
    """Integration tests for ChartWidget with price lines."""

    @pytest.fixture
    def widget(self) -> ChartWidget:
        """Create a ChartWidget instance."""
        return ChartWidget()

    @pytest.fixture
    def sample_bar(self) -> BarData:
        """Create a sample BarData for testing."""
        return BarData(
            symbol="rb2501",
            exchange="SHFE",
            datetime=datetime(2025, 1, 15, 9, 0),
            interval=None,
            volume=1000,
            open_price=100.0,
            high_price=105.0,
            low_price=95.0,
            close_price=102.0,
            gateway_name="test"
        )

    def test_widget_has_price_line_manager(self, widget: ChartWidget) -> None:
        """Test that widget has price line manager."""
        manager = widget.get_price_line_manager()
        assert manager is not None
        assert manager.get_count() == 0

    def test_add_plot_initializes_drag_handler(self, widget: ChartWidget) -> None:
        """Test that adding plot initializes drag handler."""
        widget.add_plot("test_plot")

        assert widget._price_line_drag_handler is not None

    def test_add_price_line_to_plot(self, widget: ChartWidget) -> None:
        """Test adding price line to a plot."""
        widget.add_plot("candle")

        line_id = widget.add_price_line(
            price=100.0,
            line_type="entry",
            direction="long",
            plot_name="candle"
        )

        assert line_id is not None
        line = widget.get_price_line_manager().get_line(line_id)
        assert line is not None
        assert line.get_price() == 100.0

    def test_add_price_line_to_first_plot(self, widget: ChartWidget) -> None:
        """Test adding price line to first plot when plot_name is None."""
        widget.add_plot("candle")

        line_id = widget.add_price_line(
            price=100.0,
            line_type="pending",
            direction="long"
        )

        assert line_id is not None
        line = widget.get_price_line_manager().get_line(line_id)
        assert line is not None

    def test_add_price_line_invalid_plot(self, widget: ChartWidget) -> None:
        """Test adding price line to non-existent plot raises error."""
        widget.add_plot("candle")

        with pytest.raises(ValueError, match="not found"):
            widget.add_price_line(
                price=100.0,
                line_type="entry",
                direction="long",
                plot_name="nonexistent"
            )

    def test_remove_price_line(self, widget: ChartWidget) -> None:
        """Test removing price line from widget."""
        widget.add_plot("candle")

        line_id = widget.add_price_line(
            price=100.0,
            line_type="pending",
            direction="long"
        )

        result = widget.remove_price_line(line_id)
        assert result is True

        line = widget.get_price_line_manager().get_line(line_id)
        assert line is None

    def test_remove_nonexistent_price_line(self, widget: ChartWidget) -> None:
        """Test removing non-existent price line."""
        widget.add_plot("candle")

        result = widget.remove_price_line("nonexistent")
        assert result is False

    def test_clear_all_clears_price_lines(self, widget: ChartWidget) -> None:
        """Test that clear_all clears price lines."""
        widget.add_plot("candle")

        # Add multiple lines
        widget.add_price_line(price=100.0, line_type="entry", direction="long")
        widget.add_price_line(price=200.0, line_type="pending", direction="short")
        widget.add_price_line(price=300.0, line_type="stop_loss", direction="long")

        assert widget.get_price_line_manager().get_count() == 3

        widget.clear_all()

        assert widget.get_price_line_manager().get_count() == 0

    def test_add_multiple_price_lines(self, widget: ChartWidget) -> None:
        """Test adding multiple price lines."""
        widget.add_plot("candle")

        line_ids = []
        for i in range(5):
            line_id = widget.add_price_line(
                price=100.0 + i * 10,
                line_type="pending",
                direction="long"
            )
            line_ids.append(line_id)

        assert len(line_ids) == 5
        assert widget.get_price_line_manager().get_count() == 5

        # Verify all lines exist
        for line_id in line_ids:
            line = widget.get_price_line_manager().get_line(line_id)
            assert line is not None

    def test_price_line_with_different_types(self, widget: ChartWidget) -> None:
        """Test adding price lines with different types."""
        widget.add_plot("candle")

        types = ["entry", "pending", "stop_loss", "take_profit", "preview"]

        for line_type in types:
            line_id = widget.add_price_line(
                price=100.0,
                line_type=line_type,
                direction="long"
            )
            assert line_id is not None

            line = widget.get_price_line_manager().get_line(line_id)
            assert line is not None

    def test_price_line_with_different_directions(self, widget: ChartWidget) -> None:
        """Test adding price lines with different directions."""
        widget.add_plot("candle")

        long_line_id = widget.add_price_line(
            price=100.0,
            line_type="entry",
            direction="long"
        )

        short_line_id = widget.add_price_line(
            price=200.0,
            line_type="entry",
            direction="short"
        )

        long_line = widget.get_price_line_manager().get_line(long_line_id)
        short_line = widget.get_price_line_manager().get_line(short_line_id)

        assert long_line.get_direction() == "long"
        assert short_line.get_direction() == "short"

    def test_movable_price_lines(self, widget: ChartWidget) -> None:
        """Test adding movable price lines."""
        widget.add_plot("candle")

        movable_id = widget.add_price_line(
            price=100.0,
            line_type="pending",
            direction="long",
            movable=True
        )

        fixed_id = widget.add_price_line(
            price=200.0,
            line_type="entry",
            direction="long",
            movable=False
        )

        movable_line = widget.get_price_line_manager().get_line(movable_id)
        fixed_line = widget.get_price_line_manager().get_line(fixed_id)

        assert movable_line.movable is True
        assert fixed_line.movable is False

    def test_custom_line_id(self, widget: ChartWidget) -> None:
        """Test adding price line with custom ID."""
        widget.add_plot("candle")

        custom_id = "my_custom_line"
        line_id = widget.add_price_line(
            price=100.0,
            line_type="entry",
            direction="long",
            line_id=custom_id
        )

        assert line_id == custom_id
        line = widget.get_price_line_manager().get_line(custom_id)
        assert line is not None


class TestChartWidgetWithData:
    """Tests for ChartWidget with actual bar data."""

    @pytest.fixture
    def widget(self) -> ChartWidget:
        """Create a ChartWidget with setup."""
        widget = ChartWidget()
        widget.add_plot("candle")
        return widget

    @pytest.fixture
    def sample_bars(self) -> list[BarData]:
        """Create sample bar data."""
        bars = []
        for i in range(10):
            bar = BarData(
                symbol="rb2501",
                exchange="SHFE",
                datetime=datetime(2025, 1, 15, 9, i),
                interval=None,
                volume=1000 + i * 100,
                open_price=100.0 + i,
                high_price=105.0 + i,
                low_price=95.0 + i,
                close_price=102.0 + i,
                gateway_name="test"
            )
            bars.append(bar)
        return bars

    def test_price_lines_with_bar_data(
        self,
        widget: ChartWidget,
        sample_bars: list[BarData]
    ) -> None:
        """Test price lines with bar data loaded."""
        widget.update_history(sample_bars)

        # Add price lines
        line_id1 = widget.add_price_line(price=100.0, line_type="entry", direction="long")
        line_id2 = widget.add_price_line(price=110.0, line_type="pending", direction="short")

        assert widget.get_price_line_manager().get_count() == 2

        # Verify lines still exist after data update
        line1 = widget.get_price_line_manager().get_line(line_id1)
        line2 = widget.get_price_line_manager().get_line(line_id2)

        assert line1 is not None
        assert line2 is not None
        assert line1.get_price() == 100.0
        assert line2.get_price() == 110.0

    def test_price_lines_persist_after_data_update(
        self,
        widget: ChartWidget,
        sample_bars: list[BarData]
    ) -> None:
        """Test that price lines persist after data updates."""
        widget.update_history(sample_bars)

        # Add price lines
        line_ids = []
        for price in [100.0, 105.0, 110.0]:
            line_id = widget.add_price_line(
                price=price,
                line_type="pending",
                direction="long"
            )
            line_ids.append(line_id)

        # Update data
        new_bar = BarData(
            symbol="rb2501",
            exchange="SHFE",
            datetime=datetime(2025, 1, 15, 9, 10),
            interval=None,
            volume=2000,
            open_price=110.0,
            high_price=115.0,
            low_price=105.0,
            close_price=112.0,
            gateway_name="test"
        )
        widget.update_bar(new_bar)

        # Verify lines still exist
        assert widget.get_price_line_manager().get_count() == 3
        for line_id in line_ids:
            line = widget.get_price_line_manager().get_line(line_id)
            assert line is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

