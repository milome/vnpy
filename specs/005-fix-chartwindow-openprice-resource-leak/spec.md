# Feature Specification: ChartWindow实时显示K线，修正开盘价引起的资源泄漏

**Feature Branch**: `005-fix-chartwindow-openprice-resource-leak`  
**Created**: 2025-12-02  
**Status**: Draft  
**Input**: User description: "BUGFIX: ChartWindow实时显示K线，修正开盘价引起的资源leak"  
**Related Commit**: 1df34e3 (修复富途OpenAPI连接泄露问题)  
**Problem**: ChartWindow打开一段时间后无响应，日志显示连接数超过128导致无法建立新连接

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 修复实时K线更新时的资源泄漏 (Priority: P1)

交易员在ChartWindow中查看实时K线图表，当市场行情变化导致开盘价更新时，系统应该能够正确释放旧的绘图资源，避免内存和资源泄漏。长时间运行后，系统应该保持稳定的内存使用，不会因为频繁的K线更新而导致内存持续增长。

**Why this priority**: 资源泄漏会导致系统性能下降，长时间运行后可能导致内存耗尽或程序崩溃。这是系统稳定性的关键问题。

**Independent Test**: 打开ChartWindow，订阅实时行情，观察系统内存使用情况。在开盘价频繁变化的情况下（例如程序启动时修正开盘价），运行1小时后，内存使用应该保持稳定，不应该持续增长。

**Critical Issue**: 
- ChartWindow打开一段时间后无响应
- 日志显示"连接数超过128，无法建立新连接"
- 需要查清楚是什么连接数（数据库连接？富途OpenAPI连接？）
- 需要查清楚是哪个服务或环节报错

**Acceptance Scenarios**:

1. **Given** ChartWindow已打开并订阅实时行情, **When** 收到tick数据导致开盘价更新, **Then** 旧的QPicture对象应该被正确释放，不会造成资源泄漏
2. **Given** 系统长时间运行（24小时）, **When** 实时K线持续更新, **Then** 内存使用应该保持稳定，不应该持续增长
3. **Given** 程序启动时修正开盘价导致频繁更新, **When** 系统处理大量开盘价修正, **Then** 所有旧的QPicture对象应该被正确释放
4. **Given** 用户切换K线周期, **When** 系统重新绘制K线, **Then** 旧的绘图资源应该被正确清理

---

### User Story 2 - 确保QPicture对象正确释放 (Priority: P1)

系统在更新K线时，应该确保旧的QPicture对象在使用新对象之前被正确释放。特别是在实时更新场景下，当开盘价变化导致K线重新绘制时，应该显式释放旧的QPicture对象。

**Why this priority**: Qt的QPicture对象是C++对象，需要显式释放才能避免资源泄漏。仅仅将引用设置为None可能不足以立即释放资源。

**Independent Test**: 在实时更新K线时，监控QPicture对象的创建和销毁。每次更新K线时，旧的QPicture对象应该被显式释放，不应该有未释放的对象累积。

**Acceptance Scenarios**:

1. **Given** ChartItem.update_bar()被调用, **When** 旧的QPicture对象存在, **Then** 应该先显式释放旧的QPicture对象，再设置新的引用
2. **Given** ChartItem.clear_all()被调用, **When** 存在多个QPicture对象, **Then** 所有QPicture对象应该被正确释放
3. **Given** 实时更新导致频繁调用update_bar(), **When** 每次更新时, **Then** 旧的QPicture对象应该被及时释放，不应该累积

---

### Edge Cases

- 当开盘价在短时间内频繁变化时，系统应该能够处理而不导致资源泄漏
- 当系统内存不足时，应该能够正确释放资源，避免进一步的内存压力
- 当多个ChartItem同时更新时，每个Item的资源都应该被正确管理
- 当窗口关闭时，所有ChartItem的QPicture对象应该被完全释放
- 当切换合约导致大量K线更新时，系统应该能够正确释放所有旧资源
- **当实时修正开盘价频繁查询数据库时，不应该导致数据库连接数超过限制**
- **当实时修正开盘价创建Datafeed实例时，不应该导致富途OpenAPI连接数超过128**
- **当数据库查询失败时，应该正确处理异常，避免连接泄漏**

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 系统必须在更新K线时显式释放旧的QPicture对象，避免资源泄漏
- **FR-002**: 系统必须在ChartItem.update_bar()中，在设置新的QPicture引用之前释放旧的QPicture对象
- **FR-003**: 系统必须在ChartItem.clear_all()中确保所有QPicture对象被正确释放
- **FR-004**: 系统必须在实时更新场景下，正确处理开盘价变化导致的频繁更新
- **FR-005**: 系统必须确保QPicture对象的生命周期管理正确，避免内存泄漏
- **FR-006**: 系统必须在窗口关闭时清理所有ChartItem的资源
- **FR-007**: 系统必须保持向后兼容，不破坏现有的K线绘制功能
- **FR-008**: 系统必须确保资源释放操作不会影响绘制性能
- **FR-009**: 系统必须避免在实时修正开盘价时频繁创建数据库连接，应该使用连接池或复用连接
- **FR-010**: 系统必须避免在实时修正开盘价时频繁创建Datafeed实例，应该复用现有的Datafeed实例
- **FR-011**: 系统必须在数据库查询失败时正确关闭连接，避免连接泄漏
- **FR-012**: 系统必须限制实时修正开盘价的数据库查询频率，避免过度查询
- **FR-013**: 系统必须确保所有数据库连接在使用后正确关闭，即使发生异常

