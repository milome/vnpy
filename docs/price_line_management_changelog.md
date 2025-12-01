# 价格线管理功能改进日志

## 概述

本文档记录了价格线管理功能的所有改进、bug修复和性能优化。包括从入场线拖拽创建止损/止盈线、数据库持久化、性能优化、订单处理优化等各个方面。

---

## 最新功能（2025-12-01）

### 挂单参数持久化

**功能描述：**
- 在数据库中持久化挂单参数（`order_volume`和`order_offset`），支持从数据库加载的挂单线也能触发模拟成交
- 重构触发逻辑，从价格线对象获取参数，减少对内存中`_pending_order_params`的依赖
- 简化触发逻辑，提高可靠性和可维护性

**实现位置：**
- `vnpy/chart/price_line_database.py`: 数据库迁移，添加`order_volume`和`order_offset`字段
- `vnpy/chart/price_line.py`: `PriceLineItem`添加挂单参数方法，`PriceLineManager`修改保存/加载逻辑
- `vnpy/chart/widget.py`: `trigger_pending_order_breakthrough()`重构，从价格线对象获取参数
- `vnpy/trader/ui/widget.py`: `_create_pending_order_line()`修改，保存挂单参数到价格线对象

**关键改进：**
- ✅ 数据库持久化：在`price_lines`表中添加`order_volume`和`order_offset`字段
- ✅ 价格线对象扩展：添加`get_order_volume()`、`set_order_volume()`、`get_order_offset()`、`set_order_offset()`方法
- ✅ 触发逻辑简化：优先从价格线对象获取参数，减少对内存的依赖
- ✅ 向后兼容：仍支持内存中的`_pending_order_params`，但优先使用价格线对象中的参数
- ✅ 程序重启后，从数据库加载的挂单线也能正常触发模拟成交

**详细分析文档：**
- `docs/pending_order_params_persistence_analysis.md` - 完整的持久化分析文档

---

### 挂单成交逻辑重构

**功能描述：**
- 将挂单成交逻辑提取到 `ChartWidget`，实现真实tickdata触发和模拟触发共用同一个逻辑
- 添加 `_pending_order_trigger_lock` RLock保护，避免同一个挂单线短时间内触发多次下单
- 重构 `simulate_trade_breakthrough()` 方法，简化代码结构

**实现位置：**
- `vnpy/chart/widget.py`: `trigger_pending_order_breakthrough()`, `_on_price_breakthrough()`
- `vnpy/trader/ui/widget.py`: `simulate_trade_breakthrough()`, `_on_price_breakthrough()`
- `vnpy/chart/price_breakthrough.py`: `BreakthroughEvent` 添加 `tick` 字段

**关键改进：**
- ✅ 真实tickdata触发和模拟触发共用同一个逻辑，确保行为一致
- ✅ RLock保护确保一次只有一个挂单线触发下单，避免竞态问题
- ✅ 代码结构更清晰，逻辑更集中，便于维护和测试
- ✅ `PriceBreakthroughMonitor` 在事件中传递tick数据，便于触发下单时获取价格信息

---

## 1. 核心功能实现

### 1.1 从入场线拖拽创建止损/止盈线

**功能描述：**
- 支持从已成交的入场线拖拽生成止损线或止盈线
- 根据拖拽方向自动判断是止损还是止盈（多仓：向下止损，向上止盈；空仓：向上止损，向下止盈）
- 自动设置止损/止盈线的手数与入场线一致

**实现位置：**
- `vnpy/chart/widget.py`: `mousePressEvent`, `mouseReleaseEvent`, `mouseMoveEvent`
- `vnpy/chart/price_line_drag.py`: 拖拽处理逻辑

**关键改进：**
- 在画线下单未启用时，允许从入场线拖拽创建止损/止盈线
- 在画线下单启用时，优先处理画线下单，不允许从入场线生成止损/止盈线
- 动态预览线类型切换，根据拖拽位置自动判断止损或止盈

---

### 1.2 双击入场线平仓功能

