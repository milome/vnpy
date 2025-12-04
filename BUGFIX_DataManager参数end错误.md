# Bug修复：DataManager参数错误（end参数）

## 问题

```
TypeError: ManagerEngine.download_bar_data() got an unexpected keyword argument 'end'
```

## 原因

`DataManager.download_bar_data()` 的方法签名不包含 `end` 参数：

```python
def download_bar_data(
    self,
    symbol: str,
    exchange: Exchange,
    interval: Interval | str,
    start: datetime,
    output: Callable  # ✅ 不是 end，是 output 回调函数
) -> int:
```

## 修复

### 修改前

```python
success = datamanager_engine.download_bar_data(
    symbol=symbol,
    exchange=exchange,
    interval=Interval.MINUTE,
    start=start,
    end=end  # ❌ 错误参数
)
```

### 修改后

```python
success = datamanager_engine.download_bar_data(
    symbol=symbol,
    exchange=exchange,
    interval=Interval.MINUTE,
    start=start,
    output=lambda msg: logger.info(f"[DataManager] {msg}")  # ✅ 正确参数
)
```

## 说明

`DataManager.download_bar_data()` 的行为：
- 从 `start` 时间下载到**当前时间**
- 不需要指定 `end` 参数
- 需要提供 `output` 回调函数用于进度输出

## 修改内容

**文件**：`vnpy/chart/multi_timeframe_widget.py`

**方法**：`_download_from_futu()`（第351-361行）

**关键改进**：
1. 移除 `end=end` 参数
2. 添加 `output=lambda msg: logger.info(f"[DataManager] {msg}")` 回调
3. 日志信息从 "下载 start ~ end" 改为 "下载 start 至今"

## 总结

✅ 参数修正
✅ 添加正确的 output 回调
✅ 符合 DataManager API 规范

修复完成！🎉

