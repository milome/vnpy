#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 #IMPORT 跨周期引用功能
"""

from mflang.import_parser import ImportParser, ImportStatement, PeriodType
from mflang.model_loader import load_model, get_variable


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


def test_model_file_loading():
    """测试模型文件加载"""
    print("=" * 50)
    print("测试7: 模型文件加载")
    print("=" * 50)
    
    # 测试加载AA模型
    try:
        model = load_model("AA")
        print(f"模型AA加载成功:")
        for var_name, var_expr in model.items():
            print(f"  {var_name}: {var_expr}")
        print()
    except Exception as e:
        print(f"加载AA模型失败: {e}")
        print()
    
    # 测试加载CC模型
    try:
        model = load_model("CC")
        print(f"模型CC加载成功:")
        for var_name, var_expr in model.items():
            print(f"  {var_name}: {var_expr}")
        print()
    except Exception as e:
        print(f"加载CC模型失败: {e}")
        print()
    
    # 测试获取变量
    cc_expr = get_variable("AA", "CC")
    if cc_expr:
        print(f"AA模型中的CC变量: {cc_expr}")
    else:
        print("未找到AA模型中的CC变量")
    print()


def test_import_with_model():
    """测试#IMPORT与模型文件的结合使用"""
    print("=" * 50)
    print("测试8: #IMPORT与模型文件的结合使用")
    print("=" * 50)
    
    # 解析#IMPORT语句
    code = """
#IMPORT[DAY,1,AA] AS VAR
CC:VAR.CC;
"""
    statements = ImportParser.parse_code(code)
    
    for stmt in statements:
        print(f"解析#IMPORT语句: {stmt}")
        print(f"  周期: {stmt.period.value}, N: {stmt.n}")
        print(f"  模型文件: {stmt.formula} (对应 mflang/mmodels/{stmt.formula})")
        print(f"  变量名: {stmt.var_name} (用于访问模型中的变量)")
        
        # 加载模型文件
        try:
            model = load_model(stmt.formula)
            print(f"  模型文件中的变量:")
            for var_name, var_expr in model.items():
                print(f"    {var_name}: {var_expr}")
            
            # 检查VAR.CC中的CC是否在模型中定义
            if "CC" in model:
                print(f"  [OK] 变量CC在模型{stmt.formula}中已定义")
            else:
                print(f"  [警告] 变量CC在模型{stmt.formula}中未定义")
        except Exception as e:
            print(f"  [错误] 无法加载模型文件: {e}")
        print()


def test_model_file_not_exists():
    """测试模型文件不存在的情况"""
    print("=" * 50)
    print("测试9: 模型文件不存在")
    print("=" * 50)
    
    # 测试用例1: 解析#IMPORT语句，但模型文件不存在
    code = """
#IMPORT[DAY,1,NONEXISTENT] AS VAR
CC:VAR.CC;
"""
    statements = ImportParser.parse_code(code)
    
    for stmt in statements:
        print(f"解析#IMPORT语句: {stmt}")
        print(f"  模型文件: {stmt.formula} (对应 mflang/mmodels/{stmt.formula})")
        
        # 尝试加载不存在的模型文件
        try:
            model = load_model(stmt.formula)
            print(f"  [错误] 不应该成功加载不存在的模型文件")
        except FileNotFoundError as e:
            print(f"  [OK] 正确捕获错误: 模型文件不存在 - {e}")
        except Exception as e:
            print(f"  [OK] 捕获到其他错误: {e}")
        print()
    
    # 测试用例2: 使用get_variable获取不存在的模型文件中的变量
    print("测试用例2: 使用get_variable获取不存在的模型文件中的变量")
    try:
        var_expr = get_variable("NONEXISTENT", "CC")
        if var_expr is None:
            print(f"  [OK] 正确返回None（模型文件不存在）")
        else:
            print(f"  [错误] 不应该返回变量表达式")
    except Exception as e:
        print(f"  [OK] 捕获到异常: {e}")
    print()


