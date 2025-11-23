# IndicatorManager 性能优化指南

## 1. Parquet文件频繁读写性能问题

### 当前实现

- **保存频率**：每100根K线保存一次（`_update_history_indicator` 方法）
- **保存时机**：K线完成时（`is_runtime=False`）
- **压缩格式**：zstd（压缩率高但写入较慢）

### 性能影响分析

#### 1分钟K线场景
- 100根K线 = 100分钟 ≈ 1.67小时
- 每天交易4小时 = 约2.4次保存
- **影响**：相对较小，但实盘交易中仍需注意

#### 5分钟K线场景
- 100根K线 = 500分钟 ≈ 8.3小时
- 每天交易4小时 = 约0.5次保存
- **影响**：较小

### 优化方案

#### 方案1：降低保存频率（推荐）

```python
# 在初始化时设置保存间隔
manager = IndicatorManager(
    vt_symbol="MHImain.HKFE",
    storage_path=None,
    use_database=True
)

# 设置保存间隔（每500根K线保存一次，约8.3小时）
manager._save_interval = 500
```

#### 方案2：异步保存（最佳）

修改 `_update_history_indicator` 方法，使用后台线程异步保存：

```python
import threading
from queue import Queue

class IndicatorManager:
    def __init__(self, ...):
        # ... 现有代码 ...
        self._save_queue = Queue()
        self._save_thread = None
        self._save_interval = 500  # 默认500根K线保存一次
    
    def _start_save_thread(self):
        """启动异步保存线程"""
        if self._save_thread is None or not self._save_thread.is_alive():
            self._save_thread = threading.Thread(target=self._save_worker, daemon=True)
            self._save_thread.start()
    
    def _save_worker(self):
        """异步保存工作线程"""
        while True:
            try:
                interval = self._save_queue.get(timeout=1)
                if interval is None:  # 退出信号
                    break
                self._save_indicator_to_file(interval)
                self._save_queue.task_done()
            except Exception as e:
                self.write_log(f"异步保存失败: {e}")
    
    def _update_history_indicator(self, interval: Interval, bar: BarData):
        # ... 现有更新逻辑 ...
        
        # 异步保存（不阻塞策略执行）
        if len(history_bars) % self._save_interval == 0:
            self._start_save_thread()
            self._save_queue.put(interval)
```

#### 方案3：仅在收盘时保存

```python
# 只在交易日收盘时保存
def _update_history_indicator(self, interval: Interval, bar: BarData):
    # ... 现有更新逻辑 ...
    
    # 只在收盘时保存（例如：15:00）
    if bar.datetime.hour == 15 and bar.datetime.minute == 0:
        self._save_indicator_to_file(interval)
```

#### 方案4：使用更快的压缩算法

```python
# 使用snappy压缩（写入更快，但压缩率较低）
df.write_parquet(filepath, compression="snappy")
```

### 推荐配置

**实盘交易环境**：
- 保存间隔：500-1000根K线
- 压缩格式：snappy（速度优先）或 zstd（空间优先）
- 保存时机：异步保存，避免阻塞策略

**回测环境**：
- 保存间隔：100根K线（默认）
- 压缩格式：zstd（空间优先）

## 2. ArrayManager存储2年数据

### ArrayManager限制

- **默认大小**：100根K线（`size=100`）
- **存储方式**：固定大小的numpy数组，滚动窗口更新
- **内存占用**：约20-30KB（100根K线）

### 2年数据量估算

#### 1分钟K线
- 2年 × 250交易日/年 × 240分钟/天 = **120,000根**
- ArrayManager只能存储 **100根**（0.08%）

#### 5分钟K线
- 2年 × 250交易日/年 × 48分钟/天 = **24,000根**
- ArrayManager只能存储 **100根**（0.42%）

### 结论

**ArrayManager无法存储2年数据**，它只适合：
- 短期技术指标计算（MA、RSI等）
- 需要最近N根K线的指标（N ≤ 100）

### 解决方案

#### 方案1：使用IndicatorManager（推荐）

`IndicatorManager` 专门设计用于长期历史数据：

