#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代码生成器
将AST转换为Python代码
"""

from typing import List, Optional, Dict, Set
from pathlib import Path
from .ast_visitor import (
    ASTNode, NodeType, ImportNode, VariableDeclNode, VariableAssignNode,
    TradingInstructionNode, FunctionCallNode, BinaryOpNode, UnaryOpNode,
    CrossPeriodRefNode
)
from .dependency_analyzer import DependencyAnalyzer
from .parser import parse_mflang_file


class VariableMapper:
    """变量名映射器 - 将麦语言变量名映射到Python代码"""
    
    # K线数据映射表
    KLINE_DATA_MAP = {
        # 收盘价
        'C': 'self.am.close',
        'CLOSE': 'self.am.close',
        # 最高价
        'H': 'self.am.high',
        'HIGH': 'self.am.high',
        # 最低价
        'L': 'self.am.low',
        'LOW': 'self.am.low',
        # 开盘价
        'O': 'self.am.open',
        'OPEN': 'self.am.open',
        # 成交量
        'V': 'self.am.volume',
        'VOL': 'self.am.volume',
        'VOLUME': 'self.am.volume',
        # 时间
        'TIME': 'self.am.time',
        'KTIME': 'self.am.time',
    }
    
    # 特殊函数映射（这些需要特殊处理，不是直接映射）
    SPECIAL_FUNCTIONS = {
        'BARPOS': 'BARPOS',  # BARPOS需要作为函数调用
    }
    
    def __init__(self, defined_variables: Optional[Set[str]] = None):
        """
        初始化变量映射器
        
        参数:
            defined_variables: 已定义的变量名集合
        """
        self.defined_variables = defined_variables or set()
    
    def map_identifier(self, identifier: str) -> str:
        """
        映射标识符到Python代码
        
        参数:
            identifier: 麦语言标识符
            
        返回:
            Python代码中的标识符
        """
        identifier_upper = identifier.upper()
        
        # 1. 检查是否是K线数据
        if identifier_upper in self.KLINE_DATA_MAP:
            return self.KLINE_DATA_MAP[identifier_upper]
        
        # 2. 检查是否是已定义的变量
        if identifier in self.defined_variables:
            return f"self.{identifier}"
        
        # 3. 检查是否是特殊函数（这些通常作为函数调用处理，但这里返回原样）
        if identifier_upper in self.SPECIAL_FUNCTIONS:
            return identifier  # 保持原样，由函数调用处理
        
        # 4. 其他情况：可能是未定义的变量或函数名，保持原样
        # 注意：在实际使用中，可能需要添加警告或错误处理
        return identifier
    
    def add_defined_variable(self, var_name: str):
        """添加已定义的变量"""
        self.defined_variables.add(var_name)
    
    def add_defined_variables(self, var_names: Set[str]):
        """批量添加已定义的变量"""
        self.defined_variables.update(var_names)


class CodeGenerator:
    """代码生成器 - 将AST转换为Python代码"""
    
    def __init__(self, indent: str = "    "):
        self.indent = indent
        self.indent_level = 0
        self.lines: List[str] = []
        self.import_statements: List[ImportNode] = []
        self.variables: List[VariableAssignNode] = []
        self.trading_instructions: List[TradingInstructionNode] = []
        self.if_then_blocks: List[ASTNode] = []  # IF-THEN-BEGIN-END块
        self.t_command_volume: Optional[int] = None
        self.variable_mapper: Optional[VariableMapper] = None
        self.cross_period_refs: Dict[str, str] = {}  # 跨周期引用缓存: "VARNAME.FIELD" -> "var_name"
        self.cross_period_refs_generated: Set[str] = set()  # 已生成的跨周期引用
        self.imported_models: Dict[str, ASTNode] = {}  # 已解析的导入模型: "formula_name" -> AST
        self.models_dir: Optional[Path] = None  # 模型文件目录（仅用于StrategyCodeGenerator）
    
    def generate(self, ast_root: ASTNode) -> str:
        """生成Python代码"""
        self.lines = []
        self.import_statements = []
        self.variables = []
        self.trading_instructions = []
        self.if_then_blocks = []
        self.t_command_volume = None
        
        # 遍历AST收集信息
        self._collect_info(ast_root)
        
        # 初始化变量映射器（使用已定义的变量）
        defined_vars = {var.var_name for var in self.variables}
        self.variable_mapper = VariableMapper(defined_variables=defined_vars)
        
        # 生成代码
        self._generate_header()
        self._generate_imports()
        self._generate_variable_declarations()
        # 先遍历一次表达式，收集所有跨周期引用
        self._collect_cross_period_refs(ast_root)
        # 生成跨周期引用获取代码
        self._generate_cross_period_refs_code()
        self._generate_variable_assignments()
        self._generate_if_then_blocks()
        self._generate_trading_logic()
        
        return "\n".join(self.lines)
    
    def _collect_info(self, node: ASTNode):
        """收集AST信息"""
        if node is None:
            return
        
        if node.node_type == NodeType.IMPORT:
            self.import_statements.append(node)
        elif node.node_type == NodeType.VARIABLE_ASSIGN:
            self.variables.append(node)
        elif node.node_type == NodeType.TRADING_INSTRUCTION:
            self.trading_instructions.append(node)
        elif node.node_type == NodeType.IF_THEN_BLOCK:
            self.if_then_blocks.append(node)
        elif node.node_type == NodeType.T_COMMAND:
            self.t_command_volume = node.value
        
        # 递归处理子节点
        for child in node.children:
            self._collect_info(child)
    
    def _collect_cross_period_refs(self, node: ASTNode):
        """收集所有跨周期引用（用于生成获取代码）"""
        if node is None:
            return
        
        # 如果是跨周期引用节点，收集它
        if node.node_type == NodeType.CROSS_PERIOD_REF:
            if isinstance(node, CrossPeriodRefNode):
                var_name = node.var_name
                field_name = node.field_name
                ref_key = f"{var_name}.{field_name}"
                
                if ref_key not in self.cross_period_refs:
                    python_var_name = f"{field_name.lower()}_value"
                    self.cross_period_refs[ref_key] = python_var_name
        
        # 递归处理子节点
        if node.children:
            for child in node.children:
                self._collect_cross_period_refs(child)
    
    def _parse_imported_models(self):
        """解析被导入的模型文件"""
        if not self.models_dir:
            return
        
        for imp in self.import_statements:
            formula_name = imp.formula
            if formula_name in self.imported_models:
                # 已经解析过，跳过
                continue
            
            # 构建模型文件路径
            model_file = self.models_dir / formula_name
            
            if not model_file.exists():
                self.lines.append(f"# 警告: 模型文件不存在: {model_file}")
                continue
            
            try:
                # 使用ANTLR解析器解析模型文件
                imported_ast = parse_mflang_file(str(model_file))
                if imported_ast:
                    self.imported_models[formula_name] = imported_ast
            except Exception as e:
                error_msg = f"解析模型文件 {model_file} 失败: {type(e).__name__} - {e}"
                self.lines.append(f"# 警告: {error_msg}")
                import traceback
                tb = traceback.format_exc(limit=2)
                for line in tb.strip().splitlines():
                    self.lines.append(f"# {line}")
                continue
    
    def _generate_header(self):
        """生成文件头"""
        self.lines.append("#!/usr/bin/env python3")
        self.lines.append("# -*- coding: utf-8 -*-")
        self.lines.append('"""')
        self.lines.append("自动生成的策略代码")
        self.lines.append("由麦语言AST代码生成器生成")
        self.lines.append('"""')
        self.lines.append("")
    
    def _generate_imports(self):
        """生成导入语句"""
        self.lines.append("import numpy as np")
        self.lines.append("from mflang import REF, BARSLAST, SUMBARS, BARPOS, HHV, LLV")
        self.lines.append("from mflang.functions import BP, BPK, SPK")
        self.lines.append("")
        
        if self.import_statements:
            self.lines.append("# 跨周期引用")
            for imp in self.import_statements:
                self.lines.append(
                    f"# #IMPORT [{imp.period_type},{imp.period_n},{imp.formula}] AS {imp.var_name}"
                )
            self.lines.append("")
    
    def _generate_variable_declarations(self):
        """生成变量声明"""
        # 这里可以生成变量初始化代码
        pass
    
    def _generate_variable_assignments(self):
        """生成变量赋值代码（按依赖顺序）"""
        if not self.variables:
            return
        
        # 分析变量依赖关系
        analyzer = DependencyAnalyzer()
        try:
            # 获取计算顺序
            ordered_vars = analyzer.analyze(self.variables)
            
            # 创建变量名到变量的映射
            var_map = {var.var_name: var for var in self.variables}
            
            self.lines.append("# 变量计算（按依赖顺序）")
            for var_name in ordered_vars:
                var = var_map.get(var_name)
                if var:
                    expr_code = self._generate_expression(var.expression)
                    self.lines.append(f"{var_name} = {expr_code}")
            self.lines.append("")
        except ValueError as e:
            # 循环依赖错误
            self.lines.append(f"# 错误: {e}")
            self.lines.append("# 使用原始顺序（可能有错误）")
            for var in self.variables:
                var_name = var.var_name
                expr_code = self._generate_expression(var.expression)
                self.lines.append(f"{var_name} = {expr_code}")
            self.lines.append("")
    
    def _generate_if_then_blocks(self):
        """生成IF-THEN-BEGIN-END块代码"""
        if not self.if_then_blocks:
            return
        
        self.lines.append("# IF-THEN-BEGIN-END块")
        for block in self.if_then_blocks:
            self._generate_if_then_block(block)
        self.lines.append("")
    
    def _generate_if_then_block(self, block: ASTNode):
        """生成单个IF-THEN-BEGIN-END块"""
        if not block.children:
            return
        
        # 第一个子节点是条件
        condition = block.children[0]
        cond_code = self._generate_expression(condition)
        
        # 生成if语句
        self.lines.append(f"if {cond_code}:")
        self.indent_level += 1
        
        # 处理块内语句（从第二个子节点开始）
        for stmt in block.children[1:]:
            if stmt is None:
                continue
            
            # 处理不同类型的语句
            if stmt.node_type == NodeType.VARIABLE_ASSIGN:
                # 变量赋值
                var_name = stmt.var_name
                expr_code = self._generate_expression(stmt.expression)
                self.lines.append(f"{self._indent()}{var_name} = {expr_code}")
            elif stmt.node_type == NodeType.TRADING_INSTRUCTION:
                # 交易指令
                self._generate_trading_command(stmt)
            elif stmt.node_type == NodeType.IF_THEN_BLOCK:
                # 嵌套的IF-THEN块
                self._generate_if_then_block(stmt)
            elif stmt.node_type == NodeType.EXPRESSION:
                # 表达式语句（可能是空语句或其他）
                # 跳过空语句
                pass
            else:
                # 其他类型的语句
                expr_code = self._generate_expression(stmt)
                if expr_code and expr_code != "None":
                    self.lines.append(f"{self._indent()}{expr_code}")
        
        self.indent_level -= 1
    
    def _generate_trading_logic(self):
        """生成交易逻辑代码"""
        if not self.trading_instructions:
            return
        
        self.lines.append("# 交易指令")
        for instr in self.trading_instructions:
            if instr.condition:
                cond_code = self._generate_expression(instr.condition)
                self.lines.append(f"if {cond_code}:")
                self.indent_level += 1
                self._generate_trading_command(instr)
                self.indent_level -= 1
            else:
                self._generate_trading_command(instr)
        self.lines.append("")
    
    def _generate_trading_command(self, instr: TradingInstructionNode):
        """生成交易指令代码"""
        cmd = instr.instruction_type
        if instr.group:
            self.lines.append(f"{self._indent()}{cmd}('{instr.group}')")
        else:
            self.lines.append(f"{self._indent()}{cmd}()")
    
    def _generate_expression(self, node: ASTNode) -> str:
        """生成表达式代码"""
        if node is None:
            return "None"
        
        if node.node_type == NodeType.LITERAL:
            return self._generate_literal(node)
        elif node.node_type == NodeType.IDENTIFIER:
            # 使用变量映射器转换标识符
            if self.variable_mapper:
                return self.variable_mapper.map_identifier(node.value)
            else:
                return node.value
        elif node.node_type == NodeType.BINARY_OP:
            return self._generate_binary_op(node)
        elif node.node_type == NodeType.UNARY_OP:
            return self._generate_unary_op(node)
        elif node.node_type == NodeType.FUNCTION_CALL:
            return self._generate_function_call(node)
        elif node.node_type == NodeType.CROSS_PERIOD_REF:
            return self._generate_cross_period_ref(node)
        elif node.node_type == NodeType.EXPRESSION:
            # 处理括号表达式或其他表达式包装
            if node.children and len(node.children) > 0:
                # 如果有子节点，递归处理第一个子节点（通常是实际的表达式）
                return self._generate_expression(node.children[0])
            else:
                return "None"
        else:
            return f"# TODO: {node.node_type}"
    
    def _generate_literal(self, node: ASTNode) -> str:
        """生成字面量代码"""
        value = node.value
        if isinstance(value, bool):
            return "True" if value else "False"
        elif isinstance(value, (int, float)):
            return str(value)
        else:
            return repr(value)
    
    def _generate_binary_op(self, node: BinaryOpNode) -> str:
        """生成二元运算符代码"""
        op = node.operator
        left = self._generate_expression(node.left)
        right = self._generate_expression(node.right)
        
        # 转换运算符（麦语言 -> Python）
        op_map = {
            # 比较运算符
            '=': '==',      # 等于
            '<>': '!=',     # 不等于
            '>': '>',       # 大于
            '<': '<',       # 小于
            '>=': '>=',     # 大于等于
            '<=': '<=',     # 小于等于
            # 逻辑运算符
            '&&': 'and',    # 逻辑与
            '||': 'or',     # 逻辑或
            'AND': 'and',   # 逻辑与（关键字）
            'OR': 'or',     # 逻辑或（关键字）
            # 算术运算符（保持不变）
            '+': '+',
            '-': '-',
            '*': '*',
            '/': '/',
        }
        op = op_map.get(op, op)
        
        return f"({left} {op} {right})"
    
    def _generate_unary_op(self, node: UnaryOpNode) -> str:
        """生成一元运算符代码"""
        op = node.operator
        operand = self._generate_expression(node.operand)
        
        # 转换一元运算符（麦语言 -> Python）
        op_map = {
            # 逻辑运算符
            '!': 'not',     # 逻辑非
            'NOT': 'not',   # 逻辑非（关键字）
            # 算术运算符（正负号）
            '+': '+',       # 正号（通常可以省略，但保留以保持一致性）
            '-': '-',       # 负号
        }
        op = op_map.get(op, op)
        
        # 对于逻辑非，使用 not 关键字
        if op == 'not':
            return f"(not {operand})"
        # 对于正负号，直接使用运算符
        else:
            return f"({op}{operand})"
    
    def _generate_function_call(self, node: FunctionCallNode) -> str:
        """生成函数调用代码"""
        func_name = node.function_name
        args = [self._generate_expression(arg) for arg in node.arguments]
        args_str = ", ".join(args)
        
        # 特殊函数处理（麦语言 -> Python）
        if func_name == 'IF':
            # IF(COND, TRUE_VAL, FALSE_VAL) -> Python三元运算符
            if len(args) == 3:
                return f"({args[1]} if {args[0]} else {args[2]})"
            else:
                return f"IF({args_str})"  # 参数数量不对，保持原样
        elif func_name in ['MAX', 'MAX1']:
            # MAX(X1, X2, ...) -> Python内置max函数
            return f"max({args_str})"
        elif func_name in ['MIN', 'MIN1']:
            # MIN(X1, X2, ...) -> Python内置min函数
            return f"min({args_str})"
        elif func_name == 'MOD':
            # MOD(X, Y) -> Python取模运算符
            if len(args) == 2:
                return f"({args[0]} % {args[1]})"
            else:
                return f"MOD({args_str})"
        elif func_name == 'ABS':
            # ABS(X) -> Python内置abs函数
            if len(args) >= 1:
                return f"abs({args[0]})"
            else:
                return f"ABS({args_str})"
        elif func_name in ['REF', 'BARSLAST', 'SUMBARS', 'BARPOS', 'HHV', 'LLV', 
                           'HHVBARS', 'LLVBARS', 'COUNT', 'EMA', 'MA', 'HV', 'LV']:
            # 这些函数需要从mflang导入，保持原样
            return f"{func_name}({args_str})"
        else:
            # 其他函数（可能是自定义函数或未识别的函数）
            # 保持原样，让运行时处理
            return f"{func_name}({args_str})"
    
    def _generate_cross_period_ref(self, node: CrossPeriodRefNode) -> str:
        """
        生成跨周期引用代码
        
        参数:
            node: 跨周期引用节点
            
        返回:
            Python变量名（用于引用已获取的跨周期数据）
        """
        var_name = node.var_name
        field_name = node.field_name
        ref_key = f"{var_name}.{field_name}"
        
        # 检查是否已经生成过这个跨周期引用的获取代码
        if ref_key not in self.cross_period_refs:
            # 生成一个唯一的变量名
            python_var_name = f"{field_name.lower()}_value"
            self.cross_period_refs[ref_key] = python_var_name
            self.cross_period_refs_generated.add(ref_key)
        else:
            python_var_name = self.cross_period_refs[ref_key]
        
        return python_var_name
    
    def _get_interval_string(self, period_type: str, period_n: int) -> str:
        """
        将周期类型转换为interval字符串
        
        参数:
            period_type: 周期类型（MIN, HOUR, DAY等）
            period_n: 周期参数
            
        返回:
            interval字符串，如 "5m", "1h", "1d"
        """
        period_type_upper = period_type.upper()
        
        if period_type_upper == "MIN":
            return f'"{period_n}m"'
        elif period_type_upper == "HOUR" or period_type_upper == "CUSHOUR":
            return f'"{period_n}h"'
        elif period_type_upper == "DAY":
            return f'"{period_n}d"'
        elif period_type_upper == "WEEK":
            return f'"{period_n}w"'
        elif period_type_upper == "MONTH":
            return f'"{period_n}M"'
        elif period_type_upper == "QUARTER":
            return f'"{period_n}Q"'
        elif period_type_upper == "YEAR":
            return f'"{period_n}Y"'
        else:
            # 未知周期类型，返回默认值
            return f'"{period_n}m"'
    
    def _generate_cross_period_refs_code(self):
        """生成跨周期引用获取代码"""
        if not self.cross_period_refs:
            return
        
        self.lines.append("# 获取跨周期引用数据")
        
        # 按var_name分组，以便优化代码生成
        refs_by_var = {}
        for ref_key, python_var in self.cross_period_refs.items():
            var_name, field_name = ref_key.split('.', 1)
            if var_name not in refs_by_var:
                refs_by_var[var_name] = []
            refs_by_var[var_name].append((field_name, python_var))
        
        # 为每个跨周期引用生成获取代码
        for ref_key, python_var in self.cross_period_refs.items():
            var_name, field_name = ref_key.split('.', 1)
            
            # 查找对应的IMPORT语句
            import_stmt = None
            for imp in self.import_statements:
                if imp.var_name == var_name:
                    import_stmt = imp
                    break
            
            if import_stmt:
                # 使用IndicatorManager获取数据
                interval = self._get_interval_string(import_stmt.period_type, import_stmt.period_n)
                indicator_name = f"{var_name}.{field_name}"
                
                self.lines.append(f"        # 获取跨周期引用 {ref_key}")
                self.lines.append(f"        {python_var} = self.indicator_manager.get_indicator_smart(")
                self.lines.append(f"            {interval},")
                self.lines.append(f'            "{indicator_name}",')
                self.lines.append(f"            prefer_runtime=True,      # 优先使用运行时值（正在聚合的K线）")
                self.lines.append(f"            fallback_to_history=True, # 运行时值不存在时回退到历史值")
                self.lines.append(f"            history_index=-1,         # 回退时使用最新历史值")
                self.lines.append(f"            wait_if_not_ready=True,   # 如果指标未初始化完成，等待")
                self.lines.append(f"            wait_timeout=1.0          # 最多等待1秒")
                self.lines.append(f"        )")
                self.lines.append(f"        if {python_var} is None:")
                self.lines.append(f"            {python_var} = np.nan")
            else:
                # 如果找不到对应的IMPORT语句，使用向后兼容方法
                self.lines.append(f"        # 获取跨周期引用 {ref_key}（向后兼容）")
                self.lines.append(f'        {var_name.lower()}_vars = getattr(self, "{var_name.lower()}_vars", {{}})')
                self.lines.append(f"        {python_var} = {var_name.lower()}_vars.get(\"{field_name}\", np.nan)")
        
        self.lines.append("")
    
    def _generate_cross_period_refs_code_strategy(self):
        """在策略类中生成跨周期引用获取代码"""
        if not self.cross_period_refs:
            return
        
        self.lines.append(f"{self._indent()}# 获取跨周期引用数据")
        
        for ref_key, python_var in self.cross_period_refs.items():
            var_name, field_name = ref_key.split('.', 1)
            
            import_stmt = None
            for imp in self.import_statements:
                if imp.var_name == var_name:
                    import_stmt = imp
                    break
            
            if not import_stmt:
                self.lines.append(f"{self._indent()}# 警告: 未找到跨周期变量 {var_name}")
                continue
            
            interval = self._get_interval_string(import_stmt.period_type, import_stmt.period_n)
            indicator_name = f"{var_name}.{field_name}"
            
            self.lines.append(f"{self._indent()}# 获取跨周期引用 {ref_key}")
            self.lines.append(f"{self._indent()}{python_var} = self.indicator_manager.get_indicator_smart(")
            self.indent_level += 1
            self.lines.append(f"{self._indent()}{interval},")
            self.lines.append(f'{self._indent()}"{indicator_name}",')
            self.lines.append(f'{self._indent()}"{field_name}"')
            self.indent_level -= 1
            self.lines.append(f"{self._indent()})")
            self.lines.append(f"{self._indent()}if {python_var} is None:")
            self.indent_level += 1
            self.lines.append(f"{self._indent()}{python_var} = np.nan")
            self.indent_level -= 1
            self.lines.append("")
    
    def _indent(self) -> str:
        """获取当前缩进"""
        return self.indent * self.indent_level


