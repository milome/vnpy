"""ChartWidget 数据库模块测试

测试 ChartWidgetDatabaseMixin 的所有方法。
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from vnpy.chart.widget_mixin_base import ChartWidgetMixinBase
from vnpy.chart.widget_database import ChartWidgetDatabaseMixin
from vnpy.chart.price_line import PriceLineManager, PriceLineType, PriceLineItem
from vnpy.chart.price_line_storage import PriceLineStorage, PriceLineData
from vnpy.chart.price_line_database import PriceLineDatabase
from tests.chart.test_base import TestBase


class TestChartWidgetDatabase(TestBase, ChartWidgetDatabaseMixin):
    """数据库模块测试"""
    
    @pytest.fixture(autouse=True)
    def setup(self, qtbot):
        """为每个测试设置模拟对象"""
        self._main_engine = Mock()
        self._main_engine.write_log = Mock()
        
        self._vt_symbol = "MHI2512.HKFE"
        self._price_line_manager = Mock(spec=PriceLineManager)
        self._price_line_manager.get_all_lines = Mock(return_value={})
        self._price_line_manager.get_line = Mock(return_value=None)
        self._price_line_manager.load_from_database = Mock(return_value=0)
        
        self._price_line_database = Mock(spec=PriceLineDatabase)
        self._price_line_database.load_relations = Mock(return_value=[])
        self._price_line_database.save_relation = Mock(return_value=True)
        self._price_line_database.delete_relation = Mock(return_value=True)
        
        self._price_line_storage = Mock(spec=PriceLineStorage)
        self._price_line_storage.save_lines = Mock(return_value=True)
        self._price_line_storage.load_lines = Mock(return_value=[])
        
        self._drawing_order_controller = Mock()
        self._drawing_order_controller.get_order_id_for_line = Mock(return_value=None)
        
        self._entry_line_relations = {}
        
        # Mock methods
        self.get_price_line_manager = Mock(return_value=self._price_line_manager)

    def test_load_line_relations_success(self):
        """测试加载关联关系"""
        # Arrange
        relations = [
            {
                "entry_line_id": "entry_123",
                "related_line_id": "stop_loss_123",
                "relation_type": "stop_loss"
            },
            {
                "entry_line_id": "entry_123",
                "related_line_id": "take_profit_123",
                "relation_type": "take_profit"
            }
        ]
        self._price_line_database.load_relations.return_value = relations
        
        entry_line = Mock(spec=PriceLineItem)
        stop_loss_line = Mock(spec=PriceLineItem)
        take_profit_line = Mock(spec=PriceLineItem)
        self._price_line_manager.get_line.side_effect = [
            entry_line, stop_loss_line, entry_line, take_profit_line
        ]
        
        # Act
        self._load_line_relations()
        
        # Assert
        assert "entry_123" in self._entry_line_relations
        assert self._entry_line_relations["entry_123"]["stop_loss"] == "stop_loss_123"
        assert self._entry_line_relations["entry_123"]["take_profit"] == "take_profit_123"

    def test_load_line_relations_invalid_data_skipped(self):
        """测试无效数据跳过"""
        # Arrange
        relations = [
            {
                "entry_line_id": "entry_123",
                "related_line_id": "stop_loss_123",
                "relation_type": "stop_loss"
            },
            {
                "entry_line_id": "entry_456",  # 不存在的入场线
                "related_line_id": "stop_loss_456",
                "relation_type": "stop_loss"
            }
        ]
        self._price_line_database.load_relations.return_value = relations
        
        entry_line = Mock(spec=PriceLineItem)
        self._price_line_manager.get_line.side_effect = [
            entry_line, None, None, None  # entry_456 不存在
        ]
        
        # Act
        self._load_line_relations()
        
        # Assert
        # 只有 entry_123 的关联关系被加载
        assert "entry_123" in self._entry_line_relations
        assert "entry_456" not in self._entry_line_relations

    def test_save_price_lines_success(self):
        """测试保存价格线"""
        # Arrange
        line1 = Mock(spec=PriceLineItem)
        line1.get_price.return_value = 20000.0
        line1.get_line_type.return_value = PriceLineType.ENTRY
        line1.get_direction.return_value = "long"
        
        line2 = Mock(spec=PriceLineItem)
        line2.get_price.return_value = 19900.0
        line2.get_line_type.return_value = PriceLineType.STOP_LOSS
        line2.get_direction.return_value = "long"
        
        self._price_line_manager.get_all_lines.return_value = {
            "line_1": line1,
            "line_2": line2
        }
        self._price_line_storage.save_lines.return_value = True
        
        # Act
        result = self.save_price_lines()
        
        # Assert
        assert result is True
        self._price_line_storage.save_lines.assert_called_once()

    def test_save_price_lines_no_vt_symbol(self):
        """测试无vt_symbol返回False"""
        # Arrange
        self._vt_symbol = None
        
        # Act
        result = self.save_price_lines()
        
        # Assert
        assert result is False
        self._price_line_storage.save_lines.assert_not_called()

    def test_load_price_lines_success(self):
        """测试加载价格线"""
        # Arrange
        line_data_list = [
            PriceLineData(
                line_id="line_1",
                price=20000.0,
                line_type=PriceLineType.ENTRY,
                direction="long",
                vt_symbol="MHI2512.HKFE",
                vt_orderid=None
            ),
            PriceLineData(
                line_id="line_2",
                price=19900.0,
                line_type=PriceLineType.STOP_LOSS,
                direction="long",
                vt_symbol="MHI2512.HKFE",
                vt_orderid=None
            )
        ]
        self._price_line_storage.load_lines.return_value = line_data_list
        self.add_price_line = Mock(return_value="line_id")
        
        # Act
        result = self.load_price_lines()
        
        # Assert
        assert result is True
        assert self.add_price_line.call_count == 2

    def test_load_price_lines_no_vt_symbol(self):
        """测试无vt_symbol返回False"""
        # Arrange
        self._vt_symbol = None
        
        # Act
        result = self.load_price_lines()
        
        # Assert
        assert result is False
        self._price_line_storage.load_lines.assert_not_called()
