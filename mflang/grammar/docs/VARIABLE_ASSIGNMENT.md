# 变量赋值语法说明

## 问题

如何在g4文件中定义变量赋值，例如：
```mflang
MAINTREND1M:EMA(EMA(CLOSE,3),3), PRECIS3;
```

## 答案

### 在MFLang.g4中的定义

**第177行**定义了变量赋值规则：

```antlr
// 变量赋值
// 示例: NUMOFDAY: BARPOS, NODRAW;
// 示例: ISUPTREND := MAINTREND1M >= REF(MAINTREND1M,5), PRECIS0, NODRAW;
// 注意：分号是可选的（在IF-THEN块中可能没有分号）
variableAssignment: identifier (COLON | ASSIGN) expression (COMMA formatOption)* SEMICOLON?;
```

### 语法分解

对于 `MAINTREND1M:EMA(EMA(CLOSE,3),3), PRECIS3;`：

```
MAINTREND1M:EMA(EMA(CLOSE,3),3), PRECIS3;
│           │                    │        │
│           │                    │        └─ SEMICOLON? (可选分号)
│           │                    └─────────── formatOption (PRECIS3)
│           │                    └─────────── COMMA (逗号)
│           └──────────────────────────────── expression
│           └──────────────────────────────── COLON (冒号)
└──────────────────────────────────────────── identifier (变量名)
```

### 各部分匹配

1. **identifier** → `MAINTREND1M`
   - 变量名，支持中文、英文、数字、下划线

2. **COLON** → `:`
   - 冒号，也可以使用 `:=` (ASSIGN)

3. **expression** → `EMA(EMA(CLOSE,3),3)`
   - 表达式，支持嵌套函数调用
   - 这里是一个EMA函数，第一个参数是另一个EMA函数调用

4. **COMMA formatOption** → `, PRECIS3`
   - 格式化选项，可以有多个，用逗号分隔

5. **SEMICOLON?** → `;`
   - 可选的分号

## 嵌套函数调用支持

### EMA函数定义（第316行）

```antlr
// EMA(X, N) - 指数移动平均
emaFunction: EMA LPAREN expression COMMA expression RPAREN;
```

注意：参数是 `expression`，这意味着：
- 第一个参数可以是另一个函数调用：`EMA(CLOSE,3)`
- 第二个参数可以是数字：`3`
- 支持任意深度的嵌套

### 嵌套解析过程

`EMA(EMA(CLOSE,3),3)` 的解析：

```
外层EMA函数
├─ 参数1: EMA(CLOSE,3)  ← 内层EMA函数（也是expression）
│  ├─ 参数1: CLOSE      ← K线数据标识符
│  └─ 参数2: 3          ← 整数
└─ 参数2: 3             ← 整数
```

## 表达式规则（第218-230行）

表达式支持运算符优先级和嵌套：

```antlr
expression
    : expression OR_OP expression          # OrExpression
    | expression AND_OP expression         # AndExpression
    | expression (GT | LT | GE | LE | EQ | NE) expression  # ComparisonExpression
    | expression (PLUS | MINUS) expression                # AdditiveExpression
    | expression (MULT | DIV) expression                   # MultiplicativeExpression
    | primaryExpression                                    # PrimaryExpr
    ;

primaryExpression
    : literal                             # LiteralExpr
    | identifier                         # IdentifierExpr
    | klineData                          # KlineDataExpr
    | functionCall                       # FunctionCallExpr  ← 函数调用
    | crossPeriodRef                     # CrossPeriodRefExpr
    | LPAREN expression RPAREN           # ParenExpr
    ;
```

因为 `functionCall` 是 `primaryExpression` 的一部分，而 `primaryExpression` 是 `expression` 的一部分，所以函数调用可以作为表达式的参数，支持嵌套。

## 验证

已测试，可以正确解析：

```python
from mflang.grammar import parse_mflang_string
from mflang.grammar.ast_visitor import NodeType

code = "MAINTREND1M:EMA(EMA(CLOSE,3),3), PRECIS3;"
ast = parse_mflang_string(code)

var_assign = ast.children[0]
# 变量名: MAINTREND1M
# 表达式类型: NodeType.FUNCTION_CALL
# 函数名: EMA
# 参数数量: 2
# 第一个参数: 也是FunctionCallNode (嵌套的EMA)
```

## 相关语法规则位置

- **变量赋值**: 第177行
- **表达式**: 第218-230行
- **函数调用**: 第251-271行
- **EMA函数**: 第316行
- **格式化选项**: 第340-349行

## 总结

`MAINTREND1M:EMA(EMA(CLOSE,3),3), PRECIS3;` 这个语句在g4文件中的定义是：

```antlr
variableAssignment: identifier (COLON | ASSIGN) expression (COMMA formatOption)* SEMICOLON?;
```

**关键点**：
1. ✅ 支持嵌套函数调用（因为函数参数是 `expression`）
2. ✅ 支持格式化选项（可以有多个）
3. ✅ 分号是可选的
4. ✅ 支持两种赋值方式：`:` 和 `:=`

语法定义已经完整支持这种格式！

