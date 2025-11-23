# 多周期自定义指标管理器使用指南

## 概述

`IndicatorManager` 是一个用于在多个周期计算和存储自定义指标数据的工具类。它解决了以下问题：

1. **长期历史数据存储**：`ArrayManager` 只存储固定数量（默认100）的历史数据，无法满足需要长期历史数据的指标计算需求
2. **多周期指标管理**：支持在多个周期（1分钟、5分钟、日线等）同时计算和管理指标
3. **实时增量更新**：在收到新的tick或K线数据时，增量计算指标值，避免重复计算
4. **运行时指标值支持**：支持在K线聚合过程中计算和引用运行时指标值，无需等待K线收盘
5. **数据持久化**：支持将指标数据保存到文件系统，下次启动时自动加载

## 核心功能

### 1. 指标注册

注册一个自定义指标计算函数：

```python
def my_custom_indicator(bars: List[BarData]) -> np.ndarray:
    """自定义指标计算函数"""
    closes = np.array([bar.close_price for bar in bars])
    # 计算指标...
    return indicator_values

manager.register_indicator(
    interval=Interval.MINUTE,
    indicator_name="my_indicator",
    calculator=my_custom_indicator,
    max_history=10000  # 最多保存10000个历史值
)
```

### 2. 历史数据初始化

在策略初始化时，从数据库加载历史K线数据并计算指标：

```python
database = self.cta_engine.database
manager.initialize_indicators(
    Interval.MINUTE,
    days=365,  # 加载1年历史数据
    database=database
)
```

### 3. 实时更新

在收到新的K线数据时，增量更新指标。`IndicatorManager` 支持两种更新模式：

#### 3.1 历史指标值更新（K线已完成）

当K线收盘时，更新历史指标值：

```python
def on_bar(self, bar: BarData):
    # 更新指标（历史值：K线已完成）
    manager.update_indicator(Interval.MINUTE, bar, is_runtime=False)
    
    # 获取最新历史指标值
    latest_value = manager.get_indicator(Interval.MINUTE, "my_indicator", -1)
    
    # 获取历史指标数组（用于需要多个历史值的计算）
    history_array = manager.get_indicator_array(
        Interval.MINUTE,
        "my_indicator",
        length=20  # 获取最近20个值
    )
```

#### 3.2 运行时指标值更新（K线正在聚合）

当K线正在聚合过程中，可以更新运行时指标值：

```python
def on_bar(self, bar: BarData):
    # 更新1分钟指标（历史值）
    manager.update_indicator(Interval.MINUTE, bar, is_runtime=False)
    
    # 更新5分钟指标（运行时值：基于正在聚合的5分钟K线）
    if hasattr(self.bg5, 'window_bar') and self.bg5.window_bar is not None:
        manager.update_indicator(
            Interval.MINUTE_5,
            self.bg5.window_bar,  # 正在聚合的5分钟K线
            is_runtime=True
        )
    
    # 获取5分钟指标的运行时值
    runtime_value = manager.get_runtime_indicator(
        Interval.MINUTE_5,
        "my_indicator"
    )
    
    # 或者使用get_indicator的use_runtime参数
    runtime_value = manager.get_indicator(
        Interval.MINUTE_5,
        "my_indicator",
        use_runtime=True
    )
```

**历史值 vs 运行时值：**

| 特性 | 历史值 | 运行时值 |
|------|--------|---------|
| 更新时机 | K线收盘时 | K线聚合过程中 |
| 数据来源 | 已完成的K线 | 正在聚合的K线（window_bar） |
| 存储位置 | 持久化存储 | 内存临时存储 |
| 使用场景 | 策略回测、历史分析 | 实时交易决策 |
| 获取方法 | `get_indicator()` | `get_runtime_indicator()` |

### 4. 数据持久化

指标数据会自动保存到文件系统（默认路径：`.vntrader/indicators/{vt_symbol}/`），下次启动时自动加载。

## 使用场景

### 场景1：在tick数据中使用指标

