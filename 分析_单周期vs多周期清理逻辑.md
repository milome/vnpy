# 分析：单周期 vs 多周期清理逻辑

## 单周期

### `switch_chart()`（切换合约）

```python
def switch_chart(self):
    vt_symbol = self.symbol_line.text()
    
    if vt_symbol == self.current_vt_symbol:
        return  # 同一合约，不处理
    
    # 1. 保存新合约
    self.current_vt_symbol = vt_symbol
    self.history_loaded = False
    self.history_data = []
    
    # 2. 清理图表
    self.chart.clear_all()
    
    # 3. ✅ 重新创建 BarGenerator（合约改变）
    self.bg = BarGenerator(self.on_bar)
    
    # 4. 加载历史数据
    self.load_history_data(vt_symbol)
```

### `refresh_chart()`（重新加载数据）

```python
def refresh_chart(self):
    # 1. 重置状态
    self.history_loaded = False
    self.history_data = []
    
    # 2. 清理图表
    self.chart.clear_all()
    
    # 3. ❌ 没有重新创建 BarGenerator
    # self.bg 保持不变
    
    # 4. 加载历史数据
    self.load_history_data(self.current_vt_symbol)
```

**结论**：
- 单周期在 `refresh_chart()` 时**不清理 BarGenerator** ✅
- 只在切换合约时才重新创建 BarGenerator ✅
- 实时更新在数据加载期间仍然工作 ✅

## 多周期

### `switch_symbol()`（切换合约或重新加载）

**之前的逻辑**：
```python
def switch_symbol(self, vt_symbol, exchange, start, end):
    # 1. 更新合约信息
    self._vt_symbol = vt_symbol
    self._exchange = exchange
    
    # 2. ❌ 总是清理数据（包括 BarGenerator）
    self._cleanup_data()
        - 清理 BarManager
        - 清理 ChartItem
        - 清理 BarGenerator  # ❌ 问题！
        - _realtime_enabled = False  # ❌ 问题！
    
    # 3. 重新加载数据
    self._load_data_and_build_items()
    
    # 4. 如果之前启用过实时更新，重新初始化
    if self._realtime_enabled:  # ❌ 但已经被设为 False 了！
        self._reinitialize_bar_generators()
```

**问题**：
- `_cleanup_data()` 设置了 `_realtime_enabled = False`
- 所以第4步的条件判断永远为 `False`
- BarGenerator 永远不会被重新初始化（除非在数据加载后手动调用 `enable_realtime()`）

**现在的修复**：
```python
def switch_symbol(self, vt_symbol, exchange, start, end):
    # 1. 检查合约是否改变
    symbol_changed = (vt_symbol != self._vt_symbol or exchange != self._exchange)
    
    # 2. 清理数据
    self._cleanup_data(symbol_changed=symbol_changed)
        if symbol_changed:
            - 清理所有数据（包括 BarGenerator）  ✅
            - _realtime_enabled = False  ✅
        else:
            - 只清理历史数据  ✅
            - 保留 BarGenerator  ✅
            - 保留 _realtime_enabled  ✅
    
    # 3. 重新加载数据
    self._load_data_and_build_items()
    
    # 4. 如果之前启用过实时更新，重新初始化
    if self._realtime_enabled:  # ✅ 合约未变时仍为 True
        self._reinitialize_bar_generators()
```

## 对比总结

| 场景 | 单周期 | 多周期（修复前） | 多周期（修复后） |
|------|--------|----------------|----------------|
| **切换合约** | 重新创建 BG ✅ | 清理 BG ✅ | 清理 BG ✅ |
| **重新加载** | 保留 BG ✅ | 清理 BG ❌ | 保留 BG ✅ |
| **实时更新** | 持续工作 ✅ | 中断 ❌ | 持续工作 ✅ |

## 关键修复

### `_cleanup_data(symbol_changed)`

```python
def _cleanup_data(self, symbol_changed: bool = True):
    # 清理 BarManager 和 ChartItem（总是清理）
    self._main_manager.clear_all()
    ...
    
    # 只在合约改变时清理 BarGenerator
    if symbol_changed:
        self._bg_1m = None
        self._bg_5m = None
        self._bg_1h = None
        self._bg_4h = None
        self._realtime_enabled = False
```

### `switch_symbol()`

```python
def switch_symbol(self, vt_symbol, exchange, start, end):
    # 检查合约是否改变
    symbol_changed = (vt_symbol != self._vt_symbol or exchange != self._exchange)
    
    # 更新合约信息
    self._vt_symbol = vt_symbol
    self._exchange = exchange
    
    # 清理数据（传入 symbol_changed）
    self._cleanup_data(symbol_changed=symbol_changed)
    
    # 重新加载数据
    self._load_data_and_build_items()
    
    # 重新初始化 BarGenerator（如果启用过）
    if self._realtime_enabled:
        self._reinitialize_bar_generators()
```

修复完成！🎉

