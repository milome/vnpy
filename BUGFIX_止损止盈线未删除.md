# Bug修复：止损止盈线未删除

## 问题

模拟止盈后，平仓成功：
- ✅ 入场线被删除
- ❌ 止损线和止盈线仍然显示

## 日志分析

```
[持仓同步] 标记删除入场线: entry_recovered_c377ded5
[持仓同步] 已从plot中移除入场线: entry_recovered_c377ded5
[持仓同步] 已删除入场线: entry_recovered_c377ded5
[持仓同步] 持仓为0，已删除 1 条long方向的价格线（包括入场线及关联的止损/止盈线，共找到 1 条入场线）
```

**关键问题**：
- 日志说"包括入场线及关联的止损/止盈线"
- 但没有看到"已删除关联止损线"和"已删除关联止盈线"的日志
- 说明代码没有找到关联关系

## 根本原因

### 入场线 `entry_recovered_c377ded5` 是恢复的入场线

**恢复入场线的特点**：
- ID 前缀：`entry_recovered_`
- 来源：从数据库或持仓信息恢复
- 可能情况：恢复时没有加载关联关系到内存

### 代码检查

```python
# widget_position.py 第358-413行
if hasattr(self, '_entry_line_relations') and line_id in self._entry_line_relations:
    # ❌ 问题：entry_recovered_c377ded5 不在 _entry_line_relations 中
    relations = self._entry_line_relations[line_id]
    
    # 删除止损线
    stop_loss_line_id = relations.get("stop_loss")
    # ... 删除逻辑 ...
    
    # 删除止盈线
    take_profit_line_id = relations.get("take_profit")
    # ... 删除逻辑 ...
else:
    # ❌ 问题：没有 else 分支处理"找不到关联关系"的情况
    # 导致止损止盈线没有被删除
```

## 修复方案

### 方案1：从数据库查找关联关系（推荐）

```python
# 删除关联的止损线和止盈线
relations = None

# 1. 优先从内存查找
if hasattr(self, '_entry_line_relations') and line_id in self._entry_line_relations:
    relations = self._entry_line_relations[line_id]

# 2. 如果内存中没有，从数据库查找（针对恢复的入场线）
if not relations and self._price_line_database:
    db_relations = self._price_line_database.get_related_lines(line_id)
    if db_relations:
        relations = db_relations
        self._main_engine.write_log(
            f"[持仓同步] 从数据库找到关联关系: {db_relations}"
        )

# 3. 使用找到的关联关系删除止损止盈线
if relations:
    # 删除止损线
    stop_loss_line_id = relations.get("stop_loss")
    if stop_loss_line_id:
        # ... 删除逻辑 ...
    
    # 删除止盈线
    take_profit_line_id = relations.get("take_profit")
    if take_profit_line_id:
        # ... 删除逻辑 ...
```

### 方案2：通过线的属性查找（备用）

```python
# 如果数据库也没有关联关系，通过止损止盈线的属性查找
all_lines = self._price_line_manager.get_all_lines()

for other_line_id, other_line in all_lines.items():
    # 检查是否有 entry_line_id 属性指向当前入场线
    if hasattr(other_line, 'entry_line_id'):
        if other_line.entry_line_id == line_id:
            # 找到关联的止损或止盈线
            self._price_line_manager.delete_line(other_line_id)
```

## 修改内容

### 文件：vnpy/chart/widget_position.py

**修改位置**：第358-413行

```python
# ✅ 修改后：支持从数据库查找关联关系
# 删除关联的止损线和止盈线
# 方法1：从 _entry_line_relations 查找关联关系
relations_found = False
if hasattr(self, '_entry_line_relations') and line_id in self._entry_line_relations:
    relations = self._entry_line_relations[line_id]
    relations_found = True
    
    # ... 删除止损线和止盈线 ...

# 方法2：如果没有找到关联关系（例如恢复的入场线），从数据库查找
if not relations_found and self._price_line_database:
    self._main_engine.write_log(
        f"[持仓同步] 入场线 {line_id} 在内存中没有关联关系，尝试从数据库查找"
    )
    
    db_relations = self._price_line_database.get_related_lines(line_id)
    if db_relations:
        self._main_engine.write_log(
            f"[持仓同步] 从数据库找到关联关系: {db_relations}"
        )
        
        # 删除止损线
        stop_loss_line_id = db_relations.get("stop_loss")
        if stop_loss_line_id:
            # ... 删除逻辑（同方法1）...
        
        # 删除止盈线
        take_profit_line_id = db_relations.get("take_profit")
        if take_profit_line_id:
            # ... 删除逻辑（同方法1）...
        
        # 从数据库删除关联关系
        self._price_line_database.delete_relation(line_id)
```

## 为什么恢复的入场线会有这个问题？

### 恢复入场线的流程

```
持仓恢复:
  1. 从数据库加载入场线（entry_recovered_xxx）
  2. 从数据库加载止损线（stop_xxx）
  3. 从数据库加载止盈线（profit_xxx）
  4. 从数据库加载关联关系（entry -> stop, entry -> profit）
  ↓
问题: 关联关系只保存在数据库中，没有加载到内存的 _entry_line_relations
  ↓
结果: 删除入场线时，内存中找不到关联关系，止损止盈线没有被删除
```

### 修复后的流程

```
删除入场线:
  1. 先从内存的 _entry_line_relations 查找
  2. 如果没找到，从数据库的 get_related_lines() 查找 ✅
  3. 删除所有关联的止损止盈线 ✅
  4. 从数据库删除关联关系 ✅
```

## 测试验证

### 测试场景

```
操作:
  1. 模拟成交（创建入场线、止损线、止盈线）
  2. 重启应用（触发持仓恢复）
  3. 模拟止盈（平仓）

预期结果:
  - ✅ 入场线被删除
  - ✅ 止损线被删除
  - ✅ 止盈线被删除

预期日志:
  [持仓同步] 标记删除入场线: entry_recovered_xxx
  [持仓同步] 入场线在内存中没有关联关系，尝试从数据库查找
  [持仓同步] 从数据库找到关联关系: {'stop_loss': 'stop_xxx', 'take_profit': 'profit_xxx'}
  [持仓同步] 已删除关联止损线（从数据库找到）: stop_xxx
  [持仓同步] 已删除关联止盈线（从数据库找到）: profit_xxx
  [持仓同步] 已删除入场线: entry_recovered_xxx
```

## 总结

**核心修复**：
- ✅ 支持从数据库查找关联关系
- ✅ 针对恢复的入场线的特殊处理
- ✅ 确保止损止盈线被正确删除

**关键点**：
- 恢复的入场线可能没有内存中的关联关系
- 需要从数据库补充查找
- 删除逻辑需要两条路径：内存 + 数据库

修复完成！🎉

