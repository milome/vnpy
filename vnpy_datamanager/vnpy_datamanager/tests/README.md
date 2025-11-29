# DataManager 测试用例

本目录包含DataManager模块的完整测试用例。

## 测试结构

- `conftest.py`: pytest配置文件和共享fixtures
- `test_engine.py`: 测试ManagerEngine核心功能
- `test_widget.py`: 测试UI组件（ManagerWidget, UpdateProgressDialog）
- `test_integration.py`: 集成测试，测试完整的数据更新流程

## 运行测试

### 运行所有测试

```bash
pytest vnpy_datamanager/vnpy_datamanager/tests/
```

### 运行特定测试文件

```bash
# 测试引擎功能
pytest vnpy_datamanager/vnpy_datamanager/tests/test_engine.py

# 测试UI组件
pytest vnpy_datamanager/vnpy_datamanager/tests/test_widget.py

# 运行集成测试
pytest vnpy_datamanager/vnpy_datamanager/tests/test_integration.py
```

### 运行特定测试类或方法

```bash
# 运行特定测试类
pytest vnpy_datamanager/vnpy_datamanager/tests/test_widget.py::TestUpdateProgressDialog

# 运行特定测试方法
pytest vnpy_datamanager/vnpy_datamanager/tests/test_widget.py::TestUpdateProgressDialog::test_init
```

### 显示详细输出

```bash
pytest vnpy_datamanager/vnpy_datamanager/tests/ -v
```

### 显示覆盖率

```bash
pytest vnpy_datamanager/vnpy_datamanager/tests/ --cov=vnpy_datamanager --cov-report=html
```

## 测试覆盖的功能

### 1. UpdateProgressDialog（统一进度对话框）
- ✅ 对话框初始化
- ✅ 设置总任务数
- ✅ 更新进度
- ✅ 追加消息
- ✅ 设置完成状态

### 2. ManagerWidget（主界面）
- ✅ 初始化
- ✅ 自动更新开关（启用/禁用）
- ✅ 自动更新间隔设置
- ✅ 启动/停止自动更新
- ✅ 更新下次更新时间显示
- ✅ 数据更新功能
- ✅ 自动更新数据执行
- ✅ 防止重复更新
- ✅ 窗口关闭事件处理

### 3. ManagerEngine（核心引擎）
- ✅ 获取K线数据概览
- ✅ 下载1分钟K线数据
- ✅ 下载5分钟数据（从1分钟合成）
- ✅ 下载1小时数据（从1分钟合成）
- ✅ 下载4小时数据（从已有数据合成）
- ✅ 加载K线数据
- ✅ 删除K线数据
- ✅ 导出数据到CSV
- ✅ 合成5分钟K线
- ✅ 合成1小时K线
- ✅ 合成4小时K线

### 4. 集成测试
- ✅ 完整的数据更新流程
- ✅ 自动更新启用/禁用流程
- ✅ 自动更新执行流程

## 注意事项

1. **UI测试**: UI测试需要QApplication实例，测试会自动创建
2. **模拟对象**: 所有外部依赖（数据库、数据源等）都使用Mock对象
3. **异步测试**: 自动更新功能使用QTimer，测试中会验证定时器的启动和停止
4. **时间相关**: 测试中使用固定的时间戳，避免时间依赖问题

## 依赖

测试需要以下依赖：

```bash
pytest>=7.0.0
pytest-qt>=4.0.0  # 用于Qt应用测试
pytest-cov>=4.0.0  # 用于覆盖率报告（可选）
```

安装依赖：

```bash
pip install pytest pytest-qt pytest-cov
```

