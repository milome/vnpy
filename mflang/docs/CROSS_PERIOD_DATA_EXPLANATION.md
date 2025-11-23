# 跨周期数据加载机制说明

## 问题：如何知道应该加载哪个周期的数据？

根据 `#IMPORT` 的定义：`#IMPORT [PERIOD,N,FORMULA] AS VAR`

周期信息（PERIOD 和 N）必须从 `#IMPORT` 语句中解析得到，用于确定需要加载哪个周期的数据。

例如：`#IMPORT[MIN,5,MIN5_OPEN] AS MIN5` 表示引用5分钟周期的数据。

在生成的策略代码中，周期信息通过以下机制确定：

## 完整流程

### 1. 解析 #IMPORT 语句（在 `__init__` 中）

```python
# 在 __init__ 方法中
self.import_statements = ImportParser.parse_code("""
#IMPORT[MIN,5,MIN5_OPEN] AS MIN5
""")
```

**关键信息提取：**
- `PERIOD = "MIN"` - 周期类型（分钟）
- `N = 5` - 周期数（5分钟）
- `FORMULA = "MIN5_OPEN"` - 模型文件名
- `VAR = "MIN5"` - 变量名

### 2. 创建对应的数据管理器（在 `__init__` 中）

```python
# 根据 #IMPORT 语句创建对应的 ArrayManager
self.min5_am = ArrayManager()  # MIN5周期数据
self.min5_vars = {}  # MIN5 的变量缓存
```

**命名规则：**
- 变量名 `MIN5` → 数据管理器 `self.min5_am`
- 变量名 `MIN5` → 变量缓存 `self.min5_vars`

### 3. 从 #IMPORT 语句中获取 PERIOD 和 N（在 `on_bar` 中）

**关键改进：** 不再硬编码周期信息，而是从 `self.import_statements` 中动态获取。

```python
def on_bar(self, bar: BarData):
    # 处理跨周期数据
    # 从 #IMPORT 语句中获取 PERIOD 和 N，确定需要加载哪个周期的数据
    # 遍历所有 #IMPORT 语句，根据 PERIOD 和 N 判断当前K线是否为目标周期
    for stmt in self.import_statements:
        # 从 #IMPORT 语句中获取周期信息：PERIOD 和 N
        # 例如：#IMPORT[MIN,5,MIN5_OPEN] AS MIN5
        #      PERIOD = MIN, N = 5，表示需要5分钟周期的数据
        period_type = stmt.period.value  # 周期类型（MIN, HOUR, DAY等）
        period_n = stmt.n  # 周期参数（如5表示5分钟）
        
        # 判断当前K线是否是目标周期的K线
        if self._is_period_bar(bar, period_type, period_n):
            # 更新对应周期的数据管理器
            am = getattr(self, f"{stmt.var_name.lower()}_am")
            am.update_bar(bar)
            
            # 如果数据已初始化，计算跨周期变量
            if am.inited:
                self._calculate_cross_period_vars(stmt.var_name, stmt.formula)
```

**`_is_period_bar` 方法：**
```python
def _is_period_bar(self, bar: BarData, period_type: str, n: int) -> bool:
    """
    判断是否是目标周期的K线
    
    参数:
        period_type: 周期类型（来自 #IMPORT 语句的 PERIOD，如 "MIN", "HOUR", "DAY"）
        n: 周期参数（来自 #IMPORT 语句的 N，如 5 表示5分钟）
    
    说明:
        根据 #IMPORT 语句中的 PERIOD 和 N 来判断当前K线是否为目标周期
        例如：#IMPORT[MIN,5,MIN5_OPEN] AS MIN5
             PERIOD=MIN, N=5，表示需要5分钟周期的数据
             判断条件：bar.datetime.minute % 5 == 0
    """
    if period_type == "MIN":
        # 分钟周期：判断分钟数是否能被N整除
        # 例如：N=5 表示5分钟周期，分钟数 % 5 == 0 时是5分钟K线
        return bar.datetime.minute % n == 0
    elif period_type == "HOUR":
        # 小时周期：判断小时数是否能被N整除，且分钟数为0
        return bar.datetime.hour % n == 0 and bar.datetime.minute == 0
    elif period_type == "DAY":
        # 日周期：判断是否是交易日开始
        return bar.datetime.hour == 0 and bar.datetime.minute == 0
    # ... 其他周期类型
```

