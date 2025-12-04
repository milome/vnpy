# 实时4小时K线边框实现方案

## 需求概述

### 需求1：实时4小时K线矩形边框

在多周期模式窗口中显示最近的实时4小时K线边框：

**阳线边框**：
- 颜色：红色
- 动画：顺时针跑马灯
- 起始：4小时第一根1分钟K线
- 结束：最近一根实时1分钟K线
- 高线：最近收盘价
- 低线：4小时开盘价
- 线宽：3.5像素

**阴线边框**：
- 颜色：青色
- 动画：逆时针跑马灯
- 起始：4小时第一根1分钟K线
- 结束：最近一根实时1分钟K线
- 高线：4小时开盘价
- 低线：最近收盘价
- 线宽：3.5像素

### 需求2：4小时开盘价跑马灯线

将现有的4小时开盘价黄虚线改为：
- 黄色向右延伸的慢速跑马灯线
- 线宽不变

## 技术设计

### 关键数据结构

```python
# 4小时K线的关键数据
class FourHourCandleData:
    """4小时K线数据"""
    open_price: float        # 开盘价
    current_close: float     # 当前收盘价（实时更新）
    start_index: int         # 起始1分钟K线索引
    current_index: int       # 当前1分钟K线索引
    is_bullish: bool         # 是否为阳线
```

### 实现步骤

#### 步骤1：在 MultiTimeframeWidget 中添加动画管理器

```python
# multi_timeframe_widget.py

from vnpy.chart.drawing_animation import (
    DrawingAnimationManager,
    AnimationLineDirection
)

class MultiTimeframeWidget(QtWidgets.QWidget):
    def __init__(self, ...):
        # ... 现有代码 ...
        
        # 创建动画管理器
        self._animation_manager: DrawingAnimationManager | None = None
        
        # 4小时K线边框相关
        self._current_4h_rect_id: str | None = None  # 当前4小时边框ID
        self._current_4h_open_line_id: str | None = None  # 4小时开盘价线ID
        self._current_4h_data: dict | None = None  # 当前4小时数据
```

#### 步骤2：初始化动画管理器

```python
def _init_animation_manager(self) -> None:
    """初始化动画管理器"""
    if not self._chart:
        return
    
    # 获取主图表的 plot
    first_plot = self._chart._first_plot
    
    # 创建动画管理器
    self._animation_manager = DrawingAnimationManager(
        widget=self._chart,
        plot=first_plot
    )
```

#### 步骤3：在数据加载完成后初始化

```python
def _init_ui(self):
    """构建 UI"""
    # ... 现有代码 ...
    
    # 初始化动画管理器
    self._init_animation_manager()
```

#### 步骤4：实现4小时边框更新方法

```python
def _update_4h_candle_border(self) -> None:
    """更新4小时K线边框"""
    if not self._animation_manager:
        return
    
    # 获取当前4小时K线数据
    four_hour_data = self._get_current_4h_data()
    if not four_hour_data:
        return
    
    # 删除旧边框
    if self._current_4h_rect_id:
        self._animation_manager.remove_line(self._current_4h_rect_id)
    
    # 计算边框参数
    start_index = four_hour_data['start_index']
    current_index = four_hour_data['current_index']
    open_price = four_hour_data['open_price']
    current_close = four_hour_data['current_close']
    is_bullish = current_close >= open_price
    
    # 计算边框位置
    center_index = (start_index + current_index) / 2
    width = current_index - start_index
    
    if is_bullish:
        # 阳线：红色顺时针
        color = (255, 75, 75)
        direction = AnimationLineDirection.BACKWARD
        high_price = current_close
        low_price = open_price
    else:
        # 阴线：青色逆时针
        color = (0, 255, 255)
        direction = AnimationLineDirection.FORWARD
        high_price = open_price
        low_price = current_close
    
    # 创建新边框
    self._current_4h_rect_id = self._animation_manager.create_rectangle_border(
        time_index=center_index,
        high_price=high_price,
        low_price=low_price,
        width=width,
        color=color,
        animation_direction=direction,
        dash_pattern=[8, 4],
        line_width=3.5,
        rect_id="realtime_4h_candle"
    )
```

