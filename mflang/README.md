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

### SUMBARS(X, A) - 求累加到指定值的周期数

求从当前位置向前累加X的值，直到累加和>=A所需的周期数。

#### 参数

- `X`: 时间序列数组（numpy数组或列表），最新的值在数组末尾
- `A`: 目标值，可以是整数、浮点数或数组（支持变量）

#### 返回值

- 返回一个整数数组，每个元素表示从该位置向前累加X的值，直到累加和>=A所需的周期数
- 如果累加不到目标值A，返回NaN
- 非NaN值都是整数

#### 规则

1. 从当前位置向前（向历史）累加X的值，直到累加和>=A
2. 返回需要多少个周期（包括当前位置）
3. 如果累加完所有历史数据还是不够，返回NaN
4. A可以为变量（数组）

#### 使用示例

```python
import numpy as np
from mflang import SUMBARS

# 示例1: 成交量累加到20000需要的周期数
vol = np.array([1000, 2000, 3000, 4000, 5000, 6000])
result = SUMBARS(vol, 20000)
# 结果: [nan, nan, nan, nan, nan, nan]  # 累加不到20000

# 示例2: 成交量累加到10000需要的周期数
vol = np.array([1000, 2000, 3000, 4000, 5000, 6000])
result = SUMBARS(vol, 10000)
# 结果: [nan, nan, nan, nan, 3., 2.]
# 位置4: 5000<10000(1周期), 5000+4000=9000<10000(2周期), 5000+4000+3000=12000>=10000(3周期)
# 位置5: 6000<10000(1周期), 6000+5000=11000>=10000(2周期)

# 示例3: A为变量（数组）
vol = np.array([1000, 2000, 3000, 4000, 5000])
A = np.array([5000, 6000, 7000, 8000, 9000])
result = SUMBARS(vol, A)
# 结果: [nan, nan, nan, 3., 2.]
# 位置3: 4000+3000+2000=9000>=8000, 需要3个周期
# 位置4: 5000+4000=9000>=9000, 需要2个周期
```

#### 如何获取当前值

`SUMBARS` 返回的是 numpy 数组，以下是几种获取当前值（最后一个元素）的方法：

**方法1: 获取数组最后一个值（当前值）**

```python
import numpy as np
from mflang import SUMBARS

# 计算 SUMBARS
vol = np.array([1000, 2000, 3000, 4000, 5000, 6000])
result = SUMBARS(vol, 10000)  # [nan, nan, nan, nan, 3., 2.]

# 获取最后一个值（当前值）
current_periods = result[-1]  # 2.0

# 检查是否为有效值并转换为整数
if not np.isnan(current_periods):
    periods = int(current_periods)  # 2
    print(f"成交量累加到10000需要 {periods} 个周期")
else:
    print("数据不足，无法累加到目标值")
```

**方法2: 在策略中使用获取当前周期数**

```python
vol = np.array([1000, 2000, 3000, 4000, 5000, 6000])
target_vol = 20000

# 计算累加到目标成交量需要的周期数
sumbars_result = SUMBARS(vol, target_vol)

# 获取当前值
periods_needed = sumbars_result[-1]

if not np.isnan(periods_needed):
    periods = int(periods_needed)
    print(f"成交量累加到 {target_vol} 需要 {periods} 个周期")
    # 可以根据这个周期数进行交易决策
else:
    print(f"当前数据不足以累加到 {target_vol}")
```

**方法3: 使用变量A获取当前值**

```python
vol = np.array([1000, 2000, 3000, 4000, 5000])
# A 是变量数组，每个位置使用不同的目标值
A = np.array([5000, 6000, 7000, 8000, 9000])
result = SUMBARS(vol, A)  # [1., 1., 1., 2., 2.]

# 获取最后一个值
current_periods = result[-1]  # 2.0
# 这表示：在最后一个位置，使用 A[-1]=9000，累加到9000需要2个周期
if not np.isnan(current_periods):
    periods = int(current_periods)  # 2
```

**方法4: 批量获取多个目标值的周期数**

```python
vol = np.array([1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000])

# 同时计算累加到不同目标值需要的周期数
periods_5000 = SUMBARS(vol, 5000)[-1]   # 累加到5000
periods_10000 = SUMBARS(vol, 10000)[-1]  # 累加到10000
periods_20000 = SUMBARS(vol, 20000)[-1] # 累加到20000

print(f"累加到5000需要: {int(periods_5000) if not np.isnan(periods_5000) else '不足'}")
print(f"累加到10000需要: {int(periods_10000) if not np.isnan(periods_10000) else '不足'}")
print(f"累加到20000需要: {int(periods_20000) if not np.isnan(periods_20000) else '不足'}")
```

#### 在策略中使用

```python
from vnpy_ctastrategy import CtaTemplate, ArrayManager
from mflang import SUMBARS
import numpy as np

class MyStrategy(CtaTemplate):
    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        self.am = ArrayManager()
        self.target_volume = 20000  # 目标成交量
    
    def on_bar(self, bar: BarData):
        self.am.update_bar(bar)
        
        if not self.am.inited:
            return
        
        # 获取成交量数组
        volume = self.am.volume
        
        # 计算成交量累加到目标值需要的周期数
        sumbars_result = SUMBARS(volume, self.target_volume)
        
        # 获取当前值（最后一个元素）
        periods_needed = sumbars_result[-1]
        
        # 检查数据是否足够
        if not np.isnan(periods_needed):
            periods = int(periods_needed)  # 转换为整数
            
            print(f"成交量累加到 {self.target_volume} 需要 {periods} 个周期")
            
            # 可以根据周期数进行交易决策
            if periods <= 3:
                print("成交量快速累积，可能有大资金进入")
            elif periods <= 5:
                print("成交量正常累积")
            else:
                print("成交量缓慢累积")
        else:
            print(f"当前数据不足以累加到 {self.target_volume}")
        
        # 使用变量A（动态目标值）
        # 假设目标值根据当前价格动态调整
        dynamic_target = self.target_volume * (1 + bar.close_price / 10000)
        dynamic_result = SUMBARS(volume, dynamic_target)
        dynamic_periods = dynamic_result[-1]
        
        if not np.isnan(dynamic_periods):
            periods = int(dynamic_periods)
            print(f"动态目标值 {dynamic_target:.0f} 需要 {periods} 个周期")
```

