# Indicators - 多周期指标管理器

多周期自定义指标管理器，支持长期历史数据存储和实时增量更新。

## 安装

在项目根目录下执行：

```bash
pip install -e .
```

如果需要使用Parquet格式存储（推荐）：

```bash
pip install -e ".[parquet]"
```

## 使用

```python
from indicators import IndicatorManager
from vnpy.trader.constant import Interval

manager = IndicatorManager(
    vt_symbol="MHImain.HKFE",
    use_database=True
)
```

