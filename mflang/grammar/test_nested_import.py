#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试嵌套IMPORT（解析被导入的模型文件）
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from mflang.grammar import parse_mflang_string, parse_mflang_file
from mflang.grammar.code_generator import StrategyCodeGenerator


def test_parse_imported_model():
    """测试解析被导入的模型文件"""
    print("=" * 60)
    print("测试解析被导入的模型文件")
    print("=" * 60)
    
    # 测试解析"米仓I号日内趋势"模型文件
    models_dir = project_root / "mflang" / "mmodels"
    model_file = models_dir / "米仓I号日内趋势"
    
    if not model_file.exists():
        print(f"[X] 模型文件不存在: {model_file}")
        return
    
    try:
        ast = parse_mflang_file(str(model_file))
        print(f"[OK] 成功解析模型文件: {model_file.name}")
        
        # 检查AST结构
        if ast and ast.children:
            print(f"[OK] AST包含 {len(ast.children)} 个子节点")
            
            # 统计变量数量
            from mflang.grammar.ast_visitor import VariableAssignNode, NodeType
            variables = []
            def collect_vars(node):
                if node and node.node_type == NodeType.VARIABLE_ASSIGN:
                    if isinstance(node, VariableAssignNode):
                        variables.append(node.var_name)
                if node and node.children:
                    for child in node.children:
                        collect_vars(child)
            
            collect_vars(ast)
            print(f"[OK] 找到 {len(variables)} 个变量定义")
            if variables:
                print(f"    示例变量: {variables[:5]}")
        else:
            print("[X] AST为空或无效")
            
    except Exception as e:
        print(f"[X] 解析失败: {e}")
        import traceback
        traceback.print_exc()


def test_nested_import_code_generation():
    """测试嵌套IMPORT的代码生成"""
    print("\n" + "=" * 60)
    print("测试嵌套IMPORT的代码生成")
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
        
        print("\n生成的Python代码片段（注册模型部分）:")
        print("-" * 60)
        lines = python_code.split('\n')
        in_register_section = False
        for i, line in enumerate(lines):
            if '注册导入的模型' in line:
                in_register_section = True
            if in_register_section:
                print(line)
                # 打印接下来的10行
                if i + 1 < len(lines) and 'register_indicator' in line:
                    for j in range(i + 1, min(i + 6, len(lines))):
                        print(lines[j])
                    break
        print("-" * 60)
        
        # 检查关键元素
        checks = [
            ('register_indicator', 'IndicatorManager注册'),
            ('米仓I号日内趋势', '模型文件名'),
            ('HOURTREND', '变量名'),
            ('get_indicator_smart', '跨周期数据获取'),
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


def test_parse_rice1_full():
    """测试解析完整的RICE1.txt文件（包含多个IMPORT）"""
    print("\n" + "=" * 60)
    print("测试解析完整的RICE1.txt文件")
    print("=" * 60)
    
    models_dir = project_root / "mflang" / "mmodels"
    rice1_file = models_dir / "RICE1.txt"
    
    if not rice1_file.exists():
        print(f"[X] RICE1.txt文件不存在: {rice1_file}")
        return
    
    try:
        # 解析RICE1.txt
        print(f"\n[1] 解析主模型文件: RICE1.txt")
        ast = parse_mflang_file(str(rice1_file))
        print(f"[OK] 成功解析RICE1.txt")
        
        # 检查IMPORT语句
        from mflang.grammar.ast_visitor import ImportNode, NodeType
        import_statements = []
        def collect_imports(node):
            if node and node.node_type == NodeType.IMPORT:
                if isinstance(node, ImportNode):
                    import_statements.append(node)
            if node and node.children:
                for child in node.children:
                    collect_imports(child)
        
        collect_imports(ast)
        print(f"[OK] 找到 {len(import_statements)} 个IMPORT语句")
        for imp in import_statements:
            print(f"     - #IMPORT [{imp.period_type},{imp.period_n},{imp.formula}] AS {imp.var_name}")
        
        # 检查跨周期引用
        from mflang.grammar.ast_visitor import CrossPeriodRefNode
        cross_period_refs = []
        def collect_cross_refs(node):
            if node and node.node_type == NodeType.CROSS_PERIOD_REF:
                if isinstance(node, CrossPeriodRefNode):
                    cross_period_refs.append(node)
            if node and node.children:
                for child in node.children:
                    collect_cross_refs(child)
        
        collect_cross_refs(ast)
        print(f"[OK] 找到 {len(cross_period_refs)} 个跨周期引用")
        if cross_period_refs:
            print(f"    示例引用:")
            for ref in cross_period_refs[:5]:
                print(f"     - {ref.var_name}.{ref.field_name}")
        
        # 生成策略代码
        print(f"\n[2] 生成策略代码")
        generator = StrategyCodeGenerator("RICE1Strategy")
        python_code = generator.generate(ast)
        
        print(f"[OK] 成功生成策略代码 ({len(python_code)} 字符)")
        
        # 检查生成的代码
        print(f"\n[3] 检查生成的代码")
        checks = [
            ('IndicatorManager', 'IndicatorManager导入'),
            ('self.indicator_manager', 'IndicatorManager实例'),
            ('register_indicator', '模型注册'),
            ('get_indicator_smart', '跨周期数据获取'),
            ('米仓I号日内趋势', '导入模型1'),
            ('米仓I号小时趋势', '导入模型2'),
            ('米仓I号多周期MACD', '导入模型3'),
            ('米仓I号追踪区域', '导入模型4'),
            ('米仓I号单周期MACD', '导入模型5'),
            ('米仓I号变量赋值', '导入模型6'),
        ]
        
        passed = 0
        for check_str, desc in checks:
            if check_str in python_code:
                print(f"  [OK] {desc}: 找到 {check_str}")
                passed += 1
            else:
                print(f"  [X] {desc}: 未找到 {check_str}")
        
        print(f"\n[4] 代码检查结果: {passed}/{len(checks)} 通过")
        
        # 统计注册的指标数量
        register_count = python_code.count('register_indicator')
        print(f"[OK] 生成了 {register_count} 个register_indicator调用")
        
        # 统计跨周期引用获取代码
        get_indicator_count = python_code.count('get_indicator_smart')
        print(f"[OK] 生成了 {get_indicator_count} 个get_indicator_smart调用")
        
        # 保存生成的代码到文件（可选）
        output_file = project_root / "mflang" / "grammar" / "generated_rice1_strategy.py"
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(python_code)
            print(f"\n[5] 生成的代码已保存到: {output_file}")
        except Exception as e:
            print(f"\n[5] 保存代码失败: {e}")
        
        # 显示代码片段
        print(f"\n[6] 生成的代码片段（注册模型部分）:")
        print("-" * 60)
        lines = python_code.split('\n')
        in_register_section = False
        register_lines_shown = 0
        for i, line in enumerate(lines):
            if '注册导入的模型' in line:
                in_register_section = True
            if in_register_section:
                print(line)
                register_lines_shown += 1
                if register_lines_shown > 30:  # 只显示前30行
                    print("    ... (更多代码) ...")
                    break
        print("-" * 60)
        
    except Exception as e:
        print(f"[X] 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    import sys
    import traceback
    
    try:
        print("开始运行测试...")
        test_parse_imported_model()
        test_nested_import_code_generation()
        test_parse_rice1_full()
        print("\n" + "=" * 60)
        print("所有测试完成!")
        print("=" * 60)
    except Exception as e:
        print(f"\n[严重错误] 测试过程中发生异常: {e}")
        traceback.print_exc()
        sys.exit(1)

