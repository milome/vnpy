# #IMPORT 跨周期引用函数使用指南

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
    print(f"指标: {stmt.formula}")
    print(f"变量: {stmt.var_name}")
```

### 2. 解析单个语句

```python
from mflang import ImportParser

line = "#IMPORT[MIN,2,MACD] AS VAR"
stmt = ImportParser.parse_import_statement(line)

if stmt:
    print(f"解析成功: {stmt}")
```

### 3. 验证变量名

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

## 示例

### 示例1: 引用日周期数据

```python
# 被引用的指标（保存为AA）:
# CC:REF(C,1);

# 主指标:
code = """
#IMPORT[DAY,1,AA] AS VAR
CC:VAR.CC;
"""
```

### 示例2: 引用自定义小时周期

```python
code = """
#IMPORT[CUSHOUR,6,AA]AS S
CC1:=S.CC;
"""
```

### 示例3: 多个引用

```python
code = """
#IMPORT[CUSHOUR,6,AA]AS S
CC1:=S.CC;

#IMPORT[MIN,1,AA]AS R
CC2:=R.CC;
"""
```

## 注意事项

1. **N参数限制**: 周、季周期，N>1时按1计算
2. **变量名规则**: 
   - 不能以数字开头
   - 不能与函数名重复
3. **语句数量限制**: #IMPORT、#CALL、#CALL_PLUS、#CALL_OTHER 总共不能超过6个
4. **末尾分号**: 使用 #IMPORT 时末尾不能写分号（会自动移除）

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

### 示例2: 判断趋势（当前收盘价大于前一个5分钟周期的开盘价）

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

1. **被引用的指标** (`MIN5_OPEN`): 在5分钟周期上计算前一个周期的开盘价
2. **主指标**: 使用 `#IMPORT[MIN,5,MIN5_OPEN] AS MIN5` 引用5分钟周期的数据
3. **数据对齐**: 需要将5分钟周期的数据对齐到1分钟周期
4. **判断逻辑**: 当前收盘价 > 前一个5分钟周期的开盘价 → 打印"趋势多"

**实际使用注意事项：**

- 需要维护5分钟周期的K线数据
- 需要将5分钟周期的数据对齐到1分钟周期（每个1分钟K线对应同一个5分钟周期的值）
- 确保数据同步，避免使用过时的数据

### 示例3: 从数据库或parquet文件加载5分钟数据

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

