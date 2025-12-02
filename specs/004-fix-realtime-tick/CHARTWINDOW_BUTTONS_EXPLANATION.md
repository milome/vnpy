# ChartWindow 按钮功能说明

## "切换"按钮 vs "加载"按钮

### "切换"按钮 (`switch_button`)

**功能**：切换到新的合约图表

**位置**：`vnpy/trader/ui/widget.py:2399-2400`

```python
self.switch_button: QtWidgets.QPushButton = QtWidgets.QPushButton(_("切换"))
self.switch_button.clicked.connect(self.switch_chart)
```

**对应方法**：`switch_chart()` (行3583-3673)

**主要功能**：
1. **读取新的合约代码**：从 `symbol_line` 输入框读取用户输入的合约代码
2. **切换合约**：如果输入的合约代码与当前显示的合约不同，切换到新合约
3. **完全重置**：
   - 清空当前图表数据 (`self.chart.clear_all()`)
   - 重置所有状态变量（K线状态、成交量追踪等）
   - 重置滚动条
   - 创建新的K线生成器（根据交易所类型选择不同的生成器）
4. **加载新合约数据**：调用 `load_history_data(vt_symbol)` 加载新合约的历史数据
5. **更新UI**：
   - 更新窗口标题（显示新合约和周期）
   - 更新状态标签
   - 设置图表的VT symbol（用于画线交易功能）

**使用场景**：
- 想查看另一个合约的K线图
- 在输入框中输入新的合约代码（如 `HSImain.HKFE`）后点击切换

---

### "加载"按钮 (`refresh_button`)

**功能**：刷新当前合约的历史数据

**位置**：`vnpy/trader/ui/widget.py:2473-2475`

```python
self.refresh_button: QtWidgets.QPushButton = QtWidgets.QPushButton(_("加载"))
self.refresh_button.clicked.connect(self.refresh_chart)
```

**对应方法**：`refresh_chart()` (行3679-3711)

**主要功能**：
1. **使用当前合约**：不读取输入框，直接使用 `self.current_vt_symbol`（当前已显示的合约）
2. **不切换合约**：保持显示同一个合约，只是重新加载数据
3. **重置状态**：
   - 清空当前图表数据
   - 重置K线状态和成交量追踪
   - 重置数据缺口状态
4. **重新加载数据**：调用 `load_history_data(self.current_vt_symbol)` 重新加载当前合约的历史数据
5. **更新UI**：更新状态标签显示"正在刷新..."

**使用场景**：
- 当前合约的数据需要刷新（如更新了数据库中的数据）
- 修改了起始时间后想重新加载
- 切换周期后想重新加载对应周期的数据
- **不需要切换合约，只是想刷新当前合约的数据**

---

## 关键区别总结

| 特性 | "切换"按钮 | "加载"按钮 |
|------|-----------|-----------|
| **数据源** | 从 `symbol_line` 输入框读取 | 使用 `self.current_vt_symbol` |
| **合约改变** | ✅ 可以切换到新合约 | ❌ 不改变合约，保持当前合约 |
| **创建新生成器** | ✅ 创建新的K线生成器 | ❌ 不创建（使用现有的） |
| **更新窗口标题** | ✅ 更新为新合约名称 | ❌ 不更新（保持当前标题） |
| **重置滚动条** | ✅ 重置到最右边（100） | ❌ 不重置 |
| **使用场景** | 切换查看不同合约 | 刷新当前合约数据 |

---

## 代码对比

### switch_chart() 关键代码：

```python
def switch_chart(self) -> None:
    """切换到新的合约图表"""
    # 1. 从输入框读取新合约代码
    vt_symbol: str = str(self.symbol_line.text()).strip()
    
    # 2. 检查是否改变
    if vt_symbol == self.current_vt_symbol:
        return  # 如果没有改变，直接返回
    
    # 3. 更新当前合约代码
    self.current_vt_symbol = vt_symbol
    
    # 4. 重置所有状态...
    # 5. 清空图表...
    # 6. 重置滚动条...
    # 7. 创建新的K线生成器...
    # 8. 更新窗口标题...
    # 9. 加载新合约的历史数据
    self.load_history_data(vt_symbol)
```

### refresh_chart() 关键代码：

```python
def refresh_chart(self) -> None:
    """刷新当前图表"""
    # 1. 检查是否有当前合约
    if self.current_vt_symbol:
        # 2. 重置状态（不清除 current_vt_symbol）
        self.history_loaded = False
        self.history_data = []
        # ... 重置其他状态
        
        # 3. 清空图表...
        # 4. 重新加载当前合约的数据
        self.load_history_data(self.current_vt_symbol)  # 使用当前合约
```

---

## 实际使用示例

### 场景1：切换到新合约
1. 在合约输入框输入：`HSImain.HKFE`
2. 点击"切换"按钮
3. → 图表切换到HSImain合约，加载HSImain的历史数据

### 场景2：刷新当前合约数据
1. 当前显示：`MHImain.HKFE`
2. 修改了起始时间（如改为3天前）
3. 点击"加载"按钮
4. → 图表保持显示MHImain，但重新加载从新起始时间开始的数据

### 场景3：切换周期后刷新
1. 当前显示：`MHImain.HKFE`，1分钟周期
2. 切换周期下拉框到"5分钟"
3. 点击"加载"按钮
4. → 图表保持显示MHImain，但加载5分钟周期的数据

---

## 注意事项

1. **"切换"按钮**：
   - 如果输入框中的合约代码与当前显示的合约相同，不会重新加载数据（直接返回）
   - 切换时会创建新的K线生成器，这对于HKFE交易所很重要（会使用HKFEBarGenerator）

2. **"加载"按钮**：
   - 必须先有一个当前合约（`current_vt_symbol`不为空）
   - 如果从未切换过合约（`current_vt_symbol`为空），点击"加载"不会做任何事情
   - 通常配合起始时间选择器使用，用于重新加载不同时间范围的数据

3. **数据加载**：
   - 两个按钮最终都调用 `load_history_data()` 方法
   - 区别在于传入的合约代码来源不同：
     - "切换"：使用输入框中的新合约代码
     - "加载"：使用当前已显示的合约代码


