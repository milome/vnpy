#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
命令行工具：将模型文件转换为策略文件
用法: python mflang/generate_strategy.py <模型文件名> [输出文件路径] [策略类名]
"""

import sys
import argparse
from pathlib import Path

from mflang.strategy_generator import generate_strategy_from_model


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='将模型文件转换为符合 vnpy_ctastrategy 格式的策略文件',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 生成策略文件（自动命名）
  python mflang/generate_strategy.py TEST_IMPORT
  
  # 指定输出文件路径
  python mflang/generate_strategy.py TEST_IMPORT strategies/my_strategy.py
  
  # 指定输出文件路径和策略类名
  python mflang/generate_strategy.py TEST_IMPORT strategies/my_strategy.py MyStrategy
  
  # 指定所有参数
  python mflang/generate_strategy.py TEST_IMPORT strategies/my_strategy.py MyStrategy --author "Your Name"
        """
    )
    
    parser.add_argument(
        'model_name',
        help='模型文件名（不含路径，对应 mflang/mmodels/ 目录下的文件）'
    )
    
    parser.add_argument(
        'output_file',
        nargs='?',
        default=None,
        help='输出文件路径（可选，默认: strategies/<模型名>_strategy.py）'
    )
    
    parser.add_argument(
        'strategy_class_name',
        nargs='?',
        default=None,
        help='策略类名（可选，默认自动生成）'
    )
    
    parser.add_argument(
        '--author',
        default='MFLang Generator',
        help='策略作者（默认: MFLang Generator）'
    )
    
    args = parser.parse_args()
    
    # 确定输出文件路径
    if args.output_file is None:
        # 自动生成输出文件路径
        model_name = args.model_name
        strategy_file_name = f"{model_name.lower()}_strategy.py"
        output_file = f"strategies/{strategy_file_name}"
    else:
        output_file = args.output_file
    
    # 确保输出目录存在
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 生成策略文件
    try:
        print(f"正在生成策略文件...")
        print(f"  模型文件: {args.model_name}")
        print(f"  输出文件: {output_file}")
        if args.strategy_class_name:
            print(f"  策略类名: {args.strategy_class_name}")
        print(f"  作者: {args.author}")
        print()
        
        code = generate_strategy_from_model(
            model_name=args.model_name,
            strategy_class_name=args.strategy_class_name,
            output_file=output_file,
            author=args.author
        )
        
        print(f"[成功] 策略文件已生成: {output_path.absolute()}")
        print(f"       文件大小: {len(code)} 字符")
        print(f"       代码行数: {len(code.splitlines())} 行")
        
        # 验证生成的文件
        if output_path.exists():
            print(f"[验证] 文件已成功保存")
        else:
            print(f"[警告] 文件可能未正确保存")
        
    except FileNotFoundError as e:
        print(f"[错误] 模型文件不存在: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[错误] 生成策略文件失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