**功能描述：**
- 在画线下单未启用模式下，双击入场线可以触发平仓操作
- 自动获取当前持仓手数和对手价，发送平仓订单
- 支持防抖机制，防止短时间内重复触发

**实现位置：**
- `vnpy/chart/widget.py`: `mouseDoubleClickEvent`

**关键改进：**
- 添加防抖机制（2秒TTL），防止重复触发
- 添加确认对话框，防止误操作
- 双击止损/止盈线时只删除该线，不触发平仓
- 检测并取消正在进行的拖拽操作，避免干扰双击事件

---

### 1.3 价格线ID命名规范

**功能描述：**
- 统一价格线ID命名规范，使用类型前缀区分不同价格线
- 支持UUID和计数器两种ID生成策略

**命名规范：**
- `entry_` - 入场线
- `pending_` - 挂单线
- `stop_` - 止损线
- `profit_` - 止盈线
- `preview_` - 预览线

**实现位置：**
- `vnpy/chart/price_line.py`: `PriceLineManager.create_line()`

**关键改进：**
- 默认使用UUID生成唯一ID（`entry_a1b2c3d4e5f6`格式）
- 支持计数器模式，从数据库加载后自动初始化计数器
- 确保ID全局唯一，避免冲突

---

## 2. 数据库持久化

### 2.1 价格线数据库持久化

**功能描述：**
- 实现价格线的SQLite数据库持久化
- 支持价格线数据、关联关系、持仓记录的持久化存储
- 程序重启后自动恢复价格线和关联关系

**数据库设计：**

#### price_lines 表
- `line_id`: 价格线唯一ID（主键）
- `price`: 价格值
- `line_type`: 价格线类型
- `direction`: 交易方向
- `vt_symbol`: 合约标识
- `volume`: 手数
- `created_at`, `updated_at`: 时间戳

#### price_line_relations 表
- `entry_line_id`: 入场线ID
- `related_line_id`: 关联线ID（止损或止盈线）
- `relation_type`: 关联类型（stop_loss/take_profit）

#### position_entries 表
- `vt_symbol`: 合约标识
- `direction`: 方向
- `line_id`: 关联的入场线ID
- `price`: 入场价格
- `volume`: 持仓手数
- `trade_time`: 成交时间（用于FIFO排序）

**实现位置：**
- `vnpy/chart/price_line_database.py`: 数据库操作类
- `vnpy/chart/price_line.py`: 价格线管理器集成
- `vnpy/chart/widget.py`: 图表组件集成

**关键改进：**
- 自动保存创建、更新、删除的价格线
- 自动保存和加载关联关系
- 支持FIFO平仓的持仓记录持久化
- 数据库操作使用事务，确保数据一致性

---

### 2.2 ID去重和PositionHolding持久化

**问题：**
- 程序重启后计数器重置，可能导致ID冲突
- PositionHolding数据丢失，无法正确进行FIFO平仓

**解决方案：**
1. **UUID生成策略（默认）**
   - 使用UUID生成唯一ID，确保全局唯一性
   - 格式：`entry_a1b2c3d4e5f6`（使用hex前12位）

2. **计数器初始化策略**
   - 从数据库加载后，自动初始化计数器为最大ID+1
   - 确保新创建的ID不会与已存在的ID冲突

3. **PositionHolding持久化**
   - 持仓记录保存到数据库
   - 程序重启后自动恢复持仓记录
   - 支持FIFO平仓逻辑

**实现位置：**
- `vnpy/chart/price_line.py`: ID生成逻辑
- `vnpy/chart/price_line_database.py`: 持仓记录CRUD
- `vnpy/chart/widget_position_helper.py`: 持仓管理辅助函数

---

## 3. 性能优化

### 3.1 订单提交性能优化

**优化内容：**
1. **Tick数据缓存**
   - 实现100ms TTL的tick数据缓存
   - 减少重复的API调用
   - 优化位置：`vnpy_futu/vnpy_futu/futu_gateway.py`

