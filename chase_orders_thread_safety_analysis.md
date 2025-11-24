# chase_orders 数据结构线程安全性分析

## 1. 概述

`chase_orders` 是一个 `Dict[str, ChaseOrder]` 类型的字典，用于追踪所有启用追价功能的订单。该字典在多线程环境中被频繁访问和修改，存在潜在的线程安全问题。

## 2. 访问模式分析

### 2.1 访问 `chase_orders` 的线程

1. **主线程/事件线程**
   - `send_order()` - 添加新订单（第1018行）
   - `cancel_order()` - 删除订单（第1105行）
   - `cancel_all_chase_orders()` - 清空字典（第1137行）
   - `on_order_update()` - 读取和删除（第1232-1261行）
   - `process_deal()` - 读取（第1729行）

2. **定时器线程**
   - `process_timer_event()` → `_check_timeout_orders()` - 遍历和修改（第291行，第315行）

3. **异步追价线程**
   - `delayed_chase()` 线程 - 读取和修改（第1255行，第1279行）
   - `start_chase_order()` - 读取（第1143行）

4. **重委托线程**
   - `_retry_order_with_latest_price()` - 读取、修改、删除（多处）

### 2.2 主要操作类型

1. **读取操作**
   ```python
   if orderid in self.chase_orders:  # 检查存在
       chase_order = self.chase_orders[orderid]  # 获取值
   ```

2. **写入操作**
   ```python
   self.chase_orders[orderid] = chase_order  # 添加/更新
   ```

3. **删除操作**
   ```python
   if orderid in self.chase_orders:
       del self.chase_orders[orderid]  # 删除
   ```

4. **遍历操作**
   ```python
   for orderid, chase_order in list(self.chase_orders.items()):  # 遍历
   ```

5. **复合操作**
   ```python
   # 更新字典key（删除旧key，添加新key）
   if normalized_new_orderid != old_orderid:
       self.chase_orders[normalized_new_orderid] = chase_order
       if old_orderid in self.chase_orders:
           del self.chase_orders[old_orderid]
   ```

## 3. 线程安全问题

### 3.1 问题1：检查-修改模式（Check-Then-Act）非原子性

**问题代码示例：**
```python
# 第1232-1233行
if orderid in self.chase_orders:  # 检查
    chase_order = self.chase_orders[orderid]  # 读取
```

**风险：**
- 线程A检查 `orderid in self.chase_orders` 返回 `True`
- 线程B在此时删除了该订单
- 线程A尝试读取时可能抛出 `KeyError`（虽然代码中使用了 `in` 检查，但仍有风险）

**实际代码中的多处实例：**
- 第1232行：`if orderid in self.chase_orders:`
- 第338行：`if orderid in self.chase_orders:`
- 第390行：`if orderid not in self.chase_orders:`
- 第442行：`if original_orderid not in self.chase_orders:`

### 3.2 问题2：字典key更新操作非原子性

**问题代码示例：**
```python
# 第642-649行
if normalized_new_orderid != old_orderid:
    self.chase_orders[normalized_new_orderid] = chase_order  # 步骤1：添加新key
    if old_orderid in self.chase_orders:  # 步骤2：检查旧key
        del self.chase_orders[old_orderid]  # 步骤3：删除旧key
```

**风险：**
- 在步骤1和步骤3之间，同一个订单可能同时存在于两个key下
- 其他线程可能在这期间访问到旧的key，导致数据不一致
- 如果步骤2和步骤3之间其他线程删除了旧key，可能导致误删其他订单

### 3.3 问题3：遍历时的并发修改

**问题代码示例：**
```python
# 第315行
for orderid, chase_order in list(self.chase_orders.items()):
    # ... 处理逻辑 ...
    if orderid in self.chase_orders:
        del self.chase_orders[orderid]  # 在遍历过程中删除
```

**风险：**
- 虽然使用了 `list()` 创建快照，但在遍历过程中修改字典可能导致：
  - 其他线程同时修改字典，导致状态不一致
  - 遍历过程中删除的订单可能被其他线程重新添加

### 3.4 问题4：多线程同时修改同一订单

**场景：**
- 线程A（定时器）：检查超时，准备撤单重委托
- 线程B（订单回调）：订单已成交，准备删除
- 线程C（追价线程）：准备执行追价操作

**风险：**
- 多个线程可能同时操作同一个订单，导致：
  - 已成交的订单被错误地重委托
  - 订单状态不一致
  - 重复操作导致资源浪费

