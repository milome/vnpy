# 麦语言 ANTLR 语法文件使用指南

## 文件位置

- **语法文件**: `mflang/grammar/MFLang.g4`
- **说明文档**: `mflang/grammar/README.md`

## 语法文件特性

### ✅ 已支持的语法特性

1. **#IMPORT 语句**
   ```mflang
   #IMPORT [DAY,1, 米仓I号日内趋势] AS DAYTREND
   ```

2. **VARIABLE 声明**
   ```mflang
   VARIABLE: NUMOFDAY := 0;
   ```

3. **变量赋值（两种格式）**
   ```mflang
   NUMOFDAY: BARPOS, NODRAW;
   ISUPTREND := MAINTREND1M >= REF(MAINTREND1M,5), PRECIS0, NODRAW;
   ```

4. **交易指令**
   ```mflang
   BP;
   CONDITION,BP;
   CONDITION,BPK('A');
   ```

5. **T_COMMAND 语句**
   ```mflang
   T_COMMAND(1);
   ```

6. **IF-THEN-BEGIN-END 语句块**
   ```mflang
   IF ISDOWNTREND = 1
   THEN
   BEGIN
       CURRENTTREND := -4;
   END
   ```

7. **复杂嵌套表达式**
   - 支持16层嵌套IF函数
   - 支持运算符优先级
   - 支持括号表达式

8. **函数调用**
   - `REF(X, N)`, `BARSLAST(COND)`, `SUMBARS(X, A)`
   - `HHV(X, N)`, `LLV(X, N)`, `COUNT(COND, N)`
   - `MAX(...)`, `MIN(...)`, `IF(COND, TRUE, FALSE)`
   - `EMA(X, N)`, `MA(X, N)`, `MOD(X, Y)`
   - 等等...

9. **跨周期引用**
   ```mflang
   HOURTREND.VARNAME
   DAYTREND.SCALEBUYVOL
   ```

10. **中文支持**
    - 支持中文变量名
    - 支持中文注释

11. **格式化选项**
    ```mflang
    VARNAME: expression, PRECIS0, NODRAW, COLORWHITE;
    ```

## 运算符优先级

从低到高（符合数学和逻辑运算规则）：

1. `OR`, `||` (最低优先级)
2. `AND`, `&&`
3. `NOT`, `!`
4. 比较运算符: `>`, `<`, `=`, `<>`, `>=`, `<=`
5. 加减: `+`, `-`
6. 乘除: `*`, `/`
7. 一元运算符: `+`, `-` (最高优先级)

## 下一步工作

### 1. 生成解析器代码

```bash
# 安装 ANTLR (需要 Java)
# 下载: https://www.antlr.org/download.html

# 生成 Python 解析器
antlr4 -Dlanguage=Python3 -visitor MFLang.g4

# 这会生成:
# - MFLangLexer.py
# - MFLangParser.py  
# - MFLangListener.py
# - MFLangVisitor.py
```

### 2. 实现 AST 访问者

需要实现 `MFLangVisitor` 来：
- 遍历解析树
- 构建 AST（抽象语法树）
- 进行语义分析
- 生成 Python 代码

### 3. 代码生成

将 AST 转换为 Python 代码，包括：
- 变量定义
- 函数调用转换
- 跨周期引用处理
- 交易指令生成

### 4. 测试

使用 `RICE1.txt` 进行完整测试：
- 语法解析测试
- AST 构建测试
- 代码生成测试
- 功能验证测试

## 语法文件结构

```
MFLang.g4
├── 词法规则 (Lexer Rules)
│   ├── 关键字 (VARIABLE, IF, THEN, BEGIN, END, ...)
│   ├── 运算符 (+, -, *, /, >, <, =, ...)
│   ├── 标识符 (支持中文)
│   ├── 数字 (整数、浮点数)
│   └── 注释 (// 和 /* */)
│
└── 语法规则 (Parser Rules)
    ├── program (程序入口)
    ├── statement (语句)
    ├── expression (表达式，支持优先级)
    ├── functionCall (函数调用)
    └── ...
```

## 注意事项

1. **大小写**: 关键字不区分大小写（通过词法规则处理）
2. **空白字符**: 自动忽略空格、制表符、换行符
3. **注释**: 单行和多行注释都会被忽略
4. **分号**: 变量赋值的分号是可选的（在IF-THEN块中）
5. **中文**: 完全支持中文变量名和注释

## 已知限制

1. **函数参数数量**: MAX1/MIN1 理论上支持最多16个参数，但语法文件不限制参数数量（由运行时检查）
2. **格式化选项**: 支持常见的格式化选项，但可能不包含所有选项
3. **特殊函数**: 某些特殊函数可能需要扩展语法文件

## 扩展建议

如果需要添加新的语法特性：

1. **添加新函数**: 在 `functionCall` 规则中添加新的函数规则
2. **添加新关键字**: 在词法规则中添加新的关键字
3. **添加新运算符**: 在词法规则中添加运算符，在表达式规则中处理优先级

## 参考资源

- [ANTLR 官方文档](https://github.com/antlr/antlr4)
- [ANTLR Python 目标](https://github.com/antlr/antlr4/blob/master/doc/python-target.md)
- [ANTLR 语法规则指南](https://github.com/antlr/antlr4/blob/master/doc/grammars.md)

