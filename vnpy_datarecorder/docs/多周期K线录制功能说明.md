# DataRecorder多周期K线录制功能说明

## 概述

DataRecorder模块现已支持录制多个周期的K线数据，而不仅仅是1分钟K线。该功能复用了K线图表中开发的重要功能，包括：

1. **港期时间划分机制**：正确处理港期期货的特殊交易时段
2. **大周期开盘价自动更新**：大周期K线的开盘价自动取该周期第一根分钟K线的开盘价

## 功能特性

### 支持的周期

- **1分钟**（`Interval.MINUTE`）：基础周期，从Tick数据合成
- **5分钟**（`Interval.MINUTE_5`）：从1分钟K线合成
- **1小时**（`Interval.HOUR`）：从1分钟K线合成
- **4小时**（`Interval.HOUR_4`）：从1小时K线合成

### 港期时间划分机制

对于HKFE（港期）交易所，系统会自动应用特殊的时间划分机制：

#### 1小时K线时间划分

- **夜盘时段**：
  - 17:15-18:14
  - 18:15-19:14
  - 19:15-20:14
  - 20:15-21:14
  - 21:15-22:14
  - 22:15-23:14
  - 23:15-00:14
  - 00:15-01:14
  - 01:15-02:14
- **跨休市时段**：02:15-09:29（特殊处理周末）
- **日盘时段**：
  - 09:30-10:29
  - 10:30-11:29
  - 11:30-12:00 + 13:00-13:29（跨午休）
  - 13:30-14:29
  - 14:30-15:29
  - 15:30-16:29

#### 4小时K线时间划分

- **时段1**：17:15-21:14
- **时段2**：21:15-01:14（跨日）
- **时段3**：01:15-03:00 + 09:15-11:29（跨休市，特殊处理周末和金融假期）
- **时段4**：11:30-12:00 + 13:00-16:29（跨午休）

### 大周期开盘价取值逻辑

**核心原则**：大周期K线的开盘价 = 该周期第一根分钟K线的开盘价

例如：
- 1小时K线（14:30-15:29）的开盘价 = 14:30分钟K线的开盘价
- 5分钟K线（14:30-14:34）的开盘价 = 14:30分钟K线的开盘价
- 4小时K线（17:15-21:14）的开盘价 = 17:15分钟K线的开盘价

#### 开盘价获取优先级

1. **数据库查询**（最高优先级）：查询该周期第一根分钟K线的数据
2. **1分钟K线缓存**：缓存最近完成的1分钟K线，用于快速查找
3. **BarGenerator**：实时生成中的1分钟K线
4. **Fallback**：如果以上都失败，使用tick价格（临时），后续会自动更新

#### 自动更新机制

当第一根分钟K线完成时，系统会自动检查并更新大周期K线的开盘价：

1. 检查当前是否有大周期K线正在生成
2. 检查该分钟K线是否属于该大周期K线的第一根
3. 如果开盘价不一致，自动更新：
   - 更新K线对象的开盘价
   - 更新数据库中的记录
   - 记录更新日志

## 使用方法

### UI界面使用

1. 打开DataRecorder界面（【功能】-> 【行情记录】）
2. 在【本地代码】输入框中输入合约代码
3. 在【K线周期】区域选择要录制的周期（可多选）
4. 点击【添加】按钮添加录制任务

### 代码使用

```python
from vnpy_datarecorder import DataRecorderApp, RecorderEngine
from vnpy.trader.constant import Interval

# 添加多周期K线录制
recorder_engine: RecorderEngine = main_engine.get_engine("DataRecorder")

# 录制1分钟和5分钟K线
recorder_engine.add_bar_recording(
    "rb2401.SHFE",
    intervals=[Interval.MINUTE, Interval.MINUTE_5]
)

# 录制1分钟、5分钟、1小时、4小时K线
recorder_engine.add_bar_recording(
    "MHI2511.HKFE",
    intervals=[
        Interval.MINUTE,
        Interval.MINUTE_5,
        Interval.HOUR,
        Interval.HOUR_4
    ]
)
```

### 配置格式

录制配置保存在 `data_recorder_setting.json` 文件中：

```json
{
    "bar": {
        "rb2401.SHFE": {
            "symbol": "rb2401",
            "exchange": "SHFE",
            "gateway_name": "CTP",
            "intervals": ["1m", "5m", "1h"]
        },
        "MHI2511.HKFE": {
            "symbol": "MHI2511",
            "exchange": "HKFE",
            "gateway_name": "FUTU",
            "intervals": ["1m", "5m", "1h", "4h"]
        }
    },
    "tick": {},
    "filter_window": 60
}
```

## 技术实现

### 代码复用

为了遵循DRY（Don't Repeat Yourself）原则，相关功能被提取到通用工具模块中：

#### `vnpy/trader/period_utils.py`（通用工具模块）

- `get_period_start()`: 获取周期起始时间（支持港期特殊时间划分）
- `get_hkfe_hour_period_start()`: 获取港期1小时周期起始时间
- `get_hkfe_4hour_period()`: 获取港期4小时周期起始时间和索引
- `is_hkfe_trading_time()`: 判断是否在港期交易时段
- `PeriodOpenPriceHelper`: 大周期开盘价获取辅助类

该工具模块被以下模块复用：
- K线图表模块
- DataRecorder模块
- DataManager模块

#### 引擎扩展

`RecorderEngine` 类已扩展支持：

- 多周期BarGenerator管理
- 开盘价自动更新机制
- 1分钟K线缓存（用于开盘价获取）

### 数据流程

```
Tick数据
  ↓
1分钟BarGenerator（生成1分钟K线）
  ↓
缓存1分钟K线（用于开盘价获取）
  ↓
大周期BarGenerator（从1分钟K线合成）
  ↓
获取正确的开盘价（从第一根分钟K线）
  ↓
保存到数据库
```

### 性能优化

1. **缓存机制**：使用`_minute_bars_cache`缓存最近完成的1分钟K线，避免重复查询数据库
2. **批量写入**：使用定时批量写入机制，降低数据库压力
3. **防重复日志**：使用集合记录已输出的警告/错误，避免重复日志刷屏

## 注意事项

1. **1分钟K线是基础**：所有大周期K线都从1分钟K线合成，因此必须同时录制1分钟K线
2. **开盘价延迟更新**：大周期K线的开盘价可能在第一根分钟K线完成前使用tick价格（临时），后续会自动更新
3. **港期特殊处理**：港期期货的时间划分机制会自动应用，无需额外配置
4. **数据完整性**：确保数据库中有完整的1分钟K线数据，以便正确获取开盘价

## 测试

完整的测试代码位于 `tests/test_datarecorder_multi_interval.py`，包括：

- 周期工具函数测试
- 开盘价获取测试
- 多周期录制功能测试
- 港期时间划分测试

运行测试：

```bash
python -m pytest tests/test_datarecorder_multi_interval.py -v
```

## 更新日志

### v1.2.0（当前版本）

- ✅ 支持多周期K线录制（1分钟、5分钟、1小时、4小时）
- ✅ 实现港期时间划分机制
- ✅ 实现大周期开盘价自动更新
- ✅ 提取通用工具模块，避免代码重复
- ✅ 更新UI界面，支持周期选择
- ✅ 完整的测试覆盖

## 相关文档

- [K线图表大周期开盘价取值逻辑](../../docs/new-futu/K线图表大周期开盘价取值逻辑.md)
- [DataRecorder基础使用说明](../../docs/community/app/data_recorder.md)

