# 代码复用重构TODO

## 概述

将周期时间划分和开盘价获取功能提取到通用工具模块，供以下三个模块复用：
1. **K线图表模块** (`vnpy/trader/ui/widget.py`)
2. **DataRecorder模块** (`vnpy_datarecorder/`)
3. **DataManager模块** (`vnpy_datamanager/`)

## 发现的重复代码

### 1. 周期时间划分函数

#### K线图表模块
- `_get_period_start()` (3333-3430行) - 通用周期划分
- `_get_hkfe_hour_period_start()` (3432-3509行) - 港期1小时周期划分

#### DataRecorder模块
- `get_period_start()` - 通用周期划分（功能相同）
- `get_hkfe_hour_period_start()` - 港期1小时周期划分（功能相同）

#### DataManager模块
- `_get_hkfe_5minute_period()` (355-376行) - 港期5分钟周期划分
- `_get_hkfe_hour_period()` (533-634行) - 港期1小时周期划分（功能相同）
- `_get_hkfe_4hour_period()` (811-878行) - 港期4小时周期划分（功能相同）
- `_is_hkfe_trading_time()` (319-353行) - 判断是否在交易时段

### 2. 开盘价获取逻辑

#### K线图表模块
- `_get_period_open_price()` (3764-3940行) - 大周期开盘价获取
- `_minute_bars_cache` - 1分钟K线缓存

#### DataRecorder模块
- `PeriodOpenPriceHelper.get_period_open_price()` - 大周期开盘价获取（功能相同）
- `_minute_bars_cache` - 1分钟K线缓存（功能相同）

## 重构任务清单

### 阶段1：准备通用工具模块

- [ ] **任务1.1**: 将 `vnpy_datarecorder/period_utils.py` 移动到 `vnpy/trader/period_utils.py`
  - [ ] 移动文件
  - [ ] 更新文件头部的模块说明
  - [ ] 确保所有导入路径正确

- [ ] **任务1.2**: 扩展通用工具模块，整合DataManager的功能
  - [ ] 添加 `is_hkfe_trading_time()` 函数（从DataManager提取）
  - [ ] 添加 `get_hkfe_5minute_period()` 函数（从DataManager提取）
  - [ ] 确保 `get_hkfe_hour_period_start()` 与DataManager的 `_get_hkfe_hour_period()` 逻辑一致
  - [ ] 确保 `get_period_start()` 的4小时逻辑与DataManager的 `_get_hkfe_4hour_period()` 一致
  - [ ] 扩展 `PeriodOpenPriceHelper`，支持历史数据缓存参数（供K线图表使用）

- [ ] **任务1.3**: 更新通用工具模块的文档字符串
  - [ ] 添加模块级文档
  - [ ] 完善函数文档字符串
  - [ ] 添加使用示例

### 阶段2：重构DataRecorder模块

- [ ] **任务2.1**: 更新DataRecorder模块的导入
  - [ ] 修改 `vnpy_datarecorder/engine.py`，从 `vnpy.trader.period_utils` 导入
  - [ ] 删除 `vnpy_datarecorder/period_utils.py`（已移动到trader）
  - [ ] 验证功能正常

- [ ] **任务2.2**: 更新DataRecorder文档
  - [ ] 更新 `vnpy_datarecorder/docs/多周期K线录制功能说明.md` 中的导入路径说明

### 阶段3：重构K线图表模块

- [ ] **任务3.1**: 替换时间划分函数
  - [ ] 在 `vnpy/trader/ui/widget.py` 顶部添加导入：
    ```python
    from vnpy.trader.period_utils import (
        get_period_start,
        get_hkfe_hour_period_start
    )
    ```
  - [ ] 删除 `_get_period_start()` 方法（3333-3430行）
  - [ ] 删除 `_get_hkfe_hour_period_start()` 方法（3432-3509行）
  - [ ] 将所有 `self._get_period_start()` 调用改为 `get_period_start()`
  - [ ] 将所有 `self._get_hkfe_hour_period_start()` 调用改为 `get_hkfe_hour_period_start()`
  - [ ] 注意：`get_period_start()` 需要传入 `exchange` 参数，需要从 `self.current_vt_symbol` 提取

- [ ] **任务3.2**: 重构开盘价获取逻辑
  - [ ] 在 `__init__` 中初始化 `PeriodOpenPriceHelper`：
    ```python
    from vnpy.trader.period_utils import PeriodOpenPriceHelper
    self.open_price_helper = PeriodOpenPriceHelper()
    ```
  - [ ] 重构 `_get_period_open_price()` 方法，使用 `PeriodOpenPriceHelper`
  - [ ] 在 `on_bar()` 中调用 `self.open_price_helper.cache_minute_bar(bar)`
  - [ ] 确保 `_minute_bars_cache` 的使用迁移到 `PeriodOpenPriceHelper`
  - [ ] 传递 `history_data` 和 `self.bg` 参数给 `get_period_open_price()`

- [ ] **任务3.3**: 测试K线图表功能
  - [ ] 测试标准交易所的周期划分
  - [ ] 测试港期的时间划分
  - [ ] 测试开盘价获取和更新
  - [ ] 测试历史数据加载和修正