```python
def on_tick(self, tick: TickData):
    # 使用BarGenerator将tick聚合为1分钟K线
    self.bg1min.update_tick(tick)

def on_1min_bar(self, bar: BarData):
    # 当1分钟K线完成时，更新指标
    self.indicator_manager.update_indicator(Interval.MINUTE, bar)
    
    # 获取指标值用于交易决策
    indicator_value = self.indicator_manager.get_indicator(
        Interval.MINUTE,
        "my_indicator",
        -1
    )
    
    # 使用指标进行交易...
```

### 场景2：多周期指标计算

```python
# 注册多个周期的指标
manager.register_indicator(Interval.MINUTE, "indicator", calculator)
manager.register_indicator(Interval.MINUTE_5, "indicator", calculator)
manager.register_indicator(Interval.DAILY, "indicator", calculator)

# 初始化所有周期
manager.initialize_indicators(Interval.MINUTE, days=365, database=database)
manager.initialize_indicators(Interval.MINUTE_5, days=365, database=database)
manager.initialize_indicators(Interval.DAILY, days=365, database=database)

# 在策略中使用
def on_bar(self, bar: BarData):
    # 更新1分钟指标（历史值）
    manager.update_indicator(Interval.MINUTE, bar, is_runtime=False)
    
    # 获取不同周期的历史指标值
    value_1min = manager.get_indicator(Interval.MINUTE, "indicator", -1)
    value_5min = manager.get_indicator(Interval.MINUTE_5, "indicator", -1)
    value_daily = manager.get_indicator(Interval.DAILY, "indicator", -1)
```

### 场景2.1：在1分钟K线中引用5分钟指标的运行时值

这是运行时指标值的典型应用场景：在1分钟K线更新时，可以引用5分钟指标的运行时值，无需等待5分钟K线收盘。

```python
def on_bar(self, bar: BarData):
    """1分钟K线更新"""
    # 更新1分钟指标（历史值）
    manager.update_indicator(Interval.MINUTE, bar, is_runtime=False)
    
    # 获取1分钟指标值
    value_1min = manager.get_indicator(Interval.MINUTE, "indicator", -1)
    
    # 更新5分钟指标的运行时值（基于正在聚合的5分钟K线）
    if hasattr(self.bg5, 'window_bar') and self.bg5.window_bar is not None:
        manager.update_indicator(
            Interval.MINUTE_5,
            self.bg5.window_bar,  # 正在聚合的5分钟K线
            is_runtime=True
        )
    
    # 获取5分钟指标的运行时值（正在聚合的K线对应的指标值）
    value_5min_runtime = manager.get_runtime_indicator(
        Interval.MINUTE_5,
        "indicator"
    )
    
    # 如果运行时值不存在，使用历史值作为后备
    if value_5min_runtime is None:
        value_5min_runtime = manager.get_indicator(
            Interval.MINUTE_5,
            "indicator",
            -1
        )
    
    # 使用1分钟和5分钟指标进行交易决策
    if value_1min > value_5min_runtime:
        # 交易逻辑...
        pass

def on_5min_bar(self, bar: BarData):
    """5分钟K线收盘时"""
    # 更新5分钟指标（历史值：K线已完成）
    manager.update_indicator(Interval.MINUTE_5, bar, is_runtime=False)
    
    # 运行时值会自动清空（已转为历史值）
    # 获取历史值
    value_5min_history = manager.get_indicator(
        Interval.MINUTE_5,
        "indicator",
        -1
    )
```

### 场景3：需要长期历史数据的指标

某些指标（如年化收益率、长期趋势等）需要非常长的历史数据。使用 `IndicatorManager` 可以：

1. 在初始化时加载足够长的历史数据（如1年、2年）
2. 计算指标并存储
3. 实时更新时只计算最新值

```python
# 加载2年历史数据
manager.initialize_indicators(Interval.DAILY, days=730, database=database)

# 获取长期历史指标数组
long_term_array = manager.get_indicator_array(
    Interval.DAILY,
    "long_term_indicator",
    length=500  # 获取最近500个值
)
```

## 数据存储

### 存储格式选择

`IndicatorManager` 支持两种存储格式：

#### 1. **Parquet格式（推荐，默认）**

**优势：**
- ✅ **压缩率高**：使用zstd压缩，文件大小通常比pkl小50-80%
- ✅ **读取速度快**：列式存储，支持按时间范围查询
- ✅ **跨语言兼容**：可以用pandas、polars、R、Java等读取
- ✅ **包含时间信息**：保存了每个指标值对应的时间戳
- ✅ **与VNPY AlphaLab一致**：VNPY的AlphaLab也使用parquet格式