```python
# 支持存储2年数据
manager = IndicatorManager(
    vt_symbol="MHImain.HKFE",
    storage_path=None,
    use_database=True
)

# 注册指标，设置max_history=50000（可存储约2年1分钟K线）
manager.register_indicator(
    interval=Interval.MINUTE,
    indicator_name="custom_wma",
    calculator=my_indicator,
    max_history=50000  # 约2年数据
)

# 初始化时加载2年历史数据
manager.initialize_indicators(Interval.MINUTE, days=730, database=database)
```

**内存占用估算**：
- 每个指标值：8字节（float64）
- 50000个值：400KB
- 10个指标：4MB
- **结论**：内存占用很小，完全可接受

#### 方案2：增大ArrayManager大小（不推荐）

```python
# 不推荐：内存占用过大
am = ArrayManager(size=50000)  # 需要约40MB内存
```

**问题**：
- 内存占用大（40MB+）
- 滚动更新性能下降
- 不适合实盘交易

#### 方案3：混合使用

```python
# 短期指标用ArrayManager（快速计算）
self.am = ArrayManager(size=100)  # MA、RSI等

# 长期指标用IndicatorManager（历史数据）
self.indicator_manager = IndicatorManager(...)  # 自定义指标
```

### 内存占用对比

| 方案 | 数据量 | 内存占用 | 适用场景 |
|------|--------|----------|----------|
| ArrayManager (默认) | 100根 | ~30KB | 短期指标（MA、RSI） |
| ArrayManager (增大) | 50000根 | ~40MB | 不推荐 |
| IndicatorManager | 50000根 | ~4MB | 长期自定义指标 |

### 推荐配置

**实盘交易**：
- 短期指标（MA、RSI、MACD等）：使用 `ArrayManager(size=100)`
- 长期自定义指标：使用 `IndicatorManager`，`max_history=10000-50000`
- 保存频率：500-1000根K线，异步保存

**回测环境**：
- 短期指标：`ArrayManager(size=100)`
- 长期指标：`IndicatorManager`，`max_history=50000+`
- 保存频率：100根K线（默认）

## 3. 性能优化最佳实践

### 实盘交易配置

```python
class MyStrategy(CtaTemplate):
    def on_init(self):
        # 短期指标：ArrayManager
        self.am = ArrayManager(size=100)
        
        # 长期指标：IndicatorManager
        self.indicator_manager = IndicatorManager(
            vt_symbol=self.vt_symbol,
            storage_path=None,
            use_database=True,
            storage_format="parquet"  # 或 "pkl"（更快）
        )
        
        # 设置保存间隔（500根K线，约8.3小时）
        self.indicator_manager._save_interval = 500
        
        # 注册指标
        self.indicator_manager.register_indicator(
            interval=Interval.MINUTE,
            indicator_name="custom_wma",
            calculator=self._calculate_wma,
            max_history=10000  # 约2个月数据
        )
        
        # 初始化（加载历史数据）
        database = self.cta_engine.database
        self.indicator_manager.initialize_indicators(
            Interval.MINUTE,
            days=60,  # 加载2个月历史数据
            database=database
        )
    
    def on_bar(self, bar: BarData):
        # 更新ArrayManager（快速）
        self.am.update_bar(bar)
        
        # 更新IndicatorManager（增量计算）
        self.indicator_manager.update_indicator(
            Interval.MINUTE,
            bar,
            is_runtime=False
        )
        
        # 获取指标值
        ma_short = self.am.sma(10)  # ArrayManager
        custom_wma = self.indicator_manager.get_indicator(
            Interval.MINUTE,
            "custom_wma",
            index=-1
        )  # IndicatorManager
```

### 性能监控

```python
import time

def on_bar(self, bar: BarData):
    start_time = time.time()
    
    # 更新指标
    self.indicator_manager.update_indicator(...)
    
    elapsed = time.time() - start_time
    if elapsed > 0.01:  # 超过10ms记录警告
        self.write_log(f"指标更新耗时: {elapsed*1000:.2f}ms")
```

## 总结

1. **Parquet文件读写**：
   - 实盘交易：降低保存频率（500-1000根K线），使用异步保存
   - 回测环境：默认100根K线即可

2. **ArrayManager存储能力**：
   - 无法存储2年数据（只能存储100根）
   - 使用 `IndicatorManager` 存储长期数据
   - 内存占用很小（50000根数据约4MB）

3. **推荐方案**：
   - 短期指标：`ArrayManager(size=100)`
   - 长期指标：`IndicatorManager(max_history=10000-50000)`
   - 保存策略：异步保存，降低频率

