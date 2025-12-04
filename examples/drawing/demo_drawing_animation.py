"""
动态画线示例 - Drawing Animation Demo

演示如何使用 DrawingAnimationManager 创建跑马灯效果的动态线条。

运行此脚本将显示一个图表窗口，包含多种不同风格的动态线条：
1. 阳线K线边框（索引120，红色顺时针，线宽1.5）
2. 阴线K线边框（索引80，青色逆时针，线宽2.5）
3. 正向跑马灯水平线（黄色）
4. 反向跑马灯水平线（红色）
5. 闪烁水平线（青色）
6. 正向跑马灯垂直线（绿色）
7. 慢速跑马灯水平线（紫色）
"""

import sys
from datetime import datetime, timedelta
from typing import List

from vnpy.trader.ui import QtWidgets, QtCore
from vnpy.trader.object import BarData
from vnpy.trader.constant import Exchange, Interval
from vnpy.chart import ChartWidget
from vnpy.chart.item import CandleItem, VolumeItem
from vnpy.chart.drawing_animation import (
    DrawingAnimationManager,
    AnimationLineDirection
)


def generate_sample_bars(count: int = 200) -> List[BarData]:
    """
    生成示例K线数据
    
    Args:
        count: K线数量
        
    Returns:
        K线数据列表
    """
    bars = []
    start_time = datetime.now().replace(hour=9, minute=30, second=0, microsecond=0)
    base_price = 26000.0
    
    for i in range(count):
        # 生成随机价格变化
        import random
        change = random.uniform(-50, 50)
        
        bar = BarData(
            symbol="MHI2512",
            exchange=Exchange.HKFE,
            datetime=start_time + timedelta(minutes=i),
            interval=Interval.MINUTE,
            open_price=base_price,
            high_price=base_price + abs(change) + random.uniform(0, 20),
            low_price=base_price - abs(change) - random.uniform(0, 20),
            close_price=base_price + change,
            volume=random.randint(10, 100),
            turnover=0.0,
            open_interest=0.0,
            gateway_name="DEMO"
        )
        
        bars.append(bar)
        base_price = bar.close_price
    
    return bars


