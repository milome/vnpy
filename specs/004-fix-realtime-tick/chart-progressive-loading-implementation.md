# ChartWidget 渐进式加载实现方案（带配置项）

**目标**: 实现历史K线数据的渐进式加载，先加载最近N根K线快速显示，再后台补全全量历史  
**优先级**: P0  
**预计耗时**: 2-3小时

## 一、配置项设计

### 1.1 配置项定义

在 `vnpy/trader/setting.py` 中添加以下配置项：

```python
SETTINGS: dict = {
    # ... 现有配置 ...
    
    # ChartWidget 历史数据渐进式加载配置
    "chart.history.progressive_load.enabled": True,  # 是否启用渐进式加载
    "chart.history.progressive_load.recent_days": 3,  # 最近加载天数（用于1分钟等小周期）
    "chart.history.progressive_load.recent_bars": 200,  # 最近加载K线根数（备用方案）
    "chart.history.progressive_load.intervals": ["MINUTE"],  # 哪些周期启用渐进式加载
    "chart.history.progressive_load.min_bars_for_progressive": 500,  # 超过多少根K线才启用渐进式加载
}
```

### 1.2 配置项说明

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `chart.history.progressive_load.enabled` | bool | True | 是否启用渐进式加载功能 |
| `chart.history.progressive_load.recent_days` | int | 3 | 最近加载天数（用于按时间窗口计算） |
| `chart.history.progressive_load.recent_bars` | int | 200 | 最近加载K线根数（备用方案，如果按天数计算出的根数太少） |
| `chart.history.progressive_load.intervals` | list[str] | ["MINUTE"] | 哪些周期启用渐进式加载，可选值：MINUTE, MINUTE_5, HOUR, HOUR_4, DAILY |
| `chart.history.progressive_load.min_bars_for_progressive` | int | 500 | 超过多少根K线才启用渐进式加载（避免小数据量时不必要的分步加载） |

### 1.3 配置策略

**按周期类型**:
- **1分钟**: 默认启用，加载最近3天（约4320根）
- **5分钟**: 可选启用，加载最近7天（约2016根）
- **1小时**: 可选启用，加载最近30天（约720根）
- **4小时**: 可选启用，加载最近90天（约540根）
- **日线**: 通常不需要渐进式加载（数据量小）

**按数据量**:
- 如果全量数据 < 500根，直接一次性加载（不启用渐进式）
- 如果全量数据 >= 500根，启用渐进式加载

## 二、代码修改

### 2.1 修改 `vnpy/trader/setting.py`

**文件**: `vnpy/trader/setting.py`  
**位置**: 在 `SETTINGS` 字典中添加配置项（约第42行之后）

**修改内容**:
```python
SETTINGS: dict = {
    # ... 现有配置 ...
    
    "position.view.enabled": True,
    "position.view.emit_legacy": True,
    "position.view.debug": False,
    
    # ChartWidget 历史数据渐进式加载配置
    "chart.history.progressive_load.enabled": True,
    "chart.history.progressive_load.recent_days": 3,
    "chart.history.progressive_load.recent_bars": 200,
    "chart.history.progressive_load.intervals": ["MINUTE"],
    "chart.history.progressive_load.min_bars_for_progressive": 500,
}
```

### 2.2 修改 `vnpy/trader/ui/widget.py`

**文件**: `vnpy/trader/ui/widget.py`  
**位置**: `ChartWidget.load_history_data()` 方法（约3103行）

