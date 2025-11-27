# MHImain合约数据存储方案设计文档

## 一、需求概述

针对MHImain合约，需要支持以下数据类型用于实时跨周期分析：
- **Tick数据**：实时逐笔行情数据
- **K线数据**：1分钟、5分钟、1小时、4小时、日级别
- **数据量**：约两年历史数据
- **使用场景**：实时跨周期分析

## 二、Tick数据的记录与存储方式

### 2.1 记录方式

基于VeighNa的`DataRecorder`模块实现：

```python
# DataRecorder引擎工作流程
1. 订阅合约行情（通过SubscribeRequest）
2. 接收EVENT_TICK事件
3. 时间戳过滤（默认60秒窗口，过滤异常时间戳）
4. 批量缓存（按vt_symbol分组）
5. 定时批量写入（默认每10秒）
```

**关键实现点：**

```294:296:vnpy_datarecorder/vnpy_datarecorder/engine.py
    def record_tick(self, tick: TickData) -> None:
        """"""
        self.ticks[tick.vt_symbol].append(tick)
```

```229:231:vnpy_datarecorder/vnpy_datarecorder/engine.py
        for ticks in self.ticks.values():
            self.queue.put(("tick", ticks))
        self.ticks.clear()
```

### 2.2 存储方式建议

**方案A：直接存储原始Tick（推荐用于高频分析）**
- **优点**：保留完整信息，支持精确回放
- **缺点**：存储空间大（两年约10-50GB，取决于交易活跃度）
- **适用场景**：需要精确成交价、买卖盘深度等细节

**方案B：压缩存储（推荐用于一般分析）**
- **优点**：节省存储空间（可压缩至1/5-1/10）
- **缺点**：需要解压，查询稍慢
- **适用场景**：主要用于K线合成，不需要精确回放

**存储字段结构：**
```python
TickData核心字段：
- symbol, exchange, datetime
- last_price, volume, turnover
- bid_price_1, ask_price_1
- bid_volume_1, ask_volume_1
- open_interest
```

**注意：MHImain合约的交易所代码是 `Exchange.HKFE`（香港期货交易所），不是 `Exchange.SEHK`（香港证券交易所，用于股票）。**

### 2.3 数据过滤策略

```202:207:vnpy_datarecorder/vnpy_datarecorder/engine.py
    def update_tick(self, tick: TickData) -> None:
        """"""
        # 过滤偏离本地时间戳过大的Tick数据
        tick_delta: timedelta = abs(tick.datetime - self.filter_dt)
        if abs(tick_delta) >= self.filter_delta:
            return
```

**建议配置：**
- `filter_window`: 60秒（默认值，可根据实际情况调整）
- 过滤价格为0的异常Tick
- 过滤时间戳异常的数据

## 三、历史数据的存储方式

### 3.1 数据来源

1. **DataRecorder实时录制**
   - 优点：数据实时、完整
   - 缺点：需要长期运行，占用资源

2. **DataManager批量下载**
   - 优点：一次性获取历史数据
   - 缺点：依赖数据源，可能有缺失

3. **外部数据导入**
   - 支持CSV、Excel等格式导入
   - 需要转换为BarData/TickData格式

### 3.2 存储结构设计

**按周期分层存储：**

```
数据库表结构（以MySQL为例）：
├── dbbardata (K线数据表)
│   ├── symbol (合约代码: MHImain)
│   ├── exchange (交易所: HKFE - 香港期货交易所)
│   ├── interval (周期: 1m, 5m, 1h, 4h, d)
│   ├── datetime (时间戳)
│   ├── open, high, low, close (价格)
│   ├── volume, turnover (成交量/成交额)
│   └── open_interest (持仓量)
│
└── dbtickdata (Tick数据表)
    ├── symbol (MHImain)
    ├── exchange (HKFE)
    ├── datetime
    └── ... (Tick字段)
```

**重要提示：**
- MHImain合约使用 `Exchange.HKFE`（香港期货交易所）
- 不要与 `Exchange.SEHK`（香港证券交易所，用于股票）混淆
- vt_symbol格式：`MHImain.HKFE`

