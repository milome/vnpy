# 挂单参数持久化分析

## 问题描述

从数据库加载的挂单线没有挂单参数（`_pending_order_params`），导致无法触发模拟成交。挂单参数目前只存储在内存中，程序重启后会丢失。

## 当前挂单参数结构

### 内存中的挂单参数 (`_pending_order_params[line_id]`)

```python
{
    "params": {
        "direction": Direction枚举,      # 交易方向（LONG/SHORT）
        "volume": float,                # 手数
        "price": float,                 # 价格（可以从价格线获取）
        "offset": Offset枚举,           # 开平（OPEN/CLOSE）
        "price_precision": int          # 价格精度（可选，可以从价格线获取）
    },
    "vt_symbol": str,                   # 合约标识（可以从价格线获取）
    "contract": ContractData对象       # 合约对象（可以从vt_symbol和main_engine获取）
}
```

## 触发逻辑分析

### `trigger_pending_order_breakthrough` 方法使用的字段

1. **必需字段**（用于创建OrderRequest）：
   - `params["direction"]`: Direction枚举 → 转换为字符串存储
   - `params["volume"]`: float → 直接存储
   - `params["price"]`: float → 可以从价格线获取，但为了完整性建议存储
   - `params["offset"]`: Offset枚举 → 转换为字符串存储
   - `vt_symbol`: str → 可以从价格线获取，但为了完整性建议存储

2. **可简化字段**（不需要持久化）：
   - `contract`: ContractData对象 → 可以从`vt_symbol`和`main_engine`获取
   - `price_precision`: int → 可以从价格线获取（已存储在price_lines表中）

3. **平仓判断逻辑**（需要实时查询）：
   - 通过`main_engine.get_all_positions()`查询持仓
   - 通过`_position_holdings`查询持仓（内存中）
   - 这些不需要持久化，触发时实时查询即可

## 数据库设计方案

### 方案1：在price_lines表中添加字段（推荐）

**优点**：
- 简单直接，不需要额外的表
- 查询效率高
- 数据一致性好

**缺点**：
- 只有挂单线需要这些字段，其他类型价格线不需要（会有NULL值）

**表结构修改**：
```sql
ALTER TABLE price_lines ADD COLUMN order_volume REAL;        -- 挂单手数
ALTER TABLE price_lines ADD COLUMN order_offset TEXT;         -- 开平（"OPEN"/"CLOSE"）
-- direction 和 price 已存在，vt_symbol 已存在
```

### 方案2：创建独立的pending_order_params表

**优点**：
- 数据分离，结构清晰
- 不影响现有价格线表结构

**缺点**：
- 需要额外的JOIN查询
- 需要维护外键关系

**表结构**：
```sql
CREATE TABLE IF NOT EXISTS pending_order_params (
    line_id TEXT PRIMARY KEY,
    order_volume REAL NOT NULL,
    order_offset TEXT NOT NULL,  -- "OPEN" or "CLOSE"
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (line_id) REFERENCES price_lines(line_id) ON DELETE CASCADE
)
```

## 推荐方案：方案1（在price_lines表中添加字段）

### 理由

1. **简化依赖**：触发逻辑只需要从价格线对象获取信息，不需要额外的查询
2. **性能优化**：避免JOIN查询，提高触发速度
3. **数据一致性**：价格线和挂单参数在同一张表中，保证一致性
4. **向后兼容**：对于非挂单线，这些字段为NULL，不影响现有功能

### 需要添加的字段

```sql
ALTER TABLE price_lines ADD COLUMN order_volume REAL;        -- 挂单手数（仅PENDING类型需要）
ALTER TABLE price_lines ADD COLUMN order_offset TEXT;         -- 开平（"OPEN"/"CLOSE"，仅PENDING类型需要）
```

### 字段说明

- `order_volume`: 挂单手数，REAL类型，仅PENDING类型价格线需要
- `order_offset`: 开平类型，TEXT类型，值为"OPEN"或"CLOSE"，仅PENDING类型价格线需要
- `direction`: 已存在，交易方向（"long"/"short"）
- `price`: 已存在，挂单价格
- `vt_symbol`: 已存在，合约标识

## 触发逻辑简化

### 当前逻辑依赖

1. `controller._pending_order_params[line_id]` - 内存中的挂单参数
2. `order_data["params"]` - 订单参数字典
3. `order_data["vt_symbol"]` - 合约标识
4. `order_data["contract"]` - 合约对象（用于获取gateway_name）

### 简化后的逻辑

1. **从价格线对象获取**：
   - `line.get_price()` → 价格
   - `line.get_direction()` → 方向（需要转换为Direction枚举）
   - `line.get_line_type()` → 确认是PENDING类型
   - `line.get_volume()` → 手数（需要新增方法或从数据库字段获取）
   - `line.get_offset()` → 开平（需要新增方法或从数据库字段获取）

2. **从ChartWidget获取**：
   - `self._vt_symbol` → 合约标识（或从价格线获取）

3. **从main_engine获取**：
   - `main_engine.get_contract(vt_symbol)` → 合约对象（用于获取gateway_name）

### 需要修改的代码

1. **PriceLineItem类**：
   - 添加`get_volume()`方法（从数据库字段获取）
   - 添加`get_offset()`方法（从数据库字段获取）
   - 添加`set_volume(volume)`方法
   - 添加`set_offset(offset)`方法

2. **PriceLineDatabase类**：
   - 修改`save_line()`方法，保存`order_volume`和`order_offset`
   - 修改`load_lines()`方法，加载`order_volume`和`order_offset`

