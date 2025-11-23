# #IMPORT 跨周期引用函数使用指南

## 概述

`#IMPORT [PERIOD,N,FORMULA] AS VAR` 用于引用当前合约，PERIOD参数为N的周期，指标FORMULA的数据。

**重要说明：**
- **PERIOD 和 N 共同确定需要加载哪个周期的数据**
  - 例如：`#IMPORT[MIN,2,MACD] AS VAR` 表示引用2分钟周期的数据
  - 例如：`#IMPORT[MIN,5,MIN5_OPEN] AS MIN5` 表示引用5分钟周期的数据
  - 必须从 `#IMPORT` 语句中解析出 PERIOD 和 N 来确定周期
- **FORMULA是模型文件名**，对应 `mflang/mmodels/` 目录下的模型文件
- 模型文件中定义了变量（如 `CC:REF(C,1);`），这些变量可以通过 `VAR.VARIABLE_NAME` 的方式访问
- 例如：`#IMPORT[DAY,1,AA] AS VAR` 表示引用 `mflang/mmodels/AA` 文件中定义的指标

## 快速开始

### 1. 解析 #IMPORT 语句

```python
from mflang import ImportParser

code = """
#IMPORT[DAY,1,AA] AS VAR
CC:VAR.CC;
"""

# 解析所有 #IMPORT 语句
import_statements = ImportParser.parse_code(code)

for stmt in import_statements:
    print(f"周期: {stmt.period.value}")
    print(f"N: {stmt.n}")
    print(f"模型文件: {stmt.formula}")  # FORMULA是模型文件名
    print(f"变量名: {stmt.var_name}")  # VAR是变量名，用于访问模型中的变量
```

### 2. 加载模型文件

```python
from mflang import load_model, get_variable

# 加载模型文件（FORMULA参数对应 mflang/mmodels/ 目录下的文件）
model = load_model("AA")  # 加载 mflang/mmodels/AA 文件
print(f"模型AA中的变量: {model}")
# 输出: {'CC': 'REF(C,1)'}

# 获取模型中的特定变量
cc_expr = get_variable("AA", "CC")
print(f"CC变量的定义: {cc_expr}")  # 输出: REF(C,1)
```

### 3. 解析单个语句

```python
from mflang import ImportParser

line = "#IMPORT[MIN,2,MACD] AS VAR"
stmt = ImportParser.parse_import_statement(line)

if stmt:
    print(f"解析成功: {stmt}")
    print(f"模型文件: {stmt.formula}")  # MACD是模型文件名（mflang/mmodels/MACD）
    print(f"变量名: {stmt.var_name}")  # VAR是变量名
```

### 4. 验证变量名

```python
from mflang import ImportParser

# 检查变量名是否有效
is_valid = ImportParser.validate_variable_name("VAR1")  # True
is_valid = ImportParser.validate_variable_name("1VAR")  # False
is_valid = ImportParser.validate_variable_name("REF")   # False
```

## 支持的周期类型

- `MIN`: 分钟周期
- `HOUR`: 小时周期
- `CUSHOUR`: 自定义小时周期
- `DAY`: 日周期
- `WEEK`: 一周
- `MONTH`: 月周期
- `QUARTER`: 一季度
- `YEAR`: 年周期

## 模型文件说明

**FORMULA参数是模型文件名**，模型文件存储在 `mflang/mmodels/` 目录下。

### 模型文件格式

模型文件包含变量定义，格式为：`VARIABLE_NAME:EXPRESSION;` 或 `VARIABLE_NAME:=EXPRESSION;`

**示例：`mflang/mmodels/AA` 文件内容：**
```
CC:REF(C,1);//定义一个周期前的收盘价
```

**示例：`mflang/mmodels/CC` 文件内容：**
```
CC:C;//定义收盘价
```

### 访问模型中的变量

通过 `#IMPORT` 语句定义的变量名（VAR）可以访问模型文件中定义的变量：

```python
# #IMPORT[DAY,1,AA] AS VAR
# 模型文件AA中定义了CC变量
# 通过 VAR.CC 访问模型AA中的CC变量
```

## 示例

### 示例1: 引用日周期数据

**步骤1：创建模型文件 `mflang/mmodels/AA`**
```
CC:REF(C,1);//定义一个周期前的收盘价
```

**步骤2：在主指标中使用**
```python
code = """
#IMPORT[DAY,1,AA] AS VAR
CC:VAR.CC;//跨周期引用昨天的收盘价
"""
```

