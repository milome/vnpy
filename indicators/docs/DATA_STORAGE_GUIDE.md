# IndicatorManager 数据存储指南

## 1. 数据存储位置

### 默认存储路径

**指标计算结果文件**：
```
~/.vntrader/indicators/{vt_symbol}/{interval}_indicators.{format}
```

**示例**：
- Windows: `C:\Users\{用户名}\.vntrader\indicators\MHImain_HKFE\MINUTE_indicators.parquet`
- Linux/Mac: `~/.vntrader/indicators/MHImain_HKFE/MINUTE_indicators.parquet`

**文件命名规则**：
- `{interval}`: K线周期，如 `MINUTE`, `MINUTE_5`, `HOUR`, `DAILY`
- `{format}`: 存储格式，`parquet` 或 `pkl`

### 自定义存储路径

```python
manager = IndicatorManager(
    vt_symbol="MHImain.HKFE",
    storage_path="/path/to/custom/storage",  # 自定义路径
    use_database=True
)
```

### 数据存储结构

#### 文件格式：Parquet（推荐）

**文件内容**：
```
datetime, indicator_name, value
2023-01-01 09:00:00, custom_wma, 25500.5
2023-01-01 09:01:00, custom_wma, 25501.2
...
```

**优势**：
- 压缩率高（zstd压缩）
- 跨语言兼容
- 支持时间戳查询

#### 文件格式：PKL（备选）

**文件内容**：
```python
{
    "custom_wma": [25500.5, 25501.2, ...],
    "custom_rsi": [65.3, 66.1, ...]
}
```

**优势**：
- 写入速度快
- Python原生支持

## 2. 2年多周期指标数据存储方案

### 数据量估算

#### 1分钟K线
- 2年 × 250交易日/年 × 240分钟/天 = **120,000根K线**
- 每个指标值：8字节（float64）
- 10个指标：120,000 × 10 × 8 = **9.6MB**

#### 5分钟K线
- 2年 × 250交易日/年 × 48分钟/天 = **24,000根K线**
- 10个指标：24,000 × 10 × 8 = **1.92MB**

#### 文件大小（Parquet压缩后）
- 1分钟：约 **2-3MB**（压缩率约70%）
- 5分钟：约 **0.5-1MB**

### 存储位置总结

| 数据类型 | 存储位置 | 格式 | 大小（2年） |
|---------|---------|------|------------|
| **指标计算结果** | `~/.vntrader/indicators/{vt_symbol}/` | Parquet/PKL | 2-10MB |
| **K线原始数据** | 数据库（SQLite/PostgreSQL等） | 数据库表 | 较大 |
| **运行时内存** | `deque`（内存） | Python对象 | 4-10MB |

## 3. 实盘运行时加载策略

### 启动时加载流程

```python
def on_init(self):
    """策略初始化"""
    # 1. 创建IndicatorManager
    self.indicator_manager = IndicatorManager(
        vt_symbol=self.vt_symbol,
        storage_path=None,  # 使用默认路径
        use_database=True,
        storage_format="parquet"  # 或 "pkl"
    )
    
    # 2. 注册指标（设置max_history=50000，支持2年数据）
    self.indicator_manager.register_indicator(
        interval=Interval.MINUTE,
        indicator_name="custom_wma",
        calculator=self._calculate_wma,
        max_history=50000  # 约2年1分钟K线
    )
    
    # 3. 初始化指标（自动加载）
    database = self.cta_engine.database
    self.indicator_manager.initialize_indicators(
        Interval.MINUTE,
        days=730,  # 加载2年数据
        database=database
    )
```

### 加载优先级

`initialize_indicators` 方法的加载顺序：

1. **优先从文件加载**（如果存在）
   ```python
   # 自动调用 _load_indicator_from_file
   # 从 ~/.vntrader/indicators/{vt_symbol}/MINUTE_indicators.parquet 加载
   ```

2. **如果文件不存在或数据不足，从数据库加载K线并计算**
   ```python
   # 从数据库加载2年K线数据
   bars = db.load_bar_data(..., days=730)
   # 重新计算所有指标
   indicator_values = calculator(bars)
   ```

3. **保存计算结果到文件**
   ```python
   # 自动保存到文件，下次启动时可直接加载
   self._save_indicator_to_file(interval)
   ```

### 完整加载示例

```python
class MyStrategy(CtaTemplate):
    def on_init(self):
        """策略初始化"""
        # 创建指标管理器
        self.indicator_manager = IndicatorManager(
            vt_symbol=self.vt_symbol,
            storage_path=None,  # 默认路径：~/.vntrader/indicators/MHImain_HKFE/
            use_database=True,
            storage_format="parquet"
        )
        
        # 注册多个周期的指标
        # 1分钟周期
        self.indicator_manager.register_indicator(
            interval=Interval.MINUTE,
            indicator_name="custom_wma",
            calculator=self._calculate_wma,
            max_history=50000  # 约2年数据
        )
        
        # 5分钟周期
        self.indicator_manager.register_indicator(
            interval=Interval.MINUTE_5,
            indicator_name="custom_wma",
            calculator=self._calculate_wma,
            max_history=10000  # 约2年数据
        )
        
        # 初始化指标（自动加载2年数据）
        database = self.cta_engine.database
        
        # 加载1分钟指标
        self.indicator_manager.initialize_indicators(
            Interval.MINUTE,
            days=730,  # 2年
            database=database
        )
        
        # 加载5分钟指标
        self.indicator_manager.initialize_indicators(
            Interval.MINUTE_5,
            days=730,  # 2年
            database=database
        )
        
        self.write_log("指标初始化完成")
    
    def on_bar(self, bar: BarData):
        """K线更新"""
        # 增量更新指标
        self.indicator_manager.update_indicator(
            Interval.MINUTE,
            bar,
            is_runtime=False
        )
        
        # 获取指标值
        wma_value = self.indicator_manager.get_indicator(
            Interval.MINUTE,
            "custom_wma",
            index=-1
        )
```

