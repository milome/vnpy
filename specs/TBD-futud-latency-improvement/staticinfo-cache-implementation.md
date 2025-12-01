# StaticInfo 缓存实现方案

**目标**: 将 StaticInfo(3202) 延迟从 463.19ms 降至 <1ms（缓存命中时）  
**优先级**: P0（立即实施）  
**预计耗时**: 2-3小时

## 一、现状分析

### 1.1 调用位置统计

通过代码分析，`get_stock_basicinfo` 在以下位置被调用：

1. **`query_contract()`** (1964行)
   - 用途：查询所有合约信息
   - 调用频率：启动时、手动查询时
   - 调用方式：按市场+产品类型批量查询

2. **`_resolve_main_by_volume()`** (1388行)
   - 用途：通过成交量解析主力合约
   - 调用频率：主力合约解析时（后备策略）
   - 调用方式：`get_stock_basicinfo("HK", "FUTURE")`

3. **`_resolve_main_by_nearest_expiry()`** (1452行)
   - 用途：通过最近到期日解析主力合约
   - 调用频率：主力合约解析时（后备策略）
   - 调用方式：`get_stock_basicinfo("HK", "FUTURE")`

### 1.2 调用模式分析

**调用模式**:
- **按市场+产品类型查询**: `get_stock_basicinfo(market, product)`
  - market: "HK", "US", "HK_FUTURE" 等
  - product: "STOCK", "FUTURE", "ETF" 等

**数据特点**:
- 静态数据，变化频率极低（通常只在夜间有合约上市/下线）
- 数据量大（一个市场可能有数千个合约）
- 适合全量缓存 + 按需刷新

### 1.3 性能影响

- **当前延迟**: 463.19ms（平均）
- **调用次数**: 787次
- **总耗时**: 364.5秒（约6分钟）
- **优化潜力**: 缓存后延迟降至 <1ms，总耗时降至 <1秒

## 二、设计方案

### 2.1 缓存结构设计

```python
# 缓存键设计
cache_key = (market, product)  # 例如: ("HK", "FUTURE")

# 缓存值结构
{
    "data": pd.DataFrame,           # 原始数据
    "cache_time": float,            # 缓存时间戳
    "contracts": Dict[str, ContractData]  # 已转换的合约字典（可选）
}
```

### 2.2 缓存策略

1. **TTL策略**: 
   - 默认TTL: 86400秒（24小时）
   - 可配置: 通过 `SETTINGS["futu.staticinfo.cache_ttl"]` 配置

2. **刷新策略**:
   - **启动时预加载**: 根据配置的市场列表，启动时预加载常用市场
   - **按需加载**: 未缓存的市场按需加载
   - **强制刷新**: 提供手动刷新接口（用于夜间合约更新后）

3. **缓存失效**:
   - TTL过期自动失效
   - 连接断开时清空缓存（避免脏数据）
   - 手动刷新接口

### 2.3 线程安全

- 使用 `RLock` 保护缓存读写（与现有代码风格一致）
- 缓存查询和更新都加锁

## 三、实现步骤

### Step 1: 添加缓存字段到 `__init__`

**文件**: `vnpy_futu/vnpy_futu/futu_gateway.py`  
**位置**: `__init__` 方法（约204行）

**修改内容**:
```python
# 在 __init__ 方法中添加
# StaticInfo 缓存
self._static_info_cache: Dict[Tuple[str, str], Dict[str, Any]] = {}
self._static_info_cache_lock = RLock()  # 缓存读写锁
self._static_info_cache_ttl: int = 86400  # 默认24小时
```

### Step 2: 实现缓存查询方法

**文件**: `vnpy_futu/vnpy_futu/futu_gateway.py`  
**位置**: 在 `query_contract()` 方法之前（约1960行）