**索引策略：**
- 主键：(symbol, exchange, interval, datetime)
- 索引：datetime（时间范围查询）
- 索引：symbol + exchange（合约查询）

### 3.3 数据分区策略（针对大数据量）

**时间分区：**
- 按月或按季度分区
- 提高查询性能，便于数据维护

**示例（MySQL分区）：**
```sql
CREATE TABLE dbbardata (
    ...
) PARTITION BY RANGE (YEAR(datetime) * 100 + MONTH(datetime)) (
    PARTITION p202301 VALUES LESS THAN (202302),
    PARTITION p202302 VALUES LESS THAN (202303),
    ...
);
```

## 四、跨周期K线数据的聚合和存储方式

### 4.1 聚合方式

VeighNa提供`BarGenerator`类实现K线聚合：

```165:173:vnpy/trader/utility.py
class BarGenerator:
    """
    For:
    1. generating 1 minute bar data from tick data
    2. generating x minute bar/x hour bar data from 1 minute data
    Notice:
    1. for x minute bar, x must be able to divide 60: 2, 3, 5, 6, 10, 15, 20, 30
    2. for x hour bar, x can be any number
    """
```

**聚合层级：**
```
Tick数据
  ↓ (BarGenerator.update_tick)
1分钟K线
  ↓ (BarGenerator.update_bar, window=5)
5分钟K线
  ↓ (BarGenerator.update_bar, interval=HOUR, window=1)
1小时K线
  ↓ (BarGenerator.update_bar, interval=HOUR, window=4)
4小时K线
  ↓ (BarGenerator.update_bar, interval=DAILY)
日K线
```

### 4.2 存储策略

**方案A：实时聚合存储（推荐）**
- **实现**：在DataRecorder中为每个周期创建独立的BarGenerator
- **优点**：实时生成，数据一致性好
- **缺点**：需要修改DataRecorder代码

**方案B：按需聚合存储**
- **实现**：只存储1分钟K线，其他周期按需从1分钟聚合
- **优点**：节省存储空间
- **缺点**：查询时需要实时计算，性能较差

**方案C：预聚合存储（推荐用于生产环境）**
- **实现**：存储所有周期，定期从1分钟聚合生成
- **优点**：查询性能最优
- **缺点**：存储空间较大

### 4.3 实现建议

**修改DataRecorder支持多周期：**

```python
# 在RecorderEngine中添加多周期BarGenerator
self.bar_generators: dict[str, dict[Interval, BarGenerator]] = {}

def get_bar_generator(self, vt_symbol: str, interval: Interval) -> BarGenerator:
    """获取指定周期的BarGenerator"""
    if vt_symbol not in self.bar_generators:
        self.bar_generators[vt_symbol] = {}
    
    if interval not in self.bar_generators[vt_symbol]:
        bg = BarGenerator(
            on_bar=lambda bar: self.record_bar(bar, interval),
            interval=interval,
            window=self.get_window_for_interval(interval)
        )
        self.bar_generators[vt_symbol][interval] = bg
    
    return self.bar_generators[vt_symbol][interval]

def get_window_for_interval(self, interval: Interval) -> int:
    """根据周期返回window参数"""
    mapping = {
        Interval.MINUTE_5: 5,
        Interval.HOUR: 1,
        # 4小时需要特殊处理
    }
    return mapping.get(interval, 0)
```

## 五、实时数据的引用以及前序的时序数据引用

### 5.1 实时数据引用

**策略中的数据引用流程：**

```python
# 1. 策略初始化时加载历史数据
def on_init(self):
    # 从数据库加载历史K线（注意：使用Exchange.HKFE）
    bars = database.load_bar_data(
        symbol="MHImain",
        exchange=Exchange.HKFE,  # 香港期货交易所
        interval=Interval.MINUTE,
        start=datetime.now() - timedelta(days=30),  # 加载最近30天
        end=datetime.now()
    )
    
    # 初始化ArrayManager
    self.am = ArrayManager()
    for bar in bars:
        self.am.update_bar(bar)

# 2. 实时数据更新
def on_tick(self, tick: TickData):
    # 通过BarGenerator合成1分钟K线
    self.bg.update_tick(tick)

def on_bar(self, bar: BarData):
    # 更新ArrayManager
    self.am.update_bar(bar)
    
    # 跨周期分析
    self.analyze_multi_timeframe()
```

