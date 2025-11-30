# ChartWidget 重构任务清单

## 📋 总体目标
- [ ] 将 5058 行的 `widget.py` 拆分为 8 个模块，每个 < 1500 行
- [ ] 采用 TDD 红绿灯模式进行重构
- [ ] 测试代码覆盖率 > 95%
- [ ] 保持所有功能正常工作
- [ ] 保持外部 API 不变

---

## 🔧 阶段0: 测试环境准备

### 0.1 安装测试工具
- [ ] 安装 pytest: `pip install pytest`
- [ ] 安装 pytest-qt: `pip install pytest-qt`
- [ ] 安装 pytest-cov: `pip install pytest-cov`
- [ ] 安装 coverage: `pip install coverage`
- [ ] 验证安装: `pytest --version`

### 0.2 配置测试环境
- [ ] 创建 `.coveragerc` 配置文件
- [ ] 创建 `pytest.ini` 配置文件
- [ ] 配置覆盖率阈值（95%）
- [ ] 配置测试路径和标记

### 0.3 创建测试目录结构
- [ ] 创建 `tests/chart/` 目录
- [ ] 创建 `tests/chart/__init__.py`
- [ ] 创建 `tests/chart/conftest.py` (pytest fixtures)
- [ ] 创建 `tests/chart/test_base.py` (测试基类)
- [ ] 创建各模块测试文件框架

### 0.4 创建测试基类和工具
- [ ] 实现 `mock_main_engine` fixture
- [ ] 实现 `mock_event_engine` fixture
- [ ] 实现 `chart_widget` fixture
- [ ] 实现测试辅助函数
- [ ] 编写测试工具函数文档

### 0.5 备份和版本控制
- [ ] 创建重构分支: `git checkout -b refactor/widget-split`
- [ ] 备份当前 `widget.py`: `cp widget.py widget.py.backup`
- [ ] 提交当前状态: `git commit -m "chore: backup before refactoring"`
- [ ] 创建重构里程碑标记

---

## 🎯 阶段1: 创建 Mixin 基类（TDD）

### 1.1 红（Red）- 编写测试用例
- [ ] 创建 `tests/chart/test_widget_mixin_base.py`
- [ ] 测试 `_get_main_engine()` 方法
- [ ] 测试 `_get_vt_symbol()` 方法
- [ ] 测试 `_log()` 方法
- [ ] 运行测试，确认失败（红）

### 1.2 绿（Green）- 实现基类
- [ ] 创建 `widget_mixin_base.py`
- [ ] 实现 `ChartWidgetMixinBase` 类
- [ ] 实现 `_get_main_engine()` 方法
- [ ] 实现 `_get_vt_symbol()` 方法
- [ ] 实现 `_log()` 方法
- [ ] 运行测试，确认通过（绿）

### 1.3 重构（Refactor）- 优化代码
- [ ] 代码审查和优化
- [ ] 添加文档字符串
- [ ] 运行测试，确保通过
- [ ] 检查覆盖率，确保 > 95%
- [ ] 提交代码: `git commit -m "feat: add ChartWidgetMixinBase"`

---

## 📊 阶段2: 拆分持仓管理模块（TDD）

### 2.1 红（Red）- 编写测试用例
- [ ] 创建 `tests/chart/test_widget_position.py`
- [ ] 测试 `_register_position_events()` - 成功注册
- [ ] 测试 `_register_position_events()` - 无 event_engine
- [ ] 测试 `_on_position_update()` - 合约匹配
- [ ] 测试 `_on_position_update()` - 合约不匹配
- [ ] 测试 `_on_position_update()` - 主线程调用
- [ ] 测试 `_on_position_update()` - 非主线程调用
- [ ] 测试 `_update_entry_line_pnl()` - 持仓为0
- [ ] 测试 `_update_entry_line_pnl()` - 持仓存在
- [ ] 测试 `_update_entry_line_pnl()` - 多条入场线
- [ ] 测试 `_update_entry_line_pnl()` - FIFO平仓
- [ ] 测试 `_update_entry_line_pnl()` - 合并显示
- [ ] 测试 `_clear_frozen_position_lines()` - 清除冻结持仓
- [ ] 测试 `_load_position_holdings()` - 从数据库加载
- [ ] 运行测试，确认失败（红）

### 2.2 绿（Green）- 实现模块
- [ ] 创建 `widget_position.py`
- [ ] 实现 `ChartWidgetPositionMixin` 类
- [ ] 从 `widget.py` 复制 `_register_position_events()` 方法
- [ ] 从 `widget.py` 复制 `_on_position_update()` 方法
- [ ] 从 `widget.py` 复制 `_update_entry_line_pnl()` 方法
- [ ] 从 `widget.py` 复制 `_clear_frozen_position_lines()` 方法
- [ ] 从 `widget.py` 复制 `_load_position_holdings()` 方法
- [ ] 调整导入和依赖
- [ ] 运行测试，确认通过（绿）

