# ChartWidget 重构 - 快速参考

## 📋 任务概览

| 阶段 | 名称 | 预计天数 | 状态 | 进度 |
|------|------|---------|------|------|
| 0 | 测试环境准备 | 2 | ⏳ 待开始 | 0% |
| 1 | 创建 Mixin 基类 | 1 | ⏳ 待开始 | 0% |
| 2 | 拆分持仓管理模块 | 3 | ⏳ 待开始 | 0% |
| 3 | 拆分订单处理模块 | 2 | ⏳ 待开始 | 0% |
| 4 | 拆分触发模块 | 2 | ⏳ 待开始 | 0% |
| 5 | 拆分鼠标事件模块 | 2 | ⏳ 待开始 | 0% |
| 6 | 拆分图表更新模块 | 1 | ⏳ 待开始 | 0% |
| 7 | 拆分数据库模块 | 1 | ⏳ 待开始 | 0% |
| 8 | 移动光标类 | 1 | ⏳ 待开始 | 0% |
| 9 | 集成测试和最终验证 | 3 | ⏳ 待开始 | 0% |
| **总计** | | **17** | | **0%** |

## 🎯 关键指标

- [ ] 所有文件 < 1500行
- [ ] 测试代码覆盖率 > 95%
- [ ] 所有测试用例通过
- [ ] 性能无明显下降
- [ ] 外部 API 保持不变

## 🔄 TDD 红绿灯模式

每个模块拆分遵循：

1. **🔴 红（Red）**: 先写失败的测试用例
2. **🟢 绿（Green）**: 写最少的代码让测试通过
3. **🔵 重构（Refactor）**: 优化代码，保持测试通过

## 📁 文件结构

```
vnpy/chart/
├── widget.py              # 主类 (~600行) ✅
├── widget_mixin_base.py   # Mixin基类 (~50行) ✅
├── widget_position.py     # 持仓管理 (~1200行) ✅
├── widget_order.py        # 订单处理 (~600行) ✅
├── widget_trigger.py      # 触发下单/平仓 (~700行) ✅
├── widget_mouse.py        # 鼠标事件 (~900行) ✅
├── widget_chart.py        # 图表更新 (~500行) ✅
├── widget_database.py     # 数据库操作 (~200行) ✅
└── widget_cursor.py       # 光标类 (~270行) ✅

tests/chart/
├── conftest.py
├── test_base.py
├── test_widget.py
├── test_widget_position.py
├── test_widget_order.py
├── test_widget_trigger.py
├── test_widget_mouse.py
├── test_widget_chart.py
├── test_widget_database.py
├── test_widget_cursor.py
└── test_widget_integration.py
```

## 🚀 快速开始

### 1. 准备环境
```bash
# 安装测试工具
pip install pytest pytest-qt pytest-cov coverage

# 创建重构分支
git checkout -b refactor/widget-split

# 备份当前代码
cp vnpy/chart/widget.py vnpy/chart/widget.py.backup
```

### 2. 开始第一个任务
```bash
# 进入阶段0: 测试环境准备
# 参考 widget_refactor_tasks.md 中的详细步骤
```

### 3. 运行测试
```bash
# 运行所有测试
pytest tests/chart/

# 运行测试并生成覆盖率报告
pytest tests/chart/ --cov=vnpy.chart --cov-report=html

# 查看覆盖率报告
open htmlcov/index.html
```

## 📝 任务状态标记

- ⏳ 待开始 (pending)
- 🔄 进行中 (in_progress)
- ✅ 已完成 (completed)
- ⚠️ 阻塞 (blocked)
- ❌ 失败 (failed)

## 📚 相关文档

- `widget_refactor_plan.md` - 详细重构计划
- `widget_refactor_analysis.md` - 代码分析和行数统计
- `widget_refactor_tdd_strategy.md` - TDD测试策略
- `widget_refactor_tasks.md` - 详细任务清单
- `widget_refactor_tasks.json` - JSON格式任务列表
- `重构评估总结.md` - 中文总结文档

## ⚡ 常用命令

```bash
# 运行测试
pytest tests/chart/

# 运行测试并显示覆盖率
pytest tests/chart/ --cov=vnpy.chart --cov-report=term-missing

# 生成HTML覆盖率报告
pytest tests/chart/ --cov=vnpy.chart --cov-report=html

# 检查代码行数
find vnpy/chart/widget*.py -exec wc -l {} \;

# 代码格式化
black vnpy/chart/

# 类型检查
mypy vnpy/chart/
```

## 🎯 当前阶段

**阶段**: 0 - 测试环境准备
**下一步**: 安装测试工具

## 📊 进度统计

- **总任务数**: 42
- **已完成**: 0
- **进行中**: 0
- **待开始**: 42
- **完成率**: 0%

---

**最后更新**: 2024-01-01
**负责人**: _______________

