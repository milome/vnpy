"""测试 ChartWidgetMixinBase 类"""

import pytest
from unittest.mock import Mock, MagicMock
import sys
from pathlib import Path

# 直接导入 Mixin 基类，避免通过 __init__.py 导入（会触发 widget.py 导入）
# 使用 importlib 直接导入模块
import importlib.util
spec = importlib.util.spec_from_file_location(
    "widget_mixin_base",
    Path(__file__).parent.parent.parent / "vnpy" / "chart" / "widget_mixin_base.py"
)
widget_mixin_base = importlib.util.module_from_spec(spec)
sys.modules["widget_mixin_base"] = widget_mixin_base
spec.loader.exec_module(widget_mixin_base)  # type: ignore
ChartWidgetMixinBase = widget_mixin_base.ChartWidgetMixinBase

# 标记这些测试不需要 Qt
pytestmark = pytest.mark.no_qt


class TestWidget(ChartWidgetMixinBase):
    """测试用的类，继承 ChartWidgetMixinBase"""
    pass


class TestChartWidgetMixinBase:
    """测试 ChartWidgetMixinBase 类"""
    
    def test_get_main_engine_exists(self, mock_main_engine):
        """测试 _get_main_engine() 方法 - 存在 main_engine"""
        # Arrange
        test_obj = TestWidget()
        test_obj._main_engine = mock_main_engine
        
        # Act
        result = test_obj._get_main_engine()
        
        # Assert
        assert result == mock_main_engine
    
    def test_get_main_engine_not_exists(self):
        """测试 _get_main_engine() 方法 - 不存在 main_engine"""
        # Arrange
        test_obj = TestWidget()
        # 不设置 _main_engine
        
        # Act
        result = test_obj._get_main_engine()
        
        # Assert
        assert result is None
    
    def test_get_vt_symbol_exists(self):
        """测试 _get_vt_symbol() 方法 - 存在 vt_symbol"""
        # Arrange
        test_obj = TestWidget()
        test_obj._vt_symbol = "MHI2512.HKFE"
        
        # Act
        result = test_obj._get_vt_symbol()
        
        # Assert
        assert result == "MHI2512.HKFE"
    
    def test_get_vt_symbol_not_exists(self):
        """测试 _get_vt_symbol() 方法 - 不存在 vt_symbol"""
        # Arrange
        test_obj = TestWidget()
        # 不设置 _vt_symbol
        
        # Act
        result = test_obj._get_vt_symbol()
        
        # Assert
        assert result is None
    
    def test_log_with_main_engine(self, mock_main_engine):
        """测试 _log() 方法 - 有 main_engine"""
        # Arrange
        test_obj = TestWidget()
        test_obj._main_engine = mock_main_engine
        message = "Test log message"
        source = "TestSource"
        
        # Act
        test_obj._log(message, source)
        
        # Assert
        mock_main_engine.write_log.assert_called_once_with(
            f"[{source}] {message}",
            source
        )
    
    def test_log_without_main_engine(self):
        """测试 _log() 方法 - 无 main_engine"""
        # Arrange
        test_obj = TestWidget()
        # 不设置 _main_engine
        message = "Test log message"
        source = "TestSource"
        
        # Act & Assert - 不应该抛出异常
        test_obj._log(message, source)
        # 如果没有 main_engine，应该静默处理，不报错

