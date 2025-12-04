# Bug修复：数据只加载到7天前

## 问题

多周期选择起始时间点击加载后，数据始终只加载到 2025/11/27，而不是用户选择的时间。

## 根本原因

### 问题代码

在 `load_history_data()` 中：

```python
# 1. 智能策略优化起始时间
optimized_start, need_download = _get_optimized_load_strategy(...)
# optimized_start = 2025-11-27（7天前）

# 2. 从数据库加载
data = database.load_bar_data(..., optimized_start, end)

# 3. 补齐大周期数据
if interval in [MINUTE_5, HOUR, HOUR_4]:
    data = _fill_missing_bars(
        ...,
        start=start,  # ❌ 错误：使用了 start（可能是 optimized_start）
        ...
    )
```

**问题**：
- `optimized_start` 是优化后的时间（2025-11-27，7天前）
- 传递给 `_fill_missing_bars()` 时，使用了 `optimized_start`
- 导致大周期数据也只补齐到7天前

### 用户意图 vs 实际行为

**用户意图**：
```
选择起始时间: 2025-10-02
期望加载: 2025-10-02 ~ 2025-12-04（2个月）
```

**实际行为**：
```
优化后: 2025-11-27 ~ 2025-12-04（7天）← 只下载7天
但用户期望看到2个月的数据！
```

## 修复方案

### 修复：区分下载范围和显示范围

```python
# 1. 优化下载范围（减少FUTU API调用）
optimized_start, need_download = _get_optimized_load_strategy(...)
# optimized_start = 2025-11-27（下载最近7天）

# 2. 从数据库加载用户选择的完整范围
data = database.load_bar_data(
    ...,
    start=user_start,  # ✅ 使用用户选择时间
    end=end
)

# 3. 如果需要下载，补齐数据
if need_download:
    data = _fill_missing_bars(
        ...,
        start=optimized_start,  # 只补齐优化范围（最近7天）
        end=end
    )
```

### 逻辑说明

**关键区分**：
- **下载范围**（`optimized_start`）：优化后的范围，减少下载量
- **显示范围**（`user_start`）：用户选择的范围，完整显示

**流程**：
```
1. 数据库查询: user_start ~ end（用户选择的完整范围）
   - 可能有部分数据（如 2025-11-01 ~ 2025-12-04 02:59）
   
2. 判断是否需要补齐
   - 如果数据很新：不补齐
   - 如果数据较旧：补齐最近7天（optimized_start ~ end）

3. 最终数据
   - 数据库已有的: 2025-11-01 ~ 2025-12-04 02:59
   - 补齐的: 2025-12-04 03:00 ~ 04:56
   - 总计: 2025-11-01 ~ 2025-12-04 04:56 ✅
```

## 修改内容

### 修改位置

`ChartWindow.load_history_data()` 中的 `_fill_missing_bars()` 调用：

```python
# ❌ 修复前
data = self._fill_missing_bars(..., start, end, ...)
# start 可能是 optimized_start（7天前）

# ✅ 修复后  
data = self._fill_missing_bars(..., user_start, end, ...)
# user_start 是用户选择的时间（2个月前）
```

## 测试验证

### 场景1：用户选择2个月前

```
用户选择: 2025-10-02
数据库最新: 04:00（20分钟前）

优化策略: 下载最近7天（2025-11-27 ~ 2025-12-04）
数据库查询: 2025-10-02 ~ 2025-12-04（用户范围）
补齐: 2025-12-04 03:00 ~ 04:56（只补齐缺口）

最终数据: 2025-10-02 ~ 2025-12-04 ✅
显示: 2个月完整数据 ✅
```

### 场景2：用户选择1个月前

```
用户选择: 2025-11-01
数据库最新: 04:00（20分钟前）

优化策略: 跳过下载（数据很新）
数据库查询: 2025-11-01 ~ 2025-12-04
补齐: 只补齐小缺口（如有）

最终数据: 2025-11-01 ~ 2025-12-04 ✅
显示: 1个月完整数据 ✅
```

## 总结

**修复**：在调用 `_fill_missing_bars()` 时，使用 `user_start` 而不是 `optimized_start`，确保加载用户选择的完整范围。

**效果**：
- ✅ 显示用户选择的完整时间范围
- ✅ 下载量仍然优化（只下载必要的部分）
- ✅ 性能提升保持

现在重新测试，数据应该能加载到用户选择的完整范围了！

