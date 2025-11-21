# MHImain 小恒指期货策略交易开发计划

## 项目概述

开发针对MHImain（小恒指期货）的完整量化交易系统，包括数据采集、策略开发、回测优化和实盘交易。

**目标合约**: MHImain (小型恒生指数期货)
**交易所**: HKFE (Hong Kong Futures Exchange - 香港期货交易所)
**交易所代码**: Exchange.HKFE
**Gateway**: Futu (富途)
**框架**: VNPy 4.2.0

**重要说明**:
- 小恒指期货在VNPy中使用 `Exchange.HKFE`（香港期货交易所）
- 不要与 `Exchange.SEHK`（香港证券交易所，用于股票）混淆
- 在Futu API中，期货市场代码为 "HK_FUTURE"

---

## 一、系统架构设计

### 1.1 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                    VNPy Trading System                  │
├─────────────────────────────────────────────────────────┤
│  Data Layer        │  Strategy Layer  │  Trading Layer  │
│  ├─ DataRecorder   │  ├─ CTA Strategy │  ├─ Order Mgmt │
│  ├─ DataManager    │  ├─ Backtester   │  ├─ Risk Ctrl  │
│  └─ Futu Datafeed  │  └─ Optimizer    │  └─ Futu GW    │
└─────────────────────────────────────────────────────────┘
```

### 1.2 技术栈

- **核心框架**: VNPy 4.2.0
- **数据接口**: Futu API (vnpy_futu)
- **策略框架**: vnpy_ctastrategy 1.3.3
- **回测引擎**: vnpy_ctabacktester 1.2.0
- **数据管理**: vnpy_datamanager 1.2.0
- **数据录制**: vnpy_datarecorder 1.1.1
- **数据库**: SQLite (默认) / TDengine (可选)

### 1.3 开发环境

- Python 3.13
- 开发目录: `d:\Dev\vnpy`
- 运行环境: `d:\veighna_studio`
- 策略目录: `d:\Dev\vnpy\strategies\mhi`

---

## 二、详细开发阶段

## 阶段 1: K线数据录制系统 (1-2天)

### 1.1 配置DataRecorder

**目标**: 实时录制MHImain的Tick和K线数据

**步骤**:
1. 在VNPy主界面中启用DataRecorder应用
2. 配置录制参数：
   - 合约代码: `MHImain.HKFE`
   - 录制类型: Tick数据 + 1分钟K线
   - 存储方式: SQLite数据库
   - 录制时间: 交易时段（09:15-12:00, 13:00-16:30, 17:15-01:00）

**实现文件**:
```python
# 文件位置: d:\Dev\vnpy\config\recorder_config.json
{
    "MHImain.HKFE": {
        "record_tick": true,
        "record_bar": true,
        "bar_interval": "1m"
    }
}
```

**验证**:
- 检查数据库中是否有实时数据写入
- 验证数据完整性（无缺失）
- 检查时间戳正确性

### 1.2 数据质量监控

**功能**:
- 实时监控数据录制状态
- 检测数据断连和异常
- 自动重连机制

**实现**:
```python
# 文件: d:\Dev\vnpy\scripts\monitor_data_recording.py
```

---

## 阶段 2: 历史K线数据准备 (1天)

### 2.1 下载历史数据

**目标**: 获取至少3-6个月的历史K线数据用于回测

**数据源选择**:
1. **Futu API** (推荐)
   - 优点: 与实盘数据源一致
   - 限制: 最多120天历史数据
   - 免费

2. **其他数据源**:
   - RQData (米筐): 需付费，数据质量高
   - TuShare: 免费但港股期货数据有限

**实现方案**:

```python
# 文件: d:\Dev\vnpy\scripts\download_mhi_history.py

from datetime import datetime, timedelta
from vnpy_futu import FutuGateway
from vnpy.trader.database import get_database
from vnpy.trader.constant import Exchange, Interval

def download_history_data():
    """下载MHImain历史数据"""

    # 配置参数
    symbol = "MHImain"
    exchange = Exchange.HKFE
    interval = Interval.MINUTE  # 1分钟K线
    start_date = datetime.now() - timedelta(days=90)  # 90天历史
    end_date = datetime.now()

    # 使用Futu Gateway下载
    # 实现数据下载逻辑
    pass