#### 常见应用场景

**场景1: 判断成交量累积速度**

```python
vol = np.array([1000, 2000, 3000, 4000, 5000, 6000])
target_vol = 10000

sumbars_result = SUMBARS(vol, target_vol)
periods = sumbars_result[-1]

if not np.isnan(periods):
    periods_int = int(periods)
    if periods_int <= 2:
        print("成交量快速累积，可能有大资金进入")
    elif periods_int <= 4:
        print("成交量正常累积")
    else:
        print("成交量缓慢累积")
```

**场景2: 计算价格区间内的成交量累积**

```python
# 假设要计算价格在某个区间内的成交量累积
price = np.array([100, 101, 102, 103, 104, 105])
vol = np.array([1000, 2000, 3000, 4000, 5000, 6000])

# 筛选价格在102-104之间的成交量
mask = (price >= 102) & (price <= 104)
filtered_vol = np.where(mask, vol, 0)

# 计算这些成交量累加到目标值需要的周期数
target = 5000
periods = SUMBARS(filtered_vol, target)[-1]

if not np.isnan(periods):
    print(f"价格在102-104区间的成交量累加到{target}需要{int(periods)}个周期")
```

**场景3: 使用变量A进行动态分析**

```python
vol = np.array([1000, 2000, 3000, 4000, 5000])
# 目标值根据某种条件动态变化
A = np.array([5000, 6000, 7000, 8000, 9000])
result = SUMBARS(vol, A)

# 获取当前值
current_periods = result[-1]
if not np.isnan(current_periods):
    print(f"动态目标值需要 {int(current_periods)} 个周期")
```

**场景4: 计算条件出现的次数（分钟数除以5余数为4，出现2次）**

```python
import numpy as np
from mflang import SUMBARS

# 模拟分钟数数组（假设是分钟K线数据）
# 例如：0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, ...
minutes = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19])

# 条件：分钟数除以5余数为4（即分钟数为4, 9, 14, 19, ...）
# 将条件转换为数值数组：满足条件为1，不满足为0
condition = (minutes % 5 == 4).astype(int)
# 结果: [0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
# 位置4(分钟4): 1, 位置9(分钟9): 1, 位置14(分钟14): 1, 位置19(分钟19): 1

# 计算累加到2（出现2次）需要的周期数
target_count = 2
sumbars_result = SUMBARS(condition, target_count)
# 结果: [nan, nan, nan, nan, nan, nan, nan, nan, nan, 6., 7., 8., 9., 10., 6., 7., 8., 9., 10., 6.]
# 位置9: 从位置9向前，1(位置9)+0+0+0+0+1(位置4)=2，需要6个周期
# 位置14: 从位置14向前，1(位置14)+0+0+0+0+1(位置9)=2，需要6个周期
# 位置19: 从位置19向前，1(位置19)+0+0+0+0+1(位置14)=2，需要6个周期
# 其他位置（如10,11,12,13等）需要更多周期才能累加到2

# 获取当前值（最后一个元素）
current_periods = sumbars_result[-1]

if not np.isnan(current_periods):
    periods = int(current_periods)
    print(f"分钟数除以5余数为4出现{target_count}次需要 {periods} 个周期")
    print(f"当前分钟数: {minutes[-1]}, 条件满足次数: {condition[-1]}")
else:
    print("当前数据不足以满足条件出现2次")

# 在策略中使用示例
from vnpy_ctastrategy import CtaTemplate, ArrayManager
from mflang import SUMBARS
import numpy as np

class MyStrategy(CtaTemplate):
    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        self.am = ArrayManager()
        self.condition_array = []  # 维护条件数组
    
    def on_bar(self, bar: BarData):
        self.am.update_bar(bar)
        
        if not self.am.inited:
            return
        
        # 获取当前K线的分钟数
        current_minute = bar.datetime.minute
        
        # 判断条件：分钟数除以5余数为4
        condition_met = (current_minute % 5 == 4)
        
        # 将条件转换为数值并添加到数组（1表示满足条件，0表示不满足）
        self.condition_array.append(1 if condition_met else 0)
        
        # 保持数组长度（例如只保留最近100根K线）
        if len(self.condition_array) > 100:
            self.condition_array.pop(0)
        
        # 转换为numpy数组
        condition_np = np.array(self.condition_array)
        
        # 计算累加到2（出现2次）需要的周期数
        target_count = 2
        sumbars_result = SUMBARS(condition_np, target_count)
        periods = sumbars_result[-1]
        
        if not np.isnan(periods):
            periods_int = int(periods)
            print(f"分钟数除以5余数为4出现{target_count}次需要 {periods_int} 个周期")
            # 可以根据这个周期数进行交易决策
            if periods_int <= 5:
                print("条件在短时间内出现2次，可能有机会")
        else:
            print("当前数据不足以满足条件出现2次")
```

### BARPOS - 返回从第一根K线开始到当前的周期数

返回从第一根K线开始到当前的周期数。

**重要说明**: 
- 在麦语言中，BARPOS函数**没有参数**，直接使用`BARPOS`即可
- 在Python实现中，由于技术限制，需要传入一个数组来确定K线数量
- 本文档中的示例代码使用`BARPOS(close)`等写法是为了Python实现的需要，实际麦语言中应使用`BARPOS`

#### 参数（仅Python实现需要）

- `X`: 时间序列数组（numpy数组或列表），最新的值在数组末尾
  - 用于确定K线数量，可以是任意K线数据（如close、high、low等）
  - **注意**: 在麦语言中，BARPOS没有参数，不需要传入任何值

#### 返回值

- 返回一个整数数组，每个元素表示从第一根K线到当前位置的周期数
- 第一根K线返回1
- 第二根K线返回2
- 以此类推
- 返回值都是整数

#### 规则

1. BARPOS返回本地已有的K线根数，从本机上存在的数据开始算起
2. 本机已有的第一根K线上返回值为1
3. 针对每一根K线都能取到第一根K线开始到当前的周期数

