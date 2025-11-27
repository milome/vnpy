# 变量依赖分析器实现总结

## 实现完成

✅ **变量依赖分析器已成功实现并集成到代码生成器中**

## 实现内容

### 1. DependencyAnalyzer 类

**位置**: `mflang/grammar/dependency_analyzer.py`

**功能**:
- 从AST表达式中提取变量依赖关系
- 构建依赖图
- 使用拓扑排序确定计算顺序
- 检测循环依赖

### 2. 依赖提取

**方法**: `_extract_dependencies(node: ASTNode) -> Set[str]`

**支持的节点类型**:
- `IDENTIFIER` - 标识符（变量名）
- `BINARY_OP` - 二元运算符（递归处理左右操作数）
- `UNARY_OP` - 一元运算符（递归处理操作数）
- `FUNCTION_CALL` - 函数调用（递归处理所有参数）
- `CROSS_PERIOD_REF` - 跨周期引用
- `EXPRESSION` - 表达式节点（递归处理子节点）

**过滤规则**:
- 跳过K线数据标识符（C, CLOSE, H, HIGH等）
- 跳过特殊函数（BARPOS等）
- 只提取已定义的变量

### 3. 拓扑排序

**方法**: `_topological_sort() -> List[str]`

**算法**: Kahn算法（拓扑排序）

**步骤**:
1. 计算每个变量的入度（依赖数量）
2. 找到所有入度为0的节点（没有依赖的变量）
3. 处理队列，更新依赖关系
4. 检测循环依赖

### 4. 集成到代码生成器

**修改点**:
1. 在 `CodeGenerator._generate_variable_assignments()` 中使用依赖分析
2. 在 `StrategyCodeGenerator._generate_on_bar_method()` 中使用依赖分析
3. 按依赖顺序生成变量赋值代码

## 使用示例

### 示例1: 简单依赖链

**输入**:
```mflang
A: CLOSE, NODRAW;
B: A + 1, NODRAW;
C: B * 2, NODRAW;
```

**依赖关系**:
- A: 无依赖
- B: 依赖 A
- C: 依赖 B

**计算顺序**: `['A', 'B', 'C']`

**生成的Python代码**:
```python
self.A = self.am.close
self.B = (self.A + 1)
self.C = (self.B * 2)
```

### 示例2: 复杂依赖

**输入**:
```mflang
MAINTREND1M: EMA(EMA(CLOSE, 3), 3), PRECIS3;
ISUPTREND := MAINTREND1M >= REF(MAINTREND1M, 5), PRECIS0, NODRAW;
NUMOFDAY: BARPOS, NODRAW;
```

**依赖关系**:
- MAINTREND1M: 无依赖（只依赖CLOSE，这是K线数据）
- ISUPTREND: 依赖 MAINTREND1M
- NUMOFDAY: 无依赖

**计算顺序**: `['MAINTREND1M', 'NUMOFDAY', 'ISUPTREND']` 或 `['NUMOFDAY', 'MAINTREND1M', 'ISUPTREND']`

**生成的Python代码**:
```python
self.MAINTREND1M = EMA(EMA(self.am.close, 3), 3)
self.NUMOFDAY = BARPOS(self.am.close)
self.ISUPTREND = ((self.MAINTREND1M >= REF(self.MAINTREND1M, 5)))
```

### 示例3: 循环依赖检测

**输入**:
```mflang
A: B + 1, NODRAW;
B: A + 1, NODRAW;
```

**结果**: 抛出 `ValueError`，提示检测到循环依赖

## API 说明

### DependencyAnalyzer 类

```python
class DependencyAnalyzer:
    def analyze(self, variables: List[VariableAssignNode]) -> List[str]:
        """分析变量依赖并返回计算顺序"""
        
    def get_dependencies(self, var_name: str) -> Set[str]:
        """获取指定变量的依赖集合"""
        
    def get_dependents(self, var_name: str) -> Set[str]:
        """获取依赖指定变量的所有变量"""
        
    def has_circular_dependency(self) -> bool:
        """检查是否存在循环依赖"""
        
    def get_dependency_graph(self) -> Dict[str, Set[str]]:
        """获取完整的依赖图"""
```

## 算法说明

### 拓扑排序（Kahn算法）

1. **初始化**:
   - 计算每个变量的入度（依赖数量）
   - 创建队列，包含所有入度为0的节点

2. **处理队列**:
   - 从队列中取出节点，加入结果列表
   - 更新依赖此节点的所有节点的入度
   - 如果某个节点的入度变为0，加入队列

3. **检测循环**:
   - 如果结果列表的长度不等于变量总数，说明存在循环依赖

### 时间复杂度

- **依赖提取**: O(n * m)，其中n是变量数，m是平均表达式复杂度
- **拓扑排序**: O(n + e)，其中n是变量数，e是依赖边数
- **总体**: O(n * m + n + e)

## 测试

### 测试文件

- `test_dependency_analyzer.py` - 完整的依赖分析测试

### 测试覆盖

✅ 简单依赖链测试
✅ 复杂依赖关系测试
✅ 循环依赖检测测试
✅ 代码生成集成测试

## 代码结构

### 依赖分析器

```python
class DependencyAnalyzer:
    KLINE_DATA_IDENTIFIERS = {'C', 'CLOSE', 'H', ...}
    SPECIAL_FUNCTIONS = {'BARPOS'}
    
    def __init__(self):
        self.variables: Dict[str, VariableAssignNode] = {}
        self.dependencies: Dict[str, Set[str]] = {}
        self.reverse_dependencies: Dict[str, Set[str]] = {}
```

### 集成到代码生成器

```python
# 在 _generate_variable_assignments 中
analyzer = DependencyAnalyzer()
ordered_vars = analyzer.analyze(self.variables)

for var_name in ordered_vars:
    var = var_map[var_name]
    expr_code = self._generate_expression(var.expression)
    self.lines.append(f"{var_name} = {expr_code}")
```

## 下一步

变量依赖分析器已实现，接下来可以：

1. **完善跨周期引用** - 处理 `HOURTREND.VARNAME` 格式
2. **测试完整场景** - 使用RICE1.txt进行完整测试
3. **性能优化** - 优化大型模型的依赖分析性能

## 相关文件

- `mflang/grammar/dependency_analyzer.py` - 依赖分析器实现
- `mflang/grammar/code_generator.py` - 代码生成器（已集成）
- `mflang/grammar/test_dependency_analyzer.py` - 测试脚本