class AnimationDemoWindow(QtWidgets.QMainWindow):
    """动画演示窗口"""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("动态画线跑马灯效果演示")
        self.resize(1400, 800)
        
        # 创建中心部件
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建布局
        layout = QtWidgets.QVBoxLayout(central_widget)
        
        # 创建图表
        self.chart_widget = ChartWidget()
        layout.addWidget(self.chart_widget)
        
        # 创建控制面板
        control_panel = self._create_control_panel()
        layout.addWidget(control_panel)
        
        # 初始化动画管理器和线条ID记录（在 _init_chart 之前）
        self.animation_manager: DrawingAnimationManager = None
        self.line_ids = []
        
        # 初始化图表（会创建动画管理器）
        self._init_chart()
    
    def _create_control_panel(self) -> QtWidgets.QWidget:
        """创建控制面板"""
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(panel)
        
        # 创建按钮
        self.btn_show_animations = QtWidgets.QPushButton("显示所有动画线")
        self.btn_show_animations.clicked.connect(self._show_all_animations)
        layout.addWidget(self.btn_show_animations)
        
        self.btn_clear_animations = QtWidgets.QPushButton("清除所有动画线")
        self.btn_clear_animations.clicked.connect(self._clear_all_animations)
        layout.addWidget(self.btn_clear_animations)
        
        # 添加说明标签
        info_label = QtWidgets.QLabel(
            "演示：阳线边框(红) | 阴线边框(青) | 黄色正向 | 红色反向 | 青色闪烁 | 绿色垂直"
        )
        info_label.setStyleSheet("color: white; padding: 5px;")
        layout.addWidget(info_label)
        
        layout.addStretch()
        
        return panel
    
    def _init_chart(self) -> None:
        """初始化图表"""
        # 添加K线图
        self.chart_widget.add_plot("candle", hide_x_axis=True)
        self.chart_widget.add_plot("volume", maximum_height=200)
        
        # 添加K线和成交量显示
        self.chart_widget.add_item(CandleItem, "candle", "candle")
        self.chart_widget.add_item(VolumeItem, "volume", "volume")
        
        # 添加十字光标
        self.chart_widget.add_cursor()
        
        # 加载示例数据
        bars = generate_sample_bars(200)
        self.chart_widget.update_history(bars)
        
        # 获取第一个plot（用于添加动画线）
        first_plot = self.chart_widget._first_plot
        
        # 创建动画管理器
        self.animation_manager = DrawingAnimationManager(
            widget=self.chart_widget,
            plot=first_plot
        )
    
    def _show_all_animations(self) -> None:
        """显示所有动画线"""
        # 先清除现有的动画线
        self._clear_all_animations()
        
        # 获取当前价格范围（用于定位线条）
        bars = generate_sample_bars(200)
        if not bars:
            return
        
        # 计算价格位置
        latest_bar = bars[-1]
        base_price = latest_bar.close_price
        
        # ========== 新增：4小时K线边框跑马灯效果 ==========
        # 选择一个K线来模拟4小时K线（索引120）
        target_bar_index = 120
        if target_bar_index < len(bars):
            target_bar = bars[target_bar_index]
            
            # 判断是阳线还是阴线
            is_bullish = target_bar.close_price >= target_bar.open_price
            
            # 设置颜色和动画方向
            if is_bullish:
                # 阳线：红色、反向（顺时针）
                border_color = (255, 75, 75)  # 红色
                direction = AnimationLineDirection.BACKWARD
                bar_type = "阳线"
                direction_desc = "红色反向顺时针"
            else:
                # 阴线：青色、正向（逆时针）
                border_color = (0, 255, 255)  # 青色
                direction = AnimationLineDirection.FORWARD
                bar_type = "阴线"
                direction_desc = "青色正向逆时针"
            
            # K线的价格范围（添加一些边距）
            high_price = target_bar.high_price + 20
            low_price = target_bar.low_price - 20
            
            # 使用新的矩形边框方法（使用 PlotDataItem 绘制）
            rect_id = self.animation_manager.create_rectangle_border(
                time_index=target_bar_index,
                high_price=high_price,
                low_price=low_price,
                width=6.0,  # K线边框宽度（时间单位）
                color=border_color,
                animation_direction=direction,
                dash_pattern=[8, 4],  # 虚线样式
                line_width=1.5,  # 线条宽度（像素）
                rect_id=f"candle_{target_bar_index}"
            )
            
            # 添加到线条ID列表
            self.line_ids.append(rect_id)
            
            print(f"已创建4小时K线矩形边框：索引{target_bar_index}的{bar_type}（{direction_desc}）")
            print(f"  边框ID: {rect_id}")
            print(f"  边框范围: 时间[{target_bar_index-3:.1f}, {target_bar_index+3:.1f}], "
                  f"价格[{low_price:.0f}, {high_price:.0f}]")
        
        # ========== 新增：阴线K线边框示例 ==========
        # 选择另一个K线位置来展示阴线边框（索引80）
        bearish_bar_index = 80
        if bearish_bar_index < len(bars):
            bearish_bar = bars[bearish_bar_index]
            
            # 阴线边框：青色、正向（逆时针）、更粗的线
            bearish_color = (0, 255, 255)  # 青色
            bearish_direction = AnimationLineDirection.FORWARD  # 正向（逆时针）
            
            # K线的价格范围（添加边距）
            bearish_high = bearish_bar.high_price + 20
            bearish_low = bearish_bar.low_price - 20
            
            # 创建阴线矩形边框（线条更粗）
            bearish_rect_id = self.animation_manager.create_rectangle_border(
                time_index=bearish_bar_index,
                high_price=bearish_high,
                low_price=bearish_low,
                width=6.0,  # 边框宽度
                color=bearish_color,  # 青色
                animation_direction=bearish_direction,  # 正向（逆时针）
                dash_pattern=[8, 4],
                line_width=2.5,  # 更粗的线（阳线是1.5）
                rect_id=f"candle_bearish_{bearish_bar_index}"
            )
            
            self.line_ids.append(bearish_rect_id)
            
            print(f"已创建阴线K线矩形边框：索引{bearish_bar_index}（青色正向逆时针，线宽2.5）")
            print(f"  边框ID: {bearish_rect_id}")
            print(f"  边框范围: 时间[{bearish_bar_index-3:.1f}, {bearish_bar_index+3:.1f}], "
                  f"价格[{bearish_low:.0f}, {bearish_high:.0f}]")
        # ========== 阴线K线边框效果结束 ==========
        
        # 1. 正向跑马灯水平线（黄色）- 最新价格上方
        line_id1 = self.animation_manager.create_horizontal_line(
            price=base_price + 100,
            color=(255, 255, 0),  # 黄色
            width=3,
            animation_direction=AnimationLineDirection.FORWARD,
            dash_pattern=[15, 5]
        )
        self.line_ids.append(line_id1)
        
        # 2. 反向跑马灯水平线（红色）- 最新价格上方
        line_id2 = self.animation_manager.create_horizontal_line(
            price=base_price + 50,
            color=(255, 75, 75),  # 红色
            width=3,
            animation_direction=AnimationLineDirection.BACKWARD,
            dash_pattern=[20, 10]
        )
        self.line_ids.append(line_id2)
        
        # 3. 闪烁水平线（青色）- 最新价格
        line_id3 = self.animation_manager.create_horizontal_line(
            price=base_price,
            color=(0, 255, 255),  # 青色
            width=2,
            animation_direction=AnimationLineDirection.BLINK,
            dash_pattern=[10, 5]
        )
        self.line_ids.append(line_id3)
        
        # 4. 正向跑马灯水平线（绿色）- 最新价格下方
        line_id4 = self.animation_manager.create_horizontal_line(
            price=base_price - 50,
            color=(0, 255, 0),  # 绿色
            width=3,
            animation_direction=AnimationLineDirection.FORWARD,
            dash_pattern=[10, 5]
        )
        self.line_ids.append(line_id4)
        
        # 5. 慢速跑马灯水平线（紫色）- 最新价格下方
        line_id5 = self.animation_manager.create_horizontal_line(
            price=base_price - 100,
            color=(255, 0, 255),  # 紫色
            width=3,
            animation_direction=AnimationLineDirection.FORWARD,
            dash_pattern=[30, 15]  # 更长的虚线模式，视觉上更慢
        )
        self.line_ids.append(line_id5)
        
        # 6. 垂直跑马灯线（橙色）- 在K线中间位置
        line_id6 = self.animation_manager.create_vertical_line(
            time_index=150,  # K线索引
            color=(255, 165, 0),  # 橙色
            width=3,
            animation_direction=AnimationLineDirection.FORWARD,
            dash_pattern=[15, 8]
        )
        self.line_ids.append(line_id6)
        
        # 7. 垂直反向跑马灯线（粉色）- 在K线右侧
        line_id7 = self.animation_manager.create_vertical_line(
            time_index=180,  # K线索引
            color=(255, 192, 203),  # 粉色
            width=3,
            animation_direction=AnimationLineDirection.BACKWARD,
            dash_pattern=[20, 10]
        )
        self.line_ids.append(line_id7)
        
        print(f"已创建 {len(self.line_ids)} 条动画线")
        print(f"动画管理器状态: 运行={self.animation_manager.is_running()}, "
              f"线条数={self.animation_manager.get_line_count()}")
    
    def _clear_all_animations(self) -> None:
        """清除所有动画线"""
        if self.animation_manager:
            self.animation_manager.clear_all()
            self.line_ids.clear()
            print("已清除所有动画线")