class StrategyCodeGenerator(CodeGenerator):
    """策略代码生成器 - 生成完整的策略类代码"""
    
    def __init__(self, strategy_name: str = "GeneratedStrategy", indent: str = "    ", models_dir: Optional[str] = None):
        super().__init__(indent)
        self.strategy_name = strategy_name
        # 设置模型文件目录
        if models_dir:
            self.models_dir = Path(models_dir)
        else:
            # 默认使用 mflang/mmodels/ 目录
            current_file = Path(__file__).resolve()
            mflang_dir = current_file.parent.parent
            self.models_dir = mflang_dir / "mmodels"
    
    def generate(self, ast_root: ASTNode) -> str:
        """生成完整的策略类代码"""
        self.lines = []
        self.import_statements = []
        self.variables = []
        self.trading_instructions = []
        self.if_then_blocks = []
        self.t_command_volume = None
        self.cross_period_refs = {}
        self.cross_period_refs_generated = set()
        self.imported_models = {}
        
        # 收集信息
        self._collect_info(ast_root)
        
        # 解析被导入的模型文件
        self._parse_imported_models()
        
        # 初始化变量映射器（使用已定义的变量）
        defined_vars = {var.var_name for var in self.variables}
        self.variable_mapper = VariableMapper(defined_variables=defined_vars)
        
        # 生成完整策略代码
        self._generate_header()
        self._generate_strategy_imports()
        self._generate_strategy_class(ast_root)
        
        return "\n".join(self.lines)
    
    def _generate_strategy_imports(self):
        """生成策略导入语句"""
        self.lines.append("from vnpy_ctastrategy import (")
        self.lines.append("    CtaTemplate,")
        self.lines.append("    BarData,")
        self.lines.append("    ArrayManager")
        self.lines.append(")")
        self.lines.append("")
        self.lines.append("import numpy as np")
        self.lines.append("from mflang import REF, BARSLAST, SUMBARS, BARPOS, HHV, LLV")
        self.lines.append("from mflang.functions import BP, BPK, SPK")
        
        # 如果有跨周期引用，需要导入IndicatorManager
        if self.import_statements:
            self.lines.append("from indicators import IndicatorManager")
        
        self.lines.append("")
    
    def _generate_strategy_class(self, ast_root: ASTNode):
        """生成策略类"""
        class_name = self.strategy_name
        self.lines.append(f"class {class_name}(CtaTemplate):")
        self.indent_level = 1
        
        self.lines.append(f'{self._indent()}"""自动生成的策略类"""')
        self.lines.append("")
        
        # __init__方法
        self._generate_init_method()
        
        # on_bar方法
        self._generate_on_bar_method(ast_root)
    
    def _generate_init_method(self):
        """生成__init__方法"""
        self.lines.append(f"{self._indent()}def __init__(self, cta_engine, strategy_name, vt_symbol, setting):")
        self.indent_level += 1
        self.lines.append(f'{self._indent()}"""初始化策略"""')
        self.lines.append(f"{self._indent()}super().__init__(cta_engine, strategy_name, vt_symbol, setting)")
        self.lines.append(f"{self._indent()}self.am = ArrayManager()")
        
        # 如果有跨周期引用，创建IndicatorManager并注册导入的模型
        if self.import_statements:
            self.lines.append("")
            self.lines.append(f"{self._indent()}# 创建 IndicatorManager 用于管理跨周期指标")
            self.lines.append(f"{self._indent()}self.indicator_manager = IndicatorManager(")
            self.lines.append(f"{self._indent()}    vt_symbol=self.vt_symbol,")
            self.lines.append(f"{self._indent()}    storage_path=None,  # 使用默认路径 .vntrader/indicators/")
            self.lines.append(f"{self._indent()}    use_database=True  # 使用数据库加载历史数据")
            self.lines.append(f"{self._indent()})")
            self.lines.append("")
            
            # 注册导入的模型到IndicatorManager
            self._generate_register_imported_models()
        
        self.lines.append("")
        self.indent_level -= 1
    
    def _generate_register_imported_models(self):
        """生成注册导入模型到IndicatorManager的代码"""
        if not self.import_statements:
            return
        
        self.lines.append(f"{self._indent()}# 注册导入的模型到IndicatorManager")
        
        for imp in self.import_statements:
            formula_name = imp.formula
            var_name = imp.var_name
            period_type = imp.period_type
            period_n = imp.period_n
            interval = self._get_interval_string(period_type, period_n)
            
            # 检查模型是否已解析
            if formula_name in self.imported_models:
                imported_ast = self.imported_models[formula_name]
                # 收集导入模型中的变量
                imported_vars = []
                self._collect_variables_from_ast(imported_ast, imported_vars)
                
                if imported_vars:
                    self.lines.append(f"{self._indent()}# 注册模型: {formula_name} (周期: {interval}, 变量名: {var_name})")
                    for var in imported_vars:
                        indicator_name = f"{var_name}.{var.var_name}"
                        self.lines.append(f'{self._indent()}self.indicator_manager.register_indicator(')
                        self.lines.append(f'{self._indent()}    {interval},')
                        self.lines.append(f'    "{indicator_name}",')
                        self.lines.append(f'    "{formula_name}",')
                        self.lines.append(f'    "{var.var_name}"')
                        self.lines.append(f'{self._indent()})')
                    self.lines.append("")
            else:
                # 模型未解析，生成占位符代码
                self.lines.append(f"{self._indent()}# 警告: 模型 {formula_name} 未解析，无法注册")
                self.lines.append("")
    
    def _collect_variables_from_ast(self, ast: ASTNode, variables: List[VariableAssignNode]):
        """从AST中收集变量定义"""
        if ast is None:
            return
        
        if ast.node_type == NodeType.VARIABLE_ASSIGN:
            if isinstance(ast, VariableAssignNode):
                variables.append(ast)
        
        # 递归处理子节点
        if ast.children:
            for child in ast.children:
                self._collect_variables_from_ast(child, variables)
    
    def _generate_on_bar_method(self, ast_root: ASTNode):
        """生成on_bar方法"""
        self.lines.append(f"{self._indent()}def on_bar(self, bar: BarData):")
        self.indent_level += 1
        self.lines.append(f'{self._indent()}"""K线数据回调"""')
        self.lines.append(f"{self._indent()}self.am.update_bar(bar)")
        self.lines.append("")
        self.lines.append(f"{self._indent()}if not self.am.inited:")
        self.indent_level += 1
        self.lines.append(f"{self._indent()}return")
        self.indent_level -= 1
        self.lines.append("")
        
        # 先收集跨周期引用
        self._collect_cross_period_refs(ast_root)
        
        # 生成跨周期引用获取代码
        if self.cross_period_refs:
            self._generate_cross_period_refs_code_strategy()
        
        # 生成变量计算（按依赖顺序）
        if self.variables:
            self.lines.append(f"{self._indent()}# 计算变量（按依赖顺序）")
            
            # 分析变量依赖关系
            analyzer = DependencyAnalyzer()
            try:
                # 获取计算顺序
                ordered_vars = analyzer.analyze(self.variables)
                
                # 创建变量名到变量的映射
                var_map = {var.var_name: var for var in self.variables}
                
                for var_name in ordered_vars:
                    var = var_map.get(var_name)
                    if var:
                        expr_code = self._generate_expression(var.expression)
                        self.lines.append(f"{self._indent()}self.{var_name} = {expr_code}")
            except ValueError as e:
                # 循环依赖错误
                self.lines.append(f"{self._indent()}# 错误: {e}")
                self.lines.append(f"{self._indent()}# 使用原始顺序（可能有错误）")
                for var in self.variables:
                    var_name = var.var_name
                    expr_code = self._generate_expression(var.expression)
                    self.lines.append(f"{self._indent()}self.{var_name} = {expr_code}")
            self.lines.append("")
        
        # 生成IF-THEN-BEGIN-END块
        if self.if_then_blocks:
            self.lines.append(f"{self._indent()}# IF-THEN-BEGIN-END块")
            for block in self.if_then_blocks:
                self._generate_if_then_block_strategy(block)
            self.lines.append("")
        
        # 生成交易逻辑
        if self.trading_instructions:
            self.lines.append(f"{self._indent()}# 交易指令")
            for instr in self.trading_instructions:
                if instr.condition:
                    cond_code = self._generate_expression(instr.condition)
                    self.lines.append(f"{self._indent()}if {cond_code}:")
                    self.indent_level += 1
                    self._generate_trading_command(instr)
                    self.indent_level -= 1
                else:
                    self._generate_trading_command(instr)
        
        self.indent_level -= 1

    def _generate_if_then_block_strategy(self, block: ASTNode):
        """在策略类中生成 IF-THEN-BEGIN-END 块"""
        if not block or not block.children:
            return

        condition = block.children[0]
        cond_code = self._generate_expression(condition)

        self.lines.append(f"{self._indent()}if {cond_code}:")
        self.indent_level += 1

        for stmt in block.children[1:]:
            if stmt is None:
                continue

            if stmt.node_type == NodeType.VARIABLE_ASSIGN:
                var_name = stmt.var_name
                expr_code = self._generate_expression(stmt.expression)
                self.lines.append(f"{self._indent()}self.{var_name} = {expr_code}")
            elif stmt.node_type == NodeType.TRADING_INSTRUCTION:
                self._generate_trading_command(stmt)
            elif stmt.node_type == NodeType.IF_THEN_BLOCK:
                self._generate_if_then_block_strategy(stmt)
            elif stmt.node_type == NodeType.EXPRESSION:
                continue
            else:
                expr_code = self._generate_expression(stmt)
                if expr_code and expr_code != "None":
                    self.lines.append(f"{self._indent()}{expr_code}")

        self.indent_level -= 1

