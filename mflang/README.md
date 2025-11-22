# 麦语言函数模块

本模块实现了文华财经麦语言的各种函数，用于策略开发。

## 已实现的函数

### REF(X, N) - 引用N个周期前的值

引用X在N个周期前的值。

#### 参数

- `X`: 时间序列数组（numpy数组或列表），最新的值在数组末尾
- `N`: 周期数，可以是整数、浮点数或数组

#### 返回值

- 如果X是数组，返回相同形状的数组，每个元素是对应位置N个周期前的值
- 如果数据不足或N无效，返回NaN值

#### 规则

1. 当N为有效值，但当前的k线数不足N根，返回NaN
2. N为0时返回当前X值
3. N为空值或NaN时返回NaN
4. N可以为变量（数组）

#### 使用示例

```python
import numpy as np
from mflang import REF

# 示例1: 基本用法
close = np.array([100.0, 101.0, 102.0, 103.0, 104.0, 105.0])
result = REF(close, 2)
# 结果: [nan, nan, 100., 101., 102., 103.]

# 示例2: N=0返回当前值
result = REF(close, 0)
# 结果: [100., 101., 102., 103., 104., 105.]

# 示例3: 引用5个周期前的收盘价
close = np.array([100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0])
result = REF(close, 5)
# 结果: [nan, nan, nan, nan, nan, 100., 101., 102., 103., 104.]

# 示例4: N为数组（变量）
close = np.array([100.0, 101.0, 102.0, 103.0, 104.0, 105.0])
N = np.array([0, 1, 2, 0, 1, 2])
result = REF(close, N)
# 结果: [100., 100., 100., 103., 103., 103.]
```

#### 如何获取当前值

`REF` 返回的是 numpy 数组，以下是几种获取当前值（最后一个元素）的方法：

**方法1: 获取数组最后一个值（当前值）**

```python
import numpy as np
from mflang import REF

# 计算 REF
close = np.array([100.0, 101.0, 102.0, 103.0, 104.0, 105.0])
ref_result = REF(close, 2)  # [nan, nan, 100., 101., 102., 103.]

# 获取最后一个值（当前值）
current_ref_value = ref_result[-1]  # 103.0

# 检查是否为有效值
if not np.isnan(current_ref_value):
    print(f"2个周期前的收盘价是: {current_ref_value}")
else:
    print("数据不足，无法引用2个周期前的值")
```

**方法2: 同时获取当前值和引用值进行比较**

```python
close = np.array([100.0, 101.0, 102.0, 103.0, 104.0, 105.0])
ref_close_5 = REF(close, 5)

# 获取当前收盘价
current_close = close[-1]  # 105.0

# 获取5个周期前的收盘价（当前值）
close_5_periods_ago = ref_close_5[-1]  # 可能是 NaN 或 100.0

# 比较前先检查有效性
if not np.isnan(close_5_periods_ago):
    if current_close > close_5_periods_ago:
        print(f"当前价格 {current_close} 高于5周期前 {close_5_periods_ago}")
    else:
        print(f"当前价格 {current_close} 低于或等于5周期前 {close_5_periods_ago}")
else:
    print("数据不足5根K线，无法比较")
```

**方法3: N为0时获取当前值**

```python
# N=0 时，REF 返回当前值本身
close = np.array([100.0, 101.0, 102.0, 103.0, 104.0, 105.0])
current_value = REF(close, 0)[-1]  # 105.0，等同于 close[-1]
```

**方法4: N为变量（数组）时获取当前值**

```python
close = np.array([100.0, 101.0, 102.0, 103.0, 104.0, 105.0])
# N 是变量数组，每个位置使用不同的周期数
N = np.array([0, 1, 2, 0, 1, 2])
ref_result = REF(close, N)  # [100., 100., 100., 103., 103., 103.]

# 获取最后一个值
current_ref_value = ref_result[-1]  # 103.0
# 这表示：在最后一个位置，使用 N[-1]=2，引用2个周期前的值（即 close[3]=103.0）
```

**方法5: 批量获取多个周期的引用值**

```python
close = np.array([100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0])

# 同时引用多个周期前的值
ref_1 = REF(close, 1)[-1]  # 1个周期前
ref_2 = REF(close, 2)[-1]  # 2个周期前
ref_5 = REF(close, 5)[-1]  # 5个周期前

print(f"当前: {close[-1]}, 1周期前: {ref_1}, 2周期前: {ref_2}, 5周期前: {ref_5}")
```

