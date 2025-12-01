# 止损/止盈重复下单问题修复报告

**日期**: 2025-12-01  
**问题**: 止损线触发后，在执行过程中重复下单导致错误持仓  
**状态**: ✅ 已修复

---

## 问题描述

**用户报告**:
> 画线成交一手空单，止损线触发后，在执行过程中多下了一手买多，导致空仓平完后，反而成了持仓一手多

**问题表现**:
1. 止损线触发，发送第一个平仓订单（订单6454945）
2. 3秒后防抖过期，但第一个订单还未成交
3. 止损线再次触发，发送第二个平仓订单（订单6454947）
4. 第一个订单成交，空仓被平
5. 第二个订单成交，反而开了新仓（多仓）

---

## 根本原因分析

### 1. 防抖时间过短
- **问题**: 防抖时间只有3秒，但订单可能需要更长时间才能成交
- **影响**: 3秒后防抖过期，系统认为可以再次触发

### 2. 订单检查未支持主力合约映射
- **问题**: 检查未成交订单时，只检查 `order.vt_symbol == vt_symbol`
- **实际情况**:
  - `vt_symbol` 是主力合约（如 `MHImain.HKFE`）
  - 订单的 `order.vt_symbol` 是实际合约（如 `MHI2512.HKFE`）
- **影响**: 检查不到已存在的未成交订单，导致重复下单

**日志证据**:
```
22:40:55.776 - [实时止损触发] 止损线触发，下单6454945（多单，平空仓）
22:40:59.061 - 止损线再次触发（3.3秒后，超过3秒防抖），下单6454947
```

---

## 修复方案

### 1. 增强订单检查逻辑（支持主力合约映射）

在检查未成交订单时，支持主力合约映射匹配，**复用现有的缓存机制**：

```python
# 获取主力合约映射（复用已有缓存机制）
# _get_main_contract_mapping 返回 main_vt_symbol -> actual_vt_symbol 的映射
# 例如：{"MHImain.HKFE": "MHI2512.HKFE"}
main_contract_mapping = {}
if hasattr(self, '_get_main_contract_mapping'):
    # 复用现有的缓存方法（使用gateway的缓存）
    mapping = self._get_main_contract_mapping(main_engine)
    # 提取actual_symbol（从actual_vt_symbol中提取symbol部分）
    from vnpy.trader.utility import extract_vt_symbol
    for main_vt_symbol_key, actual_vt_symbol in mapping.items():
        try:
            actual_symbol, _ = extract_vt_symbol(actual_vt_symbol)
            main_contract_mapping[main_vt_symbol_key] = actual_symbol
        except:
            pass

# 检查是否已有同方向的平仓订单（未成交），支持主力合约映射
existing_close_orders = []
for order in all_active_orders:
    if order.direction == close_direction and order.offset == Offset.CLOSE and order.is_active():
        # 直接匹配
        if order.vt_symbol == vt_symbol:
            existing_close_orders.append(order)
        # 主力合约映射匹配：图表是主力合约，订单是实际合约
        elif vt_symbol in main_contract_mapping:
            actual_symbol = main_contract_mapping[vt_symbol]
            if order.symbol == actual_symbol:
                # 检查exchange是否匹配
                from vnpy.trader.utility import extract_vt_symbol
                try:
                    _, order_exchange = extract_vt_symbol(order.vt_symbol)
                    _, chart_exchange = extract_vt_symbol(vt_symbol)
                    if order_exchange == chart_exchange:
                        existing_close_orders.append(order)
                except:
                    pass
```

**关键优化**:
- ✅ **复用 `_get_main_contract_mapping` 方法**: 该方法已实现缓存机制，直接使用gateway的缓存，无需重复查询
- ✅ **性能优化**: 避免每次触发时都遍历所有gateway，直接使用缓存的映射结果

### 2. 改进防抖逻辑

- **保持3秒防抖**: 3秒内直接跳过（避免频繁检查）
- **3秒后检查未成交订单**: 即使防抖过期，如果发现有未成交的平仓订单，也要跳过并更新防抖时间

```python
# 检查是否已有触发记录（防抖：3秒内不重复触发）
if hasattr(self, '_trigger_records'):
    last_trigger_time = self._trigger_records.get(trigger_key, 0)
    time_since_trigger = current_time - last_trigger_time
    
    # 如果防抖期内，直接跳过
    if time_since_trigger < 3.0:  # 3秒内直接跳过
        return False

# ... 检查未成交订单 ...

if existing_close_orders:
    # 已有未成交的平仓订单，跳过（并更新防抖时间）
    self._trigger_records[trigger_key] = current_time
    return False
```

---

## 修复内容

### 修改文件
- `vnpy/chart/widget_trigger.py`

### 修改的方法
1. **`trigger_stop_loss_close`**: 止损线触发平仓
2. **`trigger_take_profit_close`**: 止盈线触发平仓

### 关键改进
1. ✅ **支持主力合约映射的订单检查**: 可以正确识别实际合约的未成交订单
2. ✅ **复用缓存机制**: 使用 `_get_main_contract_mapping` 方法，复用gateway的缓存，提高性能
3. ✅ **改进防抖逻辑**: 即使防抖过期，也会检查未成交订单
4. ✅ **动态更新防抖时间**: 发现未成交订单时，更新防抖时间，避免频繁检查

---

## 验证要点

### 测试场景1: 止损触发，订单未成交时再次触发
1. 设置止损线，触发平仓
2. 3秒后，如果订单还未成交，止损线再次被触发
3. **期望**: 系统检测到未成交订单，跳过触发

### 测试场景2: 主力合约映射场景
1. 图表显示主力合约（如 `MHImain.HKFE`）
2. 实际持仓和订单是实际合约（如 `MHI2512.HKFE`）
3. 止损触发，订单未成交时再次触发
4. **期望**: 系统通过主力合约映射检测到未成交订单，跳过触发

### 测试场景3: 防抖保护
1. 止损触发后，3秒内再次触发
2. **期望**: 直接跳过（不检查订单，提高性能）

---

## 预期效果

修复后的行为：
1. ✅ **止损触发后**: 发送平仓订单
2. ✅ **3秒内再次触发**: 直接跳过（防抖保护）
3. ✅ **3秒后再次触发**: 
   - 检查是否有未成交的平仓订单
   - 如果订单存在（即使防抖过期），跳过触发并更新防抖时间
   - 如果订单不存在，允许触发（订单可能已成交或撤销）
4. ✅ **支持主力合约映射**: 正确识别实际合约的未成交订单

---

## 相关文件

- `vnpy/chart/widget_trigger.py`: 止损/止盈触发逻辑
- `vnpy/chart/widget_order.py`: 订单处理和主力合约映射逻辑

---

## 总结

**修复前**:
- 防抖过期后，无法正确识别未成交订单（主力合约映射问题）
- 导致重复下单，错误持仓

**修复后**:
- 支持主力合约映射的订单检查
- 即使防抖过期，也会检查未成交订单
- 有效防止重复下单

**修复状态**: ✅ 已完成

