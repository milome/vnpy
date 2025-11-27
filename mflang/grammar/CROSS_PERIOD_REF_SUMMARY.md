# 跨周期引用处理实现总结

## 实现完成

✅ **跨周期引用处理已成功实现并集成到代码生成器中**

## 实现内容

### 1. 跨周期引用收集

**位置**: `code_generator.py` 的 `_collect_cross_period_refs` 方法

**功能**:
- 遍历AST，收集所有跨周期引用节点
- 为每个跨周期引用生成唯一的Python变量名
- 存储在 `self.cross_period_refs` 字典中

### 2. 跨周期引用代码生成

**位置**: `code_generator.py` 的 `_generate_cross_period_ref` 方法

**功能**:
- 将跨周期引用节点转换为Python变量名
- 返回已获取的跨周期数据变量名

### 3. 跨周期引用获取代码生成

**位置**: `code_generator.py` 的 `_generate_cross_period_refs_code` 和 `_generate_cross_period_refs_code_strategy` 方法

**功能**:
- 为每个跨周期引用生成从IndicatorManager获取数据的代码
- 查找对应的#IMPORT语句
- 生成 `get_indicator_smart` 调用

### 4. 周期类型转换

**位置**: `code_generator.py` 的 `_get_interval_string` 方法

**功能**:
- 将周期类型（MIN, HOUR, DAY等）转换为interval字符串
- 支持所有周期类型

## 语法结构

### 麦语言语法

```mflang
#IMPORT [HOUR,1, 米仓I号日内趋势] AS HOURTREND;
ISSKIPDAY : HOURTREND.ISSKIPDAY, NODRAW;
```

### AST结构

```
IMPORT节点
├─ period_type: "HOUR"
├─ period_n: 1
├─ formula: "米仓I号日内趋势"
└─ var_name: "HOURTREND"

CROSS_PERIOD_REF节点
├─ var_name: "HOURTREND"
└─ field_name: "ISSKIPDAY"
```

### 生成的Python代码

```python
# 在__init__中
self.indicator_manager = IndicatorManager(
    vt_symbol=self.vt_symbol,
    storage_path=None,
    use_database=True
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

# 在表达式中使用
self.ISSKIPDAY = isskipday_value
```

## 使用示例

### 示例1: 简单跨周期引用

**输入**:
```mflang
#IMPORT [HOUR,1, 米仓I号日内趋势] AS HOURTREND;
ISSKIPDAY : HOURTREND.ISSKIPDAY, NODRAW;
```

**生成的Python代码**:
```python
# 在on_bar方法中
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

### 示例2: 表达式中的跨周期引用

**输入**:
```mflang
#IMPORT [HOUR,1, 米仓I号日内趋势] AS HOURTREND;
NUMOF4HSHIFT : IF(REF(HOURTREND.NUMOFNEWDAY, 1) < 7, 1, 0), NODRAW;
```

**生成的Python代码**:
```python
# 获取跨周期引用
numofnewday_value = self.indicator_manager.get_indicator_smart(
    "1h",
    "HOURTREND.NUMOFNEWDAY",
    ...
)

# 在表达式中使用
self.NUMOF4HSHIFT = (1 if (REF(numofnewday_value, 1) < 7) else 0)
```

### 示例3: 多个跨周期引用

**输入**:
```mflang
#IMPORT [HOUR,1, 米仓I号日内趋势] AS HOURTREND;
ISSKIPDAY : HOURTREND.ISSKIPDAY, NODRAW;
小时周期: HOURTREND.NUMOFNEWDAY, NODRAW;
```

**生成的Python代码**:
```python
# 获取跨周期引用 HOURTREND.ISSKIPDAY
isskipday_value = self.indicator_manager.get_indicator_smart(...)
# 获取跨周期引用 HOURTREND.NUMOFNEWDAY
numofnewday_value = self.indicator_manager.get_indicator_smart(...)

self.ISSKIPDAY = isskipday_value
self.小时周期 = numofnewday_value
```

## 周期类型转换

### 支持的周期类型

| 周期类型 | interval字符串 | 示例 |
|---------|---------------|------|
| MIN | `"{n}m"` | `"5m"` |
| HOUR | `"{n}h"` | `"1h"` |
| CUSHOUR | `"{n}h"` | `"2h"` |
| DAY | `"{n}d"` | `"1d"` |
| WEEK | `"{n}w"` | `"1w"` |
| MONTH | `"{n}M"` | `"1M"` |
| QUARTER | `"{n}Q"` | `"1Q"` |
| YEAR | `"{n}Y"` | `"1Y"` |

## 代码结构

### 跨周期引用处理流程

1. **收集阶段**: `_collect_cross_period_refs` 遍历AST收集所有跨周期引用
2. **代码生成阶段**: 
   - `_generate_cross_period_refs_code_strategy` 生成获取代码
   - `_generate_cross_period_ref` 在表达式中使用变量名
3. **初始化阶段**: 在 `__init__` 中创建 `IndicatorManager` 实例

### 关键方法

```python
def _collect_cross_period_refs(self, node: ASTNode):
    """收集所有跨周期引用"""
    # 递归遍历AST，收集CROSS_PERIOD_REF节点

def _generate_cross_period_ref(self, node: CrossPeriodRefNode) -> str:
    """生成跨周期引用代码"""
    # 返回Python变量名（如 isskipday_value）

def _generate_cross_period_refs_code_strategy(self):
    """生成策略类中的跨周期引用获取代码"""
    # 为每个跨周期引用生成get_indicator_smart调用

def _get_interval_string(self, period_type: str, period_n: int) -> str:
    """将周期类型转换为interval字符串"""
    # MIN -> "5m", HOUR -> "1h" 等
```

## 集成点

### 1. 导入语句

如果有跨周期引用，自动添加：
```python
from indicators import IndicatorManager
```

### 2. __init__方法

如果有跨周期引用，自动创建IndicatorManager：
```python
self.indicator_manager = IndicatorManager(
    vt_symbol=self.vt_symbol,
    storage_path=None,
    use_database=True
)
```

### 3. on_bar方法

在变量计算前，生成跨周期引用获取代码：
```python
# 获取跨周期引用数据
isskipday_value = self.indicator_manager.get_indicator_smart(...)
# 计算变量
self.ISSKIPDAY = isskipday_value
```

## 测试

### 测试文件

- `test_cross_period_ref.py` - 完整的跨周期引用测试

### 测试覆盖

✅ 简单跨周期引用测试
✅ 表达式中的跨周期引用测试
✅ 多个跨周期引用测试
✅ IndicatorManager初始化测试

## 下一步

跨周期引用处理已实现，接下来可以：

1. **测试完整场景** - 使用RICE1.txt进行完整测试
2. **集成现有系统** - 与strategy_generator.py集成
3. **性能优化** - 优化跨周期引用获取性能

## 相关文件

- `mflang/grammar/code_generator.py` - 实现文件（已更新）
- `mflang/grammar/test_cross_period_ref.py` - 测试脚本
- `mflang/grammar/ast_visitor.py` - AST访问者（已支持CROSS_PERIOD_REF）




