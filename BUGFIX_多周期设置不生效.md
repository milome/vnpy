# Bug修复：多周期设置不生效

## 问题

用户反馈：多周期设置中的 checkbox 不选择，对应周期还是显示出来。

例如：
- 取消勾选"显示 5m"
- 5分钟K线仍然显示在图表上

## 根本原因

在 `MultiTimeframeWidget` 中：

### 问题1：创建图表项时未应用可见性设置

```python
# ❌ 旧代码：创建后没有设置可见性
candle_item_5m = CrossIndexCandleItem(...)
self._chart.add_item(candle_item_5m, 0)
# 没有调用 setVisible()
```

**结果**：所有周期的K线默认都是可见的，不管设置如何

### 问题2：更新设置时未更新可见性

```python
# ❌ 旧代码：只更新透明度，没有更新可见性
def update_settings(settings):
    self._candle_item_5m.set_bearish_fill_opacity(settings.fill_opacity_5m)
    # 没有调用 setVisible(settings.show_5m)
```

**结果**：修改设置后，可见性不会改变

## 修复方案

### 修复1：创建图表项时应用可见性设置

```python
# ✅ 新代码：创建后立即应用可见性
candle_item_5m = CrossIndexCandleItem(...)
# 根据设置控制初始可见性
candle_item_5m.setVisible(self._settings.show_5m)
self._chart.add_item(candle_item_5m, 0)
logger.info(f"[多周期] 5分钟K线初始可见性: {self._settings.show_5m}")
```

### 修复2：更新设置时同时更新可见性

```python
# ✅ 新代码：同时更新透明度和可见性
def update_settings(settings):
    if self._candle_item_5m:
        # 更新透明度
        self._candle_item_5m.set_bearish_fill_opacity(settings.fill_opacity_5m)
        # 更新可见性
        self._candle_item_5m.setVisible(settings.show_5m)
        logger.info(f"[多周期] 5分钟K线可见性: {settings.show_5m}")
```

## 修改内容

### 文件：vnpy/chart/multi_timeframe_widget.py

**修改位置1**：`_load_data_and_build_items()` 方法 - 创建图表项时

```python
# 创建5分钟K线图表项
if five_minute_bars:
    candle_item_5m = CrossIndexCandleItem(...)
    # ✅ 根据设置控制初始可见性
    candle_item_5m.setVisible(self._settings.show_5m)
    self._chart.add_item(candle_item_5m, 0)
    self._candle_item_5m = candle_item_5m
    logger.info(f"[多周期] 5分钟K线初始可见性: {self._settings.show_5m}")

# 创建1小时K线图表项
if one_hour_bars:
    candle_item_1h = CrossIndexCandleItem(...)
    # ✅ 根据设置控制初始可见性
    candle_item_1h.setVisible(self._settings.show_1h)
    self._chart.add_item(candle_item_1h, 0)
    self._candle_item_1h = candle_item_1h
    logger.info(f"[多周期] 1小时K线初始可见性: {self._settings.show_1h}")

# 创建4小时K线图表项
if four_hour_bars:
    candle_item_4h = CrossIndexCandleItem(...)
    # ✅ 根据设置控制初始可见性
    candle_item_4h.setVisible(self._settings.show_4h)
    self._chart.add_item(candle_item_4h, 0)
    self._candle_item_4h = candle_item_4h
    logger.info(f"[多周期] 4小时K线初始可见性: {self._settings.show_4h}")
```

**修改位置2**：`update_settings()` 方法 - 更新设置时

```python
def update_settings(self, settings: MultiTimeframeSettings) -> None:
    """更新设置并重新绘制"""
    self._settings = settings
    
    # 更新透明度和可见性
    if self._candle_item_5m:
        self._candle_item_5m.set_bearish_fill_opacity(settings.fill_opacity_5m)
        # ✅ 根据设置控制可见性
        self._candle_item_5m.setVisible(settings.show_5m)
        logger.info(f"[多周期] 5分钟K线可见性: {settings.show_5m}")
    
    if self._candle_item_1h:
        self._candle_item_1h.set_bearish_fill_opacity(settings.fill_opacity_1h)
        # ✅ 根据设置控制可见性
        self._candle_item_1h.setVisible(settings.show_1h)
        logger.info(f"[多周期] 1小时K线可见性: {settings.show_1h}")
    
    if self._candle_item_4h:
        self._candle_item_4h.set_bearish_fill_opacity(settings.fill_opacity_4h)
        # ✅ 根据设置控制可见性
        self._candle_item_4h.setVisible(settings.show_4h)
        logger.info(f"[多周期] 4小时K线可见性: {settings.show_4h}")
    
    # 重绘
    self._chart.update()
```

