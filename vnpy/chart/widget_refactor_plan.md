# ChartWidget 重构方案

## 现状分析
- **文件大小**: 5058 行
- **主要问题**: 
  - 代码过于庞大，难以维护
  - 职责不清晰，功能耦合严重
  - 修改风险高，容易引入bug

## 重构目标
- 将文件拆分为多个模块，每个模块 < 1500 行
- 提高代码可维护性和可读性
- 保持功能完整性，不破坏现有API
- **采用TDD红绿灯模式进行重构**
- **测试代码覆盖率 > 95%**

## 模块拆分方案

### 1. `widget.py` (核心文件) - ~600行
**职责**: 主类定义、初始化、基础方法
- `__init__` - 初始化所有组件
- `_init_ui` - UI初始化
- `add_plot`, `add_item`, `get_plot`, `get_all_plots` - 图表基础操作
- `add_price_line`, `remove_price_line` - 价格线基础操作
- `get_price_line_manager` - 获取管理器
- `set_vt_symbol`, `set_main_engine` - 设置配置
- `_get_main_contract_mapping`, `_find_position_by_main_contract_mapping` - 合约映射
- `clear_all` - 清理所有数据
- `set_future_bars` - 设置未来K线数量
- `set_drawing_click_callback`, `set_drawing_mode_changed_callback` - 回调设置

### 2. `widget_position.py` (持仓管理) - ~1200行
**职责**: 持仓相关的所有逻辑
- `_register_position_events` - 注册持仓事件
- `_on_position_update` - 持仓更新事件处理
- `_update_entry_line_pnl` - 更新入场线盈亏（核心方法，~600行）
- `_clear_frozen_position_lines` - 清除冻结持仓线
- `_load_position_holdings` - 从数据库加载持仓记录

### 3. `widget_order.py` (订单处理) - ~600行
**职责**: 订单相关的处理逻辑
- `_on_order_update` - 订单更新事件处理
- `_process_order_update` - 处理订单更新（主线程）
- 订单去重逻辑
- 订单与价格线的关联管理

### 4. `widget_trigger.py` (触发下单/平仓) - ~700行
**职责**: 价格突破触发下单/平仓
- `_on_price_breakthrough` - 价格突破事件处理
- `trigger_pending_order_breakthrough` - 触发挂单线突破下单
- `trigger_stop_loss_close` - 触发止损线平仓
- `trigger_take_profit_close` - 触发止盈线平仓

### 5. `widget_mouse.py` (鼠标事件) - ~900行
**职责**: 所有鼠标事件处理
- `mouseMoveEvent` - 鼠标移动（拖拽、悬停检测）
- `mousePressEvent` - 鼠标按下（开始拖拽、画线下单）
- `mouseReleaseEvent` - 鼠标释放（结束拖拽、创建止损止盈线）
- `mouseDoubleClickEvent` - 双击事件（删除挂单、平仓、删除止损止盈）
- `_update_related_lines_on_drag` - 拖拽时更新关联线
- `_update_related_lines_on_drag_end` - 拖拽结束时更新关联线
- `_update_points_on_line_drag` - 拖拽止损止盈线时更新点数

### 6. `widget_chart.py` (图表更新) - ~500行
**职责**: 图表数据更新和显示
- `update_history` - 更新历史数据
- `update_bar` - 更新单根K线
- `_update_plot_limits` - 更新图表限制
- `_update_x_range` - 更新X轴范围
- `_update_y_range` - 更新Y轴范围
- `paintEvent` - 绘制事件
- `move_to_right` - 移动到最右侧
- `_on_key_left`, `_on_key_right`, `_on_key_up`, `_on_key_down` - 键盘导航
- `wheelEvent` - 滚轮缩放

### 7. `widget_database.py` (数据库操作) - ~200行
**职责**: 数据库相关的加载和保存
- `_load_line_relations` - 加载价格线关联关系
- `save_price_lines` - 保存价格线（legacy）
- `load_price_lines` - 加载价格线（legacy）

