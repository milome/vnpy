# Bug修复：DataManager参数错误

## 问题

多周期数据下载时报错：

```
TypeError: ManagerEngine.download_bar_data() got an unexpected keyword argument 'vt_symbol'. 
Did you mean 'symbol'?
```

## 原因

在 `_download_from_futu()` 方法中，调用 `DataManager.download_bar_data()` 时使用了错误的参数名：

```python
# ❌ 错误：使用 vt_symbol
success = datamanager_engine.download_bar_data(
    vt_symbol=vt_symbol,  # 错误参数名
    exchange=exchange,
    interval=Interval.MINUTE,
    start=start,
    end=end
)
```

**DataManager.download_bar_data()** 的正确参数是 `symbol`（不带交易所后缀），不是 `vt_symbol`。

## 修复

修改参数名从 `vt_symbol` 到 `symbol`：

```python
# ✅ 正确：使用 symbol
success = datamanager_engine.download_bar_data(
    symbol=symbol,  # 正确参数名
    exchange=exchange,
    interval=Interval.MINUTE,
    start=start,
    end=end
)
```

## 修改内容

**文件**：`vnpy/chart/multi_timeframe_widget.py`

**方法**：`_download_from_futu()`（第348-355行）

**修改**：
- 删除了构造 `vt_symbol` 的代码（不需要）
- 参数从 `vt_symbol=vt_symbol` 改为 `symbol=symbol`

## 注意

`_download_from_futu()` 方法接收的参数 `symbol` 已经是不带交易所后缀的合约代码（例如 "MHImain"），所以直接传递给 `DataManager` 即可。

## 总结

✅ 参数名称修正
✅ 删除不必要的 vt_symbol 构造代码

修复完成！🎉

