# StaticInfo 缓存实现 TODO 清单

**目标**: 将 StaticInfo(3202) 延迟从 463.19ms 降至 <1ms  
**优先级**: P0  
**预计总耗时**: 2-3小时

---

## ✅ T1: 添加缓存字段（10分钟）

**文件**: `vnpy_futu/vnpy_futu/futu_gateway.py`  
**位置**: `__init__` 方法（约204行）

**任务**:
- [ ] 添加 `_static_info_cache: Dict[Tuple[str, str], Dict[str, Any]] = {}`
- [ ] 添加 `_static_info_cache_lock = RLock()`
- [ ] 添加 `_static_info_cache_ttl: int = 86400`（24小时）

---

## ✅ T2: 实现缓存查询方法（30分钟）

**文件**: `vnpy_futu/vnpy_futu/futu_gateway.py`  
**位置**: 在 `query_contract()` 方法之前（约1960行）

**任务**:
- [ ] 实现 `_get_stock_basicinfo_cached(market, product)` 方法
- [ ] 实现缓存检查逻辑（检查缓存是否存在且未过期）
- [ ] 实现缓存更新逻辑（查询远程后更新缓存）
- [ ] 添加日志输出（缓存命中/未命中）

**关键代码**:
```python
def _get_stock_basicinfo_cached(self, market: str, product: str) -> Optional[pd.DataFrame]:
    cache_key = (market, product)
    current_time = time()
    
    with self._static_info_cache_lock:
        # 检查缓存
        if cache_key in self._static_info_cache:
            cache_entry = self._static_info_cache[cache_key]
            if (current_time - cache_entry["cache_time"]) < self._static_info_cache_ttl:
                return cache_entry["data"].copy()
        
        # 查询远程并更新缓存
        ret, data = self.quote_ctx.get_stock_basicinfo(market, product)
        if ret == 0 and not data.empty:
            self._static_info_cache[cache_key] = {
                "data": data.copy(),
                "cache_time": current_time
            }
            return data
        return None
```

---

## ✅ T3: 修改 `query_contract()`（10分钟）

**文件**: `vnpy_futu/vnpy_futu/futu_gateway.py`  
**位置**: `query_contract()` 方法（约1964行）

**任务**:
- [ ] 将 `self.quote_ctx.get_stock_basicinfo(market, futu_product)` 
- [ ] 替换为 `self._get_stock_basicinfo_cached(market, futu_product)`
- [ ] 修改错误处理（`data is None` 而不是 `code`）

**修改前**:
```python
code, data = self.quote_ctx.get_stock_basicinfo(market, futu_product)
if code:
    self.write_log(f"查询合约信息失败：{data}")
    return
```

**修改后**:
```python
data = self._get_stock_basicinfo_cached(market, futu_product)
if data is None:
    self.write_log(f"查询合约信息失败：{market}/{futu_product}")
    continue
```

---

## ✅ T4: 修改 `_resolve_main_by_volume()`（10分钟）

**文件**: `vnpy_futu/vnpy_futu/futu_gateway.py`  
**位置**: `_resolve_main_by_volume()` 方法（约1380行）

**任务**:
- [ ] 将 `ret, contract_data = self.quote_ctx.get_stock_basicinfo("HK", "FUTURE")`
- [ ] 替换为 `contract_data = self._get_stock_basicinfo_cached("HK", "FUTURE")`
- [ ] 修改错误处理（`contract_data is None` 而不是 `ret != 0`）

**修改前**:
```python
ret, contract_data = self.quote_ctx.get_stock_basicinfo("HK", "FUTURE")
if ret != 0 or contract_data.empty:
    return None
```

**修改后**:
```python
contract_data = self._get_stock_basicinfo_cached("HK", "FUTURE")
if contract_data is None or contract_data.empty:
    return None
```

---

## ✅ T5: 修改 `_resolve_main_by_nearest_expiry()`（10分钟）

**文件**: `vnpy_futu/vnpy_futu/futu_gateway.py`  
**位置**: `_resolve_main_by_nearest_expiry()` 方法（约1438行）

**任务**:
- [ ] 将 `ret, contract_data = self.quote_ctx.get_stock_basicinfo("HK", "FUTURE")`
- [ ] 替换为 `contract_data = self._get_stock_basicinfo_cached("HK", "FUTURE")`
- [ ] 修改错误处理（`contract_data is None` 而不是 `ret != 0`）