if __name__ == "__main__":
    download_history_data()
```

### 2.2 数据清洗和验证

**检查项**:
- 时间连续性（无缺失K线）
- 价格合理性（无异常跳变）
- 成交量合理性
- OHLC关系正确性（High >= Open/Close >= Low）

**实现**:
```python
# 文件: d:\Dev\vnpy\scripts\validate_data.py
```

---

## 阶段 3: 策略开发 (3-5天)

### 3.1 策略类型选择

根据小恒指期货的特点，推荐以下策略类型：

**策略A: 趋势跟踪策略**
- 基于: ATR + 移动平均线
- 适合: 日内趋势行情
- 参数: 快速均线、慢速均线、ATR倍数

**策略B: 震荡交易策略**
- 基于: RSI + 布林带
- 适合: 震荡盘整行情
- 参数: RSI周期、布林带周期、超买超卖阈值

**策略C: 突破交易策略**
- 基于: 通道突破 + 成交量
- 适合: 关键价位突破
- 参数: 通道周期、突破确认条件

### 3.2 策略模板结构

```python
# 文件: d:\Dev\vnpy\strategies\mhi\mhi_trend_strategy.py

from vnpy_ctastrategy import (
    CtaTemplate,
    StopOrder,
    TickData,
    BarData,
    TradeData,
    OrderData,
    BarGenerator,
    ArrayManager,
)