#### 使用示例

```python
import numpy as np
from mflang import BARPOS

# 示例1: 基本用法
# 在麦语言中：BARPOS
# 在Python实现中，由于技术限制需要传入数组来确定K线数量
close = np.array([100.0, 101.0, 102.0, 103.0, 104.0, 105.0])
result = BARPOS(close)  # Python实现需要参数，麦语言中为BARPOS
# 结果: [1., 2., 3., 4., 5., 6.]
# 第一根K线返回1，第二根返回2，以此类推

# 示例2: 求本地已有数据的最小值（LLV(L, BARPOS)）
# 在麦语言中：LLV(L, BARPOS)
low = np.array([99.0, 100.0, 101.0, 102.0, 103.0, 104.0])
barpos = BARPOS(low)  # Python实现需要参数，麦语言中为BARPOS
# 使用BARPOS作为周期数，求最小值
# 等价于: min_value = low.min()
min_value = low.min()
print(f"本地已有数据的最小值: {min_value}")

# 示例3: 判断是否为第一根K线（IFELSE(BARPOS=1, H, 0)）
# 在麦语言中：IFELSE(BARPOS=1, H, 0)
high = np.array([101.0, 102.0, 103.0, 104.0, 105.0, 106.0])
barpos = BARPOS(high)  # Python实现需要参数，麦语言中为BARPOS
# 如果BARPOS=1，取最高值，否则取0
result = np.where(barpos == 1, high, 0)
# 结果: [101., 0., 0., 0., 0., 0.]
print(f"第一根K线的最高值: {result[0]}")
```

#### 如何获取当前值

`BARPOS` 返回的是 numpy 数组，以下是获取当前值（最后一个元素）的方法：

**方法1: 获取数组最后一个值（当前值）**

```python
import numpy as np
from mflang import BARPOS

# 计算 BARPOS
# 在麦语言中：BARPOS
# 在Python实现中，由于技术限制需要传入数组来确定K线数量
close = np.array([100.0, 101.0, 102.0, 103.0, 104.0, 105.0])
barpos_result = BARPOS(close)  # Python实现需要参数，麦语言中为BARPOS，结果: [1., 2., 3., 4., 5., 6.]

# 获取最后一个值（当前值）
current_barpos = barpos_result[-1]  # 6.0

# 转换为整数
current_pos = int(current_barpos)  # 6
print(f"当前是第 {current_pos} 根K线")
```

**方法2: 在策略中使用**

```python
from vnpy_ctastrategy import CtaTemplate, ArrayManager
from mflang import BARPOS
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
        
        # 计算BARPOS
        # 在麦语言中：BARPOS
        # 在Python实现中，由于技术限制需要传入数组来确定K线数量
        barpos_result = BARPOS(close)  # Python实现需要参数，麦语言中为BARPOS
        
        # 获取当前值（最后一个元素）
        current_barpos = barpos_result[-1]
        current_pos = int(current_barpos)
        
        print(f"当前是第 {current_pos} 根K线")
        
        # 判断是否为第一根K线
        if current_pos == 1:
            print("这是第一根K线")
            # 可以执行初始化逻辑
```

#### 从数据库或parquet文件加载数据使用示例（小恒指期货主连MHImain，交易所HKFE）

```python
import pandas as pd
import numpy as np
from mflang import BARPOS
from datetime import datetime

# 方式1: 从parquet文件加载1小时K线数据
def load_hour_data_from_parquet(file_path: str):
    """从parquet文件加载小恒指期货主连MHImain的1小时K线数据"""
    df = pd.read_parquet(file_path)
    
    # 确保datetime列存在
    if 'datetime' not in df.columns:
        df['datetime'] = pd.to_datetime(df['time'])
    else:
        df['datetime'] = pd.to_datetime(df['datetime'])
    
    # 过滤MHImain合约数据
    if 'symbol' in df.columns:
        df = df[df['symbol'] == 'MHImain']
    
    # 按时间排序
    df = df.sort_values('datetime').reset_index(drop=True)
    
    return df

# 加载数据
parquet_file = "data/MHImain_1h_bars.parquet"
df = load_hour_data_from_parquet(parquet_file)

# 获取K线数据数组
close = df['close'].values
low = df['low'].values
high = df['high'].values

# 计算BARPOS - 针对每一根K线都能取到第一根K线开始到当前的周期数
# 在麦语言中：BARPOS
# 在Python实现中，由于技术限制需要传入数组来确定K线数量
barpos = BARPOS(close)  # Python实现需要参数，麦语言中为BARPOS
print(f"总共有 {len(barpos)} 根K线")
print(f"第一根K线的位置: {int(barpos[0])}")  # 应该是1
print(f"最后一根K线的位置: {int(barpos[-1])}")  # 应该是总K线数

# 例1: 求本地已有数据的最小值（LLV(L, BARPOS)）
# 针对每一根K线，计算从第一根到当前K线的最低值
min_low_values = []
for i in range(len(low)):
    current_barpos = int(barpos[i])
    # 从第一根到当前K线的最低值
    min_low = low[:i+1].min()
    min_low_values.append(min_low)
    print(f"第 {current_barpos} 根K线: 从第一根到当前的最低值 = {min_low}")

# 例2: 判断是否为第一根K线（IFELSE(BARPOS=1, H, 0)）
# 如果当前K线是本机已有的第一根K线，取最高值，否则取0
result = np.where(barpos == 1, high, 0)
print(f"第一根K线的最高值: {result[0]}")
print(f"其他K线的值: {result[1:5]}")  # 应该是 [0., 0., 0., 0.]

# 方式2: 从数据库加载1小时K线数据
def load_hour_data_from_database(
    connection_string: str,
    table_name: str,
    symbol: str,
    start_time: datetime,
    end_time: datetime
):
    """从数据库加载小恒指期货主连MHImain的1小时K线数据"""
    import sqlalchemy
    
    engine = sqlalchemy.create_engine(connection_string)
    
    query = f"""
    SELECT datetime, open, high, low, close, volume
    FROM {table_name}
    WHERE symbol = '{symbol}'
    AND datetime >= '{start_time}'
    AND datetime <= '{end_time}'
    AND interval = '1h'
    ORDER BY datetime
    """
    
    df = pd.read_sql(query, engine)
    df['datetime'] = pd.to_datetime(df['datetime'])
    
    return df

# 从数据库加载数据
# db_connection = "postgresql://user:password@localhost:5432/dbname"
# df = load_hour_data_from_database(
#     db_connection,
#     "kline_data",
#     "MHImain",  # 小恒指期货主连
#     datetime(2024, 1, 1),
#     datetime.now()
# )
# 
# # 使用BARPOS
# # 在麦语言中：BARPOS
# # 在Python实现中，由于技术限制需要传入数组来确定K线数量
# close = df['close'].values
# barpos = BARPOS(close)  # Python实现需要参数，麦语言中为BARPOS
# 
# # 针对每一根K线处理
# for i in range(len(barpos)):
#     current_pos = int(barpos[i])
#     current_close = close[i]
#     print(f"第 {current_pos} 根K线，收盘价: {current_close}")
```