def test_variable_not_in_model():
    """测试模型文件存在，但引用的变量未在模型文件中定义"""
    print("=" * 50)
    print("测试10: 模型文件存在，但引用的变量未定义")
    print("=" * 50)
    
    # 测试用例1: 模型文件AA存在，但尝试访问不存在的变量
    code = """
#IMPORT[DAY,1,AA] AS VAR
NONEXISTENT_VAR:VAR.NONEXISTENT_VAR;
"""
    statements = ImportParser.parse_code(code)
    
    for stmt in statements:
        print(f"解析#IMPORT语句: {stmt}")
        print(f"  模型文件: {stmt.formula} (对应 mflang/mmodels/{stmt.formula})")
        print(f"  尝试访问变量: NONEXISTENT_VAR")
        
        # 加载模型文件
        try:
            model = load_model(stmt.formula)
            print(f"  模型文件加载成功，包含变量: {list(model.keys())}")
            
            # 检查变量是否存在
            if "NONEXISTENT_VAR" in model:
                print(f"  [错误] 不应该找到NONEXISTENT_VAR变量")
            else:
                print(f"  [OK] 变量NONEXISTENT_VAR在模型{stmt.formula}中未定义（符合预期）")
            
            # 使用get_variable获取不存在的变量
            var_expr = get_variable(stmt.formula, "NONEXISTENT_VAR")
            if var_expr is None:
                print(f"  [OK] get_variable正确返回None（变量不存在）")
            else:
                print(f"  [错误] get_variable不应该返回变量表达式")
        except Exception as e:
            print(f"  [错误] 无法加载模型文件: {e}")
        print()
    
    # 测试用例2: 模型文件CC存在，但尝试访问不存在的变量
    code2 = """
#IMPORT[DAY,1,CC] AS VAR
UNKNOWN_VAR:VAR.UNKNOWN_VAR;
"""
    statements2 = ImportParser.parse_code(code2)
    
    for stmt in statements2:
        print(f"解析#IMPORT语句: {stmt}")
        print(f"  模型文件: {stmt.formula} (对应 mflang/mmodels/{stmt.formula})")
        print(f"  尝试访问变量: UNKNOWN_VAR")
        
        try:
            model = load_model(stmt.formula)
            print(f"  模型文件加载成功，包含变量: {list(model.keys())}")
            
            if "UNKNOWN_VAR" in model:
                print(f"  [错误] 不应该找到UNKNOWN_VAR变量")
            else:
                print(f"  [OK] 变量UNKNOWN_VAR在模型{stmt.formula}中未定义（符合预期）")
        except Exception as e:
            print(f"  [错误] 无法加载模型文件: {e}")
        print()
    
    # 测试用例3: 模型文件MIN5_OPEN存在，但尝试访问不存在的变量
    code3 = """
#IMPORT[MIN,5,MIN5_OPEN] AS MIN5
UNKNOWN:MIN5.UNKNOWN;
"""
    statements3 = ImportParser.parse_code(code3)
    
    for stmt in statements3:
        print(f"解析#IMPORT语句: {stmt}")
        print(f"  模型文件: {stmt.formula} (对应 mflang/mmodels/{stmt.formula})")
        print(f"  尝试访问变量: UNKNOWN")
        
        try:
            model = load_model(stmt.formula)
            print(f"  模型文件加载成功，包含变量: {list(model.keys())}")
            
            if "UNKNOWN" in model:
                print(f"  [错误] 不应该找到UNKNOWN变量")
            else:
                print(f"  [OK] 变量UNKNOWN在模型{stmt.formula}中未定义（符合预期）")
        except Exception as e:
            print(f"  [错误] 无法加载模型文件: {e}")
        print()


if __name__ == "__main__":
    test_parse_import_statement()
    test_parse_code()
    test_week_quarter_n_handling()
    test_validation()
    test_example_cases()
    test_max_imports()
    test_model_file_loading()
    test_import_with_model()
    test_model_file_not_exists()
    test_variable_not_in_model()
    
    print("=" * 50)
    print("所有测试完成！")
    print("=" * 50)