**方法6: 在循环中获取历史引用值**

```python
close = np.array([100.0, 101.0, 102.0, 103.0, 104.0, 105.0])
ref_result = REF(close, 3)

# 获取特定位置的值
for i in range(len(close)):
    ref_value = ref_result[i]
    if not np.isnan(ref_value):
        print(f"位置 {i}: 当前值={close[i]}, 3周期前={ref_value}")
    else:
        print(f"位置 {i}: 当前值={close[i]}, 3周期前=数据不足")
```

#### 在策略中使用

```python
from vnpy_ctastrategy import CtaTemplate, ArrayManager
from mflang import REF
import numpy as np

class MyStrategy(CtaTemplate):
    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        self.am = ArrayManager()
    
    def on_bar(self, bar: BarData):
        self.am.update_bar(bar)
        
        if not self.am.inited:
            return
        
        # 获取收盘价数组
        close = self.am.close
        
        # 引用5个周期前的收盘价
        ref_close_5 = REF(close, 5)
        
        # 获取最新的值（最后一个元素）
        current_close = close[-1]
        close_5_periods_ago = ref_close_5[-1]
        
        # 检查数据是否足够
        if not np.isnan(close_5_periods_ago):
            # 比较当前收盘价和5周期前的收盘价
            if current_close > close_5_periods_ago:
                print(f"当前价格 {current_close} 高于5周期前 {close_5_periods_ago}")
            elif current_close < close_5_periods_ago:
                print(f"当前价格 {current_close} 低于5周期前 {close_5_periods_ago}")
        
        # 引用1个周期前的收盘价（前一根K线）
        ref_close_1 = REF(close, 1)
        prev_close = ref_close_1[-1]
        
        if not np.isnan(prev_close):
            # 计算涨跌幅
            change_pct = (current_close - prev_close) / prev_close * 100
            print(f"相比前一根K线涨跌: {change_pct:.2f}%")
        
        # 使用变量N（例如：根据条件动态选择周期）
        # 假设根据某种条件选择不同的周期
        n_periods = 3  # 可以是动态计算的变量
        ref_close_n = REF(close, n_periods)
        close_n_periods_ago = ref_close_n[-1]
        
        if not np.isnan(close_n_periods_ago):
            print(f"{n_periods}个周期前的收盘价: {close_n_periods_ago}")
```

#### 常见应用场景

**场景1: 计算价格变化率**

```python
close = np.array([100.0, 101.0, 102.0, 103.0, 104.0, 105.0])
ref_close_5 = REF(close, 5)

current_close = close[-1]
close_5_ago = ref_close_5[-1]

if not np.isnan(close_5_ago):
    change_rate = (current_close - close_5_ago) / close_5_ago * 100
    print(f"5周期价格变化率: {change_rate:.2f}%")
```

**场景2: 判断价格突破**

```python
close = np.array([100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0])
high = np.array([101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0])

# 引用10个周期前的最高价
ref_high_10 = REF(high, 10)
prev_high_10 = ref_high_10[-1]
current_high = high[-1]

if not np.isnan(prev_high_10):
    if current_high > prev_high_10:
        print("突破10周期前的高点")
```

**场景3: 使用N为变量进行动态引用**

```python
close = np.array([100.0, 101.0, 102.0, 103.0, 104.0, 105.0])
# N 是变量，根据某种条件动态变化
N = np.array([1, 2, 1, 3, 2, 1])
ref_result = REF(close, N)

# 获取当前值
current_ref = ref_result[-1]  # 使用 N[-1]=1，引用1个周期前的值
print(f"动态引用的值: {current_ref}")
```

**场景4: 检查数据是否足够**

```python
close = np.array([100.0, 101.0, 102.0])  # 只有3根K线
ref_close_5 = REF(close, 5)  # 需要5根K线

current_ref = ref_close_5[-1]

# 检查数据是否足够
if np.isnan(current_ref):
    print("数据不足，无法引用5个周期前的值")
    print("需要至少5根K线，当前只有3根")
else:
    print(f"5个周期前的值: {current_ref}")
```

### BARSLAST(COND) - 上一次条件成立到当前的周期数

返回上一次条件COND成立到当前的周期数。

#### 参数

- `COND`: 条件数组（布尔数组或可以转换为布尔的数组），True表示条件成立

#### 返回值

- 返回一个数组，每个元素表示从该位置向前查找，最近一次条件成立到当前位置的周期数
- 如果当前位置条件成立，返回0
- 如果从开始到当前位置条件从未成立，返回NaN