2. **主力合约映射缓存**
   - 缓存主力合约到实际合约的映射关系
   - 避免重复查询API
   - 优化位置：`vnpy_futu/vnpy_futu/futu_gateway.py`

**性能提升：**
- 订单提交延迟从 ~222ms 降低到 ~100ms
- 减少了约50%的API调用

---

### 3.2 订单更新去重优化

**问题：**
- 订单更新事件可能被重复处理
- 导致挂单线、入场线被重复创建或删除

**解决方案：**
- 实现订单更新事件去重机制
- 使用 `order_key = f"{vt_orderid}_{status.value}"` 作为去重键
- TTL为1秒，确保短时间内相同事件只处理一次
- 对于"全部成交"状态，即使去重已标记，也要确保清理逻辑执行

**实现位置：**
- `vnpy/chart/widget.py`: `_on_order_update`, `_process_order_update`

**关键改进：**
- 防止重复处理订单更新事件
- 确保"全部成交"状态的清理逻辑总是执行
- 区分平仓和非平仓订单的处理逻辑

---

### 3.3 模拟成交优化

**问题：**
- 模拟成交时，异步回调时序问题导致模拟失败
- `update_tick` 异步执行，但立即检查结果

**解决方案：**
- 确保 `update_tick` 在主线程同步执行
- 同步检查 `_pending_order_params` 的移除结果

**实现位置：**
- `vnpy/trader/ui/widget.py`: `simulate_trade_breakthrough`

---

## 4. Bug修复

### 4.1 止损/止盈线关联关系清理

**问题：**
- 删除止损/止盈线时，数据库中的关联关系未被清理
- 导致出现"孤儿"关联关系

**修复：**
- 添加 `delete_relations_by_related_line_id` 方法
- 删除止损/止盈线时，同时清理数据库中的关联关系

**实现位置：**
- `vnpy/chart/price_line_database.py`: `delete_relations_by_related_line_id`
- `vnpy/chart/widget.py`: `_update_entry_line_pnl`

---

### 4.2 创建新止损/止盈线时未清理旧关联

**问题：**
- 从入场线拖拽创建新的止损/止盈线时，旧的同类型线未被删除
- 导致一个入场线关联多条止损线或止盈线

**修复：**
- 创建新的止损/止盈线前，先检查是否存在旧的同类型关联
- 如果存在，先删除旧的止损/止盈线和数据库关联关系
- 然后保存新的关联关系

**实现位置：**
- `vnpy/chart/widget.py`: `mouseReleaseEvent`

---

### 4.3 挂单线转换为入场线时的关联关系迁移

**问题：**
- 挂单线成交后转换为入场线时，关联的止损/止盈线未被正确迁移
- 挂单线ID和入场线ID相同时，导致关联关系被误删

**修复：**
- 确保 `create_entry_line` 生成新的UUID
- 迁移关联关系时，检查挂单线ID和入场线ID是否相同
- 只有在ID不同时才删除挂单线的关联关系

**实现位置：**
- `vnpy/chart/drawing_order.py`: `update_line_from_order`

---

### 4.4 订单更新去重导致的清理失败

**问题：**
- 订单更新去重机制导致"全部成交"状态的清理逻辑被跳过
- 挂单线和止损/止盈线未被删除

**修复：**
- 对于"全部成交"状态，即使去重已标记，也要确保清理逻辑执行
- 区分平仓和非平仓订单的处理逻辑
- 非平仓订单：迁移止损/止盈线到入场线
- 平仓订单：删除止损/止盈线

**实现位置：**
- `vnpy/chart/widget.py`: `_process_order_update`

---

### 4.5 合并持仓显示时止损/止盈线消失

**问题：**
- 多个持仓合并显示时，止损/止盈线被错误地迁移到主入场线
- 导致其他入场线的止损/止盈线消失

**修复：**
- 不再迁移止损/止盈线到主入场线
- 保持所有止损/止盈线可见
- 根据各自关联的入场线更新手数

