# CTA回测日志说明

## 日志输出机制

### 1. 策略日志（write_log）

**是的，CTA回测中策略会产生信号、开仓、平仓的日志！**

策略中调用 `write_log()` 函数时，日志会通过以下路径输出：

```
策略 write_log() 
  → cta_engine.write_log() 
    → backtesting_engine.write_log() 
      → 添加到 self.logs 列表
```

### 2. 日志存储位置

在CTA回测引擎中，策略的日志被存储在：
- **`backtesting_engine.logs`** - 一个列表，包含所有策略日志

### 3. 日志格式

策略日志的格式为：
```
{datetime}\t{日志消息}
```

例如：
```
2024-11-20 19:01:42	[09:30:15] 金叉做多信号 - 开仓价:20000, 止损价:19800, 趋势:上升
2024-11-20 19:01:42	[09:35:20] 成交回报:多 1手 @ 20000
2024-11-20 19:01:42	[10:15:30] 死叉平多 - 平仓价:20100
```

## 如何查看策略日志

### 方法1：在UI中查看（推荐）✅

**现在策略日志会自动显示在CTA回测UI的日志窗口中！**

修改后的回测引擎会将策略的 `write_log()` 日志通过 `output()` 输出，这样日志就会显示在UI的日志窗口中。

日志格式示例：
```
[CTA回测] 2024-11-20 19:01:42	[策略名称]  [09:30:15] 金叉做多信号 - 开仓价:20000, 止损价:19800, 趋势:上升
[CTA回测] 2024-11-20 19:01:42	[策略名称]  成交回报:多 1手 @ 20000
```

### 方法2：通过代码获取日志

回测完成后，可以通过以下方式获取日志：

```python
# 获取回测引擎实例
backtesting_engine = backtester_engine.backtesting_engine

# 方法1：直接访问logs属性
logs = backtesting_engine.logs

# 方法2：使用get_all_logs()方法（推荐）
logs = backtesting_engine.get_all_logs()

# 打印日志
for log in logs:
    print(log)
```

### 方法3：查看控制台输出

策略日志也会输出到控制台，格式为：
```
[CTA回测] 2024-11-20 19:01:42	[策略名称]  [09:30:15] 金叉做多信号 - 开仓价:20000
```

## MHITrendStrategy的日志输出

查看 `mhi_trend_strategy.py`，策略在以下情况会输出日志：

### 1. 开仓信号日志
```python
# 做多信号
self.write_log(f"[{current_time}] 金叉做多信号 - 开仓价:{self.entry_price:.0f}, "
              f"止损价:{self.long_stop:.0f}, 趋势:上升")

# 做空信号
self.write_log(f"[{current_time}] 死叉做空信号 - 开仓价:{self.entry_price:.0f}, "
              f"止损价:{self.short_stop:.0f}, 趋势:下降")
```

### 2. 平仓信号日志
```python
# 平多
self.write_log(f"[{current_time}] {close_reason}平多 - 平仓价:{bar.close_price:.0f}")

# 平空
self.write_log(f"[{current_time}] {close_reason}平空 - 平仓价:{bar.close_price:.0f}")
```

### 3. 成交回报日志
```python
self.write_log(f"成交回报: {trade.direction.value} {trade.volume}手 @ {trade.price:.0f}")
```

### 4. 盈亏日志
```python
self.write_log(f"平仓盈利: {pnl:.0f} 港币")
# 或
self.write_log(f"平仓亏损: {pnl:.0f} 港币")
```

## 日志输出示例

如果策略正常运行，你应该能看到类似这样的日志：

```
2024-11-20 19:01:42	[09:30:15] 金叉做多信号 - 开仓价:20000, 止损价:19800, 趋势:上升
2024-11-20 19:01:42	成交回报:多 1手 @ 20000
2024-11-20 19:01:42	[10:15:30] 死叉平多 - 平仓价:20100
2024-11-20 19:01:42	成交回报:空 1手 @ 20100
2024-11-20 19:01:42	平仓盈利: 1000 港币
```

## 如果看不到日志

### 可能的原因：

1. **策略没有产生交易信号**
   - 检查策略逻辑是否正确
   - 检查趋势过滤条件是否太严格

2. **日志没有输出到UI**
   - 策略日志存储在 `backtesting_engine.logs` 中
   - 需要通过代码获取或查看控制台

3. **回测参数设置问题**
   - 检查数据是否正确加载
   - 检查策略是否正常初始化

## 增强日志输出的建议

如果你想在回测中看到更详细的日志，可以在策略中添加更多 `write_log()` 调用：

```python
def on_5min_bar(self, bar: BarData):
    """5分钟K线推送"""
    # 添加调试日志
    self.write_log(f"收到K线: 时间={bar.datetime}, 收盘价={bar.close_price:.0f}")
    
    # 计算指标
    self.calculate_indicators()
    self.write_log(f"指标计算: 快线={self.fast_ma:.0f}, 慢线={self.slow_ma:.0f}, ATR={self.atr_value:.0f}")
    
    # 判断趋势
    self.update_trend_direction()
    self.write_log(f"趋势方向: {self.trend_direction} (1=上升, -1=下降, 0=无趋势)")
    
    # 生成信号
    self.generate_signals(bar)
```

## 总结

✅ **是的，CTA回测中策略会产生信号、开仓、平仓的日志**

- 日志通过 `write_log()` 函数输出
- 日志存储在 `backtesting_engine.logs` 列表中
- **日志会自动显示在CTA回测UI的日志窗口中**（已优化）
- 日志格式：`{datetime}\t[{策略名称}]  {消息}`
- 可以通过 `get_all_logs()` 方法获取所有日志

### 改进说明

已优化回测引擎的 `write_log()` 方法：
- ✅ 策略日志现在会自动通过 `output()` 输出到UI日志窗口
- ✅ 添加了 `get_all_logs()` 方法，方便获取所有策略日志
- ✅ 日志包含策略名称前缀，便于区分不同策略实例

如果回测时看不到策略日志，可能是：
1. 策略没有产生交易信号
2. 策略逻辑有问题，没有执行到日志输出代码
3. UI日志窗口被清空或隐藏