#### 在策略中使用（小恒指期货主连MHImain，交易所HKFE）

```python
from vnpy_ctastrategy import CtaTemplate, ArrayManager
from mflang import BARPOS
import numpy as np

class MHImainStrategy(CtaTemplate):
    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        self.am = ArrayManager()
    
    def on_bar(self, bar: BarData):
        self.am.update_bar(bar)
        
        if not self.am.inited:
            return
        
        # 获取小恒指期货主连MHImain的K线数据
        close = self.am.close
        low = self.am.low
        high = self.am.high
        
        # 计算BARPOS - 针对每一根K线都能取到第一根K线开始到当前的周期数
        # 在麦语言中：BARPOS
        # 在Python实现中，由于技术限制需要传入数组来确定K线数量
        barpos = BARPOS(close)  # Python实现需要参数，麦语言中为BARPOS
        current_pos = int(barpos[-1])
        
        # 例1: 求本地已有数据的最小值（LLV(L, BARPOS)）
        # 使用BARPOS作为周期数，求最低价的最小值
        min_low = low.min()
        print(f"[MHImain.HKFE] 本地已有数据的最低值: {min_low}")
        print(f"[MHImain.HKFE] 当前是第 {current_pos} 根K线")
        
        # 例2: 判断是否为第一根K线（IFELSE(BARPOS=1, H, 0)）
        # 如果当前K线是本机已有的第一根K线，取最高值，否则取0
        if current_pos == 1:
            first_high = high[0]
            print(f"[MHImain.HKFE] 第一根K线的最高值: {first_high}")
        else:
            print(f"[MHImain.HKFE] 当前是第 {current_pos} 根K线，不是第一根")
        
        # 使用BARPOS进行其他计算
        # 例如：只在数据积累到一定数量后才开始交易
        if current_pos >= 20:
            print(f"[MHImain.HKFE] 数据已积累 {current_pos} 根K线，可以开始交易")
        else:
            print(f"[MHImain.HKFE] 数据不足，当前只有 {current_pos} 根K线，需要至少20根")
```

#### 常见应用场景

**场景1: 求本地已有数据的最小值**

```python
import numpy as np
from mflang import BARPOS

# 小恒指期货主连MHImain的低价数据
low = np.array([19900.0, 19910.0, 19905.0, 19920.0, 19915.0, 19925.0])

# 计算BARPOS
# 在麦语言中：BARPOS
# 在Python实现中，由于技术限制需要传入数组来确定K线数量
barpos = BARPOS(low)  # Python实现需要参数，麦语言中为BARPOS

# 求本地已有数据的最小值（LLV(L, BARPOS)）
min_value = low.min()
print(f"本地已有数据的最小值: {min_value}")
```

**场景2: 判断是否为第一根K线**

```python
import numpy as np
from mflang import BARPOS

# 小恒指期货主连MHImain的最高价数据
high = np.array([20000.0, 20010.0, 20005.0, 20020.0, 20015.0, 20025.0])

# 计算BARPOS
# 在麦语言中：BARPOS
# 在Python实现中，由于技术限制需要传入数组来确定K线数量
barpos = BARPOS(high)  # Python实现需要参数，麦语言中为BARPOS

# IFELSE(BARPOS=1, H, 0)
# 如果BARPOS=1，取最高值，否则取0
result = np.where(barpos == 1, high, 0)
# 结果: [20000., 0., 0., 0., 0., 0.]

print(f"第一根K线的最高值: {result[0]}")
```

**场景3: 数据积累检查**

```python
import numpy as np
from mflang import BARPOS

# 小恒指期货主连MHImain的收盘价数据
close = np.array([19950.0, 19960.0, 19955.0, 19970.0, 19965.0, 19975.0])

# 计算BARPOS
# 在麦语言中：BARPOS
# 在Python实现中，由于技术限制需要传入数组来确定K线数量
barpos = BARPOS(close)  # Python实现需要参数，麦语言中为BARPOS
current_pos = int(barpos[-1])

# 检查数据是否足够
min_bars_required = 20
if current_pos >= min_bars_required:
    print(f"数据充足，当前有 {current_pos} 根K线，可以开始计算指标")
else:
    print(f"数据不足，当前只有 {current_pos} 根K线，需要至少 {min_bars_required} 根")
```

### HHV(X, N) - 求X在N个周期内的最高值

求X在N个周期内的最高值。

#### 参数

- `X`: 时间序列数组（numpy数组或列表），最新的值在数组末尾
- `N`: 周期数，可以是整数、浮点数或数组

#### 返回值

- 返回一个数组，每个元素是对应位置N个周期内的最高值
- 如果数据不足或N无效，返回NaN值

#### 规则

1. **N包含当前k线**（重要：N个周期包括当前位置）
2. 若N为0则从第一个有效值开始算起（从第一根K线到当前位置的最高值）
3. 当N为有效值，但当前的k线数不足N根，按照实际的根数计算
4. N为空值或NaN时，返回NaN
5. N可以是变量（数组）

#### 使用示例

