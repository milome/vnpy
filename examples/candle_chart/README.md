# 多周期K线叠加显示示例

## 概述

本示例演示如何在同一个图表上叠加显示1分钟K线和4小时K线，其中4小时K线使用跨索引绘制技术，可以跨越多个1分钟索引位置。

## 文件说明

### 1. `run_multi_timeframe.py`
主程序，演示多周期K线叠加显示。

### 2. `cross_index_candle_item.py`
扩展的CandleItem类，支持大周期K线的跨索引绘制。

**特点**：
- 支持跨多个索引位置绘制（大周期K线）
- 颜色：阳线红色空心，阴线青色填充（95%透明）
- 上下影线位于时间范围中点，不穿过实体

### 3. `four_hour_aggregator.py`
4小时K线聚合工具，从1分钟K线数据合成4小时K线。

**规则**（HKFE交易时段）：
- 第一根：17:15-21:14
- 第二根：21:15-01:14（跨午夜）
- 第三根：01:15-11:29（跨休市：01:15-03:00 + 09:15-11:29）
- 第四根：11:30-16:29（跨午休：11:30-12:00 + 13:00-16:29）

## 运行方法

```bash
cd D:\Dev\vnpy\examples\candle_chart
python run_multi_timeframe.py
```

## 功能说明

### 1. 跨索引绘制原理

- **1分钟K线**：每个K线占据一个索引位置（细线）
- **4小时K线**：每个K线跨越多个1分钟索引位置（粗线）

### 2. 视觉效果

- **细线**：1分钟K线，每个索引位置一根
- **粗线**：4小时K线，跨越多个索引位置
  - 阳线：红色，空心
  - 阴线：青色，填充（95%透明，几乎全透明）
- **影线**：位于时间范围中点，不穿过实体

### 3. 技术实现

1. **时间轴映射**：以1分钟K线作为X轴基准，建立 `datetime -> index` 映射
2. **索引范围计算**：计算4小时K线的起始和结束时间对应的1分钟索引
3. **跨索引绘制**：在起始索引位置绘制，宽度为 `end_index - start_index + 1`

## 代码结构

```
candle_chart/
├── run_multi_timeframe.py          # 主程序
├── cross_index_candle_item.py      # 跨索引绘制CandleItem
├── four_hour_aggregator.py         # 4小时K线聚合工具
└── README.md                        # 说明文档
```

## 使用示例

```python
from cross_index_candle_item import CrossIndexCandleItem
from four_hour_aggregator import aggregate_to_4hours
from vnpy.chart import ChartWidget, CandleItem
from vnpy.chart.manager import BarManager

# 1. 创建图表
widget = ChartWidget()
widget.add_plot("candle")
widget.add_item(CandleItem, "candle", "candle")

# 2. 加载1分钟K线数据
one_minute_bars = [...]  # 1分钟K线数据
widget.update_history(one_minute_bars)

# 3. 合成4小时K线
four_hour_bars = aggregate_to_4hours(one_minute_bars)

# 4. 创建4小时K线的BarManager
four_hour_manager = BarManager()
four_hour_manager.update_history(four_hour_bars)

# 5. 创建跨索引绘制项
four_hour_item = CrossIndexCandleItem(
    manager=four_hour_manager,
    base_manager=widget._manager  # 传入1分钟管理器用于索引映射
)

# 6. 添加到图表
candle_plot = widget.get_plot("candle")
candle_plot.addItem(four_hour_item)
```

## 注意事项

1. 确保数据库中有足够的1分钟K线数据
2. 4小时K线的聚合依赖于HKFE交易时段规则
3. 跨索引绘制需要正确的时间轴映射

## 扩展

可以基于 `CrossIndexCandleItem` 扩展支持其他周期（如5分钟、1小时等）的跨索引绘制。

