#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的代码质量检查工具
检查转换后的策略文件质量
"""

import os
import re
from pathlib import Path

def check_todo_comments(file_path):
    """检查TODO注释数量"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找所有TODO注释
        todos = re.findall(r'#\s*TODO[^\n]*', content, re.IGNORECASE)
        return len(todos), todos[:3]  # 返回数量和前3个示例
    except:
        return 0, []

def check_syntax_errors(file_path):
    """检查语法错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 尝试编译
        compile(content, file_path, 'exec')
        return True, []
    except SyntaxError as e:
        return False, [f"第{e.lineno}行: {e.msg}"]
    except:
        return True, []  # 其他错误不算语法错误

def check_strategy_structure(file_path):
    """检查策略结构"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        issues = []
        
        # 检查是否继承CtaTemplate
        if 'CtaTemplate' not in content:
            issues.append("未找到CtaTemplate继承")
        
        # 检查必要的方法
        required_methods = ['on_init', 'on_start', 'on_stop', 'on_bar']
        missing = []
        for method in required_methods:
            if not re.search(rf'def\s+{method}\s*\(', content):
                missing.append(method)
        
        if missing:
            issues.append(f"缺少方法: {', '.join(missing)}")
        
        return issues
    except:
        return ["无法检查文件"]

def check_file(file_path):
    """检查单个文件"""
    filename = os.path.basename(file_path)
    # 尝试安全编码文件名
    try:
        safe_filename = filename
    except:
        safe_filename = filename.encode('ascii', 'ignore').decode('ascii')
    
    print(f"\nChecking file: {safe_filename}")
    print("-" * 60)
    
    # 检查TODO注释
    todo_count, todo_examples = check_todo_comments(file_path)
    if todo_count > 0:
        print(f"[TODO] Found {todo_count} TODO comments")
        for todo in todo_examples:
            print(f"  - {todo.strip()[:60]}")
    else:
        print("[OK] No TODO comments")
    
    # 检查语法错误
    is_valid, errors = check_syntax_errors(file_path)
    if is_valid:
        print("[OK] Syntax is valid")
    else:
        print(f"[ERROR] Syntax errors found:")
        for error in errors:
            print(f"  - {error}")
    
    # 检查策略结构
    structure_issues = check_strategy_structure(file_path)
    if not structure_issues:
        print("[OK] Strategy structure is complete")
    else:
        print(f"[WARN] Structure issues:")
        for issue in structure_issues:
            print(f"  - {issue}")
    
    return {
        'file': filename,
        'todos': todo_count,
        'syntax_ok': is_valid,
        'structure_issues': len(structure_issues)
    }

def check_all_files(directory="converted_strategies"):
    """检查所有策略文件"""
    directory = Path(directory)
    
    if not directory.exists():
        print(f"Directory not found: {directory}")
        return
    
    print("=" * 60)
    print("VNPy Strategy Files Quality Check")
    print("=" * 60)
    
    results = []
    
    for py_file in sorted(directory.glob("*.py")):
        try:
            result = check_file(str(py_file))
            results.append(result)
        except UnicodeEncodeError:
            # 跳过有编码问题的文件名
            filename = py_file.name.encode('ascii', 'ignore').decode('ascii')
            print(f"\nChecking file: {filename} (skipped due to encoding)")
            continue
    
    # 汇总
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    total_files = len(results)
    files_with_todos = sum(1 for r in results if r['todos'] > 0)
    files_with_errors = sum(1 for r in results if not r['syntax_ok'])
    files_with_issues = sum(1 for r in results if r['structure_issues'] > 0)
    
    print(f"Total files: {total_files}")
    print(f"Files with TODO comments: {files_with_todos}")
    print(f"Files with syntax errors: {files_with_errors}")
    print(f"Files with structure issues: {files_with_issues}")
    
    total_todos = sum(r['todos'] for r in results)
    print(f"Total TODO comments: {total_todos}")
    
    if total_todos == 0 and files_with_errors == 0:
        print("\n[SUCCESS] All files passed the check!")

if __name__ == "__main__":
    import sys
    directory = sys.argv[1] if len(sys.argv) > 1 else "converted_strategies"
    check_all_files(directory)
