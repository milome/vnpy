"""ChartWidget 集成测试

测试所有模块的集成和端到端场景。
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from vnpy.trader.ui import QtWidgets, QtCore
from vnpy.trader.object import BarData, PositionData, OrderData, TickData
from vnpy.trader.constant import Exchange, Direction, Offset, Status
from vnpy.chart.widget import ChartWidget
from vnpy.chart.item import CandleItem
from tests.chart.test_base import TestBase


class TestChartWidgetIntegration(TestBase):
    """ChartWidget 集成测试"""
    
    @pytest.fixture(autouse=True)
    def setup(self, qtbot):
        """为每个测试设置模拟对象"""
        # 创建 ChartWidget 实例
        self.widget = ChartWidget()
        
        # Mock 必要的组件
        self.widget._main_engine = Mock()
        self.widget._main_engine.write_log = Mock()
        self.widget._main_engine.get_contract = Mock(return_value=Mock(
            symbol="MHI2512",
            exchange=Exchange.HKFE,
            gateway_name="TEST",
            pricetick=1.0,
            min_volume=1
        ))
        self.widget._main_engine.get_all_positions = Mock(return_value=[])
        self.widget._main_engine.get_all_active_orders = Mock(return_value=[])
        self.widget._main_engine.get_tick = Mock(return_value=self.create_tick_data())
        
        self.widget._event_engine = Mock()
        self.widget._event_engine.register = Mock()
        
        self.widget._vt_symbol = "MHI2512.HKFE"
        
        # 初始化必要的属性
        self.widget._price_line_manager = Mock()
        self.widget._price_line_manager.get_all_lines = Mock(return_value={})
        self.widget._price_line_manager.create_line = Mock(return_value="line_123")
        self.widget._price_line_manager.get_line = Mock(return_value=None)
        self.widget._price_line_manager.delete_line = Mock(return_value=True)
        
        self.widget._drawing_order_controller = Mock()
        self.widget._drawing_order_controller.is_enabled = Mock(return_value=False)
        self.widget._drawing_order_controller.get_order_id_for_line = Mock(return_value=None)
        self.widget._drawing_order_controller.link_line_to_order = Mock()
        
        self.widget._breakthrough_monitor = Mock()
        self.widget._breakthrough_monitor.register_line = Mock()
        self.widget._breakthrough_monitor.unregister_line = Mock()
        self.widget._breakthrough_monitor.update_bar = Mock()
        
        self.widget._price_line_database = Mock()
        self.widget._price_line_database.load_relations = Mock(return_value=[])
        
        self.widget._price_line_storage = Mock()
        self.widget._price_line_storage.save_lines = Mock(return_value=True)
        self.widget._price_line_storage.load_lines = Mock(return_value=[])
        
        self.widget._position_holdings = {}
        self.widget._entry_line_relations = {}
        
        # 添加一个 plot 用于测试
        self.widget.add_plot("candle")
        self.widget.add_item(CandleItem, "candle", "candle")

    def test_widget_initialization(self):
        """测试 ChartWidget 初始化"""
        # Assert
        assert self.widget is not None
        assert hasattr(self.widget, '_manager')
        assert hasattr(self.widget, '_plots')
        assert hasattr(self.widget, '_items')

    def test_all_mixins_inherited(self):
        """测试所有 Mixin 都被正确继承"""
        from vnpy.chart.widget_position import ChartWidgetPositionMixin
        from vnpy.chart.widget_order import ChartWidgetOrderMixin
        from vnpy.chart.widget_trigger import ChartWidgetTriggerMixin
        from vnpy.chart.widget_mouse import ChartWidgetMouseMixin
        from vnpy.chart.widget_chart import ChartWidgetChartMixin
        from vnpy.chart.widget_database import ChartWidgetDatabaseMixin
        
        # Assert
        assert isinstance(self.widget, ChartWidgetPositionMixin)
        assert isinstance(self.widget, ChartWidgetOrderMixin)
        assert isinstance(self.widget, ChartWidgetTriggerMixin)
        assert isinstance(self.widget, ChartWidgetMouseMixin)
        assert isinstance(self.widget, ChartWidgetChartMixin)
        assert isinstance(self.widget, ChartWidgetDatabaseMixin)

    def test_set_vt_symbol(self):
        """测试设置 VT symbol"""
        # Act
        self.widget.set_vt_symbol("MHI2512.HKFE")
        
        # Assert
        assert self.widget._vt_symbol == "MHI2512.HKFE"

    def test_update_history(self):
        """测试更新历史数据"""
        # Arrange
        history = [self.create_bar_data() for _ in range(10)]
        
        # Act
        self.widget.update_history(history)
        
        # Assert
        assert self.widget._manager.update_history.called

    def test_update_bar(self):
        """测试更新单根K线"""
        # Arrange
        bar = self.create_bar_data()
        
        # Act
        self.widget.update_bar(bar)
        
        # Assert
        assert self.widget._manager.update_bar.called

    def test_add_price_line(self):
        """测试添加价格线"""
        # Act
        line_id = self.widget.add_price_line(
            price=20000.0,
            line_type="entry",
            direction="long"
        )
        
        # Assert
        assert line_id is not None
        self.widget._price_line_manager.create_line.assert_called_once()

    def test_register_position_events(self):
        """测试注册持仓事件"""
        # Act
        self.widget._register_position_events()
        
        # Assert
        assert self.widget._event_engine.register.called

    def test_save_price_lines(self):
        """测试保存价格线"""
        # Act
        result = self.widget.save_price_lines()
        
        # Assert
        # 应该返回 True 或 False（取决于是否有价格线）
        assert isinstance(result, bool)

    def test_load_price_lines(self):
        """测试加载价格线"""
        # Act
        result = self.widget.load_price_lines()
        
        # Assert
        # 应该返回 True 或 False（取决于是否有数据）
        assert isinstance(result, bool)

    def test_clear_all(self):
        """测试清除所有数据"""
        # Act
        self.widget.clear_all()
        
        # Assert
        assert self.widget._manager.clear_all.called

    def test_end_to_end_scenario(self):
        """测试端到端场景：创建图表 -> 添加数据 -> 添加价格线 -> 更新持仓"""
        # Arrange
        self.widget.set_vt_symbol("MHI2512.HKFE")
        
        # Act: 添加历史数据
        history = [self.create_bar_data() for _ in range(20)]
        self.widget.update_history(history)
        
        # Act: 添加价格线
        line_id = self.widget.add_price_line(
            price=20000.0,
            line_type="entry",
            direction="long"
        )
        
        # Act: 更新持仓
        position = self.create_position_data(
            symbol="MHI2512",
            exchange=Exchange.HKFE,
            direction=Direction.LONG,
            volume=10
        )
        self.widget._on_position_update(Mock(data=position))
        
        # Assert
        assert line_id is not None
        assert self.widget._vt_symbol == "MHI2512.HKFE"

