# Bug修复：多周期模式下画线不显示

## 问题

多周期显示模式下，画线下单的挂单线及关联的止损线止盈线都不显示。

## 根本原因分析

经过代码审查，可能的原因包括：

1. **vt_symbol 参数传递问题**: symbol vs vt_symbol 格式混淆
2. **DrawingOrderController 参数未正确设置**: 在模式切换或画线启用时参数丢失
3. **价格线添加到错误的图表**: 可能添加到单周期图表而不是多周期图表

## 已添加的修复

### 修复1: 数据加载参数修正

**问题**: `sync_data_to_multi_timeframe()` 传入的是 vt_symbol 而不是 symbol

**修复**: 
```python
# 在 ChartWindow.sync_data_to_multi_timeframe() 中
symbol, exchange = extract_vt_symbol(self.current_vt_symbol)

self.multi_timeframe_widget.switch_symbol(
    vt_symbol=symbol,  # ← 使用 symbol（不带交易所后缀）
    exchange=exchange,
    ...
)
```

### 修复2: 添加详细调试日志

在以下位置添加了详细日志：

#### A. `MultiTimeframeWidget.enable_drawing_order()`

```python
print(f"\n[MultiTimeframeWidget] enable_drawing_order 被调用:")
print(f"  main_engine: {main_engine}")
print(f"  vt_symbol: {vt_symbol}")
print(f"  controller._vt_symbol: {getattr(controller, '_vt_symbol', 'NOT SET')}")
```

#### B. `ChartWindow.toggle_drawing_mode()`

```python
print(f"\n[ChartWindow] toggle_drawing_mode (多周期模式)")
print(f"  current_vt_symbol: {self.current_vt_symbol}")
print(f"  controller._vt_symbol = {getattr(controller, '_vt_symbol', 'NOT SET')}")
```

### 修复3: 在画线时重新设置参数

**问题**: 即使在 `enable_drawing_order()` 设置了参数，可能在后续被清空

**修复**: 在 `toggle_drawing_mode()` 中重新设置参数

```python
def toggle_drawing_mode(self):
    if self.display_mode == "multi":
        chart_widget = self.multi_timeframe_widget._chart
        
        # 重新设置参数，确保正确
        chart_widget.set_main_engine(self.main_engine)
        chart_widget.set_vt_symbol(self.current_vt_symbol)
        
        controller = chart_widget.get_drawing_order_controller()
        if controller:
            # 确保 controller 也设置了参数
            controller.set_vt_symbol(self.current_vt_symbol)
            controller.set_main_engine(self.main_engine)
```

## 测试步骤

### 步骤1: 重新启动程序

```bash
cd D:\Dev\vnpy-007-multi-timeframe-integration
update_and_run_worktree.bat
```

### 步骤2: 加载数据并切换到多周期

1. 打开K线图表
2. 输入合约：`MHImain.HKFE`
3. 点击"查询历史"
4. 选择"多周期叠加"模式

**查看日志**，应该看到：
```
[ChartWindow] 同步数据到多周期模式 - 合约: MHImain.HKFE, 数据量: 1000
[ChartWindow] 调用 MultiTimeframeWidget.switch_symbol() - symbol: MHImain, ...
[MultiTimeframeWidget] enable_drawing_order 被调用:
  vt_symbol: MHImain.HKFE  ← 完整的vt_symbol
  controller._vt_symbol: MHImain.HKFE  ← 应该有值
```

### 步骤3: 启用画线模式

点击"画线下单"按钮

**查看日志**，应该看到：
```
[ChartWindow] toggle_drawing_mode (多周期模式)
  current_vt_symbol: MHImain.HKFE
  设置 chart_widget 参数...
  设置 controller.vt_symbol: MHImain.HKFE
  设置 controller.main_engine
  验证: controller._vt_symbol = MHImain.HKFE  ← 应该有值
  验证: controller._main_engine = <MainEngine...>  ← 应该有值
[ChartWindow] 启用画线模式...
[ChartWindow] 画线模式已启用
[画线下单] 多周期模式：画线下单模式已启用
```

### 步骤4: 在图表上画线

在图表上拖动鼠标画线

**预期行为**:
1. 应该看到**预览线**（虚线）
2. 松开鼠标后弹出**挂单参数对话框**
3. 填写参数并确认
4. 应该在图表上显示**挂单线**（带箭头标记）
5. 如果设置了止损止盈，应该显示**止损线**和**止盈线**

### 步骤5: 检查日志

如果画线后没有显示，查看日志中是否有：

**正常日志**:
```
[DrawingOrderController] 开始画线
[DrawingOrderController] 画线完成
[PriceLineManager] 添加价格线: line_xxx
[ChartWindow] 创建挂单线: MHImain.HKFE BUY 1@25800
```

**异常日志**:
```
[DrawingOrderController] vt_symbol 未设置  ← 问题！
[PriceLineManager] 无法添加价格线  ← 问题！
ERROR: controller._vt_symbol = NOT SET  ← 问题！
```

## 如果问题仍然存在

### 诊断方法

在启用画线模式后，在Python控制台执行：

```python
# 获取多周期图表
chart = chart_window.multi_timeframe_widget._chart

# 检查 vt_symbol
print(f"chart._vt_symbol: {getattr(chart, '_vt_symbol', 'NOT SET')}")

# 检查 controller
controller = chart.get_drawing_order_controller()
print(f"controller: {controller}")
print(f"controller._vt_symbol: {getattr(controller, '_vt_symbol', 'NOT SET')}")
print(f"controller._main_engine: {getattr(controller, '_main_engine', 'NOT SET')}")
print(f"controller.is_enabled(): {controller.is_enabled() if controller else False}")

# 检查价格线管理器
manager = chart._price_line_manager
print(f"price_line_manager: {manager}")
lines = manager.get_all_lines() if manager else {}
print(f"当前价格线数量: {len(lines)}")
```

### 可能需要的额外修复

如果日志显示参数仍然为 'NOT SET'，可能需要检查：

1. **ChartWidget.set_vt_symbol() 的实现**
   - 确保方法正确保存了 `_vt_symbol` 属性

2. **DrawingOrderController 的初始化**
   - 确保 controller 正确引用了 chart 的参数

3. **参数传递时机**
   - 可能在设置参数后又被某个操作清空了

## 下一步

1. 重新启动程序
2. 按照测试步骤操作
3. 查看详细的调试日志
4. 把日志输出发给我，我帮你分析具体问题

## 相关文件

- `vnpy/trader/ui/widget.py` - ChartWindow 主类
- `vnpy/chart/multi_timeframe_widget.py` - MultiTimeframeWidget
- `vnpy/chart/widget.py` - ChartWidget（包含DrawingOrderController）
- `vnpy/chart/drawing_order_controller.py` - 画线控制器
- `vnpy/chart/price_line_manager.py` - 价格线管理器