**说明：**
- `#IMPORT[DAY,1,AA] AS VAR` 引用日周期，模型文件AA，变量名为VAR
- `VAR.CC` 访问模型AA中定义的CC变量（即 `REF(C,1)`）

### 示例2: 引用自定义小时周期

**模型文件 `mflang/mmodels/AA` 已存在（见示例1）**

```python
code = """
#IMPORT[CUSHOUR,6,AA]AS S
CC1:=S.CC;//跨周期引用自定义6小时周期的一个周期前的收盘价
"""
```

**说明：**
- `#IMPORT[CUSHOUR,6,AA]AS S` 引用自定义6小时周期，模型文件AA，变量名为S
- `S.CC` 访问模型AA中定义的CC变量

### 示例3: 多个引用

**模型文件 `mflang/mmodels/AA` 已存在（见示例1）**

```python
code = """
#IMPORT[CUSHOUR,6,AA]AS S
CC1:=S.CC;//跨周期引用自定义6小时周期的一个周期前的收盘价

#IMPORT[MIN,1,AA]AS R
CC2:=R.CC;//跨周期引用自定义1分钟周期的一个周期前的收盘价
"""
```

**说明：**
- 同一个模型文件（AA）可以被多个 `#IMPORT` 语句引用
- 不同的变量名（S、R）用于区分不同的引用

## 注意事项

1. **FORMULA是模型文件名**: FORMULA参数对应 `mflang/mmodels/` 目录下的模型文件
2. **模型文件中的变量**: 被引用的变量必须在模型文件中定义
3. **N参数限制**: 周、季周期，N>1时按1计算
4. **变量名规则**: 
   - 不能以数字开头
   - 不能与函数名重复
5. **语句数量限制**: #IMPORT、#CALL、#CALL_PLUS、#CALL_OTHER 总共不能超过6个
6. **末尾分号**: 使用 #IMPORT 时末尾不能写分号（会自动移除）
7. **被引用的指标中不能存在引用**: 避免循环引用

## 错误处理

```python
from mflang import ImportParser

try:
    # 无效的周期类型
    stmt = ImportParser.parse_import_statement("#IMPORT[INVALID,1,AA] AS VAR")
except ValueError as e:
    print(f"错误: {e}")

try:
    # N参数无效
    stmt = ImportParser.parse_import_statement("#IMPORT[DAY,0,AA] AS VAR")
except ValueError as e:
    print(f"错误: {e}")

try:
    # 变量名无效
    stmt = ImportParser.parse_import_statement("#IMPORT[DAY,1,AA] AS 1VAR")
except ValueError as e:
    print(f"错误: {e}")
```

## 完整示例

### 示例1: 基本解析

```python
from mflang import ImportParser, ImportStatement, PeriodType

# 示例代码
code = """
CC:REF(C,1);
保存指标，命名为AA

#IMPORT[DAY,1,AA] AS VAR
CC:VAR.CC;
"""

# 解析
statements = ImportParser.parse_code(code)

# 处理每个引用
for stmt in statements:
    print(f"引用 {stmt.formula} 的 {stmt.period.value} 周期数据")
    print(f"变量名: {stmt.var_name}")
    print(f"周期参数: {stmt.n}")
```

### 示例3: 判断趋势（当前收盘价大于前一个5分钟周期的开盘价）

这个示例展示如何在1分钟周期上，判断当前收盘价是否大于前一个5分钟周期的开盘价。