### 2.3 重构（Refactor）- 优化代码
- [ ] 拆分 `_update_entry_line_pnl()` 超大方法
  - [ ] 提取 `_handle_zero_position()` 方法
  - [ ] 提取 `_sync_position_holding()` 方法
  - [ ] 提取 `_update_entry_line_display()` 方法
  - [ ] 提取 `_handle_multiple_entry_lines()` 方法
- [ ] 代码审查和优化
- [ ] 添加文档字符串
- [ ] 运行测试，确保通过
- [ ] 检查覆盖率，确保 > 95%
- [ ] 提交代码: `git commit -m "feat: extract position management to mixin"`

### 2.4 集成到主类
- [ ] 在 `widget.py` 中导入 `ChartWidgetPositionMixin`
- [ ] 更新 `ChartWidget` 类继承
- [ ] 从 `widget.py` 删除已移动的方法
- [ ] 运行集成测试
- [ ] 验证功能正常

---

## 📦 阶段3: 拆分订单处理模块（TDD）

### 3.1 红（Red）- 编写测试用例
- [ ] 创建 `tests/chart/test_widget_order.py`
- [ ] 测试 `_on_order_update()` - 订单去重
- [ ] 测试 `_on_order_update()` - ALLTRADED 状态
- [ ] 测试 `_on_order_update()` - 合约匹配
- [ ] 测试 `_on_order_update()` - 合约不匹配
- [ ] 测试 `_process_order_update()` - 主线程处理
- [ ] 测试 `_process_order_update()` - 订单去重检查
- [ ] 测试 `_process_order_update()` - 创建入场线
- [ ] 测试 `_process_order_update()` - 平仓订单处理
- [ ] 测试 `_process_order_update()` - 清理孤儿线
- [ ] 运行测试，确认失败（红）

### 3.2 绿（Green）- 实现模块
- [ ] 创建 `widget_order.py`
- [ ] 实现 `ChartWidgetOrderMixin` 类
- [ ] 从 `widget.py` 复制 `_on_order_update()` 方法
- [ ] 从 `widget.py` 复制 `_process_order_update()` 方法
- [ ] 调整导入和依赖
- [ ] 运行测试，确认通过（绿）

### 3.3 重构（Refactor）- 优化代码
- [ ] 拆分 `_process_order_update()` 超大方法
  - [ ] 提取 `_check_order_duplicate()` 方法
  - [ ] 提取 `_handle_alltraded_order()` 方法
  - [ ] 提取 `_cleanup_orphaned_lines()` 方法
- [ ] 代码审查和优化
- [ ] 添加文档字符串
- [ ] 运行测试，确保通过
- [ ] 检查覆盖率，确保 > 95%
- [ ] 提交代码: `git commit -m "feat: extract order processing to mixin"`

### 3.4 集成到主类
- [ ] 在 `widget.py` 中导入 `ChartWidgetOrderMixin`
- [ ] 更新 `ChartWidget` 类继承
- [ ] 从 `widget.py` 删除已移动的方法
- [ ] 运行集成测试
- [ ] 验证功能正常

---

## 🎯 阶段4: 拆分触发模块（TDD）

### 4.1 红（Red）- 编写测试用例
- [ ] 创建 `tests/chart/test_widget_trigger.py`
- [ ] 测试 `_on_price_breakthrough()` - 价格突破事件
- [ ] 测试 `trigger_pending_order_breakthrough()` - 挂单线突破下单
- [ ] 测试 `trigger_pending_order_breakthrough()` - 平仓订单判断
- [ ] 测试 `trigger_pending_order_breakthrough()` - 下单失败处理
- [ ] 测试 `trigger_stop_loss_close()` - 多仓止损触发
- [ ] 测试 `trigger_stop_loss_close()` - 空仓止损触发
- [ ] 测试 `trigger_stop_loss_close()` - 无持仓跳过
- [ ] 测试 `trigger_take_profit_close()` - 多仓止盈触发
- [ ] 测试 `trigger_take_profit_close()` - 空仓止盈触发
- [ ] 测试 `trigger_take_profit_close()` - 无持仓跳过
- [ ] 运行测试，确认失败（红）

