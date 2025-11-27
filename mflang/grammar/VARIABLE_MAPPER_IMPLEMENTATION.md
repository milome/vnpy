# 变量映射器实现总结

## 实现完成

✅ **变量名映射器已成功实现并集成到代码生成器中**

## 实现内容

### 1. VariableMapper 类

**位置**: `mflang/grammar/code_generator.py`

**功能**:
- 将麦语言变量名映射到Python代码
- 支持K线数据映射
- 支持已定义变量映射
- 处理特殊函数

### 2. K线数据映射

支持以下K线数据标识符的映射：

| 麦语言标识符 | Python代码 |
|------------|-----------|
| `C`, `CLOSE` | `self.am.close` |
| `H`, `HIGH` | `self.am.high` |
| `L`, `LOW` | `self.am.low` |
| `O`, `OPEN` | `self.am.open` |
| `V`, `VOL`, `VOLUME` | `self.am.volume` |
| `TIME`, `KTIME` | `self.am.time` |

### 3. 已定义变量映射

- 自动识别AST中已定义的变量
- 将已定义变量映射为 `self.VARNAME` 格式
- 例如：`MAINTREND1M` → `self.MAINTREND1M`

### 4. 集成到代码生成器

**修改点**:
1. 在 `CodeGenerator.__init__` 中添加 `variable_mapper` 属性
2. 在 `generate` 方法中初始化变量映射器
3. 在 `_generate_expression` 方法中使用映射器转换标识符

## 使用示例

### 示例1: 简单变量赋值

**输入**:
```mflang
MAINTREND1M: EMA(CLOSE, 3), PRECIS3;
```

**生成的Python代码**:
```python
self.MAINTREND1M = EMA(self.am.close, 3)
```

### 示例2: 复杂表达式

**输入**:
```mflang
TR := MAX(MAX((HIGH - LOW), ABS(REF(CLOSE, 1) - HIGH)), ABS(REF(CLOSE, 1) - LOW));
```

**生成的Python代码**:
```python
self.TR = max(max((self.am.high - self.am.low), abs(REF(self.am.close, 1) - self.am.high)), abs(REF(self.am.close, 1) - self.am.low))
```

### 示例3: 变量引用

**输入**:
```mflang
ISUPTREND := MAINTREND1M >= REF(MAINTREND1M, 5), PRECIS0, NODRAW;
```

**生成的Python代码**:
```python
self.ISUPTREND = (self.MAINTREND1M >= REF(self.MAINTREND1M, 5))
```

## 代码结构

### VariableMapper 类

```python
class VariableMapper:
    """变量名映射器"""
    
    KLINE_DATA_MAP = {
        'C': 'self.am.close',
        'CLOSE': 'self.am.close',
        # ... 其他映射
    }
    
    def __init__(self, defined_variables: Optional[Set[str]] = None):
        self.defined_variables = defined_variables or set()
    
    def map_identifier(self, identifier: str) -> str:
        """映射标识符到Python代码"""
        # 1. 检查K线数据
        # 2. 检查已定义变量
        # 3. 检查特殊函数
        # 4. 其他情况保持原样
```

### 集成到 CodeGenerator

```python
class CodeGenerator:
    def generate(self, ast_root: ASTNode) -> str:
        # ...
        # 初始化变量映射器
        defined_vars = {var.var_name for var in self.variables}
        self.variable_mapper = VariableMapper(defined_variables=defined_vars)
        # ...
    
    def _generate_expression(self, node: ASTNode) -> str:
        # ...
        elif node.node_type == NodeType.IDENTIFIER:
            # 使用变量映射器转换标识符
            if self.variable_mapper:
                return self.variable_mapper.map_identifier(node.value)
            else:
                return node.value
```

## 测试

### 测试文件

- `test_variable_mapper.py` - 完整的变量映射器测试
- `verify_mapper.py` - 简单的验证脚本
- `test_parser.py` - 更新了代码生成测试，包含变量映射验证

### 测试覆盖

✅ K线数据映射测试
✅ 已定义变量映射测试
✅ 复杂表达式中的变量映射测试
✅ 嵌套函数调用中的变量映射测试

## 下一步

变量映射器已实现，接下来可以：

1. **完善表达式转换** - 确保所有运算符正确转换
2. **实现变量依赖分析** - 确定变量计算顺序
3. **完善跨周期引用** - 处理 `HOURTREND.VARNAME` 格式
4. **测试完整场景** - 使用RICE1.txt进行完整测试

## 相关文件

- `mflang/grammar/code_generator.py` - 变量映射器实现
- `mflang/grammar/test_variable_mapper.py` - 测试脚本
- `mflang/grammar/verify_mapper.py` - 验证脚本

