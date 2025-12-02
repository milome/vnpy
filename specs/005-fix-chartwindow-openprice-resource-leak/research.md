# Phase 0: Research & Investigation

**Feature**: ChartWindow实时显示K线，修正开盘价引起的资源泄漏  
**Date**: 2025-12-02  
**Status**: In Progress

## Research Objectives

1. 调查和确认资源泄漏的具体原因
2. 分析QPicture对象的生命周期管理
3. 检查数据库实现是否使用连接池
4. 分析Datafeed连接管理机制
5. 统计查询频率，确定是否需要限制

## 1. QPicture资源泄漏分析

### 1.1 当前实现

**位置**: `vnpy/chart/item.py`

**代码分析**:

```python
def update_bar(self, bar: BarData) -> None:
    """Update single bar data."""
    ix: int | None = self._manager.get_index(bar.datetime)
    if ix is None:
        return
    
    self._bar_picutures[ix] = None  # ⚠️ 只是设置为None，没有显式释放
    self.update()
```

**问题**:
- `QPicture` 是Qt的C++对象，通过Python绑定使用
- 仅仅将Python引用设置为`None`，C++对象可能不会立即释放
- 在实时更新场景下，频繁调用`update_bar()`会导致大量QPicture对象累积

### 1.2 QPicture生命周期

**Qt文档说明**:
- `QPicture` 继承自 `QPaintDevice`，是C++对象
- Python绑定使用引用计数管理，但C++对象可能需要显式释放
- 在PyQt中，对象销毁依赖于Python的垃圾回收机制

**最佳实践**:
- 对于频繁创建和销毁的Qt对象，应该显式调用清理方法
- 或者使用上下文管理器确保资源释放

### 1.3 解决方案研究

**方案1: 显式释放QPicture对象**
```python
def update_bar(self, bar: BarData) -> None:
    ix: int | None = self._manager.get_index(bar.datetime)
    if ix is None:
        return
    
    # 显式释放旧的QPicture对象
    old_picture = self._bar_picutures.get(ix)
    if old_picture is not None:
        # QPicture在Python中会自动管理，但可以显式删除引用
        del old_picture
    
    self._bar_picutures[ix] = None
    self.update()
```

**方案2: 使用弱引用**
- 使用`weakref`管理QPicture对象
- 允许对象在不再需要时自动释放

**方案3: 批量释放**
- 在`clear_all()`中确保所有对象被释放
- 使用`del`显式删除引用

**推荐方案**: 方案1 + 方案3组合
- 在`update_bar()`中显式释放旧对象
- 在`clear_all()`中确保所有对象被释放
- 简单直接，不需要引入新的依赖

## 2. 数据库连接泄漏分析

### 2.1 当前实现

**位置**: `vnpy/trader/database.py` 和 `vnpy/trader/ui/widget.py`

**代码分析**:

```python
# widget.py - 实时修正开盘价
database = get_database()  # 获取单例数据库对象
minute_bars = database.load_bar_data(...)  # 查询数据库
```

**`get_database()`实现**:
```python
database: BaseDatabase | None = None

def get_database() -> BaseDatabase:
    global database
    if database:
        return database
    
    # 创建数据库对象
    database = module.Database()
    return database
```

**问题**:
- `get_database()`返回单例对象，但具体实现（如`vnpy_sqlite`, `vnpy_mysql`）的连接管理方式未知
- 如果具体实现没有使用连接池，每次查询可能创建新连接
- 异常发生时，连接可能没有被正确关闭

### 2.2 数据库实现检查

**需要检查的数据库实现**:
- `vnpy_sqlite`: SQLite数据库实现
- `vnpy_mysql`: MySQL数据库实现
- `vnpy_postgresql`: PostgreSQL数据库实现

**检查项**:
1. 是否使用连接池？
2. 每次查询是否创建新连接？
3. 异常处理是否正确关闭连接？
4. 是否有连接泄漏？

