"""
Drawing Animation Manager - 动态画线管理器

实现跑马灯效果的动态线条绘制功能。
支持水平线、垂直线、线段、矩形边框等多种类型的动态显示。
"""

from typing import Optional, Literal
from enum import Enum
import numpy as np

import pyqtgraph as pg  # type: ignore

from vnpy.trader.ui import QtCore, QtGui, QtWidgets

from .base import PEN_WIDTH


class AnimationLineType(Enum):
    """动画线类型"""
    HORIZONTAL = "horizontal"      # 水平线
    VERTICAL = "vertical"          # 垂直线
    SEGMENT = "segment"            # 线段（有起点和终点）


class AnimationLineDirection(Enum):
    """跑马灯动画方向"""
    FORWARD = "forward"    # 正向（从左到右，或从上到下）
    BACKWARD = "backward"  # 反向（从右到左，或从下到上）
    BLINK = "blink"        # 闪烁效果


class AnimatedRectangle:
    """
    动画矩形边框类（使用 PlotDataItem）
    
    使用4条 PlotDataItem 绘制矩形边框，支持跑马灯动画效果。
    """
    
    def __init__(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        color: tuple[int, int, int] = (255, 255, 0),
        line_width: float = 1.5,
        animation_direction: AnimationLineDirection = AnimationLineDirection.FORWARD,
        dash_pattern: list[int] = None
    ) -> None:
        """
        初始化矩形边框
        
        Args:
            x: 矩形左下角X坐标（时间索引）
            y: 矩形左下角Y坐标（价格）
            width: 矩形宽度（时间单位）
            height: 矩形高度（价格单位）
            color: RGB颜色元组
            line_width: 线宽
            animation_direction: 动画方向
            dash_pattern: 虚线样式
        """
        self._x = x
        self._y = y
        self._width = width
        self._height = height
        self._color = color
        self._line_width = line_width
        self._animation_direction = animation_direction
        self._dash_pattern = dash_pattern or [8, 4]
        self._animation_offset = 0
        self._visible = True
        
        # 计算矩形四个顶点
        self._x1 = x
        self._y1 = y
        self._x2 = x + width
        self._y2 = y + height
        
        # 创建画笔
        self._pen = self._create_pen()
        
        # 创建4条边（使用 PlotDataItem）
        self._lines = []
        self._create_lines()
    
    def _create_pen(self) -> QtGui.QPen:
        """创建画笔"""
        pen = pg.mkPen(
            color=self._color,
            width=self._line_width,
            style=QtCore.Qt.PenStyle.CustomDashLine
        )
        pen.setDashPattern(self._dash_pattern)
        pen.setDashOffset(self._animation_offset)
        return pen
    
    def _create_lines(self) -> None:
        """创建4条边的线段"""
        # 上边：从左上到右上
        top_line = pg.PlotDataItem(
            x=[self._x1, self._x2],
            y=[self._y2, self._y2],
            pen=self._pen
        )
        self._lines.append(top_line)
        
        # 右边：从右上到右下
        right_line = pg.PlotDataItem(
            x=[self._x2, self._x2],
            y=[self._y2, self._y1],
            pen=self._pen
        )
        self._lines.append(right_line)
        
        # 下边：从右下到左下
        bottom_line = pg.PlotDataItem(
            x=[self._x2, self._x1],
            y=[self._y1, self._y1],
            pen=self._pen
        )
        self._lines.append(bottom_line)
        
        # 左边：从左下到左上
        left_line = pg.PlotDataItem(
            x=[self._x1, self._x1],
            y=[self._y1, self._y2],
            pen=self._pen
        )
        self._lines.append(left_line)
    
    def get_lines(self) -> list:
        """获取所有线条对象"""
        return self._lines
    
    def update_animation(self) -> None:
        """更新动画状态"""
        if self._animation_direction == AnimationLineDirection.FORWARD:
            self._animation_offset += 1
            if self._animation_offset > sum(self._dash_pattern):
                self._animation_offset = 0
        elif self._animation_direction == AnimationLineDirection.BACKWARD:
            self._animation_offset -= 1
            if self._animation_offset < -sum(self._dash_pattern):
                self._animation_offset = 0
        elif self._animation_direction == AnimationLineDirection.BLINK:
            self._visible = not self._visible
            for line in self._lines:
                line.setVisible(self._visible)
            return
        
        # 更新画笔
        pen = self._create_pen()
        for line in self._lines:
            line.setPen(pen)
    
    def set_color(self, color: tuple[int, int, int]) -> None:
        """设置颜色"""
        self._color = color
        pen = self._create_pen()
        for line in self._lines:
            line.setPen(pen)
    
    def setVisible(self, visible: bool) -> None:
        """设置可见性"""
        self._visible = visible
        for line in self._lines:
            line.setVisible(visible)


