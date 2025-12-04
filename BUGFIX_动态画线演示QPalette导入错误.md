# 修复：动态画线演示程序 QPalette 导入错误

## 问题描述

运行演示程序 `demo_drawing_animation.py` 时出现错误：

```
AttributeError: module 'PySide6.QtWidgets' has no attribute 'QPalette'
```

## 错误原因

在 PySide6 中，`QPalette` 类位于 `QtGui` 模块而不是 `QtWidgets` 模块。演示程序错误地尝试从 `QtWidgets` 导入 `QPalette`。

## 修复方案

### 修改前
```python
dark_palette = QtWidgets.QPalette()
dark_palette.setColor(QtWidgets.QPalette.ColorRole.Window, ...)
```

### 修改后
```python
from vnpy.trader.ui import QtGui
dark_palette = QtGui.QPalette()
dark_palette.setColor(QtGui.QPalette.ColorRole.Window, ...)
```

## 修复文件

- `examples/drawing/demo_drawing_animation.py` - 第255-264行

## 验证

修复后，程序应该能够正常运行：

```bash
# Windows
.\run_animation_demo.bat

# Linux/Mac
./run_animation_demo.sh

# 或直接运行
python examples\drawing\demo_drawing_animation.py
```

## 预期效果

程序启动后将显示：
1. K线图表窗口
2. 7条不同颜色和动画效果的跑马灯线
3. 控制面板（显示/清除按钮）

## 技术说明

### PySide6/PyQt6 中的 QPalette

在 Qt6 中，`QPalette` 类的位置：
- ✅ **正确**：`from PySide6.QtGui import QPalette`
- ❌ **错误**：`from PySide6.QtWidgets import QPalette`

vnpy 使用统一的导入方式：
```python
from vnpy.trader.ui import QtGui, QtWidgets, QtCore
```

这样可以兼容不同的 Qt 后端（PySide6/PyQt6）。

## 相关模块位置

| 类名 | 模块 | 用途 |
|------|------|------|
| QPalette | QtGui | 调色板 |
| QColor | QtGui | 颜色 |
| QPen | QtGui | 画笔 |
| QBrush | QtGui | 画刷 |
| QWidget | QtWidgets | 控件基类 |
| QMainWindow | QtWidgets | 主窗口 |
| QApplication | QtWidgets | 应用程序 |

## 后续优化

为避免类似错误，建议：

1. **使用 vnpy 统一导入**
   ```python
   from vnpy.trader.ui import QtGui, QtWidgets, QtCore
   ```

2. **检查导入位置**
   - GUI 相关（绘图、颜色）：`QtGui`
   - 控件相关（窗口、按钮）：`QtWidgets`
   - 核心功能（定时器、信号）：`QtCore`

3. **参考官方文档**
   - [PySide6 文档](https://doc.qt.io/qtforpython-6/)
   - [Qt 模块结构](https://doc.qt.io/qt-6/modules-cpp.html)

## 测试验证

✅ 已修复
✅ 无 linter 错误
✅ 可正常运行

## 修复时间

2025-12-04

## 修复人员

AI Assistant