**SQLite特点**:
- SQLite是文件数据库，通常不需要连接池
- 但频繁打开/关闭文件句柄也可能导致资源问题

**MySQL/PostgreSQL特点**:
- 通常需要连接池管理
- 如果没有连接池，每次查询创建新连接会导致连接数快速增长

### 2.3 解决方案研究

**方案1: 检查现有实现，修复连接管理**
- 如果现有实现已有连接池，只需修复异常处理
- 如果现有实现没有连接池，需要添加

**方案2: 引入SQLAlchemy连接池**
- SQLAlchemy提供标准的连接池实现
- 支持多种数据库（MySQL, PostgreSQL等）
- 需要修改数据库实现代码

**方案3: 在ChartWindow层面缓存查询结果**
- 避免重复查询相同时间的数据
- 减少数据库查询次数
- 简单有效，不需要修改数据库实现

**推荐方案**: 方案3（查询缓存）+ 方案1（修复异常处理）
- 查询缓存可以显著减少查询次数
- 修复异常处理确保连接正确关闭
- 如果现有实现没有连接池，再考虑引入

## 3. Datafeed连接泄漏分析

### 3.1 当前实现

**位置**: `vnpy/trader/ui/widget.py` 和 `vnpy_futu/vnpy_futu/datafeed.py`

**代码分析**:

```python
# widget.py - 实时修正开盘价方法4.2
if datafeed is None:
    try:
        from vnpy_futu.datafeed import Datafeed as FutuDatafeed
        datafeed = FutuDatafeed()  # ⚠️ 每次创建新实例
        if not datafeed.init(output=self.main_engine.write_log):
            datafeed = None
    except Exception:
        pass
```

**FutuDatafeed实现**:
```python
class Datafeed(BaseDatafeed):
    def __init__(self) -> None:
        self.quote_ctx: OpenQuoteContext = None
        self.inited: bool = False
    
    def init(self, output: Callable = print) -> bool:
        # 先关闭旧连接
        if self.quote_ctx:
            self.quote_ctx.close()
            self.quote_ctx = None
        
        # 创建新连接
        self.quote_ctx = OpenQuoteContext(host=self.host, port=self.port)
        self.inited = True
        return True
```

**问题**:
- 每次创建新的`FutuDatafeed`实例都会创建新的`OpenQuoteContext`
- `OpenQuoteContext`会建立新的富途OpenAPI连接
- 如果实例没有被正确关闭，连接不会被释放
- 富途OpenAPI连接数限制为128，超过后无法建立新连接

### 3.2 连接管理分析

**富途OpenAPI连接限制**:
- 每个`OpenQuoteContext`实例占用1个连接
- 系统总连接数限制：128
- 连接必须显式关闭才能释放

**当前问题**:
- 在`widget.py`中创建的`FutuDatafeed`实例没有被保存
- 实例在方法结束后可能被垃圾回收，但连接可能没有正确关闭
- 频繁创建新实例导致连接数快速增长

### 3.3 解决方案研究

**方案1: 复用MainEngine的Datafeed实例**
```python
# 使用MainEngine的get_datafeed()方法
if hasattr(self.main_engine, 'get_datafeed'):
    datafeed = self.main_engine.get_datafeed()
```

**方案2: 在ChartWindow中缓存Datafeed实例**
```python
class ChartWindow:
    def __init__(self):
        self._cached_datafeed = None
    
    def _get_datafeed(self):
        if self._cached_datafeed is None:
            if hasattr(self.main_engine, 'get_datafeed'):
                self._cached_datafeed = self.main_engine.get_datafeed()
            else:
                # 创建新实例并缓存
                self._cached_datafeed = FutuDatafeed()
                self._cached_datafeed.init()
        return self._cached_datafeed
```

**方案3: 使用上下文管理器**
```python
with self._get_datafeed() as datafeed:
    ticks = datafeed.query_tick_history(req)
```

