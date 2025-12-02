# 连接数超过128问题分析

**日期**: 2025-12-02  
**状态**: 待调查  
**相关Commit**: 1df34e3 (修复富途OpenAPI连接泄露问题)

---

## 问题描述

ChartWindow打开一段时间后无响应，日志显示"连接数超过128，无法建立新连接"。

### 问题表现

1. ChartWindow打开一段时间后无响应
2. 日志报错："连接数超过128，无法建立新连接"
3. 需要查清楚是什么连接数（数据库连接？富途OpenAPI连接？）
4. 需要查清楚是哪个服务或环节报错

---

## 问题分析

### 1. 连接数类型分析

根据Commit 1df34e3的修复，富途OpenAPI的连接数限制为128。但ChartWindow在实时修正开盘价时，可能存在以下连接泄漏：

#### 1.1 富途OpenAPI连接

**位置**: `vnpy/trader/ui/widget.py` - `process_tick_event` 方法（2852-2898行）

**问题**:
- 在实时修正开盘价的方法4.2中，如果找不到现有的datafeed，会创建新的`FutuDatafeed`实例
- 每次创建新实例都会建立新的富途OpenAPI连接
- 如果频繁创建而不关闭，会导致富途OpenAPI连接数超过128

**代码片段**:
```python
# 方法4.2：如果数据库没有，尝试从datafeed查询该分钟的tick数据
if not correct_open_price:
    try:
        datafeed = None
        if hasattr(self.main_engine, 'get_datafeed'):
            datafeed = self.main_engine.get_datafeed()
        
        # 如果没有现成的datafeed，尝试创建FUTU datafeed
        if datafeed is None:
            try:
                from vnpy_futu.datafeed import Datafeed as FutuDatafeed
                datafeed = FutuDatafeed()  # ⚠️ 每次创建新实例，建立新连接
                if not datafeed.init(output=self.main_engine.write_log):
                    datafeed = None
            except ImportError:
                pass
            except Exception:
                pass
```

**问题**:
- 每次tick更新时，如果该分钟已开始（tick.second > 0），都会尝试查询datafeed
- 如果找不到现有的datafeed，会创建新的`FutuDatafeed`实例
- 新实例会建立新的富途OpenAPI连接，但可能没有被正确关闭
- 长时间运行后，连接数会持续增长，最终超过128

#### 1.2 数据库连接

**位置**: `vnpy/trader/ui/widget.py` - `process_tick_event` 方法（2777-2807行，2826-2850行）

**问题**:
- 在实时修正开盘价的方法3中，会调用`database.load_bar_data()`查询数据库
- 在方法4.1中，会调用`database.load_tick_data()`查询数据库
- 如果每次查询都创建新连接而不关闭，会导致数据库连接数持续增长

**代码片段**:
```python
# 方法3：如果历史数据中没有，尝试从数据库加载该分钟的K线
if not correct_open_price:
    try:
        from vnpy.trader.database import get_database
        database = get_database()
        # ⚠️ 每次查询可能创建新连接
        minute_bars = database.load_bar_data(
            symbol,
            exchange,
            Interval.MINUTE,
            bar_minute_start,
            bar_minute_start
        )
    except Exception as e:
        # 数据库查询失败，忽略
        pass  # ⚠️ 异常时可能没有关闭连接
```

**问题**:
- 每次tick更新时，如果该分钟已开始，都会尝试查询数据库
- 如果数据库实现没有使用连接池，每次查询可能创建新连接
- 异常发生时，连接可能没有被正确关闭
- 长时间运行后，连接数会持续增长

---

## 需要调查的问题

### 1. 连接数类型

**问题**: 是数据库连接数还是富途OpenAPI连接数？

**调查方法**:
1. 查看错误日志的完整堆栈信息
2. 检查错误消息的来源（数据库驱动还是富途OpenAPI）
3. 监控两种连接数的变化

**可能的情况**:
- 如果是富途OpenAPI连接：错误消息应该是"连接个数超过128，请关闭无用连接"
- 如果是数据库连接：错误消息可能是"Too many connections"（MySQL）或其他数据库特定的错误

### 2. 报错来源

**问题**: 是哪个服务或环节报错？

**调查方法**:
1. 查看完整的错误堆栈
2. 检查错误发生时的上下文
3. 分析错误发生的时机（是否与实时修正开盘价相关）

**可能的情况**:
- 富途OpenAPI服务报错：在创建新的`FutuDatafeed`实例时
- 数据库服务报错：在执行数据库查询时
- 两者都有：如果两种连接都在泄漏

