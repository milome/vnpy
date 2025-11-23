# 周期数据确定机制说明

## 核心原则

根据 `#IMPORT` 的定义：`#IMPORT [PERIOD,N,FORMULA] AS VAR`

**必须从 `#IMPORT` 语句中解析出 PERIOD 和 N 来确定需要加载哪个周期的数据。**

## 示例

### 示例1：2分钟周期

```
#IMPORT[MIN,2,MACD] AS VAR
```

- PERIOD = MIN（分钟周期）
- N = 2（2分钟）
- **需要加载2分钟周期的数据**

### 示例2：5分钟周期

```
#IMPORT[MIN,5,MIN5_OPEN] AS MIN5
```

- PERIOD = MIN（分钟周期）
- N = 5（5分钟）
- **需要加载5分钟周期的数据**

### 示例3：1小时周期

```
#IMPORT[HOUR,1,HOURLY] AS H1
```

- PERIOD = HOUR（小时周期）
- N = 1（1小时）
- **需要加载1小时周期的数据**

## 在策略中的实现

### 1. 解析 #IMPORT 语句（在 `__init__` 中）

```python
def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
    # 解析 #IMPORT 语句
    self.import_statements = ImportParser.parse_code("""
    #IMPORT[MIN,5,MIN5_OPEN] AS MIN5
    """)
    
    # import_statements[0] 包含：
    # - period: PeriodType.MIN  (PERIOD)
    # - n: 5                    (N)
    # - formula: "MIN5_OPEN"    (FORMULA)
    # - var_name: "MIN5"        (VAR)
```

### 2. 从 #IMPORT 语句获取周期信息（在 `on_bar` 中）

```python
def on_bar(self, bar: BarData):
    # 遍历所有 #IMPORT 语句
    for stmt in self.import_statements:
        # 从 #IMPORT 语句中获取周期信息：PERIOD 和 N
        period_type = stmt.period.value  # 获取 PERIOD（如 "MIN"）
        period_n = stmt.n  # 获取 N（如 5）
        
        # 根据 PERIOD 和 N 判断当前K线是否为目标周期
        if self._is_period_bar(bar, period_type, period_n):
            # 更新对应周期的数据
            am = getattr(self, f"{stmt.var_name.lower()}_am")
            am.update_bar(bar)
            if am.inited:
                self._calculate_cross_period_vars(stmt.var_name, stmt.formula)
```

### 3. 判断是否是目标周期

```python
def _is_period_bar(self, bar: BarData, period_type: str, n: int) -> bool:
    """
    根据 #IMPORT 语句中的 PERIOD 和 N 来判断当前K线是否为目标周期
    
    参数:
        period_type: 来自 #IMPORT 语句的 PERIOD（如 "MIN", "HOUR", "DAY"）
        n: 来自 #IMPORT 语句的 N（如 5 表示5分钟）
    """
    if period_type == "MIN":
        # 分钟周期：判断分钟数是否能被N整除
        # 例如：N=5 表示5分钟周期，分钟数 % 5 == 0 时是5分钟K线
        return bar.datetime.minute % n == 0
    elif period_type == "HOUR":
        # 小时周期：判断小时数是否能被N整除，且分钟数为0
        return bar.datetime.hour % n == 0 and bar.datetime.minute == 0
    # ... 其他周期类型
```

## 关键点

### ✅ 正确做法

1. **从 #IMPORT 语句解析周期信息**
   ```python
   for stmt in self.import_statements:
       period_type = stmt.period.value  # 从 #IMPORT 语句获取 PERIOD
       period_n = stmt.n  # 从 #IMPORT 语句获取 N
   ```

2. **根据 PERIOD 和 N 判断周期**
   ```python
   if self._is_period_bar(bar, period_type, period_n):
       # 更新对应周期的数据
   ```

### ❌ 错误做法

1. **硬编码周期信息**
   ```python
   # 错误：硬编码了 "MIN" 和 5
   if self._is_period_bar(bar, "MIN", 5):
   ```

2. **不解析 #IMPORT 语句**
   ```python
   # 错误：没有从 #IMPORT 语句中获取周期信息
   # 应该从 stmt.period.value 和 stmt.n 获取
   ```

## 完整流程

```
#IMPORT[MIN,5,MIN5_OPEN] AS MIN5
    ↓
解析 #IMPORT 语句
    ↓
获取 PERIOD=MIN, N=5
    ↓
创建数据管理器 (self.min5_am)
    ↓
在 on_bar 中：
    ↓
遍历 self.import_statements
    ↓
获取 stmt.period.value = "MIN"
获取 stmt.n = 5
    ↓
判断是否是5分钟K线 (_is_period_bar)
    ↓
更新5分钟数据 (self.min5_am.update_bar)
    ↓
计算跨周期变量 (_calculate_cross_period_vars)
```

## 总结

- ✅ **必须**从 `#IMPORT` 语句中解析出 PERIOD 和 N
- ✅ **必须**在 `on_bar` 中遍历 `self.import_statements` 获取周期信息
- ✅ **必须**根据 PERIOD 和 N 来判断当前K线是否为目标周期
- ❌ **不能**硬编码周期信息
- ❌ **不能**忽略 #IMPORT 语句中的 PERIOD 和 N

