# Bug修复：关闭画线下单不应删除挂单止损止盈线

## 问题

多周期模式下：
1. 打开画线下单
2. 对话框选择设置止损止盈线
3. 画一条多单挂线
4. 生成了挂单止损线止盈线
5. **关闭画线下单功能**
6. ❌ 刚生成的挂单止损止盈线被删掉了（不应该删除）

## 问题分析

### 当前行为

`DrawingOrderController.disable()` 方法只清理预览线（PREVIEW），**不应该**删除挂单止损止盈线。

### 期望行为

关闭画线下单功能时：
- ✅ 保留挂单线（PENDING）
- ✅ **保留挂单止损止盈线**（用户设置的交易辅助线）
- ✅ 保留已激活的止损止盈线（关联到入场线的）

### 原因

挂单止损止盈线是用户设置的交易辅助线，不应该因为关闭画线下单功能而被删除：
1. 这些线是用户主动设置的，应该保留
2. 关闭画线下单功能只是禁用画线模式，不应该影响已存在的价格线
3. 只有当挂单线被删除（例如双击删除挂单）时，才会删除关联的止损止盈线

## 修复方案

### 修改 `DrawingOrderController.disable()` 方法

在 `disable()` 方法中**不删除**挂单止损止盈线，只清理预览线：

```python
def disable(self) -> None:
    """Disable drawing order mode."""
    # ... 清理预览线 ...
    
    # ✅ 注意：不删除挂单止损止盈线
    # 挂单止损止盈线应该保留，即使关闭画线下单功能
    # 这些线是用户设置的交易辅助线，不应该因为关闭画线下单功能而被删除
    # 只有当挂单线被删除（例如双击删除挂单）时，才会删除关联的止损止盈线
```

### 关键点

1. **不删除挂单止损止盈线**：
   - 关闭画线下单功能只是禁用画线模式
   - 不应该影响已存在的价格线（包括挂单止损止盈线）

2. **保留所有价格线**：
   - 挂单线（PENDING）保留
   - 挂单止损止盈线保留
   - 已激活的止损止盈线保留

3. **删除时机**：
   - 只有当挂单线被删除（例如双击删除挂单）时，才会删除关联的止损止盈线
   - 这个逻辑在 `mouseDoubleClickEvent` 中实现

## 修改内容

### 文件：vnpy/chart/drawing_order.py

**修改方法**：`disable()`（第99-121行）

**修改内容**：
1. 移除删除挂单止损止盈线的逻辑（如果之前有）
2. 只清理预览线（PREVIEW）
3. 添加注释说明不删除挂单止损止盈线

## 测试验证

### 测试场景

```
操作:
  1. 多周期模式
  2. 打开画线下单
  3. 对话框选择设置止损止盈线
  4. 画一条多单挂线
  5. 观察挂单止损止盈线出现
  6. 关闭画线下单功能

预期日志:
  [DrawingOrderController] 关闭画线下单模式时清理了 X 条预览线

预期结果:
  - ✅ 挂单线保留
  - ✅ 挂单止损止盈线保留（不被删除）
  - ✅ 如果挂单成交，止损止盈线会激活（关联到入场线）
```

### 边界情况

1. **挂单已成交**：
   - 挂单止损止盈线已激活（`entry_line_id` 不为空）
   - 不应该被删除 ✅

2. **没有挂单线**：
   - `_pending_line_relations` 为空
   - 不执行删除逻辑 ✅

3. **挂单线已删除**：
   - 挂单线不在 `pending_line_ids` 中
   - 跳过该挂单线的关联关系 ✅

## 总结

**核心修复**：
- ✅ 在 `disable()` 方法中**不删除**挂单止损止盈线
- ✅ 只清理预览线（PREVIEW）
- ✅ 保留所有价格线（挂单线、挂单止损止盈线、已激活的止损止盈线）

**关键点**：
- 挂单止损止盈线是用户设置的交易辅助线，应该保留
- 关闭画线下单功能只是禁用画线模式，不应该影响已存在的价格线
- 只有当挂单线被删除（例如双击删除挂单）时，才会删除关联的止损止盈线

## 补充修复：正确检查挂单关联

### 问题发现

用户报告仍然有删除问题，检查后发现：

**原因**：`_cleanup_pending_stop_profit_lines()` 检查 `pending_line_id` 属性，但挂单止损止盈线没有这个属性！

```python
# ❌ 错误检查方式
has_pending = hasattr(line, 'pending_line_id') and line.pending_line_id
```

**实际情况**：
- 挂单止损止盈线通过 `DrawingOrderController._pending_line_relations` 字典关联
- 不是通过 `pending_line_id` 属性关联

### 修复方式

**修改 `ChartWidget._cleanup_pending_stop_profit_lines()` 方法**：

```python
# ✅ 正确检查方式：通过 _pending_line_relations 字典
has_pending = False
if hasattr(self, '_drawing_order_controller'):
    if hasattr(self._drawing_order_controller, '_pending_line_relations'):
        # 遍历所有挂单线的关联关系
        for pending_id, relations in self._drawing_order_controller._pending_line_relations.items():
            if pending_id in pending_line_ids:  # 挂单线仍然存在
                # 检查当前止损止盈线是否是这个挂单线的关联线
                if relations.get('stop_loss', {}).get('line_id') == line_id:
                    has_pending = True
                    break
                if relations.get('take_profit', {}).get('line_id') == line_id:
                    has_pending = True
                    break
```

### 文件：vnpy/chart/widget.py

**修改位置**：`_cleanup_pending_stop_profit_lines()` 方法（第463行）

**关键改进**：
- 从 `_pending_line_relations` 字典中查找关联关系
- 而不是检查不存在的 `pending_line_id` 属性

修复完成！🎉