**完整修改后的代码**:
```python
def load_history_data(self, vt_symbol: str) -> None:
    """加载历史K线数据（支持渐进式加载：先加载最近一段，再后台补全全量）"""
    from threading import Thread
    from datetime import datetime, timedelta
    from tzlocal import get_localzone_name
    from vnpy.trader.setting import SETTINGS

    # 获取用户选择的起始时间
    start_qdt = self.start_datetime.dateTime()

    # 转换为Python datetime
    start_py = start_qdt.toPython()

    # 获取当前选择的周期和数据源
    interval_enum = self._get_interval_enum()
    data_source = self.current_data_source
    csv_path = self.csv_file_path

    def _load() -> None:
        try:
            from vnpy.trader.utility import extract_vt_symbol, ZoneInfo
            from vnpy.trader.constant import Interval
            from vnpy.trader.object import HistoryRequest, BarData
            from vnpy.trader.database import get_database
            from vnpy.trader.datafeed import get_datafeed

            symbol, exchange = extract_vt_symbol(vt_symbol)

            # 起始时间使用用户选择，结束时间使用当前最新时间
            local_tz = ZoneInfo(get_localzone_name())
            start: datetime = start_py.replace(tzinfo=local_tz)
            end: datetime = datetime.now(local_tz)  # 结束时间始终为当前最新

            # ---------- 读取渐进式加载配置 ----------
            progressive_enabled = SETTINGS.get("chart.history.progressive_load.enabled", True)
            recent_days = SETTINGS.get("chart.history.progressive_load.recent_days", 3)
            recent_bars = SETTINGS.get("chart.history.progressive_load.recent_bars", 200)
            progressive_intervals = SETTINGS.get("chart.history.progressive_load.intervals", ["MINUTE"])
            min_bars_for_progressive = SETTINGS.get("chart.history.progressive_load.min_bars_for_progressive", 500)

            # 判断当前周期是否启用渐进式加载
            interval_name = interval_enum.value if hasattr(interval_enum, 'value') else str(interval_enum)
            should_use_progressive = (
                progressive_enabled and
                interval_name in progressive_intervals
            )

            data: list[BarData] | None = None

            # 根据数据源加载数据
            if data_source == self.DATA_SOURCE_CSV:
                # 从CSV文件加载（一次性全部，不分页）
                data = self._load_from_csv(csv_path, symbol, exchange, interval_enum, start, end)
            else:
                # 从数据库加载（用户选择了"从数据库加载"）
                database = get_database()

                # ---------- 1）先加载全量数据，用于判断是否需要渐进式加载 ----------
                data = database.load_bar_data(
                    symbol,
                    exchange,
                    interval_enum,
                    start,
                    end,
                )

                # 如果数据库中没有数据或数据不完整，根据周期类型进行处理
                if interval_enum in [Interval.MINUTE_5, Interval.HOUR, Interval.HOUR_4]:
                    # 检测数据中的缺失时间段并补齐
                    data = self._fill_missing_bars(
                        data, symbol, exchange, interval_enum, start, end, database
                    )
                elif interval_enum == Interval.MINUTE and not data:
                    # 对于1分钟数据，如果数据库中没有数据，尝试从FUTU API获取
                    self.main_engine.write_log(f"数据库中没有{interval_enum.value}数据，尝试从FUTU API获取...")
                    data = self._fetch_bars_from_futu(
                        symbol, exchange, interval_enum, start, end
                    )
                    if data:
                        self.main_engine.write_log(
                            f"从FUTU API获取了 {len(data)} 根{interval_enum.value}K线"
                        )
                    else:
                        self.main_engine.write_log(
                            f"无法从FUTU API获取{interval_enum.value}数据，请先在DataManager中下载数据"
                        )
```

**注意**: `_fetch_bars_from_futu` 方法需要实现，见下面的 2.4 节

                # ---------- 2）渐进式加载逻辑 ----------
                if should_use_progressive and data and len(data) >= min_bars_for_progressive:
                    # 计算"最近窗口"的时间范围
                    recent_window = timedelta(days=recent_days)
                    recent_start = max(start, end - recent_window)

                    # 加载最近一段数据
                    recent_data = database.load_bar_data(
                        symbol,
                        exchange,
                        interval_enum,
                        recent_start,
                        end,
                    )

                    # 如果按天数计算的数据太少，使用按根数计算
                    if recent_data and len(recent_data) < recent_bars:
                        # 从全量数据中取最后 N 根
                        if len(data) >= recent_bars:
                            recent_data = data[-recent_bars:]
                        else:
                            recent_data = data

                    # 如果最近数据存在，先发送给图表快速显示
                    if recent_data:
                        self.main_engine.write_log(
                            f"[渐进式加载] 先加载最近 {len(recent_data)} 根K线 "
                            f"({recent_data[0].datetime.strftime('%Y-%m-%d %H:%M')} ~ "
                            f"{recent_data[-1].datetime.strftime('%Y-%m-%d %H:%M')})"
                        )
                        # 先发送最近数据，让图表快速显示
                        self.signal_history.emit(recent_data)

                        # 如果全量数据比最近数据多，稍后发送全量数据（覆盖）
                        if len(data) > len(recent_data):
                            self.main_engine.write_log(
                                f"[渐进式加载] 后台补全全量历史，共 {len(data)} 根K线 "
                                f"({data[0].datetime.strftime('%Y-%m-%d %H:%M')} ~ "
                                f"{data[-1].datetime.strftime('%Y-%m-%d %H:%M')})"
                            )
                            # 延迟一小段时间，让用户先看到最近数据
                            import time
                            time.sleep(0.1)  # 100ms延迟，确保第一次emit完成渲染
                            # 发送全量数据（会覆盖最近数据）
                            self.signal_history.emit(data)
                        else:
                            # 如果最近数据已经等于全量数据，不需要再发送
                            pass
                    else:
                        # 如果最近数据为空，直接发送全量数据
                        if data:
                            self.signal_history.emit(data)
                        else:
                            self.signal_history.emit([])
                else:
                    # 不使用渐进式加载，直接发送全量数据
                    if data:
                        self.signal_history.emit(data)
                    else:
                        self.signal_history.emit([])

            # 对于1小时数据，如果从CSV加载，需要检测并补齐gap
            if data and interval_enum == Interval.HOUR and data_source == self.DATA_SOURCE_CSV:
                # 检测并补齐gap
                data = self._detect_and_fill_gap(data, vt_symbol, interval_enum)
                # 重新发送（如果之前已经发送过）
                if should_use_progressive and len(data) >= min_bars_for_progressive:
                    self.signal_history.emit(data)

        except Exception as e:
            # 转义花括号避免loguru格式化错误
            error_msg = str(e).replace("{", "{{").replace("}", "}}")
            self.main_engine.write_log(f"加载K线历史数据失败: {error_msg}")
            self.signal_history.emit([])

    # 在后台线程加载
    thread: Thread = Thread(target=_load)
    thread.start()