```python
import numpy as np
from mflang import HHV

# 示例1: 基本用法（N=3，包含当前K线）
high = np.array([100.0, 101.0, 102.0, 103.0, 104.0, 105.0])
result = HHV(high, 3)
# 结果: [100., 101., 102., 103., 104., 105.]
# 位置0: 只有1根K线，最高值=100（按实际根数计算）
# 位置1: 有2根K线，最高值=max(100,101)=101（按实际根数计算）
# 位置2: 有3根K线，最高值=max(100,101,102)=102（N=3，包含当前K线）
# 位置3: 有3根K线，最高值=max(101,102,103)=103（N=3，包含当前K线）

# 示例2: N=0的情况（从第一个有效值开始算起）
high = np.array([100.0, 101.0, 102.0, 103.0, 104.0, 105.0])
result = HHV(high, 0)
# 结果: [100., 101., 102., 103., 104., 105.]
# 每个位置都是从第一根K线到当前位置的最高值
# 位置0: 最高值=100
# 位置1: 最高值=max(100,101)=101
# 位置2: 最高值=max(100,101,102)=102

# 示例3: 在策略中使用（小恒指期货主连MHImain，交易所HKFE）
from vnpy_ctastrategy import CtaTemplate, ArrayManager
from mflang import HHV

class MHImainStrategy(CtaTemplate):
    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        self.am = ArrayManager()
    
    def on_bar(self, bar: BarData):
        self.am.update_bar(bar)
        
        if not self.am.inited:
            return
        
        # 获取小恒指期货主连MHImain的最高价数组
        high = self.am.high
        
        # 计算前3根K线的最高价（HV(HIGH, 3)）
        # 注意：N=3包含当前K线，即当前K线和前2根K线的最高价
        hv_high_3 = HHV(high, 3)
        current_hv = hv_high_3[-1]
        
        if not np.isnan(current_hv):
            print(f"[MHImain.HKFE] 3个周期内的最高价（包含当前K线）: {current_hv}")
```

#### 如何获取当前值

`HHV` 返回的是 numpy 数组，以下是获取当前值（最后一个元素）的方法：

**方法1: 获取数组最后一个值（当前值）**

```python
import numpy as np
from mflang import HHV

# 计算 HHV
high = np.array([100.0, 101.0, 102.0, 103.0, 104.0, 105.0])
hhv_result = HHV(high, 3)  # [100., 101., 102., 103., 104., 105.]

# 获取最后一个值（当前值）
current_hhv = hhv_result[-1]  # 105.0

# 检查是否为有效值
if not np.isnan(current_hhv):
    print(f"3个周期内的最高价（包含当前K线）: {current_hhv}")
```

#### 常见应用场景

**场景1: 计算N周期内的最高价（小恒指期货主连MHImain）**

```python
import numpy as np
from mflang import HHV

# 小恒指期货主连MHImain的最高价数据
high = np.array([20000.0, 20010.0, 20005.0, 20020.0, 20015.0, 20025.0])

# 计算3个周期内的最高价（包含当前K线）
hhv_result = HHV(high, 3)
current_hhv = hhv_result[-1]

print(f"3个周期内的最高价（包含当前K线）: {current_hhv}")
```

**场景2: N=0的情况（从第一根K线开始）**

```python
import numpy as np
from mflang import HHV

# 小恒指期货主连MHImain的最高价数据
high = np.array([20000.0, 20010.0, 20005.0, 20020.0, 20015.0, 20025.0])

# N=0: 从第一个有效值开始算起
hhv_result = HHV(high, 0)
current_hhv = hhv_result[-1]

print(f"从第一根K线到当前的最高价: {current_hhv}")
```

**场景3: 数据不足N根的情况**

```python
import numpy as np
from mflang import HHV

# 只有2根K线，但N=5
high = np.array([20000.0, 20010.0])

# 数据不足5根，按照实际的根数计算
hhv_result = HHV(high, 5)
# 结果: [20000., 20010.]
# 位置0: 只有1根K线，最高值=20000
# 位置1: 只有2根K线，最高值=max(20000,20010)=20010

print(f"实际计算的最高价: {hhv_result[-1]}")
```

### #IMPORT - 跨周期引用函数

跨周期引用函数用于引用不同周期的指标数据。

#### 语法

```
#IMPORT [PERIOD,N,FORMULA] AS VAR
```

#### 参数说明

- `PERIOD`: 周期类型，支持以下值：
  - `MIN`: 分钟周期
  - `HOUR`: 小时周期
  - `CUSHOUR`: 自定义小时周期
  - `DAY`: 日周期
  - `WEEK`: 一周
  - `MONTH`: 月周期
  - `QUARTER`: 一季度
  - `YEAR`: 年周期
- `N`: 周期参数，必须为大于等于1的整数
  - 对于 `WEEK` 和 `QUARTER` 周期，N>1时按1计算
- `FORMULA`: 被引用的指标名称（字母、汉字或数字命名）
- `VAR`: 定义的变量名（不能以数字开头，不能与函数名重复）

#### 规则

1. PERIOD为周期，N为具体的参数，FORMULA为引用指标名，VAR为定义变量名
2. 支持引用自定义周期
3. N必须为大于等于1的整数，周、季周期，N写入大于1的数，按照1计算
4. 引用常规小时周期使用HOUR，引用自定义小时周期需要使用CUSHOUR
5. 该函数不支持加载到量能周期使用
6. 该函数可以小周期引用大周期，也可以大周期引用小周期
7. 被引用的指标中不能存在引用（避免循环引用）
8. FORMULA引用指标名可以为字母、汉字或数字命名的指标
9. 定义变量名不能与函数名重复
10. 一个模型中#IMPORT、#CALL、#CALL_PLUS、#CALL_OTHER总的语句个数不能超过6个
11. 使用该函数编写末尾不能编写分号

#### 使用示例

**示例1: 引用日周期上一个周期的收盘价**

```python
# 被引用的指标（保存为AA）:
# CC:REF(C,1);

# 主指标:
from mflang.import_parser import ImportParser

code = """
#IMPORT[DAY,1,AA] AS VAR
CC:VAR.CC;
"""

# 解析 #IMPORT 语句
import_statements = ImportParser.parse_code(code)
for stmt in import_statements:
    print(f"周期: {stmt.period.value}, N: {stmt.n}, 指标: {stmt.formula}, 变量: {stmt.var_name}")
```

