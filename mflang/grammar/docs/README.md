# 麦语言 ANTLR 语法文件说明

## 文件结构

- `MFLang.g4`: 麦语言语法定义文件（ANTLR 4格式）

## 使用方法

### 1. 安装 ANTLR

```bash
# 安装 Java (ANTLR需要)
# 下载 ANTLR: https://www.antlr.org/download.html
# 或使用包管理器安装

# 安装 Python 运行时
pip install antlr4-python3-runtime
```

### 2. 生成解析器

```bash
# 生成 Python 解析器
antlr4 -Dlanguage=Python3 MFLang.g4

# 这会生成以下文件：
# - MFLangLexer.py (词法分析器)
# - MFLangParser.py (语法分析器)
# - MFLangListener.py (监听器接口)
# - MFLangVisitor.py (访问者接口)
```

### 3. 使用解析器

```python
from antlr4 import *
from MFLangLexer import MFLangLexer
from MFLangParser import MFLangParser

# 读取麦语言文件
input_stream = FileStream("mflang/mmodels/RICE1.txt")
lexer = MFLangLexer(input_stream)
stream = CommonTokenStream(lexer)
parser = MFLangParser(stream)

# 解析
tree = parser.program()

# 使用访问者模式遍历AST
class MyVisitor(MFLangVisitor):
    def visitVariableAssignment(self, ctx):
        var_name = ctx.identifier().getText()
        expr = ctx.expression()
        # 处理变量赋值
        return self.visitChildren(ctx)

visitor = MyVisitor()
visitor.visit(tree)
```

## 语法特性

### 1. 支持的语句类型

- **#IMPORT语句**: `#IMPORT [PERIOD,N,FORMULA] AS VAR`
- **VARIABLE声明**: `VARIABLE: VARNAME := value;`
- **变量赋值**: `VARNAME: expression;` 或 `VARNAME := expression;`
- **交易指令**: `CONDITION,BP;` 或 `BP;`
- **T_COMMAND**: `T_COMMAND(N);`
- **IF-THEN-BEGIN-END块**: 条件语句块

### 2. 支持的函数

- `REF(X, N)` - 引用N个周期前的值
- `BARSLAST(COND)` - 上一次条件成立到当前的周期数
- `SUMBARS(X, A)` - 求累加到指定值的周期数
- `HHV(X, N)` - 求X在N个周期内的最高值
- `LLV(X, N)` - 求X在N个周期内的最低值
- `COUNT(COND, N)` - 统计N个周期内条件成立的次数
- `MAX(X1, X2, ...)` - 求最大值
- `MIN(X1, X2, ...)` - 求最小值
- `IF(COND, TRUE_VAL, FALSE_VAL)` - 条件表达式
- `EMA(X, N)` - 指数移动平均
- `MA(X, N)` - 移动平均
- `MOD(X, Y)` - 取模
- 等等...

### 3. 支持的运算符

- **算术**: `+`, `-`, `*`, `/`
- **比较**: `>`, `<`, `=`, `<>`, `>=`, `<=`
- **逻辑**: `&&`, `||`, `!` 或 `AND`, `OR`, `NOT`

### 4. 跨周期引用

支持 `VAR.VARNAME` 格式的跨周期引用，例如：
- `HOURTREND.VARNAME`
- `DAYTREND.SCALEBUYVOL`

### 5. 中文支持

支持中文变量名和注释，例如：
- `米仓I号日内趋势`
- `// 这是注释`

## 运算符优先级

从低到高：
1. `OR`, `||`
2. `AND`, `&&`
3. `NOT`, `!`
4. 比较运算符 (`>`, `<`, `=`, `<>`, `>=`, `<=`)
5. 加减 (`+`, `-`)
6. 乘除 (`*`, `/`)
7. 一元运算符 (`+`, `-`)

## 注意事项

1. **注释处理**: 单行注释 `//` 和多行注释 `/* */` 会被自动忽略
2. **空白字符**: 空格、制表符、换行符会被自动忽略
3. **大小写**: 关键字不区分大小写（通过词法规则处理）
4. **标识符**: 支持中文、英文、数字、下划线，但不能以数字开头
5. **格式化选项**: 变量赋值后可以跟多个格式化选项（用逗号分隔）

## 示例

### 示例1: 变量赋值
```mflang
NUMOFDAY: BARPOS, NODRAW;
```

### 示例2: 复杂表达式
```mflang
ISUPTREND := MAINTREND1M >= REF(MAINTREND1M,5) && MAINTREND1M > REF(MAINTREND1M,1), PRECIS0, NODRAW;
```

### 示例3: IF函数
```mflang
MACD3MIX:= 2 * (DIFF3-DEA3) * IF(((DIFF3-DEA3) > 0 && (DIFF5-DEA5) > 0) || ((DIFF3-DEA3) < 0 && (DIFF5-DEA5) < 0), 1, -1), NODRAW;
```

### 示例4: IF-THEN-BEGIN-END块
```mflang
IF ISDOWNTREND = 1
THEN
BEGIN
    CURRENTTREND := -4;
END
```

### 示例5: 跨周期引用
```mflang
BUYVOL:= DAYTREND.SCALEBUYVOL, PRECIS0, NODRAW;
```

## 下一步

1. **生成解析器**: 使用ANTLR生成Python解析器
2. **实现AST访问者**: 实现访问者模式遍历AST
3. **代码生成**: 将AST转换为Python代码
4. **测试**: 使用RICE1.txt进行完整测试

## 参考

- [ANTLR官方文档](https://github.com/antlr/antlr4/blob/master/doc/index.md)
- [ANTLR Python运行时](https://github.com/antlr/antlr4/blob/master/doc/python-target.md)

