# Tasks: 修复 ChartWindow 实时 Tick 数据刷新

**Input**: Design documents from `/specs/004-fix-realtime-tick/`  
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are REQUIRED per Constitution (Test-First Development). All tests must be written and FAIL before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `vnpy/trader/ui/`, `tests/chart/` at repository root
- Paths shown below assume single project structure

---

## Phase 1: Foundational (Blocking Prerequisites)

**Purpose**: Core event registration infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests for Foundational Phase ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T001 [P] Test event registration in tests/chart/test_event_registration.py
- [ ] T002 [P] Test event unregistration in tests/chart/test_event_registration.py
- [ ] T003 [P] Test event handler receives tick events in tests/chart/test_event_registration.py

### Implementation for Foundational Phase

- [ ] T004 Implement `register_event()` method in vnpy/trader/ui/widget.py
- [ ] T005 Implement `closeEvent()` method with event unregistration in vnpy/trader/ui/widget.py
- [ ] T006 Add error handling for missing event_engine in vnpy/trader/ui/widget.py
- [ ] T007 Add logging for event registration/unregistration in vnpy/trader/ui/widget.py

**Checkpoint**: Foundation ready - event registration infrastructure complete. User story implementation can now begin.

---

## Phase 2: User Story 1 - 实时查看多周期K线更新 (Priority: P1) 🎯 MVP

**Goal**: 实现多周期K线的实时更新功能，使交易员能够实时看到tick数据跳动和正在聚合的K线更新

**Independent Test**: 打开ChartWindow，选择任意周期，订阅行情后，观察最后一根K线是否随着tick数据实时更新。可以通过对比行情窗口的tick数据和图表中的K线变化来验证。

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T008 [P] [US1] Test 1-minute bar real-time update in tests/chart/test_realtime_tick.py
- [ ] T009 [P] [US1] Test 5-minute bar real-time update in tests/chart/test_realtime_tick.py
- [ ] T010 [P] [US1] Test 1-hour bar real-time update in tests/chart/test_realtime_tick.py
- [ ] T011 [P] [US1] Test 4-hour bar real-time update in tests/chart/test_realtime_tick.py
- [ ] T012 [P] [US1] Test daily bar real-time update in tests/chart/test_realtime_tick.py
- [ ] T013 [P] [US1] Test tick filtering by vt_symbol in tests/chart/test_realtime_tick.py
- [ ] T014 [P] [US1] Test tick filtering when history not loaded in tests/chart/test_realtime_tick.py
- [ ] T015 [P] [US1] Test BarGenerator integration for 1-minute bars in tests/chart/test_realtime_tick.py

### Implementation for User Story 1

- [ ] T016 [US1] Ensure `process_tick_event()` method is called correctly in vnpy/trader/ui/widget.py
- [ ] T017 [US1] Implement `on_bar()` callback method in vnpy/trader/ui/widget.py
- [ ] T018 [US1] Add tick data filtering logic in `process_tick_event()` in vnpy/trader/ui/widget.py
- [ ] T019 [US1] Ensure 1-minute period uses BarGenerator.update_tick() in vnpy/trader/ui/widget.py
- [ ] T020 [US1] Ensure large periods use _update_current_bar_with_tick() in vnpy/trader/ui/widget.py
- [ ] T021 [US1] Add thread safety using Qt signal slot mechanism in vnpy/trader/ui/widget.py
- [ ] T022 [US1] Add error handling and logging in tick processing in vnpy/trader/ui/widget.py

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently. All periods (1m, 5m, 1h, 4h, 1d) should update in real-time.

---

## Phase 3: User Story 2 - 实时画线交易挂单功能 (Priority: P1)

**Goal**: 实现实时挂单功能，当市场价格突破挂单线时自动触发下单

**Independent Test**: 在图表上画一条挂单线，使用模拟功能或等待真实行情，当价格突破挂单线时，验证是否触发了下单操作。可以通过日志或订单窗口确认。

**Dependencies**: Requires User Story 1 (real-time tick updates must be working)

### Tests for User Story 2 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T023 [P] [US2] Test buy order trigger on price breakthrough in tests/chart/test_drawing_trade_realtime.py
- [ ] T024 [P] [US2] Test sell order trigger on price breakthrough in tests/chart/test_drawing_trade_realtime.py
- [ ] T025 [P] [US2] Test no order trigger when price not breakthrough in tests/chart/test_drawing_trade_realtime.py
- [ ] T026 [P] [US2] Test price breakthrough detection with real-time tick in tests/chart/test_drawing_trade_realtime.py

### Implementation for User Story 2

- [ ] T027 [US2] Verify PriceBreakthroughMonitor receives real-time tick data in vnpy/chart/price_breakthrough.py
- [ ] T028 [US2] Ensure order trigger logic works with real-time tick updates in vnpy/chart/widget.py
- [ ] T029 [US2] Add logging for order trigger events in vnpy/chart/widget.py
- [ ] T030 [US2] Add error handling for order submission failures in vnpy/chart/widget.py

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently. Real-time order triggering should be functional.

---

## Phase 4: User Story 3 - 实时止损止盈功能 (Priority: P1)

**Goal**: 实现实时止损止盈功能，当市场价格触及止损或止盈线时自动触发平仓

