# Bug修复：多周期实时K线不显示

## 问题

切换到多周期模式后，不显示实时K线。

## 根本原因

**调用时序问题**：

```
用户操作:
  1. 切换到"多周期叠加"
     → _switch_to_multi_timeframe_mode()
     → enable_realtime()  # ❌ 此时还没有数据！
     → BarGenerator 初始化，但 _manager_5m/1h/4h 可能为 None
  
  2. 选择时间，点击"加载"
     → _load_multi_timeframe_data()
     → switch_symbol()
     → _load_data_and_build_items()
     → 创建 _manager_5m/1h/4h
     → 数据加载完成
     → ❌ 没有再次调用 enable_realtime()！
  
  3. 收到tick数据
     → process_tick_event()
     → multi_timeframe_widget.update_tick()
     → ❌ _bg_1m 等可能未正确初始化
```

## 修复方案

**在数据加载完成后启用实时更新**

```python
def load_data():
    try:
        # 1. 加载数据
        self.multi_timeframe_widget.switch_symbol(...)
        
        # 2. 关闭进度条
        progress.close()
        
        # 3. ✅ 启用实时更新（关键！）
        if hasattr(self.multi_timeframe_widget, 'enable_realtime'):
            self.multi_timeframe_widget.enable_realtime()
            self.main_engine.write_log("[多周期加载] 实时更新已启用")
```

## 数据流

### ✅ 修复后

```
用户操作:
  1. 切换到"多周期叠加"
     → _switch_to_multi_timeframe_mode()
     → (可能调用 enable_realtime()，但没有数据)
  
  2. 选择时间，点击"加载"
     → _load_multi_timeframe_data()
     → switch_symbol()
        a. _cleanup_data()（清理旧数据和 BarGenerator）
        b. _load_data_and_build_items()（创建 manager）
        c. _reinitialize_bar_generators()（如果之前启用过实时更新）
     → ✅ enable_realtime()（数据加载后再次启用）
        - 创建 _bg_1m, _bg_5m, _bg_1h, _bg_4h
        - _realtime_enabled = True
  
  3. 收到tick数据
     → process_tick_event()
     → multi_timeframe_widget.update_tick(tick)
     → _bg_1m.update_tick(tick)
     → ✅ 实时K线更新！
```

## 关键点

### ✅ 数据加载后启用

- `enable_realtime()` 需要在数据加载完成后调用
- 此时 `_manager_5m/1h/4h` 已经创建
- BarGenerator 可以正确初始化

### ✅ switch_symbol() 的内部逻辑

`switch_symbol()` 内部会调用 `_reinitialize_bar_generators()`（如果之前启用过实时更新）：

```python
def switch_symbol(...):
    self._cleanup_data()  # 清理 BarGenerator
    self._load_data_and_build_items()  # 创建 manager
    
    # 如果之前启用过实时更新，重新初始化
    if self._realtime_enabled:
        self._reinitialize_bar_generators()
```

但是，在新安装或首次加载时，`_realtime_enabled` 为 `False`，所以不会调用 `_reinitialize_bar_generators()`。

### ✅ 解决方案

在数据加载完成后，无论 `_realtime_enabled` 之前是什么状态，都调用 `enable_realtime()`。

## 测试验证

### 测试步骤

```
1. 切换到"多周期叠加"
2. 选择起始时间
3. 点击"加载"
4. 观察日志
5. 等待实时tick数据
```

### 预期日志

```
[多周期加载] 数据加载完成
[多周期加载] 实时更新已启用  # ✅ 新增
[多周期] 实时更新功能已启用  # ✅ 来自 enable_realtime()
```

### 预期行为

- ✅ 实时K线在图表上更新
- ✅ 1分钟、5分钟、1小时、4小时K线都实时更新

修复完成！🎉

