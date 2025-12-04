# Bug完整修复：挂单止损止盈线问题

## 问题回顾

多周期模式下，刚开启画线下单功能，还没有画线，就自动显示了挂单止损线和挂单止盈线。

## 问题分析

### 修复1：切换模式时不同步挂单线 ✅

**已完成**：在 `_switch_to_multi_timeframe_mode()` 中过滤挂单线

```
日志显示：
[ChartWindow] 跳过未激活的stop_loss线: stop_51d15a790e5f (挂单线，未关联入场线)
[ChartWindow] 跳过未激活的take_profit线: profit_61df3a727e51 (挂单线，未关联入场线)
[ChartWindow] 已同步 0 条价格线到多周期图表（过滤了挂单止损止盈线）
```

**结果**：切换模式时的同步逻辑工作正常 ✅

### 修复2：启用画线下单时从数据库加载了旧挂单线 ❌

**问题**：启用画线下单时，`ChartWidget.set_vt_symbol()` 调用了 `load_from_database()`，加载了旧的挂单线

```
日志显示：
[画线模式] 启用画线模式
[ChartWidget] 从数据库加载了 2 条价格线  # ❌ 这里加载了旧的挂单线
```

**原因**：
- 之前使用画线下单功能时，挂单止损止盈线被保存到数据库
- 启用画线下单时，`load_from_database()` 加载了所有价格线，包括挂单线
- 这些挂单线显示在图表上

## 完整修复方案

### 修复点1：切换模式时过滤挂单线（已完成）

在 `_switch_to_multi_timeframe_mode()` 中只同步已激活的价格线。

### 修复点2：从数据库加载后清理挂单线（新增）

在 `ChartWidget.set_vt_symbol()` 中，`load_from_database()` 后立即清理未关联的挂单止损止盈线。

```python
# 从数据库加载价格线
count = self._price_line_manager.load_from_database(self._first_plot)

# ✅ 新增：清理未关联的挂单止损止盈线
self._cleanup_pending_stop_profit_lines()

# 加载关联关系
self._load_line_relations()
```

## 新增方法

### `_cleanup_pending_stop_profit_lines()`

```python
def _cleanup_pending_stop_profit_lines(self) -> None:
    """
    清理未关联到入场线的挂单止损止盈线
    
    这些线是之前画线下单时创建的，但不应该在加载数据时自动显示。
    用户启用画线下单功能时，会重新创建这些线。
    """
    from vnpy.chart.price_line import PriceLineType
    
    all_lines = self._price_line_manager.get_all_lines()
    lines_to_remove = []
    
    for line_id, line in all_lines.items():
        line_type = line.get_line_type()
        
        # 只清理未关联到入场线的止损止盈线
        if line_type in [PriceLineType.STOP_LOSS, PriceLineType.TAKE_PROFIT]:
            if not hasattr(line, 'entry_line_id') or not line.entry_line_id:
                # 这是挂单线，清理
                lines_to_remove.append(line_id)
                self._main_engine.write_log(
                    f"[ChartWidget] 清理未关联的{line_type.value}线: {line_id}（挂单线，不应自动加载）"
                )
    
    # 删除这些线
    for line_id in lines_to_remove:
        line = self._price_line_manager.get_line(line_id)
        if line:
            # 从 plot 移除
            if self._first_plot:
                self._first_plot.removeItem(line)
            # 从管理器删除
            self._price_line_manager.delete_line(line_id)
            # 从数据库删除
            if self._price_line_database:
                self._price_line_database.delete_line(line_id)
```

## 修改内容

### 文件：vnpy/chart/widget.py

**修改位置1**：`set_vt_symbol()` 方法（第401-410行）

```python
# 从数据库加载价格线
count = self._price_line_manager.load_from_database(self._first_plot)
if count > 0:
    self._main_engine.write_log(f"[ChartWidget] 从数据库加载了 {count} 条价格线")

# ✅ 新增：清理未关联的挂单止损止盈线
self._cleanup_pending_stop_profit_lines()

# 加载关联关系
self._load_line_relations()
```

**修改位置2**：新增 `_cleanup_pending_stop_profit_lines()` 方法（第410行后）

## 数据流

### ❌ 修复前

```
启用画线下单:
  → 切换到多周期模式
  → ChartWidget.set_vt_symbol(...)
  → load_from_database()
     - 加载所有价格线（包括旧的挂单线）❌
  ↓
结果: 显示旧的挂单止损止盈线 ❌
```

### ✅ 修复后

```
启用画线下单:
  → 切换到多周期模式
  → ChartWidget.set_vt_symbol(...)
  → load_from_database()
     - 加载所有价格线（包括旧的挂单线）
  → _cleanup_pending_stop_profit_lines()  # ✅ 新增
     - 清理未关联的挂单止损止盈线
     - 从 plot、管理器、数据库中全部删除
  ↓
结果: 只显示已激活的价格线（入场线 + 关联的止损止盈线）✅
```

## 挂单线的生命周期

### 正常流程

```
1. 启用画线下单
   → DrawingOrderController.enable()
   → 自动创建挂单止损止盈线
   → 用户可以拖动设置价格

2. 用户画线下单
   → 创建挂单线（PENDING）
   → 挂单线关联到挂单止损止盈线

3. 挂单成交
   → 挂单线变成入场线（ENTRY）
   → 挂单止损止盈线激活（设置 entry_line_id）

4. 禁用画线下单
   → DrawingOrderController.disable()
   → 删除未激活的挂单止损止盈线 ✅
```

### 问题流程（修复前）

```
1. 启用画线下单
   → 创建挂单止损止盈线
   → 保存到数据库

2. 禁用画线下单
   → 删除挂单线（从内存和plot）
   → 但数据库中仍然保留 ❌

3. 下次启用画线下单
   → load_from_database()
   → 加载旧的挂单线 ❌
   → 显示在图表上 ❌
```

## 测试验证

### 测试场景

```
操作:
  1. 多周期模式
  2. 启用画线下单
  3. 观察图表

预期日志:
  [画线模式] 启用画线模式
  [ChartWidget] 从数据库加载了 2 条价格线
  [ChartWidget] 清理未关联的stop_loss线: stop_xxx（挂单线，不应自动加载）
  [ChartWidget] 清理未关联的take_profit线: profit_xxx（挂单线，不应自动加载）
  [ChartWidget] 已清理 2 条未关联的挂单止损止盈线
  [画线模式] 画线模式已启用

预期结果:
  - ✅ 图表上干净，没有旧的挂单线
  - ✅ DrawingOrderController 会重新创建新的挂单线（如果需要）
```

## 总结

**两阶段修复**：
1. ✅ 切换模式时不同步挂单线
2. ✅ 加载数据后清理旧的挂单线

**关键点**：
- 挂单止损止盈线不应该持久化或自动加载
- 这些线是临时的UI辅助线
- 每次启用画线下单时应该重新创建

**完整修复**！🎉

