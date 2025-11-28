# MHImain数据存储要点说明

## 一、交易所代码确认

### ✅ 正确：Exchange.HKFE

**MHImain合约使用 `Exchange.HKFE`（香港期货交易所）**

```python
from vnpy.trader.constant import Exchange

# 正确用法
vt_symbol = "MHImain.HKFE"
exchange = Exchange.HKFE

# 在数据库查询中使用
bars = database.load_bar_data(
    symbol="MHImain",
    exchange=Exchange.HKFE,  # ✅ 正确
    interval=Interval.DAILY,
    start=start_date,
    end=end_date
)
```

### ❌ 错误：Exchange.SEHK

**`Exchange.SEHK`是香港证券交易所，用于股票，不适用于期货合约**

```python
# ❌ 错误用法（不要使用）
exchange = Exchange.SEHK  # 这是股票交易所
vt_symbol = "MHImain.SEHK"  # 错误
```

### 区别说明

| 交易所代码 | 全称 | 用途 | 适用合约 |
|-----------|------|------|---------|
| **HKFE** | Hong Kong Futures Exchange | 期货交易所 | MHImain（小恒指期货）、HSImain（大恒指期货）等期货合约 |
| **SEHK** | Stock Exchange of Hong Kong | 证券交易所 | 股票（如腾讯00700、阿里09988等） |

## 二、Parquet数据格式详解

### 2.1 什么是Parquet

**Parquet**是一种列式存储格式，专为大数据分析优化：

- **列式存储**：按列而非按行存储，查询特定列时只需读取该列
- **高压缩率**：通常可压缩至原始大小的1/5-1/10
- **跨平台**：支持Python、Java、C++等多种语言
- **高效查询**：适合分析型查询（如计算技术指标）

### 2.2 VeighNa中的使用

VeighNa的`AlphaLab`模块使用**Polars**库处理Parquet文件：

```python
from vnpy.alpha import AlphaLab
from vnpy.trader.object import BarData
from vnpy.trader.constant import Interval, Exchange
from datetime import datetime

# 创建AlphaLab实例
lab = AlphaLab("./lab/mhimain")

# 保存数据（自动转换为Parquet）
bars: list[BarData] = [...]  # 你的BarData列表
lab.save_bar_data(bars)
# 文件保存为: ./lab/mhimain/daily/MHImain.HKFE.parquet

# 加载数据（自动从Parquet读取）
bars = lab.load_bar_data(
    vt_symbol="MHImain.HKFE",
    interval=Interval.DAILY,
    start=datetime(2023, 1, 1),
    end=datetime(2024, 12, 31)
)
```

### 2.3 文件结构

**目录结构：**
```
lab/mhimain/
├── daily/                    # 日线数据目录
│   └── MHImain.HKFE.parquet
├── minute/                   # 分钟线数据目录
│   └── MHImain.HKFE.parquet
├── contract.json             # 合约配置
└── ...
```

**数据列结构：**
```python
{
    "datetime": datetime,      # 时间戳
    "open": float,             # 开盘价
    "high": float,             # 最高价
    "low": float,              # 最低价
    "close": float,            # 收盘价
    "volume": int,             # 成交量
    "turnover": float,         # 成交额
    "open_interest": int       # 持仓量
}
```

### 2.4 直接使用Polars操作

```python
import polars as pl
from pathlib import Path

# 读取Parquet文件
file_path = Path("./lab/mhimain/daily/MHImain.HKFE.parquet")
df = pl.read_parquet(file_path)

# 查看数据
print(df.head())
print(df.describe())

# 数据筛选
df_filtered = df.filter(
    (pl.col("datetime") >= datetime(2024, 1, 1)) &
    (pl.col("close") > 100.0)
)

# 计算技术指标
df_with_ma = df.with_columns([
    pl.col("close").rolling_mean(20).alias("ma20"),
    pl.col("close").rolling_mean(60).alias("ma60")
])

# 保存回Parquet
df_with_ma.write_parquet(file_path)
```

