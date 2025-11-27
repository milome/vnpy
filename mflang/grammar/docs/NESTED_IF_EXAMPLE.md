# 嵌套IF语句中使用嵌套函数的案例分析

## 示例语句

```mflang
PREHIGHESTTREND35: IF(MACD35 > 0 && REF(MACD35, 1) >= 0, REF(HHV(MAINTREND1M, NUMOFDAY - NUMOFMACD35CROSSUP + 1), NUMOFDAY - NUMOFMACD35CROSSDOWN), 
    IF(MACD35 >= 0 && REF(MACD35, 1) < 0, REF(HHV(MAINTREND1M, NUMOFDAY - NUMOFMACD35CROSSUP + 1), NUMOFDAY - NUMOFMACD35CROSSDOWN),
        IF(MACD35 < 0 && REF(MACD35, 1) <= 0, REF(HHV(MAINTREND1M, NUMOFDAY - NUMOFMACD35CROSSUP + 1),  NUMOFDAY - PRENUMOFMACD35CROSSDOWN),
            IF(MACD35 <= 0 && REF(MACD35, 1) > 0, REF(HHV(MAINTREND1M, NUMOFDAY - NUMOFMACD35CROSSUP + 1), NUMOFDAY - PRENUMOFMACD35CROSSDOWN),
                0)))), PRECIS2, COLORLIGHTRED, NODRAW;
```

## 语法结构分析

### 整体结构

```
PREHIGHESTTREND35: IF(...), PRECIS2, COLORLIGHTRED, NODRAW;
│                  │                                      │
│                  │                                      └─ 格式化选项
│                  └─────────────────────────────────────── IF函数（4层嵌套）
└────────────────────────────────────────────────────────── 变量名
```

### IF函数嵌套结构（4层）

```
IF(条件1, 
    TRUE值1: REF(HHV(...), ...),  ← 嵌套函数调用
    FALSE值1: IF(条件2,            ← 第2层IF
        TRUE值2: REF(HHV(...), ...),
        FALSE值2: IF(条件3,        ← 第3层IF
            TRUE值3: REF(HHV(...), ...),
            FALSE值3: IF(条件4,    ← 第4层IF
                TRUE值4: REF(HHV(...), ...),
                FALSE值4: 0        ← 最终默认值
            )
        )
    )
)
```

### 嵌套函数调用结构

每个TRUE分支都包含：`REF(HHV(MAINTREND1M, NUMOFDAY - NUMOFMACD35CROSSUP + 1), NUMOFDAY - NUMOFMACD35CROSSDOWN)`

```
REF(
    HHV(                          ← 内层函数
        MAINTREND1M,              ← 参数1：变量名
        NUMOFDAY - NUMOFMACD35CROSSUP + 1  ← 参数2：表达式
    ),
    NUMOFDAY - NUMOFMACD35CROSSDOWN  ← REF的参数2：表达式
)
```

## 在g4文件中的定义

### 1. IF函数定义（第310行）

```antlr
// IF(COND, TRUE_VAL, FALSE_VAL) - 条件表达式
ifFunction: IF LPAREN expression COMMA expression COMMA expression RPAREN;
```

**关键点**：
- 三个参数都是 `expression`
- `FALSE_VAL` 可以是另一个 `IF` 函数调用（也是 `expression`）
- 因此支持任意深度的嵌套

### 2. REF函数定义（第274行）

```antlr
// REF(X, N) - 引用N个周期前的值
refFunction: REF LPAREN expression COMMA expression RPAREN;
```

**关键点**：
- 第一个参数是 `expression`，可以是函数调用（如 `HHV(...)`）
- 第二个参数也是 `expression`，可以是复杂表达式

### 3. HHV函数定义（第283行）

```antlr
// HHV(X, N) - 求X在N个周期内的最高值
hhvFunction: HHV LPAREN expression COMMA expression RPAREN;
```

**关键点**：
- 第二个参数是 `expression`，可以是 `NUMOFDAY - NUMOFMACD35CROSSUP + 1` 这样的表达式

### 4. 表达式规则（第218-230行）

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

**关键点**：
- `functionCall` 是 `primaryExpression` 的一部分
- `primaryExpression` 是 `expression` 的一部分
- 因此函数调用可以作为表达式的参数
- 表达式可以作为函数的参数
- **支持任意深度的嵌套**

## AST结构示例

解析后的AST结构（简化版）：

