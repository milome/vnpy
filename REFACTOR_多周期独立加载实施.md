# 重构：多周期独立加载实施

## 问题

多周期始终从FUTU下载数据，因为：
1. 多周期依赖单周期的 `sync_data_to_multi_timeframe()`
2. 单周期使用 DataManager 下载，传递的是 `start=2025-11-12 13:50:00`
3. 多周期没有调用 `_check_data_completeness()`，直接下载

## 修改内容

### 1. `refresh_chart()` - 根据模式选择加载方式

**修改前**：
```python
def refresh_chart(self):
    # 无论什么模式都加载历史数据到单周期图表
    self.load_history_data(self.current_vt_symbol)
```

**修改后**：
```python
def refresh_chart(self):
    if self.display_mode == "multi" and self.multi_timeframe_widget:
        # 多周期模式：独立加载
        self._load_multi_timeframe_data()
    else:
        # 单周期模式：使用原有逻辑
        self.load_history_data(self.current_vt_symbol)
```

### 2. 新增 `_load_multi_timeframe_data()` - 多周期独立加载

```python
def _load_multi_timeframe_data(self):
    """
    多周期模式下独立加载数据
    
    流程：
    1. 获取用户选择的时间范围（从UI控件）
    2. 调用 MultiTimeframeWidget.switch_symbol()
    3. MultiTimeframeWidget 内部会：
       a. 从数据库加载1分钟数据
       b. 调用 _check_data_completeness() 检查数据
       c. 如果需要，从FUTU下载
       d. 从1分钟聚合大周期
    """
    # 获取用户选择的时间
    user_start = self.start_date_edit.dateTime().toPython()
    end = datetime.now()
    
    # 调用 switch_symbol
    self.multi_timeframe_widget.switch_symbol(
        vt_symbol=symbol,
        exchange=exchange,
        start=user_start,
        end=end,
        progress_callback=...
    )
```

### 3. `sync_data_to_multi_timeframe()` - 改为提示

**修改前**：
```python
def sync_data_to_multi_timeframe(self):
    # 检查历史数据
    if not self.history_loaded or not self.history_data:
        return
    
    # 同步数据...
    self.multi_timeframe_widget.switch_symbol(...)
```

**修改后**：
```python
def sync_data_to_multi_timeframe(self):
    """已废弃，保留以兼容"""
    # 提示用户重新加载数据
    self.main_engine.write_log(
        "[多周期] 已切换到多周期模式，请选择起始时间后点击'加载'按钮",
        "ChartWindow"
    )
```

### 4. `process_history_data()` - 移除自动同步

**修改前**：
```python
def process_history_data(self, history):
    # ... 处理数据 ...
    
    # 如果当前是多周期模式，同步数据到多周期图表
    if self.display_mode == "multi" and self.multi_timeframe_widget:
        self.sync_data_to_multi_timeframe()
```

**修改后**：
```python
def process_history_data(self, history):
    # ... 处理数据 ...
    
    # 注意：不再自动同步数据到多周期模式
    # 多周期模式下的数据加载由 _load_multi_timeframe_data() 独立处理
```

### 5. `switch_contract()` - 移除自动同步

**修改前**：
```python
def switch_contract(self, vt_symbol):
    if self.display_mode == "multi" and self.multi_timeframe_widget:
        self.sync_data_to_multi_timeframe()
    else:
        self.load_history_data(vt_symbol)
```

**修改后**：
```python
def switch_contract(self, vt_symbol):
    # 注意：不再自动同步数据到多周期
    if self.display_mode != "multi":
        self.load_history_data(vt_symbol)
```

## 数据流

### 多周期模式

```
用户操作:
  1. 切换到"多周期叠加"
     → _switch_to_multi_timeframe_mode()
     → sync_data_to_multi_timeframe()
     → 提示: "请选择起始时间后点击'加载'按钮"
  
  2. 选择起始时间（例如 2025-11-12）
  
  3. 点击"加载"按钮
     → refresh_chart()
     → _load_multi_timeframe_data()
     → multi_timeframe_widget.switch_symbol(start=2025-11-12, end=now)
        ↓
     MultiTimeframeWidget._load_data_and_build_items():
        a. database.load_bar_data(start=2025-11-12, end=now)
        b. _check_data_completeness(existing_bars, 2025-11-12, now)
           → 检查数据库时间戳（带时区调试）
           → 判断是否需要下载
        c. 如需下载: _download_from_futu()
        d. 重新加载: database.load_bar_data(start=2025-11-12, end=now)
        e. 从1分钟聚合大周期
  
  4. 显示多周期图表
```

## 关键点

### ✅ 完全独立

- 多周期不依赖单周期数据
- 多周期有自己的时区检查和下载逻辑
- 1分钟数据严格按用户指定范围加载

### ✅ 时区调试生效

现在多周期会输出：
```
[时区调试] === 原始时间戳（转换前） ===
[时区调试] 数据库最早原始: ...
[时区调试] === 转换后时间戳 ===
...
```

### ✅ 避免重复下载

通过 `_check_data_completeness()` 的四大策略：
1. 数据库无数据 → 下载最近7天
2. 数据较旧 → 下载最近7天
3. 用户时间早 → 全量下载
4. 数据很新 → 跳过下载

重构完成！🎉

