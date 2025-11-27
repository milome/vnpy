#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试解析完整的RICE1.txt文件（包含多个IMPORT）
这是完整的测试用例，测试解析RICE1.txt及其导入的模型文件
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from mflang.grammar import parse_mflang_file
from mflang.grammar.code_generator import StrategyCodeGenerator


def main():
    """主测试函数"""
    import sys
    sys.stdout.flush()
    print("=" * 80)
    print("测试解析完整的RICE1.txt文件（包含多个IMPORT）")
    print("=" * 80)
    sys.stdout.flush()
    
    models_dir = project_root / "mflang" / "mmodels"
    rice1_file = models_dir / "RICE1.txt"
    
    if not rice1_file.exists():
        print(f"[X] RICE1.txt文件不存在: {rice1_file}")
        return False
    
    try:
        # 步骤1: 解析RICE1.txt
        print(f"\n[步骤1] 解析主模型文件: RICE1.txt")
        print("-" * 80)
        ast = parse_mflang_file(str(rice1_file))
        print(f"[OK] 成功解析RICE1.txt")
        
        # 步骤2: 检查IMPORT语句
        print(f"\n[步骤2] 检查IMPORT语句")
        print("-" * 80)
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
        print(f"[OK] 找到 {len(import_statements)} 个IMPORT语句:")
        for i, imp in enumerate(import_statements, 1):
            print(f"  {i}. #IMPORT [{imp.period_type},{imp.period_n},{imp.formula}] AS {imp.var_name}")
        
        # 步骤3: 检查跨周期引用
        print(f"\n[步骤3] 检查跨周期引用")
        print("-" * 80)
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
            # 按var_name分组统计
            refs_by_var = {}
            for ref in cross_period_refs:
                if ref.var_name not in refs_by_var:
                    refs_by_var[ref.var_name] = []
                refs_by_var[ref.var_name].append(ref.field_name)
            
            print(f"  按变量名分组:")
            for var_name, fields in refs_by_var.items():
                print(f"    {var_name}: {len(fields)} 个引用 ({', '.join(fields[:5])}{'...' if len(fields) > 5 else ''})")
        
        # 步骤4: 生成策略代码
        print(f"\n[步骤4] 生成策略代码")
        print("-" * 80)
        generator = StrategyCodeGenerator("RICE1Strategy")
        python_code = generator.generate(ast)
        
        print(f"[OK] 成功生成策略代码")
        print(f"  代码长度: {len(python_code)} 字符")
        print(f"  代码行数: {len(python_code.split(chr(10)))} 行")
        
        # 步骤5: 检查生成的代码
        print(f"\n[步骤5] 检查生成的代码")
        print("-" * 80)
        checks = [
            ('IndicatorManager', 'IndicatorManager导入'),
            ('self.indicator_manager', 'IndicatorManager实例'),
            ('register_indicator', '模型注册方法'),
            ('get_indicator_smart', '跨周期数据获取方法'),
        ]
        
        passed = 0
        for check_str, desc in checks:
            if check_str in python_code:
                print(f"  [OK] {desc}: 找到 {check_str}")
                passed += 1
            else:
                print(f"  [X] {desc}: 未找到 {check_str}")
        
        # 检查导入的模型
        print(f"\n  检查导入的模型:")
        imported_models = [
            '米仓I号日内趋势',
            '米仓I号小时趋势',
            '米仓I号多周期MACD',
            '米仓I号追踪区域',
            '米仓I号单周期MACD',
            '米仓I号变量赋值',
        ]
        
        for model_name in imported_models:
            if model_name in python_code:
                print(f"    [OK] 找到模型: {model_name}")
            else:
                print(f"    [X] 未找到模型: {model_name}")
        
        print(f"\n  代码检查结果: {passed}/{len(checks)} 通过")
        
        # 步骤6: 统计生成的代码
        print(f"\n[步骤6] 统计生成的代码")
        print("-" * 80)
        register_count = python_code.count('register_indicator')
        get_indicator_count = python_code.count('get_indicator_smart')
        print(f"  register_indicator调用: {register_count} 次")
        print(f"  get_indicator_smart调用: {get_indicator_count} 次")
        
        # 步骤7: 保存生成的代码
        print(f"\n[步骤7] 保存生成的代码")
        print("-" * 80)
        output_file = project_root / "mflang" / "grammar" / "generated_rice1_strategy.py"
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(python_code)
            print(f"  [OK] 生成的代码已保存到: {output_file}")
            print(f"  文件大小: {output_file.stat().st_size} 字节")
        except Exception as e:
            print(f"  [X] 保存代码失败: {e}")
        
        # 步骤8: 显示代码片段
        print(f"\n[步骤8] 生成的代码片段（注册模型部分）")
        print("-" * 80)
        lines = python_code.split('\n')
        in_register_section = False
        register_lines_shown = 0
        for i, line in enumerate(lines):
            if '注册导入的模型' in line:
                in_register_section = True
            if in_register_section:
                print(f"  {i+1:4d}: {line}")
                register_lines_shown += 1
                if register_lines_shown > 40:  # 显示前40行
                    print(f"  ... (更多代码，共 {len(lines)} 行) ...")
                    break
        
        print("\n" + "=" * 80)
        print("测试完成!")
        print("=" * 80)
        return True
        
    except Exception as e:
        error_msg = f"\n[X] 测试失败: {e}"
        print(error_msg)
        import traceback
        # 同时输出到stderr（会被重定向到日志文件）
        import sys
        sys.stderr.write(f"\n测试失败详细信息:\n")
        sys.stderr.write(f"错误类型: {type(e).__name__}\n")
        sys.stderr.write(f"错误消息: {str(e)}\n")
        traceback.print_exc()
        return False


