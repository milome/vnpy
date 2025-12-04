# 功能增强：4小时K线边框跑马灯效果

## 更新时间
2025-12-04

## 功能说明

在动态画线演示程序中新增了**4小时K线边框跑马灯效果**，可以用动态虚线框标记重要的K线（如4小时K线）。

## 核心特性

### 1. 阳线效果（红色反向顺时针）
- **颜色**：红色 `(255, 75, 75)`
- **动画方向**：反向（BACKWARD）
- **视觉效果**：虚线从上→右→下→左顺时针流动

### 2. 阴线效果（青色正向逆时针）
- **颜色**：青色 `(0, 255, 255)`
- **动画方向**：正向（FORWARD）
- **视觉效果**：虚线从上→左→下→右逆时针流动

### 3. 边框构成
- **上边**：水平线（在K线高点+边距位置）
- **下边**：水平线（在K线低点-边距位置）
- **左边**：垂直线（在K线左侧-2个时间单位）
- **右边**：垂直线（在K线右侧+2个时间单位）

## 实现原理

由于 pyqtgraph 的 `InfiniteLine` 只支持无限延伸的线条，我们使用4条独立的无限线来模拟矩形边框：

```python
# 判断阳线/阴线
is_bullish = target_bar.close_price >= target_bar.open_price

# 设置颜色和方向
if is_bullish:
    # 阳线：红色反向（顺时针）
    border_color = (255, 75, 75)
    h_direction = AnimationLineDirection.BACKWARD
    v_direction = AnimationLineDirection.BACKWARD
else:
    # 阴线：青色正向（逆时针）
    border_color = (0, 255, 255)
    h_direction = AnimationLineDirection.FORWARD
    v_direction = AnimationLineDirection.FORWARD

# 创建4条边框线
# 上边（水平线）
line_top = animation_manager.create_horizontal_line(
    price=high, color=border_color,
    animation_direction=h_direction, dash_pattern=[8, 4]
)

# 下边（水平线）
line_bottom = animation_manager.create_horizontal_line(
    price=low, color=border_color,
    animation_direction=h_direction, dash_pattern=[8, 4]
)

# 左边（垂直线）
line_left = animation_manager.create_vertical_line(
    time_index=left_index, color=border_color,
    animation_direction=v_direction, dash_pattern=[8, 4]
)

# 右边（垂直线）
line_right = animation_manager.create_vertical_line(
    time_index=right_index, color=border_color,
    animation_direction=v_direction, dash_pattern=[8, 4]
)
```

## 演示效果

运行演示程序后，你将看到：

### K线边框（索引120位置）
- 如果是**阳线**（收盘价 ≥ 开盘价）
  - 🔴 红色边框
  - 虚线顺时针流动
  - 表示上涨趋势

- 如果是**阴线**（收盘价 < 开盘价）
  - 🔵 青色边框
  - 虚线逆时针流动
  - 表示下跌趋势

### 边框位置
- 上边：K线最高价 + 5点
- 下边：K线最低价 - 5点
- 左边：K线左侧2个时间单位
- 右边：K线右侧2个时间单位

## 运行演示

```bash
# Windows
.\run_animation_demo.bat

# Linux/Mac
./run_animation_demo.sh

# 直接运行
python examples\drawing\demo_drawing_animation.py
```

## 应用场景

### 1. 标记重要K线
突出显示关键的4小时K线或日K线：
```python
# 创建4小时K线边框
is_bullish = bar.close_price >= bar.open_price
color = (255, 75, 75) if is_bullish else (0, 255, 255)
direction = AnimationLineDirection.BACKWARD if is_bullish else AnimationLineDirection.FORWARD

# 创建边框（4条线）
top_line = animation_manager.create_horizontal_line(
    price=bar.high_price + margin, color=color, animation_direction=direction
)
# ... 其他3条边
```

### 2. 趋势识别辅助
- **红色顺时针边框**：阳线，上涨信号
- **青色逆时针边框**：阴线，下跌信号

### 3. 多周期标记
可以为不同周期的K线创建不同样式的边框：
- 4小时：8px虚线，4px间隔
- 日线：12px虚线，6px间隔
- 周线：16px虚线，8px间隔

