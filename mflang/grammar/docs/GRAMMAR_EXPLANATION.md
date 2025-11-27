# 麦语言语法规则说明

## 变量赋值语法定义

### 语法规则

在 `MFLang.g4` 文件中，变量赋值定义如下：

```antlr
// 变量赋值
// 示例: NUMOFDAY: BARPOS, NODRAW;
// 示例: ISUPTREND := MAINTREND1M >= REF(MAINTREND1M,5), PRECIS0, NODRAW;
// 注意：分号是可选的（在IF-THEN块中可能没有分号）
variableAssignment: identifier (COLON | ASSIGN) expression (COMMA formatOption)* SEMICOLON?;
```

### 语法分解

对于语句 `MAINTREND1M:EMA(EMA(CLOSE,3),3), PRECIS3;`，语法匹配如下：

```
MAINTREND1M:EMA(EMA(CLOSE,3),3), PRECIS3;
│           │                    │        │
│           │                    │        └─ SEMICOLON (分号，可选)
│           │                    └─────────── formatOption (PRECIS3)
│           │                    └─────────── COMMA (逗号)
│           └──────────────────────────────── expression (EMA(EMA(CLOSE,3),3))
│           └──────────────────────────────── COLON (冒号)
└──────────────────────────────────────────── identifier (MAINTREND1M)
```

### 各部分说明

1. **identifier** - 变量名
   - `MAINTREND1M`
   - 支持中文、英文、数字、下划线
   - 不能以数字开头

2. **COLON** - 冒号 `:`
   - 或使用 `ASSIGN` (`:=`)
   - 两种赋值方式都支持

3. **expression** - 表达式
   - `EMA(EMA(CLOSE,3),3)` 
   - 支持嵌套函数调用
   - 支持复杂表达式

4. **formatOption** - 格式化选项（可选，可多个）
   - `PRECIS3`
   - 用逗号分隔
   - 可以有多个：`PRECIS3, NODRAW, COLORWHITE`

5. **SEMICOLON** - 分号（可选）
   - 在IF-THEN块中可能没有分号

## 嵌套函数调用

### EMA函数定义

```antlr
// EMA(X, N) - 指数移动平均
emaFunction: EMA LPAREN expression COMMA expression RPAREN;
```

### 嵌套调用解析

`EMA(EMA(CLOSE,3),3)` 的解析过程：

```
EMA(EMA(CLOSE,3),3)
│
├─ 外层EMA函数
│  ├─ 第一个参数: EMA(CLOSE,3)  ← 内层EMA函数调用
│  │  ├─ EMA函数
│  │  │  ├─ 第一个参数: CLOSE  ← K线数据
│  │  │  └─ 第二个参数: 3      ← 整数
│  └─ 第二个参数: 3            ← 整数
```

### AST结构

解析后的AST结构：

```
VariableAssignNode
├─ var_name: "MAINTREND1M"
├─ expression: FunctionCallNode
│  ├─ function_name: "EMA"
│  └─ arguments:
│     ├─ [0]: FunctionCallNode  ← 嵌套的EMA函数
│     │  ├─ function_name: "EMA"
│     │  └─ arguments:
│     │     ├─ [0]: IdentifierExpr("CLOSE")
│     │     └─ [1]: Literal(3)
│     └─ [1]: Literal(3)
└─ format_options: ["PRECIS3"]
```

## 表达式优先级

表达式按以下优先级解析（从低到高）：

1. **OR, ||** (最低)
2. **AND, &&**
3. **NOT, !**
4. **比较运算符**: `>`, `<`, `=`, `<>`, `>=`, `<=`
5. **加减**: `+`, `-`
6. **乘除**: `*`, `/`
7. **一元运算符**: `+`, `-` (最高)

## 支持的函数调用

### 单参数函数
- `BARSLAST(COND)`
- `ABS(X)`

