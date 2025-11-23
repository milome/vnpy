# IndicatorManager 内存数据结构说明

## 1. 数据结构概览

### IndicatorManager 使用的数据结构

**IndicatorManager** 使用 **`collections.deque`** 来存储指标计算结果，**不是** `ArrayManager`。

### 数据结构定义

```python
# 指标值存储（历史值：已完成的K线对应的指标值）
# 结构: {interval: {indicator_name: deque([...])}}
self.indicators: Dict[Interval, Dict[str, deque]] = {}

# 指标对应的时间戳（用于parquet格式存储和查询）
# 结构: {interval: {indicator_name: deque([datetime, ...])}}
self.indicator_timestamps: Dict[Interval, Dict[str, deque]] = {}

# 运行时指标值（正在聚合的K线对应的指标值）
# 结构: {interval: {indicator_name: value}}
self.runtime_indicators: Dict[Interval, Dict[str, Any]] = {}
```

## 2. 数据存储结构详解

### 2年多周期指标数据的内存结构

假设有2个周期（1分钟、5分钟），每个周期有3个指标：

```python
self.indicators = {
    Interval.MINUTE: {
        "custom_wma": deque([25500.5, 25501.2, ..., 26000.0], maxlen=50000),
        "custom_rsi": deque([65.3, 66.1, ..., 70.2], maxlen=50000),
        "custom_macd": deque([12.5, 13.1, ..., 15.0], maxlen=50000)
    },
    Interval.MINUTE_5: {
        "custom_wma": deque([25500.0, 25510.0, ..., 26000.0], maxlen=10000),
        "custom_rsi": deque([60.0, 61.0, ..., 65.0], maxlen=10000),
        "custom_macd": deque([10.0, 11.0, ..., 12.0], maxlen=10000)
    }
}

self.indicator_timestamps = {
    Interval.MINUTE: {
        "custom_wma": deque([datetime(2022,1,1,9,0), datetime(2022,1,1,9,1), ...], maxlen=50000),
        "custom_rsi": deque([datetime(2022,1,1,9,0), datetime(2022,1,1,9,1), ...], maxlen=50000),
        "custom_macd": deque([datetime(2022,1,1,9,0), datetime(2022,1,1,9,1), ...], maxlen=50000)
    },
    Interval.MINUTE_5: {
        "custom_wma": deque([datetime(2022,1,1,9,0), datetime(2022,1,1,9,5), ...], maxlen=10000),
        ...
    }
}
```

## 3. 与 ArrayManager 的区别

### ArrayManager（vnpy_ctastrategy）

**用途**：存储K线原始数据（open, high, low, close, volume等）

**数据结构**：
```python
class ArrayManager:
    def __init__(self, size: int = 100):
        self.open_array: np.ndarray = np.zeros(size)   # numpy数组
        self.high_array: np.ndarray = np.zeros(size)
        self.low_array: np.ndarray = np.zeros(size)
        self.close_array: np.ndarray = np.zeros(size)
        self.volume_array: np.ndarray = np.zeros(size)
        # ...
```

**特点**：
- 使用 `numpy.ndarray`（固定大小，滚动窗口）
- 默认只存储 **100根K线**
- 存储K线原始数据（价格、成交量等）
- 提供talib指标计算函数（MA、RSI、MACD等）

### IndicatorManager

**用途**：存储自定义指标计算结果

**数据结构**：
```python
class IndicatorManager:
    def __init__(self, ...):
        # 使用 deque 存储指标值
        self.indicators: Dict[Interval, Dict[str, deque]] = {}
        self.indicator_timestamps: Dict[Interval, Dict[str, deque]] = {}
```

**特点**：
- 使用 `collections.deque`（双端队列，可设置maxlen）
- 可存储 **大量历史数据**（通过 `max_history` 参数，如50000）
- 存储指标计算结果（float值）
- 支持自定义指标计算函数

## 4. 数据加载流程

### 从文件加载到内存

```python
def _load_indicator_from_parquet(self, interval: Interval):
    """从parquet文件加载指标数据到deque"""
    # 1. 读取parquet文件
    df = pl.read_parquet(filepath)
    
    # 2. 按指标名称分组
    for indicator_name in df["indicator_name"].unique():
        indicator_data = df.filter(pl.col("indicator_name") == indicator_name)
        
        # 3. 获取对应的deque
        indicator_deque = self.indicators[interval][indicator_name]
        timestamp_deque = self.indicator_timestamps[interval][indicator_name]
        
        # 4. 清空并恢复数据
        indicator_deque.clear()
        timestamp_deque.clear()
        
        # 5. 将文件中的数据append到deque
        for row in indicator_data.iter_rows(named=True):
            value = row["value"]
            dt = row["datetime"]
            indicator_deque.append(value)      # 指标值
            timestamp_deque.append(dt)          # 时间戳
```

