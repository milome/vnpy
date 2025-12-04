# POC 功能对比与恢复

## 问题描述

在 `examples/candle_chart/multi_timeframe_widget.py` (POC版本) 中实现的一些功能，在迁移到 `vnpy/chart/multi_timeframe_widget.py` (正式版本) 时丢失了。

## 缺失的功能

### 1. 阳线填充功能

**POC 版本特性**:
- 阳线（涨的K线）也有背景填充矩形
- 阳线和阴线共享透明度设置
- 使得多周期K线更加统一和美观

**当前状态**:
- 只有阴线有填充
- 阳线只有边框，没有填充

### 2. 透明度共享

**POC 版本特性**:
- 一个透明度设置同时控制阳线和阴线的填充透明度
- 用户体验更好，设置更简单

**当前状态**:
- 只有阴线填充透明度设置
- 阳线没有填充，也就没有透明度设置

## 需要恢复的功能

### 功能1: CrossIndexCandleItem 支持阳线填充

在 `vnpy/chart/cross_index_candle_item.py` 中：

**当前代码**:
```python
def __init__(
    self,
    manager: BarManager,
    base_manager: BarManager | None = None,
    bearish_fill_opacity: float = 0.05,  # 只有阴线填充透明度
    bullish_color: QtGui.QColor | None = None,
    bearish_color: QtGui.QColor | None = None,
    interval: Interval = Interval.HOUR_4,
    pen_width: int | None = None,
) -> None:
    # ...
```

**需要添加**:
```python
def __init__(
    self,
    manager: BarManager,
    base_manager: BarManager | None = None,
    bearish_fill_opacity: float = 0.05,
    bullish_fill_opacity: float = 0.05,  # ← 添加阳线填充透明度
    bullish_color: QtGui.QColor | None = None,
    bearish_color: QtGui.QColor | None = None,
    interval: Interval = Interval.HOUR_4,
    pen_width: int | None = None,
) -> None:
    # ...
```

### 功能2: 绘制阳线填充矩形

**需要修改 `_draw_bar_picture()` 方法**:

当前只绘制阴线填充：
```python
if close_price < open_price:
    # 阴线：填充
    painter.setBrush(self.bearish_brush)
    # ...
else:
    # 阳线：不填充
    painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
    # ...
```

需要改为：
```python
if close_price < open_price:
    # 阴线：填充
    painter.setBrush(self.bearish_brush)
    # ...
else:
    # 阳线：也填充
    painter.setBrush(self.bullish_brush)  # ← 使用阳线画刷
    # ...
```

### 功能3: MultiTimeframeSettings 支持阳线填充

在 `vnpy/chart/multi_timeframe_settings_dialog.py` 中：

**需要添加阳线填充透明度字段**:
```python
@dataclass
class MultiTimeframeSettings:
    """多周期K线显示设置"""
    
    # 5分钟K线设置
    show_5m: bool = True
    opacity_5m: float = 0.80
    bullish_fill_opacity_5m: float = 0.05  # ← 添加
    
    # 1小时K线设置
    show_1h: bool = True
    opacity_1h: float = 0.80
    bullish_fill_opacity_1h: float = 0.05  # ← 添加
    
    # 4小时K线设置
    show_4h: bool = True
    opacity_4h: float = 0.80
    bullish_fill_opacity_4h: float = 0.05  # ← 添加
```

### 功能4: 设置对话框支持阳线填充

**需要在对话框中添加阳线填充透明度滑块**:

或者更简单的方案：
- 阳线和阴线**共享同一个透明度设置**
- 这样用户界面更简洁
- 符合大多数使用场景

## 推荐方案：共享透明度设置

### 方案优点
1. **用户体验更好**: 一个滑块同时控制阳线和阴线透明度
2. **界面更简洁**: 不需要两个滑块
3. **符合预期**: 大多数情况下阳线和阴线应该有相同的透明度

### 实现步骤

#### 步骤1: 修改 CrossIndexCandleItem

```python
class CrossIndexCandleItem(ChartItem):
    def __init__(
        self,
        manager: BarManager,
        base_manager: BarManager | None = None,
        fill_opacity: float = 0.05,  # ← 改名，阳线阴线共享
        bullish_color: QtGui.QColor | None = None,
        bearish_color: QtGui.QColor | None = None,
        interval: Interval = Interval.HOUR_4,
        pen_width: int | None = None,
    ) -> None:
        super().__init__(manager)
        
        # 设置颜色
        self.bullish_color = bullish_color or UP_COLOR
        self.bearish_color = bearish_color or DOWN_COLOR
        
        # 设置画刷（阳线和阴线都填充）
        bullish_color_with_alpha = QtGui.QColor(self.bullish_color)
        bullish_color_with_alpha.setAlphaF(fill_opacity)
        self.bullish_brush = QtGui.QBrush(bullish_color_with_alpha)
        
        bearish_color_with_alpha = QtGui.QColor(self.bearish_color)
        bearish_color_with_alpha.setAlphaF(fill_opacity)
        self.bearish_brush = QtGui.QBrush(bearish_color_with_alpha)
        
        # ...
```

#### 步骤2: 修改绘制逻辑

```python
def _draw_bar_picture(self, ix: int, bar: BarData) -> None:
    # ...
    
    if close_price < open_price:
        # 阴线
        painter.setPen(self.bearish_pen)
        painter.setBrush(self.bearish_brush)  # 填充
    else:
        # 阳线
        painter.setPen(self.bullish_pen)
        painter.setBrush(self.bullish_brush)  # 也填充！
    
    # 绘制实体
    painter.drawRect(rect)
    
    # ...
```

#### 步骤3: 更新 MultiTimeframeSettings

保持简单，只用一个透明度字段：

```python
@dataclass
class MultiTimeframeSettings:
    """多周期K线显示设置"""
    
    # 5分钟K线设置
    show_5m: bool = True
    opacity_5m: float = 0.80  # 阳线阴线共享
    
    # 1小时K线设置
    show_1h: bool = True
    opacity_1h: float = 0.80  # 阳线阴线共享
    
    # 4小时K线设置
    show_4h: bool = True
    opacity_4h: float = 0.80  # 阳线阴线共享
```

## 对比总结

| 功能 | POC 版本 | 当前正式版本 | 是否恢复 |
|-----|---------|------------|---------|
| 阳线填充 | ✅ 有 | ❌ 无 | 🔄 需要恢复 |
| 阴线填充 | ✅ 有 | ✅ 有 | ✅ 已有 |
| 透明度共享 | ✅ 有 | ❌ 无 | 🔄 需要恢复 |
| 设置对话框 | ❌ 无 | ✅ 有 | ✅ 新增 |

## 下一步行动

1. ✅ 创建此对比文档
2. ⏭️ 修改 `CrossIndexCandleItem` 支持阳线填充
3. ⏭️ 更新绘制逻辑
4. ⏭️ 测试验证
5. ⏭️ 更新文档

## 参考

- POC 版本: `examples/candle_chart/multi_timeframe_widget.py`
- 正式版本: `vnpy/chart/multi_timeframe_widget.py`
- K线绘制: `vnpy/chart/cross_index_candle_item.py`
- 设置对话框: `vnpy/chart/multi_timeframe_settings_dialog.py`