## 4. 数据文件位置查找

### Windows

```python
from pathlib import Path

# 默认路径
default_path = Path.home() / ".vntrader" / "indicators" / "MHImain_HKFE"
print(f"指标数据路径: {default_path}")

# 列出所有文件
for file in default_path.glob("*.parquet"):
    print(f"指标文件: {file}")
```

### Linux/Mac

```bash
# 查看指标数据目录
ls -lh ~/.vntrader/indicators/MHImain_HKFE/

# 查看文件大小
du -sh ~/.vntrader/indicators/MHImain_HKFE/*
```

## 5. 数据迁移和备份

### 备份指标数据

```python
import shutil
from pathlib import Path

# 备份指标数据
source = Path.home() / ".vntrader" / "indicators" / "MHImain_HKFE"
backup = Path("/backup/indicators") / "MHImain_HKFE"

if source.exists():
    shutil.copytree(source, backup, dirs_exist_ok=True)
    print(f"指标数据已备份到: {backup}")
```

### 迁移到新机器

1. **复制指标文件**：
   ```bash
   # 从旧机器复制
   scp -r ~/.vntrader/indicators/MHImain_HKFE/ user@newmachine:~/.vntrader/indicators/
   ```

2. **确保数据库有K线数据**：
   - 指标文件只存储计算结果
   - 如果文件损坏，需要从数据库重新计算

## 6. 性能优化建议

### 首次运行（无缓存文件）

**耗时**：
- 加载2年K线：约5-10秒（取决于数据库性能）
- 计算指标：约10-30秒（取决于指标复杂度）
- **总计**：约15-40秒

**优化**：
- 使用 `storage_format="pkl"`（写入更快）
- 分阶段加载（先加载最近1年，后台加载剩余数据）

### 后续运行（有缓存文件）

**耗时**：
- 加载指标文件：约1-3秒（Parquet）或 0.5-1秒（PKL）
- **总计**：约1-3秒

**优化**：
- 使用PKL格式（加载更快）
- 定期清理旧数据（只保留最近2年）

## 7. 数据完整性检查

### 检查指标数据完整性

```python
def check_indicator_data(manager: IndicatorManager, interval: Interval):
    """检查指标数据完整性"""
    for indicator_name in manager.indicators[interval].keys():
        deque = manager.indicators[interval][indicator_name]
        timestamps = manager.indicator_timestamps[interval].get(indicator_name, deque())
        
        print(f"指标: {indicator_name}")
        print(f"  数据量: {len(deque)}")
        print(f"  时间戳量: {len(timestamps)}")
        print(f"  最早时间: {timestamps[0] if timestamps else 'N/A'}")
        print(f"  最新时间: {timestamps[-1] if timestamps else 'N/A'}")
```

### 数据修复

如果指标文件损坏或不完整：

```python
# 删除旧文件，重新计算
import os
file_path = manager.storage_path / "MINUTE_indicators.parquet"
if file_path.exists():
    os.remove(file_path)

# 重新初始化（会从数据库重新计算）
manager.initialize_indicators(Interval.MINUTE, days=730, database=database)
```

## 8. 多周期数据存储结构

### 文件组织

```
~/.vntrader/indicators/
├── MHImain_HKFE/
│   ├── MINUTE_indicators.parquet      # 1分钟指标
│   ├── MINUTE_5_indicators.parquet    # 5分钟指标
│   ├── HOUR_indicators.parquet        # 1小时指标
│   └── DAILY_indicators.parquet       # 日线指标
└── OtherSymbol_Exchange/
    └── ...
```

### 内存占用

**2年多周期数据内存占用**：
- 1分钟：10个指标 × 50000值 × 8字节 = **4MB**
- 5分钟：10个指标 × 10000值 × 8字节 = **0.8MB**
- 1小时：10个指标 × 2000值 × 8字节 = **0.16MB**
- **总计**：约 **5MB**（非常小）

## 总结

1. **存储位置**：
   - 默认：`~/.vntrader/indicators/{vt_symbol}/`
   - 文件：`{interval}_indicators.parquet` 或 `.pkl`

2. **加载策略**：
   - 优先从文件加载（快速）
   - 文件不存在时从数据库计算（慢但完整）

3. **数据量**：
   - 2年1分钟数据：约2-3MB（压缩后）
   - 内存占用：约4-5MB（非常小）

4. **性能**：
   - 首次运行：15-40秒（需要计算）
   - 后续运行：1-3秒（从文件加载）

5. **推荐配置**：
   - 存储格式：Parquet（空间优先）或PKL（速度优先）
   - 保存频率：500-1000根K线
   - 数据保留：2年（通过 `max_history` 控制）