## 4. Python GIL 的影响

### 4.1 GIL 提供的保护

Python 的全局解释器锁（GIL）确保：
- **单个字节码操作是原子的**：如 `dict[key] = value`、`del dict[key]` 等
- **简单读取操作是原子的**：如 `value = dict[key]`

### 4.2 GIL 无法保护的情况

- **复合操作**：多个字节码操作之间可能被其他线程打断
- **检查-修改模式**：`if key in dict: del dict[key]` 不是原子的
- **字典key更新**：删除旧key和添加新key之间不是原子的

## 5. 实际风险评估

### 5.1 高风险场景

1. **订单成交时的竞争条件**
   - `on_order_update()` 尝试删除已成交订单
   - `_check_timeout_orders()` 同时尝试重委托
   - 可能导致已成交订单被错误地重新委托

2. **重委托时的key更新**
   - 删除旧订单ID，添加新订单ID
   - 如果操作不原子，可能导致订单丢失或重复

3. **全撤操作**
   - `cancel_all_chase_orders()` 清空字典
   - 其他线程可能同时添加或删除订单
   - 可能导致部分订单未被取消

### 5.2 中等风险场景

1. **遍历时的修改**
   - 虽然使用了快照，但遍历过程中的修改可能影响其他线程

2. **统计信息读取**
   - `get_chase_statistics()` 读取 `len(self.chase_orders)`
   - 在读取过程中字典可能被修改，但通常不会导致严重问题

## 6. 解决方案建议

### 6.1 方案1：使用 threading.Lock（推荐）

**优点：**
- 简单直接
- 保证操作的原子性
- 性能开销可接受（对于交易场景）

**实现：**
```python
import threading

class FutuGateway(BaseGateway):
    def __init__(self, ...):
        # ...
        self.chase_orders: Dict[str, ChaseOrder] = {}
        self.chase_orders_lock = threading.RLock()  # 使用可重入锁
    
    def _safe_get_chase_order(self, orderid: str) -> Optional[ChaseOrder]:
        """线程安全地获取追价订单"""
        with self.chase_orders_lock:
            return self.chase_orders.get(orderid)
    
    def _safe_del_chase_order(self, orderid: str) -> bool:
        """线程安全地删除追价订单"""
        with self.chase_orders_lock:
            if orderid in self.chase_orders:
                del self.chase_orders[orderid]
                return True
            return False
    
    def _safe_update_chase_order_key(self, old_key: str, new_key: str, chase_order: ChaseOrder) -> None:
        """线程安全地更新订单key"""
        with self.chase_orders_lock:
            if new_key != old_key:
                self.chase_orders[new_key] = chase_order
                if old_key in self.chase_orders:
                    del self.chase_orders[old_key]
```

### 6.2 方案2：使用 collections.ChainMap 或自定义线程安全字典

**优点：**
- 封装性好
- 使用方便

**缺点：**
- 需要额外实现
- 可能影响性能

### 6.3 方案3：使用 queue.Queue 进行串行化处理

**优点：**
- 完全避免竞争条件
- 操作顺序可控

**缺点：**
- 可能影响实时性
- 实现复杂度较高

## 7. 推荐实施步骤

### 步骤1：添加锁机制
- 在 `__init__` 中初始化 `self.chase_orders_lock = threading.RLock()`
- 所有访问 `chase_orders` 的地方都使用锁保护

### 步骤2：封装常用操作
- 创建 `_safe_get_chase_order()`、`_safe_del_chase_order()` 等方法
- 统一使用这些方法访问字典

### 步骤3：重构关键路径
- 重构 `_check_timeout_orders()` 中的遍历和修改逻辑
- 重构 `_retry_order_with_latest_price()` 中的key更新逻辑
- 重构 `on_order_update()` 中的删除逻辑

### 步骤4：测试验证
- 多线程压力测试
- 模拟高并发场景
- 验证数据一致性

## 8. 代码示例：线程安全的重构

