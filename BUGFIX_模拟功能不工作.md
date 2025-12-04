# Bug修复：多周期模式下模拟功能不工作

## 问题

模拟成交、模拟止损、模拟止盈按钮在多周期模式下不能用。

从用户反馈可以看到：
- 点击"模拟成交"按钮
- 弹出提示："当前没有挂单线,请先创建挂单线后再使用模拟成交功能。"
- 但实际上图表上**有价格线显示**（挂单线、止损线、止盈线）

## 根本原因

和之前的画线不显示问题一样：**模拟功能也在使用错误的图表**！

### 问题代码

```python
def simulate_transaction(self) -> None:
    # ❌ 问题：总是使用 self.chart（单周期图表）
    price_line_manager = self.chart._price_line_manager
    all_lines = price_line_manager.get_all_lines()  # 从单周期图表获取
    
    # 结果：找不到多周期图表中的价格线！
```

**结果**:
- 价格线在多周期图表中（`multi_timeframe_widget._chart`）
- 但模拟功能在单周期图表中查找（`self.chart`）
- 所以找不到价格线！

## ✅ 已修复

### 修复1: simulate_transaction()

```python
def simulate_transaction(self) -> None:
    # ✅ 根据模式选择正确的图表
    if self.display_mode == "multi" and self.multi_timeframe_widget:
        chart = self.multi_timeframe_widget._chart
    else:
        chart = self.chart
    
    # ✅ 使用正确的图表
    price_line_manager = chart._price_line_manager
    controller = chart.get_drawing_order_controller()
    chart.trigger_pending_order_breakthrough(...)
```

### 修复2: simulate_stop_loss()

```python
def simulate_stop_loss(self) -> None:
    # ✅ 根据模式选择正确的图表
    if self.display_mode == "multi" and self.multi_timeframe_widget:
        chart = self.multi_timeframe_widget._chart
    else:
        chart = self.chart
    
    # ✅ 使用正确的图表
    price_line_manager = chart._price_line_manager
    chart.trigger_stop_loss_breakthrough(...)
```

### 修复3: simulate_take_profit()

```python
def simulate_take_profit(self) -> None:
    # ✅ 根据模式选择正确的图表
    if self.display_mode == "multi" and self.multi_timeframe_widget:
        chart = self.multi_timeframe_widget._chart
    else:
        chart = self.chart
    
    # ✅ 使用正确的图表
    price_line_manager = chart._price_line_manager
    chart.trigger_take_profit_breakthrough(...)
```

## 修改清单

### simulate_transaction() 修改

- ✅ 图表选择逻辑
- ✅ `price_line_manager = chart._price_line_manager`
- ✅ `controller = chart.get_drawing_order_controller()`
- ✅ `chart._breakthrough_monitor`
- ✅ `chart.trigger_pending_order_breakthrough()`

### simulate_stop_loss() 修改

- ✅ 图表选择逻辑
- ✅ `price_line_manager = chart._price_line_manager`
- ✅ `chart.trigger_stop_loss_breakthrough()`

### simulate_take_profit() 修改

- ✅ 图表选择逻辑
- ✅ `price_line_manager = chart._price_line_manager`
- ✅ `chart.trigger_take_profit_breakthrough()`

## 🧪 测试验证

### 测试步骤

1. **重新启动程序**
   ```bash
   update_and_run_worktree.bat
   ```

2. **创建价格线**
   - 切换到多周期模式
   - 启用画线模式
   - 创建挂单线（带止损止盈）

3. **测试模拟成交**
   - 点击"模拟成交"按钮
   - **预期**: 应该找到挂单线并触发成交
   - **日志**: 应该显示 `[模拟成交] 找到 X 条价格线`，X > 0

4. **测试模拟止损**
   - 点击"模拟止损"按钮
   - **预期**: 应该找到止损线并触发平仓
   - **日志**: 应该显示 `[模拟止损] 找到 X 条价格线`，X > 0

5. **测试模拟止盈**
   - 点击"模拟止盈"按钮
   - **预期**: 应该找到止盈线并触发平仓
   - **日志**: 应该显示 `[模拟止盈] 找到 X 条价格线`，X > 0

### 预期日志输出

**修复前**:
```
[模拟成交] 找到 0 条价格线  ← 找不到！
当前没有挂单线,请先创建挂单线后再使用模拟成交功能。
```

**修复后**:
```
[ChartWindow] simulate_transaction: 使用多周期图表
[模拟成交] 找到 3 条价格线  ← 找到了！
[模拟成交] 找到 1 条挂单线
模拟成交成功: MHImain.HKFE 多 挂单线 25829 已触发突破并下单
```

## 原理说明

### 为什么之前找不到？

```
多周期模式：
  价格线存储在: multi_timeframe_widget._chart._price_line_manager  ← 实际位置
  模拟功能查找: self.chart._price_line_manager                      ← 查找错了！
  结果: 找不到！
```

### 修复后

```
多周期模式：
  价格线存储在: multi_timeframe_widget._chart._price_line_manager  ← 实际位置
  模拟功能查找: multi_timeframe_widget._chart._price_line_manager  ← 查找正确！
  结果: 找到了！✅
```

## 影响范围

此修复影响以下功能：
- ✅ 模拟成交（触发挂单线）
- ✅ 模拟止损（触发止损线）
- ✅ 模拟止盈（触发止盈线）

所有模拟功能都会正确路由到当前显示的图表。

## 相关修复

这是继"画线不显示"问题后的第二个相关修复：

1. ✅ **画线不显示** - 价格线添加到错误的图表
2. ✅ **模拟功能不工作** - 在错误的图表中查找价格线

两个问题都是因为使用了 `self.chart` 而不是根据模式动态选择图表。

## 总结

**核心修复**: 在所有模拟功能方法中，根据 `display_mode` 动态选择正确的图表实例。

**影响**: 所有使用 `self.chart` 的模拟功能都改为使用 `chart`（动态选择的图表）。

现在重新测试，模拟功能应该能正常工作了！🎉

