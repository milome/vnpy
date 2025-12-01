# ChartWidget 渐进式加载 TODO 清单

**目标**: 实现历史K线数据的渐进式加载，先加载最近N根K线快速显示，再后台补全全量历史  
**优先级**: P0  
**预计总耗时**: 2-3小时

---

## ✅ T1: 添加配置项到 `setting.py`（10分钟）

**文件**: `vnpy/trader/setting.py`  
**位置**: `SETTINGS` 字典（约第42行之后）

**任务**:
- [ ] 在 `SETTINGS` 字典中添加以下5个配置项：

```python
SETTINGS: dict = {
    # ... 现有配置 ...
    
    # ChartWidget 历史数据渐进式加载配置
    "chart.history.progressive_load.enabled": True,  # 是否启用渐进式加载
    "chart.history.progressive_load.recent_days": 3,  # 最近加载天数
    "chart.history.progressive_load.recent_bars": 200,  # 最近加载K线根数
    "chart.history.progressive_load.intervals": ["MINUTE"],  # 哪些周期启用
    "chart.history.progressive_load.min_bars_for_progressive": 500,  # 最小根数阈值
}
```

---

## ✅ T2: 修改 `load_history_data()` 方法（60分钟）

**文件**: `vnpy/trader/ui/widget.py`  
**位置**: `ChartWidget.load_history_data()` 方法（约3103行）

**任务**:
- [ ] 导入配置模块：`from vnpy.trader.setting import SETTINGS`
- [ ] 导入时间模块：`from datetime import timedelta`
- [ ] 读取渐进式加载配置项
- [ ] 实现渐进式加载逻辑：
  - 先加载全量数据，判断是否需要渐进式加载
  - 如果需要，计算"最近窗口"时间范围
  - 加载最近一段数据，立即发送给图表
  - 延迟一小段时间后，发送全量数据（覆盖）
- [ ] 添加日志输出（使用 `[渐进式加载]` 前缀）
- [ ] 处理边界情况（数据为空、数据量小等）

**关键代码片段**:
```python
# 读取配置
progressive_enabled = SETTINGS.get("chart.history.progressive_load.enabled", True)
recent_days = SETTINGS.get("chart.history.progressive_load.recent_days", 3)
recent_bars = SETTINGS.get("chart.history.progressive_load.recent_bars", 200)
progressive_intervals = SETTINGS.get("chart.history.progressive_load.intervals", ["MINUTE"])
min_bars_for_progressive = SETTINGS.get("chart.history.progressive_load.min_bars_for_progressive", 500)

# 判断是否启用渐进式加载
interval_name = interval_enum.value if hasattr(interval_enum, 'value') else str(interval_enum)
should_use_progressive = (
    progressive_enabled and
    interval_name in progressive_intervals and
    data and len(data) >= min_bars_for_progressive
)

# 渐进式加载逻辑
if should_use_progressive:
    recent_window = timedelta(days=recent_days)
    recent_start = max(start, end - recent_window)
    recent_data = database.load_bar_data(symbol, exchange, interval_enum, recent_start, end)
    
    if recent_data and len(recent_data) < recent_bars:
        if len(data) >= recent_bars:
            recent_data = data[-recent_bars:]
    
    if recent_data:
        self.signal_history.emit(recent_data)  # 先发送最近数据
        if len(data) > len(recent_data):
            time.sleep(0.1)  # 延迟100ms
            self.signal_history.emit(data)  # 再发送全量数据
```

---

## ✅ T3: 实现 `_fetch_bars_from_futu` 方法（如果不存在，20分钟）

**文件**: `vnpy/trader/ui/widget.py`  
**位置**: 在 `load_history_data()` 方法之后

**任务**:
- [ ] 检查 `_fetch_bars_from_futu` 方法是否存在
- [ ] 如果不存在，实现该方法（通过 `main_engine.query_history()` 调用FUTU网关）

**代码框架**:
```python
def _fetch_bars_from_futu(
    self,
    symbol: str,
    exchange: "Exchange",
    interval: "Interval",
    start: datetime,
    end: datetime
) -> list:
    """从FUTU API获取K线数据"""
    try:
        from vnpy.trader.object import HistoryRequest
        
        req = HistoryRequest(
            symbol=symbol,
            exchange=exchange,
            interval=interval,
            start=start,
            end=end
        )
        
        gateway_name = "FUTU"  # 或从配置获取
        bars = self.main_engine.query_history(req, gateway_name)
        return bars if bars else []
    except Exception as e:
        self.main_engine.write_log(f"从FUTU API获取K线数据失败: {str(e)}")
        return []
```

