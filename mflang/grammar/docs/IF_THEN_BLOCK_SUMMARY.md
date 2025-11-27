# IF-THEN-BEGIN-END块处理实现总结

## 实现完成

✅ **IF-THEN-BEGIN-END块处理已成功实现并集成到代码生成器中**

## 实现内容

### 1. AST节点收集

**位置**: `code_generator.py` 的 `_collect_info` 方法

**功能**:
- 收集所有 `IF_THEN_BLOCK` 类型的AST节点
- 存储在 `self.if_then_blocks` 列表中

### 2. IF-THEN块代码生成

**位置**: `code_generator.py` 的 `_generate_if_then_blocks` 和 `_generate_if_then_block` 方法

**功能**:
- 将IF-THEN-BEGIN-END块转换为Python if语句
- 处理块内的变量赋值
- 支持嵌套的IF-THEN块

### 3. 策略类中的IF-THEN块生成

**位置**: `code_generator.py` 的 `_generate_if_then_block_strategy` 方法

**功能**:
- 在策略类的 `on_bar` 方法中生成IF-THEN块
- 正确处理变量赋值（使用 `self.` 前缀）

## 语法结构

### 麦语言语法

```mflang
IF expression
THEN
BEGIN
    statement1;
    statement2;
END
```

### AST结构

```
IF_THEN_BLOCK
├─ children[0]: condition (expression)
├─ children[1]: statement1
├─ children[2]: statement2
└─ ...
```

### 生成的Python代码

```python
if condition:
    statement1
    statement2
```

## 使用示例

### 示例1: 简单IF-THEN块

**输入**:
```mflang
IF ISDOWNTREND = 1
THEN
BEGIN
    CURRENTTREND := -4;
END
```

**生成的Python代码**:
```python
if (ISDOWNTREND == 1):
    self.CURRENTTREND = (-4)
```

### 示例2: 嵌套IF-THEN块

**输入**:
```mflang
IF A > 0
THEN
BEGIN
    B := 1;
    IF C > 0
    THEN
    BEGIN
        D := 2;
    END
END
```

**生成的Python代码**:
```python
if (A > 0):
    self.B = 1
    if (C > 0):
        self.D = 2
```

### 示例3: IF-THEN块中的变量赋值

**输入**:
```mflang
MAINTREND1M: EMA(CLOSE, 3), PRECIS3;
IF MAINTREND1M > 0
THEN
BEGIN
    ISUPTREND := 1;
    CURRENTTREND := 4;
END
```

**生成的Python代码**:
```python
# 计算变量（按依赖顺序）
self.MAINTREND1M = EMA(self.am.close, 3)

# IF-THEN-BEGIN-END块
if (self.MAINTREND1M > 0):
    self.ISUPTREND = 1
    self.CURRENTTREND = 4
```

## 代码结构

### 代码生成器修改

```python
class CodeGenerator:
    def __init__(self):
        # ...
        self.if_then_blocks: List[ASTNode] = []
    
    def _collect_info(self, node: ASTNode):
        # ...
        elif node.node_type == NodeType.IF_THEN_BLOCK:
            self.if_then_blocks.append(node)
    
    def _generate_if_then_blocks(self):
        """生成IF-THEN-BEGIN-END块代码"""
        if not self.if_then_blocks:
            return
        
        self.lines.append("# IF-THEN-BEGIN-END块")
        for block in self.if_then_blocks:
            self._generate_if_then_block(block)
        self.lines.append("")
    
    def _generate_if_then_block(self, block: ASTNode):
        """生成单个IF-THEN-BEGIN-END块"""
        # 第一个子节点是条件
        condition = block.children[0]
        cond_code = self._generate_expression(condition)
        
        # 生成if语句
        self.lines.append(f"if {cond_code}:")
        self.indent_level += 1
        
        # 处理块内语句
        for stmt in block.children[1:]:
            if stmt.node_type == NodeType.VARIABLE_ASSIGN:
                # 变量赋值
                var_name = stmt.var_name
                expr_code = self._generate_expression(stmt.expression)
                self.lines.append(f"{self._indent()}{var_name} = {expr_code}")
            # ... 其他语句类型
        
        self.indent_level -= 1
```

## 支持的功能

✅ **基本IF-THEN块**: 支持简单的IF-THEN-BEGIN-END块
✅ **嵌套IF-THEN块**: 支持块内嵌套的IF-THEN块
✅ **变量赋值**: 支持块内的变量赋值语句
✅ **交易指令**: 支持块内的交易指令
✅ **表达式转换**: 条件表达式和赋值表达式都正确转换

## 处理流程

1. **AST收集**: 在 `_collect_info` 中收集所有IF_THEN_BLOCK节点
2. **代码生成**: 在 `_generate_if_then_blocks` 中生成所有IF-THEN块
3. **单个块处理**: 在 `_generate_if_then_block` 中处理单个块
   - 提取条件表达式
   - 生成if语句
   - 处理块内所有语句
   - 支持嵌套块

## 测试

### 测试文件

- `test_if_then_block.py` - 完整的IF-THEN块测试

### 测试覆盖

✅ 简单IF-THEN块测试
✅ 嵌套IF-THEN块测试
✅ IF-THEN块中的变量赋值测试
✅ 与变量计算的集成测试

## 下一步

IF-THEN-BEGIN-END块处理已实现，接下来可以：

1. **完善跨周期引用** - 处理 `HOURTREND.VARNAME` 格式
2. **测试完整场景** - 使用RICE1.txt进行完整测试
3. **集成现有系统** - 与strategy_generator.py集成

## 相关文件

- `mflang/grammar/code_generator.py` - 实现文件（已更新）
- `mflang/grammar/test_if_then_block.py` - 测试脚本
- `mflang/grammar/MFLang.g4` - 语法定义（第199行）