**缺点：**
- 需要安装`polars`库（`pip install polars`）
- 需要将数据转换为DataFrame格式

**使用方式：**
```python
manager = IndicatorManager(
    vt_symbol="MHImain.HKFE",
    storage_format="parquet"  # 默认值
)
```

#### 2. **PKL格式（Python Pickle）**

**优势：**
- ✅ **简单易用**：Python内置支持，无需额外依赖
- ✅ **可序列化任意对象**：可以保存复杂的Python对象

**缺点：**
- ❌ **只能被Python读取**：其他语言无法读取
- ❌ **文件较大**：无压缩，文件大小通常比parquet大2-5倍
- ❌ **安全性问题**：pickle文件可能包含恶意代码
- ❌ **不包含时间信息**：只保存指标值，没有对应的时间戳

**使用方式：**
```python
manager = IndicatorManager(
    vt_symbol="MHImain.HKFE",
    storage_format="pkl"
)
```

### 文件系统存储（默认）

指标数据保存在：
```
.vntrader/indicators/{vt_symbol}/{interval}_indicators.{format}
```

**Parquet格式示例：**
```
.vntrader/indicators/MHImain_HKFE/MINUTE_indicators.parquet
.vntrader/indicators/MHImain_HKFE/MINUTE_5_indicators.parquet
```

**PKL格式示例：**
```
.vntrader/indicators/MHImain_HKFE/MINUTE_indicators.pkl
.vntrader/indicators/MHImain_HKFE/MINUTE_5_indicators.pkl
```

### 格式兼容性

- 如果存在parquet文件，优先加载parquet格式
- 如果只有pkl文件，会自动加载pkl格式
- 支持从pkl迁移到parquet：删除pkl文件后，下次保存会自动使用parquet格式

### 自定义存储路径

```python
manager = IndicatorManager(
    vt_symbol="MHImain.HKFE",
    storage_path="/path/to/custom/storage",  # 自定义路径
    storage_format="parquet"  # 或 "pkl"
)
```

### 数据库存储（未来扩展）

目前支持从数据库加载历史K线数据，但指标数据本身存储在文件系统。未来可以扩展为将指标数据也存储到数据库中。

## 性能考虑

1. **内存使用**：使用 `deque` 限制最大历史数据数量，避免内存无限增长
2. **计算效率**：实时更新时只计算最新值，不重复计算历史数据
3. **文件I/O**：每100根K线保存一次，避免频繁写入文件
4. **历史数据缓存**：保留最近1000根K线在内存中，用于指标计算

## 注意事项

1. **指标计算函数的返回值**：
   - 可以返回单个值（`float`）
   - 可以返回数组（`np.ndarray` 或 `list`）
   - 如果返回数组，`update_indicator` 只会取最后一个值

2. **历史数据长度**：
   - 确保加载足够长的历史数据以满足指标计算需求
   - 某些指标（如250日均线）需要至少250根K线

3. **多周期同步**：
   - 不同周期的指标是独立计算的
   - 确保在正确的回调函数中更新对应周期的指标

4. **运行时指标值的使用**：
   - 运行时值只在K线聚合过程中存在，K线收盘后会自动清空
   - 运行时值不会持久化到文件，只存在于内存中
   - 如果运行时值不存在，应该使用历史值作为后备
   - 运行时值的计算基于正在聚合的K线（`window_bar`），可能包含不完整的数据

5. **历史值 vs 运行时值的选择**：
   - **历史值**：用于策略回测、历史分析、K线收盘后的交易决策
   - **运行时值**：用于实时交易决策，在K线聚合过程中就能获取指标值

6. **数据一致性**：
   - 指标数据会在策略停止时自动保存
   - 如果程序异常退出，可能会丢失部分未保存的数据
   - 运行时值不会保存，只保存历史值

## 完整示例

参考 `vnpy_ctastrategy/vnpy_ctastrategy/strategies/indicator_manager_example.py` 查看完整的使用示例。

## 与ArrayManager的区别

