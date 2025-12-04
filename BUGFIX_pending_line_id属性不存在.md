# Bug修复：pending_line_id 属性不存在

## 问题

启用画线下单时报错：

```
AttributeError: 'PriceLineItem' object has no attribute 'pending_line_id'
  File "vnpy/chart/widget.py", line 501
    reason.append(f"关联挂单线={line.pending_line_id}")
```

## 原因

在 `_cleanup_pending_stop_profit_lines()` 方法的日志输出部分（第501行），尝试访问 `line.pending_line_id` 属性，但：

**PriceLineItem 没有 `pending_line_id` 属性！**

挂单止损止盈线与挂单线的关联关系是通过 `DrawingOrderController._pending_line_relations` 字典维护的，不是通过对象属性。

## 修复

### 修改前

```python
if has_pending:
    reason.append(f"关联挂单线={line.pending_line_id}")  # ❌ 属性不存在
```

### 修改后

```python
if has_pending:
    reason.append("关联挂单线")  # ✅ 不访问不存在的属性
```

## 说明

### PriceLineItem 的实际属性

PriceLineItem 对象只有以下关联相关的属性：
- `entry_line_id`：关联的入场线ID（对于已激活的止损止盈线）
- 无 `pending_line_id` 属性

### 关联关系维护方式

**挂单止损止盈线 → 挂单线**：
- 通过 `DrawingOrderController._pending_line_relations` 字典
- 格式：`{pending_line_id: {'stop_loss': {...}, 'take_profit': {...}}}`

**止损止盈线 → 入场线**：
- 通过 `ChartWidget._entry_line_relations` 字典
- 或通过 `line.entry_line_id` 属性

## 修改内容

**文件**：`vnpy/chart/widget.py`

**位置**：第488行

**修改**：日志输出从 `f"关联挂单线={line.pending_line_id}"` 改为 `"关联挂单线"`

## 总结

✅ 移除对不存在属性的访问
✅ 日志输出简化但仍然清晰

修复完成！🎉

