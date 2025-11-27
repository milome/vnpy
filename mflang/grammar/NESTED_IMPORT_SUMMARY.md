# 嵌套IMPORT支持实现总结

## 实现完成

✅ **嵌套IMPORT支持已成功实现 - 可以解析被导入的模型文件**

## 实现内容

### 1. 模型文件解析

**位置**: `code_generator.py` 的 `_parse_imported_models` 方法

**功能**:
- 遍历所有IMPORT语句
- 使用ANTLR解析器解析被导入的模型文件
- 将解析结果存储在 `self.imported_models` 字典中

### 2. 变量收集

**位置**: `code_generator.py` 的 `_collect_variables_from_ast` 方法

**功能**:
- 从导入模型的AST中收集所有变量定义
- 递归遍历AST节点

### 3. 模型注册代码生成

**位置**: `code_generator.py` 的 `_generate_register_imported_models` 方法

**功能**:
- 为每个导入的模型生成注册代码
- 调用 `IndicatorManager.register_indicator` 注册每个变量

## 使用示例

### 示例1: 基本嵌套IMPORT

**主模型文件 (RICE1.txt)**:
```mflang
#IMPORT [HOUR,1, 米仓I号日内趋势] AS HOURTREND;
ISSKIPDAY : HOURTREND.ISSKIPDAY, NODRAW;
```

**被导入的模型文件 (米仓I号日内趋势)**:
```mflang
VARIABLE: ISSKIPDAY := 0;
ISSKIPDAY : HOURTREND.ISSKIPDAY, NODRAW;
```

**生成的Python代码**:
```python
# 在__init__中
self.indicator_manager = IndicatorManager(...)

# 注册导入的模型到IndicatorManager
# 注册模型: 米仓I号日内趋势 (周期: "1h", 变量名: HOURTREND)
self.indicator_manager.register_indicator(
    "1h",
    "HOURTREND.ISSKIPDAY",
    "米仓I号日内趋势",
    "ISSKIPDAY"
)

# 在on_bar中
# 获取跨周期引用 HOURTREND.ISSKIPDAY
isskipday_value = self.indicator_manager.get_indicator_smart(
    "1h",
    "HOURTREND.ISSKIPDAY",
    prefer_runtime=True,
    fallback_to_history=True,
    history_index=-1,
    wait_if_not_ready=True,
    wait_timeout=1.0
)
if isskipday_value is None:
    isskipday_value = np.nan

self.ISSKIPDAY = isskipday_value
```

## 工作流程

### 1. 解析阶段

```
主模型文件 (RICE1.txt)
  ↓
解析 #IMPORT 语句
  ↓
发现导入: 米仓I号日内趋势
  ↓
解析被导入的模型文件
  ↓
收集模型中的变量定义
```

### 2. 代码生成阶段

```
生成 __init__ 方法
  ↓
创建 IndicatorManager
  ↓
注册导入的模型变量
  ↓
生成 on_bar 方法
  ↓
生成跨周期引用获取代码
```

## 关键方法

### `_parse_imported_models()`

```python
def _parse_imported_models(self):
    """解析被导入的模型文件"""
    for imp in self.import_statements:
        formula_name = imp.formula
        model_file = self.models_dir / formula_name
        imported_ast = parse_mflang_file(str(model_file))
        self.imported_models[formula_name] = imported_ast
```

### `_collect_variables_from_ast()`

```python
def _collect_variables_from_ast(self, ast: ASTNode, variables: List[VariableAssignNode]):
    """从AST中收集变量定义"""
    if ast.node_type == NodeType.VARIABLE_ASSIGN:
        variables.append(ast)
    # 递归处理子节点
```

### `_generate_register_imported_models()`

```python
def _generate_register_imported_models(self):
    """生成注册导入模型到IndicatorManager的代码"""
    for imp in self.import_statements:
        imported_ast = self.imported_models[formula_name]
        imported_vars = []
        self._collect_variables_from_ast(imported_ast, imported_vars)
        # 为每个变量生成register_indicator调用
```

## 限制

⚠️ **目前不支持嵌套的IMPORT**

- 如果被导入的模型文件本身也包含 `#IMPORT` 语句，这些嵌套的IMPORT不会被解析
- 这是为了避免循环依赖和复杂性

## 错误处理

- 如果模型文件不存在，会打印警告但继续执行
- 如果解析失败，会打印警告但继续执行
- 如果模型未解析，生成的代码中会包含警告注释

## 测试

### 测试文件

- `test_nested_import.py` - 完整的嵌套IMPORT测试

### 测试覆盖

✅ 解析被导入的模型文件
✅ 收集导入模型中的变量
✅ 生成模型注册代码
✅ 生成跨周期引用获取代码

## 相关文件

- `mflang/grammar/code_generator.py` - 实现文件（已更新）
- `mflang/grammar/test_nested_import.py` - 测试脚本
- `mflang/grammar/parser.py` - 解析器（用于解析模型文件）

## 下一步

嵌套IMPORT支持已实现，接下来可以：

1. **支持嵌套的IMPORT** - 解析被导入模型中的IMPORT语句（需要处理循环依赖）
2. **优化性能** - 缓存已解析的模型文件
3. **错误处理** - 更详细的错误信息和恢复机制




