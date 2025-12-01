# Research: 修复 ChartWindow 实时 Tick 数据刷新

**Date**: 2025-01-27  
**Feature**: [spec.md](spec.md) | [plan.md](plan.md)

## Research Tasks

### 1. VeighNa EventEngine 事件注册机制

**Task**: 研究 VeighNa EventEngine 的事件注册和处理机制

**Findings**:
- EventEngine 使用 `register(type: str, handler: HandlerType)` 方法注册事件处理器
- 事件处理器函数签名：`HandlerType = Callable[[Event], None]`
- EventEngine 在独立线程中运行，通过队列分发事件
- 事件处理是同步的，但EventEngine本身在后台线程运行
- 已有示例：`OmsEngine.register_event()` 展示了标准的事件注册模式

**Decision**: 使用标准 VeighNa 事件注册模式，在 ChartWindow 中实现 `register_event()` 方法

**Rationale**: 
- 遵循VeighNa框架标准模式，保持代码一致性
- EventEngine已经提供了完整的注册/注销机制
- 其他引擎（如OmsEngine）已经成功使用此模式

**Alternatives considered**:
- 直接调用方法传递tick数据：违反事件驱动架构原则，被拒绝
- 使用观察者模式：EventEngine已经实现了观察者模式，无需重复实现

### 2. Qt 信号槽机制用于线程安全UI更新

**Task**: 研究如何在EventEngine（后台线程）和Qt UI（主线程）之间安全传递数据

**Findings**:
- EventEngine 在独立线程中运行（`_run()` 方法在 `Thread` 中执行）
- Qt UI 必须在主线程中更新
- PySide6 的 `QtCore.Signal` 和 `QtCore.Slot` 机制可以安全地跨线程传递数据
- ChartWindow 已经定义了 `signal_tick: QtCore.Signal = QtCore.Signal(Event)`，但未使用

**Decision**: 使用 Qt 信号槽机制确保线程安全

**Rationale**:
- Qt 信号槽机制是跨线程通信的标准方式
- ChartWindow 已经定义了相关信号，只需连接即可
- 符合PySide6最佳实践

**Alternatives considered**:
- 使用 `QMetaObject.invokeMethod()`：更复杂，信号槽更简洁
- 使用 `QTimer.singleShot()`：适合延迟执行，不适合实时数据流

### 3. BarGenerator 与实时K线合成

**Task**: 研究 BarGenerator 如何从 tick 数据合成1分钟K线

**Findings**:
- `BarGenerator.update_tick(tick: TickData)` 方法接收tick数据并更新内部状态
- 当1分钟周期完成时，会调用 `on_bar` 回调函数
- `BarGenerator.bar` 属性包含当前正在构建的K线（未完成）
- 对于大周期（5分钟、1小时等），需要从1分钟K线或tick数据合成

**Decision**: 
- 1分钟周期：使用 BarGenerator 从 tick 合成K线
- 大周期：使用现有的 `_update_current_bar_with_tick()` 方法直接更新

**Rationale**:
- BarGenerator 已经实现了1分钟K线合成逻辑
- 大周期的实时更新逻辑已经存在，只需确保tick数据能传递到该方法

**Alternatives considered**:
- 为每个周期创建独立的BarGenerator：过于复杂，现有逻辑已足够

### 4. 事件注销和资源管理

**Task**: 研究如何正确注销事件监听器，避免内存泄漏

**Findings**:
- EventEngine 提供 `unregister(type: str, handler: HandlerType)` 方法
- 必须在窗口关闭时注销所有事件监听器
- Qt 的 `closeEvent()` 方法可以捕获窗口关闭事件
- 切换合约时也需要注销旧合约的监听器

**Decision**: 
- 在 `closeEvent()` 中注销所有事件监听器
- 在 `switch_chart()` 中注销旧合约的监听器（如果需要）

**Rationale**:
- 标准Qt窗口生命周期管理
- 防止内存泄漏和重复处理

**Alternatives considered**:
- 使用弱引用：EventEngine不支持，且Qt信号槽已处理对象生命周期

## Resolved Clarifications

所有技术细节已通过代码审查和现有实现确认，无需额外澄清。

## Implementation Notes

1. **事件注册时机**：在 `__init__()` 中调用 `register_event()`，确保窗口创建时即注册
2. **事件过滤**：在 `process_tick_event()` 中过滤非当前合约的tick数据
3. **历史数据检查**：只有在 `history_loaded` 为 True 时才处理tick更新
4. **线程安全**：使用Qt信号槽确保UI更新在主线程执行
5. **向后兼容**：不修改现有历史数据加载和gap补齐逻辑