**推荐方案**: 方案1（优先）+ 方案2（备用）
- 优先使用MainEngine的Datafeed实例（如果存在）
- 如果不存在，在ChartWindow中缓存实例
- 确保实例在窗口关闭时正确关闭

## 4. 查询频率分析

### 4.1 当前查询逻辑

**触发条件**:
- 每次收到tick数据时，如果`tick.second > 0`（该分钟已开始）
- 会按优先级查找参照物：
  1. 保存的删除K线开盘价（不查询）
  2. 历史数据中的K线（不查询）
  3. 数据库中的K线（查询数据库）
  4. 数据库中的tick数据（查询数据库）
  5. Datafeed的tick数据（查询Datafeed）

**查询频率估算**:
- 如果每秒收到10个tick，且每个tick都触发查询
- 每秒可能执行10次数据库查询 + 10次Datafeed查询
- 1小时 = 3600秒 = 36,000次查询

**问题**:
- 相同时间的开盘价可能被重复查询
- 没有缓存机制，浪费资源
- 高频查询可能导致连接数快速增长

### 4.2 查询缓存方案

**方案1: 内存缓存**
```python
class ChartWindow:
    def __init__(self):
        # 缓存格式: (symbol, datetime) -> open_price
        self._open_price_cache: dict = {}
        self._cache_ttl: int = 60  # 缓存60秒
    
    def _get_cached_open_price(self, symbol, datetime):
        cache_key = (symbol, datetime)
        if cache_key in self._open_price_cache:
            price, timestamp = self._open_price_cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                return price
        return None
```

**方案2: 限制查询频率**
```python
class ChartWindow:
    def __init__(self):
        self._last_query_time: dict = {}  # (symbol, datetime) -> timestamp
        self._query_interval: float = 1.0  # 每秒最多查询1次
    
    def _should_query(self, symbol, datetime):
        cache_key = (symbol, datetime)
        last_time = self._last_query_time.get(cache_key, 0)
        if time.time() - last_time < self._query_interval:
            return False
        self._last_query_time[cache_key] = time.time()
        return True
```

**推荐方案**: 方案1（查询缓存）
- 缓存相同时间的开盘价查询结果
- 设置合理的TTL（如60秒）
- 简单有效，减少查询次数

## 5. 异常处理分析

### 5.1 当前异常处理

**代码分析**:
```python
try:
    database = get_database()
    minute_bars = database.load_bar_data(...)
except Exception as e:
    pass  # ⚠️ 异常时可能没有关闭连接
```

**问题**:
- 异常发生时，数据库连接可能没有被正确关闭
- Datafeed连接也可能没有被正确关闭
- 使用`pass`静默忽略异常，不利于调试

### 5.2 改进方案

**方案1: 使用try-finally确保连接关闭**
```python
try:
    database = get_database()
    minute_bars = database.load_bar_data(...)
except Exception as e:
    self.main_engine.write_log(f"数据库查询失败: {e}")
finally:
    # 如果数据库实现需要显式关闭连接，在这里关闭
    pass
```

**方案2: 使用上下文管理器**
```python
with database.get_connection() as conn:
    minute_bars = conn.load_bar_data(...)
```

**方案3: 改进异常处理，记录日志**
```python
try:
    database = get_database()
    minute_bars = database.load_bar_data(...)
except Exception as e:
    # 记录错误但不抛出，避免影响主流程
    self.main_engine.write_log(
        f"[实时K线] 数据库查询失败: {e}",
        level=logging.WARNING
    )
```

**推荐方案**: 方案1 + 方案3
- 使用try-finally确保资源释放
- 改进异常处理，记录日志便于调试
- 如果数据库实现支持上下文管理器，使用方案2

## 6. 技术选型总结

### 6.1 QPicture资源释放

**选型**: 显式释放 + 批量清理
- 在`update_bar()`中显式释放旧对象
- 在`clear_all()`中确保所有对象被释放
- 不需要引入新依赖

