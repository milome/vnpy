"""
MHI CTA回测系统
基于VNPy框架的小恒指期货策略回测系统

主要功能:
- 数据获取和管理
- 策略回测和优化
- 性能分析和报告生成
- 测试驱动开发支持
"""

__version__ = "1.0.0"
__author__ = "Claude Code"
__description__ = "MHI期货策略CTA回测系统"

from .main import MHIBacktestSystem
from .config import Config

__all__ = [
    "MHIBacktestSystem",
    "Config",
    "__version__"
]