### 双参数函数
- `REF(X, N)`
- `EMA(X, N)`
- `MA(X, N)`
- `HHV(X, N)`
- `LLV(X, N)`
- `COUNT(COND, N)`
- `MOD(X, Y)`

### 三参数函数
- `IF(COND, TRUE_VAL, FALSE_VAL)`

### 可变参数函数
- `MAX(X1, X2, ...)`
- `MIN(X1, X2, ...)`
- `MAX1(X1, X2, ..., X16)`
- `MIN1(X1, X2, ..., X16)`

### 嵌套调用

所有函数都支持嵌套调用，例如：

```mflang
// 单层嵌套
MAINTREND1M: EMA(CLOSE, 3), PRECIS3;

// 双层嵌套
MAINTREND1M: EMA(EMA(CLOSE,3),3), PRECIS3;

// 多层嵌套
COMPLEX: IF(EMA(EMA(CLOSE,3),3) > REF(EMA(CLOSE,5),1), 1, 0), NODRAW;

// 复杂嵌套
TR := MAX(MAX((HIGH-LOW),ABS(REF(CLOSE,1)-HIGH)),ABS(REF(CLOSE,1)-LOW));
```

## 完整示例

### 示例1: 简单变量赋值
```mflang
NUMOFDAY: BARPOS, NODRAW;
```

### 示例2: 带表达式的赋值
```mflang
MAINTREND1M: EMA(EMA(CLOSE,3),3), PRECIS3;
```

### 示例3: 复杂表达式
```mflang
ISUPTREND := MAINTREND1M >= REF(MAINTREND1M,5) && CLOSE > HHV(HIGH, 3), PRECIS0, NODRAW;
```

### 示例4: 嵌套IF函数
```mflang
MACD3MIX := 2 * (DIFF3-DEA3) * IF(((DIFF3-DEA3) > 0 && (DIFF5-DEA5) > 0) || ((DIFF3-DEA3) < 0 && (DIFF5-DEA5) < 0), 1, -1), NODRAW;
```

### 示例5: 跨周期引用
```mflang
BUYVOL := DAYTREND.SCALEBUYVOL, PRECIS0, NODRAW;
```

## 语法规则位置

在 `MFLang.g4` 文件中的相关规则：

- **变量赋值规则**: 第177行
- **表达式规则**: 第218-230行
- **函数调用规则**: 第251-271行
- **EMA函数规则**: 第320行

## 验证

可以使用以下代码验证解析：

```python
from mflang.grammar import parse_mflang_string

code = "MAINTREND1M:EMA(EMA(CLOSE,3),3), PRECIS3;"
ast = parse_mflang_string(code)

# 检查变量赋值节点
var_assign = ast.children[0]
print(f"变量名: {var_assign.var_name}")
print(f"表达式类型: {var_assign.expression.node_type}")

# 如果是函数调用
if var_assign.expression.node_type == NodeType.FUNCTION_CALL:
    func_node = var_assign.expression
    print(f"函数名: {func_node.function_name}")
    print(f"参数数量: {len(func_node.arguments)}")
    # 检查第一个参数（嵌套的EMA）
    if len(func_node.arguments) > 0:
        nested_func = func_node.arguments[0]
        if nested_func.node_type == NodeType.FUNCTION_CALL:
            print(f"嵌套函数: {nested_func.function_name}")
```

## 总结

`MAINTREND1M:EMA(EMA(CLOSE,3),3), PRECIS3;` 这个语句在g4文件中的定义是：

```antlr
variableAssignment: identifier (COLON | ASSIGN) expression (COMMA formatOption)* SEMICOLON?;
```

其中：
- `MAINTREND1M` 匹配 `identifier`
- `:` 匹配 `COLON`
- `EMA(EMA(CLOSE,3),3)` 匹配 `expression`（支持嵌套函数调用）
- `, PRECIS3` 匹配 `COMMA formatOption`
- `;` 匹配 `SEMICOLON`

语法定义已经完整支持这种格式，包括嵌套函数调用。

