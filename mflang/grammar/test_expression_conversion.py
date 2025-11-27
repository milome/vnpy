#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试表达式转换（运算符转换）
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from mflang.grammar import parse_mflang_string
from mflang.grammar.code_generator import StrategyCodeGenerator


def test_operator_conversion():
    """测试运算符转换"""
    print("=" * 60)
    print("测试运算符转换")
    print("=" * 60)
    
    test_cases = [
        # 比较运算符
        ("A = B", "=="),
        ("A <> B", "!="),
        ("A > B", ">"),
        ("A < B", "<"),
        ("A >= B", ">="),
        ("A <= B", "<="),
        # 逻辑运算符
        ("A && B", "and"),
        ("A || B", "or"),
        ("A AND B", "and"),
        ("A OR B", "or"),
        ("!A", "not"),
        ("NOT A", "not"),
        # 算术运算符
        ("A + B", "+"),
        ("A - B", "-"),
        ("A * B", "*"),
        ("A / B", "/"),
        # 一元运算符
        ("-A", "-"),
        ("+A", "+"),
    ]
    
    print("\n1. 测试基本运算符转换:")
    for code, expected_op in test_cases:
        try:
            full_code = f"TEST: {code}, NODRAW;"
            ast = parse_mflang_string(full_code)
            generator = StrategyCodeGenerator("TestStrategy")
            python_code = generator.generate(ast)
            
            # 检查运算符是否正确转换
            if expected_op in python_code:
                print(f"  [OK] {code} -> 包含 {expected_op}")
            else:
                print(f"  [X] {code} -> 未找到 {expected_op}")
                print(f"      生成的代码: {python_code[:100]}...")
        except Exception as e:
            print(f"  [X] {code} -> 错误: {e}")


def test_complex_expressions():
    """测试复杂表达式"""
    print("\n" + "=" * 60)
    print("测试复杂表达式")
    print("=" * 60)
    
    test_cases = [
        # 复杂比较
        ("ISUPTREND := MAINTREND1M >= REF(MAINTREND1M, 5), NODRAW;",
         ["self.MAINTREND1M", ">=", "REF"]),
        # 逻辑组合
        ("COND := A > 0 && B < 10, NODRAW;",
         ["and", ">", "<"]),
        # 算术表达式
        ("TR := MAX(MAX((HIGH - LOW), ABS(REF(CLOSE, 1) - HIGH)), ABS(REF(CLOSE, 1) - LOW));",
         ["self.am.high", "-", "self.am.low", "max", "abs"]),
        # 嵌套表达式
        ("RESULT := IF(A > 0 && B < 10, A + B, A - B), NODRAW;",
         ["if", "and", ">", "<", "+", "-"]),
    ]
    
    print("\n2. 测试复杂表达式:")
    for code, expected_ops in test_cases:
        try:
            ast = parse_mflang_string(code)
            generator = StrategyCodeGenerator("TestStrategy")
            python_code = generator.generate(ast)
            
            print(f"\n  输入: {code[:50]}...")
            found_ops = [op for op in expected_ops if op in python_code]
            missing_ops = [op for op in expected_ops if op not in python_code]
            
            if len(found_ops) == len(expected_ops):
                print(f"  [OK] 所有运算符都正确转换")
            else:
                print(f"  [X] 缺少运算符: {missing_ops}")
                print(f"      找到的运算符: {found_ops}")
            
            # 显示生成的代码片段
            if "self." in python_code:
                snippet = python_code[python_code.find("self."):python_code.find("self.")+100]
                print(f"      代码片段: {snippet}...")
                
        except Exception as e:
            print(f"  [X] 错误: {e}")
            import traceback
            traceback.print_exc()


def test_unary_operators():
    """测试一元运算符"""
    print("\n" + "=" * 60)
    print("测试一元运算符")
    print("=" * 60)
    
    test_cases = [
        ("NEG := -MAINTREND1M, NODRAW;", "-"),
        ("POS := +MAINTREND1M, NODRAW;", "+"),
        ("NOT_COND := !ISUPTREND, NODRAW;", "not"),
        ("NOT_COND2 := NOT ISUPTREND, NODRAW;", "not"),
    ]
    
    print("\n3. 测试一元运算符:")
    for code, expected_op in test_cases:
        try:
            ast = parse_mflang_string(code)
            generator = StrategyCodeGenerator("TestStrategy")
            python_code = generator.generate(ast)
            
            if expected_op in python_code:
                print(f"  [OK] {code[:30]}... -> 包含 {expected_op}")
            else:
                print(f"  [X] {code[:30]}... -> 未找到 {expected_op}")
                # 显示相关代码片段
                if "self." in python_code:
                    idx = python_code.find("self.")
                    snippet = python_code[max(0, idx-20):idx+80]
                    print(f"      代码片段: {snippet}...")
        except Exception as e:
            print(f"  [X] {code[:30]}... -> 错误: {e}")


if __name__ == '__main__':
    test_operator_conversion()
    test_complex_expressions()
    test_unary_operators()
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)

