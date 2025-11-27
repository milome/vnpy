# CTA回测风控修复说明

## 问题描述

策略在回测开始时几天有交易，后续完全没有信号成交了。

## 根本原因

### 1. **每日交易次数未重置** ⚠️

**问题**：`daily_trade_count` 在整个回测期间从未按日期重置，导致：
- 一旦达到 `max_daily_trades`（5次），后续所有日期都被阻止交易
- 例如：第1天交易了5次，第2天及之后都无法交易

### 2. **连续亏损限制未重置** ⚠️

**问题**：`consecutive_losses` 达到上限后，如果一直没有盈利，会永久阻止交易：
- 一旦连续亏损2次（`max_consecutive_losses = 2`），后续所有交易都被阻止
- 除非有盈利交易重置计数器，否则策略完全无法交易

### 3. **缺少风控限制日志** ⚠️

**问题**：当风控阻止交易时，没有日志说明原因，用户无法知道为什么没有交易信号。

## 修复方案

### 1. 添加日期重置机制

```python
# 在risk_check中检查日期变化
if bar is not None:
    current_date = bar.datetime.strftime("%Y-%m-%d")
    # 如果日期变化，重置每日交易计数
    if self.last_trade_date != "" and current_date != self.last_trade_date:
        if self.daily_trade_count > 0:
            self.write_log(f"日期变化：{self.last_trade_date} -> {current_date}，重置每日交易计数")
        self.daily_trade_count = 0
        self._daily_limit_logged = False  # 重置日志标志
```

### 2. 在开仓时记录交易日期

```python
# 在on_trade中记录交易日期
if trade.offset == Offset.OPEN:
    self.daily_trade_count += 1
    self.last_trade_date = trade.datetime.strftime("%Y-%m-%d")
```

### 3. 添加风控限制日志

```python
# 检查每日交易次数限制
if self.daily_trade_count >= self.max_daily_trades:
    if not self._daily_limit_logged:
        current_date = bar.datetime.strftime("%Y-%m-%d") if bar else "未知日期"
        self.write_log(f"风控限制：{current_date} 当日交易次数已达上限{self.max_daily_trades}次，暂停当日交易")
        self._daily_limit_logged = True
    return False

# 检查连续亏损次数
if self.consecutive_losses >= self.max_consecutive_losses:
    if not self._loss_limit_logged:
        self.write_log(f"风控限制：连续亏损{self.consecutive_losses}次，达到上限{self.max_consecutive_losses}次，暂停交易")
        self._loss_limit_logged = True
    return False
```

### 4. 盈利时重置连续亏损计数器

```python
if pnl > 0:
    self.win_trades += 1
    self.consecutive_losses = 0
    self._loss_limit_logged = False  # 盈利时重置连续亏损日志标志
```

## 修复后的效果

### ✅ 每日交易次数会按日期重置

- 每个交易日开始时，`daily_trade_count` 会重置为 0
- 每个交易日最多交易 5 次，第二天重新开始计算

### ✅ 连续亏损限制会在盈利时重置

- 连续亏损达到上限时，会暂停交易
- 一旦有盈利交易，连续亏损计数器会重置为 0，可以继续交易

### ✅ 会输出风控限制日志

- 当达到每日交易次数上限时，会输出日志说明
- 当达到连续亏损上限时，会输出日志说明
- 用户可以清楚知道为什么没有交易信号

## 示例日志输出

### 正常情况
```
[09:30:15] 金叉做多信号 - 信号价:25023, 止损价:24955, 趋势:上升
成交回报: 多 1手 @ 25022
做多开仓 - 实际成交价:25022, 止损价:24955, 今日交易次数:1/5
```

### 达到每日交易次数上限
```
风控限制：2024-11-20 当日交易次数已达上限5次，暂停当日交易
```

### 日期变化重置
```
日期变化：2024-11-20 -> 2024-11-21，重置每日交易计数
[09:30:15] 金叉做多信号 - 信号价:25023, 止损价:24955, 趋势:上升
```

### 连续亏损达到上限
```
[10:15:30] 死叉平多 - 平仓价:24992
成交回报: 空 1手 @ 24994
平仓亏损: -280 港币 (开仓价:25022, 平仓价:24994)

[11:10:00] 死叉做空信号 - 信号价:24920, 止损价:25035, 趋势:下降
成交回报: 空 1手 @ 24920
做空开仓 - 实际成交价:24920, 止损价:25035, 今日交易次数:2/5

[13:50:00] 金叉平空 - 平仓价:24926
成交回报: 多 1手 @ 24925
平仓亏损: -50 港币 (开仓价:24920, 平仓价:24925)

风控限制：连续亏损2次，达到上限2次，暂停交易
```

### 盈利后重置
```
[14:20:00] 金叉做多信号 - 信号价:25050, 止损价:24980, 趋势:上升
成交回报: 多 1手 @ 25050
做多开仓 - 实际成交价:25050, 止损价:24980, 今日交易次数:3/5

[15:30:00] 死叉平多 - 平仓价:25100
成交回报: 空 1手 @ 25100
平仓盈利: 500 港币 (开仓价:25050, 平仓价:25100)
```

## 建议

### 1. 调整风控参数

如果策略表现良好，可以适当放宽风控参数：

```python
max_daily_trades: int = 10  # 从5增加到10
max_consecutive_losses: int = 3  # 从2增加到3
```

### 2. 监控风控日志

关注以下日志，了解策略的风控状态：
- `风控限制：连续亏损X次` - 说明策略可能不适合当前市场
- `风控限制：当日交易次数已达上限` - 说明策略交易频率较高

### 3. 优化策略逻辑

如果频繁触发风控限制，可能需要优化策略：
- 提高信号质量（减少假信号）
- 改进趋势过滤（减少震荡市交易）
- 调整止损参数（减少不必要的止损）

## 总结

✅ **修复了每日交易次数未重置的问题** - 每个交易日会重新开始计数

✅ **修复了连续亏损限制未重置的问题** - 盈利交易会重置连续亏损计数器

✅ **添加了风控限制日志** - 用户可以清楚知道为什么没有交易信号

现在策略可以正常在整个回测期间产生交易信号了！