### 4.2 绿（Green）- 实现模块
- [ ] 创建 `widget_trigger.py`
- [ ] 实现 `ChartWidgetTriggerMixin` 类
- [ ] 从 `widget.py` 复制 `_on_price_breakthrough()` 方法
- [ ] 从 `widget.py` 复制 `trigger_pending_order_breakthrough()` 方法
- [ ] 从 `widget.py` 复制 `trigger_stop_loss_close()` 方法
- [ ] 从 `widget.py` 复制 `trigger_take_profit_close()` 方法
- [ ] 调整导入和依赖
- [ ] 运行测试，确认通过（绿）

### 4.3 重构（Refactor）- 优化代码
- [ ] 拆分 `trigger_pending_order_breakthrough()` 超大方法
  - [ ] 提取 `_check_closing_order()` 方法
  - [ ] 提取 `_create_order_request()` 方法
  - [ ] 提取 `_send_breakthrough_order()` 方法
- [ ] 代码审查和优化
- [ ] 添加文档字符串
- [ ] 运行测试，确保通过
- [ ] 检查覆盖率，确保 > 95%
- [ ] 提交代码: `git commit -m "feat: extract trigger logic to mixin"`

### 4.4 集成到主类
- [ ] 在 `widget.py` 中导入 `ChartWidgetTriggerMixin`
- [ ] 更新 `ChartWidget` 类继承
- [ ] 从 `widget.py` 删除已移动的方法
- [ ] 运行集成测试
- [ ] 验证功能正常

---

## 🖱️ 阶段5: 拆分鼠标事件模块（TDD）

### 5.1 红（Red）- 编写测试用例
- [ ] 创建 `tests/chart/test_widget_mouse.py`
- [ ] 测试 `mouseMoveEvent()` - 画线下单模式
- [ ] 测试 `mouseMoveEvent()` - 拖拽价格线
- [ ] 测试 `mouseMoveEvent()` - 悬停检测
- [ ] 测试 `mousePressEvent()` - 开始拖拽
- [ ] 测试 `mousePressEvent()` - 从入场线拖拽
- [ ] 测试 `mousePressEvent()` - 画线下单点击
- [ ] 测试 `mouseReleaseEvent()` - 结束拖拽
- [ ] 测试 `mouseReleaseEvent()` - 创建止损止盈线
- [ ] 测试 `mouseDoubleClickEvent()` - 挂单线双击
- [ ] 测试 `mouseDoubleClickEvent()` - 入场线双击平仓
- [ ] 测试 `mouseDoubleClickEvent()` - 止损止盈线双击删除
- [ ] 测试 `_update_related_lines_on_drag()` - 拖拽时更新
- [ ] 测试 `_update_points_on_line_drag()` - 更新点数
- [ ] 运行测试，确认失败（红）

### 5.2 绿（Green）- 实现模块
- [ ] 创建 `widget_mouse.py`
- [ ] 实现 `ChartWidgetMouseMixin` 类
- [ ] 从 `widget.py` 复制 `mouseMoveEvent()` 方法
- [ ] 从 `widget.py` 复制 `mousePressEvent()` 方法
- [ ] 从 `widget.py` 复制 `mouseReleaseEvent()` 方法
- [ ] 从 `widget.py` 复制 `mouseDoubleClickEvent()` 方法
- [ ] 从 `widget.py` 复制 `_update_related_lines_on_drag()` 方法
- [ ] 从 `widget.py` 复制 `_update_related_lines_on_drag_end()` 方法
- [ ] 从 `widget.py` 复制 `_update_points_on_line_drag()` 方法
- [ ] 调整导入和依赖
- [ ] 运行测试，确认通过（绿）

### 5.3 重构（Refactor）- 优化代码
- [ ] 拆分 `mouseDoubleClickEvent()` 超大方法
  - [ ] 提取 `_handle_double_click_pending()` 方法
  - [ ] 提取 `_handle_double_click_entry()` 方法
  - [ ] 提取 `_handle_double_click_stop_loss_take_profit()` 方法
- [ ] 代码审查和优化
- [ ] 添加文档字符串
- [ ] 运行测试，确保通过
- [ ] 检查覆盖率，确保 > 90%（鼠标事件允许稍低）
- [ ] 提交代码: `git commit -m "feat: extract mouse events to mixin"`

### 5.4 集成到主类
- [ ] 在 `widget.py` 中导入 `ChartWidgetMouseMixin`
- [ ] 更新 `ChartWidget` 类继承
- [ ] 从 `widget.py` 删除已移动的方法
- [ ] 运行集成测试
- [ ] 验证功能正常

---

## 📈 阶段6: 拆分图表更新模块（TDD）

