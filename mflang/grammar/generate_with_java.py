#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动指定Java路径生成解析器
如果Java不在PATH中，可以使用此脚本
"""

import subprocess
import sys
from pathlib import Path

# ============================================================
# 配置区域：如果Java不在PATH，请修改下面的JAVA_PATH
# ============================================================

# 取消注释并设置您的Java完整路径，例如：
# JAVA_PATH = r"C:\Program Files\Eclipse Adoptium\jdk-11.0.19.9-hotspot\bin\java.exe"
# JAVA_PATH = r"C:\Program Files\Java\jdk-11\bin\java.exe"
JAVA_PATH = None  # 如果为None，将尝试使用PATH中的java

# ============================================================

def main():
    project_root = Path(__file__).parent.parent.parent
    grammar_dir = Path(__file__).parent
    jar_file = project_root / "jars" / "antlr-4.13.2-complete.jar"
    grammar_file = grammar_dir / "MFLang.g4"
    
    print("=" * 60)
    print("麦语言 ANTLR 解析器生成工具 (手动Java路径)")
    print("=" * 60)
    print()
    
    # 检查文件
    if not jar_file.exists():
        print(f"[X] 找不到jar文件: {jar_file}")
        return 1
    
    if not grammar_file.exists():
        print(f"[X] 找不到语法文件: {grammar_file}")
        return 1
    
    print(f"[OK] jar文件: {jar_file}")
    print(f"[OK] 语法文件: {grammar_file}")
    print()
    
    # 确定Java命令
    if JAVA_PATH:
        java_cmd = JAVA_PATH
        print(f"[OK] 使用指定的Java: {java_cmd}")
    else:
        java_cmd = 'java'
        print("[OK] 尝试使用PATH中的java")
    
    # 验证Java
    print("验证Java...")
    try:
        result = subprocess.run([java_cmd, '-version'],
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              text=True)
        if result.stderr:
            version = result.stderr.split('\n')[0]
            print(f"[OK] Java可用: {version}")
        else:
            print("[X] Java验证失败")
            return 1
    except Exception as e:
        print(f"[X] 无法运行Java: {e}")
        print("\n请:")
        print("1. 修改此脚本，设置JAVA_PATH变量（在文件顶部）")
        print("2. 或将Java添加到系统PATH")
        return 1
    
    print()
    
    # 生成解析器
    print("正在生成解析器...")
    cmd = [
        java_cmd,
        '-jar',
        str(jar_file),
        '-Dlanguage=Python3',
        '-visitor',
        '-o', str(grammar_dir),
        str(grammar_file)
    ]
    
    print(f"执行: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(cmd, cwd=grammar_dir,
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("[OK] 解析器生成成功!")
            print()
            print("生成的文件:")
            for ext in ['Lexer.py', 'Parser.py', 'Listener.py', 'Visitor.py']:
                file_path = grammar_dir / f"MFLang{ext}"
                if file_path.exists():
                    print(f"  - {file_path.name}")
            print()
            print("=" * 60)
            print("[OK] 完成!")
            print("=" * 60)
            return 0
        else:
            print("[X] 生成失败:")
            if result.stderr:
                print(result.stderr)
            if result.stdout:
                print(result.stdout)
            return 1
            
    except Exception as e:
        print(f"[X] 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())