#### 规则

1. 条件成立的当根k线上BARSLAST(COND)的返回值为0
2. 如果条件从未成立，返回NaN

#### 使用示例

```python
import numpy as np
from mflang import BARSLAST

# 示例1: 上一根阴线到现在的周期数
open_price = np.array([100.0, 101.0, 102.0, 103.0, 104.0, 105.0])
close_price = np.array([99.0, 102.0, 103.0, 102.0, 105.0, 106.0])
cond = open_price > close_price  # 阴线条件：开盘价 > 收盘价
result = BARSLAST(cond)
# 结果: [0., 1., 2., 0., 1., 2.]
# 位置0: 当前是阴线，返回0
# 位置1: 不是阴线，上次阴线在位置0，返回1
# 位置2: 不是阴线，上次阴线在位置0，返回2
# 位置3: 当前是阴线，返回0
# ...

# 示例2: 当日k线数（分钟周期）
# N:=BARSLAST(DATE<>REF(DATE,1))+1
# 由于条件成立的当根k线上BARSLAST(COND)的返回值为0，所以"+1"才是当日k线根数
from mflang import REF

# 模拟日期数组（简化示例）
date_array = np.array([20240101, 20240101, 20240101, 20240102, 20240102, 20240102])
date_changed = date_array != REF(date_array, 1)  # 日期是否变化
barslast_result = BARSLAST(date_changed)
n = barslast_result + 1  # 当日k线数
# 结果: [1., 2., 3., 1., 2., 3.]
```

#### 如何获取整数结果

`BARSLAST` 返回的是 numpy 数组，以下是几种获取整数结果的方法：

**方法1: 获取数组最后一个值（当前值）**

```python
import numpy as np
from mflang import BARSLAST

# 计算 BARSLAST
cond = np.array([True, False, False, True, False])
result = BARSLAST(cond)  # [0., 1., 2., 0., 1.]

# 获取最后一个值（当前值）
current_value = result[-1]  # 1.0

# 转换为整数（处理 NaN）
if not np.isnan(current_value):
    periods = int(current_value)  # 1
    print(f"距离上次条件成立已经过了 {periods} 个周期")
else:
    print("条件从未成立")
```

**方法2: 获取数组中特定位置的值**

```python
# 获取索引为 i 的值
i = 3
value = result[i]  # 0.0

# 转换为整数
if not np.isnan(value):
    periods = int(value)  # 0
```

**方法3: 批量处理（转换为整数数组，NaN保持不变）**

```python
# 将非NaN值转换为整数
result_int = np.where(np.isnan(result), np.nan, result.astype(int))
# 或者使用更安全的方式
result_int = np.array([int(x) if not np.isnan(x) else np.nan for x in result])
```

**方法4: 使用条件判断获取有效值**

```python
# 只获取有效（非NaN）的值
valid_values = result[~np.isnan(result)]  # 获取所有非NaN值
if len(valid_values) > 0:
    latest_valid = int(valid_values[-1])  # 最后一个有效值的整数形式
```

#### 在策略中使用

```python
from vnpy_ctastrategy import CtaTemplate, ArrayManager
from mflang import BARSLAST, REF
import numpy as np

class MyStrategy(CtaTemplate):
    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        self.am = ArrayManager()
    
    def on_bar(self, bar: BarData):
        self.am.update_bar(bar)
        
        if not self.am.inited:
            return
        
        # 获取开盘价和收盘价数组
        open_price = self.am.open
        close_price = self.am.close
        
        # 计算阴线条件：开盘价 > 收盘价
        cond = open_price > close_price
        
        # 计算上一根阴线到现在的周期数
        barslast_result = BARSLAST(cond)
        
        # 获取最新的值（最后一个元素）并转换为整数
        periods_since_last_negative = barslast_result[-1]
        
        if not np.isnan(periods_since_last_negative):
            periods = int(periods_since_last_negative)  # 转换为整数
            if periods == 0:
                print("当前是阴线")
            else:
                print(f"距离上一根阴线已经过了 {periods} 个周期")
        else:
            print("从未出现过阴线")
```

## 测试

运行测试文件验证函数功能：

```bash
python mflang/test_functions.py
```

## 未来计划

更多麦语言函数正在开发中，包括：

- MA - 移动平均
- EMA - 指数移动平均
- HHV - 最高值
- LLV - 最低值
- SUM - 求和
- COUNT - 计数
- ... 等等

