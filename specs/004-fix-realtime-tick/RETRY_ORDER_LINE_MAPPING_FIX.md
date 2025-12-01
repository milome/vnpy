# 修复：订单重试后挂单线无法关联的问题

**日期**: 2025-01-27  
**状态**: ✅ 已修复

## 问题描述

用户报告了一个严重问题：
> 挂单空仓触发后，经过委托下单超时重试最后成交，但挂单线已经关联不上，导致挂单线未删除，关联止损止盈也没迁移到入场线

### 问题场景

1. 用户在图表上画线创建挂单（空单）
2. 挂单触发后，gateway自动提交订单
3. 订单因超时等原因被撤销
4. Gateway的智能追价机制自动重试，生成新的订单ID
5. 新订单成功成交
6. **问题**：新订单无法关联到原始挂单线
7. **结果**：
   - 挂单线未被删除（仍然显示在图表上）
   - 止损/止盈线未迁移到入场线（停留在挂单线上）
   - 持仓显示不正确

### 根本原因

当订单被撤销并重试时，gateway会生成一个新的订单ID。但是 `DrawingOrderController` 中的映射关系 (`_line_order_map` 和 `_order_line_map`) 仍然记录着旧的订单ID与挂单线的关联。

当新订单的更新事件到达时：
1. `get_line_id_for_order(new_order_id)` 返回 `None`（因为新订单ID不在映射表中）
2. `_find_unlinked_pending_line` 被调用，试图找到未关联的挂单线
3. **但是**：由于旧订单ID仍然在 `_line_order_map` 中，挂单线被认为已经关联，无法被新订单匹配

## 修复方案

### 核心思路

在查找未关联挂单线时，不仅要检查映射表中是否存在关联，还要验证：
- 已关联的订单是否仍然有效（未撤销/未取消/未全部成交）
- 如果订单已被撤销/取消/成交，应该清理映射关系，将挂单线视为未关联

### 代码修改

#### 1. 增强 `_find_unlinked_pending_line` 方法

**位置**: `vnpy/chart/drawing_order.py:388-535`

**关键改进**：

```429:460:vnpy/chart/drawing_order.py
# ✅ 检查关联的订单是否已被撤销/取消
# 如果订单已撤销/取消，应该清理映射关系，将此挂单线视为未关联
is_order_cancelled = False
if linked_order_id and hasattr(self._widget, '_main_engine') and self._widget._main_engine:
    # 尝试从main_engine获取订单状态
    all_orders = self._widget._main_engine.get_all_orders()
    for o in all_orders:
        if o.vt_orderid == linked_order_id:
            from vnpy.trader.constant import Status
            if o.status in [Status.CANCELLED, Status.REJECTED]:
                is_order_cancelled = True
                # 清理映射关系
                self._line_order_map.pop(line_id, None)
                self._order_line_map.pop(linked_order_id, None)
                if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                    self._widget._main_engine.write_log(
                        f"[DrawingOrderController] 挂单线 {line_id} 关联的订单 {linked_order_id} 已被撤销/取消，已清理映射关系，将此挂单线视为未关联",
                        "DrawingOrderController"
                    )
                break
            # 如果订单已全部成交，也应该清理映射（订单已成交，挂单线应该已被删除或转换）
            elif o.status == Status.ALLTRADED:
                is_order_cancelled = True
                # 清理映射关系
                self._line_order_map.pop(line_id, None)
                self._order_line_map.pop(linked_order_id, None)
                if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
                    self._widget._main_engine.write_log(
                        f"[DrawingOrderController] 挂单线 {line_id} 关联的订单 {linked_order_id} 已全部成交，已清理映射关系，将此挂单线视为未关联",
                        "DrawingOrderController"
                    )
                break
```

**逻辑说明**：
- 当发现挂单线已关联到某个订单时，不再直接跳过
- 而是查询该订单的当前状态
- 如果订单状态为 `CANCELLED`、`REJECTED` 或 `ALLTRADED`，则：
  - 清理双向映射关系
  - 将此挂单线视为未关联，允许新订单匹配

#### 2. 处理 `CANCELLED` 状态时的映射清理

**位置**: `vnpy/chart/drawing_order.py:791-803`

