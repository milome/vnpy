# 今日修复总结 (2025-12-04)

## 修复列表

### 1. ✅ 时区不一致问题
**文件**：`vnpy/chart/multi_timeframe_widget.py`
**问题**：`can't subtract offset-naive and offset-aware datetimes`
**修复**：
- 在 `_check_data_completeness()` 中添加时区统一处理
- 使用 `SETTINGS.get("database.timezone")` 获取数据库时区
- 使用 `database_tz.localize()` 和 `astimezone()` 统一转换所有 datetime
**影响**：数据完整性检查不再出现时区错误

### 2. ✅ 除零错误
**文件**：`vnpy/chart/price_line_drag.py`
**问题**：`ZeroDivisionError: float division by zero`
**修复**：
- 在第110行添加 `y_height > 0` 检查
- 条件从 `if plot_height > 0:` 改为 `if plot_height > 0 and y_height > 0:`
**影响**：鼠标移动时不再出现除零错误

### 3. ✅ DataManager 参数错误（vt_symbol）
**文件**：`vnpy/chart/multi_timeframe_widget.py`
**问题**：`got an unexpected keyword argument 'vt_symbol'`
**修复**：
- `_download_from_futu()` 方法中参数从 `vt_symbol=vt_symbol` 改为 `symbol=symbol`
- 移除构造 vt_symbol 的代码
**影响**：DataManager 下载不再出现参数错误

### 4. ✅ 移除 FUTU Gateway 备用方案
**文件**：`vnpy/chart/multi_timeframe_widget.py`
**原因**：DRY 原则，如果 DataManager 失败，FUTU API 一定不可用
**修复**：
- 移除 `_download_from_futu()` 方法中的备用方案（约35行）
- 移除 `_download_minute_bars_from_futu()` 方法中的备用方案（约75行）
- 只使用 DataManager，不直接调用 FUTU Gateway
**影响**：代码减少约110行，逻辑更清晰

### 5. ✅ DataManager 参数错误（end）
**文件**：`vnpy/chart/multi_timeframe_widget.py`
**问题**：`got an unexpected keyword argument 'end'`
**修复**：
- `_download_from_futu()` 方法中移除 `end=end` 参数
- 添加 `output=lambda msg: logger.info(f"[DataManager] {msg}")` 回调
**影响**：符合 DataManager API 规范

### 6. ✅ 挂单止损止盈线关联检查修复
**文件**：`vnpy/chart/widget.py`
**问题**：关闭画线下单时挂单止损止盈线被误删
**修复**：
- `_cleanup_pending_stop_profit_lines()` 中正确检查挂单关联
- 从 `_pending_line_relations` 字典查找关联，而不是检查 `pending_line_id` 属性（不存在）
**影响**：关闭画线下单时，挂单止损止盈线正确保留

### 7. ✅ pending_line_id 属性访问错误
**文件**：`vnpy/chart/widget.py`
**问题**：`AttributeError: 'PriceLineItem' object has no attribute 'pending_line_id'`
**修复**：
- 日志输出从 `f"关联挂单线={line.pending_line_id}"` 改为 `"关联挂单线"`
- 不访问不存在的属性
**影响**：日志输出不再报错

### 8. ✅ 关闭画线下单不删除挂单止损止盈线
**文件**：`vnpy/chart/drawing_order.py`
**问题**：关闭画线下单时挂单止损止盈线被删除
**修复**：
- `disable()` 方法中只清理预览线
- 添加注释说明不删除挂单止损止盈线
**影响**：用户设置的交易辅助线正确保留

## 代码质量提升

- ✅ 减少约 110 行重复代码
- ✅ 遵循 DRY 原则
- ✅ 时区处理正确
- ✅ 防御性编程（除零检查）
- ✅ API 参数使用正确

## 测试建议

建议测试以下场景：

1. **多周期数据加载**：
   - 选择2个月前的起始时间
   - 点击"加载"
   - 切换到"多周期叠加"
   - 验证数据正确显示，无时区错误

2. **挂单止损止盈线保留**：
   - 多周期模式
   - 开启画线下单
   - 创建多单挂单（带止损止盈）
   - 关闭画线下单
   - 验证挂单止损止盈线保留
   - 模拟成交后验证止损止盈线正确激活

3. **鼠标移动无错误**：
   - 在图表上移动鼠标
   - 验证无除零错误

## 文件变更统计

- `vnpy/chart/multi_timeframe_widget.py`：+约30行，-约110行
- `vnpy/chart/price_line_drag.py`：+1行
- `vnpy/chart/widget.py`：+约20行
- `vnpy/chart/drawing_order.py`：+4行（注释）

**净减少约 55 行代码，质量提升！** 🎉

