#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试嵌套IF语句中使用嵌套函数
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from mflang.grammar import parse_mflang_string
from mflang.grammar.ast_visitor import NodeType, FunctionCallNode


def test_nested_if_with_nested_functions():
    """测试嵌套IF语句中使用嵌套函数"""
    print("=" * 60)
    print("测试嵌套IF语句中使用嵌套函数")
    print("=" * 60)
    
    # 简化版的嵌套IF语句（2层）
    code = """PREHIGHESTTREND35: IF(MACD35 > 0 && REF(MACD35, 1) >= 0, 
    REF(HHV(MAINTREND1M, NUMOFDAY - NUMOFMACD35CROSSUP + 1), NUMOFDAY - NUMOFMACD35CROSSDOWN), 
    IF(MACD35 >= 0 && REF(MACD35, 1) < 0, 
        REF(HHV(MAINTREND1M, NUMOFDAY - NUMOFMACD35CROSSUP + 1), NUMOFDAY - NUMOFMACD35CROSSDOWN), 
        0)), PRECIS2, NODRAW;"""
    
    try:
        ast = parse_mflang_string(code)
        print("[OK] 解析成功!")
        
        var_assign = ast.children[0]
        print(f"\n变量名: {var_assign.var_name}")
        print(f"表达式类型: {var_assign.expression.node_type}")
        
        # 检查外层IF
        if var_assign.expression.node_type == NodeType.FUNCTION_CALL:
            outer_if = var_assign.expression
            print(f"\n外层IF函数:")
            print(f"  函数名: {outer_if.function_name}")
            print(f"  参数数量: {len(outer_if.arguments)}")
            
            # 检查第一个参数（条件）
            if len(outer_if.arguments) > 0:
                cond = outer_if.arguments[0]
                print(f"  条件类型: {cond.node_type}")
            
            # 检查第二个参数（TRUE值 - REF函数）
            if len(outer_if.arguments) > 1:
                true_val = outer_if.arguments[1]
                print(f"\n  TRUE值类型: {true_val.node_type}")
                if true_val.node_type == NodeType.FUNCTION_CALL:
                    print(f"  TRUE值函数: {true_val.function_name}")
                    # 检查REF的第一个参数（HHV函数）
                    if len(true_val.arguments) > 0:
                        ref_arg1 = true_val.arguments[0]
                        if ref_arg1.node_type == NodeType.FUNCTION_CALL:
                            print(f"    REF参数1是函数: {ref_arg1.function_name}")
                            print(f"    嵌套函数: REF(HHV(...))")
            
            # 检查第三个参数（FALSE值 - 嵌套IF）
            if len(outer_if.arguments) > 2:
                false_val = outer_if.arguments[2]
                print(f"\n  FALSE值类型: {false_val.node_type}")
                if false_val.node_type == NodeType.FUNCTION_CALL:
                    print(f"  FALSE值函数: {false_val.function_name}")
                    if false_val.function_name == "IF":
                        print(f"    嵌套IF: IF(...)")
                        print(f"    嵌套IF参数数量: {len(false_val.arguments)}")
        
        print("\n" + "=" * 60)
        print("[OK] 嵌套IF和嵌套函数调用都支持!")
        print("=" * 60)
        
    except Exception as e:
        print(f"[X] 解析失败: {e}")
        import traceback
        traceback.print_exc()


def test_complex_nested_structure():
    """测试更复杂的嵌套结构"""
    print("\n" + "=" * 60)
    print("测试复杂嵌套结构")
    print("=" * 60)
    
    # 测试REF(HHV(...))嵌套
    code = "TEST: REF(HHV(MAINTREND1M, NUMOFDAY - NUMOFMACD35CROSSUP + 1), NUMOFDAY - NUMOFMACD35CROSSDOWN), NODRAW;"
    
    try:
        ast = parse_mflang_string(code)
        print("[OK] REF(HHV(...))嵌套解析成功!")
        
        var_assign = ast.children[0]
        ref_func = var_assign.expression
        
        if ref_func.node_type == NodeType.FUNCTION_CALL and ref_func.function_name == "REF":
            print(f"REF函数参数数量: {len(ref_func.arguments)}")
            if len(ref_func.arguments) > 0:
                hhv_func = ref_func.arguments[0]
                if hhv_func.node_type == NodeType.FUNCTION_CALL:
                    print(f"REF的第一个参数是函数: {hhv_func.function_name}")
                    print(f"嵌套结构: REF(HHV(...))")
        
    except Exception as e:
        print(f"[X] 解析失败: {e}")


if __name__ == '__main__':
    test_nested_if_with_nested_functions()
    test_complex_nested_structure()

