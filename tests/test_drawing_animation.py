"""
单元测试：动态画线管理器

测试 DrawingAnimationManager 的核心功能。
"""

import pytest
from unittest.mock import MagicMock

import pyqtgraph as pg

from vnpy.chart.drawing_animation import (
    DrawingAnimationManager,
    AnimatedLine,
    AnimationLineType,
    AnimationLineDirection
)


class TestAnimatedLine:
    """测试 AnimatedLine 类"""
    
    def test_create_horizontal_line(self):
        """测试创建水平线"""
        line = AnimatedLine(
            line_type=AnimationLineType.HORIZONTAL,
            price=26000.0,
            color=(255, 255, 0),
            width=2,
            animation_direction=AnimationLineDirection.FORWARD
        )
        
        assert line.get_line_type() == AnimationLineType.HORIZONTAL
        assert line._price == 26000.0
        assert line._base_color == (255, 255, 0)
        assert line._width == 2
        assert line._animation_direction == AnimationLineDirection.FORWARD
    
    def test_create_vertical_line(self):
        """测试创建垂直线"""
        line = AnimatedLine(
            line_type=AnimationLineType.VERTICAL,
            price=100.0,
            color=(0, 255, 255),
            width=3,
            animation_direction=AnimationLineDirection.BACKWARD
        )
        
        assert line.get_line_type() == AnimationLineType.VERTICAL
        assert line._animation_direction == AnimationLineDirection.BACKWARD
    
    def test_update_animation_forward(self):
        """测试正向动画更新"""
        line = AnimatedLine(
            line_type=AnimationLineType.HORIZONTAL,
            price=26000.0,
            animation_direction=AnimationLineDirection.FORWARD,
            dash_pattern=[10, 5]
        )
        
        initial_offset = line._animation_offset
        line.update_animation()
        
        # 偏移量应该增加
        assert line._animation_offset == initial_offset + 1
    
    def test_update_animation_backward(self):
        """测试反向动画更新"""
        line = AnimatedLine(
            line_type=AnimationLineType.HORIZONTAL,
            price=26000.0,
            animation_direction=AnimationLineDirection.BACKWARD,
            dash_pattern=[10, 5]
        )
        
        initial_offset = line._animation_offset
        line.update_animation()
        
        # 偏移量应该减少
        assert line._animation_offset == initial_offset - 1
    
    def test_update_animation_blink(self):
        """测试闪烁动画更新"""
        line = AnimatedLine(
            line_type=AnimationLineType.HORIZONTAL,
            price=26000.0,
            animation_direction=AnimationLineDirection.BLINK
        )
        
        initial_visible = line._visible
        line.update_animation()
        
        # 可见性应该切换
        assert line._visible != initial_visible
    
    def test_set_color(self):
        """测试设置颜色"""
        line = AnimatedLine(
            line_type=AnimationLineType.HORIZONTAL,
            price=26000.0,
            color=(255, 0, 0)
        )
        
        line.set_color((0, 255, 0))
        assert line._base_color == (0, 255, 0)
    
    def test_custom_dash_pattern(self):
        """测试自定义虚线样式"""
        custom_pattern = [20, 10, 5, 10]
        line = AnimatedLine(
            line_type=AnimationLineType.HORIZONTAL,
            price=26000.0,
            dash_pattern=custom_pattern
        )
        
        assert line._dash_pattern == custom_pattern


