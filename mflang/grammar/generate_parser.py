#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成ANTLR解析器的辅助脚本
如果系统已安装ANTLR，可以使用此脚本生成解析器
"""

import os
import subprocess
import sys
from pathlib import Path

def find_antlr_jar():
    """查找ANTLR jar文件"""
    # 查找可能的jar文件位置
    project_root = Path(__file__).parent.parent.parent
    possible_locations = [
        project_root / "jars" / "antlr-4.13.2-complete.jar",
        project_root / "jars" / "antlr-*.jar",
        Path.home() / ".antlr" / "antlr-*.jar",
        Path("/usr/local/lib/antlr-*.jar"),
    ]
    
    # 首先尝试精确匹配
    jar_file = project_root / "jars" / "antlr-4.13.2-complete.jar"
    if jar_file.exists():
        print(f"[OK] 找到ANTLR jar文件: {jar_file}")
        return jar_file
    
    # 尝试通配符匹配
    for pattern in possible_locations:
        if '*' in str(pattern):
            # 使用glob查找
            parent = pattern.parent
            if parent.exists():
                matches = list(parent.glob(pattern.name))
                if matches:
                    jar_file = matches[0]
                    print(f"[OK] 找到ANTLR jar文件: {jar_file}")
                    return jar_file
        elif pattern.exists():
            print(f"[OK] 找到ANTLR jar文件: {pattern}")
            return pattern
    
    return None

def find_java():
    """查找Java可执行文件"""
    import platform
    import glob
    
    # 首先尝试PATH中的java
    try:
        result = subprocess.run(['java', '-version'], 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE,
                              text=True)
        if result.stderr:  # 有输出说明Java存在
            version_line = result.stderr.split('\n')[0] if result.stderr else "Java已安装"
            print(f"[OK] Java在PATH中: {version_line}")
            return 'java'
    except FileNotFoundError:
        pass
    
    # Windows: 尝试常见安装位置
    if platform.system() == 'Windows':
        common_patterns = [
            r"D:\Program Files\Java\jdk-*\bin\java.exe",  # 用户提供的路径模式
            r"C:\Program Files\Java\jdk-*\bin\java.exe",
            r"C:\Program Files\Eclipse Adoptium\jdk-*-hotspot\bin\java.exe",
            r"C:\Program Files\OpenJDK\openjdk-*\bin\java.exe",
            r"C:\Program Files\Amazon Corretto\jdk*\bin\java.exe",
            r"C:\Program Files (x86)\Java\jdk-*\bin\java.exe",
        ]
        
        for pattern in common_patterns:
            matches = glob.glob(pattern)
            if matches:
                # 按版本号排序，选择最新的
                matches.sort(reverse=True)
                java_path = matches[0]
                print(f"[OK] 找到Java: {java_path}")
                # 验证
                try:
                    result = subprocess.run([java_path, '-version'],
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE,
                                          text=True)
                    if result.stderr:
                        return java_path
                except:
                    continue
    
    return None

def check_java():
    """检查Java是否可用"""
    java_cmd = find_java()
    if java_cmd:
        return java_cmd
    
    print("[X] Java未安装或不在PATH中")
    print("\n请先安装Java:")
    print("  - Windows: 下载并安装JDK")
    print("  - Linux: sudo apt-get install default-jdk")
    print("  - macOS: brew install openjdk")
    print("\n如果Java已安装，请:")
    print("  1. 重新打开命令行窗口（Java安装后需要重启终端）")
    print("  2. 或将Java添加到系统PATH环境变量")
    print("  3. 或使用 generate_parser_manual.bat 并手动指定Java路径")
    return None

def check_antlr():
    """检查ANTLR是否可用（通过jar文件或命令）"""
    # 首先尝试查找jar文件
    jar_file = find_antlr_jar()
    if jar_file:
        return jar_file
    
    # 尝试使用antlr4命令
    try:
        result = subprocess.run(['antlr4', '--version'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"[OK] ANTLR命令可用: {result.stdout.strip()}")
            return "command"  # 返回特殊标记表示使用命令
    except FileNotFoundError:
        pass
    
    print("[X] 未找到ANTLR")
    print("\n请确保:")
    print("1. jar文件位于: jars/antlr-4.13.2-complete.jar")
    print("2. 或安装ANTLR并添加到PATH")
    return None

def generate_parser(antlr_source, java_cmd=None):
    """生成ANTLR解析器"""
    grammar_dir = Path(__file__).parent
    grammar_file = grammar_dir / "MFLang.g4"
    
    if not grammar_file.exists():
        print(f"[X] 语法文件不存在: {grammar_file}")
        return False
    
    print(f"[OK] 找到语法文件: {grammar_file}")
    
    # 构建命令
    if isinstance(antlr_source, Path):
        # 使用jar文件
        java_executable = java_cmd if java_cmd else 'java'
        cmd = [
            java_executable,
            '-jar',
            str(antlr_source),
            '-Dlanguage=Python3',
            '-visitor',  # 生成访问者接口
            '-o', str(grammar_dir),
            str(grammar_file)
        ]
        print(f"\n使用jar文件: {antlr_source}")
        print(f"使用Java: {java_executable}")
    else:
        # 使用antlr4命令
        cmd = [
            'antlr4',
            '-Dlanguage=Python3',
            '-visitor',  # 生成访问者接口
            '-o', str(grammar_dir),
            str(grammar_file)
        ]
        print(f"\n使用antlr4命令")
    
    print(f"执行命令: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, cwd=grammar_dir, 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("[OK] 解析器生成成功!")
            print("\n生成的文件:")
            for ext in ['Lexer.py', 'Parser.py', 'Listener.py', 'Visitor.py']:
                file_path = grammar_dir / f"MFLang{ext}"
                if file_path.exists():
                    print(f"  - {file_path.name}")
            return True
        else:
            print(f"[X] 生成失败:")
            if result.stderr:
                print(result.stderr)
            if result.stdout:
                print(result.stdout)
            return False
            
    except FileNotFoundError as e:
        print(f"[X] 无法执行命令: {e}")
        if isinstance(antlr_source, Path):
            print("请确保Java已正确安装并在PATH中")
        else:
            print("请确保ANTLR已正确安装并在PATH中")
        return False
    except Exception as e:
        print(f"[X] 生成过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return False

def install_runtime():
    """安装ANTLR Python运行时"""
    print("\n检查ANTLR Python运行时...")
    try:
        import antlr4
        print("[OK] antlr4-python3-runtime已安装")
        return True
    except ImportError:
        print("[X] antlr4-python3-runtime未安装")
        print("\n正在安装...")
        try:
            result = subprocess.run([sys.executable, '-m', 'pip', 'install', 
                          'antlr4-python3-runtime'], 
                          capture_output=True, text=True, check=True)
            print("[OK] 安装成功!")
            return True
        except subprocess.CalledProcessError as e:
            print("[X] 安装失败，请手动执行:")
            print("  pip install antlr4-python3-runtime")
            if e.stderr:
                print(f"错误信息: {e.stderr}")
            return False

if __name__ == '__main__':
    print("=" * 60)
    print("麦语言 ANTLR 解析器生成工具")
    print("=" * 60)
    
    # 检查并安装运行时
    if not install_runtime():
        sys.exit(1)
    
    # 检查Java（使用jar文件时需要）
    antlr_source = check_antlr()
    if antlr_source is None:
        print("\n提示:")
        print("1. 将antlr-4.13.2-complete.jar放在 jars/ 目录下")
        print("2. 或安装ANTLR并添加到PATH")
        print("3. 或手动运行: java -jar jars/antlr-4.13.2-complete.jar -Dlanguage=Python3 -visitor MFLang.g4")
        sys.exit(1)
    
    # 如果使用jar文件，检查Java
    java_cmd = None
    if isinstance(antlr_source, Path):
        java_cmd = check_java()
        if not java_cmd:
            print("\n" + "=" * 60)
            print("提示: Java可能已安装但未添加到PATH")
            print("=" * 60)
            print("\n请尝试以下方法:")
            print("1. 重新打开命令行窗口（Java安装后需要重启终端）")
            print("2. 检查Java是否在PATH中:")
            print("   - 在命令行运行: where java")
            print("   - 如果找不到，需要手动添加到PATH")
            print("3. 使用批处理脚本（推荐）:")
            print("   - 双击运行: generate_parser_manual.bat")
            print("   - 在脚本中设置JAVA_PATH变量")
            print("4. 或者手动运行生成命令:")
            print(f"   cd {Path(__file__).parent}")
            print(f"   java -jar {antlr_source} -Dlanguage=Python3 -visitor MFLang.g4")
            sys.exit(1)
    
    # 生成解析器
    if generate_parser(antlr_source, java_cmd):
        print("\n" + "=" * 60)
        print("[OK] 解析器生成完成!")
        print("=" * 60)
        print("\n下一步:")
        print("1. 查看生成的解析器文件")
        print("2. 使用 mflang.grammar.ast_visitor 实现AST访问者")
        print("3. 使用 mflang.grammar.code_generator 生成Python代码")
    else:
        sys.exit(1)

