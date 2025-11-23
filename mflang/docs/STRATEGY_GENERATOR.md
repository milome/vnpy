# 策略代码生成器使用指南

## 概述

策略代码生成器可以将 `mflang/mmodels/` 目录下的模型文件转换为符合 `vnpy_ctastrategy` 模块格式的策略文件。

## 功能特性

- 自动解析模型文件中的 `#IMPORT` 语句
- 自动解析变量定义
- 生成符合 `vnpy_ctastrategy` 格式的策略类
- 自动处理跨周期数据管理
- 自动生成变量计算方法
- 自动生成策略逻辑框架

## 使用方法

### 方法1：命令行工具（推荐）

使用命令行工具 `mflang/generate_strategy.py` 可以方便地将模型文件转换为策略文件并保存为Python文件：

```bash
# 基本用法：自动生成输出文件路径
python mflang/generate_strategy.py TEST_IMPORT

# 指定输出文件路径
python mflang/generate_strategy.py TEST_IMPORT strategies/my_strategy.py

# 指定输出文件路径和策略类名
python mflang/generate_strategy.py TEST_IMPORT strategies/my_strategy.py MyStrategy

# 指定所有参数（包括作者）
python mflang/generate_strategy.py TEST_IMPORT strategies/my_strategy.py MyStrategy --author "Your Name"
```

**输出示例：**
```
正在生成策略文件...
  模型文件: TEST_IMPORT
  输出文件: strategies/test_import_strategy.py
  作者: MFLang Generator

策略文件已生成: strategies\test_import_strategy.py
[成功] 策略文件已生成: D:\Dev\vnpy\strategies\test_import_strategy.py
       文件大小: 5234 字符
       代码行数: 177 行
[验证] 文件已成功保存
```

### 方法2：Python API

```python
from mflang.strategy_generator import generate_strategy_from_model

# 生成策略文件并保存为Python文件
code = generate_strategy_from_model(
    model_name="TEST_IMPORT",  # 模型文件名（不含路径）
    strategy_class_name="TestImportStrategy",  # 策略类名（可选，自动生成）
    output_file="strategies/test_import_strategy.py",  # 输出文件路径（必须指定才能保存）
    author="MFLang Generator"  # 策略作者（可选）
)

# 如果不指定 output_file，只返回代码字符串，不保存文件
code = generate_strategy_from_model(
    model_name="TEST_IMPORT",
    strategy_class_name="TestImportStrategy"
)
# 此时需要手动保存
with open("strategies/test_import_strategy.py", "w", encoding="utf-8") as f:
    f.write(code)
```

### 方法3：直接运行生成器

```bash
# 直接运行生成器（使用默认参数）
python mflang/strategy_generator.py

# 运行测试
python mflang/test_strategy_generator.py
```

## 输出文件说明

生成的策略文件会保存为标准的Python文件（`.py`），包含：

1. **文件头**：包含编码声明和文档字符串
2. **导入语句**：所有必要的模块导入
3. **策略类**：完整的策略类定义
4. **所有方法**：初始化、回调、计算、逻辑等方法

生成的文件可以直接在 vnpy 的 CTA 策略模块中使用。

## 生成的策略文件结构

生成的策略文件包含以下部分：

### 1. 导入语句

```python
from vnpy_ctastrategy import (
    CtaTemplate,
    StopOrder,
    TickData,
    BarData,
    TradeData,
    OrderData,
    BarGenerator,
    ArrayManager
)

from mflang import REF, BARSLAST, SUMBARS, BARPOS, HHV, LLV
from mflang.import_parser import ImportParser, PeriodType
from mflang.model_loader import load_model
import numpy as np
```

### 2. 策略类定义

```python
class TestImportStrategy(CtaTemplate):
    """基于模型文件 TEST_IMPORT 生成的策略"""
    
    author = "MFLang Generator"
    
    # 策略参数
    parameters = []
    
    # 策略变量
    variables = ["CC", "ISBUYTREND"]
    
    CC = 0.0
    ISBUYTREND = 0.0
```

### 3. 初始化方法

```python
def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
    """初始化策略"""
    super().__init__(cta_engine, strategy_name, vt_symbol, setting)
    
    # K线管理器
    self.bg = BarGenerator(self.on_bar)
    self.am = ArrayManager()
    
    # 跨周期数据管理器
    self.min5_am = ArrayManager()  # MIN5周期数据
    
    # 跨周期变量缓存
    self.min5_vars = {}  # MIN5 的变量缓存
    
    # 解析 #IMPORT 语句
    self.import_statements = ImportParser.parse_code("""
    #IMPORT[MIN,5,MIN5_OPEN] AS MIN5
    """)
    
    # 加载被引用的模型文件
    self.min5_model = load_model("MIN5_OPEN")
```

