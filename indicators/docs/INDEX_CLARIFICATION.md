# IndicatorManager index 参数说明

## 重要澄清

**`index` 参数是指对应 `interval` 参数的周期数，不是调用它的周期数。**

## 详细说明

### 基本规则

```python
get_indicator(
    interval: Interval,      # 指定要获取哪个周期的指标
    indicator_name: str,    # 指标名称
    index: int = -1         # 相对于该 interval 的索引
)
```

**关键点**：
- `index` 是相对于 `interval` 参数的周期数
- **不是**相对于调用它的周期数

### 示例说明

#### 示例1：在1分钟周期中获取5分钟指标

```python
def on_bar(self, bar: BarData) -> None:
    """1分钟K线更新"""
    
    # 获取5分钟指标的最新值
    wma_5min = self.indicator_manager.get_indicator(
        interval=Interval.MINUTE_5,  # 指定5分钟周期
        indicator_name="custom_wma",
        index=-1  # ⚠️ 这里的 index=-1 是指5分钟周期的最后一个值，不是1分钟周期
    )
```

**说明**：
- `interval=Interval.MINUTE_5`：指定获取5分钟周期的指标
- `index=-1`：5分钟周期的最后一个值（最新的5分钟K线）
- **不是**：1分钟周期的最后一个值

#### 示例2：在1分钟周期中获取5分钟指标的历史值

```python
def on_bar(self, bar: BarData) -> None:
    """1分钟K线更新"""
    
    # 获取5分钟指标的200个周期前的值
    wma_5min_200_ago = self.indicator_manager.get_indicator(
        interval=Interval.MINUTE_5,  # 指定5分钟周期
        indicator_name="custom_wma",
        index=-201  # ⚠️ 这里的 index=-201 是指5分钟周期的200个周期前，不是1分钟周期
    )
```

**说明**：
- `index=-201`：5分钟周期的200个周期前（即200根5分钟K线前）
- **不是**：1分钟周期的200个周期前

### 周期对应关系

| 调用周期 | interval 参数 | index 含义 | 实际含义 |
|---------|--------------|-----------|---------|
| 1分钟 | `Interval.MINUTE_5` | `index=-1` | 最新的5分钟K线 |
| 1分钟 | `Interval.MINUTE_5` | `index=-2` | 1个5分钟K线前 |
| 1分钟 | `Interval.MINUTE_5` | `index=-201` | 200个5分钟K线前 |
| 1分钟 | `Interval.MINUTE` | `index=-1` | 最新的1分钟K线 |
| 1分钟 | `Interval.MINUTE` | `index=-201` | 200个1分钟K线前 |

### 时间换算

**5分钟周期的200个周期前**：
- 200根5分钟K线 = 200 × 5 = 1000分钟 = 约16.7小时

**1分钟周期的200个周期前**：
- 200根1分钟K线 = 200分钟 = 约3.3小时

**重要**：在1分钟周期中获取5分钟指标的 `index=-201`，是指200根5分钟K线前，不是200根1分钟K线前！

## 实际应用示例

### 场景1：在1分钟周期中比较当前5分钟指标和200个5分钟周期前的值

```python
def on_bar(self, bar: BarData) -> None:
    """1分钟K线更新"""
    
    # 获取5分钟指标的最新值（最新的5分钟K线）
    wma_5min_current = self.indicator_manager.get_indicator(
        Interval.MINUTE_5,
        "custom_wma",
        index=-1  # 5分钟周期的最后一个值
    )
    
    # 获取5分钟指标的200个周期前的值（200根5分钟K线前）
    wma_5min_200_ago = self.indicator_manager.get_indicator(
        Interval.MINUTE_5,
        "custom_wma",
        index=-201  # 5分钟周期的200个周期前
    )
    
    if wma_5min_current is None or wma_5min_200_ago is None:
        return
    
    # 计算200个5分钟周期的涨跌幅
    change_pct = (wma_5min_current - wma_5min_200_ago) / wma_5min_200_ago * 100
    
    # 注意：这是200根5分钟K线的涨跌幅，不是200根1分钟K线
    self.write_log(
        f"5分钟指标200周期涨跌幅: {change_pct:.2f}% "
        f"(200根5分钟K线 = 1000分钟 = 约16.7小时)"
    )
```