### 4. 通过变量名获取对应的数据管理器（在 `_calculate_cross_period_vars` 中）

```python
def _calculate_cross_period_vars(self, var_name: str, model_name: str):
    """
    计算跨周期变量
    
    参数:
        var_name: 跨周期变量名（如 "MIN5"），来自 #IMPORT 语句的 VAR
        model_name: 模型文件名（如 "MIN5_OPEN"），来自 #IMPORT 语句的 FORMULA
    
    说明:
        周期信息（PERIOD 和 N）从 #IMPORT 语句中解析得到：
        - 在 __init__ 中解析 #IMPORT 语句，存储在 self.import_statements 中
        - 在 on_bar 中通过遍历 self.import_statements 获取 PERIOD 和 N
        - 根据 PERIOD 和 N 判断当前K线是否为目标周期
        - 如果是目标周期，更新对应的 ArrayManager（如 self.min5_am）
        - 使用 ArrayManager 中的数据计算模型文件中定义的变量
    """
    # 加载模型文件
    model = load_model(model_name)
    
    # 获取对应的ArrayManager
    # 命名规则：var_name.lower() + "_am" = "min5_am"
    # 这个 ArrayManager 中存储的是对应周期的数据
    # 周期信息（PERIOD 和 N）由 on_bar 中的逻辑确定
    am = getattr(self, f"{var_name.lower()}_am")
    
    # 使用这个 ArrayManager 中的数据计算变量
    # am.open, am.close 等就是对应周期的数据（如5分钟周期）
```

## 关键点说明

### 1. 周期信息从 #IMPORT 语句中解析

**重要：** 周期信息（PERIOD 和 N）必须从 `#IMPORT` 语句中解析得到，不能硬编码。

```python
# 模型文件 TEST_IMPORT 中包含：
#IMPORT[MIN,5,MIN5_OPEN] AS MIN5

# 在 __init__ 中解析
self.import_statements = ImportParser.parse_code("""
#IMPORT[MIN,5,MIN5_OPEN] AS MIN5
""")

# import_statements[0] 包含：
# - period: PeriodType.MIN  (PERIOD，周期类型：分钟)
# - n: 5                    (N，周期参数：5分钟)
# - formula: "MIN5_OPEN"    (FORMULA，模型文件名)
# - var_name: "MIN5"        (VAR，变量名)
```

**解析过程：**
- `PERIOD = "MIN"` → `stmt.period.value = "MIN"`
- `N = 5` → `stmt.n = 5`
- `FORMULA = "MIN5_OPEN"` → `stmt.formula = "MIN5_OPEN"`
- `VAR = "MIN5"` → `stmt.var_name = "MIN5"`

### 2. 数据管理器的命名规则

数据管理器通过变量名（`var_name`）来命名：

```python
# 变量名 "MIN5" → 数据管理器 "min5_am"
self.min5_am = ArrayManager()

# 在 _calculate_cross_period_vars 中通过变量名获取
am = getattr(self, f"{var_name.lower()}_am")  # var_name="MIN5" → "min5_am"
```

### 3. 周期判断的时机（从 #IMPORT 语句中动态获取）

周期判断在 `on_bar` 方法中进行，每次收到K线时，**从 `self.import_statements` 中动态获取 PERIOD 和 N**：

```python
def on_bar(self, bar: BarData):
    # 遍历所有 #IMPORT 语句
    for stmt in self.import_statements:
        # 从 #IMPORT 语句中获取周期信息：PERIOD 和 N
        period_type = stmt.period.value  # 从 #IMPORT 语句解析得到（如 "MIN"）
        period_n = stmt.n  # 从 #IMPORT 语句解析得到（如 5）
        
        # 判断当前K线是否是目标周期的K线
        if self._is_period_bar(bar, period_type, period_n):
            # 只有当K线是目标周期时，才更新对应周期的数据
            am = getattr(self, f"{stmt.var_name.lower()}_am")
            am.update_bar(bar)
            if am.inited:
                # 计算跨周期变量
                self._calculate_cross_period_vars(stmt.var_name, stmt.formula)
```

