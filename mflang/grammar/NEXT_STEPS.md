# 麦语言解析器下一步工作计划

## 当前状态总结

### ✅ 已完成

1. **ANTLR语法文件** (`MFLang.g4`)
   - ✅ 完整的语法定义
   - ✅ 支持所有主要语法特性
   - ✅ 支持嵌套IF和嵌套函数调用

2. **解析器生成**
   - ✅ 成功生成词法分析器 (MFLangLexer.py)
   - ✅ 成功生成语法分析器 (MFLangParser.py)
   - ✅ 成功生成访问者接口 (MFLangVisitor.py)

3. **AST访问者** (`ast_visitor.py`)
   - ✅ 完整的AST节点定义
   - ✅ 解析树到AST的转换
   - ✅ 支持所有节点类型

4. **代码生成器框架** (`code_generator.py`)
   - ✅ 基础代码生成结构
   - ✅ 策略类代码生成框架
   - ⚠️ 表达式转换需要完善

### ⚠️ 需要完善

1. **代码生成器细节**
   - 变量名到K线数据的映射
   - 复杂表达式的正确转换
   - 跨周期引用的完整处理

2. **集成现有系统**
   - 与 `strategy_generator.py` 集成
   - 替换正则表达式解析

3. **测试和验证**
   - RICE1.txt完整测试
   - 生成的代码功能验证

## 下一步工作计划

### 阶段1: 完善代码生成器（优先级：高）

#### 1.1 实现变量名映射

**目标**: 将麦语言变量名映射到实际的K线数据

**需要实现**:
- K线数据映射：`C`/`CLOSE` → `self.am.close`, `H`/`HIGH` → `self.am.high` 等
- 变量名映射：识别已定义的变量，使用 `self.var_name`
- 特殊函数映射：`BARPOS` → `BARPOS(self.am.close)`

**文件**: `code_generator.py`

**示例**:
```python
# 输入: MAINTREND1M:EMA(EMA(CLOSE,3),3), PRECIS3;
# 输出: self.MAINTREND1M = EMA(EMA(self.am.close, 3), 3)
```

#### 1.2 完善表达式转换

**目标**: 正确转换所有类型的表达式

**需要实现**:
- 二元运算符转换（`&&` → `and`, `||` → `or`, `=` → `==`, `<>` → `!=`）
- 一元运算符转换（`!` → `not`）
- 函数调用转换（处理所有函数类型）
- 括号表达式处理

**文件**: `code_generator.py` 的 `_generate_expression` 方法

#### 1.3 实现跨周期引用处理

**目标**: 完整处理 `VAR.VARNAME` 格式的跨周期引用

**需要实现**:
- 识别跨周期引用节点
- 生成从IndicatorManager获取数据的代码
- 处理数据对齐逻辑

**文件**: `code_generator.py` 的 `_generate_cross_period_ref` 方法

#### 1.4 处理IF-THEN-BEGIN-END块

**目标**: 生成IF-THEN块的Python代码

**需要实现**:
- 转换IF-THEN-BEGIN-END为Python if语句
- 处理块内的变量赋值

**文件**: `code_generator.py`

### 阶段2: 集成现有系统（优先级：高）

#### 2.1 创建新的策略生成器

**目标**: 基于ANTLR解析器创建新的策略生成器

**计划**:
- 创建 `strategy_generator_v2.py` 或更新现有生成器
- 使用ANTLR解析器替代正则表达式
- 保持与现有API的兼容性

**文件**: 新文件或更新 `strategy_generator.py`

#### 2.2 变量依赖分析

**目标**: 分析变量之间的依赖关系，确定计算顺序

**需要实现**:
- 构建变量依赖图
- 拓扑排序确定计算顺序
- 处理循环依赖检测

**文件**: 新文件 `dependency_analyzer.py`

#### 2.3 与现有函数集成

**目标**: 确保生成的代码正确使用mflang函数

**需要实现**:
- 验证函数调用映射
- 处理函数参数类型
- 确保数组操作正确

### 阶段3: 测试和优化（优先级：中）

#### 3.1 RICE1.txt完整测试

**目标**: 使用RICE1.txt进行完整测试

**计划**:
- 解析整个RICE1.txt文件
- 验证所有变量都能正确解析
- 检查AST构建的完整性
- 测试代码生成

**文件**: `test_rice1_full.py`

#### 3.2 生成的代码验证

**目标**: 验证生成的Python代码可以运行

**计划**:
- 生成策略代码
- 检查语法错误
- 运行基本功能测试
- 对比与现有生成器的输出

#### 3.3 性能优化

**目标**: 优化解析和代码生成性能

