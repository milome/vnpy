# 🔴 核心Bug修复：多周期模式画线不显示

## 问题诊断

从你的日志可以看到，价格线**已经成功创建**：
```
创建挂单线: MHImain.HKFE 多 1@25827
创建止损线: 25777
创建止盈线: 25877
```

但是**看不见**！

## 🎯 根本原因

**核心问题**: 在 `_create_pending_order_line()` 方法中，价格线被添加到了**错误的图表**！

### 问题代码

```python
def _create_pending_order_line(self, params: dict) -> None:
    # ...
    
    # ❌ 问题：总是使用 self.chart（单周期图表）
    controller = self.chart.get_drawing_order_controller()
    line = self.chart._price_line_manager.get_line(line_id)
    self.chart._price_line_manager.update_line_price(line_id, params["price"])
    self.chart._breakthrough_monitor.register_line(...)
    
    # 止损线也添加到 self.chart
    stop_loss_line_id = self.chart._price_line_manager.create_line(...)
    stop_loss_line = self.chart._price_line_manager.get_line(...)
    self.chart._first_plot.addItem(stop_loss_line)  # ❌ 添加到单周期图表的plot
    
    # 止盈线也添加到 self.chart
    take_profit_line_id = self.chart._price_line_manager.create_line(...)
    take_profit_line = self.chart._price_line_manager.get_line(...)
    self.chart._first_plot.addItem(take_profit_line)  # ❌ 添加到单周期图表的plot
```

**结果**: 
- 价格线被创建了（所以日志显示"创建成功"）
- 但价格线被添加到了 `self.chart`（单周期图表）
- 而当前显示的是 `multi_timeframe_widget._chart`（多周期图表）
- 所以**看不见**！

## ✅ 已修复

### 修复内容

在 `_create_pending_order_line()` 方法开头添加了图表选择逻辑：

```python
def _create_pending_order_line(self, params: dict) -> None:
    """从画线模式创建挂单线"""
    
    # ✅ 修复：根据当前显示模式选择正确的图表
    if self.display_mode == "multi" and self.multi_timeframe_widget:
        # 多周期模式：使用 MultiTimeframeWidget 的图表
        chart = self.multi_timeframe_widget._chart
        print(f"[ChartWindow] 多周期模式：使用 multi_timeframe_widget._chart 创建价格线")
    else:
        # 单周期模式：使用 ChartWindow 的图表
        chart = self.chart
        print(f"[ChartWindow] 单周期模式：使用 self.chart 创建价格线")
    
    # 然后所有价格线操作都使用这个 chart
    controller = chart.get_drawing_order_controller()  # ✅ 使用正确的图表
    line = chart._price_line_manager.get_line(line_id)  # ✅ 使用正确的图表
    chart._price_line_manager.update_line_price(...)  # ✅ 使用正确的图表
    chart._breakthrough_monitor.register_line(...)  # ✅ 使用正确的图表
    
    # 止损线
    stop_loss_line_id = chart._price_line_manager.create_line(...)  # ✅ 使用正确的图表
    chart._first_plot.addItem(stop_loss_line)  # ✅ 添加到正确的plot
    
    # 止盈线
    take_profit_line_id = chart._price_line_manager.create_line(...)  # ✅ 使用正确的图表
    chart._first_plot.addItem(take_profit_line)  # ✅ 添加到正确的plot
```

### 修复的位置

已将以下所有 `self.chart` 替换为 `chart`（动态选择的图表）：

1. ✅ `controller = chart.get_drawing_order_controller()`
2. ✅ `line = chart._price_line_manager.get_line(line_id)`
3. ✅ `chart._price_precision = price_precision`
4. ✅ `chart._price_line_manager.update_line_price(...)`
5. ✅ `chart._breakthrough_monitor.register_line(...)`
6. ✅ `chart._on_price_breakthrough`
7. ✅ `stop_loss_line_id = chart._price_line_manager.create_line(...)`
8. ✅ `stop_loss_line = chart._price_line_manager.get_line(...)`
9. ✅ `chart._first_plot.addItem(stop_loss_line)`
10. ✅ `take_profit_line_id = chart._price_line_manager.create_line(...)`
11. ✅ `take_profit_line = chart._price_line_manager.get_line(...)`
12. ✅ `chart._first_plot.addItem(take_profit_line)`

## 🧪 验证修复

### 重新测试

1. **重新启动程序**
   ```bash
   update_and_run_worktree.bat
   ```

2. **操作流程**
   - 加载数据（单周期模式）
   - 切换到多周期模式
   - 点击"画线下单"
   - 在图表上画线

3. **查看日志**

应该看到：
```
[ChartWindow] 多周期模式：使用 multi_timeframe_widget._chart 创建价格线
创建挂单线: MHImain.HKFE 多 1@25827
[ChartWindow] 挂单线已创建: line_id=pending_xxx, 使用图表: multi  ← 确认使用多周期图表
创建止损线: 25777
创建止盈线: 25877
```

4. **预期效果**

画线后应该能**立即看到**：
- 🔴 挂单线（带向上或向下箭头）
- 🟡 止损线（水平虚线）
- 🟢 止盈线（水平虚线）

## 原理说明

### 为什么之前看不见？

ChartWindow 有两个图表实例：

1. **self.chart**: 单周期模式的 ChartWidget
2. **self.multi_timeframe_widget._chart**: 多周期模式的 ChartWidget

它们是**独立的**：
- 有独立的 PriceLineManager
- 有独立的 Plot
- 有独立的 Item 集合

### 之前的错误

```
多周期模式：
  显示的图表: multi_timeframe_widget._chart  ← 用户看到的
  价格线添加到: self.chart                  ← 添加错了！
  结果: 看不见！
```

### 修复后

```
多周期模式：
  显示的图表: multi_timeframe_widget._chart  ← 用户看到的
  价格线添加到: multi_timeframe_widget._chart  ← 添加正确！
  结果: 可以看见！✅
```

## 影响范围

此修复影响以下功能：
- ✅ 挂单线创建
- ✅ 止损线创建
- ✅ 止盈线创建
- ✅ 价格线移动
- ✅ 价格线删除
- ✅ 价格突破触发

所有价格线相关操作都会正确路由到当前显示的图表。

## 测试清单

- [ ] 多周期模式下创建挂单线
- [ ] 多周期模式下创建止损线
- [ ] 多周期模式下创建止盈线
- [ ] 多周期模式下移动价格线
- [ ] 多周期模式下删除价格线
- [ ] 单周期模式下功能仍然正常（确保没有破坏现有功能）
- [ ] 模式切换后价格线保持

## 总结

**核心修复**: 在 `_create_pending_order_line()` 中，根据 `display_mode` 动态选择正确的图表实例。

**影响**: 所有使用 `self.chart` 的地方都改为使用 `chart`（动态选择的图表）。

现在重新测试，画线应该能正常显示了！🎉