**实现位置：**
- `vnpy/chart/widget.py`: `_update_entry_line_pnl`

---

### 4.6 从合并入场线拖拽时手数显示错误

**问题：**
- 从合并显示的入场线拖拽创建止损/止盈线时，手数显示不正确
- 初始显示总手数，但随后被刷新为单个入场线的手数

**修复：**
- 创建止损/止盈线时，如果入场线手数为0或很小，从PositionHolding获取总持仓手数
- 确保止损/止盈线的手数与总持仓手数一致

**实现位置：**
- `vnpy/chart/widget.py`: `mouseReleaseEvent`

---

### 4.7 挂单线和预览线未从plot中移除

**问题：**
- 删除挂单线和预览线时，只从管理器中删除，未从plot中移除
- 导致线条在图表上仍然可见

**修复：**
- 删除挂单线和预览线时，先调用 `removeItem` 从plot中移除
- 然后再从管理器中删除

**实现位置：**
- `vnpy/chart/drawing_order.py`: `update_line_from_order`, `_hide_preview_line`

---

### 4.8 NoneType错误修复

**问题：**
- `_price_line_manager` 或 `_price_line_database` 为 `None` 时导致 `AttributeError`

**修复：**
- 添加 `None` 检查
- 延迟初始化机制
- `get_price_line_manager()` 方法自动初始化

**实现位置：**
- `vnpy/chart/widget.py`: `clear_all`, `get_price_line_manager`
- `vnpy/chart/drawing_order.py`: `_get_price_line_manager`

---

### 4.9 预览线清理问题

**问题：**
- 预览线在某些情况下没有被正确清理，导致残留
- 画线下单模式关闭时，预览线可能残留
- 从入场线拖拽创建止损/止盈线时，预览线可能残留
- 按ESC键取消拖拽时，预览线可能残留

**修复：**
- 在 `PriceLineManager` 中添加 `clear_preview_lines()` 方法，用于清理所有预览线
- 在画线下单模式关闭时，自动清理所有预览线
- 在按ESC键取消拖拽时，清理所有预览线
- 在鼠标释放事件结束时，清理所有残留的预览线
- 改进从入场线拖拽时的预览线清理逻辑，确保从plot和管理器中都删除
- 清理拖拽处理器的预览线引用，避免内存泄漏

**实现位置：**
- `vnpy/chart/price_line.py`: `clear_preview_lines()`
- `vnpy/chart/drawing_order.py`: `disable()`
- `vnpy/chart/widget.py`: `keyPressEvent()`, `mouseReleaseEvent()`
- `vnpy/chart/price_line_drag.py`: `end_drag()`

---

## 5. 测试

### 5.1 数据库测试

**测试文件：**
- `tests/test_price_line_database.py`: 数据库操作单元测试
- `tests/test_price_line_id_and_position_persistence.py`: ID生成和持仓持久化测试

**测试覆盖：**
- 价格线CRUD操作
- 关联关系CRUD操作
- 持仓记录CRUD操作
- ID生成策略
- 数据持久化和恢复

---

## 6. 文档

### 6.1 已整合的文档

以下文档的内容已整合到本文档：
- `price_line_database_implementation.md` - 数据库实现文档
- `id_deduplication_and_position_persistence.md` - ID去重和持仓持久化
- `database_performance_analysis.md` - 数据库性能分析
- `order_submission_optimization_summary.md` - 订单提交优化总结
- `order_update_deduplication_optimization.md` - 订单更新去重优化
- `simulation_trade_optimization_analysis.md` - 模拟成交优化分析
- `drawing_order_performance_analysis.md` - 画线下单性能分析
- `画线下单功能实现总结.md` - 画线下单功能总结

---

## 7. 代码变更统计

### 7.1 新增文件
- `vnpy/chart/price_line_database.py` - 数据库操作类
- `tests/test_price_line_database.py` - 数据库测试
- `tests/test_price_line_id_and_position_persistence.py` - ID和持仓持久化测试

