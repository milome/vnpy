# API Contract: ChartWindow Connection Management

**Feature**: ChartWindow实时显示K线，修正开盘价引起的资源泄漏  
**Date**: 2025-12-02  
**Component**: `vnpy/trader/ui/widget.py`

## Overview

定义ChartWindow连接管理的API契约，确保数据库和Datafeed连接正确管理。

## Class: ChartWindow

### Method: _get_datafeed

**Signature**:
```python
def _get_datafeed(self) -> BaseDatafeed | None
```

**Preconditions**:
- `self.main_engine` is not None
- Thread-safe access (protected by `self._datafeed_lock`)

**Postconditions**:
- Returns cached Datafeed instance (if available)
- Or returns MainEngine's Datafeed instance (if available)
- Or creates and caches new instance (as last resort)
- Returns None if all attempts fail

**Side Effects**:
- May create and initialize new Datafeed instance
- May cache Datafeed instance in `self._cached_datafeed`

**Exceptions**:
- Catches and logs exceptions, does not raise

**Contract**:
```python
def _get_datafeed(self) -> BaseDatafeed | None:
    """
    Get Datafeed instance with connection reuse.
    
    Contract:
    1. Thread-safe access (use lock)
    2. Priority order:
       a. MainEngine's Datafeed instance (if exists)
       b. Cached instance (if exists)
       c. New instance (create and cache)
    3. Return None if all attempts fail
    4. Never raise exceptions
    """
    with self._datafeed_lock:  # ✅ Contract: Thread-safe
        # Contract: Try MainEngine first
        if hasattr(self.main_engine, 'get_datafeed'):
            datafeed = self.main_engine.get_datafeed()
            if datafeed:
                self._cached_datafeed = datafeed
                return datafeed
        
        # Contract: Use cached instance
        if self._cached_datafeed is not None:
            return self._cached_datafeed
        
        # Contract: Create new instance as last resort
        try:
            from vnpy.trader.datafeed import get_datafeed
            datafeed = get_datafeed()
            if datafeed and hasattr(datafeed, 'init'):
                if datafeed.init(output=self.main_engine.write_log):
                    self._cached_datafeed = datafeed
                    return datafeed
        except Exception as e:
            # Contract: Log but don't raise
            self.main_engine.write_log(
                f"[ChartWindow] 创建Datafeed实例失败: {e}",
                level=logging.WARNING
            )
        
        return None
```

### Method: _get_cached_open_price

**Signature**:
```python
def _get_cached_open_price(self, symbol: str, datetime: datetime) -> float | None
```

**Preconditions**:
- `symbol` is not None and not empty
- `datetime` is valid datetime object
- `self._open_price_cache` is initialized

**Postconditions**:
- Returns cached price if exists and not expired
- Returns None if not cached or expired
- Expired entries are removed from cache

**Side Effects**:
- May remove expired cache entries

**Exceptions**:
- None

**Contract**:
```python
def _get_cached_open_price(self, symbol: str, datetime: datetime) -> float | None:
    """
    Get cached open price with TTL check.
    
    Contract:
    1. Build cache key from (symbol, datetime)
    2. Check if key exists in cache
    3. If exists, check TTL
    4. If valid, return price
    5. If expired, remove entry and return None
    6. If not exists, return None
    """
    cache_key = (symbol, datetime)
    if cache_key in self._open_price_cache:
        price, timestamp = self._open_price_cache[cache_key]
        if time.time() - timestamp < self._cache_ttl:
            return price  # ✅ Contract: Valid cache
        else:
            del self._open_price_cache[cache_key]  # ✅ Contract: Remove expired
    return None
```

### Method: _set_cached_open_price

**Signature**:
```python
def _set_cached_open_price(self, symbol: str, datetime: datetime, price: float) -> None
```

**Preconditions**:
- `symbol` is not None and not empty
- `datetime` is valid datetime object
- `price` is positive float

**Postconditions**:
- Cache entry is added or updated
- Cache size is checked and cleaned if needed

**Side Effects**:
- Adds or updates cache entry
- May trigger cache cleanup if size exceeds limit

**Exceptions**:
- None

**Contract**:
```python
def _set_cached_open_price(self, symbol: str, datetime: datetime, price: float) -> None:
    """
    Set cached open price with automatic cleanup.
    
    Contract:
    1. Build cache key from (symbol, datetime)
    2. Store (price, timestamp) in cache
    3. If cache size > 1000, clean expired entries
    """
    cache_key = (symbol, datetime)
    self._open_price_cache[cache_key] = (price, time.time())
    
    # Contract: Auto-cleanup if cache too large
    if len(self._open_price_cache) > 1000:
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self._open_price_cache.items()
            if current_time - timestamp >= self._cache_ttl
        ]
        for key in expired_keys:
            del self._open_price_cache[key]
```

### Method: closeEvent

**Signature**:
```python
def closeEvent(self, event: QtGui.QCloseEvent) -> None
```

**Preconditions**:
- Window is being closed
- `event` is valid QCloseEvent

**Postconditions**:
- Datafeed connection is closed (if exists)
- All caches are cleared
- Parent closeEvent is called

**Side Effects**:
- Datafeed instance is closed
- Cache dictionaries are cleared
- Resources are released

**Exceptions**:
- Catches and logs exceptions during cleanup

**Contract**:
```python
def closeEvent(self, event: QtGui.QCloseEvent) -> None:
    """
    Clean up resources on window close.
    
    Contract:
    1. Close Datafeed connection (if exists)
    2. Clear all caches
    3. Call parent closeEvent
    4. Never raise exceptions
    """
    # Contract: Close Datafeed connection
    if self._cached_datafeed is not None:
        try:
            if hasattr(self._cached_datafeed, 'close'):
                self._cached_datafeed.close()  # ✅ Contract: Explicit close
        except Exception as e:
            # Contract: Log but don't raise
            self.main_engine.write_log(
                f"[ChartWindow] 关闭Datafeed连接失败: {e}",
                level=logging.WARNING
            )
        finally:
            self._cached_datafeed = None
    
    # Contract: Clear all caches
    self._open_price_cache.clear()
    
    # Contract: Call parent
    super().closeEvent(event)
```

## Testing Contract

### Test: get_datafeed_reuses_mainengine_instance

**Given**: MainEngine has Datafeed instance  
**When**: _get_datafeed() is called  
**Then**: Returns MainEngine's instance, caches it

### Test: get_datafeed_caches_new_instance

**Given**: MainEngine has no Datafeed instance  
**When**: _get_datafeed() is called  
**Then**: Creates, initializes, and caches new instance

### Test: open_price_cache_ttl

**Given**: Cached open price with timestamp  
**When**: _get_cached_open_price() is called after TTL expires  
**Then**: Returns None, removes expired entry

### Test: closeevent_cleans_resources

**Given**: ChartWindow with cached Datafeed and cache entries  
**When**: closeEvent() is called  
**Then**: Datafeed is closed, caches are cleared

## Performance Contract

- **Connection Reuse**: Datafeed instance should be reused across multiple queries
- **Cache Hit Rate**: Open price cache hit rate should be > 90%
- **Resource Cleanup**: All resources should be cleaned within 1 second of window close
- **Thread Safety**: _get_datafeed() should be thread-safe

## Error Handling Contract

- **Datafeed Creation Failure**: Log warning, return None, don't raise
- **Datafeed Close Failure**: Log warning, continue cleanup, don't raise
- **Cache Operations**: Never raise exceptions, handle gracefully