def main():
    """主函数"""
    app = QtWidgets.QApplication(sys.argv)
    
    # 设置深色主题
    app.setStyle("Fusion")
    
    from vnpy.trader.ui import QtGui
    dark_palette = QtGui.QPalette()
    dark_palette.setColor(QtGui.QPalette.ColorRole.Window, QtCore.Qt.GlobalColor.black)
    dark_palette.setColor(QtGui.QPalette.ColorRole.WindowText, QtCore.Qt.GlobalColor.white)
    dark_palette.setColor(QtGui.QPalette.ColorRole.Base, QtCore.Qt.GlobalColor.black)
    dark_palette.setColor(QtGui.QPalette.ColorRole.AlternateBase, QtCore.Qt.GlobalColor.darkGray)
    dark_palette.setColor(QtGui.QPalette.ColorRole.Text, QtCore.Qt.GlobalColor.white)
    dark_palette.setColor(QtGui.QPalette.ColorRole.Button, QtCore.Qt.GlobalColor.darkGray)
    dark_palette.setColor(QtGui.QPalette.ColorRole.ButtonText, QtCore.Qt.GlobalColor.white)
    app.setPalette(dark_palette)
    
    # 创建并显示窗口
    window = AnimationDemoWindow()
    window.show()
    
    # 自动显示动画线
    QtCore.QTimer.singleShot(500, window._show_all_animations)
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

