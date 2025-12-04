"""
多周期窗口添加动画边框 - 实现示例代码

将以下代码片段添加到 multi_timeframe_widget.py 文件中
"""

# ==================== 第1步：在文件顶部添加导入 ====================
# 在 multi_timeframe_widget.py 的导入部分添加：

from vnpy.chart.drawing_animation import (
    DrawingAnimationManager,
    AnimationLineDirection
)


# ==================== 第2步：在 __init__ 方法中初始化变量 ====================
# 在 MultiTimeframeWidget.__init__ 方法的末尾添加：

class MultiTimeframeWidget(QtWidgets.QWidget):
    def __init__(self, ...):
        # ... 现有代码 ...
        
        # ✅ 添加：动画管理器相关变量
        self._animation_manager: DrawingAnimationManager | None = None
        self._current_4h_rect_id: str | None = None      # 当前4小时边框ID
        self._current_4h_open_line_id: str | None = None # 4小时开盘价线ID
        self._last_4h_period_start: datetime | None = None  # 上一个4小时周期起始时间


# ==================== 第3步：添加初始化动画管理器的方法 ====================
# 在 MultiTimeframeWidget 类中添加新方法：

    def _init_animation_manager(self) -> None:
        """初始化动画管理器"""
        if not self._chart:
            return
        
        try:
            # 获取主图表的 plot
            first_plot = self._chart._first_plot
            if not first_plot:
                return
            
            # 创建动画管理器
            self._animation_manager = DrawingAnimationManager(
                widget=self._chart,
                plot=first_plot
            )
            
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    "[多周期] 动画管理器已初始化",
                    "MultiTimeframe"
                )
        except Exception as e:
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[多周期] 动画管理器初始化失败: {e}",
                    "MultiTimeframe"
                )


# ==================== 第4步：在 _init_ui 中调用初始化 ====================
# 在 _init_ui 方法的末尾添加：

    def _init_ui(self):
        """构建 UI"""
        # ... 现有代码 ...
        
        # ✅ 添加：初始化动画管理器
        self._init_animation_manager()


# ==================== 第5步：添加获取4小时数据的方法 ====================

    def _get_current_4h_data(self) -> dict | None:
        """
        获取当前4小时K线数据
        
        Returns:
            包含以下字段的字典：
            - start_index: 4小时起始索引
            - current_index: 当前索引
            - open_price: 4小时开盘价
            - current_close: 当前收盘价
            - period_start: 周期起始时间
            - period_end: 周期结束时间
        """
        try:
            # 获取所有1分钟K线
            all_bars = self._manager_1m.get_all_bars()
            if not all_bars:
                return None
            
            # 获取最新的K线
            latest_bar = all_bars[-1]
            latest_index = len(all_bars) - 1
            
            # 计算当前4小时周期的起始时间
            from vnpy.trader.period_utils import get_hkfe_4hour_period
            period_start, period_end = get_hkfe_4hour_period(latest_bar.datetime)
            
            # 查找4小时周期的第一根1分钟K线
            start_index = None
            start_bar = None
            for i, bar in enumerate(all_bars):
                if bar.datetime >= period_start:
                    start_index = i
                    start_bar = bar
                    break
            
            if start_index is None or start_bar is None:
                return None
            
            # 4小时开盘价（第一根1分钟K线的开盘价）
            open_price = start_bar.open_price
            
            # 当前收盘价（最新1分钟K线的收盘价）
            current_close = latest_bar.close_price
            
            return {
                'start_index': start_index,
                'current_index': latest_index,
                'open_price': open_price,
                'current_close': current_close,
                'period_start': period_start,
                'period_end': period_end,
                'is_bullish': current_close >= open_price
            }
        except Exception as e:
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[多周期] 获取4小时数据失败: {e}",
                    "MultiTimeframe"
                )
            return None