### 7.2 主要修改文件
- `vnpy/chart/price_line.py` - 价格线管理器，添加数据库支持
- `vnpy/chart/widget.py` - 图表组件，集成数据库和拖拽功能
- `vnpy/chart/drawing_order.py` - 画线下单控制器，关联关系迁移
- `vnpy/chart/price_line_drag.py` - 拖拽处理，支持从入场线拖拽
- `vnpy_futu/vnpy_futu/futu_gateway.py` - 性能优化（tick缓存、主力合约映射缓存）
- `vnpy/trader/ui/widget.py` - 模拟成交优化

---

## 8. 未来改进方向

### 8.1 功能增强
- [ ] 支持批量删除价格线
- [ ] 支持价格线分组管理
- [ ] 支持价格线模板保存和加载
- [ ] 支持价格线历史记录查看

### 8.2 性能优化
- [ ] 数据库查询优化（索引优化）
- [ ] 价格线渲染性能优化
- [ ] 大量价格线时的性能优化

### 8.3 用户体验
- [ ] 价格线右键菜单
- [ ] 价格线快捷键操作
- [ ] 价格线拖拽时的视觉反馈优化

---

## 9. 版本历史

### v1.0.0 (2025-11-30)
- ✅ 实现从入场线拖拽创建止损/止盈线
- ✅ 实现价格线数据库持久化
- ✅ 实现ID去重和PositionHolding持久化
- ✅ 实现双击入场线平仓功能
- ✅ 实现订单提交性能优化
- ✅ 实现订单更新去重机制
- ✅ 修复多个关联关系清理bug
- ✅ 修复挂单线转换时的关联关系迁移问题
- ✅ 统一价格线ID命名规范
- ✅ 修复预览线清理问题，防止预览线残留

---

## 10. 总结

本次改进实现了价格线管理的完整功能，包括：
1. **功能完善**：从入场线拖拽创建止损/止盈线、双击平仓等
2. **数据持久化**：价格线、关联关系、持仓记录全部持久化
3. **性能优化**：订单提交延迟降低50%，减少API调用
4. **Bug修复**：修复了多个关联关系管理和清理的问题，包括预览线清理问题
5. **代码质量**：添加了完整的测试覆盖，统一了代码规范

所有改进都经过了充分测试，确保了功能的稳定性和可靠性。

**最新修复（2025-11-30）：**
- 修复预览线清理问题，确保在画线下单模式关闭、按ESC键、鼠标释放等场景下都能正确清理所有预览线，防止预览线残留。

---

## 11. 模拟止损和模拟止盈功能（2025-12-01）

### 11.1 功能概述

新增模拟止损和模拟止盈功能，用于在休市时测试止损/止盈线的触发逻辑。配合已有的模拟成交功能，提供完整的模拟交易测试能力。

### 11.2 功能特性

**模拟止损功能：**
- 模拟tick数据触及止损线后，触发平仓事件
- 平仓手数使用止损线对应的手数（不超过持仓手数）
- 平仓采用对价平仓+智能追价（OPPONENT_Retry2）
- 使用RLock避免多条止损线同时触发时的竞态问题
- 当持仓数为0时，止损线不触发任何操作

**模拟止盈功能：**
- 模拟tick数据触及止盈线后，触发平仓事件
- 平仓手数使用止盈线对应的手数（不超过持仓手数）
- 平仓采用对价平仓+智能追价（OPPONENT_Retry2）
- 使用RLock避免多条止盈线同时触发时的竞态问题
- 当持仓数为0时，止盈线不触发任何操作

**按钮状态管理：**
- 三个模拟功能按钮（模拟成交、模拟止损、模拟止盈）
- 无tickdata时：三个按钮全部enabled（可用于休市测试）
- 有tickdata时：三个按钮全部disabled（避免与真实行情冲突）

### 11.3 实现位置