```python
# 在 __init__ 中添加
self.chase_orders_lock = threading.RLock()

# 封装方法
def _safe_has_chase_order(self, orderid: str) -> bool:
    """线程安全地检查订单是否存在"""
    with self.chase_orders_lock:
        return orderid in self.chase_orders

def _safe_get_chase_order(self, orderid: str) -> Optional[ChaseOrder]:
    """线程安全地获取追价订单"""
    with self.chase_orders_lock:
        return self.chase_orders.get(orderid)

def _safe_set_chase_order(self, orderid: str, chase_order: ChaseOrder) -> None:
    """线程安全地设置追价订单"""
    with self.chase_orders_lock:
        self.chase_orders[orderid] = chase_order

def _safe_del_chase_order(self, orderid: str) -> bool:
    """线程安全地删除追价订单，返回是否成功删除"""
    with self.chase_orders_lock:
        if orderid in self.chase_orders:
            del self.chase_orders[orderid]
            return True
        return False

def _safe_get_all_chase_orders(self) -> Dict[str, ChaseOrder]:
    """线程安全地获取所有追价订单的副本"""
    with self.chase_orders_lock:
        return dict(self.chase_orders)  # 返回副本

def _safe_update_chase_order_key(self, old_key: str, new_key: str, chase_order: ChaseOrder) -> None:
    """线程安全地更新订单key"""
    with self.chase_orders_lock:
        if new_key != old_key:
            self.chase_orders[new_key] = chase_order
            if old_key in self.chase_orders:
                del self.chase_orders[old_key]

def _safe_clear_chase_orders(self) -> None:
    """线程安全地清空所有追价订单"""
    with self.chase_orders_lock:
        self.chase_orders.clear()
```

## 9. 性能考虑

### 9.1 锁的开销
- RLock 的开销相对较小
- 对于交易场景，数据一致性比性能更重要
- 锁的持有时间应该尽量短

### 9.2 优化建议
- 使用 `RLock` 而不是 `Lock`，避免死锁
- 尽量减少锁的持有时间
- 避免在持有锁的情况下进行耗时操作（如网络请求）

## 10. 订单号变更时的一致性保证问题

### 10.1 问题描述

在追价过程中，如果订单超时被撤单并重新委托，新订单的订单号会发生变化。如何保证追价列表中的追价行为能够针对**原始订单意图**保持一致？

### 10.2 当前实现分析

#### 10.2.1 原始订单信息的保存

在 `ChaseOrder` 类中，保存了原始订单的所有关键信息：

```python
# 第141-148行
# 保存原始订单信息（用于重委托）
self.symbol = symbol
self.exchange = exchange
self.direction = direction  # 保持原始方向
self.offset = offset  # 保持原始offset
self.volume = volume
self.original_reference = reference
self.vt_symbol = f"{symbol}.{exchange.value}"
```

**优点：**
- 原始订单信息（symbol, direction, offset, volume, original_reference）被完整保存
- 重委托时使用这些信息，确保订单意图一致

#### 10.2.2 order_time 的双重用途和关键问题

`order_time` 字段在代码中有两个重要用途：

**用途1：超时判断**
```python
# 第331行：检查订单是否超时
elapsed = current_time - chase_order.order_time
if elapsed >= chase_order.config.timeout_seconds:
    # 执行撤单重委托
```

**用途2：耗时统计**
```python
# 第1239行：计算委托到完全成交耗时
elapsed_ms = (chase_order.fill_time - chase_order.order_time) * 1000

# 第1734行：计算委托到首次成交耗时
elapsed_ms = (chase_order.first_trade_time - chase_order.order_time) * 1000
```

**关键问题：**

1. **order_time 必须更新，否则会导致立即超时**
   - 重委托后，如果不更新 `order_time`，新订单会立即被判定为超时
   - 因为 `elapsed = current_time - chase_order.order_time` 会是一个很大的值（从第一次下单开始计算）
   - 因此，重委托后**必须**更新 `order_time` 为新订单的委托时间

2. **order_time 更新导致统计不准确**
   - 如果重委托后更新了 `order_time`，统计耗时就只反映最后一次重委托到成交的时间
   - 而不是从第一次下单开始的总耗时
   - 这不符合业务需求（需要统计整个智能追价过程的总耗时）

3. **等待tick数据时也需要更新 order_time**
   - 撤单成功后等待tick数据时（第372行、第574行），也需要更新 `order_time`
   - 否则会立即触发超时检查，导致重复撤单

#### 10.2.3 重委托时的处理

```python
# 第631-651行
old_orderid = chase_order.orderid
new_orderid = self.send_order(new_order_req)
if new_orderid:
    normalized_new_orderid = self._normalize_orderid(new_orderid)
    chase_order.retry_count += 1
    chase_order.order_time = time()  # 更新委托时间（必须更新，用于下次超时判断）
    chase_order.orderid = normalized_new_orderid
    # 更新chase_orders字典的key
    if normalized_new_orderid != old_orderid:
        self.chase_orders[normalized_new_orderid] = chase_order
        if old_orderid in self.chase_orders:
            del self.chase_orders[old_orderid]
        if original_orderid in self.chase_orders and original_orderid != old_orderid:
            del self.chase_orders[original_orderid]
```

