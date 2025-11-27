# 麦语言解析器快速开始指南

## 概述

已创建完整的ANTLR解析器和代码生成系统，包括：

1. **语法文件**: `MFLang.g4` - ANTLR语法定义
2. **解析器生成脚本**: `generate_parser.py` - 自动生成ANTLR解析器
3. **AST访问者**: `ast_visitor.py` - 将解析树转换为AST
4. **代码生成器**: `code_generator.py` - 将AST转换为Python代码
5. **解析器包装**: `parser.py` - 统一的解析接口
6. **测试脚本**: `test_parser.py` - 测试解析和代码生成

## 快速开始

### 步骤1: 安装依赖

```bash
# 安装ANTLR Python运行时
pip install antlr4-python3-runtime

# 安装ANTLR工具（需要Java）
# 下载: https://www.antlr.org/download.html
# 或使用包管理器安装
```

### 步骤2: 生成解析器

```bash
# 方式1: 使用生成脚本（推荐）
cd mflang/grammar
python generate_parser.py

# 方式2: 手动生成
antlr4 -Dlanguage=Python3 -visitor MFLang.g4
```

这会生成以下文件：
- `MFLangLexer.py` - 词法分析器
- `MFLangParser.py` - 语法分析器
- `MFLangListener.py` - 监听器接口
- `MFLangVisitor.py` - 访问者接口

### 步骤3: 测试解析器

```bash
# 运行测试脚本
python mflang/grammar/test_parser.py
```

## 使用示例

### 示例1: 解析麦语言代码

```python
from mflang.grammar import parse_mflang_string

code = """
NUMOFDAY: BARPOS, NODRAW;
ISUPTREND := MAINTREND1M >= REF(MAINTREND1M,5), PRECIS0, NODRAW;
ISUPTREND,BP;
"""

# 解析代码
ast = parse_mflang_string(code)
print(f"AST根节点: {ast.node_type}")
print(f"语句数量: {len(ast.children)}")
```

### 示例2: 解析文件

```python
from mflang.grammar import parse_mflang_file

# 解析RICE1.txt
ast = parse_mflang_file("mflang/mmodels/RICE1.txt")
```

### 示例3: 生成Python代码

```python
from mflang.grammar import parse_mflang_string, StrategyCodeGenerator

# 解析
code = """
NUMOFDAY: BARPOS, NODRAW;
ISUPTREND := MAINTREND1M >= REF(MAINTREND1M,5), PRECIS0, NODRAW;
ISUPTREND,BP;
"""
ast = parse_mflang_string(code)

# 生成策略代码
generator = StrategyCodeGenerator("MyStrategy")
python_code = generator.generate(ast)
print(python_code)
```

## 文件结构

```
mflang/grammar/
├── MFLang.g4              # ANTLR语法文件
├── generate_parser.py    # 解析器生成脚本
├── parser.py              # 解析器包装类
├── ast_visitor.py         # AST访问者实现
├── code_generator.py      # 代码生成器
├── test_parser.py         # 测试脚本
├── __init__.py            # 模块初始化
├── README.md              # 详细文档
├── USAGE.md               # 使用指南
└── QUICKSTART.md          # 快速开始（本文件）

# 生成的文件（运行generate_parser.py后）
├── MFLangLexer.py         # 词法分析器（生成）
├── MFLangParser.py        # 语法分析器（生成）
├── MFLangListener.py      # 监听器接口（生成）
└── MFLangVisitor.py       # 访问者接口（生成）
```

## 核心组件说明

### 1. MFLang.g4
ANTLR语法定义文件，定义了麦语言的完整语法规则。

### 2. generate_parser.py
自动生成ANTLR解析器的脚本，检查依赖并生成解析器代码。

### 3. parser.py
解析器包装类，提供统一的解析接口：
- `parse_file()` - 解析文件
- `parse_string()` - 解析字符串

### 4. ast_visitor.py
AST访问者实现，将ANTLR解析树转换为AST（抽象语法树）：
- `ASTNode` - AST节点基类
- `ImportNode` - #IMPORT语句节点
- `VariableAssignNode` - 变量赋值节点
- `FunctionCallNode` - 函数调用节点
- 等等...

### 5. code_generator.py
代码生成器，将AST转换为Python代码：
- `CodeGenerator` - 基础代码生成器
- `StrategyCodeGenerator` - 策略代码生成器（生成完整策略类）

## 工作流程

```
麦语言代码
    ↓
[ANTLR词法分析] → 词法单元流
    ↓
[ANTLR语法分析] → 解析树
    ↓
[AST访问者] → AST（抽象语法树）
    ↓
[代码生成器] → Python代码
```

## 支持的语法特性

✅ **已支持**:
- #IMPORT语句
- VARIABLE声明
- 变量赋值（: 和 :=）
- 交易指令（BP, SP, BK, SK, BPK, SPK）
- T_COMMAND语句
- IF-THEN-BEGIN-END块
- 复杂嵌套表达式（16层+）
- 函数调用（REF, BARSLAST, SUMBARS, HHV, LLV等）
- 跨周期引用（VAR.VARNAME）
- 运算符（+, -, *, /, >, <, =, <>, &&, ||等）
- 中文变量名和注释

## 已知限制

1. **跨周期引用**: 当前返回占位符，需要根据实际跨周期数据管理器实现
2. **部分函数**: 某些特殊函数可能需要扩展代码生成器
3. **格式化选项**: 格式化选项在代码生成中被忽略（不影响功能）

## 下一步工作

1. **完善代码生成器**:
   - 实现跨周期引用的完整处理
   - 添加更多函数的代码生成
   - 优化生成的代码质量

2. **集成现有系统**:
   - 与 `strategy_generator.py` 集成
   - 与 `import_parser.py` 集成
   - 与 `model_loader.py` 集成

3. **测试和优化**:
   - 使用RICE1.txt进行完整测试
   - 性能优化
   - 错误处理改进

## 故障排除

### 问题1: ImportError - ANTLR解析器未生成

**解决方案**:
```bash
cd mflang/grammar
python generate_parser.py
```

### 问题2: 语法错误

**检查**:
1. 确保语法文件 `MFLang.g4` 正确
2. 检查麦语言代码是否符合语法规则
3. 查看ANTLR生成的错误信息

### 问题3: 代码生成不正确

**检查**:
1. AST是否正确构建（使用测试脚本验证）
2. 代码生成器是否正确处理所有节点类型
3. 查看生成的代码并手动验证

## 参考资源

- [ANTLR官方文档](https://github.com/antlr/antlr4)
- [ANTLR Python目标](https://github.com/antlr/antlr4/blob/master/doc/python-target.md)
- [麦语言语法文件](MFLang.g4)
- [详细使用指南](USAGE.md)