### 数据在内存中的存储

**2年1分钟指标数据（50000个值）**：
```python
# 内存中的实际结构
indicator_deque = deque([
    25500.5,   # 第1根K线的指标值
    25501.2,   # 第2根K线的指标值
    25502.0,   # 第3根K线的指标值
    ...
    26000.0    # 第50000根K线的指标值
], maxlen=50000)

timestamp_deque = deque([
    datetime(2022, 1, 1, 9, 0),   # 第1根K线的时间
    datetime(2022, 1, 1, 9, 1),   # 第2根K线的时间
    ...
    datetime(2024, 1, 1, 15, 0)    # 第50000根K线的时间
], maxlen=50000)
```

## 5. 为什么使用 deque 而不是 ArrayManager？

### deque 的优势

1. **动态大小**：
   - `deque` 可以动态增长（受 `maxlen` 限制）
   - `ArrayManager` 使用固定大小的numpy数组（默认100）

2. **内存效率**：
   - `deque` 使用 `maxlen` 自动限制内存（FIFO）
   - 超过 `maxlen` 时自动丢弃最旧的数据

3. **灵活性**：
   - 可以存储任意类型的指标值（float、int、自定义对象）
   - `ArrayManager` 只存储K线原始数据

4. **时间戳支持**：
   - `deque` 可以同时存储指标值和时间戳
   - `ArrayManager` 不存储时间戳（只有索引）

### 使用场景对比

| 特性 | ArrayManager | IndicatorManager |
|------|-------------|------------------|
| **数据结构** | `numpy.ndarray` | `collections.deque` |
| **存储内容** | K线原始数据（OHLCV） | 指标计算结果 |
| **数据量** | 固定100根（可调整） | 可设置（如50000根） |
| **时间戳** | 不支持 | 支持 |
| **用途** | 短期技术指标（MA、RSI） | 长期自定义指标 |
| **内存占用** | ~30KB（100根） | ~4MB（50000根） |

## 6. 数据访问方式

### 获取单个指标值

```python
# 获取最新值（索引-1）
value = manager.get_indicator(Interval.MINUTE, "custom_wma", index=-1)

# 获取上一个值（索引-2）
prev_value = manager.get_indicator(Interval.MINUTE, "custom_wma", index=-2)

# 内部实现：直接从deque获取
indicator_deque = self.indicators[interval][indicator_name]
return indicator_deque[index]  # deque支持负索引
```

### 获取指标数组

```python
# 获取最近20个值
array = manager.get_indicator_array(
    Interval.MINUTE,
    "custom_wma",
    length=20
)

# 内部实现：将deque转换为numpy数组
values = list(indicator_deque)
if length is not None:
    values = values[-length:]
return np.array(values)
```

## 7. 内存占用估算

### 2年多周期指标数据

**1分钟周期（50000个值）**：
- 每个指标值：8字节（float64）
- 每个时间戳：24字节（datetime对象）
- 10个指标：10 × (50000 × 8 + 50000 × 24) = **16MB**

**5分钟周期（10000个值）**：
- 10个指标：10 × (10000 × 8 + 10000 × 24) = **3.2MB**

**总计**：约 **20MB**（包含时间戳）

**优化**：如果不需要时间戳查询，可以只存储指标值，内存占用约 **4-5MB**

## 8. 数据持久化

### 保存到文件

```python
# 从deque转换为list，然后保存
for indicator_name, indicator_deque in self.indicators[interval].items():
    values = list(indicator_deque)  # deque → list
    timestamps = list(self.indicator_timestamps[interval][indicator_name])
    
    # 保存到parquet文件
    data_rows.append({
        "datetime": dt,
        "indicator_name": indicator_name,
        "value": value
    })
```

### 从文件加载

```python
# 从文件读取，恢复到deque
for row in indicator_data.iter_rows(named=True):
    value = row["value"]
    dt = row["datetime"]
    indicator_deque.append(value)      # 恢复到deque
    timestamp_deque.append(dt)
```

## 总结

1. **IndicatorManager 使用 `deque` 存储指标数据**，不是 `ArrayManager`
2. **数据结构**：
   - `self.indicators`: `Dict[Interval, Dict[str, deque]]` - 存储指标值
   - `self.indicator_timestamps`: `Dict[Interval, Dict[str, deque]]` - 存储时间戳
3. **与 ArrayManager 的区别**：
   - ArrayManager：存储K线原始数据（numpy数组，固定100根）
   - IndicatorManager：存储指标计算结果（deque，可设置大量历史数据）
4. **内存占用**：2年多周期数据约20MB（包含时间戳）或4-5MB（仅指标值）
5. **优势**：支持大量历史数据、自动内存管理、时间戳支持

