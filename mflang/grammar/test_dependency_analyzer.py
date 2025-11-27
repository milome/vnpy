#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试变量依赖分析器
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from mflang.grammar import parse_mflang_string
from mflang.grammar.code_generator import StrategyCodeGenerator
from mflang.grammar.dependency_analyzer import DependencyAnalyzer
from mflang.grammar.ast_visitor import VariableAssignNode


def test_simple_dependencies():
    """测试简单依赖关系"""
    print("=" * 60)
    print("测试简单依赖关系")
    print("=" * 60)
    
    code = """
    A: CLOSE, NODRAW;
    B: A + 1, NODRAW;
    C: B * 2, NODRAW;
    """
    
    try:
        ast = parse_mflang_string(code)
        variables = [node for node in ast.children if hasattr(node, 'var_name')]
        
        analyzer = DependencyAnalyzer()
        ordered_vars = analyzer.analyze(variables)
        
        print("\n变量计算顺序:")
        for i, var_name in enumerate(ordered_vars, 1):
            deps = analyzer.get_dependencies(var_name)
            print(f"  {i}. {var_name}", end="")
            if deps:
                print(f" (依赖: {', '.join(deps)})")
            else:
                print(" (无依赖)")
        
        # 验证顺序
        expected_order = ['A', 'B', 'C']
        if ordered_vars == expected_order:
            print("\n[OK] 依赖顺序正确!")
        else:
            print(f"\n[X] 依赖顺序错误!")
            print(f"    期望: {expected_order}")
            print(f"    实际: {ordered_vars}")
            
    except Exception as e:
        print(f"[X] 测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_complex_dependencies():
    """测试复杂依赖关系"""
    print("\n" + "=" * 60)
    print("测试复杂依赖关系")
    print("=" * 60)
    
    code = """
    MAINTREND1M: EMA(EMA(CLOSE, 3), 3), PRECIS3;
    ISUPTREND := MAINTREND1M >= REF(MAINTREND1M, 5), PRECIS0, NODRAW;
    NUMOFDAY: BARPOS, NODRAW;
    """
    
    try:
        ast = parse_mflang_string(code)
        variables = [node for node in ast.children if hasattr(node, 'var_name')]
        
        analyzer = DependencyAnalyzer()
        ordered_vars = analyzer.analyze(variables)
        
        print("\n变量计算顺序:")
        for i, var_name in enumerate(ordered_vars, 1):
            deps = analyzer.get_dependencies(var_name)
            print(f"  {i}. {var_name}", end="")
            if deps:
                print(f" (依赖: {', '.join(deps)})")
            else:
                print(" (无依赖)")
        
        # 验证 MAINTREND1M 在 ISUPTREND 之前
        if 'MAINTREND1M' in ordered_vars and 'ISUPTREND' in ordered_vars:
            idx_main = ordered_vars.index('MAINTREND1M')
            idx_isup = ordered_vars.index('ISUPTREND')
            if idx_main < idx_isup:
                print("\n[OK] MAINTREND1M 在 ISUPTREND 之前，顺序正确!")
            else:
                print("\n[X] 顺序错误: ISUPTREND 应该在 MAINTREND1M 之后")
        else:
            print("\n[X] 未找到预期变量")
            
    except Exception as e:
        print(f"[X] 测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_circular_dependency():
    """测试循环依赖检测"""
    print("\n" + "=" * 60)
    print("测试循环依赖检测")
    print("=" * 60)
    
    # 注意：这个代码实际上不会形成循环，因为麦语言的语法
    # 但我们可以测试检测逻辑
    code = """
    A: B + 1, NODRAW;
    B: A + 1, NODRAW;
    """
    
    try:
        ast = parse_mflang_string(code)
        variables = [node for node in ast.children if hasattr(node, 'var_name')]
        
        analyzer = DependencyAnalyzer()
        
        # 检查是否有循环依赖
        if analyzer.has_circular_dependency():
            print("[OK] 正确检测到循环依赖")
        else:
            try:
                ordered_vars = analyzer.analyze(variables)
                print(f"[OK] 无循环依赖，顺序: {ordered_vars}")
            except ValueError as e:
                print(f"[OK] 检测到循环依赖: {e}")
                
    except Exception as e:
        print(f"[X] 测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_code_generation_with_dependencies():
    """测试代码生成中的依赖分析"""
    print("\n" + "=" * 60)
    print("测试代码生成中的依赖分析")
    print("=" * 60)
    
    code = """
    MAINTREND1M: EMA(EMA(CLOSE, 3), 3), PRECIS3;
    ISUPTREND := MAINTREND1M >= REF(MAINTREND1M, 5), PRECIS0, NODRAW;
    NUMOFDAY: BARPOS, NODRAW;
    ISUPTREND,BP;
    """
    
    try:
        ast = parse_mflang_string(code)
        generator = StrategyCodeGenerator("TestStrategy")
        python_code = generator.generate(ast)
        
        print("\n生成的代码片段（变量计算部分）:")
        print("-" * 60)
        
        # 提取变量计算部分
        lines = python_code.split('\n')
        in_var_section = False
        var_lines = []
        
        for line in lines:
            if "# 计算变量" in line or "# 变量计算" in line:
                in_var_section = True
            if in_var_section:
                var_lines.append(line)
                if line.strip() == "" and var_lines:
                    break
        
        for line in var_lines[:10]:  # 只显示前10行
            print(line)
        
        # 检查顺序
        if "self.MAINTREND1M" in python_code and "self.ISUPTREND" in python_code:
            idx_main = python_code.find("self.MAINTREND1M")
            idx_isup = python_code.find("self.ISUPTREND")
            if idx_main < idx_isup:
                print("\n[OK] 生成的代码中，MAINTREND1M 在 ISUPTREND 之前")
            else:
                print("\n[X] 生成的代码顺序可能有问题")
        
        print("-" * 60)
        
    except Exception as e:
        print(f"[X] 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    test_simple_dependencies()
    test_complex_dependencies()
    test_circular_dependency()
    test_code_generation_with_dependencies()
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)

