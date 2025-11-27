#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试IF-THEN-BEGIN-END块处理
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from mflang.grammar import parse_mflang_string
from mflang.grammar.code_generator import StrategyCodeGenerator


def test_simple_if_then_block():
    """测试简单的IF-THEN-BEGIN-END块"""
    print("=" * 60)
    print("测试简单的IF-THEN-BEGIN-END块")
    print("=" * 60)
    
    code = """
    IF ISDOWNTREND = 1
    THEN
    BEGIN
        CURRENTTREND := -4;
    END
    """
    
    try:
        ast = parse_mflang_string(code)
        generator = StrategyCodeGenerator("TestStrategy")
        python_code = generator.generate(ast)
        
        print("\n生成的Python代码:")
        print("-" * 60)
        print(python_code)
        print("-" * 60)
        
        # 检查关键元素
        checks = [
            ('if', 'if语句'),
            ('ISDOWNTREND', '条件变量'),
            ('CURRENTTREND', '块内变量'),
        ]
        
        print("\n代码检查:")
        for check_str, desc in checks:
            if check_str in python_code:
                print(f"  [OK] {desc}: 找到 {check_str}")
            else:
                print(f"  [X] {desc}: 未找到 {check_str}")
        
    except Exception as e:
        print(f"[X] 测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_nested_if_then_block():
    """测试嵌套的IF-THEN-BEGIN-END块"""
    print("\n" + "=" * 60)
    print("测试嵌套的IF-THEN-BEGIN-END块")
    print("=" * 60)
    
    code = """
    IF A > 0
    THEN
    BEGIN
        B := 1;
        IF C > 0
        THEN
        BEGIN
            D := 2;
        END
    END
    """
    
    try:
        ast = parse_mflang_string(code)
        generator = StrategyCodeGenerator("TestStrategy")
        python_code = generator.generate(ast)
        
        print("\n生成的Python代码:")
        print("-" * 60)
        # 只显示相关部分
        lines = python_code.split('\n')
        in_if_section = False
        for line in lines:
            if 'if' in line.lower() or 'self.' in line:
                in_if_section = True
            if in_if_section:
                print(line)
                if line.strip() == "" and 'if' not in lines[lines.index(line)+1:lines.index(line)+3] if lines.index(line)+1 < len(lines) else []:
                    break
        print("-" * 60)
        
    except Exception as e:
        print(f"[X] 测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_if_then_with_variables():
    """测试IF-THEN块中的变量赋值"""
    print("\n" + "=" * 60)
    print("测试IF-THEN块中的变量赋值")
    print("=" * 60)
    
    code = """
    MAINTREND1M: EMA(CLOSE, 3), PRECIS3;
    IF MAINTREND1M > 0
    THEN
    BEGIN
        ISUPTREND := 1;
        CURRENTTREND := 4;
    END
    """
    
    try:
        ast = parse_mflang_string(code)
        generator = StrategyCodeGenerator("TestStrategy")
        python_code = generator.generate(ast)
        
        print("\n生成的Python代码片段:")
        print("-" * 60)
        lines = python_code.split('\n')
        for i, line in enumerate(lines):
            if 'if' in line.lower() or 'self.MAINTREND1M' in line or 'self.ISUPTREND' in line or 'self.CURRENTTREND' in line:
                print(line)
                # 显示后续几行
                for j in range(1, 3):
                    if i + j < len(lines):
                        print(lines[i + j])
        print("-" * 60)
        
        # 检查顺序
        if 'self.MAINTREND1M' in python_code and 'if' in python_code:
            idx_main = python_code.find('self.MAINTREND1M')
            idx_if = python_code.find('if')
            if idx_main < idx_if:
                print("\n[OK] 变量计算在IF语句之前，顺序正确")
            else:
                print("\n[!] 注意：变量计算顺序可能需要调整")
        
    except Exception as e:
        print(f"[X] 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    test_simple_if_then_block()
    test_nested_if_then_block()
    test_if_then_with_variables()
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)

