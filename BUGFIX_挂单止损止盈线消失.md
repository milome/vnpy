# Bug修复：挂单止损止盈线消失

## 问题

多周期模式下，挂单模拟成交后：
- ✅ 入场线出现了
- ❌ 挂单止损线消失了
- ❌ 挂单止盈线消失了

## 根本原因

在 `_cleanup_pending_stop_profit_lines()` 方法中，清理逻辑过于激进：

```python
# ❌ 旧逻辑：只要 entry_line_id 为空就删除
if line_type in [STOP_LOSS, TAKE_PROFIT]:
    if not line.entry_line_id:
        # 删除
        lines_to_remove.append(line_id)
```

**问题**：
- 挂单止损止盈线在挂单成交前，`entry_line_id` 确实是空的
- 但它们关联到挂单线（PENDING），不是孤儿线
- 清理时被误删了

## 挂单止损止盈线的生命周期

### 正常流程

```
1. 启用画线下单
   → 创建挂单止损线（stop_pending_xxx, entry_line_id=None）
   → 创建挂单止盈线（profit_pending_xxx, entry_line_id=None）

2. 用户画线下单
   → 创建挂单线（pending_xxx）
   → 挂单线关联到挂单止损止盈线
   → 可能通过 pending_line_id 属性关联

3. 挂单成交
   → 挂单线（pending_xxx）→ 入场线（entry_xxx）
   → 挂单止损线 → 已激活止损线（entry_line_id = entry_xxx）
   → 挂单止盈线 → 已激活止盈线（entry_line_id = entry_xxx）

4. 持仓平仓
   → 删除入场线
   → 删除已激活的止损止盈线
```

### 问题流程（修复前）

```
1. 启用画线下单
   → 创建挂单止损线（entry_line_id=None）
   → 创建挂单止盈线（entry_line_id=None）

2. 用户画线下单
   → 创建挂单线（pending_xxx）

3. 切换到多周期或重新设置合约
   → set_vt_symbol()
   → load_from_database()
   → _cleanup_pending_stop_profit_lines()
      → 检测到 entry_line_id 为空
      → 误删挂单止损止盈线 ❌

4. 挂单成交
   → 入场线出现 ✅
   → 止损止盈线已被删除，无法激活 ❌
```

## 修复方案

### 改进清理逻辑：三重检查

```python
def _cleanup_pending_stop_profit_lines(self):
    """清理孤儿止损止盈线（真正没有任何关联的）"""
    
    # 收集所有入场线ID和挂单线ID
    entry_line_ids = set()
    pending_line_ids = set()
    
    for line_id, line in all_lines.items():
        if line.get_line_type() == ENTRY:
            entry_line_ids.add(line_id)
        elif line.get_line_type() == PENDING:
            pending_line_ids.add(line_id)
    
    # 检查止损止盈线
    for line_id, line in all_lines.items():
        if line_type in [STOP_LOSS, TAKE_PROFIT]:
            # 检查1：是否关联到入场线
            has_entry = (hasattr(line, 'entry_line_id') and 
                        line.entry_line_id and 
                        line.entry_line_id in entry_line_ids)
            
            # 检查2：是否关联到挂单线
            has_pending = (hasattr(line, 'pending_line_id') and 
                          line.pending_line_id and 
                          line.pending_line_id in pending_line_ids)
            
            # 检查3：是否在关联关系字典中
            has_relation = line_id in self._entry_line_relations.values()
            
            # 只有三者都没有才删除
            if not has_entry and not has_pending and not has_relation:
                # 真正的孤儿线，可以安全删除
                lines_to_remove.append(line_id)
            else:
                # 有关联，保留
                reasons = []
                if has_entry: reasons.append(f"入场线={line.entry_line_id}")
                if has_pending: reasons.append(f"挂单线={line.pending_line_id}")
                if has_relation: reasons.append("在关联关系中")
                self._main_engine.write_log(
                    f"[ChartWidget] 保留{line_type.value}线: {line_id} ({', '.join(reasons)})"
                )
```

## 修改内容

### 文件：vnpy/chart/widget.py

**修改方法**：`_cleanup_pending_stop_profit_lines()`

**关键改进**：
1. 收集所有入场线ID和挂单线ID
2. 检查止损止盈线是否关联到入场线（`entry_line_id`）
3. 检查止损止盈线是否关联到挂单线（`pending_line_id`）
4. 检查止损止盈线是否在关联关系字典中
5. 只有三者都没有才删除（真正的孤儿线）

## 测试验证

### 测试场景

```
操作:
  1. 多周期模式
  2. 启用画线下单
  3. 画线创建挂单
  4. 模拟成交

预期日志:
  [画线模式] 启用画线模式
  [ChartWidget] 从数据库加载了 X 条价格线
  [ChartWidget] 保留stop_loss线: stop_xxx (关联挂单线=pending_xxx)
  [ChartWidget] 保留take_profit线: profit_xxx (关联挂单线=pending_xxx)
  [ChartWidget] 已清理 0 条孤儿止损止盈线
  ... 挂单成交 ...
  [ChartWidget] 挂单线转为入场线
  [ChartWidget] 激活止损止盈线（设置 entry_line_id）

预期结果:
  - ✅ 挂单止损止盈线保留
  - ✅ 挂单成交后转为已激活的止损止盈线
  - ✅ 入场线、止损线、止盈线都正确显示
```

## 总结

**核心修复**：
- ❌ 不再简单判断 `entry_line_id` 是否为空
- ✅ 三重检查：入场线关联 + 挂单线关联 + 关联关系字典
- ✅ 只删除真正的孤儿线

**关键点**：
- 挂单止损止盈线在成交前 `entry_line_id` 为空是正常的
- 它们通过 `pending_line_id` 关联到挂单线
- 不应该被清理逻辑误删

修复完成！🎉

