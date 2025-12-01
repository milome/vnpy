# Speckit 多模块开发最佳实践

## 📋 概述

本文档总结了在同一项目的不同模块中使用 Speckit 来开发不同功能的最佳实践。Speckit 是一个用于管理项目规范文档的工具，通过标准化的文档结构（`.speckit.*` 文件）来指导 AI 助手进行功能开发。

## ✅ 可行性确认

**完全可行！** 在同一项目的不同模块中使用 Speckit 开发不同功能不仅可行，而且是推荐的做法。

### 实际案例

当前项目中已有成功案例：
- `multi-timeframe-webapp/` 模块：使用完整的 Speckit 文件集（`.speckit.constitution`、`.speckit.specify`、`.speckit.plan`、`.speckit.clarify`）
- `specs/001-mhi-cta-backtest/` 目录：使用 Markdown 格式的规范文档

## 🏗️ 推荐的组织方式

### 方案 1：每个模块独立的 Speckit 文件集（推荐）⭐

适用于：独立的模块、子项目或功能完整的组件

```
vnpy/
├── multi-timeframe-webapp/          # 模块1：多周期Web应用
│   ├── .speckit.constitution        # 项目宪章（模块级）
│   ├── .speckit.specify             # 功能规格说明
│   ├── .speckit.plan                # 实施计划
│   ├── .speckit.clarify             # 决策和澄清文档
│   └── frontend/                    # 实际代码
│
├── vnpy_ctastrategy/                # 模块2：CTA策略模块
│   ├── .speckit.constitution
│   ├── .speckit.specify
│   ├── .speckit.plan
│   └── .speckit.clarify
│
├── vnpy_algotrading/                # 模块3：算法交易模块
│   ├── .speckit.constitution
│   ├── .speckit.specify
│   └── ...
│
└── vnpy_datamanager/                # 模块4：数据管理模块
    └── ...
```

**优点：**
- ✅ 模块完全独立，互不干扰
- ✅ AI 助手在模块目录工作时自动读取对应的 Speckit 文件
- ✅ 每个模块可以有自己的开发规范和标准
- ✅ 便于模块级别的版本管理和文档维护

### 方案 2：集中管理规范文档（适合大型功能）

适用于：跨模块的大型功能、需要统一管理的规范文档

```
vnpy/
├── specs/                            # 集中管理规范文档
│   ├── 001-mhi-cta-backtest/        # 功能1：MHI回测系统
│   │   ├── .speckit.constitution
│   │   ├── .speckit.specify
│   │   ├── .speckit.plan
│   │   └── .speckit.clarify
│   │
│   ├── 002-new-feature/             # 功能2：新功能
│   │   ├── .speckit.constitution
│   │   ├── .speckit.specify
│   │   └── ...
│   │
│   └── 003-another-feature/         # 功能3：另一个功能
│       └── ...
│
└── [实际代码模块]
```

**优点：**
- ✅ 所有规范文档集中管理，便于查找
- ✅ 适合跨多个模块的大型功能
- ✅ 便于项目级别的规划和协调

### 方案 3：混合方式（实际推荐）

结合方案 1 和方案 2，根据实际情况选择：

- **独立模块/子项目**：使用方案 1，在模块根目录放置 `.speckit.*` 文件
- **功能规范文档**：使用方案 2，在 `specs/` 目录下管理
- **项目级规范**：在项目根目录或 `docs/` 目录统一管理

## 📝 Speckit 文件说明

### `.speckit.constitution` - 项目宪章

定义模块的基本规则、技术栈、代码风格和开发标准。

**内容示例：**
```markdown
# Project Constitution

## Project Overview
This is a [模块名称] module.

## Technology Stack
- Framework: [使用的框架]
- Database: [数据库类型]
- Testing: [测试框架]

## Code Style and Standards
- Naming conventions
- Code organization patterns
- Import ordering preferences

## Development Practices
- Testing requirements
- Error handling patterns
- Git workflow
```

### `.speckit.specify` - 功能规格说明

详细描述功能需求、用户故事、技术规格和 API 设计。

