# Tick延迟诊断方案

## 问题重述

用户观察到：19:26分钟的tick在第44秒才处理（19:26:44），而期望在19:26:00左右就有tick。

## 关键澄清

从日志看，**延迟并不是45秒**！

```
tick业务时间: 19:26:44.930000  (数据源的时间戳)
系统处理时间: 19:26:45.811     (本地接收处理时间)
真实延迟: 0.88秒 ✅ 正常
```

**真正的问题**：为什么19:26分钟的tick在第44秒才到达？

## 两种可能性

### 可能性1：数据源推送延迟（最可能）
- FUTU的tick本身就在第44秒才推送
- 市场数据延迟或推送频率低
- **不是代码问题** ✅

### 可能性2：订阅或路由问题
- tick早就到了，但被延迟处理
- **需要排查代码** ⚠️

## 诊断步骤

### 步骤1：添加性能监控日志

修改 `ChartWindow.process_tick_event()` 添加计时：

```python
def process_tick_event(self, event: Event) -> None:
    import time
    
    tick: TickData = event.data
    recv_timestamp = time.time()  # 系统接收时间
    
    if tick.vt_symbol != self.current_vt_symbol:
        return
    
    # 计算tick从数据源到接收的延迟
    if tick.datetime:
        tick_business_time = tick.datetime.timestamp()
        latency = recv_timestamp - tick_business_time
        
        self.main_engine.write_log(
            f"[Tick延迟] 业务时间: {tick.datetime}, "
            f"接收时间: {datetime.fromtimestamp(recv_timestamp)}, "
            f"延迟: {latency:.3f}秒",
            "ChartWindow"
        )
    
    if self.display_mode == "multi" and self.multi_timeframe_widget:
        route_start = time.perf_counter()
        self.multi_timeframe_widget.update_tick(tick)
        route_end = time.perf_counter()
        
        if (route_end - route_start) > 0.01:  # >10ms
            self.main_engine.write_log(
                f"[性能] update_tick耗时: {(route_end-route_start)*1000:.2f}ms",
                "ChartWindow"
            )
```

### 步骤2：监控数据库查询耗时

修改 `MultiTimeframeWidget.update_tick()` 开盘价修正逻辑：

```python
# 方法2：如果历史数据中没有，尝试从数据库查询
if not correct_open_price:
    try:
        import time
        query_start = time.perf_counter()
        
        from vnpy.trader.database import get_database
        from datetime import timedelta
        
        database = get_database()
        minute_end = bar_minute_start + timedelta(minutes=1)
        db_bars = database.load_bar_data(
            symbol=self._vt_symbol,
            exchange=self._exchange,
            interval=Interval.MINUTE,
            start=bar_minute_start,
            end=minute_end
        )
        
        query_end = time.perf_counter()
        query_time_ms = (query_end - query_start) * 1000
        
        if query_time_ms > 10:  # >10ms
            if hasattr(self, '_main_engine') and self._main_engine:
                self._main_engine.write_log(
                    f"[性能] 开盘价数据库查询耗时: {query_time_ms:.2f}ms"
                )
        
        if db_bars and len(db_bars) > 0:
            correct_open_price = db_bars[0].open_price
```

### 步骤3：对比单周期模式

1. 切换到单周期模式
2. 观察同一合约的tick接收时间
3. 如果单周期也是44秒才有tick，说明是数据源问题

### 步骤4：检查tick推送频率

添加tick计数器：

```python
class MultiTimeframeWidget:
    def __init__(self, ...):
        ...
        self._tick_count_per_minute = {}  # 每分钟的tick计数
        self._current_minute = None
    
    def update_tick(self, tick: TickData) -> None:
        # 统计每分钟的tick数量
        minute_key = tick.datetime.replace(second=0, microsecond=0)
        if minute_key != self._current_minute:
            # 新的一分钟
            if self._current_minute:
                count = self._tick_count_per_minute.get(self._current_minute, 0)
                if hasattr(self, '_main_engine') and self._main_engine:
                    self._main_engine.write_log(
                        f"[Tick统计] {self._current_minute.strftime('%H:%M')} "
                        f"共收到 {count} 个tick"
                    )
            self._current_minute = minute_key
            self._tick_count_per_minute[minute_key] = 0
        
        self._tick_count_per_minute[minute_key] = \
            self._tick_count_per_minute.get(minute_key, 0) + 1
        
        # 继续原有逻辑
        ...
```

## 预期结果

### 如果是数据源问题
```
[Tick延迟] 业务时间: 19:26:44.930000, 接收时间: 19:26:45.811, 延迟: 0.88秒
[Tick统计] 19:26 共收到 1 个tick  # 如果每分钟tick很少
```
**解决方案**：联系数据源供应商，或接受这种延迟

### 如果是代码问题
```
[性能] update_tick耗时: 250.00ms  # 如果处理耗时过长
[性能] 开盘价数据库查询耗时: 200.00ms  # 如果数据库查询慢
```
**解决方案**：优化代码（异步查询、缓存等）

## 快速验证方法

**不修改代码，直接对比**：
1. 打开单周期模式，观察tick时间
2. 打开多周期模式，观察tick时间
3. 如果两者一致 → 数据源问题
4. 如果多周期延迟明显 → 代码问题

## 我的判断

从现有日志看，**最可能是数据源问题**：
- 系统处理延迟只有0.88秒（正常）
- tick的业务时间本身就在44秒
- 代码逻辑简单直接，不应引入45秒延迟

**建议**：
1. 先用单周期对比验证
2. 确认后再决定是否优化代码