**优点：**
- 使用原始订单信息（`chase_order.original_reference`）重新委托
- 保持原始方向（`chase_order.direction`）和offset（`chase_order.offset`）
- 更新字典key，确保新订单ID能正确关联到 `ChaseOrder` 对象
- 更新 `order_time` 避免新订单立即被判定为超时

**问题：**

1. **字典key更新非原子性**
   - 删除旧key和添加新key之间不是原子操作
   - 如果在这期间 `on_order_update()` 或 `process_deal()` 被调用，可能找不到订单

2. **缺少原始订单ID追踪**
   - `ChaseOrder` 中没有保存 `original_orderid` 字段
   - 只能通过日志中的 `original_orderid` 变量追踪，但这不是对象属性

3. **缺少原始订单时间追踪**
   - `ChaseOrder` 中没有保存 `original_order_time` 字段
   - 统计耗时使用的是 `order_time`，但 `order_time` 在重委托后会更新
   - 导致统计不准确（只反映最后一次重委托到成交的时间）

### 10.3 潜在问题场景

#### 场景1：新订单状态更新在key更新之前到达

```
时间线：
T1: 重委托发送新订单，获得 new_orderid
T2: 新订单的状态更新回调到达，尝试查找 chase_orders[new_orderid] → 找不到（key还没更新）
T3: 更新 chase_orders 字典key（删除旧key，添加新key）
```

**结果：** 新订单的状态更新可能无法正确关联到 `ChaseOrder` 对象

#### 场景2：耗时统计不准确（关键问题）

**当前实现：**
```python
# 第1239行：计算委托到完全成交耗时
elapsed_ms = (chase_order.fill_time - chase_order.order_time) * 1000

# 第1734行：计算委托到首次成交耗时
elapsed_ms = (chase_order.first_trade_time - chase_order.order_time) * 1000
```

**问题：**
- 如果订单经过多次重委托，`order_time` 会被多次更新（第640行、第750行）
- 统计耗时使用的是更新后的 `order_time`，只反映最后一次重委托到成交的时间
- **不符合业务需求**：应该统计从第一次下单开始的总耗时

**示例：**
```
T0: 第一次下单，order_time = T0
T3: 超时，撤单并重委托，order_time = T3（更新）
T6: 超时，撤单并重委托，order_time = T6（更新）
T7: 订单成交，fill_time = T7

当前统计：elapsed = T7 - T6 = 1秒（只反映最后一次重委托）
期望统计：elapsed = T7 - T0 = 7秒（整个追价过程的总耗时）
```

#### 场景3：无法追踪原始订单

当前代码中，`original_orderid` 只是局部变量，没有保存在 `ChaseOrder` 对象中。如果需要追踪整个追价过程的原始订单ID，无法实现。

#### 场景4：order_time 更新的必要性

**必须更新的场景：**

1. **重委托成功后（第640行、第750行）**
   - 必须更新，否则新订单会立即被判定为超时
   - 因为超时判断使用：`elapsed = current_time - chase_order.order_time`

2. **撤单成功后等待tick数据（第372行、第574行）**
   - 必须更新，避免立即触发超时检查
   - 否则会重复撤单，导致逻辑错误

**不能删除这些更新逻辑，否则会导致 regression issues！**

### 10.4 解决方案

#### 方案1：添加 original_order_time 字段（必须）

在 `ChaseOrder` 类中添加 `original_order_time` 字段，保存第一次下单的时间：

```python
class ChaseOrder:
    def __init__(self, orderid: str, original_price: float, config: ChaseConfig,
                 symbol: str, exchange, direction, offset, volume: int, reference: str):
        # ... 现有代码 ...
        self.original_order_time = time()  # 保存第一次下单时间（用于统计总耗时）
        self.order_time = time()  # 当前订单的委托时间（用于超时判断，重委托后会更新）
        # ... 其他代码 ...
```

**优点：**
- 可以准确统计整个追价过程的总耗时
- 不影响现有的超时判断逻辑（继续使用 `order_time`）
- 不需要修改现有的 `order_time` 更新逻辑

#### 方案2：修改统计耗时计算（必须）

修改统计耗时的计算，使用 `original_order_time` 而不是 `order_time`：

