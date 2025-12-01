# ChartWindow 数据自动补齐功能测试说明

## 测试覆盖范围

本测试文件 `test_chart_window_data_filling.py` 测试了 ChartWindow 的所有数据自动补齐功能，覆盖所有支持的周期。

## 支持的周期

- **1分钟** (1m)
- **5分钟** (5m)
- **1小时** (1h)
- **4小时** (4h)
- **1天** (1d)

## 测试用例列表

### 1. 历史数据缺失补齐测试

#### `test_fill_missing_bars_1m_from_database`
- **测试场景**: 1分钟数据从数据库补齐缺失数据
- **验证点**: 
  - 当历史数据中间有缺失时，能够从数据库加载并补齐
  - 补齐后的数据包含所有时间段

#### `test_fill_missing_bars_5m_from_1m_synthesis`
- **测试场景**: 5分钟数据从1分钟数据合成补齐
- **验证点**:
  - 当5分钟数据缺失时，能够从1分钟数据自动合成
  - 合成的数据正确合并到历史数据中

#### `test_fill_missing_bars_1h_from_1m_synthesis`
- **测试场景**: 1小时数据从1分钟数据合成补齐
- **验证点**:
  - 当1小时数据缺失时，能够从1分钟数据自动合成
  - 合成的数据正确合并到历史数据中

#### `test_fill_missing_bars_4h_from_1m_synthesis`
- **测试场景**: 4小时数据从1分钟数据合成补齐
- **验证点**:
  - 当4小时数据缺失时，能够从1分钟数据自动合成
  - 合成的数据正确合并到历史数据中

### 2. 与当前时间的Gap补齐测试

#### `test_detect_and_fill_gap_1m_from_database`
- **测试场景**: 1分钟数据检测并补齐与当前时间的gap（从数据库）
- **验证点**:
  - 能够检测历史数据与当前时间的gap
  - 从数据库加载gap期间的数据
  - 补齐后标记为无缺口

#### `test_detect_and_fill_gap_1m_from_futu`
- **测试场景**: 1分钟数据检测并补齐与当前时间的gap（从FUTU API）
- **验证点**:
  - 当数据库没有数据时，能够从FUTU API获取
  - 补齐后标记为无缺口

#### `test_detect_and_fill_gap_5m_from_1m_synthesis`
- **测试场景**: 5分钟数据检测并补齐与当前时间的gap（从1分钟数据合成）
- **验证点**:
  - 能够检测gap并获取1分钟数据
  - 从1分钟数据合成5分钟数据
  - 补齐后标记为无缺口

#### `test_detect_and_fill_gap_1h_from_1m_synthesis`
- **测试场景**: 1小时数据检测并补齐与当前时间的gap（从1分钟数据合成）
- **验证点**:
  - 能够检测gap并获取1分钟数据
  - 从1分钟数据合成1小时数据
  - 补齐后标记为无缺口

#### `test_detect_and_fill_gap_4h_from_1m_synthesis`
- **测试场景**: 4小时数据检测并补齐与当前时间的gap（从1分钟数据合成）
- **验证点**:
  - 能够检测gap并获取1分钟数据
  - 从1分钟数据合成4小时数据
  - 补齐后标记为无缺口

### 3. 边界情况测试

#### `test_detect_and_fill_gap_no_gap`
- **测试场景**: 没有gap时不进行补齐
- **验证点**:
  - 当历史数据已到当前时间时，不进行补齐
  - 不标记为有缺口

#### `test_detect_and_fill_gap_fail_to_fetch`
- **测试场景**: 无法获取gap数据时标记为有缺口
- **验证点**:
  - 当数据库和FUTU API都无法获取数据时
  - 正确标记为有缺口
  - 记录缺口信息

### 4. 数据加载测试

#### `test_load_history_data_1m_from_futu_when_empty`
- **测试场景**: 1分钟数据在数据库为空时从FUTU API获取
- **验证点**:
  - 当数据库完全没有数据时
  - 能够从FUTU API获取数据
  - 正确调用FUTU API方法

### 5. 配置验证测试

#### `test_all_intervals_supported`
- **测试场景**: 验证所有支持的周期都在配置中
- **验证点**:
  - INTERVAL_MAP包含所有5个周期
  - 每个周期都能正确转换为Interval枚举

## 运行测试

### 运行所有测试
```bash
pytest tests/chart/test_chart_window_data_filling.py -v
```

### 运行特定测试
```bash
pytest tests/chart/test_chart_window_data_filling.py::TestChartWindowDataFilling::test_fill_missing_bars_1m_from_database -v
```

### 运行特定周期的测试
```bash
# 测试1分钟周期
pytest tests/chart/test_chart_window_data_filling.py -k "1m" -v

# 测试5分钟周期
pytest tests/chart/test_chart_window_data_filling.py -k "5m" -v

# 测试1小时周期
pytest tests/chart/test_chart_window_data_filling.py -k "1h" -v

# 测试4小时周期
pytest tests/chart/test_chart_window_data_filling.py -k "4h" -v
```

### 运行gap补齐相关测试
```bash
pytest tests/chart/test_chart_window_data_filling.py -k "gap" -v
```

## 测试依赖

测试使用以下mock对象：
- `mock_main_engine`: 模拟MainEngine
- `mock_event_engine`: 模拟EventEngine
- `mock_database`: 模拟数据库
- `_fetch_bars_from_futu`: Mock FUTU API调用
- `_synthesize_bars_from_minute`: Mock数据合成方法

## 注意事项

1. **时区处理**: 所有测试都使用本地时区，确保时间计算正确
2. **数据限制**: 为避免测试时间过长，某些测试限制了生成的数据量
3. **Mock对象**: 测试使用Mock对象模拟外部依赖，不依赖真实的数据库或API
4. **线程安全**: `load_history_data` 在后台线程运行，测试中可能需要适当的同步机制

## 测试覆盖率目标

- ✅ 所有5个周期都覆盖
- ✅ 数据库补齐路径
- ✅ FUTU API补齐路径
- ✅ Gap检测和补齐
- ✅ 边界情况（无gap、无法获取数据）
- ✅ 配置验证

## 维护说明

当添加新的周期或修改补齐逻辑时，需要：
1. 添加对应的测试用例
2. 更新本README文档
3. 确保所有测试通过

