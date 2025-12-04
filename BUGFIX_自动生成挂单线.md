# Bug修复：多周期下自动生成挂单线

## 问题

多周期模式下，刚开启画线下单功能，还没有画线，就自动显示了挂单止损线和挂单止盈线。

## 根本原因

在 `_switch_to_multi_timeframe_mode()` 方法中（第4247-4261行）：

```python
# ❌ 旧代码：同步所有价格线
for line_id, line in single_chart_lines.items():
    if not multi_chart_manager.get_line(line_id):
        # 将单周期图表的价格线复制到多周期图表
        multi_chart_manager.add_line(line_id, line)
        multi_chart._first_plot.addItem(line)
```

**问题**：
- 这个逻辑会同步单周期图表上的**所有**价格线
- 包括挂单止损止盈线（未关联到入场线的止损止盈线）
- 导致多周期图表上出现不应该显示的挂单线

## 什么是挂单止损止盈线？

### 挂单线的特点

```python
# 挂单止损止盈线（未激活）：
# - 类型：PriceLineType.STOP_LOSS 或 PriceLineType.TAKE_PROFIT
# - entry_line_id：None 或 空字符串（未关联到入场线）
# - 状态：挂单状态（待激活）
# - 创建时机：开启画线下单功能时，自动创建
# - 用途：用户可以拖动这些线，设置止损止盈价格
```

### 已激活的止损止盈线

```python
# 已激活的止损止盈线：
# - 类型：PriceLineType.STOP_LOSS 或 PriceLineType.TAKE_PROFIT
# - entry_line_id：有值（关联到入场线）✅
# - 状态：激活状态
# - 创建时机：模拟成交后，关联到入场线
# - 用途：监控价格，触发止损止盈平仓
```

## 修复方案

### 只同步已激活的价格线

```python
# ✅ 新代码：筛选需要同步的价格线
for line_id, line in single_chart_lines.items():
    line_type = line.get_line_type()
    should_sync = False
    
    # 1. 入场线：始终同步
    if line_type == PriceLineType.ENTRY:
        should_sync = True
    
    # 2. 止损止盈线：只同步已关联到入场线的（不同步挂单线）
    elif line_type in [PriceLineType.STOP_LOSS, PriceLineType.TAKE_PROFIT]:
        if hasattr(line, 'entry_line_id') and line.entry_line_id:
            should_sync = True  # 已激活的止损止盈线
        else:
            should_sync = False  # 挂单线，不同步
    
    # 3. 挂单线：始终同步
    elif line_type == PriceLineType.PENDING:
        should_sync = True
    
    if should_sync:
        # 添加到多周期图表
        multi_chart_manager.add_line(line_id, line)
```

## 修改内容

### 文件：vnpy/trader/ui/widget.py

**修改位置**：`_switch_to_multi_timeframe_mode()` 方法（第4247-4261行）

**关键改变**：
1. 添加了 `should_sync` 判断逻辑
2. 入场线：始终同步
3. 止损止盈线：只同步已关联到入场线的
4. 挂单线（PENDING）：始终同步
5. 挂单止损止盈线：不同步

**日志输出**：
```
[ChartWindow] 同步已激活的stop_loss线: stop_xxx (关联到 entry_xxx)
[ChartWindow] 跳过未激活的stop_loss线: stop_pending_xxx (挂单线，未关联入场线)
[ChartWindow] 已同步 X 条价格线到多周期图表（过滤了挂单止损止盈线）
```

## 价格线同步策略

### 应该同步的线

✅ **入场线（ENTRY）**：
- 代表持仓
- 需要在多周期图表上显示

✅ **已激活的止损止盈线**：
- 关联到入场线（`entry_line_id` 有值）
- 代表实际的止损止盈设置
- 需要在多周期图表上显示

✅ **挂单线（PENDING）**：
- 代表未成交的挂单
- 需要在多周期图表上显示

### 不应该同步的线

❌ **挂单止损止盈线**：
- 未关联到入场线（`entry_line_id` 为空）
- 只是画线下单的预设线（用于拖动设置价格）
- 不应该自动出现在多周期图表上
- 用户在多周期图表启用画线下单时，会重新创建

## 数据流

### ❌ 旧方案：同步所有线

```
单周期图表:
  - 入场线 entry_xxx ✅
  - 已激活止损线 stop_xxx (entry_line_id = entry_xxx) ✅
  - 已激活止盈线 profit_xxx (entry_line_id = entry_xxx) ✅
  - 挂单止损线 stop_pending_xxx (entry_line_id = None) ❌
  - 挂单止盈线 profit_pending_xxx (entry_line_id = None) ❌
  ↓
切换到多周期:
  → 同步所有5条线 ❌
  ↓
多周期图表:
  - 5条线都显示（包括不应该显示的挂单线）❌
```

### ✅ 新方案：只同步已激活的线

```
单周期图表:
  - 入场线 entry_xxx ✅
  - 已激活止损线 stop_xxx (entry_line_id = entry_xxx) ✅
  - 已激活止盈线 profit_xxx (entry_line_id = entry_xxx) ✅
  - 挂单止损线 stop_pending_xxx (entry_line_id = None) ❌
  - 挂单止盈线 profit_pending_xxx (entry_line_id = None) ❌
  ↓
切换到多周期:
  → 筛选：只同步前3条（已激活的）
  → 跳过：后2条（挂单线）
  ↓
多周期图表:
  - 只显示3条线（入场线 + 已激活的止损止盈线）✅
```

## 用户启用画线下单时的行为

### 单周期模式

```
启用画线下单:
  → controller.enable()
  → 自动创建挂单止损止盈线
  → 用户可以拖动设置价格
```

### 多周期模式

```
启用画线下单:
  → controller.enable()
  → 自动创建挂单止损止盈线
  → 用户可以拖动设置价格

注意：多周期图表的挂单线是独立创建的，不是从单周期同步的
```

## 测试验证

### 测试场景1：无持仓时切换

```
操作:
  1. 单周期模式，启用画线下单（自动创建挂单线）
  2. 切换到多周期模式
  3. 启用画线下单

预期结果:
  - ✅ 切换时不显示挂单线
  - ✅ 启用画线下单后，多周期图表自己创建挂单线
```

### 测试场景2：有持仓时切换

```
操作:
  1. 单周期模式，模拟成交（创建入场线 + 已激活的止损止盈线）
  2. 切换到多周期模式

预期结果:
  - ✅ 同步入场线
  - ✅ 同步已激活的止损止盈线
  - ✅ 不同步挂单止损止盈线

预期日志:
  [ChartWindow] 同步已激活的stop_loss线: stop_xxx (关联到 entry_xxx)
  [ChartWindow] 同步已激活的take_profit线: profit_xxx (关联到 entry_xxx)
  [ChartWindow] 跳过未激活的stop_loss线: stop_pending_xxx (挂单线，未关联入场线)
  [ChartWindow] 已同步 3 条价格线到多周期图表（过滤了挂单止损止盈线）
```

## 总结

**核心修复**：
- ✅ 切换到多周期时，只同步已激活的价格线
- ✅ 不同步挂单止损止盈线
- ✅ 多周期图表启用画线下单时会独立创建挂单线

**关键点**：
- 挂单线的判断：`entry_line_id` 为空
- 已激活线的判断：`entry_line_id` 有值
- 入场线和挂单线（PENDING）：始终同步

修复完成！🎉