**示例2: 引用日周期上的收盘价**

```python
# 被引用的指标（保存为CC）:
# CC:C;

# 主指标:
code = """
#IMPORT[DAY,1,CC] AS VAR
CC:=VAR.CC;
CC1:REF(CC,1);
"""
```

**示例3: 引用自定义小时周期和分钟周期**

```python
# 被引用的指标（保存为AA）:
# CC:=REF(C,1);

# 主指标:
code = """
#IMPORT[CUSHOUR,6,AA]AS S
CC1:=S.CC;

#IMPORT[MIN,1,AA]AS R
CC2:=R.CC;
"""

import_statements = ImportParser.parse_code(code)
for stmt in import_statements:
    print(f"{stmt}")
```

**示例4: 判断趋势（当前收盘价大于前一个5分钟周期的开盘价）**

```python
# 被引用的指标（保存为MIN5_OPEN）:
# 获取5分钟周期前一个周期的开盘价
# PREV_OPEN:REF(O,1);

# 主指标（1分钟周期）:
from mflang.import_parser import ImportParser
from vnpy_ctastrategy import CtaTemplate, ArrayManager
from vnpy.trader.object import BarData

code = """
#IMPORT[MIN,5,MIN5_OPEN] AS MIN5
PREV_OPEN:=MIN5.PREV_OPEN;
"""

# 解析 #IMPORT 语句
import_statements = ImportParser.parse_code(code)

# 在策略中使用
class TrendStrategy(CtaTemplate):
    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        self.am = ArrayManager()
        # 这里需要实现跨周期数据获取逻辑
        # 实际使用时需要集成 CrossPeriodDataManager
    
    def on_bar(self, bar: BarData):
        self.am.update_bar(bar)
        
        if not self.am.inited:
            return
        
        # 获取当前收盘价
        current_close = bar.close_price
        
        # 获取前一个5分钟周期的开盘价
        # 这里需要从跨周期数据中获取
        # prev_5min_open = self.get_cross_period_data("MIN5", "PREV_OPEN")
        
        # 判断条件：当前收盘价 > 前一个5分钟周期的开盘价
        # if prev_5min_open is not None and current_close > prev_5min_open:
        #     print("趋势多")
        
        # 实际实现示例（需要完整的数据管理）:
        # 1. 通过 CrossPeriodDataManager 获取5分钟周期数据
        # 2. 执行被引用的指标 MIN5_OPEN，获取 PREV_OPEN
        # 3. 将数据对齐到当前1分钟周期
        # 4. 进行比较判断
```

**示例4的完整实现思路：**

```python
from mflang import ImportParser, CrossPeriodDataManager, ImportResolver
from datetime import datetime
import numpy as np

# 1. 定义被引用的指标（5分钟周期）
min5_formula = """
PREV_OPEN:REF(O,1);
"""

# 2. 主指标代码
main_code = """
#IMPORT[MIN,5,MIN5_OPEN] AS MIN5
PREV_OPEN:=MIN5.PREV_OPEN;
"""

# 3. 解析 #IMPORT 语句
import_statements = ImportParser.parse_code(main_code)

# 4. 在策略中实现
class TrendStrategy(CtaTemplate):
    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        self.am = ArrayManager()
        self.data_manager = CrossPeriodDataManager()
        self.resolver = ImportResolver(self.data_manager)
    
    def on_bar(self, bar: BarData):
        self.am.update_bar(bar)
        
        if not self.am.inited:
            return
        
        # 获取当前收盘价
        current_close = bar.close_price
        
        # 解析跨周期引用（需要提供5分钟周期数据）
        # 实际实现中需要：
        # 1. 获取5分钟周期的K线数据
        # 2. 执行被引用的指标公式，计算 PREV_OPEN
        # 3. 将结果对齐到当前1分钟周期
        
        # 伪代码示例：
        # results = self.resolver.resolve_imports(
        #     import_statements,
        #     symbol=bar.vt_symbol,
        #     current_time=bar.datetime,
        #     current_data=self.am.close
        # )
        # 
        # if "MIN5" in results and "PREV_OPEN" in results["MIN5"]:
        #     prev_5min_open = results["MIN5"]["PREV_OPEN"][-1]
        #     
        #     if not np.isnan(prev_5min_open) and current_close > prev_5min_open:
        #         print("趋势多")
```

**完整实现（从数据库或parquet文件加载数据）：**

```python
import pandas as pd
import numpy as np
from datetime import datetime
from mflang import ImportParser, CrossPeriodDataManager, ImportResolver
from mflang.import_parser import PeriodType

# 步骤1: 从parquet文件加载5分钟K线数据
def load_5min_data_from_parquet(file_path: str, symbol: str = None):
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

# 步骤2: 创建增强的数据管理器
class EnhancedDataManager(CrossPeriodDataManager):
    def __init__(self):
        super().__init__()
        self.period_data = {}
    
    def load_5min_data(self, file_path: str, symbol: str):
        """加载5分钟周期数据"""
        df = load_5min_data_from_parquet(file_path, symbol)
        
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
    
    def get_5min_prev_open(self, symbol: str, current_time: datetime):
        """获取前一个5分钟周期的开盘价"""
        from mflang import REF
        
        cache_key = f"{symbol}_MIN_5"
        if cache_key not in self.period_data:
            return None
        
        data = self.period_data[cache_key]
        open_prices = data['open']
        
        # 计算前一个周期的开盘价
        prev_open = REF(open_prices, 1)
        
        # 找到当前时间对应的5分钟K线位置
        # 简化处理：返回最后一个值
        if len(prev_open) > 0:
            return prev_open[-1]
        
        return None

# 步骤3: 使用策略
class TrendStrategy:
    def __init__(self, symbol: str, data_file: str):
        self.symbol = symbol
        self.data_manager = EnhancedDataManager()
        self.data_manager.load_5min_data(data_file, symbol)
        
        # 解析 #IMPORT 语句
        code = """
#IMPORT[MIN,5,MIN5_OPEN] AS MIN5
PREV_OPEN:=MIN5.PREV_OPEN;
"""
        self.import_statements = ImportParser.parse_code(code)
    
    def check_trend(self, current_close: float, current_time: datetime):
        """检查趋势：当前收盘价是否大于前一个5分钟周期的开盘价"""
        prev_open = self.data_manager.get_5min_prev_open(self.symbol, current_time)
        
        if prev_open is not None and not np.isnan(prev_open):
            if current_close > prev_open:
                print(f"[{current_time}] 趋势多 - 当前收盘价: {current_close}, 前5分钟开盘价: {prev_open}")
                return True
        
        return False

# 步骤4: 使用示例
# 假设parquet文件路径
parquet_file = "data/5min_bars.parquet"

# 创建策略实例（小恒指期货主连，交易所HKFE）
strategy = TrendStrategy(symbol="MHImain", data_file=parquet_file)

# 处理K线
current_time = datetime.now()
current_close = 105.5
strategy.check_trend(current_close, current_time)
```

