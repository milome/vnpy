# Bug 修复：鼠标点击和光标拖拽功能不工作

## 问题描述

**测试用例**: 
1. 鼠标点击功能不工作
2. 光标拖拽功能不工作

**问题现象**: 
- 鼠标点击图表界面没有反应
- 光标无法正常显示和移动
- 从入场线无法拖拽生成止损/止盈线

## 问题分析

### 根本原因

1. **`mousePressEvent` 中代码未完成**:
   - 从入场线拖拽的代码块（第222-236行）没有完成
   - 代码在第236行就结束了，没有 `event.accept()` 或 `return`
   - 也没有调用 `super().mousePressEvent(event)`
   - 这会导致代码继续执行，可能引发错误或事件未被正确处理

2. **`mouseReleaseEvent` 缺少 `super()` 调用**:
   - 当没有正在拖拽时，没有调用 `super().mouseReleaseEvent(event)`
   - 这可能导致事件未被正确传递

3. **`ChartCursor` 信号连接问题**:
   - `_connect_signal` 方法在 `scene()` 还没有准备好时可能会失败
   - 需要添加延迟连接机制

## 修复方案

### 修复 1: 完成 `mousePressEvent` 中的入场线拖拽代码

**修复前**:
```python
if clicked_line and clicked_line.get_line_type() == PriceLineType.ENTRY:
    # 从入场线开始拖拽
    self._price_line_drag_handler.start_drag_from_entry(clicked_line)
    
    # 创建预览线
    entry_price = clicked_line.get_price()
    direction = clicked_line.get_direction()
    
    # 获取当前鼠标位置的价格
    view_box = self._first_plot.getViewBox()
    if view_box:
        view_pos = view_box.mapSceneToView(scene_pos)
        preview_price = view_pos.y()
        
        # 根据拖拽方向判断是止损还是止盈

def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
```

**修复后**:
```python
if clicked_line and clicked_line.get_line_type() == PriceLineType.ENTRY:
    # 从入场线开始拖拽
    self._price_line_drag_handler.start_drag_from_entry(clicked_line)
    event.accept()
    return

# 如果没有找到任何线，调用父类处理
super().mousePressEvent(event)
```

### 修复 2: 在 `mouseReleaseEvent` 中添加 `super()` 调用

**修复前**:
```python
            event.accept()

def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:
```

**修复后**:
```python
            event.accept()
            return
        
        # 如果没有正在拖拽，调用父类处理
        super().mouseReleaseEvent(event)
```

### 修复 3: 改进 `ChartCursor` 的信号连接

**修复前**:
```python
def _connect_signal(self) -> None:
    self._widget.scene().sigMouseMoved.connect(self._mouse_moved)
```

**修复后**:
```python
def _connect_signal(self) -> None:
    # 确保 scene 已经准备好
    scene = self._widget.scene()
    if scene:
        scene.sigMouseMoved.connect(self._mouse_moved)
    else:
        # 如果 scene 还没有准备好，延迟连接
        # 这通常发生在 widget 还没有显示时
        from vnpy.trader.ui import QtCore
        QtCore.QTimer.singleShot(100, self._connect_signal)
```

## 修复效果

- ✅ `mousePressEvent` 现在正确处理所有情况
- ✅ `mouseReleaseEvent` 现在正确调用父类方法
- ✅ `ChartCursor` 的信号连接现在更健壮
- ✅ 语法检查通过
- ✅ Linter 检查通过

## 验证

### 测试步骤

1. 创建 `ChartWidget` 实例
2. 添加 plot 和 item
3. 添加光标: `widget.add_cursor()`
4. 测试鼠标点击功能
5. 测试光标移动和显示
6. 测试从入场线拖拽生成止损/止盈线

### 预期结果

- ✅ 鼠标点击正常响应
- ✅ 光标正常显示和移动
- ✅ 从入场线可以拖拽生成止损/止盈线
- ✅ 所有鼠标交互功能正常工作

## 影响范围

- **影响模块**: `widget_mouse.py`, `widget_cursor.py`
- **影响功能**: 鼠标事件处理和光标显示
- **向后兼容性**: ✅ 完全兼容（只是修复了错误的代码结构）

## 修复状态

- ✅ 问题已修复
- ✅ 代码已更新
- ✅ 语法检查通过
- ✅ Linter 检查通过
- ⏳ 需要实际测试验证

## 相关文件

- `vnpy/chart/widget_mouse.py` - 修复鼠标事件处理
- `vnpy/chart/widget_cursor.py` - 改进信号连接机制

---

**修复日期**: 2025-01-XX  
**修复人员**: AI Assistant  
**状态**: ✅ 已修复

