# Tasks: ChartWindow实时显示K线，修正开盘价引起的资源泄漏

**Input**: Design documents from `/specs/005-fix-chartwindow-openprice-resource-leak/`  
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are REQUIRED per Constitution (Test-First Development). All tests must be written and FAIL before implementation.

**Organization**: Tasks are grouped by fix area to enable independent implementation and testing of each fix.

## Format: `[ID] [P?] [Area] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Area]**: Which fix area this task belongs to (QPICTURE, CACHE, DATAFEED, EXCEPTION)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `vnpy/chart/`, `vnpy/trader/ui/`, `tests/chart/` at repository root
- Paths shown below assume single project structure

---

## Phase 1: QPicture资源释放修复 (Priority: P1) 🎯

**Goal**: 修复QPicture资源泄漏，确保旧的QPicture对象在更新时被正确释放

**Independent Test**: 创建多个K线并频繁更新，监控QPicture对象数量，验证旧对象被正确释放。

### Tests for QPicture Resource Release ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T001 [P] [QPICTURE] Test QPicture object release in update_bar() in tests/chart/test_resource_leak.py
- [ ] T002 [P] [QPICTURE] Test QPicture object release in clear_all() in tests/chart/test_resource_leak.py
- [ ] T003 [P] [QPICTURE] Test QPicture memory leak after frequent updates in tests/chart/test_resource_leak.py
- [ ] T004 [P] [QPICTURE] Test QPicture release performance (should be < 100ms) in tests/chart/test_resource_leak.py
- [ ] T005 [P] [QPICTURE] Test QPicture release on window close in tests/chart/test_resource_leak.py
- [ ] T006 [P] [QPICTURE] Test CandleItem QPicture release in tests/chart/test_resource_leak.py
- [ ] T007 [P] [QPICTURE] Test VolumeItem QPicture release in tests/chart/test_resource_leak.py

### Implementation for QPicture Resource Release

- [ ] T008 [QPICTURE] Modify ChartItem.update_bar() to explicitly release old QPicture in vnpy/chart/item.py
- [ ] T009 [QPICTURE] Modify ChartItem.clear_all() to explicitly release all QPicture objects in vnpy/chart/item.py
- [ ] T010 [QPICTURE] Add explicit deletion of old QPicture before setting new reference in vnpy/chart/item.py
- [ ] T011 [QPICTURE] Ensure QPicture release does not affect drawing performance in vnpy/chart/item.py
- [ ] T012 [QPICTURE] Add logging for QPicture release operations (optional, for debugging) in vnpy/chart/item.py

**Checkpoint**: QPicture resource release is working. Old objects are explicitly released on update and clear_all.

---

## Phase 2: 查询缓存实现 (Priority: P1) 🎯

**Goal**: 实现开盘价查询缓存，减少重复的数据库和Datafeed查询

**Independent Test**: 模拟频繁的tick更新，验证相同时间的开盘价查询被缓存，减少实际查询次数。

**Dependencies**: None (can be implemented independently)

### Tests for Query Cache ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T013 [P] [CACHE] Test open price cache hit in tests/chart/test_connection_leak.py
- [ ] T014 [P] [CACHE] Test open price cache miss in tests/chart/test_connection_leak.py
- [ ] T015 [P] [CACHE] Test cache TTL expiration in tests/chart/test_connection_leak.py
- [ ] T016 [P] [CACHE] Test cache cleanup on size limit in tests/chart/test_connection_leak.py
- [ ] T017 [P] [CACHE] Test cache clear on window close in tests/chart/test_connection_leak.py
- [ ] T018 [P] [CACHE] Test cache reduces database queries in tests/chart/test_connection_leak.py
- [ ] T019 [P] [CACHE] Test cache thread safety in tests/chart/test_connection_leak.py

### Implementation for Query Cache

