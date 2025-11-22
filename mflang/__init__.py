#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
麦语言函数模块
实现文华财经麦语言的各种函数，用于策略开发

主要函数：
- REF: 引用N个周期前的值
- BARSLAST: 上一次条件成立到当前的周期数
"""

from .functions import REF, BARSLAST

__all__ = [
    "REF",
    "BARSLAST",
]

