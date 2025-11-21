# MHImain合约策略回测流程设计文档

## 一、概述

本文档梳理了使用VeighNa框架对MHImain合约进行策略回测的完整流程。MHImain是富途期货的连续合约代码，回测使用Alpha策略回测引擎（`vnpy.alpha.strategy.BacktestingEngine`）。

## 二、系统架构

### 2.1 核心组件

```
┌─────────────────────────────────────────────────────────────┐
│                     回测系统架构                               │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  AlphaLab    │───▶│Backtesting   │───▶│  Strategy    │  │
│  │  数据管理     │    │   Engine      │    │   策略逻辑    │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                     │                     │        │
│         ▼                     ▼                     ▼        │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  Parquet     │    │  订单撮合     │    │  持仓管理     │  │
│  │  数据存储     │    │  系统        │    │              │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  合约配置     │    │  盈亏计算     │    │  统计分析     │  │
│  │  contract.json│    │              │    │              │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 关键类说明

1. **AlphaLab** (`vnpy.alpha.lab.AlphaLab`)
   - 数据管理：存储和加载历史K线数据（Parquet格式）
   - 合约管理：维护合约交易配置（手续费率、合约大小、价格跳动等）
   - 路径管理：管理数据存储目录结构

2. **BacktestingEngine** (`vnpy.alpha.strategy.backtesting.BacktestingEngine`)
   - 回测引擎：控制整个回测流程
   - 订单撮合：模拟订单成交逻辑
   - 盈亏计算：逐日盯市盈亏计算

3. **AlphaStrategy** (`vnpy.alpha.strategy.template.AlphaStrategy`)
   - 策略模板：定义策略接口
   - 持仓管理：维护策略持仓状态
   - 订单接口：提供买卖平仓接口

## 三、回测流程详解

### 3.1 数据准备阶段

#### 3.1.1 创建AlphaLab实例

```python
from vnpy.alpha import AlphaLab

# 创建实验室实例，指定数据存储路径
lab = AlphaLab("./lab/mhimain")
```

目录结构：
```
lab/mhimain/
├── daily/          # 日线数据目录
│   └── MHImain.SEHK.parquet
├── minute/         # 分钟线数据目录
│   └── MHImain.SEHK.parquet
├── contract.json   # 合约配置文件
├── dataset/        # 数据集目录
├── model/          # 模型目录
└── signal/         # 信号目录
```

#### 3.1.2 保存历史数据

历史数据需要保存为Parquet格式，存储在对应的目录下。

**数据格式要求：**
- 文件名：`{vt_symbol}.parquet`，例如：`MHImain.SEHK.parquet`
- 存储位置：根据K线周期选择`daily/`或`minute/`目录
- 数据列：datetime, open, high, low, close, volume, turnover, open_interest

**数据加载方法（如果有数据源）：**
```python
from vnpy.trader.object import BarData
from vnpy.trader.constant import Interval

# 假设有数据源，转换为BarData格式后保存
bars: list[BarData] = [...]  # 从数据源获取
lab.save_bar_data(bars)
```

#### 3.1.3 配置合约信息

合约配置保存在`contract.json`文件中，包含：
- `long_rate`: 做多手续费率（按成交金额比例）
- `short_rate`: 做空手续费率（按成交金额比例）
- `size`: 合约大小（合约乘数）
- `pricetick`: 价格跳动单位

```python
# 添加合约配置
lab.add_contract_setting(
    vt_symbol="MHImain.SEHK",
    long_rate=0.0003,      # 万分之3
    short_rate=0.0003,     # 万分之3
    size=50,               # 合约乘数（假设）
    pricetick=1.0          # 价格跳动（假设）
)
```

### 3.2 策略开发阶段

#### 3.2.1 创建策略类

策略需要继承`AlphaStrategy`并实现三个抽象方法：

```python
from vnpy.alpha.strategy import AlphaStrategy
from vnpy.trader.object import BarData
from vnpy.trader.constant import Direction, Offset

class SimpleStrategy(AlphaStrategy):
    """简单策略示例"""
    
    def on_init(self) -> None:
        """策略初始化"""
        self.write_log("策略初始化完成")
        # 初始化指标、缓存变量等
    
    def on_bars(self, bars: dict[str, BarData]) -> None:
        """K线数据回调"""
        bar = bars.get("MHImain.SEHK")
        if not bar:
            return
        
        # 策略逻辑
        # 例如：简单突破策略
        if bar.close_price > bar.open_price:
            # 买入
            self.buy("MHImain.SEHK", bar.close_price, 1)
        elif bar.close_price < bar.open_price:
            # 卖出
            self.sell("MHImain.SEHK", bar.close_price, 1)
    
    def on_trade(self, trade: TradeData) -> None:
        """成交回调"""
        self.write_log(f"成交：{trade.vt_symbol} {trade.direction} {trade.volume}@{trade.price}")
