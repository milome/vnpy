# 动态画线（跑马灯效果）使用指南

## 概述

`DrawingAnimationManager` 是一个用于在K线图上绘制动态线条的管理器类，支持跑马灯效果、闪烁效果等多种动画效果。

## 功能特性

### 1. 线条类型

- **水平线（HORIZONTAL）**：沿价格轴的水平线
- **垂直线（VERTICAL）**：沿时间轴的垂直线
- **线段（SEGMENT）**：有起点和终点的线段（未来扩展）

### 2. 动画效果

- **正向跑马灯（FORWARD）**：虚线从左向右（或从上向下）移动
- **反向跑马灯（BACKWARD）**：虚线从右向左（或从下向上）移动
- **闪烁效果（BLINK）**：线条闪烁显示

### 3. 可配置参数

- **颜色**：RGB元组，如 `(255, 255, 0)` 表示黄色
- **线宽**：像素值，默认为 2
- **虚线样式**：`dash_pattern` 列表，如 `[10, 5]` 表示10像素实线，5像素空白
- **动画速度**：定时器刷新间隔，默认 50ms
- **是否延伸**：是否作为无限线延伸

## 技术实现

### 核心原理

1. **基于 pyqtgraph.InfiniteLine**：继承 `pg.InfiniteLine` 类实现线条绘制
2. **QTimer 驱动动画**：使用 Qt 定时器定期更新虚线偏移量
3. **CustomDashLine 样式**：通过自定义虚线样式和偏移量实现跑马灯效果

### 关键代码逻辑

```python
# 1. 创建自定义虚线画笔
pen = pg.mkPen(
    color=self._base_color,
    width=self._width,
    style=QtCore.Qt.PenStyle.CustomDashLine
)
pen.setDashPattern(dash_pattern)
pen.setDashOffset(self._animation_offset)  # 关键：动态偏移

# 2. 定时更新偏移量
def update_animation(self):
    if self._animation_direction == AnimationLineDirection.FORWARD:
        self._animation_offset += 1
        if self._animation_offset > sum(self._dash_pattern):
            self._animation_offset = 0
    # 更新画笔并重绘
    pen = self._create_pen()
    self.setPen(pen)
```

## 使用示例

### 基本用法

```python
from vnpy.chart import ChartWidget
from vnpy.chart.drawing_animation import (
    DrawingAnimationManager,
    AnimationLineDirection
)

# 1. 创建图表
chart_widget = ChartWidget()
first_plot = chart_widget._first_plot

# 2. 创建动画管理器
animation_manager = DrawingAnimationManager(
    widget=chart_widget,
    plot=first_plot
)

# 3. 创建水平动画线
line_id = animation_manager.create_horizontal_line(
    price=26000.0,              # 价格位置
    color=(255, 255, 0),        # 黄色
    width=3,                    # 线宽
    animation_direction=AnimationLineDirection.FORWARD,
    dash_pattern=[15, 5]        # 15像素实线，5像素空白
)

# 4. 创建垂直动画线
vline_id = animation_manager.create_vertical_line(
    time_index=100,             # K线索引
    color=(0, 255, 255),        # 青色
    width=2,
    animation_direction=AnimationLineDirection.BACKWARD,
    dash_pattern=[10, 5]
)

# 5. 删除指定线条
animation_manager.remove_line(line_id)

# 6. 清除所有动画线
animation_manager.clear_all()
```

### 完整示例

运行 `examples/drawing/demo_drawing_animation.py` 查看完整演示：

```bash
cd D:\Dev\vnpy-007-multi-timeframe-integration
python examples/drawing/demo_drawing_animation.py
```

演示包含：
1. 黄色正向跑马灯水平线
2. 红色反向跑马灯水平线
3. 青色闪烁水平线
4. 绿色正向跑马灯水平线
5. 紫色慢速跑马灯水平线
6. 橙色正向跑马灯垂直线
7. 粉色反向跑马灯垂直线

## API 参考

### DrawingAnimationManager

#### 初始化

```python
DrawingAnimationManager(
    widget: ChartWidget = None,
    plot: pg.PlotItem = None
)
```

#### 主要方法

##### create_horizontal_line()

创建水平动画线

**参数：**
- `price` (float): 价格位置
- `color` (tuple[int, int, int]): RGB颜色元组，默认 `(255, 255, 0)`
- `width` (int): 线宽，默认 2
- `animation_direction` (AnimationLineDirection): 动画方向，默认 `FORWARD`
- `animation_speed` (int): 动画速度（毫秒），默认 100
- `dash_pattern` (list[int]): 虚线样式，默认 `None`
- `line_id` (str): 可选的线条ID，默认自动生成

**返回：**
- `str`: 线条ID

##### create_vertical_line()

创建垂直动画线

**参数：**
- `time_index` (float): 时间索引（K线索引）
- `color` (tuple[int, int, int]): RGB颜色元组，默认 `(0, 255, 255)`
- `width` (int): 线宽，默认 2
- `animation_direction` (AnimationLineDirection): 动画方向，默认 `FORWARD`
- `animation_speed` (int): 动画速度（毫秒），默认 100
- `dash_pattern` (list[int]): 虚线样式，默认 `None`
- `line_id` (str): 可选的线条ID，默认自动生成

**返回：**
- `str`: 线条ID

##### remove_line()

删除指定动画线

**参数：**
- `line_id` (str): 线条ID

**返回：**
- `bool`: 是否删除成功

##### clear_all()

清除所有动画线