### 2.5 Parquet vs 数据库

| 特性 | Parquet文件 | 数据库（MySQL/TDengine） |
|------|------------|------------------------|
| **存储方式** | 文件系统 | 数据库服务 |
| **查询性能** | 批量读取快 | 单条查询快 |
| **压缩率** | 高（5-10倍） | 中等（2-3倍） |
| **并发访问** | 文件锁限制 | 支持多用户 |
| **实时写入** | 需要合并文件 | 支持流式写入 |
| **适用场景** | 历史数据归档、回测 | 实时数据、在线查询 |

### 2.6 推荐使用场景

**使用Parquet：**
- ✅ AlphaLab回测系统（历史数据存储）
- ✅ 数据分析和研究
- ✅ 数据备份和归档
- ✅ 批量数据处理

**使用数据库：**
- ✅ DataRecorder实时录制
- ✅ 策略实盘运行（需要实时查询）
- ✅ 多用户并发访问
- ✅ 跨周期实时分析

### 2.7 数据转换示例

**从数据库导出到Parquet：**
```python
from vnpy.trader.database import get_database
from vnpy.alpha import AlphaLab
from vnpy.trader.constant import Exchange, Interval
from datetime import datetime

# 从数据库加载
database = get_database()
bars = database.load_bar_data(
    symbol="MHImain",
    exchange=Exchange.HKFE,  # ✅ 使用HKFE
    interval=Interval.DAILY,
    start=datetime(2023, 1, 1),
    end=datetime(2024, 12, 31)
)

# 保存到Parquet
lab = AlphaLab("./lab/mhimain")
lab.save_bar_data(bars)
```

**从Parquet导入到数据库：**
```python
from vnpy.alpha import AlphaLab
from vnpy.trader.database import get_database
from vnpy.trader.constant import Interval
from datetime import datetime

# 从Parquet加载
lab = AlphaLab("./lab/mhimain")
bars = lab.load_bar_data(
    vt_symbol="MHImain.HKFE",  # ✅ 使用HKFE
    interval=Interval.DAILY,
    start=datetime(2023, 1, 1),
    end=datetime(2024, 12, 31)
)

# 保存到数据库
database = get_database()
database.save_bar_data(bars)
```

## 三、快速参考

### 3.1 关键代码片段

```python
# ✅ 正确的MHImain合约配置
from vnpy.trader.constant import Exchange, Interval
from vnpy.alpha import AlphaLab
from vnpy.trader.database import get_database

# 1. 数据库查询
database = get_database()
bars = database.load_bar_data(
    symbol="MHImain",
    exchange=Exchange.HKFE,  # ✅ HKFE
    interval=Interval.DAILY,
    start=start_date,
    end=end_date
)

# 2. Parquet文件操作
lab = AlphaLab("./lab/mhimain")
lab.save_bar_data(bars)  # 保存为Parquet
bars = lab.load_bar_data(
    vt_symbol="MHImain.HKFE",  # ✅ HKFE
    interval=Interval.DAILY,
    start=start_date,
    end=end_date
)

# 3. DataRecorder录制
recorder_engine.add_tick_recording("MHImain.HKFE")  # ✅ HKFE
recorder_engine.add_bar_recording("MHImain.HKFE")  # ✅ HKFE
```

### 3.2 常见错误

❌ **错误1：使用SEHK**
```python
# ❌ 错误
exchange = Exchange.SEHK  # 这是股票交易所
vt_symbol = "MHImain.SEHK"
```

✅ **正确**
```python
# ✅ 正确
exchange = Exchange.HKFE  # 期货交易所
vt_symbol = "MHImain.HKFE"
```

## 四、总结

1. **交易所代码**：MHImain使用 `Exchange.HKFE`，不是 `Exchange.SEHK`
2. **Parquet格式**：列式存储，适合历史数据归档和回测分析
3. **使用场景**：
   - Parquet：回测、数据分析、数据归档
   - 数据库：实时录制、实盘运行、在线查询