#### 步骤5：实现获取4小时数据的方法

```python
def _get_current_4h_data(self) -> dict | None:
    """获取当前4小时K线数据"""
    # 获取所有1分钟K线
    all_bars = self._manager_1m.get_all_bars()
    if not all_bars:
        return None
    
    # 获取最新的K线
    latest_bar = all_bars[-1]
    latest_index = len(all_bars) - 1
    
    # 计算当前4小时周期的起始时间
    from vnpy.trader.period_utils import get_hkfe_4hour_period
    period_start, period_end = get_hkfe_4hour_period(latest_bar.datetime)
    
    # 查找4小时周期的第一根1分钟K线
    start_index = None
    for i, bar in enumerate(all_bars):
        if bar.datetime >= period_start:
            start_index = i
            break
    
    if start_index is None:
        return None
    
    # 获取4小时开盘价（第一根1分钟K线的开盘价）
    open_price = all_bars[start_index].open_price
    
    # 当前收盘价（最新1分钟K线的收盘价）
    current_close = latest_bar.close_price
    
    return {
        'start_index': start_index,
        'current_index': latest_index,
        'open_price': open_price,
        'current_close': current_close,
        'period_start': period_start,
        'period_end': period_end
    }
```

#### 步骤6：实现4小时开盘价跑马灯线

```python
def _update_4h_open_line(self) -> None:
    """更新4小时开盘价跑马灯线"""
    if not self._animation_manager:
        return
    
    # 获取当前4小时数据
    four_hour_data = self._get_current_4h_data()
    if not four_hour_data:
        return
    
    # 删除旧线
    if self._current_4h_open_line_id:
        self._animation_manager.remove_line(self._current_4h_open_line_id)
    
    # 创建新的开盘价跑马灯线
    self._current_4h_open_line_id = self._animation_manager.create_horizontal_line(
        price=four_hour_data['open_price'],
        color=(255, 255, 0),  # 黄色
        width=1.5,  # 保持原线宽
        animation_direction=AnimationLineDirection.FORWARD,  # 向右（正向）
        dash_pattern=[15, 8],  # 慢速：更长的虚线样式
        line_id="realtime_4h_open"
    )
```

#### 步骤7：在实时更新中调用

```python
def on_bar(self, bar: BarData) -> None:
    """
    实时接收1分钟K线更新
    """
    # 原有的更新逻辑...
    
    # 更新4小时边框和开盘价线
    self._update_4h_candle_border()
    self._update_4h_open_line()
```

## 实现文件列表

需要修改的文件：

1. **vnpy/chart/multi_timeframe_widget.py**
   - 添加动画管理器初始化
   - 实现4小时边框更新方法
   - 实现4小时开盘价线更新方法
   - 在实时更新中调用

2. **vnpy/chart/drawing_animation.py**
   - 已实现（无需修改）

## 关键技术点

### 1. 时间索引计算

```python
# 中心索引 = (起始索引 + 当前索引) / 2
center_index = (start_index + current_index) / 2

# 宽度 = 当前索引 - 起始索引
width = current_index - start_index
```

### 2. 价格线计算

**阳线**：
```python
high_price = current_close  # 高线：当前收盘价
low_price = open_price       # 低线：4小时开盘价
```

**阴线**：
```python
high_price = open_price      # 高线：4小时开盘价
low_price = current_close    # 低线：当前收盘价
```

### 3. 动画方向

- **阳线**：`BACKWARD` = 反向 = 顺时针
- **阴线**：`FORWARD` = 正向 = 逆时针

### 4. 慢速跑马灯

