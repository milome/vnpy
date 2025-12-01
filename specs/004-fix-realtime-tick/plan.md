# Implementation Plan: 修复 ChartWindow 实时 Tick 数据刷新

**Branch**: `004-fix-realtime-tick` | **Date**: 2025-01-27 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/004-fix-realtime-tick/spec.md`

## Summary

修复 ChartWindow 无法实时接收和处理 tick 数据的问题，实现多周期K线（1分钟、5分钟、1小时、4小时、1日）的实时更新，使画线交易功能（挂单、止损、止盈）能够正常工作。

**技术方案**：通过实现缺失的 `register_event()` 方法，注册 `EVENT_TICK` 事件监听器，完善 `process_tick_event()` 方法的处理逻辑，确保所有周期都能实时更新。使用 Qt 信号槽机制保证线程安全，实现事件注销机制避免内存泄漏。

## Technical Context

**Language/Version**: Python 3.10+ (推荐 3.13)  
**Primary Dependencies**: PySide6 6.8.2.1, pyqtgraph >= 0.13.7, VeighNa EventEngine  
**Storage**: N/A (实时数据流，不持久化)  
**Testing**: pytest, Qt 测试框架  
**Target Platform**: Windows, Linux, macOS  
**Project Type**: Desktop GUI application (PySide6)  
**Performance Goals**: 
- Tick更新延迟 < 100ms
- 图表刷新延迟 < 50ms  
- 价格突破触发延迟 < 200ms
- 支持至少 1000 根K线流畅显示
- 单个图表窗口内存占用 < 200MB

**Constraints**: 
- 必须保持向后兼容，不破坏现有历史数据加载和gap补齐功能
- 必须遵循VeighNa事件驱动架构
- 必须确保UI更新在主线程执行
- 必须支持所有周期（1分钟、5分钟、1小时、4小时、1日）的实时更新

**Scale/Scope**: 
- 单个ChartWindow实例
- 支持至少 5 个不同周期同时显示
- 支持至少 100 条价格线同时显示和管理
- 长时间运行（24小时）无性能退化

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Test-First Development (NON-NEGOTIABLE)
✅ **PASS**: 将遵循TDD流程，先编写测试用例验证事件注册和处理逻辑，然后实现功能。核心业务逻辑测试覆盖率目标 >= 90%。

### II. Code Quality Standards
✅ **PASS**: 代码将符合PEP8标准，使用ruff和mypy检查，所有函数和类包含完整docstring。

### III. Modular Architecture
✅ **PASS**: 事件处理逻辑将作为ChartWindow类的方法实现，遵循现有代码结构。如果代码超过500行限制，将考虑提取为Mixin。

### IV. Real-Time Performance
✅ **PASS**: 实现将确保tick更新延迟 < 100ms，图表刷新延迟 < 50ms，价格突破触发延迟 < 200ms。使用事件驱动架构，避免阻塞主线程。

### V. Data Consistency & Persistence
✅ **PASS**: 不涉及数据持久化，实时tick数据仅用于更新显示，不存储。

### VI. Event-Driven Design
✅ **PASS**: 严格遵循VeighNa事件驱动设计，通过EventEngine接收tick数据，禁止直接调用方法传递状态。事件处理将实现幂等性。

### VII. Code File Size Limit
⚠️ **NEEDS ATTENTION**: `vnpy/trader/ui/widget.py` 文件当前有5565行，远超500行限制。本次修复将添加少量代码（约50-100行），但需要考虑后续重构计划。

**Justification**: 本次修复是紧急bug修复，添加的代码量小且集中。文件重构应在后续单独进行，不应阻塞本次修复。

## Project Structure

### Documentation (this feature)

```text
specs/004-fix-realtime-tick/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
vnpy/trader/ui/
└── widget.py            # ChartWindow类，添加register_event()和相关方法

tests/chart/
├── test_realtime_tick.py        # 新增：实时tick更新测试
├── test_event_registration.py    # 新增：事件注册测试
└── test_drawing_trade_realtime.py # 新增：画线交易实时触发测试
```

**Structure Decision**: 本次修复主要修改现有文件 `vnpy/trader/ui/widget.py`，添加事件注册和处理逻辑。测试文件将新增在 `tests/chart/` 目录下，遵循现有测试结构。

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| 文件行数超限 (widget.py 5565行) | 紧急bug修复，需要快速交付 | 文件重构是长期任务，不应阻塞紧急修复。本次只添加约50-100行代码，影响可控。后续应单独规划重构任务。 |

