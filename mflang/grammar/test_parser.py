#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试解析器和代码生成器
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from mflang.grammar import (
    parse_mflang_file,
    StrategyCodeGenerator
)


def test_simple_parse():
    """测试简单解析"""
    print("=" * 60)
    print("测试简单麦语言代码解析")
    print("=" * 60)
    
    code = """
    VARIABLE: NUMOFDAY := 0;
    NUMOFDAY: BARPOS, NODRAW;
    ISUPTREND := MAINTREND1M >= REF(MAINTREND1M,5), PRECIS0, NODRAW;
    """
    
    try:
        from mflang.grammar.parser import parse_mflang_string
        ast = parse_mflang_string(code)
        print("[OK] 解析成功!")
        print(f"AST根节点类型: {ast.node_type}")
        print(f"子节点数量: {len(ast.children)}")
    except ImportError as e:
        print(f"✗ 解析器未生成: {e}")
        print("\n请先运行: python mflang/grammar/generate_parser.py")
    except Exception as e:
        print(f"✗ 解析失败: {e}")


def test_code_generation():
    """测试代码生成"""
    print("\n" + "=" * 60)
    print("测试代码生成")
    print("=" * 60)
    
    code = """
    NUMOFDAY: BARPOS, NODRAW;
    MAINTREND1M: EMA(CLOSE, 3), PRECIS3;
    ISUPTREND := MAINTREND1M >= REF(MAINTREND1M,5), PRECIS0, NODRAW;
    ISUPTREND,BP;
    """
    
    try:
        from mflang.grammar.parser import parse_mflang_string
        from mflang.grammar.code_generator import StrategyCodeGenerator
        
        # 解析
        ast = parse_mflang_string(code)
        print("[OK] AST构建成功!")
        
        # 生成代码
        generator = StrategyCodeGenerator("TestStrategy")
        python_code = generator.generate(ast)
        print("[OK] Python代码生成成功!")
        print("\n生成的代码:")
        print("-" * 60)
        print(python_code)
        print("-" * 60)
        
        # 验证变量映射
        print("\n变量映射验证:")
        checks = [
            ('self.am.close', 'CLOSE映射'),
            ('self.MAINTREND1M', '变量映射'),
            ('self.NUMOFDAY', '变量映射'),
        ]
        for check_str, desc in checks:
            if check_str in python_code:
                print(f"  [OK] {desc}: 找到 {check_str}")
            else:
                print(f"  [X] {desc}: 未找到 {check_str}")
        
    except ImportError as e:
        print(f"✗ 解析器未生成: {e}")
    except Exception as e:
        print(f"✗ 代码生成失败: {e}")
        import traceback
        traceback.print_exc()


def test_rice1_parse():
    """测试RICE1.txt解析"""
    print("\n" + "=" * 60)
    print("测试RICE1.txt解析")
    print("=" * 60)
    
    rice1_file = Path(__file__).parent.parent / "mmodels" / "RICE1.txt"
    
    if not rice1_file.exists():
        print(f"[X] 文件不存在: {rice1_file}")
        return
    
    try:
        ast = parse_mflang_file(str(rice1_file))
        print("[OK] RICE1.txt解析成功!")
        print(f"AST根节点类型: {ast.node_type}")
        print(f"语句数量: {len(ast.children)}")
        
        # 统计各种节点类型
        from collections import Counter
        from mflang.grammar.ast_visitor import NodeType
        
        def count_nodes(node, counter):
            if node:
                counter[node.node_type] += 1
                for child in node.children:
                    count_nodes(child, counter)
        
        counter = Counter()
        count_nodes(ast, counter)
        
        print("\n节点统计:")
        for node_type, count in counter.most_common():
            print(f"  {node_type.value}: {count}")
        
    except ImportError as e:
        print(f"✗ 解析器未生成: {e}")
        print("\n请先运行: python mflang/grammar/generate_parser.py")
    except Exception as e:
        print(f"✗ 解析失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    print("麦语言解析器测试")
    print("=" * 60)
    
    # 测试1: 简单解析
    test_simple_parse()
    
    # 测试2: 代码生成
    test_code_generation()
    
    # 测试3: RICE1.txt解析（可选，可能较慢）
    # test_rice1_parse()
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)