### 4. 回调方法

- `on_init()`: 策略初始化回调
- `on_start()`: 策略启动回调
- `on_stop()`: 策略停止回调
- `on_tick()`: Tick数据回调
- `on_bar()`: K线数据回调

### 5. 跨周期数据处理

```python
def _is_period_bar(self, bar: BarData, period_type: str, n: int) -> bool:
    """判断是否是目标周期的K线"""
    if period_type == "MIN":
        return bar.datetime.minute % n == 0
    elif period_type == "HOUR":
        return bar.datetime.hour % n == 0 and bar.datetime.minute == 0
    elif period_type == "DAY":
        return bar.datetime.hour == 0 and bar.datetime.minute == 0
    else:
        return False

def _calculate_cross_period_vars(self, var_name: str, model_name: str):
    """计算跨周期变量"""
    # 加载模型文件
    model = load_model(model_name)
    
    # 获取对应的ArrayManager
    am = getattr(self, f"{var_name.lower()}_am")
    
    # 计算模型中的变量
    vars_cache = {}
    for var_name_in_model, var_expr in model.items():
        # 解析并计算变量
        if "REF(O,1)" in var_expr:
            open_prices = am.open
            result = REF(open_prices, 1)
            vars_cache[var_name_in_model] = result[-1] if len(result) > 0 else np.nan
        # ... 更多表达式处理
    
    # 缓存结果
    setattr(self, f"{var_name.lower()}_vars", vars_cache)
```

### 6. 变量计算方法

```python
def _calculate_variable_cc(self) -> float:
    """计算变量 CC: C"""
    return self.am.close[-1] if len(self.am.close) > 0 else 0.0

def _calculate_variable_isbuytrend(self) -> float:
    """计算变量 ISBUYTREND: C > MIN5.PREV_OPEN"""
    # 获取当前收盘价
    current_close = self.am.close[-1] if len(self.am.close) > 0 else np.nan
    if np.isnan(current_close):
        return 0.0
    
    # 获取跨周期引用 MIN5.PREV_OPEN
    min5_vars = getattr(self, "min5_vars", {})
    prev_open_value = min5_vars.get("PREV_OPEN", np.nan)
    if np.isnan(prev_open_value):
        return 0.0
    
    # 判断条件
    result = current_close > prev_open_value
    return 1.0 if result else 0.0
```

### 7. 策略逻辑方法

```python
def _on_strategy_logic(self):
    """策略逻辑"""
    # 在这里实现策略的交易逻辑
    # 可以使用计算好的变量进行判断
    # CC = self.CC
    # ISBUYTREND = self.ISBUYTREND
    
    # 示例：根据ISBUYTREND判断趋势
    if self.ISBUYTREND > 0:
        self.write_log(f"检测到多头趋势")
        # 可以在这里添加买入逻辑
```

## 支持的表达式类型

### 当前支持

- 简单变量：`C`, `O`, `H`, `L`（收盘价、开盘价、最高价、最低价）
- REF函数：`REF(O,1)`, `REF(C,1)` 等
- 比较表达式：`C > MIN5.PREV_OPEN` 等

### 未来计划

- 更多函数：`MA`, `EMA`, `HHV`, `LLV`, `SUM` 等
- 复杂表达式：支持更多运算符和函数组合
- 条件表达式：`IFELSE`, `AND`, `OR` 等

## 注意事项

1. **周期判断**：`_is_period_bar` 方法需要根据实际的K线周期进行调整
2. **表达式解析**：当前只支持部分表达式类型，复杂表达式需要手动实现
3. **数据对齐**：跨周期数据对齐逻辑可能需要根据实际情况调整
4. **策略逻辑**：生成的策略逻辑框架需要根据实际需求完善

## 示例模型文件

### TEST_IMPORT 模型文件

```
#IMPORT[MIN,5,MIN5_OPEN] AS MIN5

CC:C;//定义收盘价
ISBUYTREND: C > MIN5.PREV_OPEN;//判断是否多头趋势
```

### MIN5_OPEN 模型文件

```
PREV_OPEN:REF(O,1);//前一个周期的开盘价
```

## 测试

运行测试脚本验证生成器功能：

```bash
python mflang/test_strategy_generator.py
```

## 相关文件

- `mflang/strategy_generator.py`: 策略代码生成器
- `mflang/test_strategy_generator.py`: 测试脚本
- `strategies/test_import_strategy.py`: 生成的策略文件示例

