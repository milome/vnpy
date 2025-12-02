# Data Model Design: ChartWindow资源泄漏修复

**Feature**: ChartWindow实时显示K线，修正开盘价引起的资源泄漏  
**Date**: 2025-12-02  
**Status**: Design Phase

## Overview

本文档定义了修复资源泄漏所需的数据模型和数据结构。主要包括：
1. QPicture资源管理模型
2. 数据库连接管理模型
3. Datafeed连接管理模型
4. 查询缓存模型

## 1. QPicture资源管理模型

### 1.1 ChartItem资源管理

**类**: `ChartItem` (位于 `vnpy/chart/item.py`)

**当前状态**:
```python
class ChartItem:
    def __init__(self):
        self._bar_picutures: dict[int, QtGui.QPicture | None] = {}
        self._item_picuture: QtGui.QPicture | None = None
    
    def update_bar(self, bar: BarData) -> None:
        ix = self._manager.get_index(bar.datetime)
        self._bar_picutures[ix] = None  # ⚠️ 没有释放旧对象
        self.update()
```

**修复后的设计**:
```python
class ChartItem:
    def __init__(self):
        self._bar_picutures: dict[int, QtGui.QPicture | None] = {}
        self._item_picuture: QtGui.QPicture | None = None
    
    def update_bar(self, bar: BarData) -> None:
        """Update single bar data with explicit resource release."""
        ix = self._manager.get_index(bar.datetime)
        if ix is None:
            return
        
        # ✅ 显式释放旧的QPicture对象
        old_picture = self._bar_picutures.get(ix)
        if old_picture is not None:
            # 显式删除引用，触发Python垃圾回收
            del old_picture
        
        self._bar_picutures[ix] = None
        self.update()
    
    def clear_all(self) -> None:
        """Clear all data with explicit resource release."""
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

**数据结构**:
- `_bar_picutures: dict[int, QtGui.QPicture | None]` - K线绘图对象缓存
  - Key: `int` - K线索引
  - Value: `QtGui.QPicture | None` - 绘图对象或None
- `_item_picuture: QtGui.QPicture | None` - 整体绘图对象

**生命周期**:
1. 创建: 在`_draw_bar_picture()`中创建新的QPicture对象
2. 缓存: 存储在`_bar_picutures`字典中
3. 更新: 在`update_bar()`中释放旧对象，创建新对象
4. 清理: 在`clear_all()`中释放所有对象

## 2. 数据库连接管理模型

### 2.1 查询缓存模型

**类**: `ChartWindow` (位于 `vnpy/trader/ui/widget.py`)

**新增数据结构**:
```python
class ChartWindow:
    def __init__(self):
        # ✅ 开盘价查询缓存
        # 格式: (symbol: str, datetime: datetime) -> (open_price: float, timestamp: float)
        self._open_price_cache: dict[tuple[str, datetime], tuple[float, float]] = {}
        self._cache_ttl: int = 60  # 缓存TTL：60秒
```

**缓存键设计**:
- Key: `(symbol: str, datetime: datetime)` - 合约代码和K线时间
- Value: `(open_price: float, timestamp: float)` - 开盘价和缓存时间戳

**缓存操作**:
```python
def _get_cached_open_price(self, symbol: str, datetime: datetime) -> float | None:
    """从缓存获取开盘价"""
    cache_key = (symbol, datetime)
    if cache_key in self._open_price_cache:
        price, timestamp = self._open_price_cache[cache_key]
        if time.time() - timestamp < self._cache_ttl:
            return price
        else:
            # 缓存过期，删除
            del self._open_price_cache[cache_key]
    return None

def _set_cached_open_price(self, symbol: str, datetime: datetime, price: float) -> None:
    """设置缓存开盘价"""
    cache_key = (symbol, datetime)
    self._open_price_cache[cache_key] = (price, time.time())
    
    # 定期清理过期缓存（可选）
    if len(self._open_price_cache) > 1000:
        self._clean_expired_cache()