### 6.1 红（Red）- 编写测试用例
- [ ] 创建 `tests/chart/test_widget_chart.py`
- [ ] 测试 `update_history()` - 更新历史数据
- [ ] 测试 `update_bar()` - 更新单根K线
- [ ] 测试 `update_bar()` - 自动跟随
- [ ] 测试 `_update_plot_limits()` - 更新图表限制
- [ ] 测试 `_update_x_range()` - 更新X轴范围
- [ ] 测试 `_update_y_range()` - 更新Y轴范围
- [ ] 测试 `paintEvent()` - 绘制事件
- [ ] 测试 `wheelEvent()` - 滚轮缩放
- [ ] 测试 `_on_key_left()` - 左移
- [ ] 测试 `_on_key_right()` - 右移
- [ ] 测试 `_on_key_up()` - 放大
- [ ] 测试 `_on_key_down()` - 缩小
- [ ] 测试 `move_to_right()` - 移动到最右侧
- [ ] 运行测试，确认失败（红）

### 6.2 绿（Green）- 实现模块
- [ ] 创建 `widget_chart.py`
- [ ] 实现 `ChartWidgetChartMixin` 类
- [ ] 从 `widget.py` 复制所有图表更新相关方法
- [ ] 调整导入和依赖
- [ ] 运行测试，确认通过（绿）

### 6.3 重构（Refactor）- 优化代码
- [ ] 代码审查和优化
- [ ] 添加文档字符串
- [ ] 运行测试，确保通过
- [ ] 检查覆盖率，确保 > 95%
- [ ] 提交代码: `git commit -m "feat: extract chart update logic to mixin"`

### 6.4 集成到主类
- [ ] 在 `widget.py` 中导入 `ChartWidgetChartMixin`
- [ ] 更新 `ChartWidget` 类继承
- [ ] 从 `widget.py` 删除已移动的方法
- [ ] 运行集成测试
- [ ] 验证功能正常

---

## 💾 阶段7: 拆分数据库模块（TDD）

### 7.1 红（Red）- 编写测试用例
- [ ] 创建 `tests/chart/test_widget_database.py`
- [ ] 测试 `_load_line_relations()` - 加载关联关系
- [ ] 测试 `_load_line_relations()` - 无效数据跳过
- [ ] 测试 `save_price_lines()` - 保存价格线
- [ ] 测试 `save_price_lines()` - 无vt_symbol返回False
- [ ] 测试 `load_price_lines()` - 加载价格线
- [ ] 测试 `load_price_lines()` - 无vt_symbol返回False
- [ ] 运行测试，确认失败（红）

### 7.2 绿（Green）- 实现模块
- [ ] 创建 `widget_database.py`
- [ ] 实现 `ChartWidgetDatabaseMixin` 类
- [ ] 从 `widget.py` 复制 `_load_line_relations()` 方法
- [ ] 从 `widget.py` 复制 `save_price_lines()` 方法
- [ ] 从 `widget.py` 复制 `load_price_lines()` 方法
- [ ] 调整导入和依赖
- [ ] 运行测试，确认通过（绿）

### 7.3 重构（Refactor）- 优化代码
- [ ] 代码审查和优化
- [ ] 添加文档字符串
- [ ] 运行测试，确保通过
- [ ] 检查覆盖率，确保 > 95%
- [ ] 提交代码: `git commit -m "feat: extract database operations to mixin"`

### 7.4 集成到主类
- [ ] 在 `widget.py` 中导入 `ChartWidgetDatabaseMixin`
- [ ] 更新 `ChartWidget` 类继承
- [ ] 从 `widget.py` 删除已移动的方法
- [ ] 运行集成测试
- [ ] 验证功能正常

---

## 🎯 阶段8: 移动光标类（TDD）

### 8.1 红（Red）- 编写测试用例
- [ ] 创建 `tests/chart/test_widget_cursor.py`
- [ ] 测试 `ChartCursor.__init__()` - 初始化
- [ ] 测试 `ChartCursor._init_ui()` - UI初始化
- [ ] 测试 `ChartCursor._mouse_moved()` - 鼠标移动
- [ ] 测试 `ChartCursor._update_line()` - 更新线条
- [ ] 测试 `ChartCursor._update_label()` - 更新标签
- [ ] 测试 `ChartCursor.update_info()` - 更新信息
- [ ] 测试 `ChartCursor.move_right()` - 右移
- [ ] 测试 `ChartCursor.move_left()` - 左移
- [ ] 测试 `ChartCursor.clear_all()` - 清除所有
- [ ] 运行测试，确认失败（红）

