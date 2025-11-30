# QtTest 鼠标事件测试说明

## 概述

`test_widget_mouse_qt.py` 使用 QtTest 和 pytest-qt 模拟真实的鼠标事件，测试 `ChartWidget` 的鼠标交互功能。

## 测试覆盖

### 1. 基本鼠标点击 (`test_mouse_click_basic`)
- 测试基本的鼠标点击事件
- 验证事件被正确处理，不会报错

### 2. 画线下单模式点击 (`test_mouse_click_drawing_order_mode`)
- 测试画线下单模式下的鼠标点击
- 验证回调函数被调用
- 验证预览线显示

### 3. 鼠标移动悬停检测 (`test_mouse_move_hover_detection`)
- 测试鼠标移动时的悬停检测
- 验证光标样式变化
- 验证价格线悬停检测

### 4. 拖拽价格线 (`test_mouse_drag_price_line`)
- 测试拖拽可移动的价格线
- 验证拖拽开始、移动、结束的完整流程
- 验证价格线位置更新

### 5. 从入场线拖拽生成止损/止盈线 (`test_mouse_drag_from_entry_line`)
- 测试从入场线拖拽生成止损/止盈线
- 验证拖拽流程
- 验证新线创建

### 6. 双击挂单线 (`test_mouse_double_click_pending_line`)
- 测试双击挂单线
- 验证删除确认对话框或直接删除

### 7. 双击入场线 (`test_mouse_double_click_entry_line`)
- 测试双击入场线（平仓）
- 验证平仓确认对话框

### 8. 鼠标滚轮缩放 (`test_mouse_wheel_zoom`)
- 测试鼠标滚轮缩放功能
- 验证图表缩放

### 9. ESC 键禁用画线下单模式 (`test_key_escape_disable_drawing_mode`)
- 测试 ESC 键禁用画线下单模式
- 验证模式状态切换

### 10. ESC 键取消拖拽 (`test_key_escape_cancel_drag`)
- 测试 ESC 键取消正在进行的拖拽
- 验证拖拽状态重置

## 使用方法

### 运行所有测试
```bash
pytest tests/chart/test_widget_mouse_qt.py -v
```

### 运行单个测试
```bash
pytest tests/chart/test_widget_mouse_qt.py::TestChartWidgetMouseQt::test_mouse_click_basic -v
```

### 跳过覆盖率检查
```bash
pytest tests/chart/test_widget_mouse_qt.py -v --no-cov
```

## 技术细节

### QtTest 方法
- `qtbot.mouseClick()` - 模拟鼠标点击
- `qtbot.mousePress()` - 模拟鼠标按下
- `qtbot.mouseMove()` - 模拟鼠标移动
- `qtbot.mouseRelease()` - 模拟鼠标释放
- `qtbot.keyClick()` - 模拟键盘按键
- `widget.wheelEvent()` - 直接调用滚轮事件（qtbot 没有 mouseWheel 方法）

### 坐标转换
由于 pyqtgraph 使用场景坐标系统，测试中需要进行坐标转换：
- `widget.mapToScene()` - 将 widget 坐标转换为场景坐标
- `view_box.mapSceneToView()` - 将场景坐标转换为视图坐标
- `view_box.mapViewToScene()` - 将视图坐标转换为场景坐标

### 注意事项
1. **坐标转换复杂性**: 由于坐标转换的复杂性，某些测试可能不会完全验证功能，但至少确保不会报错
2. **事件处理延迟**: 使用 `qtbot.wait()` 等待事件处理完成
3. **Widget 可见性**: 确保 widget 可见（`widget.show()` 和 `qtbot.waitExposed(widget)`）

## 测试结果

✅ **所有 10 个测试通过**

```
tests/chart/test_widget_mouse_qt.py::TestChartWidgetMouseQt::test_mouse_click_basic PASSED
tests/chart/test_widget_mouse_qt.py::TestChartWidgetMouseQt::test_mouse_click_drawing_order_mode PASSED
tests/chart/test_widget_mouse_qt.py::TestChartWidgetMouseQt::test_mouse_move_hover_detection PASSED
tests/chart/test_widget_mouse_qt.py::TestChartWidgetMouseQt::test_mouse_drag_price_line PASSED
tests/chart/test_widget_mouse_qt.py::TestChartWidgetMouseQt::test_mouse_drag_from_entry_line PASSED
tests/chart/test_widget_mouse_qt.py::TestChartWidgetMouseQt::test_mouse_double_click_pending_line PASSED
tests/chart/test_widget_mouse_qt.py::TestChartWidgetMouseQt::test_mouse_double_click_entry_line PASSED
tests/chart/test_widget_mouse_qt.py::TestChartWidgetMouseQt::test_mouse_wheel_zoom PASSED
tests/chart/test_widget_mouse_qt.py::TestChartWidgetMouseQt::test_key_escape_disable_drawing_mode PASSED
tests/chart/test_widget_mouse_qt.py::TestChartWidgetMouseQt::test_key_escape_cancel_drag PASSED
```

## 相关修复

在创建这些测试的过程中，修复了以下问题：

1. **MRO 问题**: 修复了 Mixin 中 `super()` 调用的问题，直接调用 `pg.PlotWidget` 的方法
2. **事件处理**: 在 `ChartWidget` 中显式重写鼠标事件方法，确保 Mixin 方法被调用
3. **初始化检查**: 添加了 `_price_line_manager` 的初始化检查

## 未来改进

1. 添加更详细的断言，验证具体的行为
2. 测试更多边界情况
3. 添加性能测试
4. 测试多线程场景