```

#### 3.2.2 策略接口说明

**持仓管理：**
- `get_pos(vt_symbol)`: 获取当前持仓
- `set_target(vt_symbol, target)`: 设置目标持仓
- `get_target(vt_symbol)`: 获取目标持仓

**下单接口：**
- `buy(vt_symbol, price, volume)`: 买入开仓
- `sell(vt_symbol, price, volume)`: 卖出平仓
- `short(vt_symbol, price, volume)`: 卖出开仓
- `cover(vt_symbol, price, volume)`: 买入平仓
- `send_order(vt_symbol, direction, offset, price, volume)`: 发送订单

**信息查询：**
- `get_cash_available()`: 获取可用资金
- `get_holding_value()`: 获取持仓市值
- `get_portfolio_value()`: 获取总资产

### 3.3 回测执行阶段

#### 3.3.1 初始化回测引擎

```python
from vnpy.alpha import AlphaLab, BacktestingEngine
from vnpy.trader.constant import Interval
from datetime import datetime

# 1. 创建AlphaLab
lab = AlphaLab("./lab/mhimain")

# 2. 创建回测引擎
engine = BacktestingEngine(lab)

# 3. 设置回测参数
engine.set_parameters(
    vt_symbols=["MHImain.SEHK"],
    interval=Interval.DAILY,              # 或 Interval.MINUTE
    start=datetime(2023, 1, 1),
    end=datetime(2023, 12, 31),
    capital=1_000_000,                    # 初始资金
    risk_free=0.02,                       # 无风险利率（年化）
    annual_days=240                       # 年交易日数
)

# 4. 添加策略
strategy_setting = {}  # 策略参数
signal_df = pl.DataFrame()  # 模型预测信号（如果有）
engine.add_strategy(SimpleStrategy, strategy_setting, signal_df)

# 5. 加载历史数据
engine.load_data()
```

#### 3.3.2 运行回测

```python
# 执行回测
engine.run_backtesting()
```

**回测执行流程：**

```
1. 策略初始化
   └─▶ strategy.on_init()

2. 数据回放循环
   └─▶ for each datetime in sorted(dts):
         ├─▶ new_bars(dt)
         │   ├─▶ 更新K线数据到bars字典
         │   ├─▶ 填充缺失数据（使用前一根K线）
         │   ├─▶ cross_order()  # 订单撮合
         │   │   ├─▶ 检查限价单是否可成交
         │   │   ├─▶ 生成TradeData
         │   │   └─▶ strategy.update_trade()
         │   ├─▶ strategy.on_bars(bars)  # 策略逻辑执行
         │   └─▶ update_daily_close()   # 更新每日收盘价
         │
3. 异常处理
   └─▶ 如果发生异常，记录日志并终止回测
```

**订单撮合逻辑（`cross_order`）：**

1. 遍历所有活跃的限价单
2. 对于买单（LONG）：
   - 如果订单价格 >= 最低价，则成交
   - 成交价 = min(订单价格, 开盘价)
3. 对于卖单（SHORT）：
   - 如果订单价格 <= 最高价，则成交
   - 成交价 = max(订单价格, 开盘价)
4. 检查涨跌停板限制
5. 更新资金和持仓
6. 生成成交记录

### 3.4 结果计算阶段

#### 3.4.1 计算逐日盯市盈亏

```python
# 计算每日盈亏
df = engine.calculate_result()
```

**计算流程：**

```
1. 按交易日分组成交记录
2. 对每个交易日：
   ├─▶ 计算交易盈亏（trading_pnl）
   │   └─▶ 基于开仓价和平仓价计算
   ├─▶ 计算持仓盈亏（holding_pnl）
   │   └─▶ (收盘价 - 昨收) * 持仓量 * 合约大小
   ├─▶ 计算手续费（commission）
   │   └─▶ 成交金额 * 手续费率
   └─▶ 计算净盈亏（net_pnl）
       └─▶ total_pnl - commission
```

**输出DataFrame列：**
- `date`: 交易日
- `trade_count`: 成交笔数
- `turnover`: 成交金额
- `commission`: 手续费
- `trading_pnl`: 交易盈亏
- `holding_pnl`: 持仓盈亏
- `total_pnl`: 总盈亏
- `net_pnl`: 净盈亏

#### 3.4.2 计算统计指标

```python
# 计算统计指标
statistics = engine.calculate_statistics()
```

**统计指标包括：**

1. **基础指标**
   - 起始日期、结束日期
   - 总交易日数、盈利交易日数、亏损交易日数
   - 起始资金、结束资金

2. **收益指标**
   - 总收益率、年化收益率
   - 日均收益率、收益标准差
   - Sharpe Ratio

3. **风险指标**
   - 最大回撤、百分比最大回撤
   - 最长回撤天数
   - 收益回撤比

4. **交易指标**
   - 总盈亏、日均盈亏
   - 总手续费、日均手续费
   - 总成交金额、日均成交金额
   - 总成交笔数、日均成交笔数

#### 3.4.3 可视化结果

```python
# 显示图表
engine.show_chart()
```

**图表包括：**
1. 资金曲线（Balance）
2. 回撤曲线（Drawdown）
3. 每日盈亏柱状图（Daily Pnl）
4. 盈亏分布直方图（Pnl Distribution）

## 四、MHImain合约特殊说明

### 4.1 合约代码格式

MHImain是富途期货的连续合约，完整合约代码格式为：
- `MHImain.SEHK` （富途交易所代码为SEHK）

### 4.2 数据准备

1. **下载历史数据**
   - 可通过富途API下载
   - 或使用DataRecorder录制
   - 或手动导入CSV/Excel数据

2. **数据转换**
   - 转换为BarData格式
   - 保存到AlphaLab的数据目录

3. **数据质量检查**
   - 确保时间序列完整
   - 检查是否有缺失数据
   - 验证价格数据的合理性

### 4.3 合约配置参数

根据实际交易情况配置：
```python
lab.add_contract_setting(
    vt_symbol="MHImain.SEHK",
    long_rate=0.0003,      # 实际手续费率
    short_rate=0.0003,     # 实际手续费率
    size=50,               # 实际合约乘数
    pricetick=1.0          # 实际价格跳动
)
```

## 五、完整示例代码

```python
from datetime import datetime
import polars as pl
from vnpy.alpha import AlphaLab, BacktestingEngine
from vnpy.trader.constant import Interval
from vnpy.alpha.strategy import AlphaStrategy
from vnpy.trader.object import BarData, TradeData