### 场景2：在1分钟周期中获取1分钟指标的历史值

```python
def on_bar(self, bar: BarData) -> None:
    """1分钟K线更新"""
    
    # 获取1分钟指标的最新值
    wma_1min_current = self.indicator_manager.get_indicator(
        Interval.MINUTE,      # 指定1分钟周期
        "custom_wma",
        index=-1  # 1分钟周期的最后一个值
    )
    
    # 获取1分钟指标的200个周期前的值（200根1分钟K线前）
    wma_1min_200_ago = self.indicator_manager.get_indicator(
        Interval.MINUTE,      # 指定1分钟周期
        "custom_wma",
        index=-201  # 1分钟周期的200个周期前
    )
    
    # 计算200个1分钟周期的涨跌幅（200分钟 = 约3.3小时）
    if wma_1min_current and wma_1min_200_ago:
        change_pct = (wma_1min_current - wma_1min_200_ago) / wma_1min_200_ago * 100
```

### 场景3：混合使用不同周期的历史值

```python
def on_bar(self, bar: BarData) -> None:
    """1分钟K线更新"""
    
    # 1分钟指标：200个1分钟周期前（200分钟前）
    wma_1min_200_ago = self.indicator_manager.get_indicator(
        Interval.MINUTE,
        "custom_wma",
        index=-201  # 200根1分钟K线前
    )
    
    # 5分钟指标：200个5分钟周期前（1000分钟前）
    wma_5min_200_ago = self.indicator_manager.get_indicator(
        Interval.MINUTE_5,
        "custom_wma",
        index=-201  # 200根5分钟K线前
    )
    
    # 注意：这两个值的时间跨度不同！
    # wma_1min_200_ago: 200分钟前
    # wma_5min_200_ago: 1000分钟前
```

## 常见误解

### 误解1：在1分钟周期中，index=-201 是指200根1分钟K线前

**错误理解**：
```python
# 在1分钟K线的 on_bar 中
wma_5min = manager.get_indicator(
    Interval.MINUTE_5,
    "custom_wma",
    index=-201  # 错误理解：200根1分钟K线前
)
```

**正确理解**：
```python
# 在1分钟K线的 on_bar 中
wma_5min = manager.get_indicator(
    Interval.MINUTE_5,  # 指定5分钟周期
    "custom_wma",
    index=-201  # 正确：200根5分钟K线前（1000分钟前）
)
```

### 误解2：index 是相对于调用周期的

**错误理解**：
- 在1分钟周期中调用，`index=-201` 就是200根1分钟K线前

**正确理解**：
- `index=-201` 是相对于 `interval` 参数的周期数
- 如果 `interval=Interval.MINUTE_5`，就是200根5分钟K线前
- 如果 `interval=Interval.MINUTE`，就是200根1分钟K线前

## 时间换算表

### 5分钟周期

| index | 周期数 | 时间跨度（分钟） | 时间跨度（小时） |
|-------|--------|----------------|----------------|
| -1 | 最新 | 0 | 0 |
| -2 | 1个周期前 | 5 | 0.08 |
| -11 | 10个周期前 | 50 | 0.83 |
| -51 | 50个周期前 | 250 | 4.17 |
| -201 | 200个周期前 | 1000 | 16.67 |

### 1分钟周期

| index | 周期数 | 时间跨度（分钟） | 时间跨度（小时） |
|-------|--------|----------------|----------------|
| -1 | 最新 | 0 | 0 |
| -2 | 1个周期前 | 1 | 0.02 |
| -11 | 10个周期前 | 10 | 0.17 |
| -51 | 50个周期前 | 50 | 0.83 |
| -201 | 200个周期前 | 200 | 3.33 |

## 总结

1. **`index` 是相对于 `interval` 参数的周期数**，不是调用它的周期数
2. **在1分钟周期中获取5分钟指标**：
   - `index=-1`：最新的5分钟K线
   - `index=-201`：200根5分钟K线前（1000分钟前）
3. **在1分钟周期中获取1分钟指标**：
   - `index=-1`：最新的1分钟K线
   - `index=-201`：200根1分钟K线前（200分钟前）
4. **时间换算**：
   - 5分钟周期的200个周期 = 1000分钟 = 约16.7小时
   - 1分钟周期的200个周期 = 200分钟 = 约3.3小时

