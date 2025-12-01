# 富途API交易费用获取说明

## 概述

已修改 `futu_gateway.py` 中的 `process_deal` 方法，使其能够从富途API返回的成交数据中提取交易费用信息。

## 实现方式

### 1. 费用信息提取

在 `process_deal` 方法中，代码会自动从富途API返回的成交数据中提取以下可能的费用字段：

- `commission`（佣金）
- `fee`（费用）
- `cost`（成本）
- `手续费`（中文字段）
- `佣金`（中文字段）
- `费用`（中文字段）

### 2. 费用信息存储

提取的费用信息会存储在 `TradeData` 对象的 `extra` 字段中，格式为字典：

```python
trade.extra = {
    "commission": 10.5,  # 佣金
    "fee": 2.0,          # 费用
    # ... 其他费用字段
}
```

## 使用方法

### 方法1：从TradeData对象获取费用

```python
# 在策略或交易逻辑中
def on_trade(self, trade: TradeData):
    """成交回调"""
    # 获取费用信息
    if trade.extra:
        commission = trade.extra.get("commission", 0)
        fee = trade.extra.get("fee", 0)
        total_cost = commission + fee
        
        self.write_log(f"成交费用: 佣金={commission}, 费用={fee}, 总计={total_cost}")
```

### 方法2：查询历史成交记录

```python
# 通过交易引擎查询成交记录
from vnpy.trader.engine import MainEngine

# 获取所有成交记录
trades = main_engine.get_all_trades()

# 遍历成交记录，提取费用信息
total_commission = 0
total_fee = 0

for trade in trades:
    if trade.extra:
        commission = trade.extra.get("commission", 0)
        fee = trade.extra.get("fee", 0)
        total_commission += commission
        total_fee += fee

print(f"总佣金: {total_commission}, 总费用: {total_fee}")
```

### 方法3：通过订单ID查询费用

```python
# 根据订单ID查询该订单的所有成交记录
trades = main_engine.get_trades(vt_orderid="FUTU.12345")

# 计算该订单的总费用
order_total_cost = 0
for trade in trades:
    if trade.extra:
        commission = trade.extra.get("commission", 0)
        fee = trade.extra.get("fee", 0)
        order_total_cost += commission + fee

print(f"订单总费用: {order_total_cost}")
```

## 注意事项

1. **字段名称可能不同**：富途API返回的费用字段名称可能因版本或市场而异。如果上述字段名不匹配，请检查富途API文档或打印 `row.keys()` 查看实际返回的字段名。

2. **费用字段可能为空**：某些成交记录可能不包含费用信息，使用前请检查 `trade.extra` 是否为 `None`。

3. **费用单位**：费用单位通常是账户货币单位（如港币、美元等），具体取决于交易市场。

4. **实时费用 vs 结算费用**：API返回的费用可能是实时估算值，最终结算费用可能略有不同。

## 调试方法

如果无法获取费用信息，可以通过以下方式调试：

```python
# 在 process_deal 方法中添加调试代码
def process_deal(self, data) -> None:
    """成交信息处理推送"""
    # 打印返回数据的所有字段
    if not data.empty:
        print("富途API返回的字段:", data.columns.tolist())
        print("第一条记录:", data.iloc[0].to_dict())
    
    # ... 其余代码
```

## 富途API文档参考

如需了解富途API返回的完整字段列表，请参考：
- 富途OpenAPI官方文档
- 富途牛牛客户端帮助中心

## 更新日志

- 2024-XX-XX: 添加交易费用提取功能，支持从成交记录中提取费用信息并存储到TradeData.extra字段