### 8. `widget_cursor.py` (光标类) - ~250行
**职责**: 图表光标显示（已独立，保持不变）
- `ChartCursor` 类及其所有方法

## 实现策略

### 方式1: Mixin模式（推荐）
将各个功能模块作为Mixin类，ChartWidget继承所有Mixin：
```python
# widget.py
class ChartWidget(
    pg.PlotWidget,
    ChartWidgetPositionMixin,
    ChartWidgetOrderMixin,
    ChartWidgetTriggerMixin,
    ChartWidgetMouseMixin,
    ChartWidgetChartMixin,
    ChartWidgetDatabaseMixin
):
    # 核心代码
    pass
```

**优点**:
- 保持单一类，API不变
- 代码组织清晰
- 易于测试和维护

### 方式2: 组合模式
将功能模块作为独立的Handler类，ChartWidget持有引用：
```python
# widget.py
class ChartWidget(pg.PlotWidget):
    def __init__(self):
        self._position_handler = PositionHandler(self)
        self._order_handler = OrderHandler(self)
        # ...
```

**优点**:
- 更彻底的解耦
- 可以独立测试各个Handler

**缺点**:
- 需要修改大量方法调用
- API可能发生变化

## 推荐方案：Mixin模式

### 文件结构
```
vnpy/chart/
├── widget.py              # 主类 + 核心方法 (~600行)
├── widget_position.py     # 持仓管理Mixin (~1200行)
├── widget_order.py         # 订单处理Mixin (~600行)
├── widget_trigger.py       # 触发下单/平仓Mixin (~700行)
├── widget_mouse.py         # 鼠标事件Mixin (~900行)
├── widget_chart.py         # 图表更新Mixin (~500行)
├── widget_database.py      # 数据库操作Mixin (~200行)
└── widget_cursor.py        # 光标类 (~250行)
```

### 实现步骤（TDD红绿灯模式）

#### 阶段0: 测试环境准备
1. **设置测试框架**
   - 安装 pytest, pytest-qt, pytest-cov, coverage
   - 配置 `.coveragerc` 文件
   - 创建 `tests/chart/` 目录结构

2. **创建测试基类**
   - `tests/chart/conftest.py` - pytest fixtures
   - `tests/chart/test_base.py` - 测试基类和工具函数

#### 阶段1: 创建Mixin基类（TDD）
1. **红**: 编写 `ChartWidgetMixinBase` 的测试用例
2. **绿**: 实现 `ChartWidgetMixinBase` 基类
3. **重构**: 优化代码，确保测试通过

#### 阶段2: 拆分持仓管理模块（TDD）
1. **红**: 编写 `widget_position.py` 的测试用例
   - 测试 `_register_position_events`
   - 测试 `_on_position_update`
   - 测试 `_update_entry_line_pnl`（重点，需要多个测试用例）
   - 测试 `_clear_frozen_position_lines`
   - 测试 `_load_position_holdings`
2. **绿**: 创建 `widget_position.py`，实现 `ChartWidgetPositionMixin`
3. **重构**: 优化代码，确保测试通过，覆盖率 > 95%

#### 阶段3: 拆分订单处理模块（TDD）
1. **红**: 编写 `widget_order.py` 的测试用例
   - 测试 `_on_order_update`
   - 测试 `_process_order_update`
   - 测试订单去重逻辑
2. **绿**: 创建 `widget_order.py`，实现 `ChartWidgetOrderMixin`
3. **重构**: 优化代码，确保测试通过，覆盖率 > 95%

#### 阶段4: 拆分触发模块（TDD）
1. **红**: 编写 `widget_trigger.py` 的测试用例
   - 测试 `_on_price_breakthrough`
   - 测试 `trigger_pending_order_breakthrough`
   - 测试 `trigger_stop_loss_close`
   - 测试 `trigger_take_profit_close`