```python
from mflang import ImportParser, REF
import numpy as np

# 步骤1: 定义被引用的指标（保存为MIN5_OPEN）
# 这个指标在5分钟周期上运行，计算前一个周期的开盘价
min5_formula_code = """
PREV_OPEN:REF(O,1);
"""

# 步骤2: 主指标代码（在1分钟周期上运行）
main_code = """
#IMPORT[MIN,5,MIN5_OPEN] AS MIN5
PREV_OPEN:=MIN5.PREV_OPEN;
"""

# 步骤3: 解析 #IMPORT 语句
import_statements = ImportParser.parse_code(main_code)
for stmt in import_statements:
    print(f"引用5分钟周期指标: {stmt.formula}")
    print(f"变量名: {stmt.var_name}")

# 步骤4: 在策略中使用（模拟数据示例）
# 假设我们已经有5分钟周期的开盘价数据
min5_open = np.array([100.0, 101.0, 102.0, 103.0, 104.0, 105.0])

# 计算前一个5分钟周期的开盘价
prev_5min_open = REF(min5_open, 1)
# 结果: [nan, 100., 101., 102., 103., 104.]

# 当前1分钟周期的收盘价（假设是105.5）
current_close = 105.5

# 获取前一个5分钟周期的开盘价（最后一个值，即当前对应的值）
prev_open_value = prev_5min_open[-1]  # 104.0

# 判断条件：当前收盘价 > 前一个5分钟周期的开盘价
if not np.isnan(prev_open_value) and current_close > prev_open_value:
    print("趋势多")
else:
    print("不满足条件")

# 在策略中的完整实现思路：
from vnpy_ctastrategy import CtaTemplate, ArrayManager
from vnpy.trader.object import BarData

class TrendStrategy(CtaTemplate):
    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        self.am = ArrayManager()
        self.min5_am = ArrayManager()  # 5分钟周期的数据管理器
    
    def on_bar(self, bar: BarData):
        self.am.update_bar(bar)
        
        if not self.am.inited:
            return
        
        # 获取当前收盘价
        current_close = bar.close_price
        
        # 如果是5分钟周期的K线，更新5分钟数据
        if bar.interval.value == 5:  # 假设5分钟周期
            self.min5_am.update_bar(bar)
            
            if self.min5_am.inited:
                # 获取5分钟周期的开盘价数组
                min5_open = self.min5_am.open
                
                # 计算前一个5分钟周期的开盘价
                prev_5min_open = REF(min5_open, 1)
                prev_open_value = prev_5min_open[-1]
                
                # 判断条件
                if not np.isnan(prev_open_value) and current_close > prev_open_value:
                    print("趋势多")
                    # 可以在这里添加交易逻辑
```

**关键点说明：**

1. **从 #IMPORT 语句解析周期信息**：
   - `#IMPORT[MIN,5,MIN5_OPEN] AS MIN5` 中，PERIOD=MIN, N=5
   - 必须从 `#IMPORT` 语句中解析出 PERIOD 和 N 来确定需要加载5分钟周期的数据
2. **被引用的指标** (`MIN5_OPEN`): 在5分钟周期上计算前一个周期的开盘价
3. **主指标**: 使用 `#IMPORT[MIN,5,MIN5_OPEN] AS MIN5` 引用5分钟周期的数据
4. **数据对齐**: 需要将5分钟周期的数据对齐到1分钟周期
5. **判断逻辑**: 当前收盘价 > 前一个5分钟周期的开盘价 → 打印"趋势多"

**实际使用注意事项：**

- 需要维护5分钟周期的K线数据
- 需要将5分钟周期的数据对齐到1分钟周期（每个1分钟K线对应同一个5分钟周期的值）
- 确保数据同步，避免使用过时的数据

### 示例4: 从数据库或parquet文件加载5分钟数据

这个示例展示如何从实际数据源（数据库或parquet文件）加载5分钟K线数据，然后通过#IMPORT引用。