### 5.2 前序时序数据引用

**ArrayManager提供时序数据访问：**

```python
class ArrayManager:
    """K线时间序列管理"""
    
    # 访问历史数据
    self.am.close_array[-1]      # 最新收盘价
    self.am.close_array[-10]     # 10根K线前的收盘价
    self.am.high_array[-20:-1]   # 最近20根K线最高价（不含最新）
    
    # 技术指标
    self.am.sma(20)              # 20周期均线
    self.am.atr(14)               # 14周期ATR
```

**跨周期数据访问：**

```python
# 方案A：多ArrayManager（推荐）
self.am_1m = ArrayManager()   # 1分钟
self.am_5m = ArrayManager()   # 5分钟
self.am_1h = ArrayManager()   # 1小时
self.am_4h = ArrayManager()   # 4小时
self.am_d = ArrayManager()    # 日线

# 方案B：按需查询数据库
def get_higher_timeframe_data(self, interval: Interval, lookback: int):
    """获取更高周期数据"""
    end = datetime.now()
    start = end - timedelta(days=lookback)
    return database.load_bar_data(
        symbol="MHImain",
        exchange=Exchange.HKFE,  # 使用HKFE
        interval=interval,
        start=start,
        end=end
    )
```

### 5.3 数据缓存策略

**内存缓存：**
- 最近N天的数据常驻内存（如30天）
- 使用LRU缓存淘汰策略

**数据库查询优化：**
- 批量加载，避免频繁查询
- 使用索引加速时间范围查询
- 考虑使用时序数据库（TDengine、DolphinDB）提升性能

## 六、数据库以及数据格式的选用

### 6.1 数据库选择对比

| 数据库 | 类型 | 优点 | 缺点 | 适用场景 |
|--------|------|------|------|----------|
| **SQLite** | SQL | 轻量、无需配置、默认选项 | 单文件、并发性能差 | 小数据量、开发测试 |
| **MySQL** | SQL | 成熟稳定、文档丰富、兼容性好 | 时序查询性能一般 | 中等数据量、通用场景 |
| **PostgreSQL** | SQL | 功能强大、扩展性好 | 配置复杂 | 大数据量、复杂查询 |
| **TDengine** | 时序 | 专为时序优化、压缩率高、查询快 | 需要单独部署 | **推荐：大数据量时序数据** |
| **DolphinDB** | 时序 | 性能极佳、支持流计算 | 商业许可、配置复杂 | 高频交易、实时分析 |
| **MongoDB** | NoSQL | 灵活、支持复杂结构 | 时序查询性能一般 | 非结构化数据 |

### 6.2 针对MHImain的推荐方案

**方案一：TDengine（强烈推荐）**

**理由：**
1. **专为时序数据设计**：自动按时间分区，查询性能优异
2. **高压缩比**：两年数据压缩后约5-10GB（Tick+多周期K线）
3. **内置缓存**：热数据自动缓存，查询速度快
4. **流式计算**：支持实时聚合，可自动生成多周期K线
5. **SQL兼容**：学习成本低，易于维护

**配置示例：**
```python
# settings.json
{
    "database.name": "taos",
    "database.host": "localhost",
    "database.port": 6030,
    "database.database": "vnpy_mhimain",
    "database.user": "root",
    "database.password": "taosdata"
}
```

**存储结构：**
```sql
-- TDengine自动按时间分区
CREATE STABLE dbbardata (
    datetime TIMESTAMP,
    open FLOAT,
    high FLOAT,
    low FLOAT,
    close FLOAT,
    volume BIGINT,
    turnover FLOAT,
    open_interest BIGINT
) TAGS (
    symbol BINARY(64),
    exchange BINARY(32),
    interval BINARY(16)
);

-- 自动创建子表（注意：exchange使用HKFE）
CREATE TABLE MHImain_1m USING dbbardata TAGS ('MHImain', 'HKFE', '1m');
CREATE TABLE MHImain_5m USING dbbardata TAGS ('MHImain', 'HKFE', '5m');
CREATE TABLE MHImain_1h USING dbbardata TAGS ('MHImain', 'HKFE', '1h');
CREATE TABLE MHImain_4h USING dbbardata TAGS ('MHImain', 'HKFE', '4h');
CREATE TABLE MHImain_d USING dbbardata TAGS ('MHImain', 'HKFE', 'd');
```

