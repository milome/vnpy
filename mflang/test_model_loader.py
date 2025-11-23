#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试模型文件加载器
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from mflang.model_loader import ModelLoader, get_model_loader, load_model, get_variable


def test_load_model():
    """测试加载模型文件"""
    print("=" * 50)
    print("测试1: 加载模型文件")
    print("=" * 50)
    
    # 测试加载AA模型
    try:
        model = load_model("AA")
        print(f"模型AA加载成功:")
        for var_name, var_expr in model.items():
            print(f"  {var_name}: {var_expr}")
        print()
    except Exception as e:
        print(f"加载失败: {e}")
        print()
    
    # 测试加载CC模型
    try:
        model = load_model("CC")
        print(f"模型CC加载成功:")
        for var_name, var_expr in model.items():
            print(f"  {var_name}: {var_expr}")
        print()
    except Exception as e:
        print(f"加载失败: {e}")
        print()


def test_get_variable():
    """测试获取模型中的变量"""
    print("=" * 50)
    print("测试2: 获取模型中的变量")
    print("=" * 50)
    
    # 测试获取AA模型中的CC变量
    cc_expr = get_variable("AA", "CC")
    if cc_expr:
        print(f"AA模型中的CC变量: {cc_expr}")
    else:
        print("未找到AA模型中的CC变量")
    print()
    
    # 测试获取CC模型中的CC变量
    cc_expr = get_variable("CC", "CC")
    if cc_expr:
        print(f"CC模型中的CC变量: {cc_expr}")
    else:
        print("未找到CC模型中的CC变量")
    print()


def test_list_models():
    """测试列出所有模型"""
    print("=" * 50)
    print("测试3: 列出所有模型")
    print("=" * 50)
    
    loader = get_model_loader()
    models = loader.list_models()
    print(f"找到 {len(models)} 个模型文件:")
    for model in models:
        print(f"  - {model}")
    print()


def test_model_loader_instance():
    """测试ModelLoader实例"""
    print("=" * 50)
    print("测试4: ModelLoader实例")
    print("=" * 50)
    
    # 创建自定义目录的加载器
    current_dir = Path(__file__).parent
    models_dir = current_dir / "mmodels"
    
    loader = ModelLoader(str(models_dir))
    
    # 测试加载
    try:
        model = loader.load_model("AA")
        print(f"使用自定义目录加载AA模型成功:")
        for var_name, var_expr in model.items():
            print(f"  {var_name}: {var_expr}")
        print()
    except Exception as e:
        print(f"加载失败: {e}")
        print()
    
    # 测试缓存
    print("测试缓存功能:")
    model1 = loader.load_model("AA")
    model2 = loader.load_model("AA")
    print(f"两次加载是否为同一对象: {model1 is model2}")
    print()
    
    # 清除缓存
    loader.clear_cache()
    model3 = loader.load_model("AA")
    print(f"清除缓存后是否为同一对象: {model1 is model3}")
    print()


def test_invalid_model():
    """测试无效模型文件"""
    print("=" * 50)
    print("测试5: 无效模型文件")
    print("=" * 50)
    
    # 测试不存在的模型
    try:
        model = load_model("NONEXISTENT")
        print("错误: 应该抛出异常")
    except FileNotFoundError as e:
        print(f"[OK] 正确捕获错误: {e}")
    except Exception as e:
        print(f"[OK] 捕获到其他错误: {e}")
    print()


def test_model_with_comments():
    """测试带注释的模型文件"""
    print("=" * 50)
    print("测试6: 带注释的模型文件")
    print("=" * 50)
    
    # 创建临时模型文件
    test_model_content = """
    // 这是注释
    VAR1:REF(C,1);  // 行内注释
    VAR2:MA(C,5);   // 另一个变量
    // 保存指标，命名为TEST
    """
    
    # 这里只是演示，实际测试需要创建临时文件
    print("模型文件应能正确处理注释:")
    print("  - 行首注释（//开头）")
    print("  - 行内注释（//在行中）")
    print("  - '保存指标，命名为'等关键字应被忽略")
    print()


if __name__ == "__main__":
    test_load_model()
    test_get_variable()
    test_list_models()
    test_model_loader_instance()
    test_invalid_model()
    test_model_with_comments()
    
    print("=" * 50)
    print("所有测试完成！")
    print("=" * 50)

