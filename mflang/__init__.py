#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
麦语言函数模块
实现文华财经麦语言的各种函数，用于策略开发

主要函数：
- REF: 引用N个周期前的值
- BARSLAST: 上一次条件成立到当前的周期数
- SUMBARS: 求累加到指定值的周期数

跨周期引用：
- #IMPORT: 跨周期引用函数（通过 import_parser 模块使用）
"""

from .functions import REF, BARSLAST, SUMBARS
from .import_parser import ImportParser, ImportStatement, PeriodType, parse_import
from .cross_period import CrossPeriodDataManager, ImportResolver

__all__ = [
    "REF",
    "BARSLAST",
    "SUMBARS",
    "ImportParser",
    "ImportStatement",
    "PeriodType",
    "parse_import",
    "CrossPeriodDataManager",
    "ImportResolver",
]