```

### 2.3 添加辅助方法（可选）

如果需要更精细的控制，可以添加一个辅助方法：

**文件**: `vnpy/trader/ui/widget.py`  
**位置**: 在 `load_history_data()` 方法之后

**新增方法**:
```python
def _should_use_progressive_load(
    self, 
    interval_enum: "Interval", 
    total_bars: int
) -> bool:
    """
    判断是否应该使用渐进式加载
    
    Args:
        interval_enum: K线周期
        total_bars: 全量K线根数
    
    Returns:
        是否应该使用渐进式加载
    """
    from vnpy.trader.setting import SETTINGS
    
    progressive_enabled = SETTINGS.get("chart.history.progressive_load.enabled", True)
    if not progressive_enabled:
        return False
    
    min_bars = SETTINGS.get("chart.history.progressive_load.min_bars_for_progressive", 500)
    if total_bars < min_bars:
        return False
    
    progressive_intervals = SETTINGS.get("chart.history.progressive_load.intervals", ["MINUTE"])
    interval_name = interval_enum.value if hasattr(interval_enum, 'value') else str(interval_enum)
    
    return interval_name in progressive_intervals
```

然后在 `load_history_data()` 中使用：
```python
should_use_progressive = self._should_use_progressive_load(interval_enum, len(data) if data else 0)
```

### 2.4 实现 `_fetch_bars_from_futu` 方法（如果不存在）

**文件**: `vnpy/trader/ui/widget.py`  
**位置**: 在 `load_history_data()` 方法之后

**任务**: 如果 `_fetch_bars_from_futu` 方法不存在，需要实现它

**实现代码**:
```python
def _fetch_bars_from_futu(
    self,
    symbol: str,
    exchange: "Exchange",
    interval: "Interval",
    start: datetime,
    end: datetime
) -> list:
    """
    从FUTU API获取K线数据
    
    Args:
        symbol: 合约代码
        exchange: 交易所
        interval: K线周期
        start: 起始时间
        end: 结束时间
    
    Returns:
        K线数据列表
    """
    try:
        from vnpy.trader.object import HistoryRequest
        
        # 构造历史数据请求
        req = HistoryRequest(
            symbol=symbol,
            exchange=exchange,
            interval=interval,
            start=start,
            end=end
        )
        
        # 通过MainEngine查询历史数据（会自动路由到FUTU网关）
        gateway_name = "FUTU"  # 或者从配置中获取
        bars = self.main_engine.query_history(req, gateway_name)
        
        return bars if bars else []
        
    except Exception as e:
        self.main_engine.write_log(f"从FUTU API获取K线数据失败: {str(e)}")
        return []
```

**注意**: 
- 如果代码中已经存在 `_fetch_bars_from_futu` 方法，检查其实现是否正确
- 如果不存在，使用上面的实现
- 该方法通过 `main_engine.query_history()` 调用，会自动路由到FUTU网关的 `query_history()` 方法

## 三、配置项使用示例

### 3.1 默认配置（推荐）

```json
{
  "chart.history.progressive_load.enabled": true,
  "chart.history.progressive_load.recent_days": 3,
  "chart.history.progressive_load.recent_bars": 200,
  "chart.history.progressive_load.intervals": ["MINUTE"],
  "chart.history.progressive_load.min_bars_for_progressive": 500
}
```

**效果**: 
- 只对1分钟周期启用渐进式加载
- 先加载最近3天的1分钟K线（约4320根）
- 如果数据量 < 500根，直接一次性加载

### 3.2 禁用渐进式加载

```json
{
  "chart.history.progressive_load.enabled": false
}
```

**效果**: 所有周期都一次性加载全量数据

### 3.3 多周期启用渐进式加载

```json
{
  "chart.history.progressive_load.enabled": true,
  "chart.history.progressive_load.recent_days": 3,
  "chart.history.progressive_load.intervals": ["MINUTE", "MINUTE_5", "HOUR"]
}
```

**效果**: 
- 1分钟、5分钟、1小时都启用渐进式加载
- 都加载最近3天的数据

### 3.4 按根数控制（更精确）

```json
{
  "chart.history.progressive_load.enabled": true,
  "chart.history.progressive_load.recent_days": 1,
  "chart.history.progressive_load.recent_bars": 500,
  "chart.history.progressive_load.min_bars_for_progressive": 1000
}
```

**效果**: 
- 先加载最近1天或500根（取较大值）
- 只有数据量 >= 1000根时才启用渐进式加载

## 四、测试验证

### 4.1 功能测试

1. **测试渐进式加载启用**:
   - 配置 `enabled: true`, `intervals: ["MINUTE"]`
   - 加载1分钟数据（>500根）
   - 验证：先看到最近3天的数据，然后看到全量数据

2. **测试渐进式加载禁用**:
   - 配置 `enabled: false`
   - 加载1分钟数据
   - 验证：直接看到全量数据，没有分步加载

3. **测试小数据量**:
   - 加载数据量 < 500根
   - 验证：直接一次性加载，不启用渐进式

4. **测试不同周期**:
   - 配置 `intervals: ["MINUTE", "MINUTE_5"]`
   - 验证：1分钟和5分钟启用渐进式，其他周期不启用

### 4.2 性能测试

**测试脚本**:
```python
import time
from vnpy.trader.setting import SETTINGS