class MHITrendStrategy(CtaTemplate):
    """MHImain趋势跟踪策略"""

    author = "Your Name"

    # 策略参数
    fast_window: int = 10        # 快速均线周期
    slow_window: int = 30        # 慢速均线周期
    atr_window: int = 20         # ATR周期
    atr_multiplier: float = 2.0  # ATR止损倍数
    fixed_size: int = 1          # 固定手数

    # 策略变量
    fast_ma: float = 0
    slow_ma: float = 0
    atr_value: float = 0
    long_entry: float = 0
    short_entry: float = 0
    long_stop: float = 0
    short_stop: float = 0

    parameters = [
        "fast_window",
        "slow_window",
        "atr_window",
        "atr_multiplier",
        "fixed_size"
    ]

    variables = [
        "fast_ma",
        "slow_ma",
        "atr_value",
        "long_entry",
        "short_entry"
    ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """构造函数"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        self.bg = BarGenerator(self.on_bar, 5, self.on_5min_bar)
        self.am = ArrayManager()

    def on_init(self):
        """策略初始化"""
        self.write_log("策略初始化")
        self.load_bar(10)  # 加载10天历史数据

    def on_start(self):
        """策略启动"""
        self.write_log("策略启动")

    def on_stop(self):
        """策略停止"""
        self.write_log("策略停止")

    def on_tick(self, tick: TickData):
        """Tick数据推送"""
        self.bg.update_tick(tick)

    def on_bar(self, bar: BarData):
        """1分钟K线推送"""
        self.bg.update_bar(bar)

    def on_5min_bar(self, bar: BarData):
        """5分钟K线推送（策略主逻辑）"""
        self.cancel_all()

        self.am.update_bar(bar)
        if not self.am.inited:
            return

        # 计算技术指标
        self.fast_ma = self.am.sma(self.fast_window)
        self.slow_ma = self.am.sma(self.slow_window)
        self.atr_value = self.am.atr(self.atr_window)

        # 交易信号逻辑
        if self.pos == 0:
            # 无持仓，检查入场信号
            if self.fast_ma > self.slow_ma:
                # 多头信号
                self.long_entry = bar.close_price
                self.long_stop = bar.close_price - self.atr_value * self.atr_multiplier
                self.buy(self.long_entry, self.fixed_size)

            elif self.fast_ma < self.slow_ma:
                # 空头信号
                self.short_entry = bar.close_price
                self.short_stop = bar.close_price + self.atr_value * self.atr_multiplier
                self.short(self.short_entry, self.fixed_size)

        elif self.pos > 0:
            # 持有多仓，检查出场信号
            if self.fast_ma < self.slow_ma or bar.close_price <= self.long_stop:
                self.sell(bar.close_price, abs(self.pos))

        elif self.pos < 0:
            # 持有空仓，检查出场信号
            if self.fast_ma > self.slow_ma or bar.close_price >= self.short_stop:
                self.cover(bar.close_price, abs(self.pos))

        self.put_event()

    def on_order(self, order: OrderData):
        """委托回报"""
        pass

    def on_trade(self, trade: TradeData):
        """成交回报"""
        self.put_event()

    def on_stop_order(self, stop_order: StopOrder):
        """停止单回报"""
        pass
```

### 3.3 策略开发最佳实践

1. **风险控制**:
   - 单次最大亏损: 账户的1-2%
   - 每日最大亏损限制
   - 持仓时间限制（避免隔夜）

2. **性能优化**:
   - 使用ArrayManager高效计算指标
   - 合理设置load_bar天数
   - 避免频繁计算复杂指标

3. **日志记录**:
   - 记录所有交易信号
   - 记录策略状态变化
   - 记录异常情况

---

## 阶段 4: 回测系统实现 (2-3天)

### 4.1 回测配置

```python
# 文件: d:\Dev\vnpy\scripts\backtest_mhi_strategy.py

from datetime import datetime
from vnpy_ctabacktester import BacktestingEngine
from vnpy.trader.constant import Exchange, Interval
from strategies.mhi.mhi_trend_strategy import MHITrendStrategy

def run_backtest():
    """运行策略回测"""

    # 创建回测引擎
    engine = BacktestingEngine()

    # 设置回测参数
    engine.set_parameters(
        vt_symbol="MHImain.HKFE",
        interval=Interval.MINUTE,
        start=datetime(2024, 8, 1),  # 回测开始日期
        end=datetime(2024, 11, 20),  # 回测结束日期
        rate=0.0003,  # 手续费率（每边0.03%）
        slippage=5,   # 滑点（5港币）
        size=10,      # 合约乘数（小恒指为10）
        pricetick=1,  # 最小价格变动（1港币）
        capital=100000,  # 初始资金（10万港币）
    )

    # 添加策略
    engine.add_strategy(MHITrendStrategy, {
        "fast_window": 10,
        "slow_window": 30,
        "atr_window": 20,
        "atr_multiplier": 2.0,
        "fixed_size": 1
    })

    # 加载历史数据
    engine.load_data()

    # 运行回测
    engine.run_backtesting()

    # 计算回测指标
    df = engine.calculate_result()
    print(df)

    # 计算统计指标
    stats = engine.calculate_statistics()
    print(stats)

    # 显示图表
    engine.show_chart()

if __name__ == "__main__":
    run_backtest()
```

### 4.2 回测评估指标

**关键指标**:
- **收益率**: 总收益率、年化收益率
- **风险指标**: 最大回撤、夏普比率、索提诺比率
- **交易统计**: 总交易次数、胜率、盈亏比
- **时间分析**: 平均持仓时间、最长连续亏损

**目标基准**:
- 年化收益率 > 15%
- 最大回撤 < 20%
- 夏普比率 > 1.0
- 胜率 > 45%
- 盈亏比 > 1.5

### 4.3 回测陷阱规避

1. **过拟合**: 不要过度优化参数
2. **未来函数**: 确保不使用未来数据
3. **交易成本**: 考虑真实滑点和手续费
4. **幸存者偏差**: 使用完整的历史数据
5. **样本外测试**: 保留20-30%数据做样本外验证

---

## 阶段 5: 参数优化 (2-3天)

### 5.1 参数优化框架

```python
# 文件: d:\Dev\vnpy\scripts\optimize_parameters.py

from vnpy_ctabacktester import BacktestingEngine, OptimizationSetting
from strategies.mhi.mhi_trend_strategy import MHITrendStrategy

def optimize_strategy():
    """策略参数优化"""

    engine = BacktestingEngine()
    engine.set_parameters(
        vt_symbol="MHImain.HKFE",
        interval=Interval.MINUTE,
        start=datetime(2024, 8, 1),
        end=datetime(2024, 11, 20),
        rate=0.0003,
        slippage=5,
        size=10,
        pricetick=1,
        capital=100000,
    )

    # 添加策略
    engine.add_strategy(MHITrendStrategy, {})

    # 设置优化参数范围
    setting = OptimizationSetting()
    setting.set_target("sharpe_ratio")  # 优化目标：夏普比率
    setting.add_parameter("fast_window", 5, 20, 5)      # 5-20，步长5
    setting.add_parameter("slow_window", 20, 60, 10)    # 20-60，步长10
    setting.add_parameter("atr_window", 10, 30, 5)      # 10-30，步长5
    setting.add_parameter("atr_multiplier", 1.5, 3.0, 0.5)  # 1.5-3.0，步长0.5

    # 运行多进程优化
    engine.run_ga_optimization(setting, max_workers=4)  # 使用4个进程

    # 或使用网格搜索（更全面但更慢）
    # engine.run_optimization(setting, max_workers=4)

if __name__ == "__main__":
    optimize_strategy()
```

### 5.2 优化方法选择

1. **网格搜索（Grid Search）**:
   - 全面遍历所有参数组合
   - 适合参数空间较小的情况
   - 耗时较长但结果可靠

2. **遗传算法（Genetic Algorithm）**:
   - 智能搜索参数空间
   - 适合参数空间较大的情况
   - 速度快但可能错过最优解

3. **贝叶斯优化（Bayesian Optimization）**:
   - 基于概率模型的智能搜索
   - 样本效率高
   - 需要额外的库支持

### 5.3 Walk-Forward Analysis（滚动优化）

```python
# 每3个月重新优化参数，验证1个月
# 避免参数过时，保持策略适应性

def walk_forward_analysis():
    """滚动窗口优化分析"""

    # 训练期: 3个月
    # 测试期: 1个月
    # 总共分析12个月数据

    # 实现滚动优化逻辑
    pass
```

---

## 阶段 6: 实盘交易实现 (2-3天)

### 6.1 实盘前检查清单

**技术准备**:
- [ ] 回测表现符合预期
- [ ] 样本外测试通过
- [ ] 风控系统完善
- [ ] 监控系统就绪
- [ ] 日志系统完备

**交易准备**:
- [ ] Futu账户资金充足
- [ ] 交易权限开通（期货）
- [ ] 网络连接稳定
- [ ] 备用方案准备

**心理准备**:
- [ ] 理解策略逻辑和风险
- [ ] 设定止损和止盈目标
- [ ] 准备应对回撤
- [ ] 不过度干预策略

### 6.2 实盘启动流程

```python
# 文件: d:\Dev\vnpy\examples\veighna_trader\run.py

# 1. 启动VNPy主程序
python run.py

# 2. 连接Futu Gateway
# 在GUI中输入Futu账户信息并连接

# 3. 启动DataRecorder（数据录制）
# 在应用管理中启用DataRecorder

# 4. 启动CtaStrategy（策略交易）
# 在应用管理中启用CtaStrategy

# 5. 加载策略
# 在CTA策略界面中加载MHITrendStrategy

# 6. 配置策略参数
# 设置优化后的最佳参数

# 7. 初始化策略
# 加载历史数据，初始化指标

# 8. 启动策略
# 开始实盘交易
```

### 6.3 实盘监控系统

```python
# 文件: d:\Dev\vnpy\scripts\monitor_live_trading.py

class TradingMonitor:
    """实盘交易监控系统"""

    def __init__(self):
        self.max_daily_loss = 2000  # 每日最大亏损（港币）
        self.max_position = 2       # 最大持仓手数

    def check_daily_loss(self):
        """检查每日亏损"""
        # 如果超过限制，自动停止策略
        pass

    def check_position(self):
        """检查持仓"""
        # 如果超过限制，发送警报
        pass

    def send_alert(self, message):
        """发送警报"""
        # 邮件、短信、微信等
        pass

    def generate_daily_report(self):
        """生成每日报告"""
        # 交易统计、盈亏分析
        pass
```

### 6.4 风险控制

**仓位管理**:
- 单次开仓不超过账户的30%
- 最大持仓不超过2手
- 避免重仓交易

**止损设置**:
- 固定止损: ATR * 2
- 移动止损: 价格移动后跟随
- 时间止损: 持仓超过一定时间强制平仓

**交易时间**:
- 避开开盘和收盘前15分钟
- 重要经济数据公布时暂停交易
- 市场异常波动时停止策略

---

## 阶段 7: 策略持续改进 (持续进行)

### 7.1 性能监控

**每日监控**:
- 当日盈亏
- 交易次数
- 胜率变化
- 策略运行异常

**每周分析**:
- 周度收益率
- 最大回撤
- 策略参数是否需要调整
- 市场环境变化

**每月评估**:
- 月度总结报告
- 策略表现评级
- 参数优化需求
- 策略改进方向

### 7.2 策略迭代

1. **信号优化**: 改进入场和出场信号
2. **风控优化**: 完善止损和止盈逻辑
3. **新策略开发**: 开发互补策略
4. **策略组合**: 多策略组合交易

---

## 三、开发时间表

| 阶段 | 任务 | 预计时间 | 优先级 |
|------|------|----------|--------|
| 1 | K线数据录制系统 | 1-2天 | 高 |
| 2 | 历史数据准备 | 1天 | 高 |
| 3 | 策略开发 | 3-5天 | 高 |
| 4 | 回测系统 | 2-3天 | 高 |
| 5 | 参数优化 | 2-3天 | 中 |
| 6 | 实盘交易 | 2-3天 | 高 |
| 7 | 持续改进 | 持续 | 中 |

**总计**: 约11-17天完成开发，然后进入持续迭代阶段

---

## 四、项目目录结构

```
d:\Dev\vnpy\
├── strategies/
│   └── mhi/
│       ├── __init__.py
│       ├── mhi_trend_strategy.py        # 趋势策略
│       ├── mhi_oscillation_strategy.py  # 震荡策略
│       └── mhi_breakout_strategy.py     # 突破策略
│
├── scripts/
│   ├── download_mhi_history.py          # 历史数据下载
│   ├── validate_data.py                 # 数据验证
│   ├── backtest_mhi_strategy.py         # 回测脚本
│   ├── optimize_parameters.py           # 参数优化
│   └── monitor_live_trading.py          # 实盘监控
│
├── config/
│   ├── recorder_config.json             # 数据录制配置
│   └── strategy_settings.json           # 策略参数配置
│
├── notebooks/
│   ├── data_analysis.ipynb              # 数据分析
│   ├── strategy_research.ipynb          # 策略研究
│   └── backtest_results.ipynb           # 回测分析
│
├── docs/
│   ├── MHI_STRATEGY_PLAN.md             # 本文档
│   ├── TRADING_RULES.md                 # 交易规则
│   └── RISK_MANAGEMENT.md               # 风险管理
│
└── tests/
    ├── test_strategy.py                 # 策略单元测试
    └── test_backtest.py                 # 回测单元测试
```

---

## 五、关键配置参数

### 5.1 MHImain合约规格

```python
CONTRACT_SPECS = {
    "symbol": "MHImain",               # 主力合约代码
    "name": "小型恒生指数期货",
    "exchange": Exchange.HKFE,         # 香港期货交易所
    "futu_market": "HK_FUTURE",        # Futu API市场代码
    "size": 10,                        # 合约乘数
    "pricetick": 1,                    # 最小变动价位（1港币）
    "min_volume": 1,                   # 最小交易单位
    "margin_rate": 0.05,               # 保证金比率（约5%）
    "commission_rate": 0.0003,         # 手续费率（每边0.03%）

    # 交易时间（香港时间）
    "trading_hours": {
        "session1": "09:15-12:00",   # 上午时段
        "session2": "13:00-16:30",   # 下午时段
        "session3": "17:15-01:00"    # 夜盘时段（次日凌晨）
    }
}
```

**注意事项**:
1. **合约代码**: MHImain是主力合约，自动切换到最近月份
2. **交易所**: 必须使用 `Exchange.HKFE`，不是 `Exchange.SEHK`
3. **Futu市场**: 在Futu Gateway中配置时选择 "HK_FUTURE"
4. **合约月份**: 如需指定月份，格式如 MHI2412（2024年12月）

### 5.2 策略默认参数

```python
STRATEGY_DEFAULTS = {
    "MHITrendStrategy": {
        "fast_window": 10,
        "slow_window": 30,
        "atr_window": 20,
        "atr_multiplier": 2.0,
        "fixed_size": 1,
        "max_positions": 2
    }
}
```

### 5.3 风控参数

```python
RISK_PARAMS = {
    "max_daily_loss": 2000,        # 每日最大亏损（港币）
    "max_position": 2,             # 最大持仓手数
    "max_order_volume": 1,         # 单次最大下单量
    "position_percent": 0.3,       # 单次开仓占账户比例
    "stop_loss_atr": 2.0,          # 止损ATR倍数
    "take_profit_atr": 3.0         # 止盈ATR倍数
}
```

---

## 六、常见问题和解决方案

### 6.1 数据问题

**Q: Futu API历史数据不足怎么办？**
A:
1. 使用其他数据源（RQData、TuShare）
2. 从其他broker获取（如IB、Wind）
3. 购买专业数据服务

**Q: 数据有缺失怎么办？**
A:
1. 前向填充（forward fill）
2. 线性插值
3. 删除缺失数据（如果很少）

### 6.2 策略问题

**Q: 回测表现好但实盘差？**
A:
1. 检查是否过拟合
2. 确认滑点和手续费设置正确
3. 验证是否有未来函数
4. 考虑市场环境变化

**Q: 策略频繁止损？**
A:
1. 放宽止损范围
2. 优化入场信号
3. 增加信号过滤条件
4. 考虑市场波动性

### 6.3 技术问题

**Q: VNPy启动报错？**
A:
1. 检查Python环境
2. 确认依赖包完整
3. 查看日志文件
4. 参考CLAUDE.md文档

**Q: 策略无法加载？**
A:
1. 检查策略文件路径
2. 确认策略类名正确
3. 验证参数配置
4. 查看错误日志

---

## 七、学习资源

### 7.1 官方文档

- VNPy官网: https://www.vnpy.com
- VNPy文档: https://www.vnpy.com/docs/cn/index.html
- GitHub: https://github.com/vnpy/vnpy

### 7.2 推荐书籍

- 《量化交易之路》
- 《海龟交易法则》
- 《期货市场技术分析》
- 《Python量化交易实战》

### 7.3 社区支持

- VNPy官方论坛
- VNPy微信群
- 知乎量化专栏
- GitHub Issues

---

## 八、下一步行动

### 立即开始（第1天）

1. **启动数据录制**:
   ```bash
   # 运行VNPy
   cd d:\Dev\vnpy\examples\veighna_trader
   python run.py
   ```

2. **配置DataRecorder**:
   - 在VNPy界面中启用DataRecorder应用
   - 添加MHImain.HKFE合约
   - 开始录制实时数据

3. **下载历史数据**:
   - 编写数据下载脚本
   - 获取至少3个月历史数据
   - 验证数据质量

### 本周目标（第1周）

- 完成数据录制系统
- 准备历史数据
- 开发第一个策略原型
- 运行初步回测

### 本月目标（第1个月）

- 完成3个策略开发
- 完成参数优化
- 通过样本外测试
- 准备小资金实盘测试

---

## 九、成功指标

### 开发阶段

- [ ] 数据录制系统稳定运行
- [ ] 历史数据完整准备
- [ ] 至少开发3个策略
- [ ] 回测夏普比率 > 1.0
- [ ] 样本外测试盈利

### 实盘阶段

- [ ] 策略稳定运行30天
- [ ] 月度盈利达标
- [ ] 风控系统有效
- [ ] 无重大交易失误

---

## 附录

### A. 技术指标公式

**ATR (Average True Range)**:
```
TR = max(High - Low, abs(High - Close_prev), abs(Low - Close_prev))
ATR = MA(TR, n)
```

**RSI (Relative Strength Index)**:
```
RS = MA(Gains, n) / MA(Losses, n)
RSI = 100 - (100 / (1 + RS))
```

**布林带 (Bollinger Bands)**:
```
Middle = MA(Close, n)
Upper = Middle + k * STD(Close, n)
Lower = Middle - k * STD(Close, n)
```

### B. 回测评估公式

**夏普比率**:
```
Sharpe = (Return - RiskFreeRate) / Volatility
```

**最大回撤**:
```
MaxDrawdown = max(Peak - Trough) / Peak
```

**盈亏比**:
```
ProfitLossRatio = AvgWin / AvgLoss
```

---

**文档版本**: v1.0
**创建日期**: 2024-11-21
**最后更新**: 2024-11-21
**作者**: Claude Code
**状态**: Draft → Review → Approved → Implementation

---

**开发建议**: 从简单开始，逐步迭代。先确保系统稳定可靠，再追求策略复杂性和收益率。
