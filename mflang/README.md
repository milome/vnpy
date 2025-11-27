# MFLang - 麦语言函数库

麦语言函数库和策略生成器，用于将文华财经麦语言模型转换为Python策略。

## 安装

在项目根目录下执行：

```bash
pip install -e .
```

## 使用

```python
from mflang import REF, BARSLAST, load_model
from mflang.strategy_generator import generate_strategy_from_model
```