**方案二：MySQL + 分区（备选方案）**

**适用场景：**
- 已有MySQL基础设施
- 数据量中等（<100GB）
- 需要与其他系统集成

**优化建议：**
- 使用InnoDB引擎
- 按时间分区（按月）
- 合理设置索引
- 考虑读写分离

**方案三：混合存储**

```
Tick数据 → TDengine（高频写入、快速查询）
K线数据 → MySQL（结构化查询、与其他系统集成）
```

### 6.3 数据格式

**VeighNa标准格式：**

```python
# BarData
BarData(
    symbol="MHImain",
    exchange=Exchange.SEHK,
    interval=Interval.MINUTE,
    datetime=datetime(2024, 1, 1, 9, 30),
    open_price=100.0,
    high_price=101.0,
    low_price=99.0,
    close_price=100.5,
    volume=10000,
    turnover=1005000.0,
    open_interest=50000
)

# TickData
TickData(
    symbol="MHImain",
    exchange=Exchange.SEHK,
    datetime=datetime(2024, 1, 1, 9, 30, 15, 123456),
    last_price=100.5,
    volume=10000,
    turnover=1005000.0,
    bid_price_1=100.4,
    ask_price_1=100.6,
    bid_volume_1=100,
    ask_volume_1=200,
    open_interest=50000
)
```

**存储优化：**
- 时间戳统一使用UTC时间，避免时区问题
- 价格使用FLOAT（或DECIMAL，根据精度需求）
- 成交量使用BIGINT
- 字符串字段使用固定长度（如symbol BINARY(64)）

## 七、实施建议

### 7.1 数据准备阶段

1. **选择数据库**：推荐TDengine
2. **配置数据库**：安装、配置、创建数据库
3. **历史数据导入**：
   - 使用DataManager下载历史数据
   - 或从外部数据源导入
   - 转换为VeighNa标准格式

### 7.2 实时录制阶段

1. **启动DataRecorder**：
   ```python
   from vnpy_datarecorder import DataRecorderApp
   main_engine.add_app(DataRecorderApp)
   ```

2. **添加录制任务**：
   ```python
   recorder_engine.add_tick_recording("MHImain.HKFE")
   recorder_engine.add_bar_recording("MHImain.HKFE")
   ```

3. **扩展多周期支持**（如需要）：
   - 修改DataRecorder支持多周期K线录制
   - 或使用定时任务从1分钟K线聚合生成

### 7.3 策略使用阶段

1. **数据加载**：
   ```python
   # 策略初始化时加载历史数据（注意：使用Exchange.HKFE）
   bars = database.load_bar_data(
       symbol="MHImain",
       exchange=Exchange.HKFE,  # 香港期货交易所
       interval=Interval.MINUTE,
       start=start_date,
       end=end_date
   )
   ```

2. **实时更新**：
   ```python
   # 通过BarGenerator合成K线
   self.bg.update_tick(tick)
   
   # 跨周期分析
   # 使用ArrayManager管理时序数据
   self.am.update_bar(bar)
   ```

### 7.4 性能优化建议

1. **数据分区**：按时间分区，提高查询性能
2. **索引优化**：合理设置索引，避免全表扫描
3. **缓存策略**：热数据常驻内存，冷数据按需加载
4. **批量操作**：批量写入、批量查询，减少IO次数
5. **压缩存储**：使用数据库压缩功能，节省存储空间

## 八、重要修正说明

### 8.1 交易所代码确认

**MHImain合约的正确交易所代码：**

- ✅ **正确**：`Exchange.HKFE`（香港期货交易所 - Hong Kong Futures Exchange）
- ❌ **错误**：`Exchange.SEHK`（香港证券交易所 - Stock Exchange of Hong Kong，用于股票）

**vt_symbol格式：**
- ✅ `MHImain.HKFE`
- ❌ `MHImain.SEHK`（错误，这是股票交易所）

