# Data Model: 修复 ChartWindow 实时 Tick 数据刷新

**Date**: 2025-01-27  
**Feature**: [spec.md](spec.md) | [plan.md](plan.md)

## Entities

### TickData
实时行情数据实体，来自VeighNa框架。

**Fields**:
- `vt_symbol: str` - 合约唯一标识符（格式：symbol.exchange）
- `symbol: str` - 合约代码
- `exchange: Exchange` - 交易所枚举
- `datetime: datetime` - 行情时间
- `last_price: float` - 最新价
- `volume: float` - 累计成交量
- `turnover: float` - 累计成交额
- `open_interest: float` - 持仓量
- `gateway_name: str` - 数据来源网关名称

**Relationships**:
- 由 Gateway 通过 EventEngine 推送
- 被 ChartWindow 接收并处理
- 用于更新 BarData（K线数据）

### BarData
K线数据实体，来自VeighNa框架。

**Fields**:
- `vt_symbol: str` - 合约唯一标识符
- `symbol: str` - 合约代码
- `exchange: Exchange` - 交易所枚举
- `datetime: datetime` - K线时间（周期开始时间）
- `interval: Interval` - K线周期（1分钟、5分钟、1小时等）
- `open_price: float` - 开盘价
- `high_price: float` - 最高价
- `low_price: float` - 最低价
- `close_price: float` - 收盘价
- `volume: float` - 成交量
- `turnover: float` - 成交额
- `open_interest: float` - 持仓量
- `gateway_name: str` - 数据来源

**State Transitions**:
- **未完成K线**：正在聚合中，每次tick更新都会更新 high_price, low_price, close_price, volume
- **已完成K线**：周期结束，不再更新，添加到历史数据

**Relationships**:
- 由 TickData 通过 BarGenerator 合成（1分钟周期）
- 由 TickData 直接更新（大周期）
- 存储在 ChartWindow.history_data 中
- 显示在 ChartWidget 中

### Event
事件对象，来自VeighNa EventEngine。

**Fields**:
- `type: str` - 事件类型（如 "eTick"）
- `data: Any` - 事件数据（对于EVENT_TICK，data是TickData对象）

**Relationships**:
- 由 EventEngine 创建和分发
- 被注册的事件处理器接收

## State Management

### ChartWindow 状态

**关键状态变量**:
- `current_vt_symbol: str` - 当前显示的合约
- `history_loaded: bool` - 历史数据是否已加载完成
- `_current_bar: BarData | None` - 当前未完成的K线（大周期）
- `_current_bar_period: datetime | None` - 当前K线所属周期
- `_current_bar_index: int` - 当前K线在history_data中的索引

**状态转换**:
1. **初始化** → `history_loaded = False`
2. **加载历史数据** → `history_loaded = True`
3. **收到tick数据** → 更新 `_current_bar` 或创建新K线
4. **切换合约** → 重置所有状态，重新加载数据

## Validation Rules

1. **Tick数据过滤**：
   - 只处理 `tick.vt_symbol == self.current_vt_symbol` 的tick数据
   - 只处理 `history_loaded == True` 时的tick数据

2. **K线时间验证**：
   - K线的 `datetime` 必须是周期开始时间
   - 1分钟K线：datetime的秒和微秒必须为0
   - 大周期K线：datetime必须符合周期边界规则

3. **价格验证**：
   - `high_price >= low_price`
   - `high_price >= open_price` 且 `high_price >= close_price`
   - `low_price <= open_price` 且 `low_price <= close_price`

## Data Flow

```
Gateway → EventEngine.put(Event(EVENT_TICK, TickData))
    ↓
EventEngine._process() → 分发到注册的处理器
    ↓
ChartWindow.process_tick_event(Event)
    ↓
过滤：tick.vt_symbol == current_vt_symbol && history_loaded
    ↓
1分钟周期：BarGenerator.update_tick(tick) → on_bar(BarData) → chart.update_bar()
大周期：_update_current_bar_with_tick(tick) → chart.update_bar()
    ↓
ChartWidget.update_bar(BarData) → 更新图表显示
```