```

**缓存清理策略**:
- TTL过期: 自动删除过期缓存
- 大小限制: 超过1000条时清理最旧的缓存
- 窗口关闭: 清空所有缓存

## 3. Datafeed连接管理模型

### 3.1 Datafeed实例缓存

**类**: `ChartWindow` (位于 `vnpy/trader/ui/widget.py`)

**新增数据结构**:
```python
class ChartWindow:
    def __init__(self):
        # ✅ Datafeed实例缓存
        self._cached_datafeed: BaseDatafeed | None = None
        self._datafeed_lock = threading.RLock()  # 线程安全锁
```

**实例获取逻辑**:
```python
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
```

**生命周期管理**:
```python
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
    
    # 调用父类方法
    super().closeEvent(event)
```

## 4. 异常处理模型

### 4.1 数据库查询异常处理

**设计模式**: try-finally确保资源释放

```python
def _query_database_for_open_price(
    self, 
    symbol: str, 
    exchange: Exchange, 
    bar_minute_start: datetime
) -> float | None:
    """从数据库查询开盘价，确保异常时正确关闭连接"""
    database = None
    try:
        from vnpy.trader.database import get_database
        database = get_database()
        
        minute_bars = database.load_bar_data(
            symbol,
            exchange,
            Interval.MINUTE,
            bar_minute_start,
            bar_minute_start
        )
        
        if minute_bars and len(minute_bars) > 0:
            minute_bar = minute_bars[0]
            if minute_bar.open_price > 0:
                return minute_bar.open_price
        
        return None
    except Exception as e:
        # ✅ 记录错误但不抛出，避免影响主流程
        self.main_engine.write_log(
            f"[ChartWindow] 数据库查询失败: {symbol}.{exchange.value} "
            f"时间: {bar_minute_start.strftime('%H:%M')}, 错误: {e}",
            level=logging.WARNING
        )
        return None
    finally:
        # ✅ 如果数据库实现需要显式关闭连接，在这里关闭
        # 注意：大多数数据库实现会自动管理连接，这里主要是确保异常处理正确
        pass
```

### 4.2 Datafeed查询异常处理

```python
def _query_datafeed_for_open_price(
    self,
    symbol: str,
    exchange: Exchange,
    bar_minute_start: datetime,
    minute_end: datetime
) -> float | None:
    """从Datafeed查询开盘价，确保异常时正确关闭连接"""
    datafeed = None
    try:
        datafeed = self._get_datafeed()
        if not datafeed:
            return None
        
        from vnpy.trader.object import HistoryRequest
        req = HistoryRequest(
            symbol=symbol,
            exchange=exchange,
            interval=Interval.TICK,
            start=bar_minute_start,
            end=minute_end
        )
        
        ticks = datafeed.query_tick_history(req, output=self.main_engine.write_log)
        
        if ticks:
            ticks.sort(key=lambda x: x.datetime)
            first_tick = ticks[0]
            if first_tick.last_price > 0:
                return first_tick.last_price
        
        return None
    except Exception as e:
        # ✅ 记录错误但不抛出
        self.main_engine.write_log(
            f"[ChartWindow] Datafeed查询失败: {symbol}.{exchange.value} "
            f"时间: {bar_minute_start.strftime('%H:%M')}, 错误: {e}",
            level=logging.WARNING
        )
        return None
    finally:
        # ✅ Datafeed实例由缓存管理，不需要在这里关闭
        # 但确保异常不会影响后续查询
        pass
```

## 5. 数据流模型

### 5.1 实时K线更新流程

```
Tick数据到达
    ↓
process_tick_event()
    ↓
BarGenerator生成/更新K线
    ↓
判断是否需要修正开盘价 (tick.second > 0)
    ↓
按优先级查找参照物:
    1. 保存的删除K线开盘价 (内存)
    2. 历史数据中的K线 (内存)
    3. 数据库中的K线 (数据库查询 + 缓存)
    4. 数据库中的tick数据 (数据库查询 + 缓存)
    5. Datafeed的tick数据 (Datafeed查询 + 缓存)
    ↓
如果找到参照物，修正开盘价
    ↓
update_bar() → ChartItem.update_bar()
    ↓
显式释放旧的QPicture对象
    ↓
创建新的QPicture对象
    ↓