**代码示例：**
```python
from vnpy.trader.constant import Exchange

# 正确用法
exchange = Exchange.HKFE
vt_symbol = "MHImain.HKFE"

# 错误用法（不要使用）
exchange = Exchange.SEHK  # 这是股票交易所
```

### 8.2 文档中的修正

本文档中所有涉及MHImain合约的地方已修正为使用`Exchange.HKFE`。

## 九、数据量估算

### 9.1 Tick数据量

**假设条件：**
- 交易时间：每天6小时（360分钟 = 21600秒）
- Tick频率：平均每秒10笔（活跃时段可能更高）
- 单条Tick：约200字节

**两年数据量：**
```
21600秒/天 × 10笔/秒 × 200字节 × 240交易日/年 × 2年
= 20,736,000,000 字节
≈ 20 GB（未压缩）
≈ 2-4 GB（压缩后）
```

### 9.2 K线数据量

**各周期数据量：**

| 周期 | 两年K线数量 | 单条大小 | 总大小 |
|------|------------|---------|--------|
| 1分钟 | 288,000 | 100字节 | 28.8 MB |
| 5分钟 | 57,600 | 100字节 | 5.76 MB |
| 1小时 | 4,800 | 100字节 | 480 KB |
| 4小时 | 1,200 | 100字节 | 120 KB |
| 日线 | 480 | 100字节 | 48 KB |

**总计：** 约35 MB（未压缩），压缩后约10-15 MB

### 9.3 总存储需求

- **Tick数据（压缩）**：2-4 GB
- **K线数据（压缩）**：10-15 MB
- **索引和元数据**：约500 MB
- **总计**：约3-5 GB

**建议存储空间**：预留10-20 GB（考虑数据增长和冗余）

## 九、Parquet数据格式说明

### 9.1 什么是Parquet格式

**Parquet**是一种列式存储格式，专为大数据分析设计，具有以下特点：

1. **列式存储**：按列存储数据，而非按行
   - 优点：查询特定列时只需读取该列数据，IO效率高
   - 适合：分析型查询（如计算技术指标）

2. **高效压缩**：
   - 相同类型数据压缩率高（通常可压缩至1/5-1/10）
   - 支持多种压缩算法（Snappy、Gzip、LZ4等）

3. **跨平台兼容**：
   - 支持Python、Java、C++等多种语言
   - 与Hadoop生态系统兼容

4. **Schema支持**：
   - 内置数据类型定义
   - 支持嵌套数据结构

### 9.2 VeighNa中的Parquet使用

VeighNa的`AlphaLab`模块使用**Polars**库处理Parquet文件：

```51:94:vnpy/alpha/lab.py
    def save_bar_data(self, bars: list[BarData]) -> None:
        """Save bar data"""
        if not bars:
            return

        # Get file path
        bar: BarData = bars[0]

        if bar.interval == Interval.DAILY:
            file_path: Path = self.daily_path.joinpath(f"{bar.vt_symbol}.parquet")
        elif bar.interval == Interval.MINUTE:
            file_path = self.minute_path.joinpath(f"{bar.vt_symbol}.parquet")
        elif bar.interval:
            logger.error(f"Unsupported interval {bar.interval.value}")
            return

        data: list = []
        for bar in bars:
            bar_data: dict = {
                "datetime": bar.datetime.replace(tzinfo=None),
                "open": bar.open_price,
                "high": bar.high_price,
                "low": bar.low_price,
                "close": bar.close_price,
                "volume": bar.volume,
                "turnover": bar.turnover,
                "open_interest": bar.open_interest
            }
            data.append(bar_data)

        new_df: pl.DataFrame = pl.DataFrame(data)

        # If file exists, read and merge
        if file_path.exists():
            old_df: pl.DataFrame = pl.read_parquet(file_path)

            new_df = pl.concat([old_df, new_df])

            new_df = new_df.unique(subset=["datetime"])

            new_df = new_df.sort("datetime")

        # Save to file
        new_df.write_parquet(file_path)
```

### 9.3 Parquet文件结构

**文件命名规则：**
- 格式：`{vt_symbol}.parquet`
- 示例：`MHImain.HKFE.parquet`