# 测试渐进式加载性能
SETTINGS["chart.history.progressive_load.enabled"] = True
SETTINGS["chart.history.progressive_load.recent_days"] = 3

# 记录首次显示时间
start = time.time()
# ... 触发 load_history_data ...
# 记录首次显示时间
first_display_time = time.time() - start

# 记录全量加载时间
full_load_time = time.time() - start

print(f"首次显示耗时: {first_display_time:.2f}秒")
print(f"全量加载耗时: {full_load_time:.2f}秒")
print(f"性能提升: {full_load_time / first_display_time:.1f}x")
```

**预期结果**:
- 首次显示耗时: < 1秒（只加载最近3天）
- 全量加载耗时: 2-5秒（取决于数据量）
- 性能提升: 2-5x

## 五、TODO 清单

### T1: 添加配置项到 `setting.py`（10分钟）

**文件**: `vnpy/trader/setting.py`  
**任务**:
- [ ] 在 `SETTINGS` 字典中添加5个配置项
- [ ] 确保配置项有合理的默认值

### T2: 修改 `load_history_data()` 方法（60分钟）

**文件**: `vnpy/trader/ui/widget.py`  
**任务**:
- [ ] 读取渐进式加载配置项
- [ ] 实现渐进式加载逻辑
- [ ] 添加日志输出
- [ ] 处理边界情况（数据为空、数据量小等）

### T3: 添加辅助方法（可选，20分钟）

**文件**: `vnpy/trader/ui/widget.py`  
**任务**:
- [ ] 实现 `_should_use_progressive_load()` 方法
- [ ] 在 `load_history_data()` 中使用该方法

### T4: 编写测试用例（30分钟）

**文件**: `tests/chart/test_progressive_loading.py`（新建）  
**任务**:
- [ ] 测试渐进式加载启用/禁用
- [ ] 测试不同周期配置
- [ ] 测试小数据量场景
- [ ] 性能测试

### T5: 更新文档（20分钟）

**文件**: `specs/004-fix-realtime-tick/README.md` 或新建文档  
**任务**:
- [ ] 说明配置项含义
- [ ] 提供配置示例
- [ ] 说明使用场景

## 六、预期效果

### 6.1 性能提升

| 场景 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| 1分钟数据（10000根） | 5-10秒 | 首次<1秒，全量5-10秒 | 首次显示快5-10x |
| 5分钟数据（5000根） | 3-5秒 | 首次<1秒，全量3-5秒 | 首次显示快3-5x |
| 日线数据（500根） | <1秒 | <1秒 | 无变化（不启用） |

### 6.2 用户体验提升

1. **快速响应**: 图表在1秒内显示最近数据，用户无需等待
2. **渐进式更新**: 后台补全历史数据，不影响用户操作
3. **可配置**: 用户可以根据需求调整配置项

## 七、注意事项

1. **数据一致性**: 确保全量数据发送时，图表能正确更新（覆盖最近数据）
2. **线程安全**: `signal_history.emit()` 是线程安全的，但要注意数据顺序
3. **配置兼容性**: 如果配置项不存在，使用默认值，确保向后兼容
4. **性能影响**: 渐进式加载会增加一次数据库查询，但用户体验提升明显

## 八、后续优化（可选）

1. **智能预加载**: 根据用户滚动位置，预加载更早的历史数据
2. **缓存机制**: 缓存最近加载的数据，避免重复查询
3. **异步加载**: 使用异步IO进一步优化性能
4. **进度提示**: 显示加载进度，让用户知道正在补全历史数据