class AnimatedLine(pg.InfiniteLine):
    """
    动画线条类
    
    支持跑马灯效果的动态线条。
    """
    
    def __init__(
        self,
        line_type: AnimationLineType,
        price: float,
        color: tuple[int, int, int] = (255, 255, 0),
        width: int = 2,
        animation_direction: AnimationLineDirection = AnimationLineDirection.FORWARD,
        animation_speed: int = 100,  # 动画速度（毫秒）
        dash_pattern: list[int] = None,  # 虚线样式 [dash, space, dash, space, ...]
        extend: bool = True,  # 是否延伸（无限线）
        start_pos: Optional[float] = None,  # 起始位置（用于线段）
        end_pos: Optional[float] = None,    # 终止位置（用于线段）
    ) -> None:
        """
        初始化动画线条
        
        Args:
            line_type: 线条类型（水平/垂直/线段）
            price: 价格位置（水平线）或时间索引（垂直线）
            color: RGB颜色元组
            width: 线宽
            animation_direction: 动画方向
            animation_speed: 动画速度（毫秒）
            dash_pattern: 虚线样式，如 [10, 5] 表示10像素实线，5像素空白
            extend: 是否延伸为无限线
            start_pos: 起始位置（仅用于线段）
            end_pos: 终止位置（仅用于线段）
        """
        # 确定线条角度（0=水平，90=垂直）
        angle = 0 if line_type == AnimationLineType.HORIZONTAL else 90
        
        # 创建基础画笔
        self._base_color = color
        self._width = width
        self._dash_pattern = dash_pattern or [10, 5]  # 默认虚线样式
        self._animation_offset = 0  # 动画偏移量
        
        # 创建画笔
        pen = self._create_pen()
        
        # 初始化 InfiniteLine
        super().__init__(
            angle=angle,
            pos=price,
            pen=pen,
            movable=False
        )
        
        # 保存参数
        self._line_type = line_type
        self._price = price
        self._animation_direction = animation_direction
        self._animation_speed = animation_speed
        self._extend = extend
        self._start_pos = start_pos
        self._end_pos = end_pos
        self._visible = True
        
        # 如果是线段类型，设置span
        if line_type == AnimationLineType.SEGMENT and start_pos is not None and end_pos is not None:
            # 注意：span是相对于整个视图的比例，这里我们需要在paintEvent中自定义绘制
            pass
    
    def _create_pen(self) -> QtGui.QPen:
        """创建画笔（带虚线样式）"""
        pen = pg.mkPen(
            color=self._base_color,
            width=self._width,
            style=QtCore.Qt.PenStyle.CustomDashLine
        )
        
        # 设置虚线样式（加上动画偏移）
        dash_pattern = self._dash_pattern.copy()
        pen.setDashPattern(dash_pattern)
        pen.setDashOffset(self._animation_offset)
        
        return pen
    
    def update_animation(self) -> None:
        """更新动画状态"""
        if self._animation_direction == AnimationLineDirection.FORWARD:
            # 正向移动
            self._animation_offset += 1
            if self._animation_offset > sum(self._dash_pattern):
                self._animation_offset = 0
        elif self._animation_direction == AnimationLineDirection.BACKWARD:
            # 反向移动
            self._animation_offset -= 1
            if self._animation_offset < -sum(self._dash_pattern):
                self._animation_offset = 0
        elif self._animation_direction == AnimationLineDirection.BLINK:
            # 闪烁效果
            self._visible = not self._visible
            self.setVisible(self._visible)
            return  # 闪烁不需要更新画笔
        
        # 更新画笔
        pen = self._create_pen()
        self.setPen(pen)
        
        # 强制重绘
        if self.scene():
            self.update()
    
    def get_line_type(self) -> AnimationLineType:
        """获取线条类型"""
        return self._line_type
    
    def set_color(self, color: tuple[int, int, int]) -> None:
        """设置颜色"""
        self._base_color = color
        pen = self._create_pen()
        self.setPen(pen)