**新增方法**:
```python
def _get_stock_basicinfo_cached(
    self, 
    market: str, 
    product: str
) -> Optional[pd.DataFrame]:
    """
    获取合约静态信息（带缓存）
    
    Args:
        market: 市场代码（如 "HK", "US"）
        product: 产品类型（如 "FUTURE", "STOCK"）
    
    Returns:
        DataFrame 或 None（失败时）
    """
    cache_key = (market, product)
    current_time = time()
    
    with self._static_info_cache_lock:
        # 检查缓存
        if cache_key in self._static_info_cache:
            cache_entry = self._static_info_cache[cache_key]
            cache_age = current_time - cache_entry["cache_time"]
            
            # 检查是否过期
            if cache_age < self._static_info_cache_ttl:
                self.write_log(
                    f"[StaticInfo缓存] 命中缓存: {market}/{product} "
                    f"(缓存年龄: {cache_age:.1f}秒)"
                )
                return cache_entry["data"].copy()  # 返回副本，避免外部修改
        
        # 缓存未命中或已过期，查询远程
        self.write_log(f"[StaticInfo缓存] 缓存未命中，查询远程: {market}/{product}")
        ret, data = self.quote_ctx.get_stock_basicinfo(market, product)
        
        if ret != 0:
            self.write_log(f"[StaticInfo缓存] 查询失败: {data}")
            return None
        
        if data.empty:
            self.write_log(f"[StaticInfo缓存] 查询结果为空: {market}/{product}")
            return None
        
        # 更新缓存
        self._static_info_cache[cache_key] = {
            "data": data.copy(),
            "cache_time": current_time
        }
        
        self.write_log(
            f"[StaticInfo缓存] 已缓存: {market}/{product} "
            f"(合约数: {len(data)})"
        )
        
        return data
```

### Step 3: 修改 `query_contract()` 方法

**文件**: `vnpy_futu/vnpy_futu/futu_gateway.py`  
**位置**: `query_contract()` 方法（约1964行）

**修改内容**:
```python
def query_contract(self) -> None:
    """查询合约"""
    # get_stock_basicinfo 是没有区分future的， 区分了地区
    if self.market in ["HK", "HK_FUTURE"]:
        market = "HK"
    else:
        market = self.market

    for product, futu_product in PRODUCT_VT2FUTU.items():
        # ✅ 修改：使用缓存方法
        data = self._get_stock_basicinfo_cached(market, futu_product)
        
        if data is None:
            self.write_log(f"查询合约信息失败：{market}/{futu_product}")
            continue

        # 后续处理逻辑保持不变
        for ix, row in data.iterrows():
            symbol, exchange = convert_symbol_futu2vt(row["code"])
            
            # ... 后续代码保持不变 ...
```

### Step 4: 修改 `_resolve_main_by_volume()` 方法

**文件**: `vnpy_futu/vnpy_futu/futu_gateway.py`  
**位置**: `_resolve_main_by_volume()` 方法（约1380行）

**修改内容**:
```python
def _resolve_main_by_volume(self, base_symbol: str) -> Optional[str]:
    """
    通过成交量解析主力合约（后备方案）
    ...
    """
    try:
        # ✅ 修改：使用缓存方法
        contract_data = self._get_stock_basicinfo_cached("HK", "FUTURE")
        
        if contract_data is None or contract_data.empty:
            return None
        
        # 后续处理逻辑保持不变
        # ...
```

### Step 5: 修改 `_resolve_main_by_nearest_expiry()` 方法

**文件**: `vnpy_futu/vnpy_futu/futu_gateway.py`  
**位置**: `_resolve_main_by_nearest_expiry()` 方法（约1438行）

**修改内容**:
```python
def _resolve_main_by_nearest_expiry(self, base_symbol: str) -> Optional[str]:
    """
    选择最近到期的月份合约作为主力合约。
    ...
    """
    try:
        # ✅ 修改：使用缓存方法
        contract_data = self._get_stock_basicinfo_cached("HK", "FUTURE")
        
        if contract_data is None or contract_data.empty:
            return None
        
        # 后续处理逻辑保持不变
        # ...
```

### Step 6: 添加缓存管理方法

