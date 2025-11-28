#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VNPy代码规范检查工具
根据VNPy项目规范检查策略文件
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Tuple

class VNPyStyleChecker:
    """VNPy代码规范检查器"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        
    def check_file(self, file_path: str) -> Tuple[List[str], List[str]]:
        """检查单个文件的代码规范"""
        self.errors = []
        self.warnings = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            filename = os.path.basename(file_path)
            
            # 1. 检查文件名（应该是下划线模式）
            self._check_filename(filename)
            
            # 2. 检查类名（应该是驼峰式）
            self._check_class_name(content, filename)
            
            # 3. 检查变量命名（应该是小写加下划线）
            self._check_variable_naming(content, lines)
            
            # 4. 检查TODO注释
            self._check_todo_comments(content, lines)
            
            # 5. 检查导入语句
            self._check_imports(content)
            
            # 6. 检查策略结构
            self._check_strategy_structure(content)
            
            return self.errors, self.warnings
            
        except Exception as e:
            return [f"无法读取文件: {e}"], []
    
    def _check_filename(self, filename: str):
        """检查文件名是否符合规范（下划线模式）"""
        if not filename.endswith('.py'):
            return
        
        name = filename[:-3]  # 移除.py
        
        # 策略文件应该是小写字母和下划线
        if re.search(r'[A-Z]', name):
            self.warnings.append(f"文件名 '{filename}' 包含大写字母，建议使用下划线命名（如：my_strategy.py）")
        
        if re.search(r'[^a-z0-9_]', name):
            self.warnings.append(f"文件名 '{filename}' 包含特殊字符，建议只使用小写字母、数字和下划线")
    
    def _check_class_name(self, content: str, filename: str):
        """检查类名是否符合规范（驼峰式）"""
        # 查找类定义
        class_pattern = r'class\s+(\w+)\s*\([^)]*CtaTemplate[^)]*\)'
        matches = re.finditer(class_pattern, content, re.IGNORECASE)
        
        for match in matches:
            class_name = match.group(1)
            
            # 应该是驼峰式（首字母大写）
            if not class_name[0].isupper():
                self.errors.append(f"类名 '{class_name}' 首字母应该大写（驼峰式）")
            
            # 应该包含Strategy后缀
            if not class_name.endswith('Strategy'):
                self.warnings.append(f"类名 '{class_name}' 建议以'Strategy'结尾")
            
            # 不应该包含下划线
            if '_' in class_name:
                self.warnings.append(f"类名 '{class_name}' 不应该包含下划线，应该使用驼峰式（如：MyStrategy）")
    
    def _check_variable_naming(self, content: str, lines: List[str]):
        """检查变量命名是否符合规范（小写加下划线）"""
        # 检查实例变量（self.xxx）
        instance_var_pattern = r'self\.([a-zA-Z_][a-zA-Z0-9_]*)'
        
        for i, line in enumerate(lines, 1):
            # 跳过注释和字符串
            if line.strip().startswith('#') or '"""' in line or "'''" in line:
                continue
            
            matches = re.finditer(instance_var_pattern, line)
            for match in matches:
                var_name = match.group(1)
                
                # 实例变量应该是小写加下划线
                if var_name and var_name[0].isupper():
                    self.warnings.append(f"第{i}行: 变量 '{var_name}' 不应该以大写字母开头，建议使用小写加下划线（如：my_variable）")
                
                # 检查是否有连续大写字母（除了常量）
                if re.search(r'[A-Z]{2,}', var_name) and not var_name.isupper():
                    self.warnings.append(f"第{i}行: 变量 '{var_name}' 包含连续大写字母，建议使用下划线分隔（如：my_variable_name）")
    
    def _check_todo_comments(self, content: str, lines: List[str]):
        """检查TODO注释"""
        todo_pattern = r'#\s*TODO[^\n]*'
        
        todos = re.findall(todo_pattern, content, re.IGNORECASE)
        if todos:
            self.warnings.append(f"发现 {len(todos)} 个TODO注释，建议完成或移除")
            # 显示前5个TODO
            for i, todo in enumerate(todos[:5], 1):
                self.warnings.append(f"  TODO {i}: {todo.strip()}")
    
    def _check_imports(self, content: str):
        """检查导入语句"""
        # 检查是否导入了必要的VNPy模块
        required_imports = [
            'CtaTemplate',
            'BarData',
        ]
        
        missing_imports = []
        for imp in required_imports:
            if imp not in content:
                missing_imports.append(imp)
        
        if missing_imports and 'class' in content and 'CtaTemplate' in content:
            self.errors.append(f"缺少必要的导入: {', '.join(missing_imports)}")
    
    def _check_strategy_structure(self, content: str):
        """检查策略结构"""
        required_methods = [
            'on_init',
            'on_start',
            'on_stop',
            'on_bar',
        ]
        
        missing_methods = []
        for method in required_methods:
            pattern = rf'def\s+{method}\s*\('
            if not re.search(pattern, content, re.IGNORECASE):
                missing_methods.append(method)
        
        if missing_methods and 'class' in content:
            self.warnings.append(f"缺少建议的方法: {', '.join(missing_methods)}")