**修改前**:
```python
ret, contract_data = self.quote_ctx.get_stock_basicinfo("HK", "FUTURE")
if ret != 0 or contract_data.empty:
    return None
```

**修改后**:
```python
contract_data = self._get_stock_basicinfo_cached("HK", "FUTURE")
if contract_data is None or contract_data.empty:
    return None
```

---

## ✅ T6: 添加缓存管理方法（20分钟）

**文件**: `vnpy_futu/vnpy_futu/futu_gateway.py`  
**位置**: 在 `_get_stock_basicinfo_cached()` 方法之后

**任务**:
- [ ] 实现 `clear_static_info_cache(market=None, product=None)` 方法
- [ ] 实现 `refresh_static_info_cache(market=None, product=None)` 方法
- [ ] 添加日志输出

**关键代码**:
```python
def clear_static_info_cache(self, market: Optional[str] = None, 
                            product: Optional[str] = None) -> None:
    """清空 StaticInfo 缓存"""
    with self._static_info_cache_lock:
        if market is None and product is None:
            self._static_info_cache.clear()
        else:
            # 清空指定缓存
            keys_to_remove = [
                key for key in self._static_info_cache.keys()
                if (market is None or key[0] == market) and
                   (product is None or key[1] == product)
            ]
            for key in keys_to_remove:
                del self._static_info_cache[key]
```

---

## ✅ T7: 连接断开时清空缓存（5分钟）

**文件**: `vnpy_futu/vnpy_futu/futu_gateway.py`  
**位置**: `close()` 或 `disconnect()` 方法

**任务**:
- [ ] 在 `close()` 方法中调用 `self.clear_static_info_cache()`
- [ ] 确保在连接断开时清空缓存，避免脏数据

---

## ✅ T8: 添加配置支持（可选，10分钟）

**文件**: `vnpy_futu/vnpy_futu/futu_gateway.py`  
**位置**: `__init__` 方法

**任务**:
- [ ] 从 `SETTINGS` 读取 `futu.staticinfo.cache_ttl` 配置
- [ ] 如果不存在，使用默认值 86400（24小时）

**关键代码**:
```python
from vnpy.trader.setting import SETTINGS
self._static_info_cache_ttl = SETTINGS.get(
    "futu.staticinfo.cache_ttl", 
    86400
)
```

---

## ✅ T9: 编写测试用例（30分钟）

**文件**: `tests/test_futu_staticinfo_cache.py`（新建）

**任务**:
- [ ] 测试缓存命中（第一次慢，第二次快）
- [ ] 测试缓存过期（设置短TTL，等待过期后查询）
- [ ] 测试缓存清空（清空后重新查询）
- [ ] 性能测试（验证延迟降低）

**测试脚本示例**:
```python
def test_cache_hit():
    gateway = FutuGateway(event_engine, "FUTU")
    
    # 第一次查询（应该慢）
    start = time.time()
    gateway.query_contract()
    first_time = (time.time() - start) * 1000
    
    # 第二次查询（应该快）
    start = time.time()
    gateway.query_contract()
    second_time = (time.time() - start) * 1000
    
    assert second_time < 10  # 应该 <10ms
    assert first_time / second_time > 100  # 性能提升 >100x
```

---

## ✅ T10: 代码审查和优化（20分钟）

**任务**:
- [ ] 代码审查（检查逻辑正确性）
- [ ] 性能测试验证（确保延迟降低）
- [ ] 日志输出优化（确保日志清晰）
- [ ] 错误处理检查（确保异常情况处理正确）

---

## 实施顺序建议

1. **T1 → T2 → T3**: 先实现核心缓存功能（约50分钟）
2. **T4 → T5**: 修改其他调用位置（约20分钟）
3. **T6 → T7**: 添加缓存管理（约25分钟）
4. **T9**: 测试验证（约30分钟）
5. **T8 → T10**: 可选优化（约30分钟）

**总计**: 约2.5小时

---

## 验证清单

完成所有任务后，验证以下内容：

- [ ] 第一次查询合约：日志显示 "缓存未命中，查询远程"
- [ ] 第二次查询合约：日志显示 "命中缓存"，延迟 <1ms
- [ ] 主力合约解析：使用缓存，速度提升
- [ ] 连接断开：缓存被清空
- [ ] 性能测试：延迟降低 >400x

---

## 预期效果

| 指标 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| 单次查询延迟 | 463.19ms | <1ms | >400x |
| 787次查询总耗时 | 364.5秒 | <1秒 | >360x |
| 缓存命中率 | 0% | >95% | - |