- `vnpy/chart/widget.py`: 
  - `trigger_stop_loss_close()` - 触发止损线平仓（通用方法，供真实tickdata和模拟触发共用）
  - `trigger_take_profit_close()` - 触发止盈线平仓（通用方法，供真实tickdata和模拟触发共用）
  - `_stop_loss_trigger_lock` - 保护止损线触发平仓逻辑的RLock
  - `_take_profit_trigger_lock` - 保护止盈线触发平仓逻辑的RLock

- `vnpy/trader/ui/widget.py`: 
  - `simulate_stop_loss()` - 模拟止损功能（创建模拟tick，调用ChartWidget的通用方法）
  - `simulate_take_profit()` - 模拟止盈功能（创建模拟tick，调用ChartWidget的通用方法）
  - `_update_simulate_buttons_state()` - 按钮状态管理
  - `process_tick_event()` - tick事件处理，更新按钮状态

### 11.4 关键实现细节

1. **RLock保护（重构后）**
   - RLock保护逻辑在 `ChartWidget` 中实现，保护的是"触发止损/止盈平仓"这个逻辑本身
   - 使用 `_stop_loss_trigger_lock` 保护止损线触发平仓逻辑
   - 使用 `_take_profit_trigger_lock` 保护止盈线触发平仓逻辑
   - 确保一次只有一个止损/止盈线触发平仓，避免竞态问题
   - **重要**：真实tickdata触发和模拟触发共用同一个触发逻辑和RLock保护，确保行为一致

2. **持仓检查**
   - 检查持仓是否存在且大于0
   - 检查可平仓手数（持仓手数 - 冻结手数）
   - 平仓手数取止损/止盈线手数和可平仓手数的最小值

3. **对价平仓+智能追价**
   - 平多仓：使用买一价（bid_price_1）
   - 平空仓：使用卖一价（ask_price_1）
   - 订单reference设置为"OPPONENT_Retry2"，启用智能追价（重试2次）

4. **按钮状态管理**
   - 在 `register_event()` 中初始化按钮状态
   - 在 `switch_chart()` 和 `refresh_chart()` 中更新按钮状态
   - 在 `process_tick_event()` 中根据tick数据更新按钮状态

### 11.5 测试

**测试文件：**
- `tests/test_simulate_stop_loss_profit.py`: 模拟止损和模拟止盈功能测试

**测试覆盖：**
- 模拟止损功能（有持仓时触发平仓）
- 模拟止损功能（无持仓时不触发）
- 模拟止盈功能（有持仓时触发平仓）
- 模拟止盈功能（无持仓时不触发）
- 多条止损/止盈线时的RLock保护
- 按钮状态管理（无tickdata时enabled，有tickdata时disabled）

---

**最新功能（2025-12-01）：**
- 新增模拟止损功能，支持在休市时测试止损线触发逻辑
- 新增模拟止盈功能，支持在休市时测试止盈线触发逻辑
- 实现按钮状态管理，无tickdata时按钮enabled，有tickdata时按钮disabled
- **重构**：将止损/止盈触发逻辑统一到ChartWidget中，真实tickdata触发和模拟触发共用同一个逻辑和RLock保护
- RLock保护逻辑在ChartWidget中实现（`_stop_loss_trigger_lock` 和 `_take_profit_trigger_lock`），确保真实tickdata触发时也有RLock保护

---

## 12. 模拟成交功能重构分析（2025-12-01）

### 12.1 分析结果

经过分析，发现模拟成交功能与真实tickdata触发已经部分共用逻辑，但仍需重构：

**已共用逻辑：**
- ✅ 都使用 `PriceBreakthroughMonitor.update_tick()` 检测价格突破
- ✅ 都使用同一个回调函数 `_on_price_breakthrough` 处理突破事件

**需要改进：**
- ❌ 回调函数 `_on_price_breakthrough` 在 `widget.py` 中，而不是在 `ChartWidget` 中
- ❌ 缺少RLock保护，可能导致同一个挂单线短时间内触发多次下单
- ❌ 逻辑分散，不利于维护

### 12.2 竞态问题分析