| 特性 | ArrayManager | IndicatorManager |
|------|-------------|------------------|
| 历史数据长度 | 固定（默认100） | 可配置（默认10000） |
| 数据持久化 | 否 | 是（文件系统） |
| 多周期支持 | 需要多个实例 | 内置支持 |
| 长期历史数据 | 不支持 | 支持 |
| 使用场景 | 短期技术指标 | 长期自定义指标 |

## 为什么使用Parquet而不是PKL？

### PKL格式的问题

1. **文件大小**：PKL格式不压缩，文件通常比Parquet大2-5倍
2. **跨语言兼容性**：只能被Python读取，无法用其他工具分析
3. **时间信息缺失**：PKL格式只保存指标值，没有对应的时间戳，无法按时间范围查询
4. **安全性**：Pickle文件可能包含恶意代码，存在安全风险

### Parquet格式的优势

1. **压缩率高**：使用zstd压缩，文件大小通常比PKL小50-80%
2. **读取速度快**：列式存储，支持高效的列式查询
3. **包含时间信息**：保存了每个指标值对应的时间戳，支持按时间范围查询
4. **跨语言兼容**：可以用pandas、polars、R、Java等工具读取和分析
5. **与VNPY生态一致**：VNPY的AlphaLab也使用Parquet格式

### 性能对比示例

假设有10,000个指标值：

| 格式 | 文件大小 | 加载时间 | 跨语言支持 |
|------|---------|---------|-----------|
| PKL | ~800KB | ~50ms | ❌ 仅Python |
| Parquet | ~200KB | ~30ms | ✅ 多语言 |

### 推荐使用Parquet

除非有特殊需求（如需要序列化复杂的Python对象），否则**强烈推荐使用Parquet格式**。

## 运行时指标值详解

### 为什么需要运行时指标值？

在传统的指标计算方式中，只能在K线收盘后才能获取该周期的指标值。但在实际交易中，我们可能需要在更小周期的K线中引用更大周期指标的当前值。

**示例场景：**
- 在1分钟K线更新时，需要知道当前5分钟K线的指标值
- 如果等待5分钟K线收盘，会延迟4分钟才能获取到指标值
- 使用运行时指标值，可以在1分钟K线更新时立即获取5分钟指标的当前值

### 工作原理

1. **运行时值计算**：
   - 基于正在聚合的K线（`BarGenerator.window_bar`）计算
   - 每次1分钟K线更新时，都会重新计算5分钟指标的运行时值
   - 运行时值反映当前正在聚合的5分钟K线的指标状态

2. **历史值转换**：
   - 当5分钟K线收盘时，运行时值会被计算为历史值
   - 历史值保存到持久化存储中
   - 运行时值清空，等待下一个5分钟K线开始聚合

### 使用示例

```python
# 在1分钟K线更新时
def on_bar(self, bar: BarData):
    # 更新5分钟指标的运行时值
    if self.bg5.window_bar:
        manager.update_indicator(
            Interval.MINUTE_5,
            self.bg5.window_bar,
            is_runtime=True
        )
    
    # 获取运行时值
    runtime_value = manager.get_runtime_indicator(
        Interval.MINUTE_5,
        "indicator"
    )
    
    # 使用运行时值进行交易决策
    if runtime_value > threshold:
        # 交易逻辑...
        pass

# 在5分钟K线收盘时
def on_5min_bar(self, bar: BarData):
    # 更新历史值（运行时值自动清空）
    manager.update_indicator(
        Interval.MINUTE_5,
        bar,
        is_runtime=False
    )
```

## 总结

`IndicatorManager` 适用于以下场景：
- ✅ 需要计算长期历史数据的自定义指标
- ✅ 需要在多个周期同时计算指标
- ✅ 需要在tick和K线收盘时使用指标
- ✅ **需要在K线聚合过程中引用更大周期指标的运行时值**
- ✅ 需要持久化指标数据
- ✅ 需要跨语言分析指标数据（使用Parquet格式）

**核心优势：**
- **运行时指标值支持**：可以在1分钟K线中引用5分钟指标的运行时值，无需等待5分钟K线收盘
- **历史值与运行时值分离**：清晰区分已完成的K线指标值和正在聚合的K线指标值
- **灵活的数据访问**：支持获取历史值、运行时值或历史数组

