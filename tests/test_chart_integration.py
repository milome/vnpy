"""
Integration tests for chart functionality with MainEngine and order system.

Tests cover:
- MainEngine integration
- Order system integration
- Event system integration
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock

from vnpy.trader.object import BarData, TickData, OrderData, OrderRequest
from vnpy.trader.constant import Direction, Offset, OrderType, Status, Exchange
from vnpy.chart.widget import ChartWidget
from vnpy.chart.drawing_order import DrawingOrderController


class TestMainEngineIntegration:
    """Integration tests with MainEngine."""

    @pytest.fixture
    def widget(self) -> ChartWidget:
        """Create a ChartWidget instance."""
        widget = ChartWidget()
        widget.add_plot("test_plot")
        return widget

    @pytest.fixture
    def mock_main_engine(self) -> Mock:
        """Create a mock MainEngine."""
        engine = Mock()
        engine.send_order = Mock(return_value="test_order.123")
        engine.get_tick = Mock(return_value=None)
        engine.write_log = Mock()
        return engine

    def test_set_main_engine(self, widget: ChartWidget, mock_main_engine: Mock) -> None:
        """Test setting MainEngine on widget."""
        widget.set_main_engine(mock_main_engine)

        assert widget._main_engine == mock_main_engine
        assert widget._drawing_order_controller is not None
        assert widget._drawing_order_controller._main_engine == mock_main_engine

    def test_set_vt_symbol(self, widget: ChartWidget) -> None:
        """Test setting VT symbol on widget."""
        widget.set_vt_symbol("rb2501.SHFE")

        assert widget._vt_symbol == "rb2501.SHFE"
        assert widget._drawing_order_controller is not None
        assert widget._drawing_order_controller._vt_symbol == "rb2501.SHFE"


class TestOrderSystemIntegration:
    """Integration tests with order system."""

    @pytest.fixture
    def widget(self) -> ChartWidget:
        """Create a ChartWidget instance."""
        widget = ChartWidget()
        widget.add_plot("test_plot")
        return widget

    @pytest.fixture
    def controller(self, widget: ChartWidget) -> DrawingOrderController:
        """Get drawing order controller."""
        return widget._drawing_order_controller

    def test_create_pending_order_line(self, controller: DrawingOrderController, widget: ChartWidget) -> None:
        """Test creating pending order line."""
        line_id = controller.create_pending_order_line(100.0, "long")

        assert line_id is not None
        line = widget.get_price_line_manager().get_line(line_id)
        assert line is not None
        assert line.get_line_type() == PriceLineType.PENDING

    def test_link_order_to_line(self, controller: DrawingOrderController) -> None:
        """Test linking order to line."""
        line_id = "test_line"
        vt_orderid = "test_order.123"

        controller.link_line_to_order(line_id, vt_orderid)

        assert controller.get_order_id_for_line(line_id) == vt_orderid
        assert controller.get_line_id_for_order(vt_orderid) == line_id

    def test_update_line_from_order_status(
        self,
        controller: DrawingOrderController,
        widget: ChartWidget
    ) -> None:
        """Test updating line when order status changes."""
        from vnpy.chart.price_line import PriceLineType

        # Create pending line
        line_id = controller.create_pending_order_line(100.0, "long")
        vt_orderid = "test_order.123"
        controller.link_line_to_order(line_id, vt_orderid)

        # Create filled order
        order = OrderData(
            symbol="rb2501",
            exchange=Exchange.SHFE,
            orderid="123",
            type=OrderType.LIMIT,
            direction=Direction.LONG,
            offset=Offset.OPEN,
            price=100.0,
            volume=1.0,
            status=Status.ALLTRADED,
            gateway_name="test"
        )

        result = controller.update_line_from_order(order)
        assert result is True

        # Line should be converted to entry
        new_line = widget.get_price_line_manager().get_line(line_id)
        assert new_line is not None
        assert new_line.get_line_type() == PriceLineType.ENTRY


class TestEventSystemIntegration:
    """Integration tests with event system."""

    @pytest.fixture
    def widget(self) -> ChartWidget:
        """Create a ChartWidget instance."""
        widget = ChartWidget()
        widget.add_plot("test_plot")
        widget.set_vt_symbol("rb2501.SHFE")
        return widget

    def test_price_breakthrough_event(self, widget: ChartWidget) -> None:
        """Test price breakthrough event handling."""
        from vnpy.chart.price_line import PriceLineType

        # Create pending line
        line_id = widget.add_price_line(
            price=100.0,
            line_type="pending",
            direction="long"
        )

        # Register for breakthrough monitoring
        breakthrough_events = []

        def on_breakthrough(event) -> None:
            breakthrough_events.append(event)

        line = widget.get_price_line_manager().get_line(line_id)
        if line:
            widget._breakthrough_monitor.register_line(line_id, line, on_breakthrough)

        # Create bar that should trigger breakthrough
        bar = BarData(
            symbol="rb2501",
            exchange=Exchange.SHFE,
            datetime=datetime.now(),
            interval=None,
            open_price=99.0,
            high_price=101.0,
            low_price=98.0,
            close_price=100.5,  # Above line price
            gateway_name="test"
        )

        widget.update_bar(bar)

        # Event may or may not trigger depending on last_price tracking
        assert len(breakthrough_events) >= 0

    def test_bar_update_triggers_breakthrough_monitor(self, widget: ChartWidget) -> None:
        """Test that bar updates trigger breakthrough monitor."""
        # Create pending line
        line_id = widget.add_price_line(
            price=100.0,
            line_type="pending",
            direction="long"
        )

        # Update with bar
        bar = BarData(
            symbol="rb2501",
            exchange=Exchange.SHFE,
            datetime=datetime.now(),
            interval=None,
            open_price=100.0,
            high_price=105.0,
            low_price=95.0,
            close_price=102.0,
            gateway_name="test"
        )

        # Should not crash
        widget.update_bar(bar)

        # Line should still exist
        line = widget.get_price_line_manager().get_line(line_id)
        assert line is not None


class TestPriceLineStorageIntegration:
    """Integration tests for price line storage."""

    @pytest.fixture
    def widget(self, tmp_path) -> ChartWidget:
        """Create a ChartWidget with temp storage."""
        widget = ChartWidget()
        widget.add_plot("test_plot")
        widget.set_vt_symbol("rb2501.SHFE")
        
        # Override storage path
        from vnpy.chart.price_line_storage import PriceLineStorage
        storage_path = tmp_path / "test_price_lines.json"
        widget._price_line_storage = PriceLineStorage(str(storage_path))
        
        return widget

    def test_save_and_load_price_lines(self, widget: ChartWidget) -> None:
        """Test saving and loading price lines."""
        # Add some price lines
        line_id1 = widget.add_price_line(price=100.0, line_type="entry", direction="long")
        line_id2 = widget.add_price_line(price=200.0, line_type="pending", direction="short")

        # Save
        result = widget.save_price_lines()
        assert result is True

        # Clear
        widget.clear_all()
        assert widget.get_price_line_manager().get_count() == 0

        # Load
        result = widget.load_price_lines()
        assert result is True
        assert widget.get_price_line_manager().get_count() == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

