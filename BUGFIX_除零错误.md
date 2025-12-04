# Bug修复：鼠标移动时除零错误

## 问题

鼠标移动时报错：

```
ZeroDivisionError: float division by zero
  File "vnpy/chart/price_line_drag.py", line 112
    distance_pixels = distance / price_per_pixel
```

## 原因

在 `find_line_near_point()` 方法中计算像素距离时：
```python
price_per_pixel = price_range / widget_height if widget_height > 0 else 0
distance_pixels = distance / price_per_pixel  # ❌ price_per_pixel 可能为 0
```

**可能的情况**：
1. `plot_height <= 0`（窗口未初始化或最小化）
2. `y_height = 0`（Y轴范围为0，即 y_max = y_min）

## 修复

修改条件检查，同时检查 `plot_height > 0` 和 `y_height > 0`：

```python
# ✅ 原代码
if plot_height > 0:
    price_per_pixel = y_height / plot_height
    distance_pixels = distance / price_per_pixel

# ✅ 修复后
if plot_height > 0 and y_height > 0:
    price_per_pixel = y_height / plot_height
    distance_pixels = distance / price_per_pixel
```

## 修改内容

**文件**：`vnpy/chart/price_line_drag.py`

**位置**：第110行

**修改**：条件检查从 `if plot_height > 0:` 改为 `if plot_height > 0 and y_height > 0:`

## 总结

✅ 防止除零错误
✅ 优雅处理异常情况（跳过而不是崩溃）

修复完成！🎉