## 设置对话框的工作流程

```
用户打开"多周期设置"对话框:
  ↓
MultiTimeframeSettingsDialog.show()
  - 显示当前设置
  - 显示 checkbox: 显示5m / 显示1H / 显示4H
  - 显示透明度滑块
  ↓
用户修改设置:
  - 取消勾选"显示 5m"
  - 调整透明度
  ↓
用户点击"确定":
  dialog.accept()
  → 调用 MultiTimeframeWidget.update_settings(new_settings)
  ↓
update_settings() 应用新设置:
  1. 更新透明度: candle_item_5m.set_bearish_fill_opacity(...)
  2. 更新可见性: candle_item_5m.setVisible(False)  # ✅ 现在会隐藏
  3. 重绘图表: self._chart.update()
  ↓
结果:
  ✅ 5分钟K线被隐藏
  ✅ 其他周期按设置显示/隐藏
```

## 测试场景

### 场景1：初始加载时应用设置

```
操作:
  1. 打开"多周期设置"
  2. 取消勾选"显示 5m"
  3. 点击"确定"
  4. 加载多周期数据

预期结果:
  - ✅ 5分钟K线不显示
  - ✅ 1小时和4小时K线按设置显示
  
预期日志:
  [多周期] 5分钟K线初始可见性: False
  [多周期] 1小时K线初始可见性: True
  [多周期] 4小时K线初始可见性: True
```

### 场景2：动态修改设置

```
操作:
  1. 加载多周期数据（所有周期都显示）
  2. 打开"多周期设置"
  3. 取消勾选"显示 1H"
  4. 点击"确定"

预期结果:
  - ✅ 1小时K线立即隐藏
  - ✅ 其他周期仍然显示
  
预期日志:
  [多周期] 1小时K线可见性: False
```

### 场景3：修改透明度

```
操作:
  1. 加载多周期数据
  2. 打开"多周期设置"
  3. 调整"5m 阴线填充透明度"到 20%
  4. 点击"确定"

预期结果:
  - ✅ 5分钟K线透明度改变
  - ✅ 5分钟K线仍然可见（如果勾选了"显示 5m"）
```

### 场景4：全部隐藏

```
操作:
  1. 加载多周期数据
  2. 打开"多周期设置"
  3. 取消勾选所有"显示"选项
  4. 点击"确定"

预期结果:
  - ✅ 只显示1分钟K线
  - ✅ 5m/1H/4H 全部隐藏
  
注意:
  - 1分钟K线始终显示（作为基础）
  - 不受"显示"设置影响
```

## PyQt 可见性控制

### `setVisible()` 方法

```python
# QGraphicsItem.setVisible(visible: bool)
# - visible = True: 显示图表项
# - visible = False: 隐藏图表项（但不删除）

candle_item.setVisible(True)   # 显示
candle_item.setVisible(False)  # 隐藏
```

**优势**：
- 不需要从场景中删除和重新添加
- 性能好
- 状态保持（数据仍在内存中）

### 与 `removeItem()` 的对比

```python
# 方案1：使用 setVisible()（推荐）✅
candle_item.setVisible(False)  # 隐藏
candle_item.setVisible(True)   # 再次显示（数据还在）

# 方案2：使用 removeItem()（不推荐）❌
scene.removeItem(candle_item)  # 删除
scene.addItem(candle_item)     # 需要重新添加
```

**为什么使用 `setVisible()`**：
- 更简单
- 性能更好
- 不需要重新管理图表项

## 总结

**核心修复**：
- ✅ 创建图表项时应用初始可见性
- ✅ 更新设置时同时更新可见性
- ✅ 使用 `setVisible()` 控制显示/隐藏

**关键点**：
- 1分钟K线始终显示（作为基础）
- 5m/1H/4H K线根据设置控制可见性
- 设置实时生效（无需重新加载数据）

修复完成！🎉