- [ ] T020 [CACHE] Add _open_price_cache dictionary to ChartWindow.__init__() in vnpy/trader/ui/widget.py
- [ ] T021 [CACHE] Implement _get_cached_open_price() method in vnpy/trader/ui/widget.py
- [ ] T022 [CACHE] Implement _set_cached_open_price() method in vnpy/trader/ui/widget.py
- [ ] T023 [CACHE] Add cache TTL check (60 seconds) in _get_cached_open_price() in vnpy/trader/ui/widget.py
- [ ] T024 [CACHE] Add cache size limit check and cleanup in _set_cached_open_price() in vnpy/trader/ui/widget.py
- [ ] T025 [CACHE] Integrate cache check in process_tick_event() before database query in vnpy/trader/ui/widget.py
- [ ] T026 [CACHE] Integrate cache check in process_tick_event() before Datafeed query in vnpy/trader/ui/widget.py
- [ ] T027 [CACHE] Set cache after successful database query in vnpy/trader/ui/widget.py
- [ ] T028 [CACHE] Set cache after successful Datafeed query in vnpy/trader/ui/widget.py
- [ ] T029 [CACHE] Clear cache in closeEvent() in vnpy/trader/ui/widget.py

**Checkpoint**: Query cache is working. Cache hit rate should be > 90%, significantly reducing database and Datafeed queries.

---

## Phase 3: Datafeed实例复用 (Priority: P1) 🎯

**Goal**: 复用Datafeed实例，避免频繁创建新的富途OpenAPI连接

**Independent Test**: 模拟频繁的tick更新，验证Datafeed实例被复用，不会创建多个实例。

**Dependencies**: None (can be implemented independently)

### Tests for Datafeed Instance Reuse ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T030 [P] [DATAFEED] Test Datafeed instance reuse from MainEngine in tests/chart/test_connection_leak.py
- [ ] T031 [P] [DATAFEED] Test Datafeed instance caching in ChartWindow in tests/chart/test_connection_leak.py
- [ ] T032 [P] [DATAFEED] Test Datafeed instance creation as last resort in tests/chart/test_connection_leak.py
- [ ] T033 [P] [DATAFEED] Test Datafeed connection close on window close in tests/chart/test_connection_leak.py
- [ ] T034 [P] [DATAFEED] Test Datafeed thread safety in tests/chart/test_connection_leak.py
- [ ] T035 [P] [DATAFEED] Test no multiple Datafeed instances created in tests/chart/test_connection_leak.py
- [ ] T036 [P] [DATAFEED] Test FutuOpenAPI connection count stays below 128 in tests/chart/test_connection_leak.py

### Implementation for Datafeed Instance Reuse

- [ ] T037 [DATAFEED] Add _cached_datafeed attribute to ChartWindow.__init__() in vnpy/trader/ui/widget.py
- [ ] T038 [DATAFEED] Add _datafeed_lock for thread safety in ChartWindow.__init__() in vnpy/trader/ui/widget.py
- [ ] T039 [DATAFEED] Implement _get_datafeed() method with MainEngine priority in vnpy/trader/ui/widget.py
- [ ] T040 [DATAFEED] Implement _get_datafeed() with instance caching in vnpy/trader/ui/widget.py
- [ ] T041 [DATAFEED] Implement _get_datafeed() with new instance creation as last resort in vnpy/trader/ui/widget.py
- [ ] T042 [DATAFEED] Replace direct FutuDatafeed creation with _get_datafeed() in process_tick_event() in vnpy/trader/ui/widget.py
- [ ] T043 [DATAFEED] Add Datafeed close in closeEvent() in vnpy/trader/ui/widget.py
- [ ] T044 [DATAFEED] Add error handling and logging in _get_datafeed() in vnpy/trader/ui/widget.py

**Checkpoint**: Datafeed instance reuse is working. No multiple instances are created, connection count stays below 128.

---

## Phase 4: 异常处理改进 (Priority: P2)

**Goal**: 改进异常处理，确保数据库和Datafeed连接在异常时也能正确关闭

**Independent Test**: 模拟数据库和Datafeed查询异常，验证连接被正确关闭，不会泄漏。

**Dependencies**: Phase 2 and Phase 3 (uses cache and Datafeed methods)

