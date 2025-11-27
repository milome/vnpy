# MFLang 导入模型文件解析指南

本文档总结了解析 MFLang（麦语言）模型文件的问题、解决方案和完整流程。

## 1. 背景

MFLang 是一种用于定义交易策略的领域特定语言（DSL）。在解析 `RICE1.txt` 及其导入的子模型（如 `RICE1_DAY`）时，遇到了多个语法解析问题。

### 1.1 核心组件

- **ANTLR4**: 用于生成 MFLang 词法分析器和语法分析器
- **MFLang.g4**: 语法定义文件
- **ast_visitor.py**: 将 ANTLR 解析树转换为自定义 AST
- **code_generator.py**: 将 AST 转换为可执行的 Python 策略代码

## 2. 遇到的问题及解决方案

### 2.1 嵌套 IF-THEN-BEGIN-END 块

**问题**: MFLang 支持在 IF-THEN 块内嵌套另一个 IF-THEN 块，但原始语法不支持。

```mflang
IF TOTALKDATANUM < 88
THEN
BEGIN
    IF ISDOWNTREND = 1
    THEN
    BEGIN
        CURRENTTREND := -4;
    END
END
```

**错误信息**:
```
line 368:1 extraneous input 'IF' expecting {'END', ...}
```

**解决方案**: 修改 `blockStatement` 规则，添加 `ifThenBlock` 作为第一个分支：

```antlr
blockStatement
    : ifThenBlock
    | identifier (COLON | ASSIGN) expression (COMMA formatOption)* SEMICOLON?
    | formatOnlyStatement
    | emptyStatement
    ;
```

同时手动修改 `MFLangParser.py`，在 `blockStatement()` 方法开头检查 IF 关键字：

```python
def blockStatement(self):
    localctx = MFLangParser.BlockStatementContext(self, self._ctx, self.state)
    self.enterRule(localctx, 20, self.RULE_blockStatement)
    try:
        # Check if current token is IF - handle nested IF-THEN blocks
        if self._input.LA(1) == MFLangParser.IF:
            self.enterOuterAlt(localctx, 1)
            self.ifThenBlock()
        else:
            # 原有解析逻辑...
```

### 2.2 格式化输出语句

**问题**: MFLang 支持仅由标识符和格式化选项组成的语句，用于输出变量并应用格式。

```mflang
SETTLE, DOT, COLORYELLOW;
CONTROLAVERAGE:100, COLORRED, NODRAW;
```

**错误信息**:
```
line 134:10 missing ')' at ','
```

**解决方案**: 新增 `formatOnlyStatement` 规则：

```antlr
// 仅格式化选项组成的语句（例如 SETTLE, DOT, COLORYELLOW;）
formatOnlyStatement
    : identifier COMMA formatOption (COMMA? formatOption)* SEMICOLON?
    ;
```

### 2.3 绘图函数中的颜色参数

**问题**: `DRAWCOLORKLINE` 等绘图函数的参数可以是颜色常量，但原始语法将所有参数都当作表达式处理。

```mflang
DRAWCOLORKLINE(BARTYPE = 0 && CURRENTTREND = 4 && ISUP, COLORRED, 1), LINETHICK1;
```

**错误信息**:
```
line 526:57 mismatched input 'COLORRED' expecting {..., INTEGER, FLOAT, STRING, IDENTIFIER}
```

**解决方案**: 新增 `drawArg` 规则，允许参数为表达式或格式化选项：

```antlr
// 绘图函数参数：可以是表达式或格式化选项
drawArg: expression | formatOption;

// 绘图语句
drawStatement: drawFunction LPAREN drawArg (COMMA drawArg)* RPAREN (COMMA formatOption)* SEMICOLON?;
```

### 2.4 新增的格式化选项

**问题**: 原始语法缺少部分格式化选项和颜色常量。

**解决方案**: 在词法规则中添加缺失的 token：

```antlr
// 新增颜色
COLORPURPLE: 'COLORPURPLE';

// 新增格式选项
VOLSTICK: 'VOLSTICK';
ALIGN0: 'ALIGN0';
ALIGN1: 'ALIGN1';
ALIGN2: 'ALIGN2';
ALIGN3: 'ALIGN3';
ALIGN4: 'ALIGN4';
FONTSIZE10: 'FONTSIZE10';
FONTSIZE12: 'FONTSIZE12';
FONTSIZE14: 'FONTSIZE14';
DOTSTYLE: 'DOT';
```

并更新 `formatOption` 规则：

```antlr
formatOption
    : PRECIS0 | PRECIS1 | PRECIS2 | PRECIS3
    | NODRAW
    | COLORWHITE | COLORRED | COLORGREEN | COLORYELLOW
    | COLORLIGHTRED | COLORLIGHTGREEN | COLORCYAN | COLORBLUE | COLORPURPLE
    | LINETHICK1 | LINETHICK2 | LINETHICK3 | LINETHICK5
    | rgbFunction
    | DASH | DASHDOT | DASHDOTDOT | DOTSTYLE
    | VOLSTICK
    | ALIGN0 | ALIGN1 | ALIGN2 | ALIGN3 | ALIGN4
    | FONTSIZE10 | FONTSIZE12 | FONTSIZE14
    ;
```

