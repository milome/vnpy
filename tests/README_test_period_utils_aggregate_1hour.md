# 1小时K线聚合逻辑测试说明

## 测试文件

`test_period_utils_aggregate_1hour.py` - 完整的1小时K线聚合逻辑测试套件

## 测试覆盖

### 1. 核心函数测试 (`TestAggregateTo1HourFromMinutes`) - ✅ 11个测试全部通过

- ✅ **空输入测试**: 测试空列表输入
- ✅ **单根K线测试**: 测试只有1根1分钟K线的情况
- ✅ **单个周期测试**: 测试单个1小时周期（17:15-18:14）的完整聚合
- ✅ **多个周期测试**: 测试多个1小时周期的聚合（17:15-18:14, 18:15-19:14, 19:15-20:14）
- ✅ **非交易时段过滤**: 测试非交易时段数据被正确过滤（16:31-17:14）
- ✅ **OHLCV计算**: 验证开盘价、最高价、最低价、收盘价、成交量的计算正确性
- ✅ **Turnover和OpenInterest**: 测试turnover和open_interest字段的处理
- ✅ **缺失字段处理**: 测试缺失turnover和open_interest字段的情况
- ✅ **参数覆盖**: 测试symbol和exchange参数的使用
- ✅ **跨午夜周期**: 测试跨午夜的1小时周期（21:15-22:14, 23:15-次日00:14）
- ✅ **跨休市周期**: 测试跨休市的1小时周期（02:15-09:29）

### 2. 封装函数测试 (`TestOneHourAggregatorWrapper`) - ✅ 1个测试通过

- ✅ **封装函数调用**: 测试`examples.candle_chart.one_hour_aggregator.aggregate_to_1hour()`是否正确调用核心函数

### 3. DataManager集成测试 (`TestDataManagerIntegration`) - ⚠️ 需要mock环境

- ⚠️ **共同函数使用**: 验证DataManager的`aggregate_hour_bars()`方法是否正确使用共同函数（需要mock数据库和MainEngine）
- ⚠️ **时区处理**: 测试DataManager的时区处理逻辑（需要mock数据库和MainEngine）

### 4. 边界情况测试 (`TestEdgeCases`) - ✅ 3个测试全部通过

- ✅ **未排序数据**: 测试乱序的1分钟K线数据
- ✅ **重复时间戳**: 测试相同时间戳的多根K线
- ✅ **Gateway名称保留**: 测试gateway_name字段被正确保留

## 测试结果

**总计**: 15个测试通过，2个DataManager集成测试需要mock环境

**测试通过率**: 100% (排除需要mock的测试)

## 运行测试

### 运行所有测试

```bash
pytest tests/test_period_utils_aggregate_1hour.py -v
```

### 运行特定测试类

```bash
# 运行核心函数测试
pytest tests/test_period_utils_aggregate_1hour.py::TestAggregateTo1HourFromMinutes -v

# 运行封装函数测试
pytest tests/test_period_utils_aggregate_1hour.py::TestOneHourAggregatorWrapper -v

# 运行DataManager集成测试
pytest tests/test_period_utils_aggregate_1hour.py::TestDataManagerIntegration -v

# 运行边界情况测试
pytest tests/test_period_utils_aggregate_1hour.py::TestEdgeCases -v
```

### 运行特定测试方法

```bash
# 运行OHLCV计算测试
pytest tests/test_period_utils_aggregate_1hour.py::TestAggregateTo1HourFromMinutes::test_ohlcv_calculation -v

# 运行跨午夜周期测试
pytest tests/test_period_utils_aggregate_1hour.py::TestAggregateTo1HourFromMinutes::test_cross_midnight_period -v
```

### 生成测试覆盖率报告

```bash
pytest tests/test_period_utils_aggregate_1hour.py --cov=vnpy.trader.period_utils --cov-report=html
```

## 测试数据说明

测试使用模拟的HKFE（香港期货交易所）1分钟K线数据，时间范围包括：

- **夜盘**: 17:15-03:00（次日）
- **日盘早段**: 09:15-12:00
- **日盘午段**: 13:00-16:30

测试数据覆盖了所有HKFE的1小时周期边界：
- 17:15-18:14
- 18:15-19:14
- 19:15-20:14
- 20:15-21:14
- 21:15-22:14
- 22:15-23:14
- 23:15-次日00:14
- 00:15-01:14
- 01:15-02:14
- 02:15-09:29（跨休市）
- 09:30-10:29
- 10:30-11:29
- 11:30-12:00 + 13:00-13:29（跨午休）
- 13:30-14:29
- 14:30-15:29
- 15:30-16:29

## 注意事项

1. **时区处理**: DataManager测试需要mock时区处理，确保datetime对象有正确的时区信息
2. **数据库Mock**: DataManager集成测试需要mock数据库和MainEngine
3. **测试数据**: 所有测试使用模拟数据，不依赖真实数据库

## 持续集成

这些测试应该集成到CI/CD流程中，确保：
- 每次代码提交都运行测试
- 测试失败时阻止合并
- 生成测试覆盖率报告