### Tests for Exception Handling ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T045 [P] [EXCEPTION] Test database query exception handling in tests/chart/test_connection_leak.py
- [ ] T046 [P] [EXCEPTION] Test Datafeed query exception handling in tests/chart/test_connection_leak.py
- [ ] T047 [P] [EXCEPTION] Test connection cleanup on exception in tests/chart/test_connection_leak.py
- [ ] T048 [P] [EXCEPTION] Test error logging on exception in tests/chart/test_connection_leak.py
- [ ] T049 [P] [EXCEPTION] Test no exception propagation to main flow in tests/chart/test_connection_leak.py

### Implementation for Exception Handling

- [ ] T050 [EXCEPTION] Wrap database query in try-finally in process_tick_event() in vnpy/trader/ui/widget.py
- [ ] T051 [EXCEPTION] Wrap Datafeed query in try-finally in process_tick_event() in vnpy/trader/ui/widget.py
- [ ] T052 [EXCEPTION] Add error logging for database query failures in vnpy/trader/ui/widget.py
- [ ] T053 [EXCEPTION] Add error logging for Datafeed query failures in vnpy/trader/ui/widget.py
- [ ] T054 [EXCEPTION] Ensure exceptions don't break main tick processing flow in vnpy/trader/ui/widget.py
- [ ] T055 [EXCEPTION] Add connection cleanup in finally blocks (if needed) in vnpy/trader/ui/widget.py

**Checkpoint**: Exception handling is improved. Connections are properly closed even on exceptions.

---

## Phase 5: 连接数监控和诊断 (Priority: P2)

**Goal**: 添加连接数监控和日志，帮助诊断连接泄漏问题

**Dependencies**: Phase 2, Phase 3, Phase 4

### Tests for Connection Monitoring ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T056 [P] [MONITOR] Test database connection count monitoring in tests/chart/test_connection_leak.py
- [ ] T057 [P] [MONITOR] Test Datafeed connection count monitoring in tests/chart/test_connection_leak.py
- [ ] T058 [P] [MONITOR] Test connection count logging in tests/chart/test_connection_leak.py
- [ ] T059 [P] [MONITOR] Test connection leak detection in tests/chart/test_connection_leak.py

### Implementation for Connection Monitoring

- [ ] T060 [MONITOR] Add connection count monitoring method in vnpy/trader/ui/widget.py
- [ ] T061 [MONITOR] Add periodic connection count logging (optional) in vnpy/trader/ui/widget.py
- [ ] T062 [MONITOR] Add connection count check before creating new connections in vnpy/trader/ui/widget.py
- [ ] T063 [MONITOR] Add warning when connection count approaches limit in vnpy/trader/ui/widget.py

**Checkpoint**: Connection monitoring is working. Can track connection count and detect leaks.

---

## Phase 6: 集成测试和验证 (Priority: P1) 🎯

**Goal**: 验证所有修复是否正常工作，确保没有回归问题

**Dependencies**: Phase 1, Phase 2, Phase 3, Phase 4

### Integration Tests ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T064 [P] [INTEGRATION] Test long-running stability (1 hour) in tests/chart/test_integration_resource_leak.py
- [ ] T065 [P] [INTEGRATION] Test memory usage stability in tests/chart/test_integration_resource_leak.py
- [ ] T066 [P] [INTEGRATION] Test connection count stability in tests/chart/test_integration_resource_leak.py
- [ ] T067 [P] [INTEGRATION] Test all fixes work together in tests/chart/test_integration_resource_leak.py
- [ ] T068 [P] [INTEGRATION] Test backward compatibility in tests/chart/test_integration_resource_leak.py
- [ ] T069 [P] [INTEGRATION] Test performance impact (should be < 5% degradation) in tests/chart/test_integration_resource_leak.py

### Performance Tests

- [ ] T070 [P] [PERF] Test QPicture release performance in tests/chart/test_performance_resource_leak.py
- [ ] T071 [P] [PERF] Test cache hit rate (should be > 90%) in tests/chart/test_performance_resource_leak.py
- [ ] T072 [P] [PERF] Test query frequency reduction in tests/chart/test_performance_resource_leak.py
- [ ] T073 [P] [PERF] Test memory usage over time in tests/chart/test_performance_resource_leak.py
- [ ] T074 [P] [PERF] Test connection count over time in tests/chart/test_performance_resource_leak.py

### Validation Tests

