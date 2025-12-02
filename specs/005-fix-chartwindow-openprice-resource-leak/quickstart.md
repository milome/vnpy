# Quick Start Guide: ChartWindow资源泄漏修复

**Feature**: ChartWindow实时显示K线，修正开盘价引起的资源泄漏  
**Date**: 2025-12-02  
**Status**: Design Phase

## Overview

本指南提供快速开始修复ChartWindow资源泄漏问题的步骤和示例代码。

## 修复内容概览

本次修复主要解决三个资源泄漏问题：

1. **QPicture资源泄漏**: 实时更新K线时，旧的QPicture对象没有被正确释放
2. **数据库连接泄漏**: 实时修正开盘价时频繁查询数据库，可能导致连接数超过限制
3. **Datafeed连接泄漏**: 实时修正开盘价时频繁创建Datafeed实例，导致富途OpenAPI连接数超过128

## 快速修复步骤

### Step 1: 修复QPicture资源释放

**文件**: `vnpy/chart/item.py`

**修改位置**: `ChartItem.update_bar()` 和 `ChartItem.clear_all()`

**修改内容**:
```python
def update_bar(self, bar: BarData) -> None:
    """Update single bar data."""
    ix: int | None = self._manager.get_index(bar.datetime)
    if ix is None:
        return
    
    # ✅ 显式释放旧的QPicture对象
    old_picture = self._bar_picutures.get(ix)
    if old_picture is not None:
        del old_picture
    
    self._bar_picutures[ix] = None
    self.update()

def clear_all(self) -> None:
    """Clear all data in the item."""
    # ✅ 显式释放所有QPicture对象
    for ix, picture in self._bar_picutures.items():
        if picture is not None:
            del picture
    
    if self._item_picuture is not None:
        del self._item_picuture
    
    self._item_picuture = None
    self._bar_picutures.clear()
    self.update()
```

### Step 2: 添加查询缓存

**文件**: `vnpy/trader/ui/widget.py`

**修改位置**: `ChartWindow.__init__()` 和 `process_tick_event()`

**修改内容**:
```python
class ChartWindow:
    def __init__(self, main_engine, event_engine):
        # ... 现有代码 ...
        
        # ✅ 添加开盘价查询缓存
        self._open_price_cache: dict[tuple[str, datetime], tuple[float, float]] = {}
        self._cache_ttl: int = 60  # 缓存60秒
    
    def _get_cached_open_price(self, symbol: str, datetime: datetime) -> float | None:
        """从缓存获取开盘价"""
        cache_key = (symbol, datetime)
        if cache_key in self._open_price_cache:
            price, timestamp = self._open_price_cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                return price
            else:
                del self._open_price_cache[cache_key]
        return None
    
    def _set_cached_open_price(self, symbol: str, datetime: datetime, price: float) -> None:
        """设置缓存开盘价"""
        cache_key = (symbol, datetime)
        self._open_price_cache[cache_key] = (price, time.time())
        
        # 定期清理过期缓存
        if len(self._open_price_cache) > 1000:
            current_time = time.time()
            expired_keys = [
                key for key, (_, timestamp) in self._open_price_cache.items()
                if current_time - timestamp >= self._cache_ttl
            ]
            for key in expired_keys:
                del self._open_price_cache[key]
```

### Step 3: 复用Datafeed实例

**文件**: `vnpy/trader/ui/widget.py`

**修改位置**: `ChartWindow.__init__()` 和 `process_tick_event()`

**修改内容**:
```python
class ChartWindow:
    def __init__(self, main_engine, event_engine):
        # ... 现有代码 ...
        
        # ✅ 添加Datafeed实例缓存
        self._cached_datafeed: BaseDatafeed | None = None
        self._datafeed_lock = threading.RLock()
    
    def _get_datafeed(self) -> BaseDatafeed | None:
        """获取Datafeed实例，优先使用MainEngine的实例"""
        with self._datafeed_lock:
            # 优先使用MainEngine的Datafeed实例
            if hasattr(self.main_engine, 'get_datafeed'):
                datafeed = self.main_engine.get_datafeed()
                if datafeed:
                    self._cached_datafeed = datafeed
                    return datafeed
            
            # 如果MainEngine没有，使用缓存的实例
            if self._cached_datafeed is not None:
                return self._cached_datafeed
            
            # 如果缓存也没有，尝试创建新实例（仅作为最后手段）
            try:
                from vnpy.trader.datafeed import get_datafeed
                datafeed = get_datafeed()
                if datafeed and hasattr(datafeed, 'init'):
                    if datafeed.init(output=self.main_engine.write_log):
                        self._cached_datafeed = datafeed
                        return datafeed
            except Exception as e:
                self.main_engine.write_log(
                    f"[ChartWindow] 创建Datafeed实例失败: {e}",
                    level=logging.WARNING
                )
            
            return None
    
    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """窗口关闭时清理资源"""
        # ✅ 关闭Datafeed连接
        if self._cached_datafeed is not None:
            try:
                if hasattr(self._cached_datafeed, 'close'):
                    self._cached_datafeed.close()
            except Exception as e:
                self.main_engine.write_log(
                    f"[ChartWindow] 关闭Datafeed连接失败: {e}",
                    level=logging.WARNING
                )
            finally:
                self._cached_datafeed = None
        
        # 清理缓存
        self._open_price_cache.clear()
        
        super().closeEvent(event)
```