**存储目录：**
```
lab/mhimain/
├── daily/              # 日线数据
│   └── MHImain.HKFE.parquet
├── minute/            # 分钟线数据
│   └── MHImain.HKFE.parquet
└── ...
```

**数据列结构：**
```python
{
    "datetime": datetime,      # 时间戳（无时区）
    "open": float,             # 开盘价
    "high": float,             # 最高价
    "low": float,              # 最低价
    "close": float,            # 收盘价
    "volume": int,             # 成交量
    "turnover": float,         # 成交额
    "open_interest": int       # 持仓量
}
```

### 9.4 如何使用Parquet格式

#### 9.4.1 保存数据到Parquet

```python
from vnpy.alpha import AlphaLab
from vnpy.trader.object import BarData
from vnpy.trader.constant import Interval, Exchange

# 创建AlphaLab实例
lab = AlphaLab("./lab/mhimain")

# 准备BarData列表
bars: list[BarData] = [
    BarData(
        symbol="MHImain",
        exchange=Exchange.HKFE,
        interval=Interval.DAILY,
        datetime=datetime(2024, 1, 1),
        open_price=100.0,
        high_price=101.0,
        low_price=99.0,
        close_price=100.5,
        volume=10000,
        turnover=1005000.0,
        open_interest=50000
    ),
    # ... 更多BarData
]

# 保存数据（自动转换为Parquet格式）
lab.save_bar_data(bars)
# 文件保存为: ./lab/mhimain/daily/MHImain.HKFE.parquet
```

#### 9.4.2 从Parquet加载数据

```python
from vnpy.alpha import AlphaLab
from vnpy.trader.constant import Interval
from datetime import datetime

# 创建AlphaLab实例
lab = AlphaLab("./lab/mhimain")

# 加载数据（自动从Parquet文件读取）
bars = lab.load_bar_data(
    vt_symbol="MHImain.HKFE",
    interval=Interval.DAILY,
    start=datetime(2023, 1, 1),
    end=datetime(2024, 12, 31)
)

# bars是BarData对象列表，可直接用于策略
```

#### 9.4.3 直接使用Polars操作Parquet

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

### 9.5 Parquet vs 数据库存储对比

| 特性 | Parquet文件 | 数据库（MySQL/TDengine） |
|------|------------|------------------------|
| **存储方式** | 文件系统 | 数据库服务 |
| **查询性能** | 批量读取快 | 单条查询快 |
| **压缩率** | 高（5-10倍） | 中等（2-3倍） |
| **并发访问** | 文件锁限制 | 支持多用户 |
| **实时写入** | 需要合并文件 | 支持流式写入 |
| **适用场景** | 历史数据归档、回测 | 实时数据、在线查询 |

### 9.6 推荐使用场景

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

### 9.7 数据转换示例

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
    exchange=Exchange.HKFE,
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
    vt_symbol="MHImain.HKFE",
    interval=Interval.DAILY,
    start=datetime(2023, 1, 1),
    end=datetime(2024, 12, 31)
)

# 保存到数据库
database = get_database()
database.save_bar_data(bars)
```

## 十、总结

### 10.1 推荐方案

**数据库**：TDengine（时序数据库，专为金融数据优化）

**存储策略**：
- Tick数据：实时录制，压缩存储
- K线数据：多周期预聚合存储（1m, 5m, 1h, 4h, d）
- 历史数据：批量导入，按时间分区

**数据引用**：
- 实时数据：通过BarGenerator合成
- 历史数据：通过ArrayManager管理时序
- 跨周期：多ArrayManager或按需查询

### 10.2 关键要点

1. **数据一致性**：确保时间戳准确，使用统一时区
2. **性能优化**：合理分区、索引，使用缓存
3. **存储优化**：压缩存储，定期清理过期数据
4. **可扩展性**：设计时考虑未来数据增长和查询需求

### 10.3 后续优化方向

1. **实时聚合**：使用流式计算自动生成多周期K线
2. **数据压缩**：进一步优化压缩算法
3. **分布式存储**：数据量进一步增长时考虑分布式方案
4. **数据备份**：定期备份，确保数据安全

