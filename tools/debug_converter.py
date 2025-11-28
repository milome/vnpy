#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试版本的XTRD转换器
用于诊断解析问题
"""

import re
import os
from batch_xtrd_converter import BatchXTRDConverter, XTRDParser
import logging

# 设置详细日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DebugXTRDParser(XTRDParser):
    """调试版本的XTRD解析器"""
    
    def parse_xtrd_content(self, content: str, filename: str) -> None:
        """调试解析XTRD文件内容"""
        print(f"\n{'='*60}")
        print(f"调试解析文件: {filename}")
        print(f"{'='*60}")
        
        # 显示文件基本信息
        print(f"文件大小: {len(content)} 字符")
        print(f"前500字符预览:")
        print("-" * 40)
        print(content[:500])
        print("-" * 40)
        
        # 检查XML标签
        print(f"\n检查XML标签:")
        xml_tags = ['PARAMDEFAULTSET', 'CODE', 'VERSION', 'EDITTIME', 'AUTHOR', 'PROPERTY']
        
        for tag in xml_tags:
            pattern = f'<{tag}>(.*?)</{tag}>'
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                tag_content = match.group(1).strip()
                print(f"  ✓ {tag}: {len(tag_content)} 字符")
                if tag == 'CODE':
                    print(f"    代码预览: {tag_content[:200]}...")
            else:
                print(f"  ✗ {tag}: 未找到")
        
        # 提取CODE部分进行详细分析
        code_match = re.search(r'<CODE>(.*?)</CODE>', content, re.DOTALL | re.IGNORECASE)
        if code_match:
            code = code_match.group(1).strip()
            print(f"\n分析CODE部分 ({len(code)} 字符):")
            
            # 检查导入语句
            print(f"\n检查 #IMPORT 语句:")
            import_pattern = re.compile(r'#IMPORT\s*\[([^,]+),\s*(\d+),\s*([^\]]+)\]\s*AS\s*(\w+)', re.IGNORECASE)
            imports = import_pattern.findall(code)
            
            if imports:
                for i, (period_type, period_num, model_name, alias) in enumerate(imports, 1):
                    print(f"  {i}. {period_type}, {period_num}, {model_name} AS {alias}")
            else:
                print("  未找到 #IMPORT 语句")
                # 尝试查找可能的导入模式
                possible_imports = re.findall(r'#IMPORT[^\n]*', code, re.IGNORECASE)
                if possible_imports:
                    print("  可能的导入语句:")
                    for imp in possible_imports:
                        print(f"    {imp}")
            
            # 检查变量定义
            print(f"\n检查 VARIABLE 定义:")
            variable_pattern = re.compile(r'VARIABLE\s*:\s*(\w+)\s*:=\s*([^;]+);', re.IGNORECASE | re.MULTILINE)
            variables = variable_pattern.findall(code)
            
            if variables:
                for i, (var_name, var_expr) in enumerate(variables[:10], 1):  # 只显示前10个
                    print(f"  {i}. {var_name} := {var_expr[:50]}...")
                if len(variables) > 10:
                    print(f"  ... 还有 {len(variables) - 10} 个变量")
            else:
                print("  未找到 VARIABLE 定义")
                # 尝试其他变量模式
                alt_vars = re.findall(r'(\w+)\s*:=\s*([^;\n]+)', code, re.IGNORECASE)
                if alt_vars:
                    print("  可能的变量赋值:")
                    for var_name, var_expr in alt_vars[:5]:
                        if not var_name.upper() in ['IF', 'THEN', 'BEGIN', 'END', 'ELSE']:
                            print(f"    {var_name} := {var_expr[:50]}...")
            
            # 检查函数调用
            print(f"\n检查函数调用:")
            functions = ['MA', 'EMA', 'MACD', 'ATR', 'HHV', 'LLV', 'REF', 'BARSLAST', 'COUNT']
            for func in functions:
                pattern = f'{func}\\s*\\([^)]*\\)'
                matches = re.findall(pattern, code, re.IGNORECASE)
                if matches:
                    print(f"  {func}: {len(matches)} 次调用")
                    if len(matches) <= 3:
                        for match in matches:
                            print(f"    {match}")
                    else:
                        print(f"    示例: {matches[0]}, {matches[1]}, ...")
            
            # 检查条件语句
            print(f"\n检查条件语句:")
            if_pattern = re.compile(r'IF\s+(.+?)\s+THEN\s+BEGIN(.*?)END', re.IGNORECASE | re.DOTALL)
            if_statements = if_pattern.findall(code)
            if if_statements:
                print(f"  找到 {len(if_statements)} 个 IF-THEN-BEGIN-END 结构")
                for i, (condition, body) in enumerate(if_statements[:3], 1):
                    print(f"    {i}. IF {condition[:50]}... THEN BEGIN ... END")
            else:
                print("  未找到 IF-THEN-BEGIN-END 结构")
            
            # 检查绘图函数
            print(f"\n检查绘图函数:")
            draw_functions = ['DRAWLINE3', 'DRAWTEXT', 'DRAWCOLORKLINE']
            for func in draw_functions:
                pattern = f'{func}\\s*\\([^)]*\\)'
                matches = re.findall(pattern, code, re.IGNORECASE)
                if matches:
                    print(f"  {func}: {len(matches)} 次调用")
        
        else:
            print("\n❌ 未找到 <CODE> 标签!")
        
        print(f"\n{'='*60}")

def debug_single_file(file_path: str):
    """调试单个文件"""
    parser = DebugXTRDParser()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        try:
            with open(file_path, 'r', encoding='gbk') as f:
                content = f.read()
        except:
            print(f"无法读取文件: {file_path}")
            return
    
    parser.parse_xtrd_content(content, os.path.basename(file_path))

def debug_zip_file(zip_path: str):
    """调试ZIP文件"""
    converter = BatchXTRDConverter()
    
    # 提取文件
    xtrd_files = converter._extract_xtrd_files(zip_path)
    
    print(f"ZIP文件包含 {len(xtrd_files)} 个XTRD文件:")
    for filename in xtrd_files.keys():
        print(f"  - {filename}")
    
    # 逐个调试
    parser = DebugXTRDParser()
    for filename, content in xtrd_files.items():
        parser.parse_xtrd_content(content, filename)

if __name__ == "__main__":
    print("=== XTRD文件调试工具 ===")
    print("1. 调试单个XTRD文件")
    print("2. 调试ZIP文件")
    print("3. 退出")
    
    choice = input("请选择 (1-3): ").strip()
    
    if choice == '1':
        file_path = input("请输入XTRD文件路径: ").strip()
        if os.path.exists(file_path):
            debug_single_file(file_path)
        else:
            print("文件不存在!")
    
    elif choice == '2':
        zip_path = input("请输入ZIP文件路径: ").strip()
        if os.path.exists(zip_path):
            debug_zip_file(zip_path)
        else:
            print("文件不存在!")
    
    elif choice == '3':
        print("退出")
    
    else:
        print("无效选择!")