```python
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from mflang import ImportParser, REF
from mflang.import_parser import PeriodType

# 步骤1: 从parquet文件加载5分钟K线数据
def load_5min_from_parquet(file_path: str, symbol: str = None):
    """从parquet文件加载5分钟K线数据"""
    df = pd.read_parquet(file_path)
    
    # 确保datetime列存在
    if 'datetime' not in df.columns:
        df['datetime'] = pd.to_datetime(df['time'])
    else:
        df['datetime'] = pd.to_datetime(df['datetime'])
    
    # 如果指定了symbol，进行过滤
    if symbol and 'symbol' in df.columns:
        df = df[df['symbol'] == symbol]
    
    # 按时间排序
    df = df.sort_values('datetime').reset_index(drop=True)
    
    return df

# 步骤2: 从数据库加载5分钟K线数据
def load_5min_from_database(
    connection_string: str,
    table_name: str,
    symbol: str,
    start_time: datetime,
    end_time: datetime
):
    """从数据库加载5分钟K线数据"""
    import sqlalchemy
    
    engine = sqlalchemy.create_engine(connection_string)
    
    query = f"""
    SELECT datetime, open, high, low, close, volume
    FROM {table_name}
    WHERE symbol = '{symbol}'
    AND datetime >= '{start_time}'
    AND datetime <= '{end_time}'
    AND interval = '5m'
    ORDER BY datetime
    """
    
    df = pd.read_sql(query, engine)
    df['datetime'] = pd.to_datetime(df['datetime'])
    
    return df

# 步骤3: 创建数据管理器
class DataManager:
    def __init__(self):
        self.period_data = {}
    
    def load_5min_data(self, file_path: str, symbol: str):
        """加载5分钟周期数据"""
        df = load_5min_from_parquet(file_path, symbol)
        
        # 转换为numpy数组
        self.period_data[f"{symbol}_MIN_5"] = {
            'datetime': df['datetime'].values,
            'open': df['open'].values.astype(float),
            'high': df['high'].values.astype(float),
            'low': df['low'].values.astype(float),
            'close': df['close'].values.astype(float),
            'volume': df['volume'].values.astype(float) if 'volume' in df.columns else None,
        }
        return True
    
    def get_5min_prev_open(self, symbol: str):
        """获取前一个5分钟周期的开盘价"""
        cache_key = f"{symbol}_MIN_5"
        if cache_key not in self.period_data:
            return None
        
        data = self.period_data[cache_key]
        open_prices = data['open']
        
        # 使用REF函数计算前一个周期的开盘价
        prev_open = REF(open_prices, 1)
        
        # 返回最后一个值（当前对应的值）
        if len(prev_open) > 0:
            return prev_open[-1]
        
        return None

# 步骤4: 创建策略
class TrendStrategy:
    def __init__(self, symbol: str, data_file: str):
        self.symbol = symbol
        self.data_manager = DataManager()
        self.data_manager.load_5min_data(data_file, symbol)
        
        # 解析 #IMPORT 语句
        code = """
#IMPORT[MIN,5,MIN5_OPEN] AS MIN5
PREV_OPEN:=MIN5.PREV_OPEN;
"""
        self.import_statements = ImportParser.parse_code(code)
        print(f"解析到 {len(self.import_statements)} 个 #IMPORT 语句")
    
    def check_trend(self, current_close: float, current_time: datetime):
        """检查趋势：当前收盘价是否大于前一个5分钟周期的开盘价"""
        prev_open = self.data_manager.get_5min_prev_open(self.symbol)
        
        if prev_open is not None and not np.isnan(prev_open):
            if current_close > prev_open:
                print(f"[{current_time}] 趋势多 - 当前收盘价: {current_close:.2f}, 前5分钟开盘价: {prev_open:.2f}")
                return True
            else:
                print(f"[{current_time}] 不满足条件 - 当前收盘价: {current_close:.2f}, 前5分钟开盘价: {prev_open:.2f}")
        
        return False

# 步骤5: 使用示例
# 方式1: 从parquet文件加载
parquet_file = "data/5min_bars.parquet"

# 如果文件不存在，创建示例数据
if not Path(parquet_file).exists():
    print(f"创建示例数据文件: {parquet_file}")
    dates = pd.date_range(start='2024-01-01', periods=100, freq='5min')
    sample_data = pd.DataFrame({
        'datetime': dates,
        'open': 100 + np.random.randn(100).cumsum() * 0.1,
        'high': 100 + np.random.randn(100).cumsum() * 0.1 + 0.5,
        'low': 100 + np.random.randn(100).cumsum() * 0.1 - 0.5,
        'close': 100 + np.random.randn(100).cumsum() * 0.1,
        'volume': np.random.randint(1000, 10000, 100)
    })
    Path(parquet_file).parent.mkdir(parents=True, exist_ok=True)
    sample_data.to_parquet(parquet_file, index=False)
    print(f"示例数据已创建: {parquet_file}")

# 创建策略实例（小恒指期货主连，交易所HKFE）
strategy = TrendStrategy(symbol="MHImain", data_file=parquet_file)

# 模拟处理几根K线
test_times = pd.date_range(start='2024-01-01 09:00', periods=10, freq='1min')
test_closes = 100 + np.random.randn(10).cumsum() * 0.1

print("\n处理K线数据:")
for time, close in zip(test_times, test_closes):
    strategy.check_trend(close, time)

# 方式2: 从数据库加载（需要配置数据库连接）
# db_connection = "postgresql://user:password@localhost:5432/dbname"
# 
# # 加载数据（小恒指期货主连，交易所HKFE）
# df = load_5min_from_database(
#     db_connection,
#     "kline_data",
#     "MHImain",  # 小恒指期货主连
#     datetime(2024, 1, 1),
#     datetime.now()
# )
# 
# # 保存为parquet文件（可选）
# df.to_parquet("data/5min_bars.parquet", index=False)
# 
# # 使用策略
# strategy = TrendStrategy(symbol="MHImain", data_file="data/5min_bars.parquet")
```