**从数据库加载数据的示例：**

```python
import sqlalchemy
import pandas as pd
from datetime import datetime

def load_5min_data_from_database(
    connection_string: str,
    table_name: str,
    symbol: str,
    start_time: datetime,
    end_time: datetime
):
    """从数据库加载5分钟K线数据"""
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

# 使用数据库数据（小恒指期货主连，交易所HKFE）
db_connection = "postgresql://user:password@localhost:5432/dbname"
df = load_5min_data_from_database(
    db_connection,
    "kline_data",
    "MHImain",  # 小恒指期货主连
    datetime(2024, 1, 1),
    datetime.now()
)

# 后续处理与parquet文件相同
```

#### 在策略中使用

```python
from mflang.import_parser import ImportParser, ImportStatement
from mflang.cross_period import ImportResolver, CrossPeriodDataManager

# 解析代码中的 #IMPORT 语句
code = """
#IMPORT[DAY,1,AA] AS VAR
CC:VAR.CC;
"""

# 1. 解析 #IMPORT 语句
import_statements = ImportParser.parse_code(code)

# 2. 创建数据管理器和解析器
data_manager = CrossPeriodDataManager()
resolver = ImportResolver(data_manager)

# 3. 解析跨周期引用（需要提供当前合约、时间等）
# results = resolver.resolve_imports(
#     import_statements,
#     symbol="MHImain.HKFE",
#     current_time=datetime.now(),
#     current_data=current_bar_data
# )

# 4. 使用结果
# var_cc = results["VAR"]["CC"]
```

#### 验证功能

```python
from mflang.import_parser import ImportParser

# 验证变量名
is_valid = ImportParser.validate_variable_name("VAR1")  # True
is_valid = ImportParser.validate_variable_name("1VAR")  # False (以数字开头)
is_valid = ImportParser.validate_variable_name("REF")   # False (与函数名重复)

# 解析单个语句
line = "#IMPORT[DAY,1,AA] AS VAR"
stmt = ImportParser.parse_import_statement(line)
if stmt:
    print(f"周期: {stmt.period.value}")
    print(f"N: {stmt.n}")
    print(f"指标: {stmt.formula}")
    print(f"变量: {stmt.var_name}")
```

#### 注意事项

1. **避免循环引用**: 被引用的指标中不能包含其他 #IMPORT 语句
2. **数据对齐**: 跨周期引用时，需要将大周期数据对齐到小周期，或将小周期数据聚合到大周期
3. **性能考虑**: 跨周期引用需要加载不同周期的数据，可能影响性能
4. **数据可用性**: 确保被引用的周期数据可用，否则可能返回空值

### 复杂表达式解析示例

**示例: 解析 #IMPORT[MIN,5,MACD] AS MIN5_VAR；REF(BARPOS, BARSLAST(MIN5_VAR.MACD > 0 && CLOSE > HHV(HIGH, 3)))**

这个示例展示如何解析复杂的麦语言表达式，从数据库或parquet文件加载小恒指期货主连MHImain的1分钟和跨周期K线数据。

**表达式说明：**
- **#IMPORT[MIN,5,MACD] AS MIN5_VAR**: 使用#IMPORT引用5分钟周期的MACD数据，MACD是标准公式名称，通过解析import_stmt确定跨周期引用对应的周期
- **BARPOS**: 当前1分钟周期里的K线位置，从本机第一根K线开始计数
- **MIN5_VAR.MACD**: 通过#IMPORT引用5分钟周期的MACD数据
- **条件**: MIN5_VAR.MACD > 0 && CLOSE > HHV(HIGH, 3)
- **返回**: REF(BARPOS, BARSLAST结果)，即BARPOS根K线前的BARSLAST值对应的K线位置（BARPOS）