if __name__ == '__main__':
    import sys
    import traceback
    from datetime import datetime
    
    # 创建错误日志文件
    error_log_file = Path(__file__).parent / "test_rice1_import_errors.log"
    
    # 同时输出到控制台和文件
    class TeeOutput:
        def __init__(self, *files):
            self.files = files
        
        def write(self, obj):
            for f in self.files:
                f.write(obj)
                f.flush()
        
        def flush(self):
            for f in self.files:
                f.flush()
    
    try:
        # 打开错误日志文件
        with open(error_log_file, 'w', encoding='utf-8') as log_file:
            # 写入开始时间
            log_file.write(f"=" * 80 + "\n")
            log_file.write(f"测试开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            log_file.write(f"=" * 80 + "\n\n")
            log_file.flush()
            
            # 将stderr重定向到文件和控制台
            original_stderr = sys.stderr
            sys.stderr = TeeOutput(original_stderr, log_file)
            
            try:
                # 强制刷新输出
                sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
                sys.stderr.reconfigure(encoding='utf-8') if hasattr(sys.stderr, 'reconfigure') else None
                
                print(f"错误日志将保存到: {error_log_file}")
                print("=" * 80)
                
                success = main()
                
                sys.stdout.flush()
                sys.stderr.flush()
                
                # 写入结束时间
                log_file.write(f"\n" + "=" * 80 + "\n")
                log_file.write(f"测试结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                log_file.write(f"测试结果: {'成功' if success else '失败'}\n")
                log_file.write(f"=" * 80 + "\n")
                log_file.flush()
                
                print(f"\n错误日志已保存到: {error_log_file}")
                sys.exit(0 if success else 1)
                
            except KeyboardInterrupt:
                error_msg = "\n\n测试被用户中断"
                print(error_msg)
                log_file.write(error_msg + "\n")
                sys.exit(1)
            except Exception as e:
                error_msg = f"\n\n未捕获的异常: {e}"
                print(error_msg)
                log_file.write(error_msg + "\n")
                log_file.write("\n完整堆栈跟踪:\n")
                traceback.print_exc(file=log_file)
                traceback.print_exc()
                log_file.write(f"\n测试结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                sys.exit(1)
            finally:
                # 恢复原始stderr
                sys.stderr = original_stderr
                
    except Exception as e:
        # 如果连日志文件都无法创建
        print(f"无法创建错误日志文件: {e}")
        traceback.print_exc()
        sys.exit(1)