**内容示例：**
```markdown
# Feature Specifications

## Feature 1: [功能名称]

### Overview
功能描述和业务价值

### User Stories
- 作为[角色]，我希望[目标]，以便[价值]

### Requirements
#### Functional Requirements
1. 系统应该...
2. 用户应该能够...

#### Non-Functional Requirements
- Performance: [性能要求]
- Scalability: [可扩展性要求]
```

### `.speckit.plan` - 实施计划

制定开发计划、任务分解、时间安排和里程碑。

**内容示例：**
```markdown
# Implementation Plan

## Phase 1: [阶段名称]
- Task 1: [任务描述]
- Task 2: [任务描述]

## Phase 2: [阶段名称]
- Task 1: [任务描述]
```

### `.speckit.clarify` - 决策和澄清文档

记录关键决策、技术选型理由、问题澄清和变更日志。

**内容示例：**
```markdown
# Clarifications and Decisions

## Q1: [问题描述]
**Decision:** [决策内容]
**Rationale:** [决策理由]

## D1: [决策编号] - [决策标题]
**Date:** [日期]
**Context:** [背景]
**Decision:** [决策内容]
**Impact:** [影响分析]
```

## 🎯 最佳实践建议

### 1. 模块独立性原则

- ✅ **每个模块的 Speckit 文件只管理该模块的功能**
- ✅ **模块之间通过接口和约定进行交互，而不是直接依赖**
- ✅ **`.speckit.constitution` 可以继承项目级规范，但可以添加模块特定的规则**

**示例：**
```markdown
# 在模块的 .speckit.constitution 中
## Project-Specific Rules
- 继承项目级代码风格规范
- 本模块特定要求：使用 TypeScript strict mode
- 本模块特定要求：所有组件必须包含单元测试
```

### 2. 命名和组织规范

**模块级 Speckit 文件：**
- 位置：放在模块根目录
- 命名：`.speckit.constitution`、`.speckit.specify` 等
- 示例：`multi-timeframe-webapp/.speckit.specify`

**功能级 Speckit 文件：**
- 位置：放在 `specs/` 目录下
- 命名：`specs/001-feature-name/.speckit.specify`
- 编号：使用三位数字前缀便于排序

### 3. 文档引用和继承

**项目级规范：**
- 在项目根目录或 `docs/` 目录定义通用规范
- 各模块的 `.speckit.constitution` 引用项目级规范

**跨模块依赖：**
- 在 `.speckit.clarify` 中明确记录跨模块依赖关系
- 使用接口和抽象层减少直接依赖

**示例：**
```markdown
# 在模块的 .speckit.clarify 中
## D5: 跨模块依赖设计
**Context:** 本模块需要调用 vnpy_ctastrategy 模块的功能
**Decision:** 通过事件总线（EventEngine）进行通信，不直接导入
**Rationale:** 保持模块解耦，便于独立测试和维护
```

### 4. 版本控制和变更管理

- ✅ **所有 `.speckit.*` 文件都应该纳入 Git 版本控制**
- ✅ **重要变更在 `.speckit.clarify` 中记录变更日志**
- ✅ **使用有意义的提交信息，便于追踪变更历史**

**变更日志示例：**
```markdown
# 在 .speckit.clarify 中
## Changelog

### 2025-01-15
- D10: 决定使用 ECharts 替代 TradingView（性能考虑）
- Q5: 澄清了4小时K线时间边界划分规则

### 2025-01-10
- D8: 选择 React + TypeScript 作为前端技术栈
- Q3: 确认数据格式使用 CSV
```

### 5. AI 助手上下文管理

**工作原理：**
- 当在模块目录工作时，AI 助手会优先读取该模块的 Speckit 文件
- 确保每个模块的 Speckit 文件完整且准确

**最佳实践：**
- ✅ 在开始开发前，确保 Speckit 文件已创建并完善
- ✅ 定期更新 `.speckit.clarify`，记录开发过程中的决策
- ✅ 在 `.speckit.specify` 中保持功能需求的准确性

## ⚠️ 注意事项

### 1. 避免冲突

**模块隔离：**
- 不同模块的 Speckit 文件互不影响
- 每个模块可以有自己的技术栈和开发规范

**跨模块协调：**
- 如果功能涉及多个模块，在 `.speckit.clarify` 中明确记录
- 使用统一的接口规范，避免模块间直接耦合