**计划**:
- 分析解析性能瓶颈
- 优化AST构建
- 优化代码生成

### 阶段4: 文档和工具（优先级：低）

#### 4.1 完善文档

**目标**: 编写完整的使用文档

**计划**:
- API文档
- 使用示例
- 故障排除指南

#### 4.2 开发工具

**目标**: 创建辅助开发工具

**计划**:
- AST可视化工具
- 语法检查工具
- 代码对比工具

## 详细实施步骤

### 步骤1: 实现变量映射（预计2-3小时）

```python
# 在 code_generator.py 中添加
class VariableMapper:
    """变量映射器"""
    
    KLINE_DATA_MAP = {
        'C': 'self.am.close',
        'CLOSE': 'self.am.close',
        'H': 'self.am.high',
        'HIGH': 'self.am.high',
        'L': 'self.am.low',
        'LOW': 'self.am.low',
        'O': 'self.am.open',
        'OPEN': 'self.am.open',
        'V': 'self.am.volume',
        'VOLUME': 'self.am.volume',
    }
    
    def map_identifier(self, identifier: str, defined_vars: set) -> str:
        """映射标识符"""
        # 检查是否是K线数据
        if identifier.upper() in self.KLINE_DATA_MAP:
            return self.KLINE_DATA_MAP[identifier.upper()]
        # 检查是否是已定义的变量
        elif identifier in defined_vars:
            return f"self.{identifier}"
        # 其他情况
        else:
            return identifier
```

### 步骤2: 完善表达式转换（预计3-4小时）

需要处理：
- 运算符转换表
- 函数调用参数转换
- 嵌套表达式处理
- 类型推断

### 步骤3: 实现依赖分析（预计2-3小时）

```python
class DependencyAnalyzer:
    """变量依赖分析器"""
    
    def analyze(self, ast: ASTNode) -> List[str]:
        """分析变量依赖，返回计算顺序"""
        # 构建依赖图
        # 拓扑排序
        # 返回计算顺序
        pass
```

### 步骤4: 集成测试（预计2-3小时）

- 使用简单模型测试
- 使用RICE1.txt测试
- 对比现有生成器

## 优先级排序

### 高优先级（立即开始）

1. **变量映射实现** - 代码生成的基础
2. **表达式转换完善** - 确保生成的代码正确
3. **RICE1.txt测试** - 验证实际场景

### 中优先级（第一阶段完成后）

4. **依赖分析** - 确保变量计算顺序正确
5. **跨周期引用完善** - 完整功能支持
6. **IF-THEN块处理** - 支持更多语法特性

### 低优先级（后续优化）

7. **性能优化** - 提升解析速度
8. **错误处理改进** - 更好的错误信息
9. **文档完善** - 使用指南

## 预期时间线

### 第1周
- ✅ 完成变量映射
- ✅ 完善表达式转换
- ✅ 基础代码生成测试

### 第2周
- ✅ 实现依赖分析
- ✅ 完善跨周期引用
- ✅ RICE1.txt完整测试

### 第3周
- ✅ 集成现有系统
- ✅ 性能优化
- ✅ 文档完善

## 成功标准

### 功能完整性
- ✅ 能够解析RICE1.txt的所有语法
- ✅ 能够生成可运行的Python代码
- ✅ 生成的代码功能正确

### 代码质量
- ✅ 生成的代码可读性好
- ✅ 错误处理完善
- ✅ 性能满足需求

### 集成度
- ✅ 与现有系统无缝集成
- ✅ 保持向后兼容
- ✅ API清晰易用

## 风险与挑战

### 技术风险
1. **复杂表达式转换** - 可能需要多次迭代
2. **跨周期引用** - 需要理解现有系统架构
3. **性能问题** - RICE1.txt很大，可能影响性能

### 缓解措施
1. 分阶段实施，逐步完善
2. 充分测试，及时发现问题
3. 性能测试和优化

## 下一步行动

### 立即开始（今天）

1. **实现变量映射器**
   - 创建 `VariableMapper` 类
   - 实现K线数据映射
   - 实现变量名映射

2. **完善表达式转换**
   - 修复运算符转换
   - 完善函数调用转换
   - 测试简单表达式

3. **创建测试用例**
   - 简单变量赋值测试
   - 嵌套函数调用测试
   - 复杂表达式测试

### 本周完成

4. **实现依赖分析**
5. **完善代码生成器**
6. **RICE1.txt基础测试**

## 参考资源

- 现有代码生成器: `mflang/strategy_generator.py`
- 函数实现: `mflang/functions/functions.py`
- 跨周期处理: `mflang/cross_period.py`
- 模型加载器: `mflang/model_loader.py`

