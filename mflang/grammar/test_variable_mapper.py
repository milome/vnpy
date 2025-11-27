#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试变量映射器
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from mflang.grammar import parse_mflang_string
from mflang.grammar.code_generator import StrategyCodeGenerator, VariableMapper


def test_variable_mapper():
    """测试变量映射器"""
    print("=" * 60)
    print("测试变量映射器")
    print("=" * 60)
    
    # 测试K线数据映射
    mapper = VariableMapper()
    
    test_cases = [
        ('C', 'self.am.close'),
        ('CLOSE', 'self.am.close'),
        ('H', 'self.am.high'),
        ('HIGH', 'self.am.high'),
        ('L', 'self.am.low'),
        ('LOW', 'self.am.low'),
        ('O', 'self.am.open'),
        ('OPEN', 'self.am.open'),
        ('V', 'self.am.volume'),
        ('VOLUME', 'self.am.volume'),
    ]
    
    print("\n1. 测试K线数据映射:")
    for identifier, expected in test_cases:
        result = mapper.map_identifier(identifier)
        status = "[OK]" if result == expected else "[X]"
        print(f"  {status} {identifier} -> {result} (期望: {expected})")
    
    # 测试已定义变量映射
    mapper_with_vars = VariableMapper(defined_variables={'MAINTREND1M', 'NUMOFDAY', 'ISUPTREND'})
    
    print("\n2. 测试已定义变量映射:")
    test_vars = [
        ('MAINTREND1M', 'self.MAINTREND1M'),
        ('NUMOFDAY', 'self.NUMOFDAY'),
        ('ISUPTREND', 'self.ISUPTREND'),
        ('UNKNOWN_VAR', 'UNKNOWN_VAR'),  # 未定义的变量保持原样
    ]
    
    for identifier, expected in test_vars:
        result = mapper_with_vars.map_identifier(identifier)
        status = "[OK]" if result == expected else "[X]"
        print(f"  {status} {identifier} -> {result} (期望: {expected})")
    
    print("\n" + "=" * 60)


def test_code_generation_with_mapper():
    """测试代码生成中使用变量映射器"""
    print("\n" + "=" * 60)
    print("测试代码生成中的变量映射")
    print("=" * 60)
    
    # 测试代码1: 简单的K线数据使用
    code1 = """
    NUMOFDAY: BARPOS, NODRAW;
    ISUPTREND := MAINTREND1M >= REF(MAINTREND1M, 5), PRECIS0, NODRAW;
    """
    
    print("\n测试代码1: 使用K线数据和变量")
    print("输入代码:")
    print(code1)
    
    try:
        ast = parse_mflang_string(code1)
        generator = StrategyCodeGenerator("TestStrategy1")
        python_code = generator.generate(ast)
        
        print("\n生成的Python代码:")
        print("-" * 60)
        print(python_code)
        print("-" * 60)
        
        # 检查关键映射
        checks = [
            ('self.am.close', 'CLOSE映射'),
            ('self.MAINTREND1M', '变量映射'),
            ('self.NUMOFDAY', '变量映射'),
        ]
        
        print("\n映射检查:")
        for check_str, desc in checks:
            if check_str in python_code:
                print(f"  [OK] {desc}: 找到 {check_str}")
            else:
                print(f"  [X] {desc}: 未找到 {check_str}")
        
    except Exception as e:
        print(f"[X] 生成失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试代码2: 复杂表达式
    code2 = """
    MAINTREND1M: EMA(EMA(CLOSE, 3), 3), PRECIS3;
    TR := MAX(MAX((HIGH - LOW), ABS(REF(CLOSE, 1) - HIGH)), ABS(REF(CLOSE, 1) - LOW));
    """
    
    print("\n" + "=" * 60)
    print("测试代码2: 复杂表达式和嵌套函数")
    print("输入代码:")
    print(code2)
    
    try:
        ast = parse_mflang_string(code2)
        generator = StrategyCodeGenerator("TestStrategy2")
        python_code = generator.generate(ast)
        
        print("\n生成的Python代码:")
        print("-" * 60)
        print(python_code)
        print("-" * 60)
        
        # 检查关键映射
        checks = [
            ('self.am.close', 'CLOSE映射'),
            ('self.am.high', 'HIGH映射'),
            ('self.am.low', 'LOW映射'),
            ('self.MAINTREND1M', '变量映射'),
            ('self.TR', '变量映射'),
        ]
        
        print("\n映射检查:")
        for check_str, desc in checks:
            if check_str in python_code:
                print(f"  [OK] {desc}: 找到 {check_str}")
            else:
                print(f"  [X] {desc}: 未找到 {check_str}")
        
    except Exception as e:
        print(f"[X] 生成失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    test_variable_mapper()
    test_code_generation_with_mapper()

