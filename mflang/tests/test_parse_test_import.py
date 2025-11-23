#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试解析 TEST_IMPORT 模型文件
该文件包含 #IMPORT 语句和使用了跨周期引用变量的定义
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from mflang.import_parser import ImportParser, ImportStatement
from mflang.model_loader import ModelLoader, load_model, get_variable
from mflang import REF
import numpy as np
import pandas as pd


def test_parse_test_import_file():
    """测试解析 TEST_IMPORT 模型文件"""
    print("=" * 60)
    print("测试解析 TEST_IMPORT 模型文件")
    print("=" * 60)
    print()
    
    # 步骤1: 读取文件内容
    print("步骤1: 读取 TEST_IMPORT 文件内容")
    print("-" * 60)
    test_import_file = Path(__file__).parent / "mmodels" / "TEST_IMPORT"
    
    try:
        with open(test_import_file, 'r', encoding='utf-8') as f:
            file_content = f.read()
        print("文件内容:")
        print(file_content)
        print()
    except Exception as e:
        print(f"读取文件失败: {e}")
        return
    
    # 步骤2: 解析文件中的 #IMPORT 语句
    print("步骤2: 解析文件中的 #IMPORT 语句")
    print("-" * 60)
    
    import_statements = ImportParser.parse_code(file_content)
    print(f"找到 {len(import_statements)} 个 #IMPORT 语句:")
    
    for i, stmt in enumerate(import_statements, 1):
        print(f"\n  {i}. {stmt}")
        print(f"     周期: {stmt.period.value}, N: {stmt.n}")
        print(f"     模型文件: {stmt.formula} (对应 mflang/mmodels/{stmt.formula})")
        print(f"     变量名: {stmt.var_name}")
        
        # 验证被引用的模型文件是否存在
        try:
            referenced_model = load_model(stmt.formula)
            print(f"     被引用的模型文件 {stmt.formula} 加载成功")
            print(f"     包含变量: {list(referenced_model.keys())}")
        except Exception as e:
            print(f"     警告: 无法加载被引用的模型文件 {stmt.formula}: {e}")
    print()
    
    # 步骤3: 解析文件中的变量定义（排除 #IMPORT 语句）
    print("步骤3: 解析文件中的变量定义")
    print("-" * 60)
    
    # 使用 ModelLoader 加载模型文件（会自动处理 #IMPORT 语句）
    try:
        loader = ModelLoader()
        model = loader.load_model("TEST_IMPORT")
        
        print(f"模型 TEST_IMPORT 加载成功，包含 {len(model)} 个变量:")
        for var_name, var_expr in model.items():
            print(f"  {var_name}: {var_expr}")
        print()
        
        # 检查变量定义中是否使用了跨周期引用
        print("检查变量定义中的跨周期引用:")
        for var_name, var_expr in model.items():
            # 使用正则表达式匹配 VAR.VARIABLE_NAME 格式的引用
            import re
            # 匹配模式: 变量名.变量名（如 MIN5.PREV_OPEN）
            pattern = r'([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)'
            matches = re.finditer(pattern, var_expr)
            
            found_refs = []
            for match in matches:
                var_ref = match.group(1)  # 如 MIN5
                var_field = match.group(2)  # 如 PREV_OPEN
                found_refs.append((var_ref, var_field))
            
            if found_refs:
                print(f"  {var_name}: 使用了跨周期引用")
                for var_ref, var_field in found_refs:
                    print(f"    -> {var_ref}.{var_field}")
                    
                    # 检查引用的变量是否在 #IMPORT 语句中定义
                    found_import = False
                    for stmt in import_statements:
                        if stmt.var_name == var_ref:
                            found_import = True
                            print(f"      -> 引用来自 #IMPORT[{stmt.period.value},{stmt.n},{stmt.formula}] AS {stmt.var_name}")
                            
                            # 检查被引用的模型文件中是否定义了该变量
                            try:
                                referenced_model = load_model(stmt.formula)
                                if var_field in referenced_model:
                                    print(f"      -> [OK] 变量 {var_field} 在被引用的模型 {stmt.formula} 中已定义: {referenced_model[var_field]}")
                                else:
                                    print(f"      -> [警告] 变量 {var_field} 在被引用的模型 {stmt.formula} 中未定义")
                                    print(f"         可用变量: {list(referenced_model.keys())}")
                            except Exception as e:
                                print(f"      -> [错误] 无法加载被引用的模型: {e}")
                            break
                    
                    if not found_import:
                        print(f"      -> [警告] 变量 {var_ref} 未在 #IMPORT 语句中定义")
                        print(f"         可用的 #IMPORT 变量: {[stmt.var_name for stmt in import_statements]}")
            else:
                print(f"  {var_name}: 未使用跨周期引用")
        print()
        
    except Exception as e:
        print(f"加载模型文件失败: {e}")
        import traceback
        traceback.print_exc()
        print()
    
    # 步骤4: 验证完整的解析流程
    print("步骤4: 验证完整的解析流程")
    print("-" * 60)
    
    # 4.1 验证 #IMPORT 语句
    if len(import_statements) > 0:
        stmt = import_statements[0]
        print(f"[OK] #IMPORT 语句解析成功:")
        print(f"     {stmt}")
        
        # 4.2 验证被引用的模型文件
        try:
            referenced_model = load_model(stmt.formula)
            print(f"[OK] 被引用的模型文件 {stmt.formula} 存在")
            print(f"     包含变量: {list(referenced_model.keys())}")
        except Exception as e:
            print(f"[错误] 被引用的模型文件 {stmt.formula} 不存在: {e}")
        
        # 4.3 验证模型文件中的变量定义
        try:
            model = load_model("TEST_IMPORT")
            print(f"[OK] TEST_IMPORT 模型文件解析成功")
            print(f"     包含变量: {list(model.keys())}")
            
            # 4.4 验证跨周期引用的变量是否存在
            for var_name, var_expr in model.items():
                if 'MIN5.PREV_OPEN' in var_expr:
                    print(f"[OK] 变量 {var_name} 使用了跨周期引用 MIN5.PREV_OPEN")
                    
                    # 检查 MIN5 是否在 #IMPORT 语句中定义
                    min5_stmt = None
                    for stmt in import_statements:
                        if stmt.var_name == "MIN5":
                            min5_stmt = stmt
                            break
                    
                    if min5_stmt:
                        print(f"[OK] MIN5 在 #IMPORT 语句中已定义")
                        
                        # 检查 PREV_OPEN 是否在被引用的模型中定义
                        try:
                            min5_model = load_model(min5_stmt.formula)
                            if "PREV_OPEN" in min5_model:
                                print(f"[OK] PREV_OPEN 在被引用的模型 {min5_stmt.formula} 中已定义")
                            else:
                                print(f"[警告] PREV_OPEN 在被引用的模型 {min5_stmt.formula} 中未定义")
                        except Exception as e:
                            print(f"[错误] 无法加载被引用的模型: {e}")
        except Exception as e:
            print(f"[错误] 无法加载 TEST_IMPORT 模型文件: {e}")
    
    print()
    
    # 步骤5: 计算被引用模型文件中的变量
    print("步骤5: 计算被引用模型文件中的变量")
    print("-" * 60)
    
    print("说明: 加载完被引用的模型文件后，需要解析变量定义并计算变量值")
    print("      这样在被引用时（如 MIN5.PREV_OPEN）才能使用实际的计算结果")
    print()
    
    try:
        # 解析 #IMPORT
        import_statements = ImportParser.parse_code(file_content)
        
        if len(import_statements) == 0:
            print("[错误] 未找到 #IMPORT 语句")
            return
        
        stmt = import_statements[0]
        print(f"处理 #IMPORT 语句: {stmt}")
        print(f"  被引用的模型文件: {stmt.formula}")
        print()
        
        # 加载被引用的模型文件
        referenced_model = load_model(stmt.formula)
        print(f"[OK] 步骤1: 加载被引用模型 {stmt.formula}")
        print(f"     包含变量定义: {referenced_model}")
        print()
        
        # 步骤5.1: 准备K线数据（模拟5分钟周期的数据）
        print("步骤5.1: 准备5分钟周期的K线数据")
        dates_5min = pd.date_range(start='2024-01-01 09:00', periods=20, freq='5min')
        # 模拟小恒指期货主连MHImain的5分钟K线数据
        np.random.seed(42)  # 固定随机种子以便结果可复现
        df_5min = pd.DataFrame({
            'datetime': dates_5min,
            'open': 20000 + np.random.randn(20).cumsum() * 10,
            'high': 20000 + np.random.randn(20).cumsum() * 10 + 20,
            'low': 20000 + np.random.randn(20).cumsum() * 10 - 20,
            'close': 20000 + np.random.randn(20).cumsum() * 10,
            'volume': np.random.randint(1000, 10000, 20)
        })
        print(f"     生成了 {len(df_5min)} 根5分钟K线数据")
        print(f"     时间范围: {df_5min['datetime'].iloc[0]} 到 {df_5min['datetime'].iloc[-1]}")
        print(f"     开盘价范围: {df_5min['open'].min():.2f} - {df_5min['open'].max():.2f}")
        print()
        
        # 步骤5.2: 计算被引用模型中的变量
        print("步骤5.2: 计算被引用模型中的变量")
        referenced_variables = {}
        
        for var_name, var_expr in referenced_model.items():
            print(f"  计算变量: {var_name} = {var_expr}")
            
            # 解析并执行变量表达式
            # 这里需要根据表达式类型执行相应的计算
            # 示例：处理 REF(O,1) 表达式
            import re
            
            # 处理 REF(O,1) 或 REF(C,1) 等表达式
            ref_match = re.search(r'REF\s*\(\s*(\w+)\s*,\s*(\d+)\s*\)', var_expr)
            if ref_match:
                data_key = ref_match.group(1).upper()  # O, C, H, L等
                n_periods = int(ref_match.group(2))
                
                # 映射数据键
                data_mapping = {
                    'O': 'open',
                    'C': 'close',
                    'H': 'high',
                    'L': 'low',
                    'V': 'volume'
                }
                
                if data_key in data_mapping:
                    actual_key = data_mapping[data_key]
                    if actual_key in df_5min.columns:
                        data_array = df_5min[actual_key].values
                        result = REF(data_array, n_periods)
                        referenced_variables[var_name] = result
                        print(f"    -> 使用 {actual_key} 数据，计算 REF({actual_key}, {n_periods})")
                        print(f"    -> 结果数组长度: {len(result)}")
                        print(f"    -> 最后一个值（当前值）: {result[-1]:.2f}" if not np.isnan(result[-1]) else "    -> 最后一个值（当前值）: NaN")
                    else:
                        print(f"    -> [错误] 数据列 {actual_key} 不存在")
                else:
                    print(f"    -> [错误] 不支持的数据键: {data_key}")
            else:
                # 处理其他类型的表达式（如简单的 C, O 等）
                simple_match = re.match(r'^([COHLV])$', var_expr.strip())
                if simple_match:
                    data_key = simple_match.group(1)
                    data_mapping = {
                        'C': 'close',
                        'O': 'open',
                        'H': 'high',
                        'L': 'low',
                        'V': 'volume'
                    }
                    if data_key in data_mapping:
                        actual_key = data_mapping[data_key]
                        if actual_key in df_5min.columns:
                            result = df_5min[actual_key].values
                            referenced_variables[var_name] = result
                            print(f"    -> 使用 {actual_key} 数据")
                            print(f"    -> 结果数组长度: {len(result)}")
                            print(f"    -> 最后一个值（当前值）: {result[-1]:.2f}")
                else:
                    print(f"    -> [警告] 暂不支持该表达式类型: {var_expr}")
            print()
        
        print(f"[OK] 步骤5.2完成: 计算了 {len(referenced_variables)} 个变量")
        print(f"     已计算的变量: {list(referenced_variables.keys())}")
        print()
        
        # 步骤5.3: 使用计算后的变量值
        print("步骤5.3: 使用计算后的变量值")
        print("说明: 现在可以在 TEST_IMPORT 模型中使用 MIN5.PREV_OPEN 的实际值")
        print()
        
        # 加载当前模型
        current_model = load_model("TEST_IMPORT")
        print(f"[OK] 步骤5.3.1: 加载当前模型 TEST_IMPORT")
        print(f"     包含变量: {list(current_model.keys())}")
        print()
        
        # 计算当前模型中的变量（使用计算后的跨周期引用值）
        print("步骤5.3.2: 计算当前模型中的变量（使用跨周期引用值）")
        
        # 准备1分钟周期的数据（用于计算 TEST_IMPORT 中的变量）
        dates_1min = pd.date_range(start='2024-01-01 09:00', periods=100, freq='1min')
        np.random.seed(42)
        df_1min = pd.DataFrame({
            'datetime': dates_1min,
            'open': 20000 + np.random.randn(100).cumsum() * 10,
            'high': 20000 + np.random.randn(100).cumsum() * 10 + 20,
            'low': 20000 + np.random.randn(100).cumsum() * 10 - 20,
            'close': 20000 + np.random.randn(100).cumsum() * 10,
            'volume': np.random.randint(1000, 10000, 100)
        })
        print(f"     生成了 {len(df_1min)} 根1分钟K线数据")
        print()
        
        # 计算 TEST_IMPORT 中的变量
        current_variables = {}
        
        for var_name, var_expr in current_model.items():
            print(f"  计算变量: {var_name} = {var_expr}")
            
            # 检查是否使用了跨周期引用
            import re
            pattern = r'([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)'
            matches = list(re.finditer(pattern, var_expr))
            
            if matches:
                # 有跨周期引用，需要替换为实际值
                print(f"    -> 检测到跨周期引用")
                
                # 简化处理：对于 ISBUYTREND: C > MIN5.PREV_OPEN
                # 需要将 MIN5.PREV_OPEN 替换为实际计算的值
                for match in matches:
                    var_ref = match.group(1)  # MIN5
                    var_field = match.group(2)  # PREV_OPEN
                    
                    # 检查是否在 #IMPORT 语句中定义
                    for stmt in import_statements:
                        if stmt.var_name == var_ref:
                            # 获取被引用变量的值
                            if var_field in referenced_variables:
                                ref_value = referenced_variables[var_field]
                                print(f"    -> 找到跨周期引用: {var_ref}.{var_field}")
                                print(f"    -> 值数组长度: {len(ref_value)}")
                                
                                # 简化处理：将跨周期值对齐到1分钟周期
                                # 实际实现中需要更复杂的数据对齐逻辑
                                # 这里简化：使用最后一个值
                                if len(ref_value) > 0 and not np.isnan(ref_value[-1]):
                                    ref_current_value = ref_value[-1]
                                    print(f"    -> 当前值: {ref_current_value:.2f}")
                                    
                                    # 计算表达式（简化版：只处理 C > MIN5.PREV_OPEN）
                                    if 'C >' in var_expr or 'C>' in var_expr:
                                        current_close = df_1min['close'].iloc[-1]
                                        result = current_close > ref_current_value
                                        current_variables[var_name] = result
                                        print(f"    -> 当前收盘价: {current_close:.2f}")
                                        print(f"    -> 计算结果: {var_name} = {result}")
                                    else:
                                        print(f"    -> [警告] 暂不支持该表达式类型")
                                else:
                                    print(f"    -> [警告] 跨周期引用值为 NaN")
                            else:
                                print(f"    -> [错误] 变量 {var_field} 未在被引用模型中计算")
                            break
            else:
                # 没有跨周期引用，直接计算
                # 处理简单的变量定义，如 CC:C
                if var_expr.strip() == 'C':
                    result = df_1min['close'].values
                    current_variables[var_name] = result
                    print(f"    -> 使用收盘价数据")
                    print(f"    -> 结果数组长度: {len(result)}")
                    print(f"    -> 最后一个值: {result[-1]:.2f}")
                else:
                    print(f"    -> [警告] 暂不支持该表达式类型: {var_expr}")
            print()
        
        print(f"[OK] 步骤5.3.2完成: 计算了 {len(current_variables)} 个变量")
        print(f"     已计算的变量: {list(current_variables.keys())}")
        print()
        
        # 步骤5.4: 展示最终结果
        print("步骤5.4: 最终结果")
        print("-" * 60)
        print("被引用模型变量计算结果:")
        for var_name, var_value in referenced_variables.items():
            if isinstance(var_value, np.ndarray):
                if len(var_value) > 0:
                    print(f"  {var_name}: 数组长度={len(var_value)}, 当前值={var_value[-1]:.2f}" if not np.isnan(var_value[-1]) else f"  {var_name}: 数组长度={len(var_value)}, 当前值=NaN")
        
        print()
        print("当前模型变量计算结果:")
        for var_name, var_value in current_variables.items():
            if isinstance(var_value, (bool, np.bool_)):
                print(f"  {var_name}: {var_value}")
            elif isinstance(var_value, np.ndarray):
                if len(var_value) > 0:
                    print(f"  {var_name}: 数组长度={len(var_value)}, 当前值={var_value[-1]:.2f}" if not np.isnan(var_value[-1]) else f"  {var_name}: 数组长度={len(var_value)}, 当前值=NaN")
        
        print()
        print("[总结]")
        print("1. 加载被引用的模型文件（MIN5_OPEN）")
        print("2. 解析变量定义（PREV_OPEN:REF(O,1)）")
        print("3. 使用实际K线数据计算变量值（REF(open, 1)）")
        print("4. 在 TEST_IMPORT 中使用计算后的值（MIN5.PREV_OPEN）")
        print("5. 计算当前模型的变量（ISBUYTREND: C > MIN5.PREV_OPEN）")
        
    except Exception as e:
        print(f"[错误] 测试使用场景失败: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    print("=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    test_parse_test_import_file()

