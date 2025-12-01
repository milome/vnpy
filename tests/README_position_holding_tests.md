# 持仓管理系统测试说明

## 概述

本测试套件用于验证持仓管理系统的核心功能，确保FIFO平仓逻辑、加权平均价格计算和合并显示功能正常工作。

## 快速开始

### 运行所有测试

**从项目根目录运行**（推荐）:
```bash
# 基本运行
pytest tests/test_position_holding.py -v

# 显示详细输出
pytest tests/test_position_holding.py -v -s

# 生成JUnit XML报告
pytest tests/test_position_holding.py -v --junit-xml=tests/test_position_holding_report.xml
```

**从 tests 目录运行**:
```bash
cd tests

# 基本运行（注意：不需要 tests/ 前缀）
pytest test_position_holding.py -v

# 或者使用相对路径
pytest ./test_position_holding.py -v
```

### 运行特定测试

**从项目根目录**:
```bash
# 运行特定测试类
pytest tests/test_position_holding.py::TestPositionHolding -v

# 运行特定测试方法
pytest tests/test_position_holding.py::TestPositionHolding::test_fifo_close_position_full -v

# 运行集成测试
pytest tests/test_position_holding.py::TestPositionHoldingIntegration -v
```

**从 tests 目录**:
```bash
cd tests

# 运行特定测试类
pytest test_position_holding.py::TestPositionHolding -v

# 运行特定测试方法
pytest test_position_holding.py::TestPositionHolding::test_fifo_close_position_full -v
```

## 测试覆盖范围

### 1. 基础功能测试
- ✅ 创建持仓管理对象
- ✅ 添加入场持仓记录
- ✅ 添加多个入场持仓记录
- ✅ 清空持仓记录
- ✅ 持仓记录按时间排序

### 2. FIFO平仓逻辑测试
- ✅ 完全平掉第一条持仓
- ✅ 部分平掉第一条持仓
- ✅ 平掉多条持仓（跨多条持仓）

### 3. 加权平均价格计算
- ✅ 不同价格、不同手数的加权平均价格计算

### 4. 辅助函数测试
- ✅ 添加持仓记录到持仓管理系统
- ✅ 从订单数据更新持仓记录
- ✅ 处理持仓平仓（FIFO）
- ✅ 边界情况处理（空持仓、全部平仓）

### 5. 集成场景测试
- ✅ 多条入场线合并显示
- ✅ FIFO部分平仓场景（2手多仓，平掉1手）
- ✅ 不同手数持仓的FIFO平仓

## 测试场景示例

### 场景1：多次开仓合并显示

```python
# 第一次开仓：1手@26040
holding.add_entry("line_1", 26040.0, 1.0, "FUTU.12345", t1)

# 第二次开仓：1手@26050
holding.add_entry("line_2", 26050.0, 1.0, "FUTU.12346", t2)

# 结果：加权平均价格 = (26040 + 26050) / 2 = 26045
# 总手数 = 2
```

### 场景2：FIFO部分平仓

```python
# 持仓：2手（1手@26040，1手@26050）
# 平掉1手

closed_entries = holding.close_position(1.0)

# 结果：先平掉26040的1手，剩余1手@26050
```

### 场景3：跨多条持仓平仓

```python
# 持仓：6手（2手@26040，1手@26050，3手@26030）
# 平掉4手

closed_entries = holding.close_position(4.0)

# 结果：
# - 平掉2手@26040（完全）
# - 平掉1手@26050（完全）
# - 平掉1手@26030（部分）
# 剩余：2手@26030
```

## 测试报告

测试报告文件：
- **JUnit XML报告**: `tests/test_position_holding_report.xml`
- **测试总结**: `tests/test_position_holding_summary.md`

## 持续集成

建议在CI/CD流程中运行这些测试，确保功能不会回退：

```yaml
# 示例 GitHub Actions 配置
- name: Run Position Holding Tests
  run: |
    pytest tests/test_position_holding.py -v --junit-xml=test-results.xml
```

## 注意事项

1. **时间顺序**: 测试中使用 `datetime.now()` 和 `timedelta` 来模拟时间顺序，确保FIFO逻辑正确
2. **精度问题**: 浮点数比较时使用 `abs(a - b) < 0.01` 来避免精度问题
3. **模拟数据**: 所有测试都使用模拟数据，不依赖实际交易系统

## 故障排查

### 测试失败

如果测试失败，检查：
1. 是否正确安装了所有依赖
2. 代码是否有语法错误
3. 测试数据是否正确

### 运行缓慢

如果测试运行缓慢，可以：
1. 使用 `-x` 选项在第一个失败时停止
2. 使用 `-k` 选项过滤测试
3. 使用 `--tb=short` 减少输出

## 贡献

添加新测试时，请确保：
1. 测试名称清晰描述测试内容
2. 测试覆盖边界情况
3. 测试独立运行（不依赖其他测试）
4. 测试使用有意义的断言消息