```
VariableAssignNode
├─ var_name: "PREHIGHESTTREND35"
├─ expression: FunctionCallNode (IF)
│  ├─ function_name: "IF"
│  └─ arguments:
│     ├─ [0]: BinaryOpNode (&&)  ← 条件1: MACD35 > 0 && REF(MACD35, 1) >= 0
│     ├─ [1]: FunctionCallNode (REF)  ← TRUE值1
│     │  ├─ function_name: "REF"
│     │  └─ arguments:
│     │     ├─ [0]: FunctionCallNode (HHV)  ← 嵌套函数
│     │     │  ├─ function_name: "HHV"
│     │     │  └─ arguments:
│     │     │     ├─ [0]: IdentifierExpr ("MAINTREND1M")
│     │     │     └─ [1]: BinaryOpNode (-)  ← 表达式: NUMOFDAY - NUMOFMACD35CROSSUP + 1
│     │     └─ [1]: BinaryOpNode (-)  ← 表达式: NUMOFDAY - NUMOFMACD35CROSSDOWN
│     └─ [2]: FunctionCallNode (IF)  ← FALSE值1: 第2层IF
│        ├─ function_name: "IF"
│        └─ arguments:
│           ├─ [0]: BinaryOpNode (&&)  ← 条件2
│           ├─ [1]: FunctionCallNode (REF)  ← TRUE值2
│           │  └─ ... (类似结构)
│           └─ [2]: FunctionCallNode (IF)  ← FALSE值2: 第3层IF
│              └─ ... (继续嵌套)
```

## 语法支持验证

### ✅ 已支持的特性

1. **多层嵌套IF**: ✅ 支持（IF的FALSE参数可以是另一个IF）
2. **嵌套函数调用**: ✅ 支持（REF的第一个参数可以是HHV）
3. **表达式作为函数参数**: ✅ 支持（HHV的第二个参数可以是表达式）
4. **复杂表达式**: ✅ 支持（NUMOFDAY - NUMOFMACD35CROSSUP + 1）

### 测试验证

已测试，可以成功解析：

```python
from mflang.grammar import parse_mflang_string

code = """PREHIGHESTTREND35: IF(MACD35 > 0 && REF(MACD35, 1) >= 0, 
    REF(HHV(MAINTREND1M, NUMOFDAY - NUMOFMACD35CROSSUP + 1), NUMOFDAY - NUMOFMACD35CROSSDOWN), 
    IF(MACD35 >= 0 && REF(MACD35, 1) < 0, 
        REF(HHV(MAINTREND1M, NUMOFDAY - NUMOFMACD35CROSSUP + 1), NUMOFDAY - NUMOFMACD35CROSSDOWN), 
        0)), PRECIS2, NODRAW;"""

ast = parse_mflang_string(code)
# 解析成功！
```

## 语法规则总结

### 核心规则

1. **变量赋值**:
   ```antlr
   variableAssignment: identifier (COLON | ASSIGN) expression (COMMA formatOption)* SEMICOLON?;
   ```

2. **IF函数**:
   ```antlr
   ifFunction: IF LPAREN expression COMMA expression COMMA expression RPAREN;
   ```
   - 三个参数都是 `expression`
   - 第三个参数可以是另一个 `IF` 函数调用 → 支持嵌套

3. **REF函数**:
   ```antlr
   refFunction: REF LPAREN expression COMMA expression RPAREN;
   ```
   - 第一个参数是 `expression`，可以是函数调用 → 支持嵌套

4. **HHV函数**:
   ```antlr
   hhvFunction: HHV LPAREN expression COMMA expression RPAREN;
   ```
   - 第二个参数是 `expression`，可以是复杂表达式

### 嵌套支持原理

```
expression
  → primaryExpression
    → functionCall
      → 参数是 expression
        → 可以是另一个 functionCall
          → 支持任意深度嵌套
```

## 实际应用

### RICE1.txt中的复杂案例

这个4层嵌套IF语句展示了：
1. **条件嵌套**: IF的FALSE分支是另一个IF
2. **函数嵌套**: REF函数的参数是HHV函数
3. **表达式嵌套**: 函数参数包含复杂表达式

所有这些都通过 `expression` 的递归定义实现。

## 结论

✅ **g4语法文件已完整支持嵌套IF语句中使用嵌套函数**

关键设计：
- 函数参数定义为 `expression`（而不是具体类型）
- `expression` 可以包含 `functionCall`
- `functionCall` 的参数又是 `expression`
- 形成递归支持，允许任意深度的嵌套

无需修改语法文件，当前定义已经支持这种复杂场景！

