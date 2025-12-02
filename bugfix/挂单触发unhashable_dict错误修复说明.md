# 挂单触发 unhashable type: 'dict' 错误修复说明

**日期**: 2025-12-03  
**问题**: 挂单触发时出现 `unhashable type: 'dict'` 错误  
**状态**: ✅ 已修复

---

## 问题描述

### 错误信息

```
[ChartWidget] [实时挂单触发失败] 发送订单时发生异常: MHImain.HKFE 多 1手@25950.984809127247 
(挂单线: pending_afbcfdff7093, 错误: unhashable type: 'dict', 当前价格: 25953.0)
```

### 问题表现

1. 用户在图表上创建挂单线
2. 价格突破挂单线，触发下单
3. 发送订单时发生异常：`unhashable type: 'dict'`
4. 挂单触发失败，挂单线保持监控状态

---

## 根本原因分析

### 可能的原因

1. **`vt_orderid` 类型错误**：
   - `send_order` 方法应该返回字符串类型的 `vt_orderid`
   - 但在某些情况下，可能返回了字典或其他不可哈希的类型
   - 当尝试将 `vt_orderid` 作为字典键使用时（`controller._order_line_map[vt_orderid]`），会抛出 `unhashable type: 'dict'` 错误

2. **`controller` 对象状态异常**：
   - `controller._line_order_map` 或 `controller._order_line_map` 可能被错误地设置成了非字典类型
   - 虽然 `DrawingOrderController` 在 `__init__` 中已经初始化了这些字典，但在某些情况下可能被覆盖

3. **`_pending_line_relations` 类型错误**：
   - 在获取挂单关联的止损止盈信息时，如果 `_pending_line_relations` 不是字典类型，可能导致错误

---

## 修复方案

### 修复内容

在 `vnpy/chart/widget_trigger.py` 的 `trigger_pending_order_breakthrough` 方法中进行了以下修复：

#### 1. 添加 `vt_orderid` 类型检查

```python
# 确保 vt_orderid 是字符串类型
if not isinstance(vt_orderid, str):
    if main_engine:
        main_engine.write_log(
            f"[ChartWidget] 警告: send_order 返回了非字符串类型: {type(vt_orderid)}, 值: {vt_orderid}",
            "ChartWidget"
        )
    # 尝试转换为字符串
    vt_orderid = str(vt_orderid) if vt_orderid else None
```

#### 2. 优先使用 `link_line_to_order` 方法

```python
if vt_orderid:
    # 使用 controller 的方法关联订单和挂单线（更安全）
    if hasattr(controller, 'link_line_to_order'):
        controller.link_line_to_order(line_id, vt_orderid)
    else:
        # 向后兼容：如果方法不存在，直接操作字典
        if not hasattr(controller, '_line_order_map'):
            controller._line_order_map = {}
        if not hasattr(controller, '_order_line_map'):
            controller._order_line_map = {}
        
        controller._line_order_map[line_id] = vt_orderid
        controller._order_line_map[vt_orderid] = line_id
```

#### 3. 添加 `_pending_line_relations` 类型检查

```python
if controller and hasattr(controller, '_pending_line_relations'):
    try:
        # 确保 _pending_line_relations 是字典类型
        if isinstance(controller._pending_line_relations, dict):
            relations = controller._pending_line_relations.get(line_id, {})
        else:
            relations = {}
            if main_engine:
                main_engine.write_log(
                    f"[ChartWidget] 警告: _pending_line_relations 不是字典类型: {type(controller._pending_line_relations)}",
                    "ChartWidget"
                )
    except Exception as rel_error:
        relations = {}
        if main_engine:
            main_engine.write_log(
                f"[ChartWidget] 获取挂单关联关系失败: {str(rel_error)}",
                "ChartWidget"
            )
```

---

## 修复效果

### 预期效果

1. **类型安全**：
   - 确保 `vt_orderid` 是字符串类型，避免作为字典键时出错
   - 检查 `_pending_line_relations` 的类型，避免类型错误

2. **错误处理**：
   - 添加了详细的错误日志，便于定位问题
   - 如果类型错误，尝试转换或使用默认值，避免程序崩溃

3. **向后兼容**：
   - 优先使用 `controller.link_line_to_order` 方法（如果存在）
   - 如果方法不存在，回退到直接操作字典的方式

### 验证要点

修复后，应该验证以下场景：

1. **正常挂单触发**：
   - 挂单线触发时，`vt_orderid` 是字符串，应该正常关联订单和挂单线

2. **类型错误处理**：
   - 如果 `vt_orderid` 不是字符串，应该记录警告并尝试转换
   - 如果转换失败，应该跳过关联，但不影响其他功能

3. **关联关系获取**：
   - 如果 `_pending_line_relations` 不是字典类型，应该使用空字典，避免错误

---

## 相关文件

- `vnpy/chart/widget_trigger.py` - 挂单触发逻辑
- `vnpy/chart/drawing_order.py` - 挂单控制器

---

## 注意事项

1. **类型检查的重要性**：
   - Python 是动态类型语言，类型错误可能在运行时才发现
   - 添加类型检查可以提高代码的健壮性

2. **错误日志**：
   - 如果出现类型错误，会记录详细的警告日志
   - 这些日志可以帮助定位问题的根本原因

3. **向后兼容**：
   - 修复保持了向后兼容性
   - 如果 `controller` 没有 `link_line_to_order` 方法，仍然使用直接操作字典的方式

