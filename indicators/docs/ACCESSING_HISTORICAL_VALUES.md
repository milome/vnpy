# 访问历史指标值指南

## 1. 使用 get_indicator 方法访问历史值

### 基本用法

`get_indicator` 方法支持通过 `index` 参数访问历史值，`deque` 支持负索引：

```python
# 获取最新值（当前K线）
current_value = manager.get_indicator(
    interval=Interval.MINUTE,
    indicator_name="custom_wma",
    index=-1  # 最新值
)

# 获取上一个值（1个周期前）
prev_value = manager.get_indicator(
    interval=Interval.MINUTE,
    indicator_name="custom_wma",
    index=-2  # 1个周期前
)

# 获取200个周期前的值
value_200_periods_ago = manager.get_indicator(
    interval=Interval.MINUTE,
    indicator_name="custom_wma",
    index=-201  # 200个周期前（注意：-1是当前，-201是200个周期前）
)
```

### 索引说明

**deque 的索引规则**：
- `index=-1`：最新值（当前K线）
- `index=-2`：上一个值（1个周期前）
- `index=-3`：2个周期前
- `index=-201`：200个周期前

**注意**：索引从 `-1` 开始，所以：
- 200个周期前 = `index=-201`（不是 `-200`）

## 2. 完整示例

### 示例1：比较当前值和200个周期前的值

```python
def on_bar(self, bar: BarData):
    """K线更新"""
    # 更新指标
    self.indicator_manager.update_indicator(Interval.MINUTE, bar)
    
    # 获取当前值
    current_wma = self.indicator_manager.get_indicator(
        Interval.MINUTE,
        "custom_wma",
        index=-1
    )
    
    # 获取200个周期前的值
    wma_200_periods_ago = self.indicator_manager.get_indicator(
        Interval.MINUTE,
        "custom_wma",
        index=-201  # 200个周期前
    )
    
    # 检查数据是否足够
    if current_wma is None or wma_200_periods_ago is None:
        self.write_log("数据不足，无法比较")
        return
    
    # 比较：如果当前值比200个周期前高20%，做多
    if current_wma > wma_200_periods_ago * 1.2:
        if self.pos == 0:
            self.buy(bar.close_price, self.fixed_size)
            self.write_log(
                f"买入信号: 当前WMA={current_wma:.2f}, "
                f"200周期前WMA={wma_200_periods_ago:.2f}"
            )
```

### 示例2：计算200周期内的涨跌幅

```python
def calculate_200_period_change(self, interval: Interval, indicator_name: str) -> Optional[float]:
    """计算200个周期内的涨跌幅"""
    current_value = self.indicator_manager.get_indicator(
        interval,
        indicator_name,
        index=-1
    )
    
    value_200_ago = self.indicator_manager.get_indicator(
        interval,
        indicator_name,
        index=-201  # 200个周期前
    )
    
    if current_value is None or value_200_ago is None:
        return None
    
    if value_200_ago == 0:
        return None
    
    # 计算涨跌幅（百分比）
    change_pct = (current_value - value_200_ago) / value_200_ago * 100
    return change_pct

# 使用
def on_bar(self, bar: BarData):
    self.indicator_manager.update_indicator(Interval.MINUTE, bar)
    
    change_pct = self.calculate_200_period_change(
        Interval.MINUTE,
        "custom_wma"
    )
    
    if change_pct is not None:
        self.write_log(f"200周期涨跌幅: {change_pct:.2f}%")
```

### 示例3：获取多个历史值进行比较

```python
def on_bar(self, bar: BarData):
    """K线更新"""
    self.indicator_manager.update_indicator(Interval.MINUTE, bar)
    
    # 获取多个历史值
    current = self.indicator_manager.get_indicator(
        Interval.MINUTE, "custom_wma", index=-1
    )
    prev_10 = self.indicator_manager.get_indicator(
        Interval.MINUTE, "custom_wma", index=-11  # 10个周期前
    )
    prev_50 = self.indicator_manager.get_indicator(
        Interval.MINUTE, "custom_wma", index=-51  # 50个周期前
    )
    prev_200 = self.indicator_manager.get_indicator(
        Interval.MINUTE, "custom_wma", index=-201  # 200个周期前
    )
    
    # 检查数据完整性
    if any(v is None for v in [current, prev_10, prev_50, prev_200]):
        return
    
    # 策略逻辑：如果当前值 > 10周期前 > 50周期前 > 200周期前，趋势向上
    if current > prev_10 > prev_50 > prev_200:
        if self.pos == 0:
            self.buy(bar.close_price, self.fixed_size)
            self.write_log("趋势向上，买入")
```

## 3. 使用 get_indicator_array 方法

如果需要获取一段连续的历史值，可以使用 `get_indicator_array`：