**完整示例文件：**

更完整的实现请参考 `mflang/example_trend_strategy.py` 文件，其中包含：
- 完整的数据加载器（支持parquet和数据库）
- 增强的跨周期数据管理器
- 完整的策略实现
- 详细的使用示例

### 示例4: 模型文件中包含#IMPORT语句和跨周期引用（TEST_IMPORT）

这个示例展示如何在模型文件中使用#IMPORT语句，并在变量定义中使用跨周期引用的变量。

**步骤1：创建被引用的模型文件 `mflang/mmodels/MIN5_OPEN`**
```
PREV_OPEN:REF(O,1);//前一个周期的开盘价
```

**步骤2：创建主模型文件 `mflang/mmodels/TEST_IMPORT`**
```
#IMPORT[MIN,5,MIN5_OPEN] AS MIN5

CC:C;//定义收盘价
ISBUYTREND: C > MIN5.PREV_OPEN;//判断是否多头趋势
```

**步骤3：解析和使用模型文件**

```python
from mflang import ImportParser, load_model, REF
import numpy as np
import pandas as pd

# 读取TEST_IMPORT文件内容
from pathlib import Path
test_import_file = Path("mflang/mmodels/TEST_IMPORT")
with open(test_import_file, 'r', encoding='utf-8') as f:
    file_content = f.read()

# 解析#IMPORT语句
import_statements = ImportParser.parse_code(file_content)
for stmt in import_statements:
    print(f"#IMPORT语句: {stmt}")
    print(f"  被引用的模型文件: {stmt.formula}")

# 加载被引用的模型文件
referenced_model = load_model("MIN5_OPEN")
print(f"被引用模型包含变量: {referenced_model}")
# 输出: {'PREV_OPEN': 'REF(O,1)'}

# 加载当前模型文件
current_model = load_model("TEST_IMPORT")
print(f"当前模型包含变量: {current_model}")
# 输出: {'CC': 'C', 'ISBUYTREND': 'C > MIN5.PREV_OPEN'}

# 步骤4: 计算被引用模型中的变量（重要！）
# 准备5分钟周期的K线数据
dates_5min = pd.date_range(start='2024-01-01 09:00', periods=20, freq='5min')
df_5min = pd.DataFrame({
    'datetime': dates_5min,
    'open': 20000 + np.random.randn(20).cumsum() * 10,
    'close': 20000 + np.random.randn(20).cumsum() * 10,
})

# 计算被引用模型中的变量
referenced_variables = {}
for var_name, var_expr in referenced_model.items():
    if var_expr.strip() == 'REF(O,1)':
        # 执行REF(O,1)计算
        open_prices = df_5min['open'].values
        result = REF(open_prices, 1)
        referenced_variables[var_name] = result
        print(f"计算 {var_name}: 数组长度={len(result)}, 当前值={result[-1]:.2f}")

# 步骤5: 使用计算后的变量值计算当前模型中的变量
# 准备1分钟周期的K线数据
dates_1min = pd.date_range(start='2024-01-01 09:00', periods=100, freq='1min')
df_1min = pd.DataFrame({
    'datetime': dates_1min,
    'close': 20000 + np.random.randn(100).cumsum() * 10,
})

# 计算当前模型中的变量
for var_name, var_expr in current_model.items():
    if var_name == "ISBUYTREND":
        # 解析表达式 C > MIN5.PREV_OPEN
        # 获取MIN5.PREV_OPEN的值（已计算）
        if "PREV_OPEN" in referenced_variables:
            prev_open_value = referenced_variables["PREV_OPEN"][-1]  # 当前值
            current_close = df_1min['close'].iloc[-1]
            isbuytrend = current_close > prev_open_value
            print(f"计算 {var_name}: {current_close:.2f} > {prev_open_value:.2f} = {isbuytrend}")
```

**关键点说明：**

1. **模型文件可以包含#IMPORT语句**: TEST_IMPORT模型文件本身包含#IMPORT语句
2. **变量定义可以使用跨周期引用**: ISBUYTREND变量定义中使用了MIN5.PREV_OPEN
3. **必须先计算被引用模型中的变量**: 在使用MIN5.PREV_OPEN之前，需要先计算被引用模型MIN5_OPEN中的PREV_OPEN变量
4. **使用计算后的值**: 在计算当前模型的变量时，使用已计算的跨周期引用值

**完整示例请参考**: `mflang/test_parse_test_import.py`

