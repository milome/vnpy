# 对比：单周期 vs 多周期实时K线更新

## 单周期实时K线更新逻辑

### `process_tick_event()` - 1分钟周期

```python
if interval_enum == Interval.MINUTE:
    if self.bg:
        # 1. 更新 BarGenerator
        self.bg.update_tick(tick)
        
        # 2. 获取正在构建的K线
        if self.bg.bar:
            bar = copy(self.bg.bar)
            bar.datetime = bar.datetime.replace(second=0, microsecond=0)
            
            # 3. 修正开盘价（从历史数据或数据库获取）
            # ... 开盘价修正逻辑 ...
            
            # 4. ✅ 更新图表（每次tick都更新）
            self.chart.update_bar(bar)
```

**关键**：
- ✅ 每次tick都调用 `update_bar(bar)`
- ✅ 正在构建的K线实时显示

## 多周期实时K线更新逻辑（修复后）

### `update_tick()` - MultiTimeframeWidget

```python
def update_tick(self, tick):
    # 1. 更新 BarGenerator
    self._bg_1m.update_tick(tick)
    
    # 2. ✅ 实时更新正在构建的K线（每次tick都更新）
    if self._bg_1m.bar:
        # 更新主图
        self._chart.update_bar(self._bg_1m.bar)
        
        # 强制刷新显示
        candle_plot = self._chart.get_plot("candle")
        if candle_plot:
            candle_plot.update()
        self._chart.update()
```

**关键**：
- ✅ 每次tick都调用 `update_bar()`
- ✅ 添加了强制刷新（`candle_plot.update()`, `self._chart.update()`）

## 对比

| 功能 | 单周期 | 多周期（修复前） | 多周期（修复后） |
|------|--------|----------------|----------------|
| **tick处理** | ✅ | ✅ | ✅ |
| **更新 bg.bar** | ✅ | ✅ | ✅ |
| **update_bar()** | ✅ | ❌ | ✅ |
| **强制刷新** | ? | ❌ | ✅ |
| **实时K线显示** | ✅ | ❌ | ✅ |

## ChartWidget.update_bar() 的工作原理

需要检查 `ChartWidget.update_bar()` 是否会自动刷新显示。

如果不会自动刷新，单周期可能也需要添加强制刷新。

让我检查 `ChartWidget.update_bar()` 的实现。

