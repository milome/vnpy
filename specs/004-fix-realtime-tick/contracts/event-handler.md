# Event Handler Contract

**Feature**: 修复 ChartWindow 实时 Tick 数据刷新  
**Date**: 2025-01-27

## Event Registration Contract

### Method: `register_event()`

**Purpose**: 注册事件监听器，使ChartWindow能够接收tick数据

**Signature**:
```python
def register_event(self) -> None:
    """注册事件监听器"""
```

**Preconditions**:
- `self.event_engine` 必须已初始化
- `self.process_tick_event` 方法必须已实现

**Postconditions**:
- `EVENT_TICK` 事件已注册到 EventEngine
- 后续的 `EVENT_TICK` 事件将被 `process_tick_event` 处理

**Side Effects**:
- EventEngine 的 `_handlers` 字典中添加了新的处理器

**Error Handling**:
- 如果 EventEngine 未初始化，应记录错误但不抛出异常（向后兼容）

## Event Processing Contract

### Method: `process_tick_event(event: Event) -> None`

**Purpose**: 处理接收到的tick事件，更新K线显示

**Signature**:
```python
def process_tick_event(self, event: Event) -> None:
    """处理Tick事件 - 支持所有周期的实时更新"""
```

**Input**:
- `event: Event` - 包含TickData的事件对象
- `event.type` 必须是 `EVENT_TICK`
- `event.data` 必须是 `TickData` 对象

**Preconditions**:
- `self.current_vt_symbol` 必须已设置
- `self.history_loaded` 必须为 `True`（可选，但建议）

**Postconditions**:
- 如果tick属于当前合约且历史数据已加载，K线将被更新
- 如果tick不属于当前合约或历史数据未加载，方法直接返回，不更新

**Side Effects**:
- 可能更新 `self._current_bar`
- 可能调用 `self.chart.update_bar()`
- 可能更新 `self.history_data`

**Error Handling**:
- 如果 `event.data` 不是 TickData，应记录错误并返回
- 如果处理过程中发生异常，应记录错误但不影响其他功能

## Event Unregistration Contract

### Method: `closeEvent(event: QtGui.QCloseEvent) -> None`

**Purpose**: 窗口关闭时注销事件监听器

**Signature**:
```python
def closeEvent(self, event: QtGui.QCloseEvent) -> None:
    """窗口关闭时注销事件监听"""
```

**Preconditions**:
- `self.event_engine` 必须已初始化
- `self.process_tick_event` 必须是已注册的处理器

**Postconditions**:
- 所有事件监听器已从 EventEngine 注销
- 不会再有tick事件被处理

**Side Effects**:
- EventEngine 的 `_handlers` 字典中移除了处理器

**Error Handling**:
- 如果注销失败，应记录警告但不阻止窗口关闭

