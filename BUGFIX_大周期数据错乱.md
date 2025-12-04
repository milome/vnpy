# Bug修复：大周期数据从7天前开始错乱

## 问题

用户选择起始时间为 2025-11-03，但：
1. 大周期数据从 2025-11-27 开始（7天前）
2. 7天前的大周期数据全是乱的

## 根本原因

### 错误的时间范围使用

**多周期加载逻辑中**：

```python
# ❌ 错误：使用了优化后的时间（7天前）
optimized_start, need_download = _get_optimized_start_time(database)
# optimized_start = 2025-11-27（7天前）

# 加载1分钟数据
one_minute_bars = database.load_bar_data(..., optimized_start, end)
# ❌ 只加载了7天的数据

# 并行加载大周期
five_minute_bars = database.load_bar_data(..., self._start, self._end)
# ❌ self._start 和 self._end 是什么值？如果也被优化了，就会错乱
```

**问题**：
- 如果 `self._start` 被设置为优化后的时间（11-27）
- 但用户期望的是原始选择的时间（11-03）
- 导致大周期数据只有7天，其他数据是空的或错误的

## 修复方案

### 关键原则

**所有周期的数据加载都必须使用用户指定的完整时间范围！**

```python
# ✅ 正确：始终使用用户选择的时间
one_minute_bars = database.load_bar_data(
    start=self._start,  # 用户选择的起始时间（2025-11-03）
    end=self._end       # 用户选择的结束时间
)

# ✅ 大周期也使用相同范围
five_minute_bars = database.load_bar_data(
    start=self._start,  # 同样使用用户选择
    end=self._end
)
```

### 移除优化逻辑

**在多周期中不需要优化**：
- 下载优化已在单周期的 `load_history_data()` 中完成
- 多周期直接使用数据库中已有的数据
- 不需要再次判断和优化

```python
# ❌ 删除：多周期中的优化逻辑
optimized_start, need_download = _get_optimized_start_time(database)

# ✅ 改为：直接使用用户选择的时间
# 加载已经在单周期中完成，数据库中已有完整数据
```

## 修改内容

### MultiTimeframeWidget._load_data_and_build_items()

**修复1**：移除 `_get_optimized_start_time()` 调用

```python
# ❌ 删除
optimized_start, need_download = self._get_optimized_start_time(database)

# ✅ 直接使用 self._start
```

**修复2**：1分钟数据使用完整范围

```python
# ✅ 使用用户选择的完整范围
one_minute_bars = database.load_bar_data(
    start=self._start,  # 用户选择（2025-11-03）
    end=self._end
)
```

**修复3**：大周期数据使用完整范围

```python
# ✅ 并行加载时，使用完整范围
def load_interval_data(interval):
    bars = database.load_bar_data(
        start=self._start,  # 用户选择的完整范围
        end=self._end
    )
```

## 数据流说明

### 单周期 → 多周期的数据传递

```
用户选择: 2025-11-03 ~ 2025-12-04

单周期加载:
  1. database.load_bar_data(2025-11-03, 2025-12-04)
  2. 智能下载优化（只下载必要的部分）
  3. 数据库现在有: 2025-11-03 ~ 2025-12-04 的完整数据 ✅
  ↓
多周期同步:
  1. switch_symbol(start=2025-11-03, end=2025-12-04)
  2. 1m: database.load_bar_data(2025-11-03, 2025-12-04)
  3. 5m: database.load_bar_data(2025-11-03, 2025-12-04)
  4. 1H: database.load_bar_data(2025-11-03, 2025-12-04)
  5. 4H: database.load_bar_data(2025-11-03, 2025-12-04)
  ↓
结果: 所有周期都显示 2025-11-03 ~ 2025-12-04 的完整数据 ✅
```

## 为什么多周期不需要优化？

**原因**：

1. **下载已完成**：单周期加载时已经下载并保存到数据库
2. **数据库已全**：多周期只从数据库读取，不涉及 FUTU API
3. **读取很快**：数据库查询很快（< 1秒），不需要优化

**职责分工**：
- **单周期**：负责下载和优化（与 FUTU API 交互）
- **多周期**：只负责加载和显示（从数据库读取）

## 测试验证

**测试场景**：

1. 选择起始时间：2025-11-03
2. 点击"加载"按钮
3. 切换到多周期模式

**预期结果**：

- ✅ 所有周期（1m/5m/1H/4H）都显示从 2025-11-03 开始的数据
- ✅ 数据对齐正确
- ✅ 没有错乱的数据
- ✅ 时间滑块显示 11-03 ~ 12-04

修复已完成！现在大周期数据应该正确显示用户选择的完整时间范围了。🎉