**关键改进：**
- ❌ **错误做法**：硬编码 `_is_period_bar(bar, "MIN", 5)`
- ✅ **正确做法**：从 `stmt.period.value` 和 `stmt.n` 动态获取

### 4. 数据对齐机制

- **当前周期**：策略运行在1分钟周期上（`self.am`）
- **跨周期**：需要5分钟周期的数据（`self.min5_am`）
- **更新时机**：只有当收到5分钟周期的K线时，才更新 `self.min5_am`
- **使用时机**：每次 `on_bar` 都会使用 `self.min5_vars` 中的缓存值

## 改进建议

当前的实现中，`_is_period_bar` 方法中的周期信息是硬编码的。可以改进为从 `self.import_statements` 中动态获取：

```python
def on_bar(self, bar: BarData):
    # 遍历所有 #IMPORT 语句
    for stmt in self.import_statements:
        # 从 import_statements 中获取周期信息
        if self._is_period_bar(bar, stmt.period.value, stmt.n):
            # 获取对应的数据管理器
            am = getattr(self, f"{stmt.var_name.lower()}_am")
            am.update_bar(bar)
            if am.inited:
                self._calculate_cross_period_vars(stmt.var_name, stmt.formula)
```

这样就不需要在代码中硬编码周期信息了。

## 总结

**周期信息的传递路径（从 #IMPORT 语句中解析）：**

1. **模型文件** (`TEST_IMPORT`) → `#IMPORT[MIN,5,MIN5_OPEN] AS MIN5`
   - PERIOD = "MIN"（周期类型）
   - N = 5（周期参数）
   - FORMULA = "MIN5_OPEN"（模型文件名）
   - VAR = "MIN5"（变量名）

2. **解析 #IMPORT 语句** (`__init__`) → `self.import_statements` 存储周期信息
   - `stmt.period.value = "MIN"`（从 PERIOD 解析）
   - `stmt.n = 5`（从 N 解析）
   - `stmt.formula = "MIN5_OPEN"`（从 FORMULA 解析）
   - `stmt.var_name = "MIN5"`（从 VAR 解析）

3. **创建管理器** (`__init__`) → `self.min5_am` 用于存储5分钟数据
   - 根据 `stmt.var_name` 创建对应的 ArrayManager

4. **从 #IMPORT 语句获取周期信息** (`on_bar`) → 遍历 `self.import_statements`
   - `period_type = stmt.period.value`（从 #IMPORT 语句获取 PERIOD）
   - `period_n = stmt.n`（从 #IMPORT 语句获取 N）

5. **判断周期** (`on_bar`) → `_is_period_bar(bar, period_type, period_n)` 判断是否是目标周期K线
   - 使用从 #IMPORT 语句解析得到的 `period_type` 和 `period_n`

6. **更新数据** (`on_bar`) → `self.min5_am.update_bar(bar)` 更新目标周期数据
   - 只有当K线是目标周期时才更新

7. **计算变量** (`_calculate_cross_period_vars`) → 通过 `var_name="MIN5"` 获取 `self.min5_am`
   - 使用对应周期的数据计算模型文件中定义的变量

**关键：** 
- ✅ **正确做法**：周期信息（PERIOD 和 N）必须从 `#IMPORT` 语句中解析得到
- ✅ **正确做法**：在 `on_bar` 中遍历 `self.import_statements`，动态获取 `stmt.period.value` 和 `stmt.n`
- ❌ **错误做法**：硬编码周期信息（如 `_is_period_bar(bar, "MIN", 5)`）

**示例：**
- `#IMPORT[MIN,2,MACD] AS VAR` → PERIOD=MIN, N=2，表示需要2分钟周期的数据
- `#IMPORT[MIN,5,MIN5_OPEN] AS MIN5` → PERIOD=MIN, N=5，表示需要5分钟周期的数据
- `#IMPORT[HOUR,1,HOURLY] AS H1` → PERIOD=HOUR, N=1，表示需要1小时周期的数据

