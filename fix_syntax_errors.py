#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复转换后Python文件中的语法错误
"""

import os
import re
from pathlib import Path

def fix_syntax_errors_in_file(file_path: str) -> bool:
    """修复单个文件中的语法错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 修复 "self.variable = # TODO: 转换表达式 0" 类型的错误
        pattern1 = r'(\s+self\.\w+\s*=\s*)# TODO: 转换表达式 (\d+)'
        content = re.sub(pattern1, r'\g<1>\g<2>', content)
        
        # 修复 "self.variable = # TODO: 转换表达式 expression" 类型的错误
        pattern2 = r'(\s+self\.\w+\s*=\s*)# TODO: 转换表达式 ([^#\n]+)'
        def replace_expression(match):
            prefix = match.group(1)
            expr = match.group(2).strip()
            
            # 如果是简单数字，直接使用
            if re.match(r'^-?\d+(\.\d+)?$', expr):
                return f"{prefix}{expr}"
            
            # 如果是简单的数学运算，直接使用
            if re.match(r'^-?\d+(\.\d+)?\s*[+\-*/]\s*-?\d+(\.\d+)?$', expr):
                return f"{prefix}{expr}"
            
            # 其他情况，设为0并保留注释
            return f"{prefix}0  # TODO: 转换表达式 {expr}"
        
        content = re.sub(pattern2, replace_expression, content)
        
        # 修复其他常见的语法错误
        # 修复空的赋值语句
        content = re.sub(r'(\s+self\.\w+\s*=\s*)$', r'\g<1>0', content, flags=re.MULTILINE)
        
        # 如果内容有变化，写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
        
    except Exception as e:
        print(f"修复文件 {file_path} 时出错: {e}")
        return False

def fix_all_strategy_files(directory: str = "converted_strategies"):
    """修复目录中所有策略文件的语法错误"""
    directory = Path(directory)
    
    if not directory.exists():
        print(f"目录不存在: {directory}")
        return
    
    fixed_files = []
    error_files = []
    
    for py_file in directory.glob("*.py"):
        print(f"检查文件: {py_file.name}")
        
        try:
            if fix_syntax_errors_in_file(str(py_file)):
                fixed_files.append(py_file.name)
                print(f"  ✓ 已修复语法错误")
            else:
                print(f"  - 无需修复")
        except Exception as e:
            error_files.append((py_file.name, str(e)))
            print(f"  ✗ 修复失败: {e}")
    
    print(f"\n修复完成:")
    print(f"  成功修复: {len(fixed_files)} 个文件")
    if fixed_files:
        for filename in fixed_files:
            print(f"    - {filename}")
    
    print(f"  修复失败: {len(error_files)} 个文件")
    if error_files:
        for filename, error in error_files:
            print(f"    - {filename}: {error}")

def validate_python_syntax(file_path: str) -> bool:
    """验证Python文件语法是否正确"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 尝试编译Python代码
        compile(content, file_path, 'exec')
        return True
        
    except SyntaxError as e:
        print(f"语法错误 {file_path}:{e.lineno}: {e.msg}")
        return False
    except Exception as e:
        print(f"验证文件 {file_path} 时出错: {e}")
        return False

def validate_all_files(directory: str = "converted_strategies"):
    """验证目录中所有Python文件的语法"""
    directory = Path(directory)
    
    if not directory.exists():
        print(f"目录不存在: {directory}")
        return
    
    valid_files = []
    invalid_files = []
    
    for py_file in directory.glob("*.py"):
        if validate_python_syntax(str(py_file)):
            valid_files.append(py_file.name)
        else:
            invalid_files.append(py_file.name)
    
    print(f"\n语法验证结果:")
    print(f"  语法正确: {len(valid_files)} 个文件")
    print(f"  语法错误: {len(invalid_files)} 个文件")
    
    if invalid_files:
        print(f"\n需要修复的文件:")
        for filename in invalid_files:
            print(f"    - {filename}")

if __name__ == "__main__":
    print("=== Python策略文件语法修复工具 ===")
    print("1. 修复语法错误")
    print("2. 验证语法")
    print("3. 修复并验证")
    print("4. 退出")
    
    choice = input("请选择操作 (1-4): ").strip()
    
    if choice == '1':
        directory = input("请输入目录路径 (默认: converted_strategies): ").strip()
        if not directory:
            directory = "converted_strategies"
        fix_all_strategy_files(directory)
    
    elif choice == '2':
        directory = input("请输入目录路径 (默认: converted_strategies): ").strip()
        if not directory:
            directory = "converted_strategies"
        validate_all_files(directory)
    
    elif choice == '3':
        directory = input("请输入目录路径 (默认: converted_strategies): ").strip()
        if not directory:
            directory = "converted_strategies"
        print("正在修复语法错误...")
        fix_all_strategy_files(directory)
        print("\n正在验证语法...")
        validate_all_files(directory)
    
    elif choice == '4':
        print("退出")
    
    else:
        print("无效选择!")

