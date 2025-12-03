# K线显示问题诊断

## 问题描述

运行 `real_time_charts.py` 后看不到K线显示。

## 可能原因分析

### 1. 需要点击"启动策略"按钮 ⚠️ 最常见原因

**问题**：数据只有在点击"启动策略"按钮后才会生成。

**检查方法**：
- 运行程序后，查看是否有"启动策略"按钮
- 点击按钮后，状态应该变为"运行中"
- 连接状态应该变为"已连接"

**解决**：必须点击"启动策略"按钮才能看到K线。

### 2. 数据量不足

**问题**：原始代码要求至少2条K线数据才会绘制（已修复为1条）。

**检查方法**：
- 等待至少几秒钟，让数据生成
- 检查控制台是否有错误信息

### 3. Y轴范围未设置 ⚠️ 已修复

**问题**：图表Y轴没有自动调整范围，K线可能绘制在可见区域外。

**已修复**：添加了自动Y轴范围调整功能。

### 4. 坐标系统问题

**潜在问题**：
- K线使用整数索引作为X坐标
- Y坐标使用价格
- 如果价格范围很大或很小，可能看不见

**已修复**：添加了自动范围计算和调整。

## 使用步骤

1. 运行程序：
   ```bash
   python visualization/real_time_charts.py
   ```

2. **必须点击"启动策略"按钮**

3. 等待几秒钟，让数据生成

4. 应该能看到K线显示在图表中

## 代码修复记录

### 修复1：降低数据要求
- 从需要2条数据降低到1条数据即可绘制

### 修复2：添加Y轴自动范围调整
```python
# ✅ 自动调整Y轴范围以显示所有K线
if len(self.ohlc_data) > 0:
    # 计算价格范围
    all_prices = []
    for _, o, h, l, c, _ in self.ohlc_data:
        all_prices.extend([o, h, l, c])
    
    if all_prices:
        min_price = min(all_prices)
        max_price = max(all_prices)
        price_range = max_price - min_price
        
        # 添加一些边距（10%）
        margin = price_range * 0.1 if price_range > 0 else 100
        self.main_chart.setYRange(min_price - margin, max_price + margin, padding=0)
    
    # 自动调整X轴范围
    max_index = len(self.ohlc_data) - 1
    self.main_chart.setXRange(-1, max(max_index + 1, 10), padding=0)
```

## 调试建议

如果仍然看不到K线，可以添加调试输出：

```python
def draw_candlesticks(self):
    """绘制K线"""
    if len(self.ohlc_data) < 1:
        print("警告：没有K线数据")
        return
    
    print(f"准备绘制 {len(self.ohlc_data)} 条K线")
    
    # 准备K线数据
    candlestick_data = [(i, o, h, l, c) for i, o, h, l, c, v in self.ohlc_data]
    
    # 打印第一条K线的数据
    if candlestick_data:
        print(f"第一条K线数据: {candlestick_data[0]}")
    
    # 创建K线图形项
    candlestick_item = CandlestickItem(candlestick_data)
    self.main_chart.addItem(candlestick_item)
    print("K线图形项已添加到图表")
    
    # ... 自动范围调整代码 ...
```

## 常见问题

### Q: 窗口打开了但看不到任何内容？
A: 确保点击了"启动策略"按钮。

### Q: 点击了启动按钮但还是看不到K线？
A: 
1. 等待几秒钟，数据需要时间生成
2. 检查是否有错误信息
3. 尝试最大化窗口
4. 检查图表区域是否可见

### Q: K线显示但很小？
A: 这是正常的，随着数据增多，K线会逐渐显示。

## 技术细节

### K线绘制流程

1. `add_bar_data()` - 添加K线数据到 `ohlc_data`
2. `refresh_chart()` - 刷新图表（每秒调用一次）
3. `draw_candlesticks()` - 绘制K线
   - 准备数据：`[(i, o, h, l, c), ...]`
   - 创建 `CandlestickItem`
   - 添加到图表
   - 自动调整Y轴范围

### CandlestickItem 工作原理

- 使用 `QPicture` 预渲染K线图形
- X轴使用索引（0, 1, 2, ...）
- Y轴使用价格
- 颜色：阳线红色，阴线绿色