```python
# 第1239行修改为：
elapsed_ms = (chase_order.fill_time - chase_order.original_order_time) * 1000

# 第1734行修改为：
elapsed_ms = (chase_order.first_trade_time - chase_order.original_order_time) * 1000
```

**优点：**
- 统计准确（从第一次下单开始计算）
- 符合业务需求（统计整个智能追价过程的总耗时）

#### 方案3：添加原始订单ID字段（推荐）

在 `ChaseOrder` 类中添加 `original_orderid` 字段：

```python
class ChaseOrder:
    def __init__(self, orderid: str, original_price: float, config: ChaseConfig,
                 symbol: str, exchange, direction, offset, volume: int, reference: str):
        # ... 现有代码 ...
        self.original_orderid = orderid  # 保存第一次下单的订单ID
        self.orderid = orderid  # 当前订单ID（重委托后会更新）
        # ... 其他代码 ...
```

**优点：**
- 可以追踪整个追价过程的原始订单
- 便于日志记录和问题排查
- 不影响现有逻辑

#### 方案4：原子化字典key更新（推荐）

使用锁保护字典key更新操作：

```python
def _safe_update_chase_order_key(self, old_key: str, new_key: str, chase_order: ChaseOrder) -> None:
    """线程安全地更新订单key"""
    with self.chase_orders_lock:
        if new_key != old_key:
            # 先添加新key，再删除旧key，确保新订单能立即被找到
            self.chase_orders[new_key] = chase_order
            if old_key in self.chase_orders:
                del self.chase_orders[old_key]
```

**优点：**
- 确保新订单ID能立即被找到
- 避免状态更新丢失

#### 重要提醒：不要修改现有的 order_time 更新逻辑

**必须保留的 order_time 更新：**

1. **第640行：重委托成功后**
   ```python
   chase_order.order_time = time()  # 必须更新，用于下次超时判断
   ```

2. **第750行：等待tick后重委托成功**
   ```python
   chase_order.order_time = time()  # 必须更新，用于下次超时判断
   ```

3. **第372行：撤单成功后等待tick数据**
   ```python
   chase_order.order_time = current_time  # 必须更新，避免立即触发超时
   ```

4. **第574行：撤单成功但无法获取tick**
   ```python
   chase_order.order_time = time()  # 必须更新，避免立即触发超时
   ```

**如果删除这些更新，会导致：**
- 重委托后的新订单立即被判定为超时
- 撤单后等待tick数据时立即触发超时检查
- 导致重复撤单和逻辑错误

### 10.5 推荐实施步骤

1. **添加 `original_order_time` 字段（必须）**
   - 在 `ChaseOrder.__init__` 中保存第一次下单的时间
   - 这个字段**永远不更新**，用于统计总耗时

2. **添加 `original_orderid` 字段（推荐）**
   - 在 `ChaseOrder.__init__` 中保存第一次下单的订单ID
   - 重委托时不要更新这个字段

3. **修改统计耗时计算（必须）**
   - 将第1239行和第1734行的统计计算改为使用 `original_order_time`
   - 确保统计的是从第一次下单开始的总耗时

4. **保留所有现有的 `order_time` 更新逻辑（必须）**
   - **不要删除**任何现有的 `order_time` 更新代码
   - 这些更新是必要的，用于超时判断

5. **原子化字典key更新（推荐）**
   - 使用锁保护字典key更新操作
   - 先添加新key，再删除旧key

6. **增强日志记录（推荐）**
   - 在日志中记录 `original_orderid` 和当前 `orderid`
   - 便于追踪整个追价过程

### 10.6 代码示例：改进后的实现