```python
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from mflang import BARSLAST, BARPOS, HHV
from mflang import ImportParser
from mflang.import_parser import PeriodType
import talib

# 步骤1: 从parquet文件加载数据（小恒指期货主连MHImain，交易所HKFE）
def load_minute_data_from_parquet(file_path: str, symbol: str = "MHImain", interval: str = "1m"):
    """从parquet文件加载K线数据"""
    df = pd.read_parquet(file_path)
    
    if 'datetime' not in df.columns:
        df['datetime'] = pd.to_datetime(df['time'])
    else:
        df['datetime'] = pd.to_datetime(df['datetime'])
    
    if 'symbol' in df.columns:
        df = df[df['symbol'] == symbol]
    if 'interval' in df.columns:
        df = df[df['interval'] == interval]
    
    df = df.sort_values('datetime').reset_index(drop=True)
    return df

# 加载1分钟K线数据
df_1min = load_minute_data_from_parquet("data/MHImain_1m_bars.parquet", "MHImain", "1m")

# 步骤2: 解析#IMPORT语句
import_code = """
#IMPORT[MIN,5,MACD] AS MIN5_VAR
"""
import_statements = ImportParser.parse_code(import_code)
import_stmt = import_statements[0]
print(f"解析#IMPORT语句: {import_stmt}")
print(f"  周期: {import_stmt.period.value}, N: {import_stmt.n}, 指标: {import_stmt.formula}, 变量: {import_stmt.var_name}")

# 步骤3: 根据import_stmt确定跨周期引用对应的周期
# 使用import_stmt.period和import_stmt.n来确定需要加载的周期数据
target_period_minutes = None
if import_stmt.period == PeriodType.MIN:
    target_period_minutes = import_stmt.n
elif import_stmt.period == PeriodType.HOUR:
    target_period_minutes = import_stmt.n * 60
elif import_stmt.period == PeriodType.CUSHOUR:
    target_period_minutes = import_stmt.n * 60
elif import_stmt.period == PeriodType.DAY:
    target_period_minutes = import_stmt.n * 24 * 60
else:
    raise ValueError(f"不支持的周期类型: {import_stmt.period.value}")

print(f"  目标周期: {target_period_minutes}分钟")

# 步骤4: 加载跨周期数据（根据import_stmt确定周期）
# 这里假设已经加载了对应周期的数据
df_cross_period = load_minute_data_from_parquet("data/MHImain_5m_bars.parquet", "MHImain", "5m")

# 步骤5: 获取1分钟周期的数据
close_1min = df_1min['close'].values
high_1min = df_1min['high'].values

# 步骤6: 计算BARPOS - 当前K线位置（从本机第一根K线开始计数）
barpos = BARPOS(close_1min)  # BARPOS是当前K线位置数组

# 步骤7: 通过#IMPORT获取MIN5_VAR.MACD（跨周期的MACD数据）
# 计算跨周期MACD
def calculate_macd(close: np.ndarray):
    """计算MACD指标"""
    macd, signal, hist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
    return macd

close_target = df_cross_period['close'].values
macd_target = calculate_macd(close_target)  # 被引用的指标在目标周期上的MACD

# 步骤8: 将跨周期MACD对齐到1分钟周期（#IMPORT的跨周期引用）
# 根据import_stmt确定的目标周期进行对齐
# 对齐后的数据就是MIN5_VAR.MACD
macd_target_aligned = np.full(len(df_1min), np.nan, dtype=float)
for i, dt_1min in enumerate(df_1min['datetime']):
    for j, dt_target in enumerate(df_cross_period['datetime']):
        if dt_1min >= dt_target and dt_1min < dt_target + timedelta(minutes=target_period_minutes):
            if j < len(macd_target):
                macd_target_aligned[i] = macd_target[j]
            break

# 步骤9: 计算HHV(HIGH, 3) - 前3根K线的最高价（包含当前K线）
hv_high_3 = HHV(high_1min, 3)

# 步骤10: 计算条件：MIN5_VAR.MACD > 0 && CLOSE > HHV(HIGH, 3)
min5_var_macd = macd_target_aligned  # MIN5_VAR.MACD（根据import_stmt确定的目标周期）
cond1 = min5_var_macd > 0  # MIN5_VAR.MACD > 0
cond2 = close_1min > hv_high_3  # CLOSE > HHV(HIGH, 3)
condition = cond1 & cond2  # 组合条件

# 步骤11: 计算BARSLAST(condition) - 上一次条件成立到当前的周期数
barslast_result = BARSLAST(condition)

# 步骤12: 计算REF(BARPOS, BARSLAST结果)
# BARPOS是数组，REF函数支持数组作为N参数
# REF(BARPOS, BARSLAST结果) - BARPOS根K线前的BARSLAST值对应的K线位置（BARPOS）
result = np.full_like(barslast_result, np.nan, dtype=float)
for i in range(len(barslast_result)):
    barpos_val = int(barpos[i])
    if i < len(barslast_result) and not np.isnan(barslast_result[i]):
        barslast_val = int(barslast_result[i])
        if barslast_val >= 0 and barpos_val > barslast_val:
            result[i] = barpos_val - barslast_val

# 步骤13: 获取当前值（最后一根K线的结果）
current_result = result[-1]
current_barpos = int(barpos[-1])

if not np.isnan(current_result):
    barpos_value = int(current_result)
    print(f"[MHImain.HKFE] 当前K线位置（BARPOS）: {current_barpos}")
    print(f"[MHImain.HKFE] REF(BARPOS, BARSLAST结果): {barpos_value}")
    print(f"[MHImain.HKFE] 说明: 最近一次满足条件的K线位置是第 {barpos_value} 根K线")
    print(f"[MHImain.HKFE] （K线位置从本机第一根K线开始计算）")
else:
    print("[MHImain.HKFE] 未找到满足条件的K线或数据不足")

# 完整示例请参考: mflang/example_parse_formula.py
```

**关键点说明：**

1. **#IMPORT语句解析**: 使用ImportParser解析#IMPORT[MIN,5,MACD] AS MIN5_VAR语句（MACD是标准公式名称）
2. **根据import_stmt确定周期**: 使用import_stmt.period和import_stmt.n来确定跨周期引用对应的周期（如MIN,5表示5分钟）
3. **动态周期计算**: 根据周期类型（MIN、HOUR、DAY等）和N值计算目标周期分钟数
4. **BARPOS**: 使用BARPOS获取当前K线位置（从本机第一根K线开始计数）
5. **跨周期引用**: 通过MIN5_VAR.MACD访问跨周期的MACD数据（根据import_stmt确定的目标周期）
6. **数据对齐**: 根据目标周期将跨周期MACD对齐到1分钟周期
7. **条件计算**: MIN5_VAR.MACD > 0 && CLOSE > HHV(HIGH, 3)
8. **BARSLAST**: 计算上一次条件成立到当前的周期数
9. **REF**: 引用BARPOS根K线前的BARSLAST值对应的K线位置（BARPOS是数组）
10. **结果**: 返回BARPOS根K线前的BARSLAST值对应的K线位置（BARPOS）（K线位置从本机第一根K线开始计算）

**完整实现请参考**: `mflang/example_parse_formula.py`

## 测试

运行测试文件验证函数功能：

```bash
# 测试基础函数
python mflang/test_functions.py

# 测试 #IMPORT 解析
python mflang/test_import.py

# 测试复杂表达式解析
python mflang/example_parse_formula.py
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

