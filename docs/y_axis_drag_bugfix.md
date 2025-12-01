# Y轴拖拽功能Bug修复总结

## 修复日期
2025-12-02

## 问题描述

在使用图表组件时，发现Y轴拖拽功能存在以下问题：

1. **Y轴向上拖拽不能动**：当价格处于周期最高值时，无法向上拖拽Y轴查看更高价格
2. **拖拽X轴会自动改变Y轴位置**：拖拽X轴（时间轴）时，Y轴范围会被自动重置，覆盖用户手动设置的范围
3. **Y轴拖拽单位太小**：拖拽灵敏度太低，如果不小心拖到最底部，非常难回到最上面

## 根本原因分析

### 问题1：Y轴向上拖拽限制
- `_update_plot_limits` 方法将Y轴的最大值限制为数据的最大值（`yMax=max_value`）
- 当价格处于周期最高值时，Y轴无法超出数据范围，导致无法向上拖拽

### 问题2：X轴拖拽影响Y轴
- `sigXRangeChanged` 信号在X轴范围改变时会触发 `_update_y_range` 方法
- 虽然代码中有检查 `y_axis_manually_set`，但在X轴拖拽时检查不够完善
- 导致拖拽X轴时，Y轴范围被自动重置

### 问题3：拖拽灵敏度低
- 拖拽时价格移动量计算公式：`price_delta = (total_dy_pixels / plot_height) * y_range`
- 当plot高度较大时，单位像素对应的价格变化很小，导致拖拽效率低

## 修复方案

### 1. 移除Y轴拖拽限制

**文件**: `vnpy/chart/widget_mouse.py`

在开始拖拽Y轴时，临时移除Y轴限制，允许无限制拖拽：

```python
# 放宽Y轴限制，允许无限制拖拽
if hasattr(self, '_item_plot_map') and target_plot in self._item_plot_map.values():
    for item, plot in self._item_plot_map.items():
        if plot == target_plot:
            import sys
            max_float = sys.float_info.max
            min_float = -sys.float_info.max
            
            target_plot.setLimits(
                yMin=min_float,  # 无最小值限制
                yMax=max_float   # 无最大值限制
            )
            break
```

**关键改动**:
- 使用 `sys.float_info.max` 和 `-sys.float_info.max` 实现无限制拖拽
- 即使价格处于周期最高值，也可以向上拖拽查看更高价格

### 2. 防止X轴拖拽影响Y轴

**文件**: `vnpy/chart/widget_chart.py`

在 `_update_y_range` 方法中添加X轴拖拽检查：

```python
# 如果正在拖动X轴，且Y轴已被手动设置，跳过自动更新
if hasattr(self, '_axis_drag_state') and self._axis_drag_state.get('is_dragging_x_axis'):
    if hasattr(self, '_axis_drag_state') and self._axis_drag_state.get('y_axis_manually_set'):
        return
```

**关键改动**:
- 检测X轴拖拽状态
- 如果Y轴已被手动设置，在X轴拖拽时跳过Y轴自动更新
- 保持用户手动设置的Y轴范围

### 3. 增加Y轴拖拽灵敏度

**文件**: `vnpy/chart/widget_mouse.py`

在计算价格移动量时增加灵敏度系数：

```python
# 增加灵敏度系数（3倍），使拖拽更容易控制
sensitivity = 3.0  # 灵敏度系数，值越大拖拽越快
price_delta = (total_dy_pixels / plot_height) * y_range * sensitivity
```

**关键改动**:
- 添加灵敏度系数（3.0倍）
- 使拖拽更加灵敏，更容易控制
- 减少拖拽到极端位置后难以恢复的问题

### 4. 添加双击Y轴快速回到数据范围功能

**文件**: `vnpy/chart/widget_mouse.py`

在 `mouseDoubleClickEvent` 方法中添加双击Y轴检测：

```python
# 检查是否双击了右侧坐标轴区域（Y轴）
is_on_axis, target_plot = self._is_mouse_on_right_axis(event)
if is_on_axis and target_plot:
    # 获取当前X轴范围对应的数据范围
    # 重置Y轴范围到数据范围
    # 清除手动设置标志，恢复自动范围更新
    # 恢复Y轴限制到数据范围
```

**关键改动**:
- 检测双击Y轴区域
- 自动计算当前X轴范围对应的数据Y轴范围
- 重置Y轴到数据范围
- 恢复自动更新和限制设置
- 提供快速恢复功能，解决拖拽到极端位置的问题

## 技术细节

### 使用 `plot.setRange()` 而不是 `view_box.setYRange()`

为了与X轴拖拽保持一致，Y轴拖拽也使用 `plot.setRange()` 方法：

```python
# 使用plot.setRange设置Y轴范围（与X轴拖拽保持一致的方式）
target_plot.setRange(yRange=(new_y_min, new_y_max), padding=0)
```

### 禁用自动范围更新

在拖拽过程中和拖拽结束后，保持禁用自动范围更新：

```python
# 禁用Y轴自动范围更新，防止拖拽时被自动重置
view_box.disableAutoRange(axis='y')
# 标记Y轴已被手动设置
self._axis_drag_state['y_axis_manually_set'] = True
```

## 测试建议

1. **测试Y轴向上拖拽**：
   - 加载价格处于周期最高值的数据
   - 尝试向上拖拽Y轴
   - 验证可以拖拽到超出数据范围的位置

2. **测试X轴拖拽不影响Y轴**：
   - 手动拖拽Y轴到某个位置
   - 然后拖拽X轴
   - 验证Y轴位置保持不变

3. **测试拖拽灵敏度**：
   - 拖拽Y轴，验证灵敏度是否合适
   - 如果拖拽到极端位置，验证双击Y轴可以快速恢复

4. **测试双击恢复功能**：
   - 将Y轴拖拽到极端位置（最上或最下）
   - 双击Y轴
   - 验证Y轴自动回到数据范围

## 相关文件

- `vnpy/chart/widget_mouse.py` - 鼠标事件处理和拖拽逻辑
- `vnpy/chart/widget_chart.py` - 图表更新和Y轴范围管理

## 后续优化建议

1. **灵敏度可配置**：可以考虑将灵敏度系数作为配置项，允许用户自定义
2. **拖拽范围限制**：虽然允许无限制拖拽，但可以考虑添加合理的范围限制，避免拖拽到过于极端的位置
3. **快捷键支持**：可以考虑添加快捷键来快速重置Y轴范围

## 提交信息

相关提交：
- `修复Y轴向上拖拽限制问题 - 允许无限制拖拽`
- `修复Y轴向上拖拽不能动的问题`
- `修复拖拽X轴时自动改变Y轴位置的问题`
- `增加Y轴拖拽灵敏度并添加双击恢复功能`

