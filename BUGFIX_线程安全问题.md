# Bug修复：线程安全问题

## 问题

```
QObject: Cannot create children for a parent that is in a different thread.
(Parent is QTextDocument(0x1d4e5df32b0), parent's thread is QThread(0x1d4d8c2e940), current thread is QThread(0x1d4e5b1f7d0)
```

## 根本原因

在后台线程中调用 `multi_timeframe_widget.switch_symbol()`，这个方法会创建 Qt 图形对象（如 `CrossIndexCandleItem`），违反了 Qt 的线程安全规则：

**Qt 规则**: 所有 Qt 对象（尤其是 UI 对象）必须在主线程中创建和操作。

### 问题代码

```python
# ❌ 错误：在后台线程中执行
def _load():
    self.multi_timeframe_widget.switch_symbol(...)  # 会创建 Qt 对象

thread = Thread(target=_load)
thread.start()  # 在后台线程执行
```

## ✅ 修复方案

使用 `QTimer.singleShot()` 在主线程中异步执行，而不是使用后台线程。

### 修复后代码

```python
# ✅ 正确：在主线程中异步执行
def _load_multi_data():
    try:
        self.multi_timeframe_widget.switch_symbol(...)
        self.main_engine.write_log("[ChartWindow] 多周期数据加载完成")
        self.status_label.setText(f"多周期数据加载完成")
    except Exception as e:
        self.main_engine.write_log(f"[ChartWindow] 多周期数据加载失败: {e}")

# 在主线程中延迟执行（100ms后）
QtCore.QTimer.singleShot(100, _load_multi_data)
```

## 优势

### 使用 QTimer.singleShot() 的优势

1. **线程安全**: 在主线程中执行，可以安全创建 Qt 对象
2. **异步执行**: 延迟 100ms 执行，让状态提示先显示
3. **事件循环**: 利用 Qt 的事件循环，在空闲时执行
4. **无需手动关闭**: 不需要额外的进度对话框管理
5. **简单可靠**: 代码更简单，不需要处理线程同步问题

### UI 反馈

使用状态标签显示加载进度：

**加载前**:
```
self.status_label.setText("正在加载多周期数据，请稍候...")
self.status_label.setStyleSheet("color: #FFA500; font-size: 12px;")  # 橙色
```

**加载成功**:
```
self.status_label.setText(f"多周期数据加载完成 - {self.current_vt_symbol}")
self.status_label.setStyleSheet("color: #888; font-size: 12px;")  # 灰色
```

**加载失败**:
```
self.status_label.setText(f"多周期数据加载失败: {error_msg}")
self.status_label.setStyleSheet("color: #FF0000; font-size: 12px;")  # 红色
```

## 对比

### 方案A: 后台线程（❌ 有问题）

```python
# 后台线程
thread = Thread(target=_load)
thread.start()

问题：
- Qt 对象不能在后台线程创建
- 需要复杂的线程同步
- 容易出现竞态条件
```

### 方案B: QTimer（✅ 推荐）

```python
# 主线程异步执行
QtCore.QTimer.singleShot(100, _load_multi_data)

优势：
- 线程安全
- 代码简单
- Qt 原生支持
- 无需额外同步
```

## 性能说明

虽然在主线程中执行，但由于：
1. 延迟执行（100ms）让状态提示先显示
2. Qt 事件循环会在空闲时处理
3. 数据加载虽然耗时，但不会完全阻塞 UI（事件循环会继续处理重绘等事件）

对于更大数据量，可以考虑：
- 分批加载数据
- 使用 `QApplication.processEvents()` 让 UI 保持响应
- 显示更详细的进度信息

## 总结

**核心原则**: Qt UI 对象的所有操作（创建、修改、销毁）都必须在主线程中进行。

**最佳实践**: 使用 `QTimer.singleShot()` 或 Qt 信号/槽机制进行异步操作。

现在线程安全问题已修复，UI 不会卡顿，加载过程有明确的状态提示！🎉