3. **trigger_pending_order_breakthrough方法**：
   - 修改逻辑，从价格线对象获取参数，而不是从`_pending_order_params`
   - 简化依赖，减少对内存中挂单参数的依赖

## 实现步骤

1. **数据库迁移**：添加`order_volume`和`order_offset`字段
2. **PriceLineItem扩展**：添加获取/设置volume和offset的方法
3. **数据库操作**：修改保存/加载逻辑
4. **触发逻辑重构**：从价格线对象获取参数，而不是从内存
5. **创建挂单时**：同时保存到数据库和内存（保持向后兼容）

## 注意事项

1. **向后兼容**：对于从数据库加载的旧挂单线，如果`order_volume`和`order_offset`为NULL，应该跳过或使用默认值
2. **数据验证**：确保只有PENDING类型的价格线才有这些字段的值
3. **性能考虑**：触发逻辑应该尽量减少数据库查询，优先使用内存中的价格线对象
4. **字段区分**：
   - `volume`：用于入场线的持仓手数（已存在）
   - `order_volume`：用于挂单线的订单手数（新增）
   - 两者用途不同，需要区分

## 实现细节

### 1. PriceLineItem类扩展

需要添加的字段和方法：

```python
# 在__init__中添加
self._order_volume: Optional[float] = None  # 挂单线的订单手数
self._order_offset: Optional[str] = None    # 挂单线的开平类型（"OPEN"/"CLOSE"）

# 添加方法
def get_order_volume(self) -> Optional[float]:
    """获取挂单线的订单手数（仅PENDING类型）"""
    return getattr(self, '_order_volume', None)

def set_order_volume(self, volume: float) -> None:
    """设置挂单线的订单手数（仅PENDING类型）"""
    self._order_volume = volume

def get_order_offset(self) -> Optional[str]:
    """获取挂单线的开平类型（仅PENDING类型）"""
    return getattr(self, '_order_offset', None)

def set_order_offset(self, offset: str) -> None:
    """设置挂单线的开平类型（仅PENDING类型）"""
    self._order_offset = offset
```

### 2. 数据库迁移脚本

```sql
-- 添加新字段
ALTER TABLE price_lines ADD COLUMN order_volume REAL;
ALTER TABLE price_lines ADD COLUMN order_offset TEXT;

-- 创建索引（可选，提高查询性能）
CREATE INDEX IF NOT EXISTS idx_price_lines_order_params 
ON price_lines(line_type, order_volume) 
WHERE line_type = 'pending';
```

### 3. 触发逻辑简化示例

```python
def trigger_pending_order_breakthrough(self, line_id: str, line: PriceLineItem, tick: TickData) -> bool:
    """简化后的触发逻辑，从价格线对象获取参数"""
    
    # 从价格线对象获取参数（减少对内存的依赖）
    order_volume = line.get_order_volume()
    order_offset_str = line.get_order_offset()
    
    if order_volume is None or order_offset_str is None:
        # 从数据库加载的旧挂单线，没有挂单参数
        return False
    
    # 从价格线获取其他信息
    price = line.get_price()
    direction_str = line.get_direction()
    vt_symbol = self._vt_symbol  # 或从价格线获取
    
    # 转换为枚举类型
    from vnpy.trader.constant import Direction, Offset
    direction = Direction.LONG if direction_str == "long" else Direction.SHORT
    offset = Offset.OPEN if order_offset_str == "OPEN" else Offset.CLOSE
    
    # 获取合约对象（从main_engine获取，不需要持久化）
    contract = main_engine.get_contract(vt_symbol)
    if not contract:
        return False
    
    # 创建订单请求
    req = OrderRequest(
        symbol=contract.symbol,
        exchange=contract.exchange,
        direction=direction,
        type=OrderType.LIMIT,
        volume=order_volume,
        price=price,
        offset=offset
    )
    
    # 发送订单
    vt_orderid = main_engine.send_order(req, contract.gateway_name)
    return vt_orderid is not None
```

### 4. 创建挂单时的保存逻辑

```python
# 在_create_pending_order_line方法中
# 1. 创建价格线
line_id = controller.create_pending_order_line(price=params["price"], direction=direction_str)

# 2. 设置挂单参数到价格线对象
line = self.chart._price_line_manager.get_line(line_id)
if line:
    line.set_order_volume(params["volume"])
    line.set_order_offset(params["offset"].value)  # 转换为字符串
    
    # 3. 保存到数据库（PriceLineManager会自动保存）
    # 4. 同时保存到内存（保持向后兼容）
    controller._pending_order_params[line_id] = {
        "params": params,
        "vt_symbol": vt_symbol,
        "contract": contract
    }
```

## 总结

### 需要持久化的最小字段集合

1. **order_volume** (REAL): 挂单手数
2. **order_offset** (TEXT): 开平类型（"OPEN"/"CLOSE"）

### 不需要持久化的字段

1. **contract对象**：可以从`vt_symbol`和`main_engine`获取
2. **price_precision**：已存储在`price_lines.price_precision`字段
3. **direction**：已存储在`price_lines.direction`字段
4. **price**：已存储在`price_lines.price`字段
5. **vt_symbol**：已存储在`price_lines.vt_symbol`字段

### 触发逻辑的简化

- **减少依赖**：从价格线对象直接获取参数，而不是从内存中的`_pending_order_params`
- **提高可靠性**：即使程序重启，从数据库加载的挂单线也能正常触发
- **保持兼容**：仍然支持内存中的挂单参数，但优先使用价格线对象中的参数

