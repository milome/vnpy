#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试策略加载功能
模拟 CTA 引擎如何加载策略
"""

import importlib
import sys
from pathlib import Path
from vnpy_ctastrategy.template import CtaTemplate, TargetPosTemplate

def load_strategy_class_from_folder(path: Path, module_name: str = ""):
    """
    从文件夹加载策略类（模拟 CtaEngine 的逻辑）
    """
    from glob import glob
    
    classes = {}
    
    for suffix in ["py", "pyd", "so"]:
        pathname: str = str(path.joinpath(f"*.{suffix}"))
        for filepath in glob(pathname):
            filename = Path(filepath).stem
            name: str = f"{module_name}.{filename}"
            
            try:
                module = importlib.import_module(name)
                importlib.reload(module)
                
                print(f"\n检查模块: {name}")
                print(f"  文件: {filepath}")
                
                for attr_name in dir(module):
                    value = getattr(module, attr_name)
                    if (
                        isinstance(value, type)
                        and issubclass(value, CtaTemplate)
                        and value not in {CtaTemplate, TargetPosTemplate}
                    ):
                        print(f"  [OK] 找到策略类: {attr_name}")
                        print(f"    - 作者: {getattr(value, 'author', 'N/A')}")
                        print(f"    - 参数: {getattr(value, 'parameters', [])[:3]}...")
                        classes[value.__name__] = value
            except Exception as e:
                print(f"  [ERROR] 加载失败: {name}")
                print(f"    错误: {e}")
                import traceback
                traceback.print_exc()
    
    return classes


def main():
    """主函数"""
    print("=" * 60)
    print("测试策略加载功能")
    print("=" * 60)
    
    # 测试从 vnpy_ctastrategy.strategies 加载
    path1 = Path(__file__).parent / "vnpy_ctastrategy" / "vnpy_ctastrategy" / "strategies"
    print(f"\n扫描路径1: {path1}")
    
    if not path1.exists():
        print(f"  路径不存在: {path1}")
    else:
        classes1 = load_strategy_class_from_folder(path1, "vnpy_ctastrategy.strategies")
        print(f"\n从路径1加载的策略类: {list(classes1.keys())}")
    
    # 测试从当前目录的 strategies 加载
    path2 = Path.cwd() / "strategies"
    print(f"\n扫描路径2: {path2}")
    
    if not path2.exists():
        print(f"  路径不存在: {path2}")
    else:
        classes2 = load_strategy_class_from_folder(path2, "strategies")
        print(f"\n从路径2加载的策略类: {list(classes2.keys())}")
    
    # 检查 TestImportStrategy 是否被加载
    all_classes = {**classes1, **classes2}
    
    print("\n" + "=" * 60)
    print("总结")
    print("=" * 60)
    print(f"总共加载了 {len(all_classes)} 个策略类:")
    for name in sorted(all_classes.keys()):
        print(f"  - {name}")
    
    if "TestImportStrategy" in all_classes:
        print("\n[SUCCESS] TestImportStrategy 已成功加载！")
    else:
        print("\n[FAILED] TestImportStrategy 未找到！")
        print("\n可能的原因:")
        print("  1. 策略文件路径不正确")
        print("  2. 策略类名不是 TestImportStrategy")
        print("  3. 导入时发生错误（请查看上面的错误信息）")


if __name__ == "__main__":
    main()