对于简单的短期技术指标（如MA、RSI等），继续使用 `ArrayManager` 即可。

## 与AlphaLab集成

### 导出指标数据用于AlphaLab训练

`IndicatorManager` 可以将指标数据导出为AlphaLab可用的格式，用于机器学习模型训练。

#### 格式说明

**IndicatorManager保存的格式：**
```
datetime, indicator_name, value
```

**AlphaLab期望的格式：**
```
datetime, vt_symbol, {indicator_name1}, {indicator_name2}, ...
```

每个指标作为一列，列名为指标名称。

#### 导出方法

```python
# 导出单个周期的指标数据
df = manager.export_to_alphalab_format(
    interval=Interval.MINUTE,
    output_path="./lab/indicators/MINUTE_indicators.parquet"  # 可选
)

# 导出所有周期的指标数据
results = manager.export_all_indicators_to_alphalab_format(
    output_dir="./lab/indicators/"  # 可选
)
```

#### 在AlphaLab中使用

导出的指标数据可以通过 `AlphaDataset.add_feature()` 方法添加为特征：

```python
from vnpy.alpha import AlphaLab, AlphaDataset
import polars as pl

# 创建AlphaLab
lab = AlphaLab("./lab/mhimain")

# 加载K线数据
df = lab.load_bar_df(
    vt_symbols=["MHImain.HKFE"],
    interval=Interval.MINUTE,
    start="2023-01-01",
    end="2024-01-01",
    extended_days=0
)

# 加载指标数据（从IndicatorManager导出）
indicator_df = pl.read_parquet("./lab/indicators/MINUTE_indicators.parquet")

# 创建数据集
dataset = AlphaDataset(
    df=df,
    train_period=("2023-01-01", "2023-06-30"),
    valid_period=("2023-07-01", "2023-09-30"),
    test_period=("2023-10-01", "2023-12-31")
)

# 添加指标作为特征
# 方法1：直接添加指标列（如果指标数据已与K线数据对齐）
for indicator_name in ["custom_wma", "custom_rsi"]:
    if indicator_name in indicator_df.columns:
        # 重命名列以匹配AlphaDataset期望的格式
        feature_df = indicator_df.select(["datetime", "vt_symbol", indicator_name])
        feature_df = feature_df.rename({indicator_name: "data"})
        dataset.add_feature(indicator_name, result=feature_df)

# 方法2：使用表达式计算（如果指标需要进一步处理）
# dataset.add_feature("wma_normalized", "custom_wma / close")

# 准备数据
dataset.prepare_data()

# 现在可以使用dataset进行模型训练
```

#### 注意事项

1. **时间对齐**：确保指标数据的时间戳与K线数据对齐
2. **数据合并**：指标数据需要与K线数据通过 `datetime` 和 `vt_symbol` 进行join
3. **缺失值处理**：指标数据中的NaN值需要在训练前处理
4. **多周期指标**：不同周期的指标需要分别导出，然后在AlphaDataset中合并

#### 完整示例

```python
# 1. 在策略中计算并保存指标
manager = IndicatorManager(vt_symbol="MHImain.HKFE")
# ... 注册和计算指标 ...

# 2. 导出指标数据
manager.export_all_indicators_to_alphalab_format(
    output_dir="./lab/mhimain/indicators/"
)

# 3. 在AlphaLab中使用
lab = AlphaLab("./lab/mhimain")
df = lab.load_bar_df(...)

# 加载指标数据
indicator_1min = pl.read_parquet("./lab/mhimain/indicators/MINUTE_indicators.parquet")
indicator_5min = pl.read_parquet("./lab/mhimain/indicators/MINUTE_5_indicators.parquet")

# 创建数据集
dataset = AlphaDataset(df, ...)

# 添加指标特征
for col in indicator_1min.columns:
    if col not in ["datetime", "vt_symbol"]:
        feature_df = indicator_1min.select(["datetime", "vt_symbol", col])
        feature_df = feature_df.rename({col: "data"})
        dataset.add_feature(f"{col}_1min", result=feature_df)

# 准备数据并训练模型
dataset.prepare_data()
# ... 训练模型 ...
```

