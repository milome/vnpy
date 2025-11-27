#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
麦语言函数模块
"""

# 直接导入 functions.py 模块中的函数
# 由于文件名和目录名相同，使用 importlib 来避免冲突
import importlib.util
from pathlib import Path

# 加载 functions.py 模块
_functions_path = Path(__file__).parent / "functions.py"
spec = importlib.util.spec_from_file_location("functions", _functions_path)
_functions_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_functions_module)

# 导出函数
REF = _functions_module.REF
BARSLAST = _functions_module.BARSLAST
SUMBARS = _functions_module.SUMBARS
BARPOS = _functions_module.BARPOS
HHV = _functions_module.HHV
BP = _functions_module.BP
BPK = _functions_module.BPK
SPK = _functions_module.SPK

__all__ = [
    "REF",
    "BARSLAST",
    "SUMBARS",
    "BARPOS",
    "HHV",
    "BP",
    "BPK",
    "SPK",
]
