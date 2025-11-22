#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 #IMPORT 跨周期引用功能
"""

from mflang.import_parser import ImportParser, ImportStatement, PeriodType


def test_parse_import_statement():
    """测试解析单个 #IMPORT 语句"""
    print("=" * 50)
    print("测试1: 解析单个 #IMPORT 语句")
    print("=" * 50)
    
    # 测试用例1: 基本格式
    line1 = "#IMPORT[DAY,1,AA] AS VAR"
    stmt1 = ImportParser.parse_import_statement(line1)
    print(f"输入: {line1}")
    print(f"解析结果: {stmt1}")
    print(f"周期: {stmt1.period.value}, N: {stmt1.n}, 指标: {stmt1.formula}, 变量: {stmt1.var_name}")
    print()
    
    # 测试用例2: 分钟周期
    line2 = "#IMPORT[MIN,2,MACD] AS VAR"
    stmt2 = ImportParser.parse_import_statement(line2)
    print(f"输入: {line2}")
    print(f"解析结果: {stmt2}")
    print()
    
    # 测试用例3: 自定义小时周期
    line3 = "#IMPORT[CUSHOUR,6,AA]AS S"
    stmt3 = ImportParser.parse_import_statement(line3)
    print(f"输入: {line3}")
    print(f"解析结果: {stmt3}")
    print()
    
    # 测试用例4: 带分号（应该被移除）
    line4 = "#IMPORT[DAY,1,CC] AS VAR;"
    stmt4 = ImportParser.parse_import_statement(line4)
    print(f"输入: {line4}")
    print(f"解析结果: {stmt4}")
    print()


def test_parse_code():
    """测试解析完整代码"""
    print("=" * 50)
    print("测试2: 解析完整代码")
    print("=" * 50)
    
    code = """
CC:REF(C,1);
保存指标，命名为AA

#IMPORT[DAY,1,AA] AS VAR
CC:VAR.CC;
"""
    
    statements = ImportParser.parse_code(code)
    print(f"代码:\n{code}")
    print(f"找到 {len(statements)} 个 #IMPORT 语句:")
    for stmt in statements:
        print(f"  - {stmt}")
    print()


def test_week_quarter_n_handling():
    """测试周、季周期的N参数处理"""
    print("=" * 50)
    print("测试3: 周、季周期的N参数处理")
    print("=" * 50)
    
    # 周周期，N>1应该按1计算
    line1 = "#IMPORT[WEEK,2,FORMULA] AS VAR"
    stmt1 = ImportParser.parse_import_statement(line1)
    print(f"输入: {line1}")
    print(f"解析结果: N={stmt1.n} (应该是1，因为WEEK周期N>1按1计算)")
    print()
    
    # 季周期，N>1应该按1计算
    line2 = "#IMPORT[QUARTER,5,FORMULA] AS VAR"
    stmt2 = ImportParser.parse_import_statement(line2)
    print(f"输入: {line2}")
    print(f"解析结果: N={stmt2.n} (应该是1，因为QUARTER周期N>1按1计算)")
    print()


def test_validation():
    """测试验证功能"""
    print("=" * 50)
    print("测试4: 验证功能")
    print("=" * 50)
    
    # 测试无效的周期类型
    try:
        line = "#IMPORT[INVALID,1,AA] AS VAR"
        ImportParser.parse_import_statement(line)
        print("错误: 应该抛出异常")
    except ValueError as e:
        print(f"[OK] 正确捕获错误: {e}")
    print()
    
    # 测试N<1
    try:
        line = "#IMPORT[DAY,0,AA] AS VAR"
        ImportParser.parse_import_statement(line)
        print("错误: 应该抛出异常")
    except ValueError as e:
        print(f"[OK] 正确捕获错误: {e}")
    print()
    
    # 测试变量名以数字开头
    try:
        line = "#IMPORT[DAY,1,AA] AS 1VAR"
        ImportParser.parse_import_statement(line)
        print("错误: 应该抛出异常")
    except ValueError as e:
        print(f"[OK] 正确捕获错误: {e}")
    print()
    
    # 测试变量名与函数名重复
    try:
        line = "#IMPORT[DAY,1,AA] AS REF"
        ImportParser.parse_import_statement(line)
        print("错误: 应该抛出异常")
    except ValueError as e:
        print(f"[OK] 正确捕获错误: {e}")
    print()


def test_example_cases():
    """测试示例用例"""
    print("=" * 50)
    print("测试5: 示例用例")
    print("=" * 50)
    
    # 示例1
    code1 = """
CC:REF(C,1);
保存指标，命名为AA

#IMPORT[DAY,1,AA] AS VAR
CC:VAR.CC;
"""
    print("示例1:")
    print(code1)
    statements1 = ImportParser.parse_code(code1)
    for stmt in statements1:
        print(f"  {stmt}")
    print()
    
    # 示例2
    code2 = """
CC:C;
保存指标，命名为CC

#IMPORT[DAY,1,CC] AS VAR
CC:=VAR.CC;
"""
    print("示例2:")
    print(code2)
    statements2 = ImportParser.parse_code(code2)
    for stmt in statements2:
        print(f"  {stmt}")
    print()
    
    # 示例3
    code3 = """
CC:=REF(C,1);
保存指标，命名为AA

#IMPORT[CUSHOUR,6,AA]AS S
CC1:=S.CC;

#IMPORT[MIN,1,AA]AS R
CC2:=R.CC;
"""
    print("示例3:")
    print(code3)
    statements3 = ImportParser.parse_code(code3)
    for stmt in statements3:
        print(f"  {stmt}")
    print()


def test_max_imports():
    """测试最大导入数量限制"""
    print("=" * 50)
    print("测试6: 最大导入数量限制")
    print("=" * 50)
    
    # 创建7个 #IMPORT 语句（超过6个限制）
    code = "\n".join([f"#IMPORT[DAY,1,AA{i}] AS VAR{i}" for i in range(7)])
    
    try:
        ImportParser.parse_code(code)
        print("错误: 应该抛出异常")
    except ValueError as e:
        print(f"[OK] 正确捕获错误: {e}")
    print()


if __name__ == "__main__":
    test_parse_import_statement()
    test_parse_code()
    test_week_quarter_n_handling()
    test_validation()
    test_example_cases()
    test_max_imports()
    
    print("=" * 50)
    print("所有测试完成！")
    print("=" * 50)