def check_strategy_files(directory: str = "converted_strategies"):
    """检查目录中所有策略文件"""
    directory = Path(directory)
    
    if not directory.exists():
        print(f"目录不存在: {directory}")
        return
    
    checker = VNPyStyleChecker()
    
    print("=== VNPy代码规范检查 ===\n")
    
    all_errors = []
    all_warnings = []
    
    for py_file in directory.glob("*.py"):
        print(f"检查文件: {py_file.name}")
        errors, warnings = checker.check_file(str(py_file))
        
        if errors:
            print(f"  [ERROR] 发现 {len(errors)} 个错误:")
            for error in errors:
                print(f"    - {error}")
            all_errors.extend([(py_file.name, e) for e in errors])
        
        if warnings:
            print(f"  [WARN] 发现 {len(warnings)} 个警告:")
            for warning in warnings[:5]:  # 只显示前5个警告
                print(f"    - {warning}")
            if len(warnings) > 5:
                print(f"    ... 还有 {len(warnings) - 5} 个警告")
            all_warnings.extend([(py_file.name, w) for w in warnings])
        
        if not errors and not warnings:
            print(f"  [OK] 通过检查")
        
        print()
    
    print("=" * 60)
    print(f"检查完成:")
    print(f"  总错误数: {len(all_errors)}")
    print(f"  总警告数: {len(all_warnings)}")
    
    if all_errors:
        print(f"\n需要修复的错误:")
        for filename, error in all_errors:
            print(f"  {filename}: {error}")
    
    return len(all_errors), len(all_warnings)

def print_style_guide():
    """打印VNPy代码规范指南"""
    guide = """
=== VNPy代码规范指南 ===

1. 命名规则
   - 类名：驼峰式（CamelCase），如 MyStrategy
   - 变量名：小写加下划线（snake_case），如 my_variable
   - 文件名：小写加下划线，如 my_strategy.py
   - 常量：大写加下划线，如 MAX_SIZE

2. 策略文件结构
   - 继承自 CtaTemplate
   - 必须实现 on_init(), on_start(), on_stop(), on_bar() 方法
   - 定义 parameters 和 variables 列表

3. 导入规范
   - 使用 vnpy_ctastrategy 模块
   - 导入必要的类型（BarData, TickData, OrderData等）

4. 代码质量
   - 移除所有 TODO 注释
   - 添加必要的文档字符串
   - 使用类型注解（推荐）

5. 策略参数和变量
   - parameters: 策略参数列表（可配置）
   - variables: 策略变量列表（运行时状态）

示例：
```python
from vnpy_ctastrategy import CtaTemplate, StopOrder
from vnpy.trader.object import BarData

class MyStrategy(CtaTemplate):
    author = "您的名字"
    
    parameters = ["param1", "param2"]
    variables = ["var1", "var2"]
    
    def on_init(self):
        self.write_log("策略初始化")
    
    def on_bar(self, bar: BarData):
        # 策略逻辑
        pass
```
"""
    print(guide)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--guide":
        print_style_guide()
    else:
        directory = sys.argv[1] if len(sys.argv) > 1 else "converted_strategies"
        check_strategy_files(directory)