### Key Entities

- **ChartItem**: 图表项基类，负责管理K线的绘制和QPicture对象的生命周期
- **CandleItem**: 蜡烛图项，继承自ChartItem，负责绘制K线蜡烛图
- **QPicture**: Qt绘图对象，用于缓存K线的绘制结果，需要显式释放
- **BarData**: K线数据，包含开盘价、最高价、最低价、收盘价等信息
- **BarManager**: K线数据管理器，负责管理K线数据的存储和索引
- **Database**: 数据库接口，负责K线和tick数据的查询，需要管理连接池
- **Datafeed**: 数据服务接口，负责从外部数据源查询历史数据，需要复用连接
- **FutuDatafeed**: 富途数据服务实现，使用OpenAPI连接，连接数限制为128

## Problem Analysis

### 连接数超过128的问题

根据Commit 1df34e3的修复，富途OpenAPI的连接数限制为128。但ChartWindow在实时修正开盘价时，可能存在以下问题：

1. **数据库连接泄漏**：
   - 在`process_tick_event`方法中（2777-2807行），每次需要修正开盘价时都会调用`database.load_bar_data()`查询数据库
   - 在方法4.1中（2826-2850行），还会调用`database.load_tick_data()`查询数据库
   - 如果每次查询都创建新连接而不关闭，会导致数据库连接数持续增长

2. **Datafeed连接泄漏**：
   - 在方法4.2中（2852-2898行），如果找不到现有的datafeed，会创建新的`FutuDatafeed`实例
   - 每次创建新实例都会建立新的富途OpenAPI连接
   - 如果频繁创建而不关闭，会导致富途OpenAPI连接数超过128

3. **异常处理不当**：
   - 数据库查询和Datafeed查询都有异常处理，但可能没有正确关闭连接
   - 异常发生时，连接可能没有被释放

### 需要调查的问题

1. **连接数类型**：
   - 是数据库连接数（MySQL/SQLite等）？
   - 还是富途OpenAPI连接数？
   - 或者是两者都有？

2. **报错来源**：
   - 是数据库报错（如MySQL的max_connections）？
   - 还是富途OpenAPI报错（"连接个数超过128"）？
   - 需要查看具体错误日志

3. **查询频率**：
   - 实时修正开盘价时，每个tick都会触发查询吗？
   - 查询是否有去重或缓存机制？
   - 是否需要限制查询频率？

### 解决方案方向

1. **使用数据库连接池**：
   - 检查当前数据库实现是否使用连接池
   - 如果没有，考虑引入连接池（如SQLAlchemy的连接池）
   - 确保连接在使用后正确归还到池中

2. **复用Datafeed实例**：
   - 在ChartWindow中缓存Datafeed实例，避免频繁创建
   - 使用MainEngine的get_datafeed()方法获取现有实例
   - 避免在每次查询时创建新实例

3. **添加查询缓存**：
   - 对于相同时间的开盘价查询，使用缓存避免重复查询
   - 限制查询频率，避免过度查询

4. **改进异常处理**：
   - 使用try-finally确保连接在使用后正确关闭
   - 即使发生异常，也要确保连接被释放

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 在实时更新场景下，系统运行1小时后，内存使用增长不超过初始内存的10%
- **SC-002**: 每次update_bar()调用时，旧的QPicture对象应该在100毫秒内被释放
- **SC-003**: 系统运行24小时后，内存使用应该保持稳定，不应该有持续增长趋势
- **SC-004**: 在开盘价频繁变化的情况下（每秒更新），系统应该能够正确处理而不导致资源泄漏
- **SC-005**: 所有ChartItem的QPicture对象在窗口关闭时应该100%被释放
- **SC-006**: 资源释放操作不应该导致绘制性能下降超过5%
- **SC-007**: 系统应该通过内存泄漏检测工具（如valgrind、Application Verifier）的检测，无资源泄漏报告
- **SC-008**: 系统运行1小时后，数据库连接数应该保持稳定，不应该持续增长
- **SC-009**: 系统运行1小时后，富途OpenAPI连接数不应该超过128，不应该出现"连接数超过128"的错误
- **SC-010**: 实时修正开盘价的数据库查询应该使用连接池，每次查询不应该创建新连接
- **SC-011**: 实时修正开盘价的Datafeed查询应该复用现有实例，不应该频繁创建新实例
- **SC-012**: 系统应该能够识别并记录连接数超过限制的具体原因（数据库连接还是富途OpenAPI连接）