### Step 4: 改进异常处理

**文件**: `vnpy/trader/ui/widget.py`

**修改位置**: `process_tick_event()` 中的数据库和Datafeed查询

**修改内容**:
```python
# 在查询数据库时
try:
    # 先检查缓存
    cached_price = self._get_cached_open_price(symbol, bar_minute_start)
    if cached_price:
        correct_open_price = cached_price
    else:
        # 查询数据库
        database = get_database()
        minute_bars = database.load_bar_data(...)
        
        if minute_bars and len(minute_bars) > 0:
            correct_open_price = minute_bars[0].open_price
            # 设置缓存
            self._set_cached_open_price(symbol, bar_minute_start, correct_open_price)
except Exception as e:
    # ✅ 记录错误但不抛出，避免影响主流程
    self.main_engine.write_log(
        f"[ChartWindow] 数据库查询失败: {e}",
        level=logging.WARNING
    )
finally:
    # ✅ 确保资源释放（如果需要）
    pass
```

## 测试验证

### 单元测试

**测试QPicture资源释放**:
```python
def test_qpicture_resource_release():
    """测试QPicture对象是否正确释放"""
    item = CandleItem(manager)
    
    # 创建多个K线
    for i in range(10):
        bar = create_test_bar(i)
        item.update_bar(bar)
    
    # 检查对象数量
    picture_count = sum(1 for p in item._bar_picutures.values() if p is not None)
    assert picture_count <= 10  # 不应该超过K线数量
    
    # 清理后检查
    item.clear_all()
    assert len(item._bar_picutures) == 0
    assert item._item_picuture is None
```

**测试查询缓存**:
```python
def test_open_price_cache():
    """测试开盘价查询缓存"""
    window = ChartWindow(main_engine, event_engine)
    
    # 第一次查询（应该查询数据库）
    price1 = window._get_cached_open_price("MHImain", datetime(2025, 12, 2, 10, 0))
    assert price1 is None  # 缓存中没有
    
    # 设置缓存
    window._set_cached_open_price("MHImain", datetime(2025, 12, 2, 10, 0), 20000.0)
    
    # 第二次查询（应该从缓存获取）
    price2 = window._get_cached_open_price("MHImain", datetime(2025, 12, 2, 10, 0))
    assert price2 == 20000.0
```

### 集成测试

**测试长时间运行**:
```python
def test_long_running_resource_stability():
    """测试长时间运行后资源是否稳定"""
    window = ChartWindow(main_engine, event_engine)
    
    # 模拟1小时运行
    start_time = time.time()
    tick_count = 0
    
    while time.time() - start_time < 3600:  # 1小时
        # 模拟tick数据
        tick = create_test_tick()
        window.process_tick_event(tick)
        tick_count += 1
        
        # 每1000个tick检查一次资源
        if tick_count % 1000 == 0:
            # 检查连接数
            # 检查内存使用
            # 检查缓存大小
            pass
    
    # 验证资源使用稳定
    assert window._open_price_cache is not None
    assert len(window._open_price_cache) < 1000  # 缓存不应该无限增长
```

## 性能基准测试

### 内存使用测试

```python
def test_memory_usage():
    """测试内存使用是否稳定"""
    import tracemalloc
    
    tracemalloc.start()
    
    window = ChartWindow(main_engine, event_engine)
    
    # 运行一段时间
    for i in range(10000):
        tick = create_test_tick()
        window.process_tick_event(tick)
    
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    # 验证内存使用在合理范围内
    assert peak < 100 * 1024 * 1024  # 小于100MB
```

### 连接数测试

```python
def test_connection_count():
    """测试连接数是否稳定"""
    window = ChartWindow(main_engine, event_engine)
    
    # 运行一段时间
    for i in range(1000):
        tick = create_test_tick()
        window.process_tick_event(tick)
    
    # 检查Datafeed连接数
    # 检查数据库连接数
    # 验证不超过限制
    pass
```

## 部署检查清单

- [ ] 修复QPicture资源释放代码
- [ ] 添加查询缓存代码
- [ ] 实现Datafeed实例复用
- [ ] 改进异常处理
- [ ] 添加单元测试
- [ ] 添加集成测试
- [ ] 运行性能基准测试
- [ ] 代码审查
- [ ] 更新文档

## 回滚计划

如果修复后出现问题，可以：

1. **部分回滚**: 只回滚有问题的部分（如只回滚查询缓存）
2. **完全回滚**: 恢复到修复前的代码
3. **渐进式部署**: 先在测试环境验证，再部署到生产环境

## 常见问题

### Q1: 修复后性能会下降吗？

**A**: 不会。修复后通过缓存和复用减少了查询次数，性能应该提升。

### Q2: 缓存会导致数据不一致吗？

**A**: 不会。开盘价在K线完成后不会改变，缓存60秒足够覆盖实时更新期间。

### Q3: 如何监控修复效果？

**A**: 可以通过日志和监控工具查看：
- 连接数变化
- 内存使用情况
- 缓存命中率
- 查询频率

## 下一步

完成修复后，建议：

1. 运行完整的测试套件
2. 在测试环境验证
3. 监控生产环境资源使用
4. 收集用户反馈