### 2.5 Unicode 文件名问题

**问题**: 在 Windows PowerShell 中，包含中文字符的文件名（如 `米仓I号日内趋势`）可能导致编码问题。

**解决方案**: 将文件重命名为 ASCII 兼容的名称（如 `RICE1_DAY`）。

## 3. 完整解析流程

### 3.1 文件结构

```
mflang/
├── grammar/
│   ├── MFLang.g4           # ANTLR 语法定义
│   ├── MFLangLexer.py      # 生成的词法分析器
│   ├── MFLangParser.py     # 生成的语法分析器
│   ├── ast_visitor.py      # AST 访问器
│   ├── code_generator.py   # 代码生成器
│   └── parser.py           # 解析器包装类
└── mmodels/
    ├── RICE1.txt           # 主模型文件
    └── RICE1_DAY           # 导入的子模型
```

### 3.2 解析步骤

1. **词法分析**: `MFLangLexer` 将源代码转换为 token 流
2. **语法分析**: `MFLangParser` 将 token 流转换为解析树
3. **AST 构建**: `MFLangASTVisitor` 遍历解析树，构建自定义 AST
4. **代码生成**: `StrategyCodeGenerator` 将 AST 转换为 Python 策略代码

### 3.3 重新生成解析器

当修改 `MFLang.g4` 后，需要重新生成解析器：

```powershell
cd d:\Dev\vnpy
& "D:\Program Files\Java\jdk-25\bin\java.exe" -jar d:\Dev\vnpy\jars\antlr-4.13.2-complete.jar -Dlanguage=Python3 -visitor mflang\grammar\MFLang.g4
```

### 3.4 测试解析

使用测试脚本验证解析结果：

```python
from mflang.grammar.parser import MFLangParserWrapper

parser = MFLangParserWrapper()
ast = parser.parse_file("mflang/mmodels/RICE1_DAY")
print(f"Parsed: {bool(ast)}")
```

## 4. 关键语法规则总结

### 4.1 语句类型

```antlr
statement
    : importStatement        // #IMPORT [DAY,1,模型名] AS 别名
    | variableDeclaration    // VARIABLE: 变量名 := 初值;
    | variableAssignment     // 变量名: 表达式, 格式选项;
    | tradingInstruction     // 条件, BP/SP/BK/SK;
    | tCommandStatement      // T_COMMAND(1);
    | ifThenBlock            // IF 条件 THEN BEGIN ... END
    | drawStatement          // DRAWTEXT(...), 格式选项;
    | formatOnlyStatement    // 变量名, 格式选项;
    | emptyStatement         // ;
    ;
```

### 4.2 IF-THEN 块（支持嵌套）

```antlr
ifThenBlock: IF expression THEN BEGIN blockStatement* END;

blockStatement
    : ifThenBlock            // 嵌套 IF-THEN
    | identifier (COLON | ASSIGN) expression (COMMA formatOption)* SEMICOLON?
    | formatOnlyStatement
    | emptyStatement
    ;
```

### 4.3 绘图语句

```antlr
drawStatement: drawFunction LPAREN drawArg (COMMA drawArg)* RPAREN (COMMA formatOption)* SEMICOLON?;

drawArg: expression | formatOption;

drawFunction
    : DRAWLINE3 | DRAWTEXT | DRAWTEXT_REL
    | DRAWCOLORKLINE | DRAWCOLOR | DRAWTITLE | DRAWHLINE
    ;
```

## 5. 调试技巧

### 5.1 查看详细错误

```python
parser = MFLangParserWrapper()
try:
    ast = parser.parse_file(path)
except Exception as e:
    print(f"错误: {e}")
    if parser._last_parser_errors:
        for line, col, msg in parser._last_parser_errors[:10]:
            print(f"  line {line}:{col} {msg}")
```

### 5.2 单独解析模型文件

```powershell
python scripts/parse_model.py mflang/mmodels/RICE1_DAY
```

### 5.3 错误数量变化追踪

| 修改 | 错误数 |
|------|--------|
| 初始状态 | 79 |
| 添加嵌套 IF-THEN 支持 | 184 (临时增加) |
| 修复 blockStatement | 58 |
| 添加 drawArg 规则 | 0 ✓ |

## 6. 注意事项

1. **手动修改解析器**: 由于 ANTLR 生成的代码使用状态机，某些修改需要手动编辑 `MFLangParser.py`
2. **保持同步**: 修改 `.g4` 文件后，必须重新生成并可能需要手动合并修改
3. **文件编码**: 确保所有文件使用 UTF-8 编码
4. **测试覆盖**: 修改语法后，应测试所有相关的模型文件