### 8.2 绿（Green）- 移动类
- [ ] 创建 `widget_cursor.py`
- [ ] 从 `widget.py` 移动 `ChartCursor` 类
- [ ] 调整导入和依赖
- [ ] 在 `widget.py` 中导入 `ChartCursor`
- [ ] 运行测试，确认通过（绿）

### 8.3 重构（Refactor）- 优化代码
- [ ] 代码审查和优化
- [ ] 添加文档字符串
- [ ] 运行测试，确保通过
- [ ] 检查覆盖率，确保 > 95%
- [ ] 提交代码: `git commit -m "feat: move ChartCursor to separate file"`

---

## 🔗 阶段9: 集成测试和最终验证

### 9.1 更新导入和导出
- [ ] 更新 `widget.py` 的导入语句
- [ ] 更新 `__init__.py` 的导出
- [ ] 验证所有导入正确
- [ ] 运行代码检查工具（flake8, pylint）

### 9.2 集成测试
- [ ] 创建 `tests/chart/test_widget_integration.py`
- [ ] 测试所有模块的集成
- [ ] 测试端到端场景
- [ ] 测试真实使用场景
- [ ] 运行所有测试，确保通过

### 9.3 覆盖率验证
- [ ] 运行覆盖率报告: `pytest --cov=vnpy.chart --cov-report=html`
- [ ] 检查总体覆盖率，确保 > 95%
- [ ] 检查各模块覆盖率
- [ ] 修复覆盖率不足的部分
- [ ] 生成最终覆盖率报告

### 9.4 性能测试
- [ ] 对比重构前后的性能
- [ ] 测试内存使用情况
- [ ] 测试启动时间
- [ ] 测试响应时间
- [ ] 记录性能指标

### 9.5 代码质量检查
- [ ] 检查所有文件行数，确保 < 1500行
- [ ] 运行代码格式化工具（black）
- [ ] 运行类型检查工具（mypy）
- [ ] 代码审查
- [ ] 修复所有问题

### 9.6 文档更新
- [ ] 更新 `README.md`（如果有）
- [ ] 更新代码注释
- [ ] 更新 API 文档
- [ ] 创建重构说明文档
- [ ] 更新变更日志

### 9.7 最终提交
- [ ] 运行所有测试: `pytest tests/chart/`
- [ ] 检查覆盖率: `coverage report`
- [ ] 代码审查
- [ ] 提交最终代码: `git commit -m "feat: complete widget refactoring"`
- [ ] 创建 Pull Request
- [ ] 等待代码审查和合并

---

## 📊 进度跟踪

### 总体进度
- [ ] 阶段0: 测试环境准备 (0/5)
- [ ] 阶段1: 创建 Mixin 基类 (0/3)
- [ ] 阶段2: 拆分持仓管理模块 (0/4)
- [ ] 阶段3: 拆分订单处理模块 (0/4)
- [ ] 阶段4: 拆分触发模块 (0/4)
- [ ] 阶段5: 拆分鼠标事件模块 (0/4)
- [ ] 阶段6: 拆分图表更新模块 (0/4)
- [ ] 阶段7: 拆分数据库模块 (0/4)
- [ ] 阶段8: 移动光标类 (0/3)
- [ ] 阶段9: 集成测试和最终验证 (0/7)

### 关键指标
- [ ] 所有文件 < 1500行
- [ ] 测试覆盖率 > 95%
- [ ] 所有测试通过
- [ ] 性能无明显下降
- [ ] 外部 API 保持不变

---

## 📝 注意事项

1. **严格按照 TDD 红绿灯模式**
   - 先写测试（红）→ 实现功能（绿）→ 重构优化（蓝）
   - 每个阶段都要确保测试通过

2. **测试覆盖率要求**
   - 总体覆盖率 > 95%
   - 每个模块拆分后立即检查覆盖率
   - 覆盖率不足时补充测试用例

3. **代码提交规范**
   - 每个模块完成后提交一次
   - 提交信息清晰描述变更
   - 保持提交历史清晰

4. **功能验证**
   - 每个模块集成后立即验证功能
   - 运行集成测试
   - 手动测试关键功能

5. **回滚计划**
   - 如果出现问题，可以回滚到备份
   - 保持重构分支独立
   - 主分支不受影响

---

## 🎯 完成标准

重构完成需要满足以下所有条件：

- ✅ 所有文件 < 1500行
- ✅ 测试代码覆盖率 > 95%
- ✅ 所有测试用例通过（pytest）
- ✅ 所有功能正常工作
- ✅ 性能无明显下降（< 5%）
- ✅ 外部 API 保持不变
- ✅ 代码审查通过
- ✅ 文档更新完成

---

**开始日期**: _______________
**预计完成日期**: _______________
**实际完成日期**: _______________