---

## ✅ T4: 添加辅助方法（可选，20分钟）

**文件**: `vnpy/trader/ui/widget.py`  
**位置**: 在 `_fetch_bars_from_futu()` 方法之后

**任务**:
- [ ] 实现 `_should_use_progressive_load()` 方法
- [ ] 在 `load_history_data()` 中使用该方法，简化判断逻辑

**代码框架**:
```python
def _should_use_progressive_load(
    self, 
    interval_enum: "Interval", 
    total_bars: int
) -> bool:
    """判断是否应该使用渐进式加载"""
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

---

## ✅ T5: 编写测试用例（30分钟）

**文件**: `tests/chart/test_progressive_loading.py`（新建）

**任务**:
- [ ] 测试渐进式加载启用场景
- [ ] 测试渐进式加载禁用场景
- [ ] 测试不同周期配置
- [ ] 测试小数据量场景（< 500根）
- [ ] 性能测试（首次显示 vs 全量加载）

**测试脚本框架**:
```python
def test_progressive_load_enabled():
    """测试渐进式加载启用"""
    SETTINGS["chart.history.progressive_load.enabled"] = True
    SETTINGS["chart.history.progressive_load.intervals"] = ["MINUTE"]
    
    # 模拟加载大量1分钟数据
    # 验证：先收到最近数据，再收到全量数据

def test_progressive_load_disabled():
    """测试渐进式加载禁用"""
    SETTINGS["chart.history.progressive_load.enabled"] = False
    
    # 模拟加载数据
    # 验证：只收到一次全量数据

def test_small_data():
    """测试小数据量（< 500根）"""
    # 模拟加载少量数据
    # 验证：不启用渐进式加载，直接一次性加载
```

---

## ✅ T6: 更新文档（20分钟）

**文件**: 
- `specs/004-fix-realtime-tick/README.md` 或
- `docs/community/info/chart_widget.md`（如果存在）

**任务**:
- [ ] 说明配置项含义和默认值
- [ ] 提供配置示例（JSON格式）
- [ ] 说明使用场景和效果
- [ ] 添加性能对比数据

---

## 实施顺序建议

1. **T1** → **T2** → **T3**: 先添加配置项，再实现功能，最后实现辅助方法（约90分钟）
2. **T4**: 可选优化，简化代码（约20分钟）
3. **T5**: 测试验证（约30分钟）
4. **T6**: 文档更新（约20分钟）

**总计**: 约2.5-3小时

---

## 验证清单

完成所有任务后，验证以下内容：

- [ ] 配置项已添加到 `setting.py`
- [ ] `load_history_data()` 支持渐进式加载
- [ ] 1分钟数据（>500根）先显示最近3天，再显示全量
- [ ] 5分钟数据（未配置）直接显示全量
- [ ] 小数据量（<500根）直接显示全量
- [ ] 日志输出清晰（`[渐进式加载]` 前缀）
- [ ] 测试用例通过

---

## 配置示例

### 默认配置（推荐）
```json
{
  "chart.history.progressive_load.enabled": true,
  "chart.history.progressive_load.recent_days": 3,
  "chart.history.progressive_load.recent_bars": 200,
  "chart.history.progressive_load.intervals": ["MINUTE"],
  "chart.history.progressive_load.min_bars_for_progressive": 500
}
```

### 禁用渐进式加载
```json
{
  "chart.history.progressive_load.enabled": false
}
```

### 多周期启用
```json
{
  "chart.history.progressive_load.enabled": true,
  "chart.history.progressive_load.recent_days": 3,
  "chart.history.progressive_load.intervals": ["MINUTE", "MINUTE_5", "HOUR"]
}
```

---

## 预期效果

| 场景 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| 1分钟数据（10000根） | 5-10秒 | 首次<1秒 | 首次显示快5-10x |
| 5分钟数据（5000根） | 3-5秒 | 首次<1秒 | 首次显示快3-5x |
| 日线数据（500根） | <1秒 | <1秒 | 无变化 |

---

## 注意事项

1. **数据一致性**: 确保全量数据发送时，图表能正确更新（覆盖最近数据）
2. **线程安全**: `signal_history.emit()` 是线程安全的
3. **配置兼容性**: 如果配置项不存在，使用默认值
4. **性能影响**: 渐进式加载会增加一次数据库查询，但用户体验提升明显