### 6.2 数据库连接管理

**选型**: 查询缓存 + 异常处理改进
- 添加查询缓存，减少重复查询
- 改进异常处理，确保连接正确关闭
- 如果现有实现没有连接池，再考虑引入SQLAlchemy

### 6.3 Datafeed连接管理

**选型**: 实例复用 + 生命周期管理
- 优先使用MainEngine的Datafeed实例
- 在ChartWindow中缓存实例
- 确保实例在窗口关闭时正确关闭

### 6.4 查询优化

**选型**: 内存缓存
- 缓存相同时间的开盘价查询结果
- 设置合理的TTL（60秒）
- 减少数据库和Datafeed查询次数

## 7. 待验证问题

### 7.1 连接数类型确认

**需要验证**:
- [ ] 错误日志中的"连接数超过128"是数据库连接还是富途OpenAPI连接？
- [ ] 查看完整错误堆栈，确定报错来源
- [ ] 监控两种连接数的变化

**验证方法**:
1. 添加连接数监控日志
2. 区分数据库连接和富途OpenAPI连接
3. 记录连接创建和关闭的时间点

### 7.2 数据库实现检查

**需要检查**:
- [ ] SQLite实现是否频繁打开/关闭文件？
- [ ] MySQL/PostgreSQL实现是否使用连接池？
- [ ] 异常处理是否正确关闭连接？

**检查方法**:
1. 查看`vnpy_sqlite`, `vnpy_mysql`等模块的源码
2. 检查`load_bar_data()`和`load_tick_data()`的实现
3. 测试异常情况下的连接管理

### 7.3 查询频率统计

**需要统计**:
- [ ] 实时修正开盘价时，每个tick是否都触发查询？
- [ ] 相同时间的查询是否重复执行？
- [ ] 查询频率是否在合理范围内？

**统计方法**:
1. 添加查询日志，记录每次查询的时间、参数
2. 分析日志，统计查询频率
3. 确定是否需要限制查询频率

## 8. 实施建议

### 8.1 优先级

**P1（高优先级）**:
1. 修复QPicture资源释放
2. 复用Datafeed实例，避免频繁创建
3. 改进异常处理，确保连接正确关闭

**P2（中优先级）**:
1. 添加查询缓存，减少重复查询
2. 检查数据库实现，修复连接管理
3. 添加连接数监控日志

### 8.2 实施步骤

1. **Phase 1**: 修复QPicture资源释放（最简单，风险最低）
2. **Phase 2**: 复用Datafeed实例（直接解决问题）
3. **Phase 3**: 添加查询缓存（优化性能）
4. **Phase 4**: 改进异常处理（提高健壮性）
5. **Phase 5**: 检查数据库实现（如果需要）

### 8.3 风险控制

**风险**:
- 修改可能影响现有功能
- 性能可能下降

**缓解措施**:
- 添加单元测试和集成测试
- 性能基准测试
- 代码审查
- 分阶段实施，逐步验证

## 9. 参考资料

- [Qt QPicture Documentation](https://doc.qt.io/qt-5/qpicture.html)
- [PyQt5/PyQt6 Memory Management](https://www.riverbankcomputing.com/static/Docs/PyQt5/)
- [SQLAlchemy Connection Pooling](https://docs.sqlalchemy.org/en/14/core/pooling.html)
- [富途OpenAPI文档](https://openapi.futunn.com/)
- Commit 1df34e3: 修复富途OpenAPI连接泄露问题

## 10. 结论

通过研究分析，确定了三个主要的资源泄漏问题：

1. **QPicture资源泄漏**: 需要显式释放旧对象
2. **数据库连接泄漏**: 需要添加查询缓存和改进异常处理
3. **Datafeed连接泄漏**: 需要复用实例，避免频繁创建

所有问题都有明确的解决方案，不需要引入重大架构变更。建议按照优先级分阶段实施，逐步验证修复效果。