更新图表显示
```

### 5.2 资源释放流程

```
窗口关闭 / 切换合约
    ↓
closeEvent() / 清理方法
    ↓
清理Datafeed连接
    ↓
清理查询缓存
    ↓
ChartItem.clear_all()
    ↓
显式释放所有QPicture对象
    ↓
清空所有缓存字典
```

## 6. 性能优化模型

### 6.1 缓存命中率优化

**缓存策略**:
- TTL: 60秒（开盘价在K线完成后不会改变）
- 大小限制: 1000条（避免内存过度占用）
- 清理策略: LRU（最近最少使用）

**预期效果**:
- 缓存命中率: > 90%（相同时间的查询会被缓存）
- 查询减少: 从每秒10次减少到每秒1次以下
- 连接数减少: 显著减少数据库和Datafeed连接使用

### 6.2 连接复用优化

**Datafeed连接复用**:
- 使用MainEngine的Datafeed实例（如果存在）
- 在ChartWindow中缓存实例
- 避免频繁创建新实例

**预期效果**:
- Datafeed连接数: 从可能的多实例减少到1个
- 富途OpenAPI连接数: 保持在安全范围内（< 128）

## 7. 线程安全模型

### 7.1 线程安全考虑

**Datafeed实例访问**:
- 使用`threading.RLock()`保护实例访问
- 确保多线程环境下的安全性

**缓存访问**:
- Python字典操作是原子的（GIL保护）
- 不需要额外的锁机制

**QPicture对象**:
- Qt对象在主线程创建和使用
- 通过Qt信号槽机制确保线程安全

## 8. 数据一致性模型

### 8.1 缓存一致性

**缓存更新策略**:
- 写入时更新: 查询到新数据时更新缓存
- TTL过期: 缓存60秒后自动过期
- 手动清理: 窗口关闭或切换合约时清理

**数据准确性**:
- 开盘价在K线完成后不会改变
- 缓存60秒足够覆盖实时更新期间
- 如果数据已过期，重新查询确保准确性

## 9. 错误处理模型

### 9.1 错误分类

**可恢复错误**:
- 数据库查询失败: 记录日志，继续使用BarGenerator的开盘价
- Datafeed查询失败: 记录日志，继续使用BarGenerator的开盘价
- 缓存查询失败: 重新查询数据库/Datafeed

**不可恢复错误**:
- 连接数超过限制: 记录错误，停止创建新连接
- 内存不足: 清理缓存，记录警告

### 9.2 错误恢复策略

**连接失败恢复**:
- 数据库连接失败: 使用BarGenerator的开盘价（可能不准确但可用）
- Datafeed连接失败: 使用BarGenerator的开盘价
- 连接数超限: 清理旧连接，等待后重试

**资源泄漏恢复**:
- 定期检查连接数，超过阈值时清理
- 窗口关闭时强制清理所有资源

## 10. 监控和日志模型

### 10.1 监控指标

**资源使用监控**:
- QPicture对象数量
- 数据库连接数
- Datafeed连接数
- 缓存大小

**性能监控**:
- 查询频率
- 缓存命中率
- 资源释放时间

### 10.2 日志记录

**日志级别**:
- INFO: 正常操作（资源释放、缓存命中）
- WARNING: 可恢复错误（查询失败、连接超限）
- ERROR: 不可恢复错误（内存不足、连接泄漏）

**日志内容**:
- 资源释放操作
- 连接创建/关闭
- 缓存操作
- 异常信息

## 11. 总结

### 11.1 数据模型要点

1. **QPicture资源管理**: 显式释放旧对象，避免内存泄漏
2. **查询缓存**: 减少重复查询，降低连接使用
3. **Datafeed实例复用**: 避免频繁创建新连接
4. **异常处理**: 确保异常时资源正确释放
5. **线程安全**: 使用锁保护共享资源
6. **监控日志**: 记录关键操作和错误

### 11.2 设计原则

- **最小化修改**: 只修改必要的代码，保持向后兼容
- **性能优先**: 缓存和复用减少资源使用
- **健壮性**: 异常处理确保系统稳定
- **可观测性**: 日志和监控便于问题诊断