使用更长的虚线样式实现慢速效果：
```python
dash_pattern = [15, 8]  # 15像素实线，8像素空白（比正常的[8, 4]长）
```

## 性能优化

### 1. 减少不必要的更新

```python
# 只在K线真正变化时更新
if self._current_4h_data:
    old_index = self._current_4h_data['current_index']
    new_index = four_hour_data['current_index']
    if old_index == new_index:
        return  # 索引未变化，不更新
```

### 2. 批量操作

```python
# 同时更新边框和开盘价线
def update_4h_animations(self):
    """批量更新4小时相关动画"""
    self._update_4h_candle_border()
    self._update_4h_open_line()
```

## 测试验证

### 测试用例

1. **阳线边框测试**
   - 当前价格 > 4小时开盘价
   - 应显示红色顺时针边框
   - 高线 = 当前价格，低线 = 开盘价

2. **阴线边框测试**
   - 当前价格 < 4小时开盘价
   - 应显示青色逆时针边框
   - 高线 = 开盘价，低线 = 当前价格

3. **实时更新测试**
   - 每次新的1分钟K线到来时
   - 边框应自动扩展（宽度增加）
   - 高低线应根据最新价格调整

4. **周期切换测试**
   - 跨越4小时周期时
   - 旧边框应删除
   - 新边框应创建

### 调试日志

```python
def _update_4h_candle_border(self):
    # ... 代码 ...
    
    if self._main_engine:
        self._main_engine.write_log(
            f"[4H边框] 类型={'阳线' if is_bullish else '阴线'} "
            f"索引[{start_index}~{current_index}] "
            f"价格[{low_price:.0f}~{high_price:.0f}]",
            "MultiTimeframe"
        )
```

## 使用示例

```python
# 创建多周期窗口
widget = MultiTimeframeWidget(
    vt_symbol="MHImain.HKFE",
    exchange=Exchange.HKFE,
    start=start_time,
    end=end_time,
    main_engine=main_engine
)

# 实时更新（由外部调用）
def on_tick(tick: TickData):
    # ... 生成1分钟K线 ...
    widget.on_bar(bar_1m)  # 会自动更新4小时边框
```

## 效果预览

### 阳线边框（红色顺时针）

```
4小时周期: 09:00 - 13:00
├─ 09:00 开盘价: 26000
├─ 11:57 当前价: 26100
└─ 边框:
   ┌────────────────────────┐  ← 高线: 26100 (当前价)
   │  240根1分钟K线         │
   │  红色顺时针跑马灯      │
   └────────────────────────┘  ← 低线: 26000 (开盘价)
```

### 阴线边框（青色逆时针）

```
4小时周期: 13:00 - 17:00
├─ 13:00 开盘价: 26000
├─ 15:30 当前价: 25900
└─ 边框:
   ┌────────────────────────┐  ← 高线: 26000 (开盘价)
   │  150根1分钟K线         │
   │  青色逆时针跑马灯      │
   └────────────────────────┘  ← 低线: 25900 (当前价)
```

### 4小时开盘价线（黄色慢速跑马灯）

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━→  26000 (4H开盘价，黄色慢速向右)
```

## 注意事项

1. **线宽统一性**：K线边框线宽设为3.5像素，与K线线框协调
2. **性能考虑**：每次1分钟K线更新都会重绘边框，需确保性能
3. **周期切换**：跨越4小时周期时要及时删除旧边框
4. **时区处理**：确保使用港交所时区计算4小时周期
5. **数据完整性**：确保4小时周期的起始K线在数据范围内

## 下一步行动

1. 在 `multi_timeframe_widget.py` 中添加相关方法
2. 在 `_init_ui()` 中初始化动画管理器
3. 在实时更新方法中调用边框更新
4. 测试阳线和阴线两种情况
5. 测试跨周期切换
6. 优化性能和视觉效果

---

**准备好了吗？让我们开始实现！** 🚀