##### is_running()

检查动画是否正在运行

**返回：**
- `bool`: 是否正在运行

##### get_line_count()

获取当前动画线数量

**返回：**
- `int`: 线条数量

### AnimationLineDirection（枚举）

- `FORWARD`: 正向跑马灯
- `BACKWARD`: 反向跑马灯
- `BLINK`: 闪烁效果

### AnimationLineType（枚举）

- `HORIZONTAL`: 水平线
- `VERTICAL`: 垂直线
- `SEGMENT`: 线段（未来扩展）

## 性能优化

### 1. 定时器管理

- 动画管理器使用单个定时器驱动所有动画线
- 当没有动画线时自动停止定时器，节省资源
- 刷新率固定为 50ms（每秒20帧），平衡流畅度和性能

### 2. 虚线样式建议

- **快速跑马灯**：使用较短的虚线模式，如 `[10, 5]`
- **慢速跑马灯**：使用较长的虚线模式，如 `[30, 15]`
- **密集效果**：使用短间隔，如 `[5, 2]`
- **稀疏效果**：使用长间隔，如 `[20, 20]`

### 3. 内存管理

- 及时删除不需要的动画线
- 避免创建过多动画线（建议不超过20条）
- 定期调用 `clear_all()` 清理临时线条

## 应用场景

### 1. 价格警戒线

使用闪烁或跑马灯效果标记重要价格位置：

```python
# 重要阻力位 - 红色闪烁
resistance_line = animation_manager.create_horizontal_line(
    price=26500.0,
    color=(255, 75, 75),
    width=3,
    animation_direction=AnimationLineDirection.BLINK
)

# 重要支撑位 - 绿色闪烁
support_line = animation_manager.create_horizontal_line(
    price=25500.0,
    color=(0, 255, 0),
    width=3,
    animation_direction=AnimationLineDirection.BLINK
)
```

### 2. 开盘价标记

使用跑马灯效果标记当日开盘价：

```python
open_line = animation_manager.create_horizontal_line(
    price=opening_price,
    color=(255, 255, 0),
    width=2,
    animation_direction=AnimationLineDirection.FORWARD,
    dash_pattern=[15, 5]
)
```

### 3. 时间节点标记

使用垂直跑马灯标记重要时间点：

```python
# 标记市场开盘时间
open_time_line = animation_manager.create_vertical_line(
    time_index=market_open_index,
    color=(0, 255, 255),
    width=2,
    animation_direction=AnimationLineDirection.FORWARD
)
```

### 4. 动态止损止盈线

使用跑马灯效果增强止损止盈线的可见性：

```python
# 止损线 - 橙色跑马灯
stop_loss_line = animation_manager.create_horizontal_line(
    price=stop_loss_price,
    color=(255, 165, 0),
    width=3,
    animation_direction=AnimationLineDirection.FORWARD,
    dash_pattern=[10, 5]
)

# 止盈线 - 绿色跑马灯
take_profit_line = animation_manager.create_horizontal_line(
    price=take_profit_price,
    color=(0, 255, 0),
    width=3,
    animation_direction=AnimationLineDirection.FORWARD,
    dash_pattern=[10, 5]
)
```

## 常见问题

### Q1: 如何调整跑马灯速度？

A: 跑马灯速度由两个因素决定：
1. 虚线样式长度：更长的虚线模式视觉上更慢
2. 定时器刷新率：目前固定为50ms（不建议修改）

```python
# 慢速跑马灯：使用长虚线模式
slow_line = animation_manager.create_horizontal_line(
    price=26000.0,
    dash_pattern=[30, 15]  # 更长的虚线
)

# 快速跑马灯：使用短虚线模式
fast_line = animation_manager.create_horizontal_line(
    price=26100.0,
    dash_pattern=[5, 3]  # 更短的虚线
)
```

### Q2: 动画线会影响图表性能吗？

A: 适度使用（< 20条）不会明显影响性能。关键优化措施：
- 使用单个定时器驱动所有动画
- 只在必要时重绘
- 自动停止空闲定时器

### Q3: 如何实现渐变颜色效果？

A: 目前版本不支持渐变颜色。可以通过创建多条不同颜色的线来模拟：

```python
# 创建一组颜色渐变的线条
colors = [
    (255, 0, 0),    # 红
    (255, 128, 0),  # 橙
    (255, 255, 0),  # 黄
]
for i, color in enumerate(colors):
    animation_manager.create_horizontal_line(
        price=base_price + i * 10,
        color=color,
        width=2
    )
```

### Q4: 可以在多周期图表中使用吗？

A: 可以。每个图表窗口（ChartWidget）可以有独立的 `DrawingAnimationManager` 实例：

```python
# 主图动画管理器
main_animation = DrawingAnimationManager(
    widget=main_chart,
    plot=main_chart._first_plot
)

# 4小时图动画管理器
h4_animation = DrawingAnimationManager(
    widget=h4_chart,
    plot=h4_chart._first_plot
)
```

## 未来扩展

### 计划功能

1. **线段支持**：支持有起点和终点的线段
2. **渐变颜色**：支持颜色渐变效果
3. **自定义动画曲线**：支持加速、减速等动画曲线
4. **波浪效果**：支持波浪形动画
5. **粒子效果**：支持粒子沿线运动

### 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 创建 Pull Request

## 技术支持

如有问题或建议，请：
- 创建 GitHub Issue
- 查阅项目文档
- 联系开发团队

## 许可证

本项目遵循 MIT 许可证。