class TestDrawingAnimationManager:
    """测试 DrawingAnimationManager 类"""
    
    @pytest.fixture
    def mock_plot(self):
        """创建模拟的 PlotItem"""
        plot = MagicMock(spec=pg.PlotItem)
        return plot
    
    @pytest.fixture
    def manager(self, mock_plot):
        """创建动画管理器实例"""
        return DrawingAnimationManager(plot=mock_plot)
    
    def test_create_horizontal_line(self, manager, mock_plot):
        """测试创建水平线"""
        line_id = manager.create_horizontal_line(
            price=26000.0,
            color=(255, 255, 0)
        )
        
        # 检查线条ID格式
        assert line_id.startswith("h_line_")
        
        # 检查线条是否已添加到管理器
        assert line_id in manager._animated_lines
        
        # 检查是否添加到plot
        mock_plot.addItem.assert_called_once()
        
        # 检查定时器是否启动
        assert manager.is_running()
    
    def test_create_vertical_line(self, manager, mock_plot):
        """测试创建垂直线"""
        line_id = manager.create_vertical_line(
            time_index=100.0,
            color=(0, 255, 255)
        )
        
        # 检查线条ID格式
        assert line_id.startswith("v_line_")
        
        # 检查线条是否已添加到管理器
        assert line_id in manager._animated_lines
        
        # 检查是否添加到plot
        assert mock_plot.addItem.call_count >= 1
    
    def test_remove_line(self, manager, mock_plot):
        """测试删除线条"""
        line_id = manager.create_horizontal_line(price=26000.0)
        
        # 删除线条
        result = manager.remove_line(line_id)
        
        assert result is True
        assert line_id not in manager._animated_lines
        mock_plot.removeItem.assert_called_once()
    
    def test_remove_nonexistent_line(self, manager):
        """测试删除不存在的线条"""
        result = manager.remove_line("nonexistent_id")
        assert result is False
    
    def test_clear_all(self, manager, mock_plot):
        """测试清除所有线条"""
        # 创建多条线
        manager.create_horizontal_line(price=26000.0)
        manager.create_horizontal_line(price=26100.0)
        manager.create_vertical_line(time_index=100.0)
        
        initial_count = manager.get_line_count()
        assert initial_count == 3
        
        # 清除所有线条
        manager.clear_all()
        
        assert manager.get_line_count() == 0
        assert not manager.is_running()
    
    def test_custom_line_id(self, manager):
        """测试自定义线条ID"""
        custom_id = "my_custom_line"
        line_id = manager.create_horizontal_line(
            price=26000.0,
            line_id=custom_id
        )
        
        assert line_id == custom_id
        assert custom_id in manager._animated_lines
    
    def test_animation_parameters(self, manager):
        """测试动画参数配置"""
        line_id = manager.create_horizontal_line(
            price=26000.0,
            color=(255, 0, 0),
            width=5,
            animation_direction=AnimationLineDirection.BACKWARD,
            dash_pattern=[30, 15]
        )
        
        line = manager._animated_lines[line_id]
        assert line._base_color == (255, 0, 0)
        assert line._width == 5
        assert line._animation_direction == AnimationLineDirection.BACKWARD
        assert line._dash_pattern == [30, 15]
    
    def test_get_line_count(self, manager):
        """测试获取线条数量"""
        assert manager.get_line_count() == 0
        
        manager.create_horizontal_line(price=26000.0)
        assert manager.get_line_count() == 1
        
        manager.create_vertical_line(time_index=100.0)
        assert manager.get_line_count() == 2
    
    def test_timer_starts_with_first_line(self, manager):
        """测试添加第一条线时启动定时器"""
        assert not manager.is_running()
        
        manager.create_horizontal_line(price=26000.0)
        
        assert manager.is_running()
        assert manager._animation_timer is not None
    
    def test_timer_stops_when_empty(self, manager):
        """测试删除最后一条线时停止定时器"""
        line_id = manager.create_horizontal_line(price=26000.0)
        assert manager.is_running()
        
        manager.remove_line(line_id)
        assert not manager.is_running()
    
    def test_multiple_lines_different_directions(self, manager):
        """测试创建不同方向的多条线"""
        line1 = manager.create_horizontal_line(
            price=26000.0,
            animation_direction=AnimationLineDirection.FORWARD
        )
        line2 = manager.create_horizontal_line(
            price=26100.0,
            animation_direction=AnimationLineDirection.BACKWARD
        )
        line3 = manager.create_horizontal_line(
            price=26200.0,
            animation_direction=AnimationLineDirection.BLINK
        )
        
        assert manager.get_line_count() == 3
        
        # 验证每条线的方向设置正确
        assert manager._animated_lines[line1]._animation_direction == AnimationLineDirection.FORWARD
        assert manager._animated_lines[line2]._animation_direction == AnimationLineDirection.BACKWARD
        assert manager._animated_lines[line3]._animation_direction == AnimationLineDirection.BLINK


class TestEnums:
    """测试枚举类"""
    
    def test_animation_line_type_enum(self):
        """测试 AnimationLineType 枚举"""
        assert AnimationLineType.HORIZONTAL.value == "horizontal"
        assert AnimationLineType.VERTICAL.value == "vertical"
        assert AnimationLineType.SEGMENT.value == "segment"
    
    def test_animation_line_direction_enum(self):
        """测试 AnimationLineDirection 枚举"""
        assert AnimationLineDirection.FORWARD.value == "forward"
        assert AnimationLineDirection.BACKWARD.value == "backward"
        assert AnimationLineDirection.BLINK.value == "blink"


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])