**文件**: `vnpy_futu/vnpy_futu/futu_gateway.py`  
**位置**: 在 `_get_stock_basicinfo_cached()` 方法之后

**新增方法**:
```python
def clear_static_info_cache(self, market: Optional[str] = None, 
                            product: Optional[str] = None) -> None:
    """
    清空 StaticInfo 缓存
    
    Args:
        market: 如果指定，只清空该市场的缓存；None 表示清空所有
        product: 如果指定，只清空该产品的缓存；None 表示清空所有
    """
    with self._static_info_cache_lock:
        if market is None and product is None:
            # 清空所有缓存
            count = len(self._static_info_cache)
            self._static_info_cache.clear()
            self.write_log(f"[StaticInfo缓存] 已清空所有缓存 ({count}条)")
        else:
            # 清空指定缓存
            keys_to_remove = []
            for key in self._static_info_cache.keys():
                cache_market, cache_product = key
                if (market is None or cache_market == market) and \
                   (product is None or cache_product == product):
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self._static_info_cache[key]
            
            self.write_log(
                f"[StaticInfo缓存] 已清空指定缓存: "
                f"market={market}, product={product} ({len(keys_to_remove)}条)"
            )

def refresh_static_info_cache(self, market: Optional[str] = None,
                             product: Optional[str] = None) -> None:
    """
    强制刷新 StaticInfo 缓存
    
    Args:
        market: 如果指定，只刷新该市场的缓存；None 表示刷新所有
        product: 如果指定，只刷新该产品的缓存；None 表示刷新所有
    """
    # 先清空缓存
    self.clear_static_info_cache(market, product)
    
    # 重新查询（会触发缓存更新）
    if market is None:
        markets = ["HK", "US", "HK_FUTURE"]
    else:
        markets = [market]
    
    if product is None:
        products = list(PRODUCT_VT2FUTU.values())
    else:
        products = [product]
    
    for m in markets:
        for p in products:
            self._get_stock_basicinfo_cached(m, p)
    
    self.write_log(f"[StaticInfo缓存] 已刷新缓存")
```

### Step 7: 在连接断开时清空缓存

**文件**: `vnpy_futu/vnpy_futu/futu_gateway.py`  
**位置**: `close()` 或 `disconnect()` 方法

**修改内容**:
```python
def close(self) -> None:
    """关闭连接"""
    # ... 现有代码 ...
    
    # ✅ 新增：清空缓存
    self.clear_static_info_cache()
    
    # ... 现有代码 ...
```

### Step 8: 添加配置支持（可选）

**文件**: `vnpy_futu/vnpy_futu/futu_gateway.py`  
**位置**: `__init__` 方法

**修改内容**:
```python
def __init__(self, event_engine: EventEngine, gateway_name: str) -> None:
    """构造函数"""
    # ... 现有代码 ...
    
    # StaticInfo 缓存
    self._static_info_cache: Dict[Tuple[str, str], Dict[str, Any]] = {}
    self._static_info_cache_lock = RLock()
    
    # ✅ 从配置读取TTL（如果存在）
    from vnpy.trader.setting import SETTINGS
    self._static_info_cache_ttl = SETTINGS.get(
        "futu.staticinfo.cache_ttl", 
        86400  # 默认24小时
    )
```

## 四、测试验证

### 4.1 功能测试

1. **缓存命中测试**:
   - 第一次查询：应该看到 "缓存未命中，查询远程"
   - 第二次查询：应该看到 "命中缓存"
   - 验证延迟：第二次查询应该 <1ms

2. **缓存过期测试**:
   - 设置短TTL（如10秒）
   - 等待TTL过期后查询：应该重新查询远程

3. **缓存清空测试**:
   - 调用 `clear_static_info_cache()`：应该清空所有缓存
   - 再次查询：应该重新查询远程

### 4.2 性能测试

