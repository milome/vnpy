#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试跨周期引用处理
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from mflang.grammar import parse_mflang_string
from mflang.grammar.code_generator import StrategyCodeGenerator


def test_cross_period_ref():
    """测试跨周期引用"""
    print("=" * 60)
    print("测试跨周期引用处理")
    print("=" * 60)
    
    code = """
    #IMPORT [HOUR,1, 米仓I号日内趋势] AS HOURTREND;
    ISSKIPDAY : HOURTREND.ISSKIPDAY, NODRAW;
    小时周期: HOURTREND.NUMOFNEWDAY, NODRAW;
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
            ('IndicatorManager', 'IndicatorManager导入'),
            ('self.indicator_manager', 'IndicatorManager实例'),
            ('get_indicator_smart', '跨周期数据获取'),
            ('HOURTREND.ISSKIPDAY', '跨周期引用'),
            ('isskipday_value', '跨周期变量'),
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


def test_cross_period_ref_in_expression():
    """测试表达式中的跨周期引用"""
    print("\n" + "=" * 60)
    print("测试表达式中的跨周期引用")
    print("=" * 60)
    
    code = """
    #IMPORT [HOUR,1, 米仓I号日内趋势] AS HOURTREND;
    NUMOF4HSHIFT : IF(ISSKIPDAY = 1, IF(REF(HOURTREND.NUMOFNEWDAY, 1) < 7, REF(HOURTREND.KTIME, 1) = 1030 && HOURTREND.NUMOFNEWDAY <> REF(HOURTREND.NUMOFNEWDAY, 1), 0), 0), NODRAW;
    """
    
    try:
        ast = parse_mflang_string(code)
        generator = StrategyCodeGenerator("TestStrategy")
        python_code = generator.generate(ast)
        
        print("\n生成的Python代码片段（跨周期引用部分）:")
        print("-" * 60)
        lines = python_code.split('\n')
        in_cross_period_section = False
        for line in lines:
            if '跨周期引用' in line or 'get_indicator_smart' in line:
                in_cross_period_section = True
            if in_cross_period_section:
                print(line)
                if line.strip() == "" and '跨周期引用' not in lines[lines.index(line)+1:lines.index(line)+3] if lines.index(line)+1 < len(lines) else []:
                    break
        print("-" * 60)
        
        # 检查是否生成了所有需要的跨周期引用
        expected_refs = ['HOURTREND.NUMOFNEWDAY', 'HOURTREND.KTIME']
        print("\n跨周期引用检查:")
        for ref in expected_refs:
            if ref in python_code:
                print(f"  [OK] 找到跨周期引用: {ref}")
            else:
                print(f"  [X] 未找到跨周期引用: {ref}")
        
    except Exception as e:
        print(f"[X] 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    test_cross_period_ref()
    test_cross_period_ref_in_expression()
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)