```791:803:vnpy/chart/drawing_order.py
if order.status == StatusEnum.CANCELLED:
    # 订单被撤销：清理旧订单的映射关系，但保留挂单线，以便新订单（重委托）可以找到它
    if line_id:
        # 从反向映射中移除旧订单ID
        self._order_line_map.pop(order.vt_orderid, None)
        # 从正向映射中移除（但保留挂单线）
        self._line_order_map.pop(line_id, None)
        if hasattr(self._widget, '_main_engine') and self._widget._main_engine:
            self._widget._main_engine.write_log(
                f"[DrawingOrderController] 订单 {order.vt_orderid} 已撤销，已清理映射关系，保留挂单线 {line_id} 供新订单匹配",
                "DrawingOrderController"
            )
    return True
```

**逻辑说明**：
- 当订单被撤销时，立即清理映射关系
- **但保留挂单线**（不删除），以便重试订单能够找到它

#### 3. 强制查找逻辑中的类似处理

**位置**: `vnpy/chart/drawing_order.py:734-752`

在强制查找逻辑中也添加了相同的检查，确保在订单已成交但未关联挂单线的情况下，也能正确找到并关联挂单线。

## 修复效果

### 修复前

1. 挂单触发 → 订单提交（订单ID: `FUTU.6455221`）
2. 订单超时 → 被撤销（状态: `CANCELLED`）
3. 映射关系保留：`挂单线A -> FUTU.6455221`
4. Gateway重试 → 新订单提交（订单ID: `FUTU.6455230`）
5. 新订单成交 → 更新事件到达
6. `get_line_id_for_order(FUTU.6455230)` → 返回 `None`
7. `_find_unlinked_pending_line` → 发现挂单线A已关联到 `FUTU.6455221`，跳过
8. **结果**：挂单线未删除，止损/止盈线未迁移 ❌

### 修复后

1. 挂单触发 → 订单提交（订单ID: `FUTU.6455221`）
2. 订单超时 → 被撤销（状态: `CANCELLED`）
3. **立即清理映射关系**：`挂单线A -> FUTU.6455221` （已清除）
4. Gateway重试 → 新订单提交（订单ID: `FUTU.6455230`）
5. 新订单成交 → 更新事件到达
6. `get_line_id_for_order(FUTU.6455230)` → 返回 `None`
7. `_find_unlinked_pending_line` → 发现挂单线A未关联（映射已清理）→ **匹配成功**
8. `link_line_to_order(挂单线A, FUTU.6455230)` → 建立新关联
9. 删除挂单线 → 创建入场线 → 迁移止损/止盈线 ✅

## 测试验证

### 测试场景

1. ✅ 正常订单流程（无需重试）
   - 挂单触发 → 订单成交 → 挂单线删除 → 入场线创建 → 止损/止盈线迁移

2. ✅ 订单重试场景
   - 挂单触发 → 订单超时撤销 → 重试订单成交 → 挂单线正确关联并删除 → 入场线创建 → 止损/止盈线迁移

3. ✅ 多次重试场景
   - 挂单触发 → 订单撤销1 → 重试1撤销 → 重试2撤销 → 重试3成交 → 挂单线正确关联

4. ✅ 手动撤销后手动重试
   - 挂单触发 → 手动撤销 → 手动重新下单（相同挂单线）→ 新订单正确关联

## 相关代码位置

- **主要修复**: `vnpy/chart/drawing_order.py`
  - `_find_unlinked_pending_line`: 第388-535行
  - `update_line_from_order`: 第791-803行（CANCELLED处理）
  - `update_line_from_order`: 第734-752行（强制查找中的检查）

## 注意事项

1. **性能考虑**: 在 `_find_unlinked_pending_line` 中，每次都要查询 `main_engine.get_all_orders()`。如果挂单线数量很多，可能会有性能影响。但由于挂单线通常不会太多（一般<10个），这个影响可以接受。

2. **状态一致性**: 修复依赖于 `main_engine` 中订单状态的准确性。确保订单状态更新及时，否则可能无法正确识别已撤销的订单。

3. **日志输出**: 修复中添加了详细的日志输出，便于问题排查和验证修复效果。

## 总结

通过增强 `_find_unlinked_pending_line` 方法，使其能够检测并清理已失效的订单映射关系，成功解决了订单重试后挂单线无法关联的问题。修复确保了：

- ✅ 重试订单能够正确关联到原始挂单线
- ✅ 挂单线在订单成交后正确删除
- ✅ 止损/止盈线正确迁移到入场线
- ✅ 持仓显示准确

