#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证变量映射器"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from mflang.grammar.code_generator import VariableMapper

# 测试1: K线数据映射
print("Test 1: K线数据映射")
mapper = VariableMapper()
tests = [
    ('C', 'self.am.close'),
    ('CLOSE', 'self.am.close'),
    ('H', 'self.am.high'),
    ('HIGH', 'self.am.high'),
    ('L', 'self.am.low'),
    ('LOW', 'self.am.low'),
]

all_ok = True
for ident, expected in tests:
    result = mapper.map_identifier(ident)
    ok = result == expected
    all_ok = all_ok and ok
    status = "OK" if ok else "FAIL"
    print(f"  {status}: {ident} -> {result}")

# 测试2: 已定义变量映射
print("\nTest 2: 已定义变量映射")
mapper2 = VariableMapper(defined_variables={'MAINTREND1M', 'NUMOFDAY'})
tests2 = [
    ('MAINTREND1M', 'self.MAINTREND1M'),
    ('NUMOFDAY', 'self.NUMOFDAY'),
    ('UNKNOWN', 'UNKNOWN'),
]

for ident, expected in tests2:
    result = mapper2.map_identifier(ident)
    ok = result == expected
    all_ok = all_ok and ok
    status = "OK" if ok else "FAIL"
    print(f"  {status}: {ident} -> {result}")

print(f"\nOverall: {'PASS' if all_ok else 'FAIL'}")

