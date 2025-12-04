# Bug修复：模拟函数中的 chart 未定义

## 问题

模拟止损时报错：

```
NameError: name 'chart' is not defined. Did you mean: 'self.chart'?
```

## 根本原因

在 `simulate_stop_loss()` 和 `simulate_take_profit()` 方法中，直接使用了 `chart` 变量，但这个变量没有定义。

### 代码位置

**文件**：`vnpy/trader/ui/widget.py`

**方法**：
- `simulate_stop_loss()` - 第7455行
- `simulate_take_profit()` - 第7601行

### 错误代码

```python
# ❌ 错误：chart 变量未定义
result = chart.trigger_stop_loss_close(line_id, line, simulate_tick)
```

## 修复方案

### 根据当前模式选择正确的图表

```python
# ✅ 正确：根据 display_mode 选择图表
if self.display_mode == "多周期叠加":
    chart = self.multi_timeframe_widget._chart  # 使用多周期图表
else:
    chart = self.chart  # 使用单周期图表

# 现在可以安全地使用 chart 变量
result = chart.trigger_stop_loss_close(line_id, line, simulate_tick)
```

## 修改内容

### 文件：vnpy/trader/ui/widget.py

**修改1**：`simulate_stop_loss()` 方法（第7455行）

```python
# 修改前：
result = chart.trigger_stop_loss_close(line_id, line, simulate_tick)

# 修改后：
# 根据当前模式选择正确的图表
if self.display_mode == "多周期叠加":
    chart = self.multi_timeframe_widget._chart
else:
    chart = self.chart

result = chart.trigger_stop_loss_close(line_id, line, simulate_tick)
```

**修改2**：`simulate_take_profit()` 方法（第7601行）

```python
# 修改前：
result = chart.trigger_take_profit_close(line_id, line, simulate_tick)

# 修改后：
# 根据当前模式选择正确的图表
if self.display_mode == "多周期叠加":
    chart = self.multi_timeframe_widget._chart
else:
    chart = self.chart

result = chart.trigger_take_profit_close(line_id, line, simulate_tick)
```

## 为什么需要选择图表？

### 两种模式，两个图表

```
单周期模式:
  - 使用 self.chart (ChartWidget)
  - 价格线在 self.chart 上

多周期模式:
  - 使用 self.multi_timeframe_widget._chart (ChartWidget)
  - 价格线在 multi_timeframe_widget._chart 上
```

### 模拟函数需要操作当前激活的图表

```python
# 模拟止损/止盈的逻辑
def simulate_stop_loss():
    # 1. 从当前图表获取价格线
    if self.display_mode == "多周期叠加":
        chart = self.multi_timeframe_widget._chart
    else:
        chart = self.chart
    
    # 2. 触发止损平仓
    chart.trigger_stop_loss_close(...)
```

## 相关方法

以下方法也使用了类似的图表选择逻辑：

1. **`simulate_transaction()`** - 模拟成交
2. **`simulate_trade_breakthrough()`** - 模拟突破成交
3. **`simulate_stop_loss()`** - 模拟止损
4. **`simulate_take_profit()`** - 模拟止盈

所有这些方法都需要根据 `display_mode` 选择正确的图表。

## 测试验证

### 测试场景1：单周期模式

```
操作:
  1. 单周期模式
  2. 模拟成交
  3. 模拟止损

预期结果:
  - ✅ 使用 self.chart
  - ✅ 止损成功
  - ✅ 入场线和止损止盈线被删除
```

### 测试场景2：多周期模式

```
操作:
  1. 多周期模式
  2. 模拟成交
  3. 模拟止损

预期结果:
  - ✅ 使用 self.multi_timeframe_widget._chart
  - ✅ 止损成功
  - ✅ 入场线和止损止盈线被删除（使用数据库查找关联关系）
```

## 总结

**核心修复**：
- ✅ 在 `simulate_stop_loss()` 中添加 chart 变量定义
- ✅ 在 `simulate_take_profit()` 中添加 chart 变量定义
- ✅ 根据 `display_mode` 选择正确的图表

**关键点**：
- 单周期和多周期使用不同的图表对象
- 模拟函数需要操作当前激活的图表
- 必须先定义 chart 变量再使用

修复完成！🎉