**测试脚本**:
```python
import time
from vnpy_futu import FutuGateway

gateway = FutuGateway(event_engine, "FUTU")

# 第一次查询（应该慢）
start = time.time()
gateway.query_contract()
first_time = (time.time() - start) * 1000
print(f"第一次查询耗时: {first_time:.2f}ms")

# 第二次查询（应该快）
start = time.time()
gateway.query_contract()
second_time = (time.time() - start) * 1000
print(f"第二次查询耗时: {second_time:.2f}ms")

print(f"性能提升: {first_time / second_time:.1f}x")
```

**预期结果**:
- 第一次查询: ~463ms
- 第二次查询: <1ms
- 性能提升: >400x

## 五、TODO 清单

### T1: 添加缓存字段 ✅
- [ ] 在 `__init__` 中添加 `_static_info_cache` 字典
- [ ] 添加 `_static_info_cache_lock` 锁
- [ ] 添加 `_static_info_cache_ttl` TTL配置

**预计耗时**: 10分钟

### T2: 实现缓存查询方法 ✅
- [ ] 实现 `_get_stock_basicinfo_cached()` 方法
- [ ] 实现缓存检查逻辑
- [ ] 实现缓存更新逻辑
- [ ] 添加日志输出

**预计耗时**: 30分钟

### T3: 修改 `query_contract()` ✅
- [ ] 将 `get_stock_basicinfo()` 替换为 `_get_stock_basicinfo_cached()`
- [ ] 测试功能正常

**预计耗时**: 10分钟

### T4: 修改 `_resolve_main_by_volume()` ✅
- [ ] 将 `get_stock_basicinfo()` 替换为 `_get_stock_basicinfo_cached()`
- [ ] 测试功能正常

**预计耗时**: 10分钟

### T5: 修改 `_resolve_main_by_nearest_expiry()` ✅
- [ ] 将 `get_stock_basicinfo()` 替换为 `_get_stock_basicinfo_cached()`
- [ ] 测试功能正常

**预计耗时**: 10分钟

### T6: 添加缓存管理方法 ✅
- [ ] 实现 `clear_static_info_cache()` 方法
- [ ] 实现 `refresh_static_info_cache()` 方法
- [ ] 添加日志输出

**预计耗时**: 20分钟

### T7: 连接断开时清空缓存 ✅
- [ ] 在 `close()` 或 `disconnect()` 中调用 `clear_static_info_cache()`
- [ ] 测试功能正常

**预计耗时**: 5分钟

### T8: 添加配置支持（可选）✅
- [ ] 从 `SETTINGS` 读取TTL配置
- [ ] 添加默认值

**预计耗时**: 10分钟

### T9: 编写测试用例 ✅
- [ ] 编写缓存命中测试
- [ ] 编写缓存过期测试
- [ ] 编写性能测试

**预计耗时**: 30分钟

### T10: 代码审查和优化 ✅
- [ ] 代码审查
- [ ] 性能测试验证
- [ ] 日志输出优化

**预计耗时**: 20分钟

## 六、预期效果

### 6.1 性能提升

| 指标 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| 单次查询延迟 | 463.19ms | <1ms | >400x |
| 787次查询总耗时 | 364.5秒 | <1秒 | >360x |
| 缓存命中率 | 0% | >95% | - |

### 6.2 用户体验提升

1. **启动速度**: 启动时合约查询从数秒降至毫秒级
2. **主力合约解析**: 主力合约解析速度显著提升
3. **手动查询**: 合约查询响应速度提升400倍以上

## 七、注意事项

1. **内存占用**: 缓存会占用一定内存，但通常 <50MB，可接受
2. **数据一致性**: 静态数据变化频率低，24小时TTL足够
3. **线程安全**: 所有缓存操作都使用锁保护
4. **错误处理**: 缓存查询失败时回退到远程查询

## 八、后续优化（可选）

1. **持久化缓存**: 将缓存保存到磁盘，启动时加载
2. **增量更新**: 只更新变化的合约，而不是全量刷新
3. **缓存统计**: 添加缓存命中率统计
4. **预加载**: 启动时预加载常用市场的合约信息

