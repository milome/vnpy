# mflang 目录重组说明

## 目录结构变化

### 重组前
```
mflang/
├── __init__.py
├── functions.py          # 麦语言函数实现
├── test_*.py             # 测试文件（5个）
├── *.md                  # 文档文件（5个）
├── import_parser.py
├── cross_period.py
├── model_loader.py
├── strategy_generator.py
├── generate_strategy.py
├── example_*.py
└── mmodels/
```

### 重组后
```
mflang/
├── __init__.py
├── functions/             # 麦语言函数模块
│   ├── __init__.py
│   └── functions.py
├── tests/                # 测试文件和示例文件目录
│   ├── test_functions.py
│   ├── test_import.py
│   ├── test_model_loader.py
│   ├── test_parse_test_import.py
│   ├── test_strategy_generator.py
│   ├── example_parse_formula.py
│   └── example_trend_strategy.py
├── docs/                 # 文档目录
│   ├── README.md
│   ├── IMPORT_USAGE.md
│   ├── CROSS_PERIOD_DATA_EXPLANATION.md
│   ├── PERIOD_DETERMINATION.md
│   ├── STRATEGY_GENERATOR.md
│   └── REORGANIZATION.md
├── import_parser.py
├── cross_period.py
├── model_loader.py
├── strategy_generator.py
├── generate_strategy.py
├── example_*.py
└── mmodels/
```

## 主要变化

### 1. 测试文件和示例文件
- **移动位置**: 
  - 所有 `test_*.py` 文件移动到 `tests/` 目录
  - 所有 `example_*.py` 文件移动到 `tests/` 目录
- **导入路径**: 保持不变，仍然使用 `from mflang import ...` 或 `from mflang.xxx import ...`

### 2. 文档文件
- **移动位置**: 所有 `*.md` 文件移动到 `docs/` 目录
- **文档引用**: 如果代码中有文档路径引用，需要更新

### 3. 函数模块
- **移动位置**: `functions.py` 移动到 `functions/` 目录
- **导入路径**: 
  - 旧: `from mflang.functions import REF`
  - 新: `from mflang.functions import REF` (保持不变，通过 `functions/__init__.py` 导出)
- **内部导入**: `mflang/__init__.py` 使用 `from .functions import ...`

## 导入路径说明

### 用户代码中的导入（无需修改）

```python
# 这些导入路径保持不变
from mflang import REF, BARSLAST, SUMBARS, BARPOS, HHV
from mflang.import_parser import ImportParser
from mflang.model_loader import load_model
from mflang.cross_period import CrossPeriodDataManager
```

### 内部模块导入

```python
# mflang/__init__.py
from .functions import REF, BARSLAST, SUMBARS, BARPOS, HHV

# mflang/functions/__init__.py
# 使用 importlib 加载 functions.py 模块
```

## 运行测试

### 方式1: 直接运行测试文件
```bash
python mflang/tests/test_functions.py
python mflang/tests/test_import.py
python mflang/tests/test_strategy_generator.py
```

### 方式2: 使用 pytest
```bash
pytest mflang/tests/
```

### 方式3: 作为模块运行
```bash
python -m pytest mflang.tests
```

## 验证

运行以下命令验证重组后的代码是否正常工作：

```python
# 验证函数导入
from mflang import REF, BARSLAST, SUMBARS, BARPOS, HHV

# 验证其他模块导入
from mflang.import_parser import ImportParser
from mflang.model_loader import load_model

# 验证策略生成器
python -m mflang.generate_strategy TEST_IMPORT strategies/test.py TestStrategy
```

## 注意事项

1. **测试文件路径**: 测试文件中的相对路径引用可能需要调整
2. **文档路径**: 如果代码中有文档路径引用，需要更新为 `docs/` 目录
3. **导入兼容性**: 所有公共 API 的导入路径保持不变，确保向后兼容

## 文件清单

### 移动的测试文件和示例文件
- `test_functions.py` → `tests/test_functions.py`
- `test_import.py` → `tests/test_import.py`
- `test_model_loader.py` → `tests/test_model_loader.py`
- `test_parse_test_import.py` → `tests/test_parse_test_import.py`
- `test_strategy_generator.py` → `tests/test_strategy_generator.py`
- `example_parse_formula.py` → `tests/example_parse_formula.py`
- `example_trend_strategy.py` → `tests/example_trend_strategy.py`

### 移动的文档文件
- `README.md` → `docs/README.md`
- `IMPORT_USAGE.md` → `docs/IMPORT_USAGE.md`
- `CROSS_PERIOD_DATA_EXPLANATION.md` → `docs/CROSS_PERIOD_DATA_EXPLANATION.md`
- `PERIOD_DETERMINATION.md` → `docs/PERIOD_DETERMINATION.md`
- `STRATEGY_GENERATOR.md` → `docs/STRATEGY_GENERATOR.md`

### 移动的函数文件
- `functions.py` → `functions/functions.py`

## 更新日期

2025-11-23

