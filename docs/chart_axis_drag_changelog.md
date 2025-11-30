# ChartWidget 坐标轴拖拽功能变更日志

## [2025-12-01] - 坐标轴拖拽功能

### 新增功能

#### 1. 右侧价格坐标轴拖拽
- **功能描述**: 鼠标左键按住图表右侧价格坐标轴，可以向上或向下拖动调整价格显示范围
- **实现位置**: `vnpy/chart/widget_mouse.py`
- **主要方法**:
  - `_is_mouse_on_right_axis()`: 检测鼠标是否在右侧坐标轴区域
  - `_init_axis_drag_state()`: 初始化坐标轴拖拽状态
- **交互方式**:
  - 在右侧60像素的坐标轴区域按住鼠标左键
  - 向上拖动：价格范围向上移动（显示更高价格）
  - 向下拖动：价格范围向下移动（显示更低价格）
  - 鼠标悬停在坐标轴区域时显示垂直调整光标

#### 2. 底部时间轴拖拽
- **功能描述**: 鼠标左键按住图表底部时间轴，可以向右拖动显示更多未来空间
- **实现位置**: `vnpy/chart/widget_mouse.py`
- **主要方法**:
  - `_is_mouse_on_bottom_axis()`: 检测鼠标是否在底部时间轴区域
- **交互方式**:
  - 在底部50像素的时间轴区域按住鼠标左键
  - 向右拖动：增加右侧索引，显示更多未来空间
  - 动态更新 `_future_bars` 以允许显示超出当前数据范围的未来空间
  - 鼠标悬停在时间轴区域时显示水平调整光标

### 技术实现

#### 坐标轴区域检测
- 使用 widget 坐标系统进行检测
- 右侧坐标轴：检测鼠标是否在 widget 右侧60像素内
- 底部时间轴：检测鼠标是否在 widget 底部50像素内
- 结合场景坐标转换，精确定位鼠标所在的 plot

#### 拖拽状态管理
```python
_axis_drag_state = {
    'is_dragging': False,          # Y轴拖拽状态
    'is_dragging_x_axis': False,   # X轴拖拽状态
    'start_pos': None,             # 拖拽起始位置
    'start_y_range': None,         # Y轴起始范围
    'start_x_range': None,         # X轴起始范围
    'start_right_ix': None,        # 起始右侧索引
    'target_plot': None            # 目标plot
}
```

#### 坐标转换
- 拖动距离（像素）转换为价格/索引变化
- Y轴：`price_delta = (dy_pixels / plot_height) * y_range`
- X轴：`index_delta = (dx_pixels / plot_width) * x_range`

### 测试

#### 新增测试用例
在 `tests/chart/test_widget_mouse_qt.py` 中新增：

1. `test_mouse_drag_right_axis_basic`: 测试右侧坐标轴基本拖拽
2. `test_mouse_drag_right_axis_downward`: 测试向下拖拽
3. `test_mouse_hover_right_axis_cursor`: 测试光标变化
4. `test_mouse_drag_right_axis_continuous`: 测试连续拖拽
5. `test_mouse_drag_right_axis_multiple_plots`: 测试多plot场景

所有测试用例均通过。

### 文档更新

- 更新 `tests/chart/QTTEST_MOUSE_EVENTS_README.md`，添加坐标轴拖拽测试说明
- 创建 `docs/chart_axis_drag_changelog.md` 变更日志

### 兼容性

- ✅ 完全向后兼容
- ✅ 不影响现有功能
- ✅ 与价格线拖拽、画线下单等功能兼容

### 使用示例

```python
# 功能自动启用，无需额外配置
# 用户可以直接在图表上：
# 1. 在右侧坐标轴区域按住鼠标拖动，调整价格显示范围
# 2. 在底部时间轴区域按住鼠标拖动，显示更多未来空间
```

### 未来改进

1. 添加拖拽动画效果
2. 支持键盘快捷键辅助拖拽
3. 添加拖拽速度限制，避免过快变化
4. 优化多plot场景下的拖拽体验

---

**更新日期**: 2025-12-01  
**状态**: ✅ 已完成并测试通过

