#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试策略代码生成器
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from mflang.strategy_generator import generate_strategy_from_model


def test_generate_test_import_strategy():
    """测试生成 TEST_IMPORT 模型的策略文件"""
    print("=" * 60)
    print("测试生成 TEST_IMPORT 模型的策略文件")
    print("=" * 60)
    print()
    
    # 生成策略文件
    output_file = "strategies/test_import_strategy.py"
    code = generate_strategy_from_model(
        model_name="TEST_IMPORT",
        strategy_class_name="TestImportStrategy",
        output_file=output_file,
        author="MFLang Generator"
    )
    
    print(f"[OK] 策略文件已生成: {output_file}")
    print()
    
    # 验证生成的代码
    print("验证生成的代码:")
    print("-" * 60)
    
    # 检查关键元素
    checks = [
        ("from vnpy_ctastrategy import", "导入 vnpy_ctastrategy 模块"),
        ("class TestImportStrategy(CtaTemplate)", "策略类定义"),
        ("def __init__", "__init__ 方法"),
        ("def on_bar", "on_bar 方法"),
        ("def _calculate_cross_period_vars", "跨周期变量计算方法"),
        ("def _calculate_variable_cc", "CC 变量计算方法"),
        ("def _calculate_variable_isbuytrend", "ISBUYTREND 变量计算方法"),
        ("self.min5_am", "MIN5 周期数据管理器"),
        ("self.min5_vars", "MIN5 变量缓存"),
    ]
    
    for check_str, description in checks:
        if check_str in code:
            print(f"  [OK] {description}")
        else:
            print(f"  [错误] 缺少: {description}")
    
    print()
    print("=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    test_generate_test_import_strategy()