### 阶段4：重构DataManager模块

- [ ] **任务4.1**: 替换时间划分函数
  - [ ] 在 `vnpy_datamanager/engine.py` 顶部添加导入：
    ```python
    from vnpy.trader.period_utils import (
        get_period_start,
        get_hkfe_hour_period_start,
        is_hkfe_trading_time
    )
    ```
  - [ ] 删除 `_is_hkfe_trading_time()` 方法（319-353行），使用 `is_hkfe_trading_time()`
  - [ ] 删除 `_get_hkfe_5minute_period()` 方法（355-376行），使用 `get_period_start(dt, Interval.MINUTE_5, Exchange.HKFE)`
  - [ ] 删除 `_get_hkfe_hour_period()` 方法（533-634行），使用 `get_hkfe_hour_period_start()`
  - [ ] 删除 `_get_hkfe_4hour_period()` 方法（811-878行），使用 `get_period_start(dt, Interval.HOUR_4, Exchange.HKFE)`
  - [ ] 更新所有调用点，传入正确的参数

- [ ] **任务4.2**: 更新合成方法
  - [ ] 更新 `aggregate_5minute_bars()` 中的周期计算
  - [ ] 更新 `aggregate_hour_bars()` 中的周期计算
  - [ ] 更新 `aggregate_4hour_bars()` 中的周期计算
  - [ ] 注意：`_get_hkfe_4hour_period()` 返回 `(period_start, period_index)`，需要适配

- [ ] **任务4.3**: 测试DataManager功能
  - [ ] 测试5分钟数据合成
  - [ ] 测试1小时数据合成
  - [ ] 测试4小时数据合成
  - [ ] 测试港期时间划分正确性

### 阶段5：测试和验证

- [ ] **任务5.1**: 单元测试
  - [ ] 为通用工具模块编写完整测试
  - [ ] 测试所有周期的时间划分（标准交易所和港期）
  - [ ] 测试开盘价获取的各个优先级路径
  - [ ] 测试边界情况（跨日、跨周末、金融假期）

- [ ] **任务5.2**: 集成测试
  - [ ] 测试K线图表模块功能完整性
  - [ ] 测试DataRecorder模块功能完整性
  - [ ] 测试DataManager模块功能完整性
  - [ ] 测试三个模块之间的兼容性

- [ ] **任务5.3**: 性能测试
  - [ ] 对比重构前后的性能
  - [ ] 确保缓存机制正常工作
  - [ ] 确保没有性能退化

### 阶段6：文档更新

- [ ] **任务6.1**: 更新代码文档
  - [ ] 更新 `vnpy/trader/period_utils.py` 的模块文档
  - [ ] 添加使用示例到各个模块

- [ ] **任务6.2**: 更新用户文档
  - [ ] 更新K线图表相关文档
  - [ ] 更新DataRecorder相关文档
  - [ ] 更新DataManager相关文档

- [ ] **任务6.3**: 更新重构方案文档
  - [ ] 记录重构过程中的问题和解决方案
  - [ ] 更新 `vnpy_datarecorder/docs/代码复用重构方案.md`

## 注意事项

### 兼容性考虑

1. **参数差异**：
   - K线图表的 `_get_period_start()` 从 `self.current_vt_symbol` 获取交易所
   - 通用工具模块需要显式传入 `exchange` 参数
   - 需要适配调用方式

2. **返回值差异**：
   - DataManager的 `_get_hkfe_4hour_period()` 返回 `(period_start, period_index)`
   - 通用工具模块的 `get_period_start()` 只返回 `period_start`
   - 需要决定是否保留 `period_index` 或移除

3. **缓存机制**：
   - K线图表模块有 `_minute_bars_cache` 和 `history_data`
   - DataRecorder模块有 `_minute_bars_cache`
   - 需要统一到 `PeriodOpenPriceHelper`

### 测试重点

1. **港期时间划分**：
   - 夜盘时段边界
   - 跨日处理
   - 跨周末处理
   - 跨午休处理

2. **开盘价获取**：
   - 数据库查询路径
   - 缓存查找路径
   - BarGenerator查找路径
   - Fallback路径

3. **数据合成**：
   - 5分钟数据合成
   - 1小时数据合成
   - 4小时数据合成

## 预期收益

1. **代码减少**：预计减少约500-600行重复代码
2. **维护成本**：统一维护，降低维护成本
3. **一致性**：确保所有模块使用相同的逻辑
4. **可测试性**：工具模块可以独立测试
5. **可扩展性**：其他模块也可以使用这些工具

## 风险评估

1. **低风险**：通用工具模块已经实现并测试
2. **中风险**：K线图表模块重构需要仔细测试
3. **中风险**：DataManager模块重构需要验证合成逻辑
4. **建议**：分阶段进行，每个阶段完成后充分测试

## 时间估算

- 阶段1：2-3小时
- 阶段2：1小时
- 阶段3：3-4小时
- 阶段4：2-3小时
- 阶段5：2-3小时
- 阶段6：1-2小时

**总计**：11-16小时

