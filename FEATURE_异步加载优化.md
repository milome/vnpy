# 功能优化：多周期数据异步加载与进度显示

## 实现内容

### 1. 进度对话框类 `MultiTimeframeLoadProgressDialog`

借鉴 DataManager 的设计，创建了专用的进度对话框：

**特点**：
- ✅ 进度条显示 0-100% 的加载进度
- ✅ 状态标签显示当前操作（如"正在加载1分钟数据..."）
- ✅ 消息列表显示详细的加载日志（带时间戳）
- ✅ 自动滚动到最新消息
- ✅ 完成时显示绿色"✅ 加载完成！"
- ✅ 失败时显示红色"❌ 加载失败"

### 2. 进度回调机制

在 `MultiTimeframeWidget.switch_symbol()` 和 `_load_data_and_build_items()` 方法中添加进度回调参数：

```python
def switch_symbol(
    self,
    vt_symbol: str,
    exchange: Exchange,
    start: datetime,
    end: datetime,
    progress_callback=None  # 进度回调函数
) -> None:
    if progress_callback:
        progress_callback("正在清理旧数据...", 5)
    
    self._cleanup_data()
    
    self._load_data_and_build_items(progress_callback)
    
    if progress_callback:
        progress_callback("加载完成！", 100)
```

### 3. 详细的进度更新

在数据加载的每个阶段都更新进度：

| 进度 | 操作 | 消息 |
|------|------|------|
| 5% | 清理旧数据 | "正在清理旧数据..." |
| 10% | 开始加载 | "正在加载1分钟K线数据..." |
| 20% | 1m数据完成 | "1分钟数据加载完成: XXXX 条" |
| 30% | 开始5m | "正在加载5分钟K线数据..." |
| 45% | 5m数据完成 | "5分钟数据加载完成: XXX 条" |
| 55% | 开始1H | "正在加载1小时K线数据..." |
| 70% | 1H数据完成 | "1小时数据加载完成: XXX 条" |
| 75% | 开始4H | "正在加载4小时K线数据..." |
| 85% | 4H数据完成 | "4小时数据加载完成: XXX 条" |
| 88% | 创建图表项 | "正在创建图表项..." |
| 90% | 更新1m图表 | "正在更新1分钟图表..." |
| 91-99% | 创建各周期图表项 | "5分钟/1小时/4小时图表项创建完成" |
| 98% | 实时更新初始化 | "正在重新初始化实时更新..." |
| 100% | 完成 | "加载完成！" |

### 4. ChartWindow 集成

在 `sync_data_to_multi_timeframe()` 方法中集成进度对话框：

```python
# 创建并显示进度对话框
progress = MultiTimeframeLoadProgressDialog(self)
progress.show()
QtWidgets.QApplication.processEvents()

# 定义进度回调
def on_progress(message: str, progress_value: int):
    progress.set_status(message)
    progress.set_progress(progress_value)

# 异步执行加载
def _load_multi_data():
    try:
        self.multi_timeframe_widget.switch_symbol(
            vt_symbol=symbol,
            exchange=exchange,
            start=start_datetime,
            end=end_datetime,
            progress_callback=on_progress  # 传入进度回调
        )
        progress.set_completed()
        # 延迟800ms关闭，让用户看到完成状态
        QtCore.QTimer.singleShot(800, progress.close)
    except Exception as e:
        progress.set_error(f"加载失败: {e}")
        QtCore.QTimer.singleShot(3000, progress.close)

# 延迟50ms执行，确保进度对话框先显示
QtCore.QTimer.singleShot(50, _load_multi_data)
```

## 线程安全说明

### 为什么不使用后台线程？

Qt UI 对象（`QGraphicsItem`、`QTextDocument` 等）只能在主线程中创建和操作。`MultiTimeframeWidget.switch_symbol()` 会创建：
- `CrossIndexCandleItem` (QGraphicsItem)
- `BarManager`
- `ChartWidget` 更新

**如果在后台线程执行**：
```
❌ QObject: Cannot create children for a parent that is in a different thread.
```

### 解决方案：QTimer.singleShot()

使用 `QTimer.singleShot()` 在主线程中延迟执行：
- ✅ 线程安全（在主线程执行）
- ✅ 非阻塞（通过事件循环异步执行）
- ✅ 简单可靠（Qt 原生支持）

### 保持 UI 响应

在每个进度更新点调用：
```python
if progress_callback:
    progress_callback("消息", 进度值)
    # progress_callback 内部会调用 processEvents()
```

## 使用效果

### 用户体验流程

1. **切换到多周期模式**
   - 选择"模式: 多周期叠加"
   - 立即弹出进度对话框

2. **加载过程（1-2秒）**
   ```
   ┌──────────────────────────────────┐
   │ 多周期数据加载                    │
   ├──────────────────────────────────┤
   │ 正在加载5分钟K线数据...           │
   │ ████████████░░░░░░░░ 45%        │
   │                                  │
   │ 加载详情:                        │
   │ ┌────────────────────────────┐ │
   │ │ [04:06:22] 开始加载多周期数据 │ │
   │ │ [04:06:22] 正在清理旧数据... │ │
   │ │ [04:06:22] 正在加载1分钟数据 │ │
   │ │ [04:06:23] 1分钟数据: 41280条│ │
   │ │ [04:06:23] 正在加载5分钟数据 │ │
   │ └────────────────────────────┘ │
   └──────────────────────────────────┘
   ```

3. **加载完成**
   - 进度条 100%
   - 状态显示"✅ 加载完成！"
   - 800ms 后自动关闭
   - 显示多周期K线

### 日志输出

```
[ChartWindow] 准备加载多周期数据 - symbol: MHImain, exchange: HKFE
[多周期] _load_data_and_build_items 开始执行
[多周期] 1分钟K线数据加载完成，数量: 41280
[多周期] 5分钟数据加载完成: 8256 条
[多周期] 1小时数据加载完成: 1377 条
[多周期] 4小时数据加载完成: 345 条
[ChartWindow] 多周期数据加载完成
```

## 性能优化

### 当前性能

- **数据量**: 41280 条 1分钟数据（约 1个月）
- **加载时间**: 1-2 秒
- **UI 响应**: 通过 `processEvents()` 保持响应
- **内存**: 合理（分批处理）

### 未来优化方向

1. **数据缓存**: 缓存已加载的数据，避免重复加载
2. **增量更新**: 只加载新增数据，而不是全量重新加载
3. **分批渲染**: 将大量数据分批添加到图表
4. **虚拟化**: 只渲染可见区域的K线

## 总结

通过借鉴 DataManager 的设计，实现了：
- ✅ 专业的进度对话框
- ✅ 详细的加载进度反馈
- ✅ 线程安全的异步加载
- ✅ 良好的用户体验

现在多周期数据加载过程清晰、流畅、可控！🎉

