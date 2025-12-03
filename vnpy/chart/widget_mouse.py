"""ChartWidget 鼠标事件模块 Mixin

处理所有鼠标交互功能。
"""

from typing import TYPE_CHECKING
from time import time

from vnpy.trader.ui import QtGui, QtCore, QtWidgets
from vnpy.trader.object import OrderRequest, PositionData
from vnpy.trader.constant import Direction, Offset, OrderType, Exchange
from vnpy.trader.locale import _

from .widget_mixin_base import ChartWidgetMixinBase
from .price_line import PriceLineType

if TYPE_CHECKING:
    from .price_line import PriceLineItem


class ChartWidgetMouseMixin(ChartWidgetMixinBase):
    """鼠标事件处理相关功能 Mixin"""
    
    def _init_axis_drag_state(self) -> None:
        """初始化坐标轴拖拽状态变量"""
        if not hasattr(self, '_axis_drag_state'):
            self._axis_drag_state = {
                'is_dragging': False,
                'is_dragging_x_axis': False,  # 是否正在拖拽X轴
                'start_pos': None,
                'start_y_range': None,
                'start_x_range': None,  # 开始拖拽时的X轴范围
                'target_plot': None,
                'y_axis_manually_set': False  # Y轴是否被手动设置（拖拽后保持禁用自动更新）
            }
    
    def _is_mouse_on_right_axis(self, event: QtGui.QMouseEvent) -> tuple[bool, 'pg.PlotItem | None']:
        """检测鼠标是否在右侧坐标轴区域
        
        Args:
            event: 鼠标事件
            
        Returns:
            (是否在坐标轴区域, 对应的PlotItem)
        """
        import pyqtgraph as pg
        
        if not self._plots:
            return False, None
        
        # 获取鼠标位置（widget坐标系）
        widget_pos = event.pos()
        widget_width = self.width()
        
        # 右侧坐标轴宽度（从 widget.py 中的设置看是60像素）
        axis_width = 60
        
        # 检查鼠标是否在右侧坐标轴区域（基于widget坐标）
        axis_start_x = widget_width - axis_width
        
        # 如果鼠标不在坐标轴区域，直接返回
        if widget_pos.x() < axis_start_x:
            return False, None
        
        # 将widget坐标转换为场景坐标
        scene_pos = self.mapToScene(widget_pos)
        
        # 遍历所有plot，找到鼠标Y坐标所在的plot
        for plot_name, plot in self._plots.items():
            view_box = plot.getViewBox()
            if not view_box:
                continue
                
            # 获取plot的ViewBox在场景中的边界矩形
            vb_rect = view_box.sceneBoundingRect()
            if not vb_rect.isValid():
                continue
            
            # 检查鼠标Y坐标是否在plot的范围内
            if vb_rect.top() <= scene_pos.y() <= vb_rect.bottom():
                # 尝试获取坐标轴的实际边界矩形
                right_axis = plot.getAxis("right")
                if right_axis:
                    try:
                        axis_rect = right_axis.sceneBoundingRect()
                        if axis_rect.isValid():
                            # 检查鼠标是否在坐标轴矩形内，或者非常接近坐标轴
                            # 允许一些容差，因为坐标轴可能很窄
                            if axis_rect.contains(scene_pos):
                                return True, plot
                            # 如果鼠标在坐标轴附近（X坐标在坐标轴矩形内，Y坐标在plot范围内）
                            elif (axis_rect.left() <= scene_pos.x() <= axis_rect.right() and
                                  vb_rect.top() <= scene_pos.y() <= vb_rect.bottom()):
                                return True, plot
                    except Exception:
                        pass
                
                # 如果无法获取坐标轴矩形，只要鼠标在右侧60像素内且Y坐标在plot范围内，就认为是在坐标轴区域
                # 这样更可靠，因为坐标轴的精确位置可能因布局而异
                return True, plot
        
        return False, None
    
    def _is_mouse_on_bottom_axis(self, event: QtGui.QMouseEvent) -> tuple[bool, 'pg.PlotItem | None']:
        """检测鼠标是否在底部时间轴区域
        
        Args:
            event: 鼠标事件
            
        Returns:
            (是否在时间轴区域, 对应的PlotItem)
        """
        import pyqtgraph as pg
        
        if not self._plots:
            return False, None
        
        # 获取鼠标位置（widget坐标系）
        widget_pos = event.pos()
        widget_height = self.height()
        
        # 底部时间轴高度（大约40-50像素，可根据实际情况调整）
        axis_height = 50
        
        # 检查鼠标是否在底部时间轴区域（基于widget坐标）
        axis_start_y = widget_height - axis_height
        
        # 如果鼠标不在时间轴区域，直接返回
        if widget_pos.y() < axis_start_y:
            return False, None
        
        # 将widget坐标转换为场景坐标
        scene_pos = self.mapToScene(widget_pos)
        
        # 查找第一个有底部坐标轴的plot（通常是最下方的plot）
        # 从后往前查找，找到最后一个plot（通常是显示时间轴的plot）
        plot_list = list(self._plots.items())
        for plot_name, plot in reversed(plot_list):
            # 检查这个plot是否显示了底部坐标轴
            bottom_axis = plot.getAxis("bottom")
            if bottom_axis:
                # 获取plot的ViewBox在场景中的边界矩形
                view_box = plot.getViewBox()
                if view_box:
                    vb_rect = view_box.sceneBoundingRect()
                    if vb_rect.isValid():
                        # 检查鼠标X坐标是否在plot的范围内
                        if vb_rect.left() <= scene_pos.x() <= vb_rect.right():
                            try:
                                # 尝试获取坐标轴的实际边界矩形
                                axis_rect = bottom_axis.sceneBoundingRect()
                                if axis_rect.isValid() and axis_rect.contains(scene_pos):
                                    return True, plot
                            except Exception:
                                pass
                            
                            # 如果无法获取坐标轴矩形，只要鼠标在底部50像素内且X坐标在plot范围内，就认为是在时间轴区域
                            return True, plot
        
        return False, None
    
    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        """
        Handle mouse move event for price line hover detection and dragging.
        """
        # 初始化坐标轴拖拽状态
        self._init_axis_drag_state()
        
        # 处理X轴（时间轴）拖拽
        if self._axis_drag_state['is_dragging_x_axis']:
            target_plot = self._axis_drag_state['target_plot']
            if target_plot:
                import pyqtgraph as pg
                view_box = target_plot.getViewBox()
                if view_box:
                    # 计算拖动距离（像素）
                    current_pos = event.pos()
                    start_pos = self._axis_drag_state['start_pos']
                    if start_pos:
                        # 获取plot的ViewBox在场景中的边界矩形
                        plot_rect = view_box.sceneBoundingRect()
                        plot_width = plot_rect.width()
                        
                        if plot_width > 0:
                            # 获取初始的X轴范围
                            start_x_range = self._axis_drag_state['start_x_range']
                            if start_x_range:
                                x_min, x_max = start_x_range
                                x_range = x_max - x_min
                                
                                # 计算总拖动距离（像素）
                                # 向右拖动为正值（增加X坐标）
                                total_dx_pixels = current_pos.x() - start_pos.x()
                                
                                # 计算索引移动量：拖动距离转换为索引范围
                                # 向右拖动时，增加右侧索引（显示更多未来空间）
                                index_delta = (total_dx_pixels / plot_width) * x_range
                                
                                # 获取当前数据的总数
                                data_count = self._manager.get_count() if hasattr(self, '_manager') else 0
                                bar_count = self._bar_count if hasattr(self, '_bar_count') else 100
                                
                                # 计算新的右侧索引
                                start_right_ix = self._axis_drag_state.get('start_right_ix', data_count)
                                new_right_ix = start_right_ix + index_delta
                                
                                # 确保不超出数据范围（但可以超出以显示未来空间）
                                new_right_ix = max(bar_count, new_right_ix)
                                
                                # 更新右侧索引
                                self._right_ix = int(new_right_ix)
                                
                                # 计算新的X轴范围
                                new_min_ix = self._right_ix - bar_count
                                new_max_ix = self._right_ix
                                
                                # 如果右侧索引超出数据范围，需要增加未来空间
                                if self._right_ix > data_count:
                                    future_bars_needed = int(self._right_ix - data_count)
                                    if hasattr(self, '_future_bars'):
                                        # 增加未来空间，确保足够大
                                        self._future_bars = max(self._future_bars, future_bars_needed)
                                        # 更新plot限制，允许显示更多未来空间
                                        if hasattr(self, '_update_plot_limits'):
                                            self._update_plot_limits()
                                
                                # 添加调试日志（已注释：减少日志干扰）
                                # if hasattr(self, '_main_engine') and self._main_engine:
                                #     self._main_engine.write_log(
                                #         f"[ChartWidget] 拖拽时间轴: dx={total_dx_pixels:.1f}px, "
                                #         f"index_delta={index_delta:.2f}, "
                                #         f"right_ix={self._right_ix}, x_range=[{new_min_ix:.2f}, {new_max_ix:.2f}], "
                                #         f"future_bars={self._future_bars if hasattr(self, '_future_bars') else 0}",
                                #         "ChartWidget"
                                #     )
                                
                                # 直接设置所有plot的X轴范围
                                for plot in self._plots.values():
                                    plot.setRange(xRange=(new_min_ix, new_max_ix), padding=0)
            
            event.accept()
            return
        
        # 处理坐标轴拖拽（Y轴）
        if self._axis_drag_state['is_dragging']:
            target_plot = self._axis_drag_state['target_plot']
            if target_plot:
                import pyqtgraph as pg
                view_box = target_plot.getViewBox()
                if view_box:
                    # 计算拖动距离（像素）
                    current_pos = event.pos()
                    start_pos = self._axis_drag_state['start_pos']
                    if start_pos:
                        # 获取plot的ViewBox在场景中的边界矩形
                        plot_rect = view_box.sceneBoundingRect()
                        plot_height = plot_rect.height()
                        
                        if plot_height > 0:
                            # 获取初始的Y轴范围
                            start_y_range = self._axis_drag_state['start_y_range']
                            if start_y_range:
                                y_min, y_max = start_y_range
                                y_range = y_max - y_min
                                
                                # 计算总拖动距离（像素）
                                # 注意：使用widget坐标系的Y坐标差异
                                total_dy_pixels = start_pos.y() - current_pos.y()  # 向上拖动为正值
                                
                                # 计算价格移动量：拖动距离转换为价格范围
                                # 向上拖动时，价格范围向上移动（最小值增加，最大值增加）
                                # 增加灵敏度系数（3倍），使拖拽更容易控制
                                sensitivity = 3.0  # 灵敏度系数，值越大拖拽越快
                                price_delta = (total_dy_pixels / plot_height) * y_range * sensitivity
                                
                                # 更新Y轴范围（基于初始范围计算，避免累积误差）
                                new_y_min = y_min + price_delta
                                new_y_max = y_max + price_delta
                                
                                # 添加调试日志（帮助诊断问题）
                                if hasattr(self, '_main_engine') and self._main_engine:
                                    direction = "向上" if total_dy_pixels > 0 else "向下"
                                    self._main_engine.write_log(
                                        f"[ChartWidget] 拖拽坐标轴: {direction}, dy={total_dy_pixels:.1f}px, "
                                        f"price_delta={price_delta:.2f}, "
                                        f"y_range=[{new_y_min:.2f}, {new_y_max:.2f}], "
                                        f"start_pos={start_pos.y()}, current_pos={current_pos.y()}",
                                        "ChartWidget"
                                    )
                                
                                # 使用plot.setRange设置Y轴范围（与X轴拖拽保持一致的方式）
                                # 直接对PlotItem设置范围，而不是对ViewBox设置
                                target_plot.setRange(yRange=(new_y_min, new_y_max), padding=0)
            
            event.accept()
            return
        
        # Check if in drawing mode - show preview line
        if self._drawing_order_controller and self._drawing_order_controller.is_enabled():
            if self._first_plot:
                view_box = self._first_plot.getViewBox()
                if view_box:
                    scene_pos = self.mapToScene(event.pos())
                    view_pos = view_box.mapSceneToView(scene_pos)
                    price = view_pos.y()
                    
                    if price > 0:
                        self._drawing_order_controller.update_preview_line(price)
                    # 调用父类方法
                    import pyqtgraph as pg
                    pg.PlotWidget.mouseMoveEvent(self, event)
                    return

        # 检查鼠标是否在坐标轴区域（即使没有价格线拖拽处理器）
        # 先检查X轴（时间轴）
        is_on_x_axis, _ = self._is_mouse_on_bottom_axis(event)
        if is_on_x_axis:
            self.setCursor(QtCore.Qt.CursorShape.SizeHorCursor)
        else:
            # 再检查Y轴（价格轴）
            is_on_axis, _ = self._is_mouse_on_right_axis(event)
            if is_on_axis:
                self.setCursor(QtCore.Qt.CursorShape.SizeVerCursor)
            elif not self._price_line_drag_handler or not self._first_plot:
                # 调用父类方法
                import pyqtgraph as pg
                pg.PlotWidget.mouseMoveEvent(self, event)
                return

        # 确保 price_line_manager 已初始化
        if not hasattr(self, '_price_line_manager') or self._price_line_manager is None:
            # 使用 get_price_line_manager() 进行延迟初始化
            if hasattr(self, 'get_price_line_manager'):
                self._price_line_manager = self.get_price_line_manager()
            else:
                super().mouseMoveEvent(event)
                return

        # Get scene position
        scene_pos = self.mapToScene(event.pos())
        
        # Get all price lines
        all_lines = list(self._price_line_manager.get_all_lines().values())
        
        # If dragging, update drag position
        if self._price_line_drag_handler.is_dragging():
            new_price = self._price_line_drag_handler.convert_scene_to_price(scene_pos)
            if new_price is not None:
                # 如果是从入场线拖拽，更新预览线并判断类型
                if self._price_line_drag_handler.is_dragging_from_entry():
                    entry_line = self._price_line_drag_handler.get_entry_line()
                    if entry_line:
                        entry_price = entry_line.get_price()
                        direction = entry_line.get_direction()
                        
                        # 根据拖拽方向判断是止损还是止盈
                        if direction == "long":
                            # 多仓：价格低于入场价是止损，高于入场价是止盈
                            line_type = PriceLineType.STOP_LOSS if new_price < entry_price else PriceLineType.TAKE_PROFIT
                        else:
                            # 空仓：价格高于入场价是止损，低于入场价是止盈
                            line_type = PriceLineType.STOP_LOSS if new_price > entry_price else PriceLineType.TAKE_PROFIT
                        
                        # 添加调试日志，帮助排查类型判断问题
                        # 注释拖拽预览线类型判断日志，减少日志输出（拖拽时频繁打印）
                        # if hasattr(self, '_main_engine') and self._main_engine:
                        #     line_type_name = "止损" if line_type == PriceLineType.STOP_LOSS else "止盈"
                        #     price_diff = new_price - entry_price
                        #     position_desc = "上方" if price_diff > 0 else "下方"
                        #     self._main_engine.write_log(
                        #         f"[ChartWidget] 拖拽预览线类型判断: 入场价={entry_price:.2f}, "
                        #         f"拖拽价格={new_price:.2f} ({position_desc}, 价差={price_diff:+.2f}), "
                        #         f"方向={direction}, 判断为={line_type_name}",
                        #         "ChartWidget"
                        #     )
                        
                        preview_line = self._price_line_drag_handler.get_preview_line()
                        if preview_line:
                            # 更新预览线的类型和价格
                            old_line_type = preview_line.get_line_type()
                            if old_line_type != line_type:
                                # 类型改变，需要重新创建预览线
                                if preview_line.scene() is not None:
                                    view_box = self._first_plot.getViewBox()
                                    if view_box:
                                        view_box.removeItem(preview_line)
                                
                                # 删除旧预览线
                                for lid, line in self._price_line_manager.get_all_lines().items():
                                    if line == preview_line:
                                        self._price_line_manager.delete_line(lid)
                                        break
                                
                                # 创建新预览线
                                preview_line_id = self._price_line_manager.create_line(
                                    price=new_price,
                                    line_type=line_type,
                                    direction=direction,
                                    movable=True,
                                    price_precision=self._price_precision
                                )
                                preview_line = self._price_line_manager.get_line(preview_line_id)
                                if preview_line and self._first_plot:
                                    self._first_plot.addItem(preview_line)
                                    self._price_line_drag_handler.set_preview_line(preview_line)
                            else:
                                # 类型相同，只更新价格
                                preview_line.set_price(new_price, self._price_precision)
                        else:
                            # 没有预览线，创建新的
                            preview_line_id = self._price_line_manager.create_line(
                                price=new_price,
                                line_type=line_type,
                                direction=direction,
                                movable=True,
                                price_precision=self._price_precision
                            )
                            preview_line = self._price_line_manager.get_line(preview_line_id)
                            if preview_line and self._first_plot:
                                self._first_plot.addItem(preview_line)
                                self._price_line_drag_handler.set_preview_line(preview_line)
                else:
                    # 正常拖拽
                    self._price_line_drag_handler.update_drag(new_price)
                    # 如果拖拽的是挂单线，实时更新关联的止损/止盈线
                    dragging_line = self._price_line_drag_handler.get_dragging_line()
                    if dragging_line:
                        self._update_related_lines_on_drag(dragging_line, new_price)
        else:
            # 检查鼠标是否在坐标轴区域（用于显示光标）
            is_on_x_axis, _ = self._is_mouse_on_bottom_axis(event)
            if is_on_x_axis:
                self.setCursor(QtCore.Qt.CursorShape.SizeHorCursor)
            else:
                is_on_axis, _ = self._is_mouse_on_right_axis(event)
                if is_on_axis:
                    self.setCursor(QtCore.Qt.CursorShape.SizeVerCursor)
                else:
                    # Check for hover (包括入场线)
                    hovered_line = self._price_line_drag_handler.find_line_near_point(
                        scene_pos, all_lines, include_entry_lines=True
                    )
                    
                    # Change cursor style
                    if hovered_line:
                        self.setCursor(QtCore.Qt.CursorShape.SizeVerCursor)
                    else:
                        self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)

        # 调用父类方法
        import pyqtgraph as pg
        pg.PlotWidget.mouseMoveEvent(self, event)
    
    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        """
        Handle mouse press event to start dragging price line or create order in drawing mode.
        """
        # Only handle left button
        if event.button() != QtCore.Qt.MouseButton.LeftButton:
            # 调用父类方法
            import pyqtgraph as pg
            pg.PlotWidget.mousePressEvent(self, event)
            return
        
        # 初始化坐标轴拖拽状态
        self._init_axis_drag_state()
        
        # 检查是否点击了底部时间轴区域（X轴拖拽）
        is_on_x_axis, target_plot_x = self._is_mouse_on_bottom_axis(event)
        if is_on_x_axis and target_plot_x:
            import pyqtgraph as pg
            view_box = target_plot_x.getViewBox()
            if view_box:
                # 开始X轴拖拽
                self._axis_drag_state['is_dragging_x_axis'] = True
                self._axis_drag_state['start_pos'] = event.pos()
                self._axis_drag_state['target_plot'] = target_plot_x
                view_range = view_box.viewRange()
                if view_range:
                    self._axis_drag_state['start_x_range'] = view_range[0]
                    # 保存开始时的右侧索引
                    self._axis_drag_state['start_right_ix'] = self._right_ix if hasattr(self, '_right_ix') else 0
                
                # 添加调试日志
                if hasattr(self, '_main_engine') and self._main_engine:
                    self._main_engine.write_log(
                        f"[ChartWidget] 开始拖拽时间轴: 位置={event.pos()}, "
                        f"x_range={self._axis_drag_state['start_x_range']}, "
                        f"start_right_ix={self._axis_drag_state['start_right_ix']}",
                        "ChartWidget"
                    )
                
                # 改变鼠标光标
                self.setCursor(QtCore.Qt.CursorShape.SizeHorCursor)
                event.accept()
                return
        
        # 检查是否点击了右侧坐标轴区域（Y轴拖拽）
        is_on_axis, target_plot = self._is_mouse_on_right_axis(event)
        if is_on_axis and target_plot:
            import pyqtgraph as pg
            view_box = target_plot.getViewBox()
            if view_box:
                # 开始坐标轴拖拽
                self._axis_drag_state['is_dragging'] = True
                self._axis_drag_state['start_pos'] = event.pos()
                self._axis_drag_state['target_plot'] = target_plot
                view_range = view_box.viewRange()
                if view_range:
                    self._axis_drag_state['start_y_range'] = view_range[1]
                
                # 禁用Y轴自动范围更新，防止拖拽时被自动重置
                view_box.disableAutoRange(axis='y')
                # 标记Y轴已被手动设置
                self._axis_drag_state['y_axis_manually_set'] = True
                
                # 放宽Y轴限制，允许无限制拖拽（类似X轴有未来空间的概念）
                # 在拖拽时移除Y轴限制，允许用户自由拖拽到任何位置
                if hasattr(self, '_item_plot_map') and target_plot in self._item_plot_map.values():
                    # 找到对应的item
                    for item, plot in self._item_plot_map.items():
                        if plot == target_plot:
                            # 获取当前的limits，只保留X轴限制，移除Y轴限制
                            # 通过设置一个非常大的值来实现无限制
                            # 或者不设置yMin和yMax参数
                            import sys
                            max_float = sys.float_info.max
                            min_float = -sys.float_info.max
                            
                            # 获取当前X轴限制（如果有）
                            view_box = target_plot.getViewBox()
                            if view_box:
                                # 设置Y轴为无限制（使用非常大的值）
                                target_plot.setLimits(
                                    yMin=min_float,  # 无最小值限制
                                    yMax=max_float   # 无最大值限制
                                )
                            break
                
                # 添加调试日志
                if hasattr(self, '_main_engine') and self._main_engine:
                    self._main_engine.write_log(
                        f"[ChartWidget] 开始拖拽坐标轴: 位置={event.pos()}, "
                        f"widget_width={self.width()}, "
                        f"y_range={self._axis_drag_state['start_y_range']}",
                        "ChartWidget"
                    )
                
                # 改变鼠标光标
                self.setCursor(QtCore.Qt.CursorShape.SizeVerCursor)
                event.accept()
                return

        # 添加调试日志（仅在开发时启用）
        if hasattr(self, '_main_engine') and self._main_engine:
            self._main_engine.write_log(
                f"[ChartWidget] mousePressEvent: 位置={event.pos()}, "
                f"drag_handler={self._price_line_drag_handler is not None}, "
                f"first_plot={self._first_plot is not None}, "
                f"price_line_manager={hasattr(self, '_price_line_manager') and self._price_line_manager is not None}",
                "ChartWidget"
            )

        # 优先检查是否在画线下单模式
        # 在画线下单模式下，任何点击都应该弹出下单对话框，不允许从入场线生成止损/止盈线
        if self._drawing_order_controller and self._drawing_order_controller.is_enabled():
            # Handle drawing order mode
            if self._first_plot:
                # Get click price
                view_box = self._first_plot.getViewBox()
                if view_box:
                    scene_pos = self.mapToScene(event.pos())
                    view_pos = view_box.mapSceneToView(scene_pos)
                    price = view_pos.y()
                    
                    if price > 0:
                        # 注释掉画线下单的详细调试日志，减少日志输出
                        # if hasattr(self, '_main_engine') and self._main_engine:
                        #     self._main_engine.write_log(
                        #         f"[ChartWidget] 画线下单模式点击: 价格={price:.2f}, "
                        #         f"回调存在={hasattr(self, '_on_drawing_click')}, "
                        #         f"回调不为None={hasattr(self, '_on_drawing_click') and self._on_drawing_click is not None}",
                        #         "ChartWidget"
                        #     )
                        
                        # Show preview line
                        self._drawing_order_controller.show_preview_line(price, "long")
                        
                        # Call callback for order dialog (will be handled by parent widget)
                        if hasattr(self, '_on_drawing_click') and self._on_drawing_click:
                            # 注释掉画线下单回调日志，减少日志输出
                            # if hasattr(self, '_main_engine') and self._main_engine:
                            #     self._main_engine.write_log(
                            #         f"[ChartWidget] 调用画线下单回调: 价格={price:.2f}",
                            #         "ChartWidget"
                            #     )
                            self._on_drawing_click(price)
                        else:
                            # 如果回调未设置，记录警告
                            if hasattr(self, '_main_engine') and self._main_engine:
                                self._main_engine.write_log(
                                    f"[ChartWidget] 警告: 画线下单模式已启用，但回调未设置。请调用 set_drawing_click_callback() 设置回调。",
                                    "ChartWidget"
                                )
                        event.accept()
                        return

        if not self._price_line_drag_handler or not self._first_plot:
            # 调用父类方法
            import pyqtgraph as pg
            pg.PlotWidget.mousePressEvent(self, event)
            return

        # 确保 price_line_manager 已初始化
        if not hasattr(self, '_price_line_manager') or self._price_line_manager is None:
            # 使用 get_price_line_manager() 进行延迟初始化
            if hasattr(self, 'get_price_line_manager'):
                self._price_line_manager = self.get_price_line_manager()
            else:
                # 调用父类方法
                import pyqtgraph as pg
                pg.PlotWidget.mousePressEvent(self, event)
                return

        # Get scene position
        scene_pos = self.mapToScene(event.pos())
        
        # Get all price lines
        all_lines = list(self._price_line_manager.get_all_lines().values())
        
        # Find line near click position (优先检查是否可以拖拽)
        clicked_line = self._price_line_drag_handler.find_line_near_point(
            scene_pos, all_lines
        )
        
        # 如果点击的是可拖拽的价格线，优先处理拖拽
        if clicked_line and clicked_line.movable:
            self._price_line_drag_handler.start_drag(clicked_line)
            event.accept()
            return
        
        # 如果第一次查找没有找到线，或者找到的是不可移动的线，尝试查找入场线（包括不可移动的）
        if clicked_line is None or (clicked_line and not clicked_line.movable):
            # 尝试查找入场线（包括不可移动的）
            entry_line = self._price_line_drag_handler.find_line_near_point(
                scene_pos, all_lines, include_entry_lines=True
            )
            # 如果找到的是入场线，使用它
            if entry_line and entry_line.get_line_type() == PriceLineType.ENTRY:
                clicked_line = entry_line
        
        # 如果点击的是入场线，开始从入场线拖拽生成止损/止盈线
        # 注意：只有在画线下单未启用时才允许此操作
        if clicked_line and clicked_line.get_line_type() == PriceLineType.ENTRY:
            # 从入场线开始拖拽
            self._price_line_drag_handler.start_drag_from_entry(clicked_line)
            event.accept()
            return
        
        # 如果没有找到任何线，调用父类处理
        # 注意：由于 MRO 问题，不能直接使用 super()，直接调用 PlotWidget 的方法
        import pyqtgraph as pg
        pg.PlotWidget.mousePressEvent(self, event)
    
    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        """
        Handle mouse release event to end dragging price line.
        """
        # 初始化坐标轴拖拽状态
        self._init_axis_drag_state()
        
        # 结束X轴拖拽
        if self._axis_drag_state['is_dragging_x_axis']:
            self._axis_drag_state['is_dragging_x_axis'] = False
            self._axis_drag_state['start_pos'] = None
            self._axis_drag_state['start_x_range'] = None
            self._axis_drag_state['start_right_ix'] = None
            self._axis_drag_state['target_plot'] = None
            
            # 恢复鼠标光标
            self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
            
            # X轴拖拽结束后，可能需要更新未来空间
            # 计算当前需要的未来空间
            data_count = self._manager.get_count() if hasattr(self, '_manager') else 0
            if self._right_ix > data_count:
                future_bars = int(self._right_ix - data_count)
                if hasattr(self, '_future_bars'):
                    self._future_bars = future_bars
                    if hasattr(self, '_update_plot_limits'):
                        self._update_plot_limits()
            
            # 不直接返回，继续处理其他拖拽
        
        # 结束坐标轴拖拽（Y轴）
        if self._axis_drag_state['is_dragging']:
            self._axis_drag_state['is_dragging'] = False
            self._axis_drag_state['start_pos'] = None
            self._axis_drag_state['start_y_range'] = None
            target_plot = self._axis_drag_state['target_plot']
            self._axis_drag_state['target_plot'] = None
            
            # 保持禁用自动范围更新，因为用户已经手动设置了范围
            # 这样用户手动拖拽的范围不会被自动重置
            if target_plot:
                view_box = target_plot.getViewBox()
                if view_box:
                    view_box.disableAutoRange(axis='y')
            
            # 恢复鼠标光标
            self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
            
            # 不直接返回，继续处理其他拖拽（如价格线拖拽）
        
        from .price_line import PriceLineType
        
        if self._price_line_drag_handler and self._price_line_drag_handler.is_dragging():
            # 如果是从入场线拖拽，创建止损/止盈线
            if self._price_line_drag_handler.is_dragging_from_entry():
                entry_line = self._price_line_drag_handler.get_entry_line()
                preview_line = self._price_line_drag_handler.get_preview_line()
                final_price = self._price_line_drag_handler.end_drag()
                
                if entry_line and preview_line and final_price is not None:
                    # 获取入场线的ID
                    # 确保 price_line_manager 已初始化
                    if not hasattr(self, '_price_line_manager') or self._price_line_manager is None:
                        if hasattr(self, 'get_price_line_manager'):
                            self._price_line_manager = self.get_price_line_manager()
                        else:
                            # 调用父类方法
                            import pyqtgraph as pg
                            pg.PlotWidget.mouseReleaseEvent(self, event)
                            return
                    manager = self._price_line_manager
                    entry_line_id = None
                    for lid, line in manager.get_all_lines().items():
                        if line == entry_line:
                            entry_line_id = lid
                            break
                    
                    if entry_line_id:
                        # 获取预览线的类型和方向
                        line_type = preview_line.get_line_type()
                        direction = preview_line.get_direction()
                        
                        # ✅ 重新验证类型判断（基于最终价格，确保类型正确）
                        entry_price = entry_line.get_price()
                        if direction == "long":
                            # 多仓：价格低于入场价是止损，高于入场价是止盈
                            expected_line_type = PriceLineType.STOP_LOSS if final_price < entry_price else PriceLineType.TAKE_PROFIT
                        else:
                            # 空仓：价格高于入场价是止损，低于入场价是止盈
                            expected_line_type = PriceLineType.STOP_LOSS if final_price > entry_price else PriceLineType.TAKE_PROFIT
                        
                        # 如果预览线类型与预期不符，使用预期类型（防止类型判断错误）
                        if line_type != expected_line_type:
                            if hasattr(self, '_main_engine') and self._main_engine:
                                old_type_name = "止损" if line_type == PriceLineType.STOP_LOSS else "止盈"
                                new_type_name = "止损" if expected_line_type == PriceLineType.STOP_LOSS else "止盈"
                                self._main_engine.write_log(
                                    f"[ChartWidget] 预览线类型修正: 入场价={entry_price:.2f}, 最终价格={final_price:.2f}, "
                                    f"方向={direction}, 预览线类型={old_type_name} -> 修正为={new_type_name}",
                                    "ChartWidget"
                                )
                            line_type = expected_line_type
                        
                        # 删除预览线
                        preview_line_id = None
                        for lid, line in manager.get_all_lines().items():
                            if line == preview_line:
                                preview_line_id = lid
                                break
                        
                        if preview_line_id:
                            # 从图表中移除预览线（如果还在plot中）
                            if preview_line.scene() is not None and self._first_plot:
                                try:
                                    self._first_plot.removeItem(preview_line)
                                except Exception:
                                    pass
                            
                            # 删除预览线，创建真正的止损/止盈线
                            manager.delete_line(preview_line_id)
                            
                            # 清理拖拽处理器的预览线引用
                            if self._price_line_drag_handler:
                                self._price_line_drag_handler._preview_line = None
                            
                            # ✅ 价格合理性检查：防止止盈线设置在错误位置导致立即触发
                            current_price = 0
                            if hasattr(self, '_main_engine') and self._main_engine and hasattr(self, '_vt_symbol') and self._vt_symbol:
                                tick = self._main_engine.get_tick(self._vt_symbol)
                                if tick and tick.last_price > 0:
                                    current_price = tick.last_price
                            
                            # 检查止盈线价格是否合理
                            price_warning = ""
                            if line_type == PriceLineType.TAKE_PROFIT and current_price > 0:
                                if direction == "long":
                                    # 多单止盈：止盈价应该 > 当前价
                                    if final_price <= current_price:
                                        price_warning = f"⚠️ 多单止盈价 {final_price:.0f} ≤ 当前价 {current_price:.0f}，创建后可能立即触发平仓"
                                else:
                                    # 空单止盈：止盈价应该 < 当前价
                                    if final_price >= current_price:
                                        price_warning = f"⚠️ 空单止盈价 {final_price:.0f} ≥ 当前价 {current_price:.0f}，创建后可能立即触发平仓"
                            
                            # 如果有价格警告，弹窗提示用户
                            if price_warning and hasattr(self, '_main_engine') and self._main_engine:
                                self._main_engine.write_log(price_warning, "ChartWidget")
                                from vnpy.trader.ui import QtWidgets
                                reply = QtWidgets.QMessageBox.warning(
                                    self,
                                    "止盈价格警告",
                                    f"{price_warning}\n\n是否仍然创建？",
                                    QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                                    QtWidgets.QMessageBox.StandardButton.No
                                )
                                if reply == QtWidgets.QMessageBox.StandardButton.No:
                                    # 用户取消创建，清理预览线
                                    if preview_line and self._first_plot:
                                        try:
                                            self._first_plot.removeItem(preview_line)
                                        except Exception:
                                            pass
                                        manager.delete_line(preview_line_id)
                                    event.accept()
                                    return
                            
                            # 创建止损/止盈线
                            new_line_id = manager.create_line(
                                price=final_price,
                                line_type=line_type,
                                direction=direction,
                                movable=True,
                                price_precision=self._price_precision
                            )
                            
                            new_line = manager.get_line(new_line_id)
                            # 设置创建时间（用于防止创建后立即触发）
                            if new_line:
                                new_line.set_creation_time()
                            if new_line and self._first_plot:
                                self._first_plot.addItem(new_line)
                                
                                # 获取入场线的手数（如果是合并显示的，获取总持仓手数）
                                entry_volume = entry_line.get_volume()
                                
                                # 如果入场线手数为0或很小，尝试从 PositionHolding 获取总持仓手数
                                if entry_volume <= 0.01:
                                    if hasattr(self, '_position_holdings') and self._position_holdings:
                                        holding = self._position_holdings.get(direction)
                                        if holding:
                                            # 计算总持仓手数
                                            total_volume = sum(e.volume for e in holding.get_all_entries())
                                            if total_volume > 0:
                                                entry_volume = total_volume
                                
                                # 为创建的止损/止盈线设置手数
                                if entry_volume > 0:
                                    new_line.set_volume(entry_volume)
                                    if hasattr(self, '_main_engine') and self._main_engine:
                                        line_type_name = "止损" if line_type == PriceLineType.STOP_LOSS else "止盈"
                                        self._main_engine.write_log(
                                            f"[入场线管理] 从入场线创建{line_type_name}线: 价格={final_price:.2f}, "
                                            f"入场线ID={entry_line_id}, 手数={entry_volume}",
                                            "Chart"
                                        )
                                
                                # 存储入场线和止损/止盈线的关联关系
                                if not hasattr(self, '_entry_line_relations'):
                                    self._entry_line_relations = {}
                                
                                if entry_line_id not in self._entry_line_relations:
                                    self._entry_line_relations[entry_line_id] = {}
                                
                                if line_type == PriceLineType.STOP_LOSS:
                                    # 如果已有旧的止损线关联，先清理旧的关联关系和数据库记录
                                    old_stop_loss_id = self._entry_line_relations[entry_line_id].get("stop_loss")
                                    if old_stop_loss_id and old_stop_loss_id != new_line_id:
                                        # 删除数据库中的旧关联关系
                                        if self._price_line_database:
                                            self._price_line_database.delete_relation(entry_line_id, "stop_loss")
                                        # 删除旧的止损线（如果存在）
                                        old_stop_loss_line = manager.get_line(old_stop_loss_id)
                                        if old_stop_loss_line:
                                            # 从图表中移除
                                            if old_stop_loss_line.scene() is not None and self._first_plot:
                                                try:
                                                    self._first_plot.removeItem(old_stop_loss_line)
                                                except Exception:
                                                    pass
                                            # 从管理器中删除
                                            manager.delete_line(old_stop_loss_id)
                                            # 清理数据库中的关联关系（通过关联线ID删除）
                                            if self._price_line_database and hasattr(self._price_line_database, 'delete_relations_by_related_line_id'):
                                                self._price_line_database.delete_relations_by_related_line_id(old_stop_loss_id)
                                            if hasattr(self, '_main_engine') and self._main_engine:
                                                self._main_engine.write_log(
                                                    f"[入场线管理] 已删除旧的止损线关联: {entry_line_id} -> {old_stop_loss_id}",
                                                    "Chart"
                                                )
                                    
                                    self._entry_line_relations[entry_line_id]["stop_loss"] = new_line_id
                                    # 保存关联关系到数据库
                                    if self._price_line_database:
                                        success = self._price_line_database.save_relation(
                                            entry_line_id, new_line_id, "stop_loss"
                                        )
                                        if hasattr(self, '_main_engine') and self._main_engine:
                                            if success:
                                                self._main_engine.write_log(
                                                    f"[入场线管理] 已保存止损线关联关系到数据库: {entry_line_id} -> {new_line_id}",
                                                    "Chart"
                                                )
                                            else:
                                                self._main_engine.write_log(
                                                    f"[入场线管理] 警告：保存止损线关联关系到数据库失败: {entry_line_id} -> {new_line_id}",
                                                    "Chart"
                                                )
                                elif line_type == PriceLineType.TAKE_PROFIT:
                                    # 如果已有旧的止盈线关联，先清理旧的关联关系和数据库记录
                                    old_take_profit_id = self._entry_line_relations[entry_line_id].get("take_profit")
                                    if old_take_profit_id and old_take_profit_id != new_line_id:
                                        # 删除数据库中的旧关联关系
                                        if self._price_line_database:
                                            self._price_line_database.delete_relation(entry_line_id, "take_profit")
                                        # 删除旧的止盈线（如果存在）
                                        old_take_profit_line = manager.get_line(old_take_profit_id)
                                        if old_take_profit_line:
                                            # 从图表中移除
                                            if old_take_profit_line.scene() is not None and self._first_plot:
                                                try:
                                                    self._first_plot.removeItem(old_take_profit_line)
                                                except Exception:
                                                    pass
                                            # 从管理器中删除
                                            manager.delete_line(old_take_profit_id)
                                            # 清理数据库中的关联关系（通过关联线ID删除）
                                            if self._price_line_database and hasattr(self._price_line_database, 'delete_relations_by_related_line_id'):
                                                self._price_line_database.delete_relations_by_related_line_id(old_take_profit_id)
                                            if hasattr(self, '_main_engine') and self._main_engine:
                                                self._main_engine.write_log(
                                                    f"[ChartWidget] 已删除旧的止盈线关联: {entry_line_id} -> {old_take_profit_id}",
                                                    "ChartWidget"
                                                )
                                    
                                    self._entry_line_relations[entry_line_id]["take_profit"] = new_line_id
                                    # 保存关联关系到数据库
                                    if self._price_line_database:
                                        success = self._price_line_database.save_relation(
                                            entry_line_id, new_line_id, "take_profit"
                                        )
                                        if hasattr(self, '_main_engine') and self._main_engine:
                                            if success:
                                                self._main_engine.write_log(
                                                    f"[ChartWidget] 已保存止盈线关联关系到数据库: {entry_line_id} -> {new_line_id}",
                                                    "ChartWidget"
                                                )
                                            else:
                                                self._main_engine.write_log(
                                                    f"[ChartWidget] 警告：保存止盈线关联关系到数据库失败: {entry_line_id} -> {new_line_id}",
                                                    "ChartWidget"
                                                )
                                
                                # 记录日志
                                if hasattr(self, '_main_engine') and self._main_engine:
                                    line_type_name = "止损" if line_type == PriceLineType.STOP_LOSS else "止盈"
                                    volume_info = f", 手数={entry_volume}" if entry_volume > 0 else ""
                                    self._main_engine.write_log(
                                        f"[ChartWidget] 从入场线创建{line_type_name}线: 价格={final_price:.2f}, "
                                        f"入场线ID={entry_line_id}{volume_info}",
                                        "ChartWidget"
                                    )
                
                event.accept()
                return
            
            # 正常拖拽处理
            dragging_line = self._price_line_drag_handler.get_dragging_line()
            final_price = self._price_line_drag_handler.end_drag()
            
            if dragging_line and final_price is not None:
                # 检查拖拽的是挂单线还是止损/止盈线
                line_type = dragging_line.get_line_type()
                
                if line_type == PriceLineType.PENDING:
                    # 如果拖拽的是挂单线，更新关联的止损/止盈线
                    self._update_related_lines_on_drag_end(dragging_line, final_price)
                elif line_type in (PriceLineType.STOP_LOSS, PriceLineType.TAKE_PROFIT):
                    # 如果拖拽的是止损/止盈线，更新保存的点数
                    self._update_points_on_line_drag(dragging_line, final_price, line_type)
                    
                    # ✅ 拖拽结束后，根据关联类型决定是否激活
                    if dragging_line:
                        # 获取拖拽线的ID
                        dragged_line_id = None
                        if self._price_line_manager:
                            all_lines = self._price_line_manager.get_all_lines()
                            for lid, line in all_lines.items():
                                if line == dragging_line:
                                    dragged_line_id = lid
                                    break
                        
                        # 判断是否关联挂单线
                        is_pending_related = False
                        if dragged_line_id and self._drawing_order_controller:
                            if hasattr(self._drawing_order_controller, '_pending_line_relations'):
                                # 遍历所有挂单线的关联关系
                                for pending_id, relations in self._drawing_order_controller._pending_line_relations.items():
                                    stop_loss_info = relations.get("stop_loss")
                                    take_profit_info = relations.get("take_profit")
                                    
                                    if (stop_loss_info and stop_loss_info.get("line_id") == dragged_line_id) or \
                                       (take_profit_info and take_profit_info.get("line_id") == dragged_line_id):
                                        is_pending_related = True
                                        break
                        
                        # 根据关联类型决定是否激活
                        if is_pending_related:
                            # 挂单关联的止损止盈线：保持未激活状态
                            # 不修改 creation_time（保持 None 或原值）
                            # 等待挂单成交后再激活
                            pass
                        else:
                            # 入场线关联或独立的止损止盈线：拖拽后激活
                            # 无论是刚创建的（已激活）还是之前创建的，
                            # 拖拽后都重新设置 creation_time（防止拖拽后立即触发）
                            dragging_line.set_creation_time()
            
            event.accept()
            return
        
        # 如果没有正在拖拽，调用父类处理
        # 注意：由于 MRO 问题，不能直接使用 super()，直接调用 PlotWidget 的方法
        import pyqtgraph as pg
        pg.PlotWidget.mouseReleaseEvent(self, event)
    
    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:
        """
        Handle double click event for price line actions.
        
        - Double click Y axis: Reset Y axis range to data range
        - Double click pending line: Delete entire pending order
        - Double click entry line: Close position
        - Double click stop loss/take profit line: Delete the line
        """
        # 初始化坐标轴拖拽状态
        self._init_axis_drag_state()
        
        # 检查是否双击了右侧坐标轴区域（Y轴）
        is_on_axis, target_plot = self._is_mouse_on_right_axis(event)
        if is_on_axis and target_plot:
            import pyqtgraph as pg
            view_box = target_plot.getViewBox()
            if view_box:
                # 双击Y轴：重置Y轴范围到数据范围
                # 获取当前X轴范围
                view_range = view_box.viewRange()
                if view_range:
                    min_ix = max(0, int(view_range[0][0]))
                    max_ix = min(self._manager.get_count(), int(view_range[0][1]))
                    
                    # 获取数据范围
                    if hasattr(self, '_item_plot_map'):
                        for item, plot in self._item_plot_map.items():
                            if plot == target_plot:
                                y_range = item.get_y_range(min_ix, max_ix)
                                y_min, y_max = y_range
                                
                                # 重置Y轴范围到数据范围
                                target_plot.setRange(yRange=y_range, padding=0)
                                
                                # 清除手动设置标志，允许自动更新
                                if hasattr(self, '_axis_drag_state'):
                                    self._axis_drag_state['y_axis_manually_set'] = False
                                
                                # 恢复自动范围更新
                                view_box.enableAutoRange(axis='y')
                                
                                # 恢复Y轴限制到数据范围
                                target_plot.setLimits(
                                    yMin=y_min,
                                    yMax=y_max
                                )
                                
                                # 添加日志
                                if hasattr(self, '_main_engine') and self._main_engine:
                                    self._main_engine.write_log(
                                        f"[ChartWidget] 双击Y轴：重置Y轴范围到数据范围 [{y_min:.2f}, {y_max:.2f}]",
                                        "ChartWidget"
                                    )
                                
                                event.accept()
                                return
                
                event.accept()
                return
        
        if not self._price_line_drag_handler or not self._first_plot:
            super().mouseDoubleClickEvent(event)
            return

        # 如果正在从入场线拖拽，先取消拖拽（避免双击时创建预览线）
        if self._price_line_drag_handler.is_dragging_from_entry():
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[ChartWidget] 双击事件: 检测到正在从入场线拖拽，先取消拖拽",
                    "ChartWidget"
                )
            # 取消拖拽并删除预览线
            self._price_line_drag_handler.cancel_drag()
            # 删除预览线（如果存在）
            preview_line = self._price_line_drag_handler.get_preview_line()
            if preview_line:
                # 查找预览线的ID并删除
                # 确保 price_line_manager 已初始化
                if not hasattr(self, '_price_line_manager') or self._price_line_manager is None:
                    if hasattr(self, 'get_price_line_manager'):
                        self._price_line_manager = self.get_price_line_manager()
                    else:
                        super().mouseDoubleClickEvent(event)
                        return
                manager = self._price_line_manager
                for lid, line in manager.get_all_lines().items():
                    if line == preview_line:
                        # 从 plot 中移除
                        if preview_line.scene() is not None and self._first_plot:
                            try:
                                self._first_plot.removeItem(preview_line)
                            except Exception:
                                pass
                        # 从管理器中删除
                        manager.delete_line(lid)
                        break

        # Get scene position
        scene_pos = self.mapToScene(event.pos())
        
        # 确保 price_line_manager 已初始化
        if not hasattr(self, '_price_line_manager') or self._price_line_manager is None:
            if hasattr(self, 'get_price_line_manager'):
                self._price_line_manager = self.get_price_line_manager()
            else:
                super().mouseDoubleClickEvent(event)
                return
        
        # Get all price lines（在取消拖拽后重新获取，确保不包含刚创建的预览线）
        all_lines = list(self._price_line_manager.get_all_lines().values())
        
        # Find line near click position (include entry lines for double click)
        clicked_line = self._price_line_drag_handler.find_line_near_point(
            scene_pos, all_lines, include_entry_lines=True
        )
        
        # 添加调试日志
        if hasattr(self, '_main_engine') and self._main_engine:
            self._main_engine.write_log(
                f"[鼠标事件] 双击事件: 场景位置={scene_pos}, 价格线数量={len(all_lines)}, "
                f"找到价格线={clicked_line is not None}",
                "Chart"
            )
        
        if clicked_line:
            line_type = clicked_line.get_line_type()
            
            # 添加调试日志
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[鼠标事件] 双击事件: 找到价格线类型={line_type.value if hasattr(line_type, 'value') else line_type}",
                    "Chart"
                )
            
            # 如果找到的是止损/止盈线，检查附近是否有入场线（优先处理入场线）
            if line_type in (PriceLineType.STOP_LOSS, PriceLineType.TAKE_PROFIT):
                # 手动查找附近的入场线（使用相同的阈值）
                view_box = self._first_plot.getViewBox() if self._first_plot else None
                if view_box:
                    view_pos = view_box.mapSceneToView(scene_pos)
                    mouse_price = view_pos.y()
                    
                    # 计算阈值（价格单位）
                    view_range = view_box.viewRange()
                    if view_range:
                        y_range = view_range[1]
                        y_height = y_range[1] - y_range[0]
                        plot_height = view_box.height()
                        if plot_height > 0:
                            price_per_pixel = y_height / plot_height
                            hover_threshold_pixels = self._price_line_drag_handler._hover_threshold if hasattr(self._price_line_drag_handler, '_hover_threshold') else 10
                            price_threshold = hover_threshold_pixels * price_per_pixel
                            
                            # 查找附近的入场线
                            nearby_entry_line = None
                            min_entry_distance = float('inf')
                            
                            for line in all_lines:
                                if line.get_line_type() == PriceLineType.ENTRY:
                                    line_price = line.get_price()
                                    distance = abs(mouse_price - line_price)
                                    
                                    if distance < price_threshold and distance < min_entry_distance:
                                        min_entry_distance = distance
                                        nearby_entry_line = line
                            
                            # 如果找到附近的入场线，优先处理入场线
                            if nearby_entry_line:
                                if hasattr(self, '_main_engine') and self._main_engine:
                                    self._main_engine.write_log(
                                        f"[鼠标事件] 双击事件: 找到止损/止盈线，但附近有入场线（距离={min_entry_distance:.2f}），优先处理入场线",
                                        "Chart"
                                    )
                                clicked_line = nearby_entry_line
                                line_type = PriceLineType.ENTRY
            
            # Find line ID in manager
            # 使用对象引用比较（优先）
            line_id = None
            clicked_price = clicked_line.get_price()
            clicked_direction = clicked_line.get_direction()
            
            # 确保 price_line_manager 已初始化（应该已经初始化，但为了安全起见再次检查）
            if not hasattr(self, '_price_line_manager') or self._price_line_manager is None:
                if hasattr(self, 'get_price_line_manager'):
                    self._price_line_manager = self.get_price_line_manager()
                else:
                    # 调用父类方法
                    import pyqtgraph as pg
                    pg.PlotWidget.mouseDoubleClickEvent(self, event)
                    return
            
            # 首先尝试对象引用比较
            for lid, line in self._price_line_manager.get_all_lines().items():
                if line == clicked_line:
                    line_id = lid
                    if hasattr(self, '_main_engine') and self._main_engine:
                        self._main_engine.write_log(
                            f"[鼠标事件] 双击事件: 通过对象引用找到line_id={line_id}",
                            "Chart"
                        )
                    break
            
            # 如果对象引用比较失败，使用价格、类型和方向匹配（备用方案）
            if not line_id:
                for lid, line in self._price_line_manager.get_all_lines().items():
                    if (line.get_line_type() == line_type and 
                        abs(line.get_price() - clicked_price) < 0.01 and
                        line.get_direction() == clicked_direction):
                        line_id = lid
                        if hasattr(self, '_main_engine') and self._main_engine:
                            self._main_engine.write_log(
                                f"[鼠标事件] 双击事件: 通过价格和类型匹配找到line_id={line_id} "
                                f"(价格={clicked_price}, 类型={line_type.value if hasattr(line_type, 'value') else line_type}, 方向={clicked_direction})",
                                "Chart"
                            )
                        break
            
            # 添加调试日志
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[鼠标事件] 双击事件: line_id={line_id}, 价格线管理器中的线数量={len(self._price_line_manager.get_all_lines())}, "
                    f"点击的价格={clicked_price}, 方向={clicked_direction}",
                    "Chart"
                )
            
            if line_id:
                if line_type == PriceLineType.PENDING:
                    # Double click pending line: Delete entire pending order with confirmation
                    from vnpy.trader.ui import QtWidgets
                    from vnpy.trader.locale import _
                    
                    reply = QtWidgets.QMessageBox.question(
                        self,
                        _("确认删除"),
                        _("确定要删除挂单线吗？\n这将同时撤销关联的订单。"),
                        QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                        QtWidgets.QMessageBox.StandardButton.No
                    )
                    
                    if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                        # Get order ID if linked
                        vt_orderid = None
                        if self._drawing_order_controller:
                            vt_orderid = self._drawing_order_controller.get_order_id_for_line(line_id)
                            
                            # 删除关联的止损线和止盈线
                            if hasattr(self._drawing_order_controller, '_pending_line_relations'):
                                relations = self._drawing_order_controller._pending_line_relations.get(line_id)
                                if relations:
                                    # 删除止损线
                                    stop_loss_info = relations.get("stop_loss")
                                    if stop_loss_info and stop_loss_info.get("line_id"):
                                        stop_loss_line_id = stop_loss_info["line_id"]
                                        # 使用统一的价格线删除接口，确保同时从突破监控中注销
                                        self.remove_price_line(stop_loss_line_id)
                                    # 删除止盈线
                                    take_profit_info = relations.get("take_profit")
                                    if take_profit_info and take_profit_info.get("line_id"):
                                        take_profit_line_id = take_profit_info["line_id"]
                                        # 使用统一的价格线删除接口，确保同时从突破监控中注销
                                        self.remove_price_line(take_profit_line_id)
                                # 清理关联关系
                                self._drawing_order_controller._pending_line_relations.pop(line_id, None)
                            
                            # 清理挂单参数（如果存在）
                            if hasattr(self._drawing_order_controller, '_pending_order_params'):
                                self._drawing_order_controller._pending_order_params.pop(line_id, None)
                            
                            # 取消注册价格突破监控
                            if self._breakthrough_monitor:
                                self._breakthrough_monitor.unregister_line(line_id)
                            
                            if vt_orderid:
                                # Cancel order if exists
                                # Note: This requires access to main_engine, which should be set via set_main_engine
                                if self._main_engine:
                                    try:
                                        # Get order to cancel
                                        order = self._main_engine.get_order(vt_orderid)
                                        if order:
                                            from vnpy.trader.object import CancelRequest
                                            cancel_req = CancelRequest(
                                                orderid=order.orderid,
                                                symbol=order.symbol,
                                                exchange=order.exchange
                                            )
                                            self._main_engine.cancel_order(cancel_req, order.gateway_name)
                                    except Exception as e:
                                        print(f"Error canceling order {vt_orderid}: {e}")
                            
                            # Remove line from controller (this will also remove mappings)
                            if vt_orderid:
                                self._drawing_order_controller.remove_order_line(vt_orderid)
                                # 确保挂单线本身也通过统一接口删除（包括突破监控反注册）
                                self.remove_price_line(line_id)
                            else:
                                # If no order linked, just remove the line
                                self.remove_price_line(line_id)
                        else:
                            # No controller, just remove the line
                            self.get_price_line_manager().delete_line(line_id)
                elif line_type == PriceLineType.ENTRY:
                    # Double click entry line: Close position
                    # 添加调试日志
                    if hasattr(self, '_main_engine') and self._main_engine:
                        drawing_enabled = self._drawing_order_controller.is_enabled() if self._drawing_order_controller else False
                        self._main_engine.write_log(
                            f"[鼠标事件] 双击入场线: line_id={line_id}, 画线下单状态={drawing_enabled}, "
                            f"入场线价格={clicked_line.get_price()}, 方向={clicked_line.get_direction()}, 手数={clicked_line.get_volume()}",
                            "Chart"
                        )
                    
                    # 只有在画线下单未启动时才触发平仓
                    if not self._drawing_order_controller or not self._drawing_order_controller.is_enabled():
                        # 防抖检查：防止短时间内对同一入场线重复触发平仓
                        current_time = time()
                        if line_id in self._last_double_click_close:
                            last_time = self._last_double_click_close[line_id]
                            if current_time - last_time < self._double_click_debounce_ttl:
                                if hasattr(self, '_main_engine') and self._main_engine:
                                    self._main_engine.write_log(
                                        f"[鼠标事件] 双击入场线防抖：入场线 {line_id} 在 {current_time - last_time:.2f} 秒前已触发平仓，跳过重复操作",
                                        "Chart"
                                    )
                                return
                        
                        # 记录本次双击时间
                        self._last_double_click_close[line_id] = current_time
                        
                        if hasattr(self, '_main_engine') and self._main_engine:
                            self._main_engine.write_log(
                                f"[鼠标事件] 画线下单未启用，准备触发平仓",
                                "Chart"
                            )
                        # 获取入场线的方向和手数
                        direction_str = clicked_line.get_direction()
                        entry_volume = clicked_line.get_volume()
                        
                        if hasattr(self, '_main_engine') and self._main_engine:
                            self._main_engine.write_log(
                                f"[鼠标事件] 双击入场线平仓: 方向={direction_str}, 入场线手数={entry_volume}",
                                "Chart"
                            )
                        
                        # 如果入场线手数为0或很小，尝试从 PositionHolding 获取总持仓手数
                        if entry_volume <= 0.01:
                            if hasattr(self, '_position_holdings') and self._position_holdings:
                                holding = self._position_holdings.get(direction_str)
                                if holding:
                                    # 计算总持仓手数
                                    total_volume = sum(e.volume for e in holding.get_all_entries())
                                    if total_volume > 0:
                                        entry_volume = total_volume
                        
                        # 如果手数仍然为0，尝试从 main_engine 获取持仓信息
                        if entry_volume <= 0.01 and self._main_engine:
                            all_positions = self._main_engine.get_all_positions()
                            for pos in all_positions:
                                # 检查合约是否匹配（考虑主力合约映射）
                                pos_vt_symbol = pos.vt_symbol
                                chart_vt_symbol = self._vt_symbol
                                
                                matched = False
                                if chart_vt_symbol and pos_vt_symbol == chart_vt_symbol:
                                    matched = True
                                elif chart_vt_symbol:
                                    position_symbol = pos.symbol
                                    chart_symbol = chart_vt_symbol.split('.')[0] if '.' in chart_vt_symbol else chart_vt_symbol
                                    for gateway_name in self._main_engine.get_all_gateway_names():
                                        gateway = self._main_engine.get_gateway(gateway_name)
                                        if gateway and hasattr(gateway, 'get_main_contract_mapping'):
                                            mapping = gateway.get_main_contract_mapping()
                                            for main_symbol, actual_symbol in mapping.items():
                                                if actual_symbol == position_symbol:
                                                    main_vt_symbol = f"{main_symbol}.{pos.exchange.value}"
                                                    if main_vt_symbol == chart_vt_symbol:
                                                        matched = True
                                                        break
                                            if matched:
                                                break
                                
                                if matched:
                                    pos_direction = "long" if pos.direction.value == "多" else "short"
                                    if pos_direction == direction_str:
                                        entry_volume = pos.volume
                                        break
                        
                        # 如果手数仍然为0，提示用户
                        if entry_volume <= 0.01:
                            if self._main_engine:
                                self._main_engine.write_log(
                                    f"[ChartWidget] 双击入场线平仓失败：持仓手数为0",
                                    "ChartWidget"
                                )
                            return
                        
                        # 显示确认对话框
                        from vnpy.trader.ui import QtWidgets
                        from vnpy.trader.locale import _
                        
                        direction_display = "多仓" if direction_str == "long" else "空仓"
                        message = _(
                            f"确定要平仓吗？\n\n"
                            f"方向：{direction_display}\n"
                            f"手数：{int(entry_volume) if entry_volume == int(entry_volume) else entry_volume}手\n"
                            f"入场价格：{clicked_line.get_price():.2f}"
                        )
                        
                        reply = QtWidgets.QMessageBox.question(
                            self,
                            _("确认平仓"),
                            message,
                            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                            QtWidgets.QMessageBox.StandardButton.No
                        )
                        
                        if reply != QtWidgets.QMessageBox.StandardButton.Yes:
                            # 用户取消，清理防抖记录
                            self._last_double_click_close.pop(line_id, None)
                            if hasattr(self, '_main_engine') and self._main_engine:
                                self._main_engine.write_log(
                                    f"[ChartWidget] 用户取消平仓操作",
                                    "ChartWidget"
                                )
                            return
                        
                        # 获取对价（对手价）
                        if not self._main_engine or not self._vt_symbol:
                            if self._main_engine:
                                self._main_engine.write_log(
                                    f"[鼠标事件] 双击入场线平仓失败：缺少必要信息",
                                    "Chart"
                                )
                            return
                        
                        # 获取行情数据
                        tick_data = self._main_engine.get_tick(self._vt_symbol)
                        if not tick_data:
                            if self._main_engine:
                                self._main_engine.write_log(
                                    f"[ChartWidget] 双击入场线平仓失败：无法获取行情数据",
                                    "ChartWidget"
                                )
                            return
                        
                        # 计算对手价：平多仓用买一价，平空仓用卖一价
                        from vnpy.trader.constant import Direction
                        if direction_str == "long":
                            # 平多仓：使用买一价（对手价）
                            opponent_price = tick_data.bid_price_1 if tick_data.bid_price_1 > 0 else tick_data.last_price
                            close_direction = Direction.SHORT
                        else:
                            # 平空仓：使用卖一价（对手价）
                            opponent_price = tick_data.ask_price_1 if tick_data.ask_price_1 > 0 else tick_data.last_price
                            close_direction = Direction.LONG
                        
                        if opponent_price <= 0:
                            if self._main_engine:
                                self._main_engine.write_log(
                                    f"[鼠标事件] 双击入场线平仓失败：无法获取有效对手价",
                                    "Chart"
                                )
                            return
                        
                        # 解析合约信息
                        if '.' not in self._vt_symbol:
                            if self._main_engine:
                                self._main_engine.write_log(
                                    f"[ChartWidget] 双击入场线平仓失败：合约格式错误",
                                    "ChartWidget"
                                )
                            return
                        
                        symbol, exchange_str = self._vt_symbol.split('.', 1)
                        from vnpy.trader.constant import Exchange
                        try:
                            exchange = Exchange(exchange_str)
                        except ValueError:
                            if self._main_engine:
                                self._main_engine.write_log(
                                    f"[ChartWidget] 双击入场线平仓失败：交易所格式错误",
                                    "ChartWidget"
                                )
                            return
                        
                        # 获取网关名称
                        gateway_name = None
                        for gw_name in self._main_engine.get_all_gateway_names():
                            gateway = self._main_engine.get_gateway(gw_name)
                            if gateway:
                                # 检查网关是否支持该合约
                                contract = self._main_engine.get_contract(self._vt_symbol)
                                if contract and contract.gateway_name == gw_name:
                                    gateway_name = gw_name
                                    break
                        
                        if not gateway_name:
                            if self._main_engine:
                                self._main_engine.write_log(
                                    f"[ChartWidget] 双击入场线平仓失败：无法找到对应的网关",
                                    "ChartWidget"
                                )
                            return
                        
                        # 创建平仓订单请求
                        from vnpy.trader.object import OrderRequest
                        from vnpy.trader.constant import OrderType, Offset
                        
                        req = OrderRequest(
                            symbol=symbol,
                            exchange=exchange,
                            direction=close_direction,
                            offset=Offset.CLOSE,
                            type=OrderType.OPPONENT,
                            price=opponent_price,
                            volume=entry_volume,
                            reference="双击入场线平仓"
                        )
                        
                        # 发送订单
                        try:
                            vt_orderid = self._main_engine.send_order(req, gateway_name)
                            if self._main_engine:
                                self._main_engine.write_log(
                                    f"[ChartWidget] 双击入场线平仓：方向={direction_str}, 手数={entry_volume}, "
                                    f"对手价={opponent_price:.2f}, 订单ID={vt_orderid}",
                                    "ChartWidget"
                                )
                        except Exception as e:
                            if self._main_engine:
                                self._main_engine.write_log(
                                    f"[ChartWidget] 双击入场线平仓失败：{str(e)}",
                                    "ChartWidget"
                                )
                elif line_type in (PriceLineType.STOP_LOSS, PriceLineType.TAKE_PROFIT):
                    # Double click stop loss/take profit: Delete the line
                    # 双击止损/止盈线只删除该线，不触发平仓
                    if hasattr(self, '_main_engine') and self._main_engine:
                        self._main_engine.write_log(
                            f"[ChartWidget] 双击{line_type.value}线，准备删除: line_id={line_id}",
                            "ChartWidget"
                        )
                    
                    # 使用统一的价格线删除接口，确保同时从突破监控中注销
                    delete_result = self.remove_price_line(line_id)
                    if hasattr(self, '_main_engine') and self._main_engine:
                        self._main_engine.write_log(
                            f"[ChartWidget] 双击{line_type.value}线，删除结果: line_id={line_id}, 成功={delete_result}",
                            "ChartWidget"
                        )
            
            event.accept()
            return

        # 调用父类的 mouseDoubleClickEvent（如果存在）
        # 在 Mixin 模式中，ChartWidgetMixinBase 没有这个方法，
        # 但最终的 ChartWidget 继承自 pg.PlotWidget，所以直接调用 pg.PlotWidget 的方法
        import pyqtgraph as pg
        if isinstance(self, pg.PlotWidget):
            pg.PlotWidget.mouseDoubleClickEvent(self, event)
        else:
            # 如果不是 PlotWidget，尝试调用 QWidget 的方法
            from vnpy.trader.ui import QtWidgets
            if isinstance(self, QtWidgets.QWidget):
                QtWidgets.QWidget.mouseDoubleClickEvent(self, event)
    
    def _update_related_lines_on_drag(self, dragging_line, new_price: float) -> None:
        """
        拖拽挂单线时，实时更新关联的止损/止盈线位置。
        
        Args:
            dragging_line: 正在拖拽的价格线
            new_price: 新的价格
        """
        if not self._drawing_order_controller:
            return
        
        # 检查是否是挂单线
        from .price_line import PriceLineType
        if dragging_line.get_line_type() != PriceLineType.PENDING:
            return
        
        # 找到挂单线的ID
        line_id = None
        for lid, line in self._price_line_manager.get_all_lines().items():
            if line == dragging_line:
                line_id = lid
                break
        
        if not line_id:
            return
        
        # 获取关联关系
        if not hasattr(self._drawing_order_controller, '_pending_line_relations'):
            return
        
        relations = self._drawing_order_controller._pending_line_relations.get(line_id)
        if not relations:
            return
        
        # 获取订单参数以获取方向和pricetick
        if not hasattr(self._drawing_order_controller, '_pending_order_params'):
            return
        
        order_data = self._drawing_order_controller._pending_order_params.get(line_id)
        if not order_data:
            return
        
        params = order_data.get("params", {})
        contract = order_data.get("contract")
        if not contract:
            return
        
        direction = params.get("direction")
        # 对于 MHImain，最小变动单位是 1 个点
        # 如果合约数据中的 pricetick 不正确，使用默认值 1.0
        pricetick = contract.pricetick if contract.pricetick > 0 else 1.0
        pricetick = max(pricetick, 1.0)  # 确保至少为 1.0
        
        # 判断方向：Direction.LONG 或 "多" 表示做多
        from vnpy.trader.constant import Direction
        is_long = (direction == Direction.LONG)
        
        # 从挂单线获取订单手数
        pending_line_volume = dragging_line.get_order_volume()
        
        # 更新止损线
        stop_loss_info = relations.get("stop_loss")
        if stop_loss_info:
            stop_loss_line_id = stop_loss_info.get("line_id")
            stop_loss_points = stop_loss_info.get("points", 50)
            if stop_loss_line_id:
                stop_loss_line = self._price_line_manager.get_line(stop_loss_line_id)
                if stop_loss_line:
                    # 根据新价格和点数计算止损价格（使用pricetick）
                    if is_long:
                        new_stop_loss_price = new_price - stop_loss_points * pricetick
                    else:
                        new_stop_loss_price = new_price + stop_loss_points * pricetick
                    # 获取价格精度
                    price_precision = getattr(self, '_price_precision', 0)
                    stop_loss_line.set_price(new_stop_loss_price, price_precision)
                    # 从挂单线获取订单手数并设置到止损线
                    if pending_line_volume is not None and pending_line_volume > 0:
                        stop_loss_line.set_volume(pending_line_volume)
        
        # 更新止盈线
        take_profit_info = relations.get("take_profit")
        if take_profit_info:
            take_profit_line_id = take_profit_info.get("line_id")
            take_profit_points = take_profit_info.get("points", 50)
            if take_profit_line_id:
                take_profit_line = self._price_line_manager.get_line(take_profit_line_id)
                if take_profit_line:
                    # 根据新价格和点数计算止盈价格（使用pricetick）
                    if is_long:
                        new_take_profit_price = new_price + take_profit_points * pricetick
                    else:
                        new_take_profit_price = new_price - take_profit_points * pricetick
                    # 获取价格精度
                    price_precision = getattr(self, '_price_precision', 0)
                    take_profit_line.set_price(new_take_profit_price, price_precision)
                    # 从挂单线获取订单手数并设置到止盈线
                    if pending_line_volume is not None and pending_line_volume > 0:
                        take_profit_line.set_volume(pending_line_volume)
    
    def _update_related_lines_on_drag_end(self, dragging_line, final_price: float) -> None:
        """
        拖拽挂单线结束时，最终更新关联的止损/止盈线位置。
        
        Args:
            dragging_line: 正在拖拽的价格线
            final_price: 最终价格
        """
        # 使用相同的逻辑更新
        self._update_related_lines_on_drag(dragging_line, final_price)
    
    def _update_points_on_line_drag(self, dragged_line, new_price: float, line_type) -> None:
        """
        当单独拖拽止损线或止盈线时，根据新价格反推点数并更新保存。
        
        Args:
            dragged_line: 被拖拽的止损/止盈线
            new_price: 新的价格
            line_type: 价格线类型（STOP_LOSS 或 TAKE_PROFIT）
        """
        if not self._drawing_order_controller:
            return
        
        # 找到被拖拽的线的ID
        dragged_line_id = None
        for lid, line in self._price_line_manager.get_all_lines().items():
            if line == dragged_line:
                dragged_line_id = lid
                break
        
        if not dragged_line_id:
            return
        
        # 反向查找：找到包含此止损/止盈线的挂单线
        if not hasattr(self._drawing_order_controller, '_pending_line_relations'):
            return
        
        pending_line_id = None
        relation_key = None
        
        # 遍历所有挂单线的关联关系，找到包含此止损/止盈线的挂单线
        for pid, relations in self._drawing_order_controller._pending_line_relations.items():
            stop_loss_info = relations.get("stop_loss")
            take_profit_info = relations.get("take_profit")
            
            if stop_loss_info and stop_loss_info.get("line_id") == dragged_line_id:
                pending_line_id = pid
                relation_key = "stop_loss"
                break
            elif take_profit_info and take_profit_info.get("line_id") == dragged_line_id:
                pending_line_id = pid
                relation_key = "take_profit"
                break
        
        if not pending_line_id or not relation_key:
            return
        
        # 获取挂单线的价格和订单参数
        pending_line = self._price_line_manager.get_line(pending_line_id)
        if not pending_line:
            return
        
        pending_price = pending_line.get_price()
        
        # 获取订单参数以获取方向和pricetick
        if not hasattr(self._drawing_order_controller, '_pending_order_params'):
            return
        
        order_data = self._drawing_order_controller._pending_order_params.get(pending_line_id)
        if not order_data:
            return
        
        params = order_data.get("params", {})
        contract = order_data.get("contract")
        if not contract:
            return
        
        direction = params.get("direction")
        # 对于 MHImain，最小变动单位是 1 个点
        pricetick = contract.pricetick if contract.pricetick > 0 else 1.0
        pricetick = max(pricetick, 1.0)  # 确保至少为 1.0
        
        # 判断方向：Direction.LONG 或 "多" 表示做多
        from vnpy.trader.constant import Direction
        is_long = (direction == Direction.LONG)
        
        # 根据新价格和挂单线价格，反推点数
        price_diff = abs(new_price - pending_price)
        new_points = int(round(price_diff / pricetick))
        
        # 确保点数至少为1
        if new_points < 1:
            new_points = 1
        
        # 更新保存的点数
        relations = self._drawing_order_controller._pending_line_relations.get(pending_line_id)
        if relations and relation_key in relations:
            relations[relation_key]["points"] = new_points
            # 记录日志（如果有main_engine的话）
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"更新{relation_key}点数: 挂单价格={pending_price:.2f}, 新价格={new_price:.2f}, "
                    f"价格差={price_diff:.2f}, pricetick={pricetick}, 新点数={new_points}"
                )