class DrawingAnimationManager:
    """
    动态画线管理器
    
    管理所有动画线条的创建、更新和删除。
    使用定时器驱动动画效果。
    """
    
    def __init__(
        self,
        widget: "ChartWidget" = None,
        plot: pg.PlotItem = None
    ) -> None:
        """
        初始化动画管理器
        
        Args:
            widget: ChartWidget 实例
            plot: PlotItem 实例（用于添加线条）
        """
        self._widget = widget
        self._plot = plot
        
        # 动画线条字典：line_id -> AnimatedLine or AnimatedRectangle
        self._animated_lines: dict[str, AnimatedLine | AnimatedRectangle] = {}
        
        # 线条ID计数器
        self._line_id_counter = 0
        
        # 动画定时器
        self._animation_timer: Optional[QtCore.QTimer] = None
        self._is_running = False
    
    def create_horizontal_line(
        self,
        price: float,
        color: tuple[int, int, int] = (255, 255, 0),
        width: int = 2,
        animation_direction: AnimationLineDirection = AnimationLineDirection.FORWARD,
        animation_speed: int = 100,
        dash_pattern: list[int] = None,
        line_id: Optional[str] = None
    ) -> str:
        """
        创建水平动画线
        
        Args:
            price: 价格位置
            color: RGB颜色元组
            width: 线宽
            animation_direction: 动画方向
            animation_speed: 动画速度（毫秒）
            dash_pattern: 虚线样式
            line_id: 可选的线条ID
            
        Returns:
            线条ID
        """
        if line_id is None:
            line_id = f"h_line_{self._line_id_counter}"
            self._line_id_counter += 1
        
        # 创建动画线
        line = AnimatedLine(
            line_type=AnimationLineType.HORIZONTAL,
            price=price,
            color=color,
            width=width,
            animation_direction=animation_direction,
            animation_speed=animation_speed,
            dash_pattern=dash_pattern,
            extend=True
        )
        
        # 添加到图表
        if self._plot:
            self._plot.addItem(line)
        
        # 保存到字典
        self._animated_lines[line_id] = line
        
        # 启动动画定时器（如果还未启动）
        self._start_animation_timer()
        
        return line_id
    
    def create_vertical_line(
        self,
        time_index: float,
        color: tuple[int, int, int] = (0, 255, 255),
        width: int = 2,
        animation_direction: AnimationLineDirection = AnimationLineDirection.FORWARD,
        animation_speed: int = 100,
        dash_pattern: list[int] = None,
        line_id: Optional[str] = None
    ) -> str:
        """
        创建垂直动画线
        
        Args:
            time_index: 时间索引（K线索引）
            color: RGB颜色元组
            width: 线宽
            animation_direction: 动画方向
            animation_speed: 动画速度（毫秒）
            dash_pattern: 虚线样式
            line_id: 可选的线条ID
            
        Returns:
            线条ID
        """
        if line_id is None:
            line_id = f"v_line_{self._line_id_counter}"
            self._line_id_counter += 1
        
        # 创建动画线
        line = AnimatedLine(
            line_type=AnimationLineType.VERTICAL,
            price=time_index,  # 对于垂直线，price参数用作时间索引
            color=color,
            width=width,
            animation_direction=animation_direction,
            animation_speed=animation_speed,
            dash_pattern=dash_pattern,
            extend=True
        )
        
        # 添加到图表
        if self._plot:
            self._plot.addItem(line)
        
        # 保存到字典
        self._animated_lines[line_id] = line
        
        # 启动动画定时器（如果还未启动）
        self._start_animation_timer()
        
        return line_id
    
    def remove_line(self, line_id: str) -> bool:
        """
        删除动画线
        
        Args:
            line_id: 线条ID
            
        Returns:
            是否删除成功
        """
        line = self._animated_lines.pop(line_id, None)
        if line is None:
            return False
        
        # 从图表中移除
        if self._plot:
            # 如果是 AnimatedRectangle，需要删除其所有线条
            if isinstance(line, AnimatedRectangle):
                for plot_line in line.get_lines():
                    self._plot.removeItem(plot_line)
            else:
                self._plot.removeItem(line)
        
        # 如果没有动画线了，停止定时器
        if not self._animated_lines:
            self._stop_animation_timer()
        
        return True
    
    def clear_all(self) -> None:
        """清除所有动画线"""
        if self._plot:
            for line_obj in list(self._animated_lines.values()):
                # 如果是 AnimatedRectangle，需要删除其所有线条
                if isinstance(line_obj, AnimatedRectangle):
                    for plot_line in line_obj.get_lines():
                        self._plot.removeItem(plot_line)
                else:
                    # AnimatedLine 类型
                    self._plot.removeItem(line_obj)
        
        self._animated_lines.clear()
        self._stop_animation_timer()
    
    def _start_animation_timer(self) -> None:
        """启动动画定时器"""
        if self._is_running:
            return
        
        if self._animation_timer is None:
            self._animation_timer = QtCore.QTimer()
            self._animation_timer.timeout.connect(self._update_animation)
        
        # 设置定时器间隔（使用最小速度，默认100ms）
        self._animation_timer.start(50)  # 50ms刷新率，足够流畅
        self._is_running = True
    
    def _stop_animation_timer(self) -> None:
        """停止动画定时器"""
        if not self._is_running:
            return
        
        if self._animation_timer:
            self._animation_timer.stop()
        
        self._is_running = False
    
    def _update_animation(self) -> None:
        """更新所有动画线的状态"""
        for line in self._animated_lines.values():
            line.update_animation()
    
    def is_running(self) -> bool:
        """检查动画是否正在运行"""
        return self._is_running
    
    def get_line_count(self) -> int:
        """获取动画线数量"""
        return len(self._animated_lines)
    
    def create_rectangle_border(
        self,
        time_index: float,
        high_price: float,
        low_price: float,
        width: float = 2.0,
        color: tuple[int, int, int] = (255, 255, 0),
        animation_direction: AnimationLineDirection = AnimationLineDirection.FORWARD,
        dash_pattern: list[int] = None,
        line_width: int = 2,
        rect_id: Optional[str] = None
    ) -> str:
        """
        创建矩形边框（真正的封闭矩形）
        
        Args:
            time_index: K线的时间索引（中心位置）
            high_price: 矩形上边价格
            low_price: 矩形下边价格
            width: K线宽度（时间单位），默认2.0
            color: RGB颜色元组
            animation_direction: 动画方向
            dash_pattern: 虚线样式
            line_width: 线宽
            rect_id: 可选的矩形ID
            
        Returns:
            矩形ID字符串
        """
        if rect_id is None:
            rect_id = f"rect_{self._line_id_counter}"
            self._line_id_counter += 1
        
        # 计算矩形位置
        x = time_index - width / 2  # 左下角X
        y = low_price               # 左下角Y
        rect_width = width
        rect_height = high_price - low_price
        
        # 创建动画矩形
        rect = AnimatedRectangle(
            x=x,
            y=y,
            width=rect_width,
            height=rect_height,
            color=color,
            line_width=line_width,
            animation_direction=animation_direction,
            dash_pattern=dash_pattern or [8, 4]
        )
        
        # 添加矩形的4条边到图表
        if self._plot:
            for line in rect.get_lines():
                self._plot.addItem(line)
        
        # 保存到字典
        self._animated_lines[rect_id] = rect
        
        # 启动动画定时器
        self._start_animation_timer()
        
        return rect_id