2. **绿**: 创建 `widget_trigger.py`，实现 `ChartWidgetTriggerMixin`
3. **重构**: 优化代码，确保测试通过，覆盖率 > 95%

#### 阶段5: 拆分鼠标事件模块（TDD）
1. **红**: 编写 `widget_mouse.py` 的测试用例
   - 测试 `mouseMoveEvent`
   - 测试 `mousePressEvent`
   - 测试 `mouseReleaseEvent`
   - 测试 `mouseDoubleClickEvent`
2. **绿**: 创建 `widget_mouse.py`，实现 `ChartWidgetMouseMixin`
3. **重构**: 优化代码，确保测试通过，覆盖率 > 95%

#### 阶段6: 拆分图表更新模块（TDD）
1. **红**: 编写 `widget_chart.py` 的测试用例
   - 测试 `update_history`
   - 测试 `update_bar`
   - 测试各种更新方法
2. **绿**: 创建 `widget_chart.py`，实现 `ChartWidgetChartMixin`
3. **重构**: 优化代码，确保测试通过，覆盖率 > 95%

#### 阶段7: 拆分数据库模块（TDD）
1. **红**: 编写 `widget_database.py` 的测试用例
   - 测试 `_load_line_relations`
   - 测试 `save_price_lines`
   - 测试 `load_price_lines`
2. **绿**: 创建 `widget_database.py`，实现 `ChartWidgetDatabaseMixin`
3. **重构**: 优化代码，确保测试通过，覆盖率 > 95%

#### 阶段8: 移动光标类（TDD）
1. **红**: 编写 `widget_cursor.py` 的测试用例
   - 测试 `ChartCursor` 的所有方法
2. **绿**: 创建 `widget_cursor.py`，移动 `ChartCursor` 类
3. **重构**: 优化代码，确保测试通过，覆盖率 > 95%

#### 阶段9: 集成测试和覆盖率验证
1. **集成测试**: 测试所有模块的集成
2. **覆盖率验证**: 运行 `coverage report`，确保 > 95%
3. **性能测试**: 确保性能无明显下降
4. **更新文档**: 更新 `__init__.py` 导出和文档

## 注意事项

1. **保持API兼容性**
   - 所有公共方法保持不变
   - 内部方法可以重构

2. **共享状态管理**
   - Mixin通过 `self` 访问ChartWidget的属性
   - 确保属性命名一致

3. **导入顺序**
   - Mixin类需要先定义
   - ChartWidget最后定义并继承所有Mixin

4. **测试策略（TDD红绿灯模式）**
   - **红（Red）**: 先写失败的测试用例
   - **绿（Green）**: 写最少的代码让测试通过
   - **重构（Refactor）**: 优化代码，保持测试通过
   - 每个模块拆分前先写测试
   - 测试覆盖率必须 > 95%
   - 使用 pytest + coverage 进行测试和覆盖率统计

5. **向后兼容**
   - 保持 `__init__.py` 中的导出不变
   - 外部代码无需修改

## 预期效果

- **代码可维护性**: 每个文件职责单一，易于理解和修改
- **代码可读性**: 相关功能集中，逻辑清晰
- **开发效率**: 修改某个功能时只需关注对应文件
- **测试友好**: 可以针对每个模块编写单元测试

## 风险评估

- **低风险**: 使用Mixin模式，不改变类结构
- **中风险**: 需要仔细处理共享状态和方法调用
- **缓解措施**: 分步实施，每步都进行测试验证

## 成功标准

- ✅ 所有文件 < 1500行
- ✅ 所有功能正常工作
- ✅ **测试代码覆盖率 > 95%**
- ✅ 性能无明显下降
- ✅ 代码可读性提升
- ✅ 外部API保持不变
- ✅ 所有测试用例通过（pytest）
- ✅ 遵循TDD红绿灯模式