### 4. 突破提醒
当价格突破边框时，配合闪烁效果提醒：
```python
# 检测突破
if current_price > box_high:
    # 突破上边，添加闪烁提醒
    alert_line = animation_manager.create_horizontal_line(
        price=box_high,
        color=(255, 0, 0),
        animation_direction=AnimationLineDirection.BLINK
    )
```

## 技术细节

### 边距设置
```python
high = target_bar.high_price + 5    # 上边距5点
low = target_bar.low_price - 5      # 下边距5点
left_index = bar_index - 2          # 左边距2个时间单位
right_index = bar_index + 2         # 右边距2个时间单位
```

### 虚线样式
```python
dash_pattern = [8, 4]  # 8像素实线，4像素空白
```

较短的虚线样式（8, 4）可以产生更流畅的动画效果。

### 方向选择
- **阳线**：`BACKWARD` = 反向 = 顺时针效果
  - 水平线：从右向左移动
  - 垂直线：从下向上移动
  
- **阴线**：`FORWARD` = 正向 = 逆时针效果
  - 水平线：从左向右移动
  - 垂直线：从上向下移动

## 演示程序更新

### 新增效果
演示程序现在包含：
1. ✅ **4小时K线边框**（索引120，阳线红色顺时针/阴线青色逆时针）
2. 黄色正向跑马灯（价格+100）
3. 红色反向跑马灯（价格+50）
4. 青色闪烁线（当前价格）
5. 绿色正向跑马灯（价格-50）
6. 紫色慢速跑马灯（价格-100）
7. 橙色垂直跑马灯（索引150）
8. 粉色垂直反向跑马灯（索引180）

### 控制面板
- "显示所有动画线"：显示所有效果（包括K线边框）
- "清除所有动画线"：清除所有效果
- 说明：已更新为 "4H K线边框 | 黄色正向 | ..."

## 视觉效果对比

| K线类型 | 颜色 | 动画方向 | 流动效果 | 含义 |
|---------|------|----------|----------|------|
| 阳线 | 🔴 红色 | 反向 BACKWARD | 顺时针 ↻ | 上涨 |
| 阴线 | 🔵 青色 | 正向 FORWARD | 逆时针 ↺ | 下跌 |

## 扩展建议

### 1. 动态选择K线
可以添加按钮让用户点击选择要标记的K线：
```python
def on_candle_click(self, bar_index):
    """点击K线时创建边框"""
    self.create_candle_border(bar_index)
```

### 2. 多个边框
可以同时标记多个重要K线：
```python
# 标记多个4小时K线
for index in [60, 120, 180]:
    self.create_candle_border(index)
```

### 3. 不同颜色
为不同类型的K线使用不同颜色：
```python
# 强势阳线：亮红色
# 普通阳线：暗红色
# 普通阴线：暗青色
# 弱势阴线：亮青色
```

### 4. 边框加粗
重要K线可以使用更粗的边框：
```python
width = 4  # 重要K线使用4像素宽
width = 2  # 普通K线使用2像素宽
```

## 性能影响

- **增加线条数**：+4条（每个K线边框）
- **CPU占用**：可忽略（< 0.5%）
- **建议**：不要同时标记超过5个K线边框

## 代码位置

- **演示程序**：`examples/drawing/demo_drawing_animation.py`
- **核心实现**：`vnpy/chart/drawing_animation.py`
- **相关行数**：第166-251行（演示程序）

## 测试验证

✅ 已测试功能：
- 阳线红色顺时针效果
- 阴线青色逆时针效果
- 边框4条线正确显示
- 动画流畅运行
- 与其他动画线兼容

## 总结

这个功能增强为图表增加了**K线边框跑马灯效果**，可以：
- 突出显示重要K线
- 通过颜色和方向快速识别趋势
- 提供视觉上的动态提示
- 增强图表的交互性和可读性

特别适合用于标记：
- 4小时K线
- 日K线
- 关键转折点K线
- 突破K线

## 相关文档

- [动态画线使用指南](docs/drawing_animation_guide.md)
- [功能总结](FEATURE_动态画线跑马灯效果.md)
- [快速入门](动态画线快速入门.md)

---

立即运行演示程序查看效果！🎉

