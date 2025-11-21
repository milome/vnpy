# MHImain合约策略回测示例

这是一个最简单的MHImain合约策略回测示例，用于验证回测系统是否正常工作。

## 文件说明

- `simple_strategy.py`: 简单的策略实现
  - `SimpleMHImainStrategy`: 简单趋势策略（收盘价高于开盘价买入，低于开盘价卖出）
  - `BuyAndHoldStrategy`: 买入持有策略（用于测试系统）
  
- `backtest_mhimain.py`: 完整的回测脚本
  - 数据下载
  - 合约配置
  - 回测执行
  - 结果显示

## 使用步骤

### 1. 配置数据服务

在`vt_setting.json`中配置数据服务（如富途）：

```json
{
    "datafeed.name": "futu",
    "datafeed.host": "127.0.0.1",
    "datafeed.port": 11111
}
```

### 2. 准备数据

有两种方式准备数据：

#### 方式1: 自动下载（推荐）

运行脚本会自动下载数据：

```bash
cd examples/mhimain_backtest
python backtest_mhimain.py
```

#### 方式2: 手动准备数据

如果有历史数据文件，可以手动导入到`./lab/mhimain/daily/`或`./lab/mhimain/minute/`目录。

### 3. 配置合约参数

在`backtest_mhimain.py`中的`setup_contract_config`函数中配置实际的合约参数：

```python
lab.add_contract_setting(
    vt_symbol="MHImain.SEHK",
    long_rate=0.0003,      # 做多手续费率（根据实际情况调整）
    short_rate=0.0003,     # 做空手续费率（根据实际情况调整）
    size=50,               # 合约乘数（根据实际情况调整）
    pricetick=1.0          # 价格跳动单位（根据实际情况调整）
)
```

### 4. 运行回测

```bash
python backtest_mhimain.py
```

## 策略说明

### SimpleMHImainStrategy（简单趋势策略）

- **逻辑**: 
  - 收盘价高于开盘价 → 买入
  - 收盘价低于开盘价 → 卖出
  
- **特点**: 最简单的趋势跟随策略，用于测试回测系统

### BuyAndHoldStrategy（买入持有策略）

- **逻辑**: 第一个交易日买入，持有到最后
- **特点**: 用于测试回测系统是否正常工作

## 输出结果

回测完成后会显示：

- 基础统计：起始日期、结束日期、总交易日等
- 收益指标：总收益率、年化收益等
- 风险指标：最大回撤、Sharpe Ratio等
- 交易指标：总盈亏、手续费、成交笔数等
- 可视化图表：资金曲线、回撤曲线等

## 常见问题

### 1. 数据下载失败

**问题**: 提示"数据服务初始化失败"

**解决**:
- 确保富途牛牛客户端已启动
- 确保OpenD服务已开启（端口11111）
- 检查`vt_setting.json`中的配置

### 2. 合约配置错误

**问题**: 提示"找不到合约配置"

**解决**:
- 确保运行了`setup_contract_config`函数
- 检查`./lab/mhimain/contract.json`文件是否存在

### 3. 回测结果为空

**问题**: 提示"未生成回测结果"

**解决**:
- 检查数据是否完整
- 检查策略逻辑是否正确
- 检查是否有成交记录

### 4. 图表显示失败

**问题**: 图表无法显示

**解决**:
- 确保安装了plotly库：`pip install plotly`
- 如果在非图形界面环境，可以注释掉`engine.show_chart()`行

## 下一步

1. **优化策略**: 在`simple_strategy.py`中添加更复杂的策略逻辑
2. **参数优化**: 使用遗传算法或网格搜索优化策略参数
3. **扩展数据**: 添加更多历史数据进行更长期的回测
4. **风险管理**: 添加止损、止盈等风险管理机制

## 参考文档

- [MHImain回测流程设计文档](../../MHImain回测流程设计文档.md)
- VeighNa官方文档