### 2. 保持一致性

**项目级标准：**
- 在项目根目录或 `docs/` 目录定义通用标准
- 各模块的 `.speckit.constitution` 应遵循项目级标准

**代码风格：**
- 使用统一的代码格式化工具（如 Prettier、Black）
- 在项目级配置文件中定义，各模块继承

### 3. 文档维护

**及时更新：**
- 功能变更时及时更新 `.speckit.specify`
- 技术决策变更时更新 `.speckit.clarify`
- 计划调整时更新 `.speckit.plan`

**文档同步：**
- 确保 Speckit 文件与实际代码保持一致
- 定期审查文档的准确性

## 📚 实际应用示例

### 示例 1：独立模块使用 Speckit

**场景：** `multi-timeframe-webapp` 是一个独立的 Web 应用模块

**文件结构：**
```
multi-timeframe-webapp/
├── .speckit.constitution    # 定义：React + TypeScript + ECharts
├── .speckit.specify         # 定义：多周期K线图功能需求
├── .speckit.plan           # 定义：分阶段实施计划
├── .speckit.clarify        # 记录：技术选型决策
└── frontend/               # 实际代码
```

**优势：**
- AI 助手在 `multi-timeframe-webapp/` 目录工作时，自动读取该模块的 Speckit 文件
- 模块完全独立，可以有自己的开发节奏和技术栈

### 示例 2：功能规范文档管理

**场景：** MHI CTA 回测系统是一个跨模块的大型功能

**文件结构：**
```
specs/
└── 001-mhi-cta-backtest/
    ├── specification.md    # 功能规格（Markdown格式）
    └── plan.md            # 实施计划（Markdown格式）

# 或者使用 Speckit 格式：
specs/
└── 001-mhi-cta-backtest/
    ├── .speckit.constitution
    ├── .speckit.specify
    ├── .speckit.plan
    └── .speckit.clarify
```

**优势：**
- 集中管理大型功能的规范文档
- 便于项目级别的规划和协调
- 可以跨多个模块进行功能开发

## 🔄 工作流程建议

### 1. 新模块开发流程

1. **创建模块目录结构**
2. **创建 Speckit 文件集**
   - 复制项目级模板或参考现有模块
   - 根据模块特点定制 `.speckit.constitution`
3. **编写功能规格**
   - 在 `.speckit.specify` 中详细描述功能需求
4. **制定实施计划**
   - 在 `.speckit.plan` 中分解任务和阶段
5. **开始开发**
   - AI 助手会根据 Speckit 文件指导开发

### 2. 功能迭代流程

1. **更新功能规格**
   - 在 `.speckit.specify` 中更新需求
2. **记录决策**
   - 在 `.speckit.clarify` 中记录技术决策
3. **调整计划**
   - 在 `.speckit.plan` 中更新实施计划
4. **继续开发**
   - 保持文档与代码同步

## 📊 对比总结

| 特性 | 模块级 Speckit | 集中管理规范文档 |
|------|---------------|-----------------|
| **适用场景** | 独立模块/子项目 | 跨模块大型功能 |
| **文件位置** | 模块根目录 | `specs/` 目录 |
| **独立性** | 高 | 中 |
| **AI 上下文** | 自动识别 | 需要指定路径 |
| **维护成本** | 低 | 中 |
| **推荐度** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

## 🎓 总结

在同一项目的不同模块中使用 Speckit 开发不同功能是完全可行的，而且是推荐的最佳实践。关键要点：

1. ✅ **模块独立性**：每个模块可以有自己的 Speckit 文件集
2. ✅ **灵活组织**：根据实际情况选择模块级或集中管理方式
3. ✅ **文档同步**：保持 Speckit 文件与实际代码的一致性
4. ✅ **决策记录**：在 `.speckit.clarify` 中记录重要决策
5. ✅ **版本控制**：所有 Speckit 文件纳入 Git 管理

通过遵循这些最佳实践，可以充分利用 Speckit 来管理多模块项目的开发，提高开发效率和代码质量。

---

**文档版本：** 1.0  
**最后更新：** 2025-01-15  
**维护者：** vnpy 开发团队