### 3. 查询频率

**问题**: 实时修正开盘价时，每个tick都会触发查询吗？

**调查方法**:
1. 添加日志记录每次查询
2. 统计查询频率
3. 分析查询触发条件

**当前逻辑**:
- 如果`tick.second > 0`，说明该分钟已开始，会尝试修正开盘价
- 修正开盘价时会按优先级查找参照物：
  1. 保存的删除K线开盘价（不查询）
  2. 历史数据中的K线（不查询）
  3. 数据库中的K线（查询数据库）
  4. 数据库中的tick数据（查询数据库）
  5. Datafeed的tick数据（查询Datafeed）

**问题**:
- 如果每个tick都触发查询，频率会非常高
- 没有查询缓存机制，相同时间的查询会重复执行
- 没有查询频率限制，可能导致过度查询

---

## 解决方案

### 方案1: 使用数据库连接池（推荐）

**目标**: 避免频繁创建数据库连接

**实现**:
1. 检查当前数据库实现是否使用连接池
2. 如果没有，考虑引入连接池（如SQLAlchemy的连接池）
3. 确保连接在使用后正确归还到池中

**优点**:
- 连接复用，减少连接创建开销
- 连接数可控，避免连接泄漏
- 提高性能

**缺点**:
- 需要修改数据库实现
- 可能需要引入新的依赖

### 方案2: 复用Datafeed实例（推荐）

**目标**: 避免频繁创建Datafeed实例

**实现**:
1. 在ChartWindow中缓存Datafeed实例
2. 使用MainEngine的`get_datafeed()`方法获取现有实例
3. 避免在每次查询时创建新实例

**优点**:
- 避免频繁创建富途OpenAPI连接
- 减少连接数增长
- 提高性能

**缺点**:
- 需要确保Datafeed实例的正确生命周期管理

### 方案3: 添加查询缓存

**目标**: 减少重复查询

**实现**:
1. 对于相同时间的开盘价查询，使用缓存
2. 限制查询频率，避免过度查询
3. 设置缓存过期时间

**优点**:
- 减少数据库和Datafeed查询次数
- 提高性能
- 减少连接使用

**缺点**:
- 需要管理缓存生命周期
- 可能占用内存

### 方案4: 改进异常处理

**目标**: 确保连接正确关闭

**实现**:
1. 使用try-finally确保连接在使用后正确关闭
2. 即使发生异常，也要确保连接被释放
3. 使用上下文管理器（context manager）管理连接

**优点**:
- 确保连接正确关闭
- 避免连接泄漏
- 提高代码健壮性

**缺点**:
- 需要修改现有代码
- 可能需要重构异常处理逻辑

---

## 实施建议

### 优先级

1. **P1**: 复用Datafeed实例（方案2）
   - 这是最直接的问题，富途OpenAPI连接数限制为128
   - 实现相对简单，影响范围小

2. **P1**: 改进异常处理（方案4）
   - 确保所有连接在使用后正确关闭
   - 这是基础保障，必须实施

3. **P2**: 使用数据库连接池（方案1）
   - 如果确认是数据库连接泄漏，需要实施
   - 可能需要较大的改动

4. **P2**: 添加查询缓存（方案3）
   - 减少查询次数，提高性能
   - 可以作为优化措施

### 实施步骤

1. **调查阶段**:
   - 添加连接数监控日志
   - 区分数据库连接和富途OpenAPI连接
   - 确定具体是哪种连接泄漏

2. **修复阶段**:
   - 根据调查结果，实施相应的解决方案
   - 优先修复最严重的问题

3. **验证阶段**:
   - 长时间运行测试
   - 监控连接数变化
   - 验证问题已解决

---

## 相关文件

- `vnpy/trader/ui/widget.py` - ChartWindow实现，包含实时修正开盘价逻辑
- `vnpy/trader/database.py` - 数据库接口定义
- `vnpy_futu/vnpy_futu/datafeed.py` - 富途Datafeed实现
- `specs/TBD-futud-latency-improvement/connection-leak-fix.md` - 富途OpenAPI连接泄漏修复文档

---

## 待办事项

- [ ] 添加连接数监控日志，区分数据库连接和富途OpenAPI连接
- [ ] 查看完整错误堆栈，确定报错来源
- [ ] 统计查询频率，分析是否需要限制
- [ ] 检查数据库实现是否使用连接池
- [ ] 实施Datafeed实例复用
- [ ] 改进异常处理，确保连接正确关闭
- [ ] 添加查询缓存机制
- [ ] 长时间运行测试，验证问题已解决