**潜在竞态场景：**
1. **真实tickdata快速波动**：价格在挂单线附近快速波动，多个tick连续触发突破检测
2. **模拟成交与真实tickdata同时触发**：用户点击"模拟成交"按钮，同时收到真实tickdata
3. **多个挂单线同时触发**：多个挂单线价格相近，一个tick可能同时触发多个挂单线

**现有保护机制：**
- 在 `_on_price_breakthrough` 中，下单后会移除挂单参数并取消注册
- 但这只是"事后"保护，不能防止并发触发

### 12.3 重构建议

**建议：**
1. **提取通用逻辑到ChartWidget**
   - 创建 `trigger_pending_order_breakthrough()` 方法
   - 与止损/止盈触发逻辑保持一致的设计模式

2. **添加RLock保护**
   - 在 `ChartWidget` 中添加 `_pending_order_trigger_lock`
   - 保护挂单线触发下单逻辑，确保一次只有一个挂单线触发下单

3. **重构模拟成交方法**
   - 简化 `simulate_trade_breakthrough()` 方法
   - 只负责创建模拟tick数据，调用ChartWidget的通用方法

4. **重构真实tickdata触发**
   - 在 `ChartWidget` 中添加处理tick的方法
   - 与模拟触发共用同一个逻辑

**详细分析文档：**
- `docs/simulate_trade_breakthrough_refactoring_analysis.md` - 完整的重构分析文档

---

**分析完成（2025-12-01）：**
- 完成模拟成交功能重构分析，确认需要将挂单成交逻辑提取到ChartWidget
- 确认需要添加RLock保护，避免同一个挂单线短时间内触发多次下单
- 详细分析文档已保存到 `docs/simulate_trade_breakthrough_refactoring_analysis.md`

**重构完成（2025-12-01）：**
- ✅ 在 `ChartWidget` 中添加 `_pending_order_trigger_lock` RLock，保护挂单线触发下单逻辑
- ✅ 在 `ChartWidget` 中添加 `trigger_pending_order_breakthrough()` 通用方法，封装挂单成交逻辑
- ✅ 重构 `ChartWidget._on_price_breakthrough()` 方法，调用通用触发方法
- ✅ 重构 `widget.py` 中的 `_on_price_breakthrough()` 方法，调用 `ChartWidget` 的通用方法
- ✅ 重构 `simulate_trade_breakthrough()` 方法，直接调用 `ChartWidget.trigger_pending_order_breakthrough()`
- ✅ 修改 `PriceBreakthroughMonitor`，在 `BreakthroughEvent` 中添加 `tick` 字段，传递tick数据
- ✅ 确保真实tickdata触发（通过 `process_tick_event`）也使用 `ChartWidget` 的通用方法
- ✅ 所有挂单成交逻辑（真实tickdata触发和模拟触发）现在共用同一个方法和RLock保护

**重构效果：**
- 真实tickdata触发和模拟触发现在共用同一个逻辑，确保行为一致
- RLock保护确保一次只有一个挂单线触发下单，避免竞态问题
- 代码结构更清晰，逻辑更集中，便于维护和测试

**挂单参数持久化完成（2025-12-01）：**
- ✅ 数据库迁移：在`price_lines`表中添加`order_volume`和`order_offset`字段
- ✅ `PriceLineItem`扩展：添加`get_order_volume()`、`set_order_volume()`、`get_order_offset()`、`set_order_offset()`方法
- ✅ 数据库操作：修改`save_line()`和`load_lines()`方法，保存和加载挂单参数
- ✅ 触发逻辑重构：`trigger_pending_order_breakthrough()`优先从价格线对象获取参数，减少对内存的依赖
- ✅ 创建挂单时：同时保存挂单参数到价格线对象和数据库，保持向后兼容（内存中的`_pending_order_params`仍然保留）

**持久化效果：**
- 从数据库加载的挂单线现在也能正常触发模拟成交
- 触发逻辑简化，减少对内存中`_pending_order_params`的依赖
- 程序重启后，挂单线仍然可以正常触发
- 保持向后兼容，支持旧的内存中的挂单参数