**Independent Test**: 在图表上为持仓设置止损线和止盈线，使用模拟功能或等待真实行情，当价格触及止损或止盈线时，验证是否触发了平仓操作。

**Dependencies**: Requires User Story 1 (real-time tick updates must be working)

### Tests for User Story 3 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T031 [P] [US3] Test stop loss trigger for long position in tests/chart/test_drawing_trade_realtime.py
- [ ] T032 [P] [US3] Test take profit trigger for long position in tests/chart/test_drawing_trade_realtime.py
- [ ] T033 [P] [US3] Test stop loss trigger for short position in tests/chart/test_drawing_trade_realtime.py
- [ ] T034 [P] [US3] Test take profit trigger for short position in tests/chart/test_drawing_trade_realtime.py
- [ ] T035 [P] [US3] Test no trigger when price not touching lines in tests/chart/test_drawing_trade_realtime.py

### Implementation for User Story 3

- [ ] T036 [US3] Verify stop loss line monitoring receives real-time tick data in vnpy/chart/widget.py
- [ ] T037 [US3] Verify take profit line monitoring receives real-time tick data in vnpy/chart/widget.py
- [ ] T038 [US3] Ensure close position logic works with real-time tick updates in vnpy/chart/widget.py
- [ ] T039 [US3] Add logging for stop loss/take profit trigger events in vnpy/chart/widget.py
- [ ] T040 [US3] Add error handling for close position failures in vnpy/chart/widget.py

**Checkpoint**: At this point, all three user stories should be fully functional. Real-time drawing trading (order, stop loss, take profit) should be complete.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories and ensure production readiness

- [ ] T041 [P] Add performance monitoring for tick update latency in vnpy/trader/ui/widget.py
- [ ] T042 [P] Add performance monitoring for chart refresh latency in vnpy/trader/ui/widget.py
- [ ] T043 [P] Add performance monitoring for price breakthrough trigger latency in vnpy/chart/widget.py
- [ ] T044 [P] Verify event unregistration on contract switch in vnpy/trader/ui/widget.py
- [ ] T045 [P] Add integration tests for all periods real-time update in tests/chart/test_integration_realtime.py
- [ ] T046 [P] Add integration tests for drawing trade real-time triggers in tests/chart/test_integration_realtime.py
- [ ] T047 [P] Run code quality checks (ruff check, mypy) and fix issues
- [ ] T048 [P] Update documentation in quickstart.md with verification results
- [ ] T049 [P] Add performance benchmarks and validation in tests/chart/test_performance.py
- [ ] T050 [P] Verify backward compatibility with existing history data loading in tests/chart/test_backward_compat.py

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 1)**: No dependencies - can start immediately
- **User Story 1 (Phase 2)**: Depends on Foundational completion - BLOCKS User Stories 2 and 3
- **User Story 2 (Phase 3)**: Depends on User Story 1 completion
- **User Story 3 (Phase 4)**: Depends on User Story 1 completion (can run in parallel with US2)
- **Polish (Phase 5)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 1) - No dependencies on other stories
- **User Story 2 (P1)**: Can start after User Story 1 - Requires real-time tick updates
- **User Story 3 (P1)**: Can start after User Story 1 - Requires real-time tick updates (can run in parallel with US2)

### Within Each Phase

- Tests (REQUIRED per Constitution) MUST be written and FAIL before implementation
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Foundational tests (T001-T003) can run in parallel
- All User Story 1 tests (T008-T015) can run in parallel
- All User Story 2 tests (T023-T026) can run in parallel
- All User Story 3 tests (T031-T035) can run in parallel
- User Stories 2 and 3 can be worked on in parallel (after US1 completes)
- All Polish tasks (T041-T050) can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Test 1-minute bar real-time update in tests/chart/test_realtime_tick.py"
Task: "Test 5-minute bar real-time update in tests/chart/test_realtime_tick.py"
Task: "Test 1-hour bar real-time update in tests/chart/test_realtime_tick.py"
Task: "Test 4-hour bar real-time update in tests/chart/test_realtime_tick.py"
Task: "Test daily bar real-time update in tests/chart/test_realtime_tick.py"
Task: "Test tick filtering by vt_symbol in tests/chart/test_realtime_tick.py"
Task: "Test tick filtering when history not loaded in tests/chart/test_realtime_tick.py"
Task: "Test BarGenerator integration for 1-minute bars in tests/chart/test_realtime_tick.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Foundational (event registration)
2. Complete Phase 2: User Story 1 (real-time K-line updates)
3. **STOP and VALIDATE**: Test User Story 1 independently
4. Deploy/demo if ready

### Incremental Delivery

1. Complete Foundational → Event registration ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP - real-time K-line updates!)
3. Add User Story 2 → Test independently → Deploy/Demo (real-time order triggering)
4. Add User Story 3 → Test independently → Deploy/Demo (real-time stop loss/take profit)
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (real-time K-line updates)
3. Once User Story 1 is done:
   - Developer B: User Story 2 (order triggering)
   - Developer C: User Story 3 (stop loss/take profit) - can run in parallel with US2
4. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- **CRITICAL**: Verify tests fail before implementing (TDD requirement per Constitution)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
- All tests are REQUIRED per Constitution (Test-First Development)