# ==================== 第6步：添加更新4小时边框的方法 ====================

    def _update_4h_candle_border(self) -> None:
        """更新4小时K线矩形边框"""
        if not self._animation_manager:
            return
        
        try:
            # 获取当前4小时数据
            four_hour_data = self._get_current_4h_data()
            if not four_hour_data:
                return
            
            # 检查是否跨越周期（周期切换时删除旧边框）
            current_period_start = four_hour_data['period_start']
            if (self._last_4h_period_start and 
                current_period_start != self._last_4h_period_start):
                # 周期切换，删除旧边框
                if self._current_4h_rect_id:
                    self._animation_manager.remove_line(self._current_4h_rect_id)
                    self._current_4h_rect_id = None
                    
                    if hasattr(self, '_main_engine') and self._main_engine:
                        self._main_engine.write_log(
                            "[多周期] 4小时周期切换，已删除旧边框",
                            "MultiTimeframe"
                        )
            
            self._last_4h_period_start = current_period_start
            
            # 删除旧边框（实时更新）
            if self._current_4h_rect_id:
                self._animation_manager.remove_line(self._current_4h_rect_id)
            
            # 提取数据
            start_index = four_hour_data['start_index']
            current_index = four_hour_data['current_index']
            open_price = four_hour_data['open_price']
            current_close = four_hour_data['current_close']
            is_bullish = four_hour_data['is_bullish']
            
            # 计算边框位置
            center_index = (start_index + current_index) / 2
            width = current_index - start_index + 1  # +1 确保包含当前K线
            
            # 根据阳线/阴线设置参数
            if is_bullish:
                # 阳线：红色顺时针
                color = (255, 75, 75)
                direction = AnimationLineDirection.BACKWARD
                high_price = current_close
                low_price = open_price
                bar_type = "阳线"
            else:
                # 阴线：青色逆时针
                color = (0, 255, 255)
                direction = AnimationLineDirection.FORWARD
                high_price = open_price
                low_price = current_close
                bar_type = "阴线"
            
            # 创建新边框
            self._current_4h_rect_id = self._animation_manager.create_rectangle_border(
                time_index=center_index,
                high_price=high_price,
                low_price=low_price,
                width=width,
                color=color,
                animation_direction=direction,
                dash_pattern=[8, 4],
                line_width=3.5,  # 按需求设置为3.5像素
                rect_id="realtime_4h_candle"
            )
            
            # 日志输出
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[多周期] 4H边框更新: {bar_type} "
                    f"索引[{start_index}~{current_index}] "
                    f"价格[{low_price:.0f}~{high_price:.0f}] "
                    f"宽度={width}",
                    "MultiTimeframe"
                )
                
        except Exception as e:
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[多周期] 更新4小时边框失败: {e}",
                    "MultiTimeframe"
                )


# ==================== 第7步：修改4小时开盘价线为跑马灯效果 ====================

    def _update_4h_open_price_line_animated(self) -> None:
        """
        更新4小时开盘价跑马灯线（替换原有的 _update_4h_open_price_reference_line 方法）
        """
        if not self._animation_manager:
            return
        
        try:
            # 获取当前4小时数据
            four_hour_data = self._get_current_4h_data()
            if not four_hour_data:
                return
            
            # 删除旧线
            if self._current_4h_open_line_id:
                self._animation_manager.remove_line(self._current_4h_open_line_id)
            
            # 创建新的开盘价跑马灯线
            self._current_4h_open_line_id = self._animation_manager.create_horizontal_line(
                price=four_hour_data['open_price'],
                color=(255, 255, 0),  # 黄色
                width=1.5,  # 保持原线宽
                animation_direction=AnimationLineDirection.FORWARD,  # 向右（正向）
                dash_pattern=[15, 8],  # 慢速：更长的虚线样式
                line_id="realtime_4h_open"
            )
            
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[多周期] 4H开盘价线更新: {four_hour_data['open_price']:.0f} "
                    f"(黄色慢速跑马灯)",
                    "MultiTimeframe"
                )
                
        except Exception as e:
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[多周期] 更新4小时开盘价线失败: {e}",
                    "MultiTimeframe"
                )


# ==================== 第8步：在实时更新方法中调用 ====================
# 找到现有的实时更新方法（可能是 on_bar 或类似的方法），添加调用：

    def on_bar(self, bar: BarData) -> None:
        """
        实时接收1分钟K线更新
        """
        # ... 现有的更新逻辑 ...
        
        # ✅ 添加：更新4小时动画边框和开盘价线
        try:
            self._update_4h_candle_border()
            self._update_4h_open_price_line_animated()
        except Exception as e:
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[多周期] 更新动画失败: {e}",
                    "MultiTimeframe"
                )


# ==================== 第9步：替换或注释原有的开盘价线方法 ====================
# 找到原有的 _update_4h_open_price_reference_line 方法（约1875-1918行），
# 将其注释掉或替换为新的动画方法调用：

    def _update_4h_open_price_reference_line(self) -> None:
        """
        【已替换】原方法已被 _update_4h_open_price_line_animated 替代
        """
        # 调用新的动画方法
        self._update_4h_open_price_line_animated()


# ==================== 第10步：清理资源（可选）====================
# 在窗口关闭时清理动画资源：

    def closeEvent(self, event) -> None:
        """窗口关闭事件"""
        # 清理动画
        if self._animation_manager:
            self._animation_manager.clear_all()
        
        # ... 其他清理代码 ...
        
        super().closeEvent(event)


# ==================== 使用说明 ====================
"""
使用步骤：

1. 将上述代码片段按步骤添加到 multi_timeframe_widget.py 文件中

2. 修改位置：
   - 第1步：文件顶部导入区域
   - 第2步：__init__ 方法末尾（约第130行）
   - 第3-7步：作为新方法添加到类中（约第1800行之后）
   - 第8步：在实时更新方法中调用（需要找到对应的方法）
   - 第9步：约第1875-1918行

3. 测试：
   - 启动多周期窗口
   - 观察是否有4小时边框和开盘价跑马灯线
   - 确认阳线/阴线颜色和方向正确
   - 观察实时更新是否正常

4. 调试日志：
   - 检查控制台输出的日志
   - 确认动画管理器已初始化
   - 确认边框和开盘价线已创建

5. 常见问题：
   - 如果看不到边框：检查 _animation_manager 是否已初始化
   - 如果边框位置不对：检查 _get_current_4h_data 的计算逻辑
   - 如果没有动画效果：检查定时器是否正常运行
"""