# 1. 数据准备
lab = AlphaLab("./lab/mhimain")

# 配置合约（如果还没有配置）
lab.add_contract_setting(
    vt_symbol="MHImain.SEHK",
    long_rate=0.0003,
    short_rate=0.0003,
    size=50,
    pricetick=1.0
)

# 2. 创建简单策略
class SimpleMHImainStrategy(AlphaStrategy):
    def on_init(self) -> None:
        self.write_log("MHImain策略初始化")
    
    def on_bars(self, bars: dict[str, BarData]) -> None:
        bar = bars.get("MHImain.SEHK")
        if not bar:
            return
        
        pos = self.get_pos("MHImain.SEHK")
        
        # 简单策略：收盘价高于开盘价买入，低于开盘价卖出
        if bar.close_price > bar.open_price and pos <= 0:
            self.buy("MHImain.SEHK", bar.close_price, 1)
        elif bar.close_price < bar.open_price and pos >= 0:
            self.sell("MHImain.SEHK", bar.close_price, abs(pos))
    
    def on_trade(self, trade: TradeData) -> None:
        self.write_log(f"成交：{trade.vt_symbol} {trade.direction} {trade.volume}@{trade.price}")

# 3. 设置回测
engine = BacktestingEngine(lab)
engine.set_parameters(
    vt_symbols=["MHImain.SEHK"],
    interval=Interval.DAILY,
    start=datetime(2023, 1, 1),
    end=datetime(2023, 12, 31),
    capital=1_000_000,
    risk_free=0.02,
    annual_days=240
)

engine.add_strategy(SimpleMHImainStrategy, {}, pl.DataFrame())

# 4. 执行回测
engine.load_data()
engine.run_backtesting()

# 5. 计算结果
df = engine.calculate_result()
statistics = engine.calculate_statistics()

# 6. 显示结果
print("\n=== 回测统计 ===")
for key, value in statistics.items():
    print(f"{key}: {value}")

engine.show_chart()
```

## 六、常见问题与注意事项

### 6.1 数据问题

1. **数据缺失**
   - 如果某个时间点没有数据，系统会用前一根K线填充
   - 建议确保数据完整性

2. **数据格式**
   - 确保datetime格式正确
   - 价格和成交量不能为负数

### 6.2 策略问题

1. **持仓管理**
   - 注意`pos_data`是净持仓（可正可负）
   - 买入增加持仓，卖出减少持仓

2. **订单撮合**
   - 限价单可能不会立即成交
   - 需要检查订单状态

3. **资金管理**
   - 下单前检查可用资金
   - 注意保证金要求（当前实现可能未考虑）

### 6.3 性能优化

1. **数据加载**
   - 大量数据时使用Parquet格式提高加载速度

2. **策略计算**
   - 避免在`on_bars`中进行复杂计算
   - 使用缓存机制减少重复计算

## 七、下一步工作

1. **实现简单策略**
   - 从最简单的买入持有策略开始
   - 逐步增加策略复杂度

2. **数据准备**
   - 下载MHImain历史数据
   - 转换为Parquet格式

3. **合约配置**
   - 确认实际交易参数
   - 配置正确的合约信息

4. **回测验证**
   - 使用小样本数据测试
   - 验证回测逻辑正确性

5. **策略优化**
   - 参数优化
   - 策略改进

## 八、参考资源

1. **代码位置**
   - 回测引擎：`vnpy/alpha/strategy/backtesting.py`
   - 策略模板：`vnpy/alpha/strategy/template.py`
   - 数据管理：`vnpy/alpha/lab.py`

2. **示例代码**
   - `examples/alpha_research/research_workflow_lgb.ipynb`
   - `examples/cta_backtesting/backtesting_demo.ipynb`

3. **文档**
   - VeighNa官方文档
   - Alpha模块说明