```python
class ChaseOrder:
    def __init__(self, orderid: str, original_price: float, config: ChaseConfig,
                 symbol: str, exchange, direction, offset, volume: int, reference: str):
        # ... 现有代码 ...
        self.original_orderid = orderid  # 保存原始订单ID（第一次下单的ID，不更新）
        self.orderid = orderid  # 当前订单ID（重委托后会更新）
        self.original_order_time = time()  # 保存第一次下单时间（不更新，用于统计总耗时）
        self.order_time = time()  # 当前订单的委托时间（重委托后会更新，用于超时判断）
        # ... 其他代码 ...

# 在 _retry_order_with_latest_price 中（保持现有逻辑不变）
def _retry_order_with_latest_price(self, chase_order: ChaseOrder) -> None:
    # ... 现有代码 ...
    
    # 发送新订单
    old_orderid = chase_order.orderid
    new_orderid = self.send_order(new_order_req)
    if new_orderid:
        normalized_new_orderid = self._normalize_orderid(new_orderid)
        if not normalized_new_orderid:
            return
        
        chase_order.retry_count += 1
        # 必须更新 order_time，用于下次超时判断（不要删除这行！）
        chase_order.order_time = time()  # 保留这行，用于超时判断
        
        # 原子化更新字典key
        with self.chase_orders_lock:
            chase_order.orderid = normalized_new_orderid
            if normalized_new_orderid != old_orderid:
                # 先添加新key，确保新订单能立即被找到
                self.chase_orders[normalized_new_orderid] = chase_order
                # 再删除旧key
                if old_orderid in self.chase_orders:
                    del self.chase_orders[old_orderid]
                if chase_order.original_orderid in self.chase_orders and chase_order.original_orderid != old_orderid:
                    del self.chase_orders[chase_order.original_orderid]
        
        self.write_log(f"订单{chase_order.original_orderid}重委托成功："
                      f"新订单{normalized_new_orderid}，价格{new_price:.3f}，"
                      f"第{chase_order.retry_count}次重试")

# 修改统计耗时计算（第1239行）
def on_order_update(self, order: OrderData) -> None:
    # ... 现有代码 ...
    if order.status == Status.ALLTRADED and chase_order.fill_time is None:
        chase_order.fill_time = time()
        # 使用 original_order_time 计算总耗时
        elapsed_ms = (chase_order.fill_time - chase_order.original_order_time) * 1000
        self.chase_stats["order_to_fill_times"].append(elapsed_ms)
        # ... 其他代码 ...

# 修改统计耗时计算（第1734行）
def process_deal(self, data) -> None:
    # ... 现有代码 ...
    if chase_order.first_trade_time is None:
        chase_order.first_trade_time = time()
        # 使用 original_order_time 计算总耗时
        elapsed_ms = (chase_order.first_trade_time - chase_order.original_order_time) * 1000
        self.chase_stats["order_to_first_trade_times"].append(elapsed_ms)
        # ... 其他代码 ...
```

**关键点：**
1. `original_order_time` 在初始化时设置，**永远不更新**
2. `order_time` 在重委托后**必须更新**，用于超时判断
3. 统计耗时使用 `original_order_time`，确保统计的是总耗时
4. 超时判断继续使用 `order_time`，确保逻辑正确

## 11. 总结

`chase_orders` 字典在多线程环境中存在明显的线程安全问题，主要体现在：

1. **检查-修改模式非原子性**：可能导致 KeyError 或数据不一致
2. **字典key更新非原子性**：可能导致订单丢失或重复
3. **并发修改风险**：多个线程同时操作同一订单可能导致状态不一致
4. **订单号变更时的一致性保证**：重委托时订单号变更，需要确保追价行为针对原始订单意图保持一致
5. **order_time 的双重用途冲突**：既用于超时判断（必须更新），又用于耗时统计（应该使用原始时间）

### 11.1 关键发现：order_time 的双重用途

**用途1：超时判断（必须更新）**
- 重委托后必须更新 `order_time`，否则新订单会立即被判定为超时
- 撤单后等待tick数据时也必须更新，避免立即触发超时检查

**用途2：耗时统计（应该使用原始时间）**
- 应该统计从第一次下单开始的总耗时
- 但当前实现使用的是 `order_time`，而 `order_time` 在重委托后会更新
- 导致统计不准确（只反映最后一次重委托到成交的时间）

**解决方案：**
- 添加 `original_order_time` 字段保存第一次下单时间（永远不更新）
- 保留 `order_time` 字段，继续在重委托后更新（用于超时判断）
- 修改统计耗时计算，使用 `original_order_time` 而不是 `order_time`

### 11.2 建议实施方案

**线程安全：**
- 采用方案1（使用 threading.RLock），这是最简单、最可靠的解决方案

**订单号变更一致性：**
1. 添加 `original_orderid` 字段追踪原始订单
2. 添加 `original_order_time` 字段保存第一次下单时间
3. 修改统计耗时计算，使用 `original_order_time`
4. **保留所有现有的 `order_time` 更新逻辑**（不要删除，避免 regression issues）
5. 原子化字典key更新操作

**重要提醒：**
- **不要删除任何现有的 `order_time` 更新代码**
- 这些更新是必要的，用于超时判断
- 如果删除会导致重委托后的新订单立即被判定为超时