- [ ] T075 [P] [VALIDATION] Test 24-hour stability in tests/chart/test_validation_resource_leak.py
- [ ] T076 [P] [VALIDATION] Test memory leak detection with tools in tests/chart/test_validation_resource_leak.py
- [ ] T077 [P] [VALIDATION] Test connection leak detection in tests/chart/test_validation_resource_leak.py
- [ ] T078 [P] [VALIDATION] Test all success criteria are met in tests/chart/test_validation_resource_leak.py

**Checkpoint**: All fixes are validated. System runs stably for 24 hours without resource leaks.

---

## Phase 7: 文档和清理 (Priority: P3)

**Goal**: 更新文档，清理临时代码，准备发布

**Dependencies**: All previous phases

### Documentation

- [ ] T079 [P] [DOC] Update code comments for resource release in vnpy/chart/item.py
- [ ] T080 [P] [DOC] Update code comments for cache implementation in vnpy/trader/ui/widget.py
- [ ] T081 [P] [DOC] Update code comments for Datafeed reuse in vnpy/trader/ui/widget.py
- [ ] T082 [P] [DOC] Add changelog entry for resource leak fixes
- [ ] T083 [P] [DOC] Update README if needed

### Code Cleanup

- [ ] T084 [P] [CLEANUP] Remove debug logging if added in vnpy/chart/item.py
- [ ] T085 [P] [CLEANUP] Remove debug logging if added in vnpy/trader/ui/widget.py
- [ ] T086 [P] [CLEANUP] Review and optimize cache cleanup logic
- [ ] T087 [P] [CLEANUP] Review and optimize connection monitoring (if too verbose)

**Checkpoint**: Code is clean, documented, and ready for review.

---

## Task Summary

### By Priority

**P1 (Critical - Must Complete)**:
- Phase 1: QPicture资源释放修复 (T001-T012)
- Phase 2: 查询缓存实现 (T013-T029)
- Phase 3: Datafeed实例复用 (T030-T044)
- Phase 6: 集成测试和验证 (T064-T078)

**P2 (Important - Should Complete)**:
- Phase 4: 异常处理改进 (T045-T055)
- Phase 5: 连接数监控和诊断 (T056-T063)

**P3 (Nice to Have)**:
- Phase 7: 文档和清理 (T079-T087)

### By Fix Area

**QPICTURE** (12 tasks): T001-T012  
**CACHE** (17 tasks): T013-T029  
**DATAFEED** (15 tasks): T030-T044  
**EXCEPTION** (11 tasks): T045-T055  
**MONITOR** (8 tasks): T056-T063  
**INTEGRATION** (15 tasks): T064-T078  
**DOC** (9 tasks): T079-T087

**Total**: 87 tasks

### Parallel Execution Opportunities

Tasks marked with **[P]** can be executed in parallel:
- Test tasks can be written in parallel
- Different fix areas can be implemented in parallel (after Phase 1)
- Documentation can be done in parallel with implementation

---

## Implementation Order Recommendation

1. **Week 1**: Phase 1 (QPicture) + Phase 2 (Cache) - Core fixes
2. **Week 2**: Phase 3 (Datafeed) + Phase 4 (Exception) - Connection fixes
3. **Week 3**: Phase 6 (Integration) - Validation
4. **Week 4**: Phase 5 (Monitor) + Phase 7 (Doc) - Polish

---

## Success Criteria Validation

Each phase should validate against success criteria:

- **SC-001**: Memory usage growth < 10% after 1 hour (Phase 6)
- **SC-002**: QPicture release < 100ms (Phase 1)
- **SC-003**: Memory stable after 24 hours (Phase 6)
- **SC-008**: Database connection count stable (Phase 2, Phase 6)
- **SC-009**: FutuOpenAPI connection count < 128 (Phase 3, Phase 6)
- **SC-010**: Database queries use connection pool/reuse (Phase 2)
- **SC-011**: Datafeed queries reuse instances (Phase 3)

---

## Notes

- All test tasks must be completed BEFORE implementation tasks
- Tests should fail initially, then pass after implementation
- Code review required before merging
- Performance benchmarks should be recorded before and after fixes