```python
# 获取最近200个值（包括当前值）
wma_array = self.indicator_manager.get_indicator_array(
    Interval.MINUTE,
    "custom_wma",
    length=200
)

if wma_array is not None and len(wma_array) >= 200:
    current_value = wma_array[-1]      # 最新值
    value_200_ago = wma_array[0]       # 200个周期前的值（数组的第一个元素）
    
    # 计算涨跌幅
    change_pct = (current_value - value_200_ago) / value_200_ago * 100
```

### 数组索引说明

使用 `get_indicator_array` 时：
- `array[-1]`：最新值（当前K线）
- `array[0]`：最旧的值（如果length=200，则是200个周期前）
- `array[-200]`：200个周期前的值（如果数组长度>=200）

## 4. 数据完整性检查

### 检查数据是否足够

```python
def get_indicator_safe(self, interval, indicator_name, index):
    """安全获取指标值，检查数据是否足够"""
    # 获取deque长度
    if interval not in self.indicator_manager.indicators:
        return None
    
    if indicator_name not in self.indicator_manager.indicators[interval]:
        return None
    
    deque_length = len(self.indicator_manager.indicators[interval][indicator_name])
    
    # 检查索引是否有效
    if abs(index) > deque_length:
        self.write_log(
            f"警告: 请求的索引 {index} 超出数据范围 "
            f"(当前数据量: {deque_length})"
        )
        return None
    
    # 获取值
    return self.indicator_manager.get_indicator(interval, indicator_name, index)

# 使用
def on_bar(self, bar: BarData):
    # 安全获取200个周期前的值
    value_200_ago = self.get_indicator_safe(
        Interval.MINUTE,
        "custom_wma",
        index=-201
    )
    
    if value_200_ago is None:
        return  # 数据不足，跳过
```

## 5. 性能考虑

### 直接访问 vs 数组转换

**方法1：直接访问（推荐）**
```python
# 只访问一个值，性能最好
value = manager.get_indicator(Interval.MINUTE, "custom_wma", index=-201)
```
- **性能**：O(1)，直接索引访问
- **内存**：不创建额外数组

**方法2：获取数组**
```python
# 需要获取多个值时使用
array = manager.get_indicator_array(Interval.MINUTE, "custom_wma", length=200)
value_200_ago = array[0]
```
- **性能**：O(n)，需要转换为list再转numpy数组
- **内存**：创建临时数组

### 推荐

- **单个值访问**：使用 `get_indicator(index=-201)`
- **多个值访问**：使用 `get_indicator_array(length=200)`

## 6. 实际应用场景

### 场景1：长期趋势判断

```python
def check_long_term_trend(self):
    """检查长期趋势（200周期）"""
    current = self.indicator_manager.get_indicator(
        Interval.MINUTE, "custom_wma", index=-1
    )
    value_200_ago = self.indicator_manager.get_indicator(
        Interval.MINUTE, "custom_wma", index=-201
    )
    
    if current is None or value_200_ago is None:
        return None
    
    # 计算200周期涨幅
    change = (current - value_200_ago) / value_200_ago
    
    if change > 0.1:  # 上涨超过10%
        return "strong_uptrend"
    elif change < -0.1:  # 下跌超过10%
        return "strong_downtrend"
    else:
        return "sideways"
```

### 场景2：历史极值比较

```python
def compare_with_200_period_high(self):
    """比较当前值与200周期内的最高值"""
    current = self.indicator_manager.get_indicator(
        Interval.MINUTE, "custom_wma", index=-1
    )
    
    # 获取最近200个值
    array = self.indicator_manager.get_indicator_array(
        Interval.MINUTE, "custom_wma", length=200
    )
    
    if current is None or array is None or len(array) < 200:
        return None
    
    # 计算200周期内的最高值
    max_value = np.max(array)
    
    # 如果当前值接近最高值（95%以上），可能是顶部
    if current >= max_value * 0.95:
        return "near_high"
    
    return "normal"
```

## 7. 注意事项

### 1. 索引计算

- `index=-1`：最新值（当前K线）
- `index=-201`：200个周期前
- **公式**：N个周期前 = `index=-(N+1)`

### 2. 数据量检查

在访问200个周期前的值之前，确保deque中有足够的数据：

```python
# 检查数据量
deque_length = len(self.indicator_manager.indicators[interval][indicator_name])
if deque_length < 201:  # 需要至少201个值（包括当前值）
    self.write_log(f"数据不足: 当前只有 {deque_length} 个值，需要至少201个")
    return
```

### 3. None值处理

如果索引超出范围，`get_indicator` 会返回 `None`：

```python
value = manager.get_indicator(Interval.MINUTE, "custom_wma", index=-201)
if value is None:
    # 数据不足或索引无效
    return
```

## 总结

1. **访问200个周期前的值**：使用 `index=-201`
2. **索引规则**：N个周期前 = `index=-(N+1)`
3. **数据检查**：确保deque长度 >= 201
4. **性能优化**：单个值用 `get_indicator`，多个值用 `get_indicator_array`
5. **错误处理**：检查返回值是否为 `None`

