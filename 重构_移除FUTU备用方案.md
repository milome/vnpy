# 重构：移除 FUTU Gateway 备用方案

## 原因

**DRY 原则**（Don't Repeat Yourself）：
- DataManager 本身就封装了 FUTU API 的下载逻辑
- 如果 DataManager 下载失败，直接调用 FUTU Gateway 也不会成功
- 备用方案是重复造轮子，增加维护成本

## 修改内容

### 文件：vnpy/chart/multi_timeframe_widget.py

#### 修改1：`_download_from_futu()` 方法

**修改前**：
```python
# 方案1：优先使用 DataManager
if datamanager_engine and hasattr(...):
    success = datamanager_engine.download_bar_data(...)
    if success:
        return bars
    else:
        return None

# 方案2：直接使用 FUTU Gateway（备用方案）
futu_gateway = ...
bars = futu_gateway.query_history(req)
return bars
```

**修改后**：
```python
# 使用 DataManager（DRY原则，不重复造轮子）
if not datamanager_engine:
    return None

success = datamanager_engine.download_bar_data(...)
if success:
    return bars
else:
    return None

# 不再有备用方案
```

#### 修改2：`_download_minute_bars_from_futu()` 方法

**同样的修改**：移除 FUTU Gateway 备用方案，只使用 DataManager

## 优势

### ✅ 代码更简洁

- 减少约 60 行代码
- 逻辑更清晰
- 易于维护

### ✅ 遵循 DRY 原则

- 不重复实现下载逻辑
- 只依赖 DataManager
- 如果需要修改下载逻辑，只需要修改 DataManager

### ✅ 错误处理更统一

- 如果 DataManager 不可用 → 返回 None
- 如果 DataManager 下载失败 → 返回 None
- 不再有两层错误处理

## 下载流程

### `_download_from_futu()` 方法
```
请求下载:
  ↓
检查 MainEngine → 无 → 返回 None
  ↓
获取 DataManager → 无 → 返回 None
  ↓
调用 DataManager.download_bar_data()
  ↓
成功: 从数据库重新加载并返回
失败: 返回 None
```

### `_download_minute_bars_from_futu()` 方法
```
请求下载:
  ↓
检查 MainEngine → 无 → 返回 None
  ↓
获取 DataManager → 无 → 返回 None
  ↓
调用 DataManager.download_history_data()
  ↓
从数据库重新加载并返回
```

**简单直接！** ✅

## 总结

**核心原则**：
- ✅ 只使用 DataManager 下载数据
- ✅ 不直接调用 FUTU Gateway
- ✅ 如果 DataManager 失败，说明 FUTU API 不可用，无需重试

**代码行数减少**：
- `_download_from_futu()`：减少约 35 行
- `_download_minute_bars_from_futu()`：减少约 75 行
- **总计减少约 110 行代码**

**维护性提升**：只需维护 DataManager 的下载逻辑

**代码质量提升**：
- ✅ 遵循 DRY 原则
- ✅ 单一职责：只使用 DataManager
- ✅ 错误处理更简洁
- ✅ 无重复逻辑

重构完成！🎉

