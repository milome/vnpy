# 止损/止盈对手价下单确认报告

**日期**: 2025-12-01  
**确认内容**: 触发止损和止盈都使用对手价委托下单  
**状态**: ✅ 已确认

---

## 确认结果

✅ **止损触发（`trigger_stop_loss_close`）**: 使用对手价  
✅ **止盈触发（`trigger_take_profit_close`）**: 使用对手价

---

## 代码实现细节

### 1. 止损触发对手价实现

**文件**: `vnpy/chart/widget_trigger.py`  
**方法**: `trigger_stop_loss_close`  
**行数**: 489-508

```python
# 计算对手价：平多仓用买一价，平空仓用卖一价
if close_direction == Direction.SHORT:
    # 平多仓：用买一价（对手价）
    opponent_price = tick.bid_price_1 if tick.bid_price_1 > 0 else tick.last_price
else:
    # 平空仓：用卖一价（对手价）
    opponent_price = tick.ask_price_1 if tick.ask_price_1 > 0 else tick.last_price

# 创建订单请求（对手价限价单+智能追价）
# 使用对手价限价单，确保在波动率大的时段也能快速成交
req = OrderRequest(
    symbol=contract.symbol,
    exchange=contract.exchange,
    direction=close_direction,
    offset=Offset.CLOSE,
    type=OrderType.LIMIT,  # 限价单，但使用对手价，确保快速成交
    price=opponent_price,  # 对手价：买一/卖一
    volume=close_volume,
    reference="OPPONENT_Retry2"  # 启用智能追价（重试2次）
)
```

### 2. 止盈触发对手价实现

**文件**: `vnpy/chart/widget_trigger.py`  
**方法**: `trigger_take_profit_close`  
**行数**: 806-825

```python
# 计算对手价：平多仓用买一价，平空仓用卖一价
if close_direction == Direction.SHORT:
    # 平多仓：用买一价（对手价）
    opponent_price = tick.bid_price_1 if tick.bid_price_1 > 0 else tick.last_price
else:
    # 平空仓：用卖一价（对手价）
    opponent_price = tick.ask_price_1 if tick.ask_price_1 > 0 else tick.last_price

# 创建订单请求（对手价限价单+智能追价）
# 使用对手价限价单，确保在波动率大的时段也能快速成交
req = OrderRequest(
    symbol=contract.symbol,
    exchange=contract.exchange,
    direction=close_direction,
    offset=Offset.CLOSE,
    type=OrderType.LIMIT,  # 限价单，但使用对手价，确保快速成交
    price=opponent_price,  # 对手价：买一/卖一
    volume=close_volume,
    reference="OPPONENT_Retry2"  # 启用智能追价（重试2次）
)
```

---

## 对手价计算逻辑

### 对手价选择规则

1. **平多仓**（close_direction = SHORT）:
   - 使用 `tick.bid_price_1`（买一价）
   - 如果买一价无效（≤0），回退到 `tick.last_price`（最新价）

2. **平空仓**（close_direction = LONG）:
   - 使用 `tick.ask_price_1`（卖一价）
   - 如果卖一价无效（≤0），回退到 `tick.last_price`（最新价）

### 为什么使用对手价？

1. **提高成交率**: 在波动率大的时段，使用对手价可以更快成交
2. **避免滑点**: 对手价是当前市场最优价格，减少了价格滑点
3. **紧急平仓**: 止损/止盈通常是紧急平仓，对手价能确保快速成交

---

## 日志记录

### 止损触发日志

```python
main_engine.write_log(
    f"[ChartWidget] [实时止损触发] {current_time} {vt_symbol} {position_direction} "
    f"止损线 {line_price_str} 触发平仓 {close_volume}手@对手价{opponent_price_str} "
    f"(当前价格: {current_price_str}, 止损线ID: {line_id}, 订单ID: {vt_orderid})",
    "ChartWidget"
)
```

**日志示例**:
```
[ChartWidget] [实时止损触发] 22:40:55.776 MHImain.HKFE 空 止损线 26077 触发平仓 1.0手@对手价26080 (当前价格: 26080, 止损线ID: stop_2e885976ca47, 订单ID: FUTU.6454945)
```

### 止盈触发日志

```python
main_engine.write_log(
    f"[ChartWidget] [实时止盈触发] {current_time} {vt_symbol} {position_direction} "
    f"止盈线 {line_price_str} 触发平仓 {close_volume}手@对手价{opponent_price_str} "
    f"(当前价格: {current_price_str}, 止盈线ID: {line_id}, 订单ID: {vt_orderid})",
    "ChartWidget"
)
```

**日志示例**:
```
[ChartWidget] [实时止盈触发] 22:41:10.123 MHImain.HKFE 多 止盈线 26100 触发平仓 1.0手@对手价26105 (当前价格: 26105, 止盈线ID: profit_xxx, 订单ID: FUTU.6455000)
```

---

## 订单类型说明

### 订单类型: `OrderType.LIMIT`

- **类型**: 限价单
- **价格**: 使用对手价（bid_price_1 或 ask_price_1）
- **优势**: 既能快速成交，又能控制价格

### 智能追价配置: `reference="OPPONENT_Retry2"`

- **功能**: 启用智能追价机制
- **重试次数**: 2次
- **行为**: 如果订单未成交，自动调整价格重试

---

## 验证要点

### 测试场景1: 止损触发（空仓）

1. 设置止损线，价格触及止损线
2. **期望**: 
   - 使用 `ask_price_1` 作为对手价（平空仓）
   - 日志显示 `@对手价{ask_price_1}`
   - 订单类型为限价单，价格为对手价

### 测试场景2: 止损触发（多仓）

1. 设置止损线，价格触及止损线
2. **期望**: 
   - 使用 `bid_price_1` 作为对手价（平多仓）
   - 日志显示 `@对手价{bid_price_1}`
   - 订单类型为限价单，价格为对手价

### 测试场景3: 止盈触发（空仓）

1. 设置止盈线，价格触及止盈线
2. **期望**: 
   - 使用 `ask_price_1` 作为对手价（平空仓）
   - 日志显示 `@对手价{ask_price_1}`
   - 订单类型为限价单，价格为对手价

### 测试场景4: 止盈触发（多仓）

1. 设置止盈线，价格触及止盈线
2. **期望**: 
   - 使用 `bid_price_1` 作为对手价（平多仓）
   - 日志显示 `@对手价{bid_price_1}`
   - 订单类型为限价单，价格为对手价

### 测试场景5: 对手价无效时回退

1. 对手价无效（bid_price_1 ≤ 0 或 ask_price_1 ≤ 0）
2. **期望**: 
   - 回退到 `last_price`（最新价）
   - 日志正常显示

---

## 总结

✅ **止损触发**: 已实现对手价下单  
✅ **止盈触发**: 已实现对手价下单  
✅ **价格计算**: 
- 平多仓：使用 `bid_price_1`（买一价）
- 平空仓：使用 `ask_price_1`（卖一价）
- 无效时回退到 `last_price`（最新价）

✅ **订单类型**: 限价单（LIMIT）使用对手价  
✅ **智能追价**: 启用（`OPPONENT_Retry2`）  
✅ **日志记录**: 详细记录对手价信息

**确认状态**: ✅ 已完成

