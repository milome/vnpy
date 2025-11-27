# 表达式转换完善总结

## 实现完成

✅ **表达式转换（运算符转换）已完善**

## 实现内容

### 1. 二元运算符转换

**位置**: `code_generator.py` 的 `_generate_binary_op` 方法

**支持的运算符转换**:

| 麦语言运算符 | Python运算符 | 说明 |
|------------|------------|------|
| `=` | `==` | 等于 |
| `<>` | `!=` | 不等于 |
| `>` | `>` | 大于 |
| `<` | `<` | 小于 |
| `>=` | `>=` | 大于等于 |
| `<=` | `<=` | 小于等于 |
| `&&` | `and` | 逻辑与 |
| `\|\|` | `or` | 逻辑或 |
| `AND` | `and` | 逻辑与（关键字） |
| `OR` | `or` | 逻辑或（关键字） |
| `+` | `+` | 加法 |
| `-` | `-` | 减法 |
| `*` | `*` | 乘法 |
| `/` | `/` | 除法 |

### 2. 一元运算符转换

**位置**: `code_generator.py` 的 `_generate_unary_op` 方法

**支持的运算符转换**:

| 麦语言运算符 | Python运算符 | 说明 |
|------------|------------|------|
| `!` | `not` | 逻辑非 |
| `NOT` | `not` | 逻辑非（关键字） |
| `+` | `+` | 正号 |
| `-` | `-` | 负号 |

**特殊处理**:
- 逻辑非：生成 `(not operand)` 格式
- 正负号：生成 `(+operand)` 或 `(-operand)` 格式（无空格）

### 3. 函数调用转换

**位置**: `code_generator.py` 的 `_generate_function_call` 方法

**特殊函数转换**:

| 麦语言函数 | Python代码 | 说明 |
|----------|-----------|------|
| `IF(COND, TRUE, FALSE)` | `(TRUE if COND else FALSE)` | 三元运算符 |
| `MAX(X1, X2, ...)` | `max(X1, X2, ...)` | Python内置函数 |
| `MIN(X1, X2, ...)` | `min(X1, X2, ...)` | Python内置函数 |
| `MOD(X, Y)` | `(X % Y)` | 取模运算符 |
| `ABS(X)` | `abs(X)` | Python内置函数 |

**保持原样的函数**（需要从mflang导入）:
- `REF`, `BARSLAST`, `SUMBARS`, `BARPOS`
- `HHV`, `LLV`, `HHVBARS`, `LLVBARS`
- `COUNT`, `EMA`, `MA`, `HV`, `LV`

### 4. 表达式处理增强

**位置**: `code_generator.py` 的 `_generate_expression` 方法

**新增功能**:
- 处理 `NodeType.EXPRESSION` 类型的节点（括号表达式等）
- 递归处理表达式子节点

## 使用示例

### 示例1: 比较运算符

**输入**:
```mflang
ISUPTREND := MAINTREND1M >= REF(MAINTREND1M, 5), NODRAW;
```

**生成的Python代码**:
```python
self.ISUPTREND = (self.MAINTREND1M >= REF(self.MAINTREND1M, 5))
```

### 示例2: 逻辑运算符

**输入**:
```mflang
COND := A > 0 && B < 10, NODRAW;
```

**生成的Python代码**:
```python
self.COND = ((A > 0) and (B < 10))
```

### 示例3: 复杂表达式

**输入**:
```mflang
TR := MAX(MAX((HIGH - LOW), ABS(REF(CLOSE, 1) - HIGH)), ABS(REF(CLOSE, 1) - LOW));
```

**生成的Python代码**:
```python
self.TR = max(max((self.am.high - self.am.low), abs(REF(self.am.close, 1) - self.am.high)), abs(REF(self.am.close, 1) - self.am.low))
```

### 示例4: 一元运算符

**输入**:
```mflang
NEG := -MAINTREND1M, NODRAW;
NOT_COND := !ISUPTREND, NODRAW;
```

**生成的Python代码**:
```python
self.NEG = (-self.MAINTREND1M)
self.NOT_COND = (not self.ISUPTREND)
```

### 示例5: IF函数

**输入**:
```mflang
RESULT := IF(A > 0 && B < 10, A + B, A - B), NODRAW;
```

**生成的Python代码**:
```python
self.RESULT = ((A + B) if ((A > 0) and (B < 10)) else (A - B))
```

## 运算符优先级

运算符优先级通过语法文件的规则顺序和括号来保证：

1. **最低优先级**: `||`, `OR` (逻辑或)
2. **次低优先级**: `&&`, `AND` (逻辑与)
3. **比较运算符**: `>`, `<`, `>=`, `<=`, `=`, `<>`
4. **加减运算符**: `+`, `-`
5. **乘除运算符**: `*`, `/`
6. **一元运算符**: `!`, `NOT`, `+`, `-` (最高优先级)

括号表达式会自动保持优先级。

## 测试

### 测试文件

- `test_expression_conversion.py` - 完整的表达式转换测试

### 测试覆盖

✅ 所有二元运算符转换
✅ 所有一元运算符转换
✅ 复杂表达式转换
✅ 嵌套表达式转换
✅ 函数调用转换

## 代码结构

### 运算符映射表

```python
# 二元运算符映射
op_map = {
    '=': '==',      # 等于
    '<>': '!=',     # 不等于
    '&&': 'and',    # 逻辑与
    '||': 'or',     # 逻辑或
    # ... 其他运算符
}

# 一元运算符映射
op_map = {
    '!': 'not',     # 逻辑非
    'NOT': 'not',   # 逻辑非（关键字）
    '+': '+',       # 正号
    '-': '-',       # 负号
}
```

### 函数转换逻辑

```python
if func_name == 'IF':
    return f"({args[1]} if {args[0]} else {args[2]})"
elif func_name in ['MAX', 'MAX1']:
    return f"max({args_str})"
elif func_name in ['MIN', 'MIN1']:
    return f"min({args_str})"
# ... 其他函数
```

## 下一步

表达式转换已完善，接下来可以：

1. **实现变量依赖分析** - 确定变量计算顺序
2. **完善跨周期引用** - 处理 `HOURTREND.VARNAME` 格式
3. **测试完整场景** - 使用RICE1.txt进行完整测试

## 相关文件

- `mflang/grammar/code_generator.py` - 实现文件
- `mflang/grammar/test_expression_conversion.py` - 测试脚本

