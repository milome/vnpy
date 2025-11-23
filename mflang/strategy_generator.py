#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略代码生成器
将 mflang/mmodels 目录下的模型文件转换为符合 vnpy_ctastrategy 格式的策略文件
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass

from mflang.import_parser import ImportParser, ImportStatement, PeriodType
from mflang.model_loader import ModelLoader, load_model


@dataclass
class VariableInfo:
    """变量信息"""
    name: str
    expression: str
    uses_cross_period: bool = False
    cross_period_refs: List[str] = None  # 如 ["MIN5.PREV_OPEN"]


class StrategyGenerator:
    """策略代码生成器"""
    
    def __init__(self, models_dir: Optional[str] = None):
        """
        初始化生成器
        
        参数:
            models_dir: 模型文件目录，默认为 mflang/mmodels/
        """
        self.model_loader = ModelLoader(models_dir)
        self.import_parser = ImportParser()
    
    def generate_strategy(
        self,
        model_name: str,
        strategy_class_name: Optional[str] = None,
        output_file: Optional[str] = None,
        author: str = "MFLang Generator"
    ) -> str:
        """
        生成策略代码
        
        参数:
            model_name: 模型文件名（不含路径）
            strategy_class_name: 策略类名，如果为None则自动生成
            output_file: 输出文件路径，如果为None则不写入文件
            author: 策略作者
            
        返回:
            生成的策略代码字符串
        """
        # 读取模型文件内容
        model_file = self.model_loader.models_dir / model_name
        if not model_file.exists():
            raise FileNotFoundError(f"模型文件不存在: {model_file}")
        
        with open(model_file, 'r', encoding='utf-8') as f:
            model_content = f.read()
        
        # 解析 #IMPORT 语句
        import_statements = ImportParser.parse_code(model_content)
        
        # 加载模型文件中的变量定义
        model_variables = self.model_loader.load_model(model_name)
        
        # 解析变量信息
        variables_info = self._parse_variables(model_variables, import_statements)
        
        # 生成策略类名
        if strategy_class_name is None:
            strategy_class_name = self._generate_class_name(model_name)
        
        # 生成代码
        code = self._generate_code(
            model_name=model_name,
            strategy_class_name=strategy_class_name,
            import_statements=import_statements,
            variables_info=variables_info,
            author=author
        )
        
        # 写入文件
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(code)
            # 验证文件是否成功写入
            if output_path.exists() and output_path.stat().st_size > 0:
                print(f"策略文件已生成: {output_path}")
            else:
                raise IOError(f"文件写入失败: {output_path}")
        
        return code
    
    def _parse_variables(
        self,
        model_variables: Dict[str, str],
        import_statements: List[ImportStatement]
    ) -> List[VariableInfo]:
        """解析变量信息"""
        variables_info = []
        import_var_names = {stmt.var_name for stmt in import_statements}
        
        for var_name, var_expr in model_variables.items():
            # 检查是否使用跨周期引用
            cross_period_refs = self._extract_cross_period_refs(var_expr, import_var_names)
            uses_cross_period = len(cross_period_refs) > 0
            
            variables_info.append(VariableInfo(
                name=var_name,
                expression=var_expr,
                uses_cross_period=uses_cross_period,
                cross_period_refs=cross_period_refs
            ))
        
        return variables_info
    
    def _extract_cross_period_refs(
        self,
        expression: str,
        import_var_names: Set[str]
    ) -> List[str]:
        """提取跨周期引用"""
        refs = []
        # 匹配 VAR.VARIABLE_NAME 格式
        pattern = r'([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)'
        matches = re.finditer(pattern, expression)
        
        for match in matches:
            var_ref = match.group(1)
            if var_ref in import_var_names:
                refs.append(f"{var_ref}.{match.group(2)}")
        
        return refs
    
    def _generate_class_name(self, model_name: str) -> str:
        """生成策略类名"""
        # 将模型名转换为驼峰式类名
        # 例如: TEST_IMPORT -> TestImportStrategy
        parts = model_name.split('_')
        class_name = ''.join(word.capitalize() for word in parts)
        return f"{class_name}Strategy"
    
    def _generate_code(
        self,
        model_name: str,
        strategy_class_name: str,
        import_statements: List[ImportStatement],
        variables_info: List[VariableInfo],
        author: str
    ) -> str:
        """生成策略代码"""
        lines = []
        
        # 文件头
        lines.append('#!/usr/bin/env python3')
        lines.append('# -*- coding: utf-8 -*-')
        lines.append(f'"""')
        lines.append(f'自动生成的策略文件')
        lines.append(f'基于模型文件: {model_name}')
        lines.append(f'"""')
        lines.append('')
        
        # 导入语句
        lines.append('from vnpy_ctastrategy import (')
        lines.append('    CtaTemplate,')
        lines.append('    StopOrder,')
        lines.append('    TickData,')
        lines.append('    BarData,')
        lines.append('    TradeData,')
        lines.append('    OrderData,')
        lines.append('    BarGenerator,')
        lines.append('    ArrayManager')
        lines.append(')')
        lines.append('')
        lines.append('from mflang import REF, BARSLAST, SUMBARS, BARPOS, HHV, LLV')
        lines.append('from mflang.import_parser import ImportParser, PeriodType')
        lines.append('from mflang.model_loader import load_model')
        lines.append('import numpy as np')
        lines.append('')
        
        # 策略类定义
        lines.append(f'class {strategy_class_name}(CtaTemplate):')
        lines.append(f'    """基于模型文件 {model_name} 生成的策略"""')
        lines.append('')
        
        # 作者
        lines.append(f'    author = "{author}"')
        lines.append('')
        
        # 参数和变量
        lines.append('    # 策略参数')
        lines.append('    parameters = []')
        lines.append('')
        lines.append('    # 策略变量')
        variables_list = [f'"{var.name}"' for var in variables_info]
        lines.append(f'    variables = [{", ".join(variables_list)}]')
        lines.append('')
        
        # 变量初始化
        for var in variables_info:
            lines.append(f'    {var.name} = 0.0')
        lines.append('')
        
        # __init__ 方法
        lines.append('    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):')
        lines.append('        """初始化策略"""')
        lines.append('        super().__init__(cta_engine, strategy_name, vt_symbol, setting)')
        lines.append('        ')
        lines.append('        # K线管理器')
        lines.append('        self.bg = BarGenerator(self.on_bar)')
        lines.append('        self.am = ArrayManager()')
        lines.append('        ')
        
        # 跨周期数据管理器
        if import_statements:
            lines.append('        # 跨周期数据管理器')
            lines.append('        # 根据 PERIOD 和 N 的组合创建 ArrayManager，相同周期的引用共享同一个 ArrayManager')
            # 收集所有唯一的周期组合
            period_managers = {}  # key: period_key, value: list of stmt
            for stmt in import_statements:
                period_key = self._get_period_key(stmt)
                if period_key not in period_managers:
                    period_managers[period_key] = []
                period_managers[period_key].append(stmt)
            
            # 为每个唯一的周期组合创建一个 ArrayManager
            for period_key, stmts in period_managers.items():
                # 使用第一个 stmt 的信息作为代表（它们都有相同的 PERIOD 和 N）
                first_stmt = stmts[0]
                manager_name = f"{first_stmt.period.value.lower()}_{first_stmt.n}_am"
                lines.append(f'        self.{manager_name} = ArrayManager()  # {first_stmt.period.value}{first_stmt.n}周期数据（共享）')
            lines.append('        ')
            lines.append('        # 跨周期变量缓存（每个 var_name 有独立的缓存）')
            for stmt in import_statements:
                lines.append(f'        self.{stmt.var_name.lower()}_vars = {{}}  # {stmt.var_name} 的变量缓存')
            lines.append('        ')
        
        lines.append('        # 解析 #IMPORT 语句')
        lines.append(f'        self.import_statements = ImportParser.parse_code("""')
        for stmt in import_statements:
            lines.append(f'        {stmt}')
        lines.append('        """)')
        lines.append('        ')
        lines.append('        # 加载被引用的模型文件')
        for stmt in import_statements:
            lines.append(f'        self.{stmt.var_name.lower()}_model = load_model("{stmt.formula}")')
        lines.append('')
        
        # on_init 方法
        lines.append('    def on_init(self):')
        lines.append('        """策略初始化回调"""')
        lines.append('        self.write_log("策略初始化")')
        lines.append('        self.load_bar(10)  # 加载10根K线')
        lines.append('')
        
        # on_start 方法
        lines.append('    def on_start(self):')
        lines.append('        """策略启动回调"""')
        lines.append('        self.write_log("策略启动")')
        lines.append('')
        
        # on_stop 方法
        lines.append('    def on_stop(self):')
        lines.append('        """策略停止回调"""')
        lines.append('        self.write_log("策略停止")')
        lines.append('')
        
        # on_tick 方法
        lines.append('    def on_tick(self, tick: TickData):')
        lines.append('        """Tick数据回调"""')
        lines.append('        self.bg.update_tick(tick)')
        lines.append('')
        
        # on_bar 方法
        lines.append('    def on_bar(self, bar: BarData):')
        lines.append('        """K线数据回调"""')
        lines.append('        self.am.update_bar(bar)')
        lines.append('        ')
        lines.append('        if not self.am.inited:')
        lines.append('            return')
        lines.append('        ')
        
        # 处理跨周期数据
        if import_statements:
            lines.append('        # 处理跨周期数据')
            lines.append('        # 从 #IMPORT 语句中获取 PERIOD 和 N，确定需要加载哪个周期的数据')
            lines.append('        # 遍历所有 #IMPORT 语句，根据 PERIOD 和 N 判断当前K线是否为目标周期')
            lines.append('        for stmt in self.import_statements:')
            lines.append('            # 从 #IMPORT 语句中获取周期信息：PERIOD 和 N')
            lines.append('            # 例如：#IMPORT[MIN,5,MIN5_OPEN] AS MIN5')
            lines.append('            #      PERIOD = MIN, N = 5，表示需要5分钟周期的数据')
            lines.append('            period_type = stmt.period.value  # 周期类型（MIN, HOUR, DAY等）')
            lines.append('            period_n = stmt.n  # 周期参数（如5表示5分钟）')
            lines.append('            ')
            lines.append('            # 判断当前K线是否是目标周期的K线')
            lines.append('            if self._is_period_bar(bar, period_type, period_n):')
            lines.append('                # 根据 PERIOD 和 N 获取对应的 ArrayManager（相同周期共享）')
            lines.append('                period_key = f"{period_type.lower()}_{period_n}"')
            lines.append('                am = getattr(self, f"{period_key}_am")')
            lines.append('                am.update_bar(bar)')
            lines.append('                ')
            lines.append('                # 如果数据已初始化，计算跨周期变量')
            lines.append('                if am.inited:')
            lines.append('                    self._calculate_cross_period_vars(stmt.var_name, stmt.formula, period_type, period_n)')
            lines.append('        ')
            lines.append('        # 注意：如果当前K线不是目标周期，跨周期变量使用上一次计算的值')
            lines.append('        ')
        
        # 计算变量
        lines.append('        # 计算策略变量')
        for var in variables_info:
            if var.uses_cross_period:
                lines.append(f'        # 计算 {var.name}: {var.expression}')
                lines.append(f'        self.{var.name} = self._calculate_variable_{var.name.lower()}()')
            else:
                lines.append(f'        # 计算 {var.name}: {var.expression}')
                lines.append(f'        self.{var.name} = self._calculate_variable_{var.name.lower()}()')
        lines.append('        ')
        lines.append('        # 策略逻辑')
        lines.append('        self._on_strategy_logic()')
        lines.append('')
        
        # 辅助方法：判断是否是目标周期K线
        if import_statements:
            lines.append('    def _is_period_bar(self, bar: BarData, period_type: str, n: int) -> bool:')
            lines.append('        """')
            lines.append('        判断是否是目标周期的K线')
            lines.append('        ')
            lines.append('        参数:')
            lines.append('            period_type: 周期类型（来自 #IMPORT 语句的 PERIOD，如 "MIN", "HOUR", "DAY"）')
            lines.append('            n: 周期参数（来自 #IMPORT 语句的 N，如 5 表示5分钟）')
            lines.append('        ')
            lines.append('        说明:')
            lines.append('            根据 #IMPORT 语句中的 PERIOD 和 N 来判断当前K线是否为目标周期')
            lines.append('            例如：#IMPORT[MIN,5,MIN5_OPEN] AS MIN5')
            lines.append('                 PERIOD=MIN, N=5，表示需要5分钟周期的数据')
            lines.append('                 判断条件：bar.datetime.minute % 5 == 0')
            lines.append('        """')
            lines.append('        if period_type == "MIN":')
            lines.append('            # 分钟周期：判断分钟数是否能被N整除')
            lines.append('            # 例如：N=5 表示5分钟周期，分钟数 % 5 == 0 时是5分钟K线')
            lines.append('            return bar.datetime.minute % n == 0')
            lines.append('        elif period_type == "HOUR":')
            lines.append('            # 小时周期：判断小时数是否能被N整除，且分钟数为0')
            lines.append('            # 例如：N=2 表示2小时周期，小时数 % 2 == 0 且分钟数为0时是2小时K线')
            lines.append('            return bar.datetime.hour % n == 0 and bar.datetime.minute == 0')
            lines.append('        elif period_type == "CUSHOUR":')
            lines.append('            # 自定义小时周期：判断小时数是否能被N整除，且分钟数为0')
            lines.append('            return bar.datetime.hour % n == 0 and bar.datetime.minute == 0')
            lines.append('        elif period_type == "DAY":')
            lines.append('            # 日周期：判断是否是交易日开始（小时数为0，分钟数为0）')
            lines.append('            return bar.datetime.hour == 0 and bar.datetime.minute == 0')
            lines.append('        elif period_type == "WEEK":')
            lines.append('            # 周周期：判断是否是周一且小时数为0，分钟数为0')
            lines.append('            return bar.datetime.weekday() == 0 and bar.datetime.hour == 0 and bar.datetime.minute == 0')
            lines.append('        elif period_type == "MONTH":')
            lines.append('            # 月周期：判断是否是月初且小时数为0，分钟数为0')
            lines.append('            return bar.datetime.day == 1 and bar.datetime.hour == 0 and bar.datetime.minute == 0')
            lines.append('        elif period_type == "QUARTER":')
            lines.append('            # 季度周期：判断是否是季度初且小时数为0，分钟数为0')
            lines.append('            # 季度初：1月、4月、7月、10月的1号')
            lines.append('            return (bar.datetime.month in [1, 4, 7, 10] and ')
            lines.append('                    bar.datetime.day == 1 and ')
            lines.append('                    bar.datetime.hour == 0 and ')
            lines.append('                    bar.datetime.minute == 0)')
            lines.append('        elif period_type == "YEAR":')
            lines.append('            # 年周期：判断是否是年初且小时数为0，分钟数为0')
            lines.append('            return (bar.datetime.month == 1 and ')
            lines.append('                    bar.datetime.day == 1 and ')
            lines.append('                    bar.datetime.hour == 0 and ')
            lines.append('                    bar.datetime.minute == 0)')
            lines.append('        else:')
            lines.append('            # 其他周期类型，需要根据实际情况实现')
            lines.append('            return False')
            lines.append('')
        
        # 辅助方法：计算跨周期变量
        if import_statements:
            lines.append('    def _calculate_cross_period_vars(self, var_name: str, model_name: str, period_type: str, period_n: int):')
            lines.append('        """')
            lines.append('        计算跨周期变量')
            lines.append('        ')
            lines.append('        参数:')
            lines.append('            var_name: 跨周期变量名（如 "MIN5"），来自 #IMPORT 语句的 VAR')
            lines.append('            model_name: 模型文件名（如 "MIN5_OPEN"），来自 #IMPORT 语句的 FORMULA')
            lines.append('            period_type: 周期类型（如 "MIN"），来自 #IMPORT 语句的 PERIOD')
            lines.append('            period_n: 周期参数（如 5），来自 #IMPORT 语句的 N')
            lines.append('        ')
            lines.append('        说明:')
            lines.append('            通过 PERIOD 和 N 来确定 ArrayManager，而不是通过 var_name')
            lines.append('            - 相同 PERIOD 和 N 的 #IMPORT 语句共享同一个 ArrayManager')
            lines.append('            - ArrayManager 命名规则：{period_type.lower()}_{period_n}_am（如 min_5_am）')
            lines.append('            - 每个 var_name 有独立的变量缓存（vars_cache）')
            lines.append('        """')
            lines.append('        # 加载模型文件')
            lines.append('        model = load_model(model_name)')
            lines.append('        ')
            lines.append('        # 根据 PERIOD 和 N 获取对应的 ArrayManager')
            lines.append('        # 命名规则：{period_type.lower()}_{period_n}_am（如 min_5_am）')
            lines.append('        # 相同周期的引用共享同一个 ArrayManager')
            lines.append('        period_key = f"{period_type.lower()}_{period_n}"')
            lines.append('        am = getattr(self, f"{period_key}_am")')
            lines.append('        ')
            lines.append('        # 计算模型中的变量')
            lines.append('        vars_cache = {}')
            lines.append('        for var_name_in_model, var_expr in model.items():')
            lines.append('            # 解析并计算变量')
            lines.append('            # 这里需要根据表达式类型执行相应的计算')
            lines.append('            # 示例：处理 REF(O,1)')
            lines.append('            if "REF(O,1)" in var_expr:')
            lines.append('                open_prices = am.open')
            lines.append('                result = REF(open_prices, 1)')
            lines.append('                vars_cache[var_name_in_model] = result[-1] if len(result) > 0 else np.nan')
            lines.append('            elif "REF(C,1)" in var_expr:')
            lines.append('                close_prices = am.close')
            lines.append('                result = REF(close_prices, 1)')
            lines.append('                vars_cache[var_name_in_model] = result[-1] if len(result) > 0 else np.nan')
            lines.append('            elif var_expr.strip() == "C":')
            lines.append('                vars_cache[var_name_in_model] = am.close[-1] if len(am.close) > 0 else np.nan')
            lines.append('            elif var_expr.strip() == "O":')
            lines.append('                vars_cache[var_name_in_model] = am.open[-1] if len(am.open) > 0 else np.nan')
            lines.append('            # 可以添加更多表达式类型的处理')
            lines.append('        ')
            lines.append('        # 缓存结果')
            lines.append('        setattr(self, f"{var_name.lower()}_vars", vars_cache)')
            lines.append('')
        
        # 辅助方法：计算各个变量
        for var in variables_info:
            lines.append(f'    def _calculate_variable_{var.name.lower()}(self) -> float:')
            lines.append(f'        """计算变量 {var.name}: {var.expression}"""')
            
            if var.uses_cross_period:
                # 使用跨周期引用
                # 先获取所有跨周期引用变量
                cross_period_vars = {}
                for ref in var.cross_period_refs:
                    var_ref, var_field = ref.split('.')
                    lines.append(f'        # 获取跨周期引用 {ref}')
                    lines.append(f'        {var_ref.lower()}_vars = getattr(self, "{var_ref.lower()}_vars", {{}})')
                    lines.append(f'        {var_field.lower()}_value = {var_ref.lower()}_vars.get("{var_field}", np.nan)')
                    cross_period_vars[ref] = f'{var_field.lower()}_value'
                lines.append('        ')
                
                # 解析表达式并计算
                if '>' in var.expression:
                    # 处理比较表达式，如 C > MIN5.PREV_OPEN
                    parts = var.expression.split('>')
                    left = parts[0].strip()
                    right = parts[1].strip()
                    
                    # 处理左侧
                    if left == 'C':
                        lines.append('        current_close = self.am.close[-1] if len(self.am.close) > 0 else np.nan')
                        left_value = 'current_close'
                    elif left == 'O':
                        lines.append('        current_open = self.am.open[-1] if len(self.am.open) > 0 else np.nan')
                        left_value = 'current_open'
                    elif left == 'H':
                        lines.append('        current_high = self.am.high[-1] if len(self.am.high) > 0 else np.nan')
                        left_value = 'current_high'
                    elif left == 'L':
                        lines.append('        current_low = self.am.low[-1] if len(self.am.low) > 0 else np.nan')
                        left_value = 'current_low'
                    else:
                        left_value = left.lower()
                        lines.append(f'        {left_value} = 0.0  # 需要根据实际情况实现')
                    
                    # 处理右侧
                    if '.' in right:
                        # 跨周期引用，如 MIN5.PREV_OPEN
                        var_ref, var_field = right.split('.')
                        # 检查是否已经在前面获取过
                        ref_key = f'{var_ref}.{var_field}'
                        if ref_key in [r for r in var.cross_period_refs]:
                            # 使用已获取的变量
                            right_value = f'{var_field.lower()}_value'
                        else:
                            # 需要获取
                            lines.append(f'        {var_ref.lower()}_vars = getattr(self, "{var_ref.lower()}_vars", {{}})')
                            right_value = f'{var_ref.lower()}_vars.get("{var_field}", np.nan)'
                    else:
                        # 普通变量
                        if right == 'C':
                            lines.append('        right_value = self.am.close[-1] if len(self.am.close) > 0 else np.nan')
                            right_value = 'right_value'
                        elif right == 'O':
                            lines.append('        right_value = self.am.open[-1] if len(self.am.open) > 0 else np.nan')
                            right_value = 'right_value'
                        elif right == 'H':
                            lines.append('        right_value = self.am.high[-1] if len(self.am.high) > 0 else np.nan')
                            right_value = 'right_value'
                        elif right == 'L':
                            lines.append('        right_value = self.am.low[-1] if len(self.am.low) > 0 else np.nan')
                            right_value = 'right_value'
                        else:
                            right_value = right.lower()
                    
                    lines.append('        if np.isnan({}) or np.isnan({}):'.format(left_value, right_value))
                    lines.append('            return 0.0')
                    lines.append(f'        result = {left_value} > {right_value}')
                    lines.append('        return 1.0 if result else 0.0')
                else:
                    lines.append('        # 需要根据实际表达式实现计算逻辑')
                    lines.append('        return 0.0')
            else:
                # 不使用跨周期引用
                if var.expression.strip() == 'C':
                    lines.append('        return self.am.close[-1] if len(self.am.close) > 0 else 0.0')
                elif var.expression.strip() == 'O':
                    lines.append('        return self.am.open[-1] if len(self.am.open) > 0 else 0.0')
                elif var.expression.strip() == 'H':
                    lines.append('        return self.am.high[-1] if len(self.am.high) > 0 else 0.0')
                elif var.expression.strip() == 'L':
                    lines.append('        return self.am.low[-1] if len(self.am.low) > 0 else 0.0')
                else:
                    lines.append('        # 需要根据实际表达式实现计算逻辑')
                    lines.append('        return 0.0')
            lines.append('')
        
        # 策略逻辑方法
        lines.append('    def _on_strategy_logic(self):')
        lines.append('        """策略逻辑"""')
        lines.append('        # 在这里实现策略的交易逻辑')
        lines.append('        # 可以使用计算好的变量进行判断')
        for var in variables_info:
            lines.append(f'        # {var.name} = {self._get_variable_value(var.name)}')
        lines.append('        ')
        lines.append('        # 示例：根据ISBUYTREND判断趋势')
        isbuytrend_vars = [v for v in variables_info if 'TREND' in v.name.upper() or 'BUY' in v.name.upper()]
        if isbuytrend_vars:
            trend_var = isbuytrend_vars[0]
            lines.append(f'        if self.{trend_var.name} > 0:')
            lines.append('            self.write_log(f"检测到多头趋势")')
            lines.append('            # 可以在这里添加买入逻辑')
        else:
            lines.append('        # 根据策略变量实现交易逻辑')
        lines.append('')
        
        return '\n'.join(lines)
    
    def _get_period_key(self, stmt: ImportStatement) -> str:
        """获取周期键"""
        return f"{stmt.period.value}_{stmt.n}"
    
    def _get_variable_value(self, var_name: str) -> str:
        """获取变量值的字符串表示"""
        return f"self.{var_name}"


def generate_strategy_from_model(
    model_name: str,
    strategy_class_name: Optional[str] = None,
    output_file: Optional[str] = None,
    author: str = "MFLang Generator"
) -> str:
    """
    便捷函数：从模型文件生成策略代码
    
    参数:
        model_name: 模型文件名（不含路径）
        strategy_class_name: 策略类名，如果为None则自动生成
        output_file: 输出文件路径，如果为None则不写入文件
        author: 策略作者
        
    返回:
        生成的策略代码字符串
    """
    generator = StrategyGenerator()
    return generator.generate_strategy(
        model_name=model_name,
        strategy_class_name=strategy_class_name,
        output_file=output_file,
        author=author
    )


if __name__ == "__main__":
    # 示例：生成 TEST_IMPORT 模型的策略文件
    print("生成策略文件...")
    code = generate_strategy_from_model(
        model_name="TEST_IMPORT",
        strategy_class_name="TestImportStrategy",
        output_file="strategies/test_import_strategy.py",
        author="MFLang Generator"
    )
    print("策略代码生成完成！")
    print("\n生成的代码预览（前50行）：")
    print("\n".join(code.split('\n')[:50]))

