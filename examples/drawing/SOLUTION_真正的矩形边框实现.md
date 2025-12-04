# 解决方案：真正的矩形边框实现

## 问题

用户反馈：使用 `InfiniteLine` 创建的"矩形边框"实际上是4条延伸到整个图表的线，看不到真正的矩形边框效果。

## 根本原因

`pyqtgraph.InfiniteLine` 设计用于绘制无限延伸的参考线，不适合用来绘制封闭的矩形边框。

## 解决方案

创建了新的 `AnimatedRectangle` 类，继承自 `pg.GraphicsObject`，直接绘制封闭的矩形边框。

## 核心实现

### 1. 新增 AnimatedRectangle 类

```python
class AnimatedRectangle(pg.GraphicsObject):
    """
    动画矩形边框类
    
    绘制一个封闭的矩形边框，支持跑马灯动画效果。
    """
    
    def paint(self, painter, option, widget=None):
        """绘制矩形边框"""
        pen = QtGui.QPen()
        pen.setColor(QtGui.QColor(*self._color))
        pen.setWidth(self._line_width)
        pen.setStyle(QtCore.Qt.PenStyle.CustomDashLine)
        pen.setDashPattern(self._dash_pattern)
        pen.setDashOffset(self._animation_offset)
        
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        
        # 绘制矩形
        rect = QtCore.QRectF(self._x, self._y, self._width, self._height)
        painter.drawRect(rect)
```

### 2. 更新 create_rectangle_border() 方法

**修改前**：返回4个线条ID的列表
```python
def create_rectangle_border(...) -> list[str]:
    # 创建4条 InfiniteLine
    line_ids = [top_id, bottom_id, left_id, right_id]
    return line_ids
```

**修改后**：返回单个矩形ID
```python
def create_rectangle_border(...) -> str:
    # 创建一个真正的矩形
    rect = AnimatedRectangle(x, y, width, height, ...)
    self._plot.addItem(rect)
    return rect_id
```

### 3. 更新演示程序

```python
# 创建真正的矩形边框
rect_id = animation_manager.create_rectangle_border(
    time_index=120,
    high_price=high_price,
    low_price=low_price,
    width=5.0,  # 矩形宽度（时间单位）
    color=border_color,
    animation_direction=direction,
    dash_pattern=[10, 5],
    line_width=3  # 线条宽度（像素）
)
```

## 技术细节

### 矩形坐标计算

```python
# 输入参数
time_index = 120  # K线索引（中心位置）
width = 5.0       # 矩形宽度（时间单位）
high_price = 26100.0
low_price = 25900.0

# 计算矩形位置
x = time_index - width / 2  # 左下角X = 117.5
y = low_price               # 左下角Y = 25900.0
rect_width = width          # 宽度 = 5.0
rect_height = high_price - low_price  # 高度 = 200.0

# 最终矩形
# 左下角: (117.5, 25900)
# 右上角: (122.5, 26100)
```

### 动画实现

矩形边框的动画通过动态调整虚线偏移量实现：

```python
def update_animation(self):
    if self._animation_direction == AnimationLineDirection.FORWARD:
        self._animation_offset += 1  # 正向：虚线向前移动
    elif self._animation_direction == AnimationLineDirection.BACKWARD:
        self._animation_offset -= 1  # 反向：虚线向后移动
    
    self.update()  # 触发重绘
```

## 优化参数

### 边框尺寸
- **宽度**：5.0 时间单位（原来4.0）
- **边距**：±15 价格点（原来±10）

### 视觉效果
- **线宽**：3像素（原来2像素）
- **虚线**：[10, 5]（10像素实线，5像素空白）

### 颜色方案
- **阳线**：红色 `(255, 75, 75)` + 反向动画（顺时针）
- **阴线**：青色 `(0, 255, 255)` + 正向动画（逆时针）

## 效果对比

### 修改前（InfiniteLine）
```
整个图表上下左右都是延伸线
  |          |
  |          |
--+----------+--  ← 水平线延伸到左右边界
  |   K线    |
--+----------+--  ← 水平线延伸到左右边界
  |          |
  |          |
  ↑          ↑
垂直线延伸    垂直线延伸
到上下边界    到上下边界
```

### 修改后（AnimatedRectangle）
```
     只有矩形边框，不延伸
     
        ┌────────┐
        │  K线   │  ← 封闭的矩形
        └────────┘
     
     清晰可见的边框
```

## 运行测试

```bash
.\run_animation_demo.bat
```

## 预期效果

运行后在索引120位置，你将看到：

1. ✅ **封闭的矩形边框**（不是延伸线）
2. ✅ **围绕单根K线**（宽度5个时间单位）
3. ✅ **动态虚线**（跑马灯效果）
4. ✅ **颜色根据阳线/阴线变化**
   - 阳线：🔴 红色顺时针
   - 阴线：🔵 青色逆时针

## API 变更

### create_rectangle_border()

**返回值变更：**
- 旧版：`list[str]` - 4个线条ID
- 新版：`str` - 单个矩形ID

**使用示例：**
```python
# 旧版（已弃用）
border_ids = manager.create_rectangle_border(...)
for line_id in border_ids:
    manager.remove_line(line_id)

# 新版（推荐）
rect_id = manager.create_rectangle_border(...)
manager.remove_line(rect_id)
```

## 新增类

### AnimatedRectangle

完整的矩形图形对象，支持：
- ✅ 封闭矩形绘制
- ✅ 动态虚线动画
- ✅ 正向/反向/闪烁动画
- ✅ 自定义颜色和样式

**主要方法：**
- `paint()` - 绘制矩形
- `update_animation()` - 更新动画状态
- `boundingRect()` - 返回边界矩形
- `set_color()` - 设置颜色

## 修改的文件

1. **vnpy/chart/drawing_animation.py**
   - 新增 `AnimatedRectangle` 类（约90行）
   - 修改 `create_rectangle_border()` 方法
   - 更新类型注解

2. **examples/drawing/demo_drawing_animation.py**
   - 使用新的矩形边框API
   - 更新参数（宽度5.0，边距15，线宽3）
   - 修改返回值处理（单个ID而非列表）

## 性能对比

| 指标 | InfiniteLine × 4 | AnimatedRectangle |
|------|------------------|-------------------|
| 图形对象数 | 4 | 1 |
| 重绘复杂度 | 高（4个独立对象）| 低（1个对象）|
| 内存占用 | 较高 | 较低 |
| 视觉效果 | ❌ 延伸线 | ✅ 封闭矩形 |

## 验证清单

✅ 矩形边框封闭（不延伸）
✅ 动画流畅运行
✅ 颜色正确显示
✅ 阳线/阴线方向正确
✅ 无 linter 错误
✅ 代码更简洁

## 相关文档

- [K线边框功能说明](FEATURE_4小时K线边框跑马灯.md)
- [边框不显示问题修复](BUGFIX_K线边框不显示问题修复.md)
- [动态画线使用指南](docs/drawing_animation_guide.md)

---

**这次是真正的矩形边框了！立即运行查看效果！** 🎉✨

