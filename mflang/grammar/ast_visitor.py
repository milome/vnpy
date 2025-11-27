#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AST访问者实现
遍历ANTLR解析树并构建AST（抽象语法树）
"""

from typing import Any, Optional, List, Dict
from dataclasses import dataclass
from enum import Enum

# 如果解析器已生成，导入它
try:
    from .MFLangVisitor import MFLangVisitor
    from .MFLangParser import MFLangParser
except ImportError:
    # 如果解析器未生成，定义占位符
    MFLangVisitor = None
    MFLangParser = None


class NodeType(Enum):
    """AST节点类型"""
    PROGRAM = "PROGRAM"
    IMPORT = "IMPORT"
    VARIABLE_DECL = "VARIABLE_DECL"
    VARIABLE_ASSIGN = "VARIABLE_ASSIGN"
    TRADING_INSTRUCTION = "TRADING_INSTRUCTION"
    T_COMMAND = "T_COMMAND"
    IF_THEN_BLOCK = "IF_THEN_BLOCK"
    EXPRESSION = "EXPRESSION"
    FUNCTION_CALL = "FUNCTION_CALL"
    IDENTIFIER = "IDENTIFIER"
    LITERAL = "LITERAL"
    CROSS_PERIOD_REF = "CROSS_PERIOD_REF"
    BINARY_OP = "BINARY_OP"
    UNARY_OP = "UNARY_OP"


@dataclass
class ASTNode:
    """AST节点基类"""
    node_type: NodeType
    value: Any = None
    children: List['ASTNode'] = None
    line: int = 0
    column: int = 0
    
    def __post_init__(self):
        if self.children is None:
            self.children = []


@dataclass
class ImportNode(ASTNode):
    """#IMPORT语句节点"""
    period_type: str = ""
    period_n: int = 0
    formula: str = ""
    var_name: str = ""


@dataclass
class VariableDeclNode(ASTNode):
    """变量声明节点"""
    var_name: str = ""
    initial_value: ASTNode = None


@dataclass
class VariableAssignNode(ASTNode):
    """变量赋值节点"""
    var_name: str = ""
    expression: ASTNode = None
    format_options: List[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        if self.format_options is None:
            self.format_options = []


@dataclass
class TradingInstructionNode(ASTNode):
    """交易指令节点"""
    condition: Optional[ASTNode] = None
    instruction_type: str = ""  # BP, SP, BK, SK, BPK, SPK
    group: Optional[str] = None  # A-I


@dataclass
class FunctionCallNode(ASTNode):
    """函数调用节点"""
    function_name: str = ""
    arguments: List[ASTNode] = None
    
    def __post_init__(self):
        super().__post_init__()
        if self.arguments is None:
            self.arguments = []


@dataclass
class BinaryOpNode(ASTNode):
    """二元运算符节点"""
    operator: str = ""
    left: ASTNode = None
    right: ASTNode = None


@dataclass
class UnaryOpNode(ASTNode):
    """一元运算符节点"""
    operator: str = ""
    operand: ASTNode = None


@dataclass
class CrossPeriodRefNode(ASTNode):
    """跨周期引用节点"""
    var_name: str = ""  # 如 HOURTREND
    field_name: str = ""  # 如 VARNAME


class ASTVisitor:
    """AST访问者 - 将ANTLR解析树转换为AST"""
    
    def __init__(self):
        self.ast_root: Optional[ASTNode] = None
        self.current_line = 0
        self.current_column = 0
    
    def visit(self, tree) -> ASTNode:
        """访问解析树并返回AST根节点"""
        if MFLangVisitor is None:
            raise ImportError(
                "ANTLR解析器未生成。请先运行: "
                "python mflang/grammar/generate_parser.py"
            )
        
        visitor = MFLangASTVisitor()
        self.ast_root = visitor.visit(tree)
        return self.ast_root


if MFLangVisitor is not None:
    class MFLangASTVisitor(MFLangVisitor):
        """ANTLR访问者实现 - 构建AST"""
        
        def __init__(self):
            super().__init__()
        
        def visitProgram(self, ctx: MFLangParser.ProgramContext) -> ASTNode:
            """访问程序根节点"""
            node = ASTNode(NodeType.PROGRAM)
            for stmt in ctx.statement():
                child = self.visit(stmt)
                if child:
                    node.children.append(child)
            return node
        
        def visitImportStatement(self, ctx: MFLangParser.ImportStatementContext) -> ASTNode:
            """访问#IMPORT语句"""
            period_type = ctx.periodType().getText()
            period_n = int(ctx.integer().getText())
            formula = ctx.identifier()[0].getText()
            var_name = ctx.identifier()[1].getText()
            
            node = ImportNode(
                NodeType.IMPORT,
                period_type=period_type,
                period_n=period_n,
                formula=formula,
                var_name=var_name
            )
            return node
        
        def visitVariableDeclaration(self, ctx: MFLangParser.VariableDeclarationContext) -> ASTNode:
            """访问VARIABLE声明"""
            var_name = ctx.identifier().getText()
            initial_value = self.visit(ctx.expression())
            
            node = VariableDeclNode(
                NodeType.VARIABLE_DECL,
                var_name=var_name,
                initial_value=initial_value
            )
            return node
        
        def visitVariableAssignment(self, ctx: MFLangParser.VariableAssignmentContext) -> ASTNode:
            """访问变量赋值"""
            if ctx.identifier():
                var_name = ctx.identifier().getText()
            elif ctx.literal():
                var_name = ctx.literal().getText()
            else:
                var_name = ""

            expression = self.visit(ctx.expression()) if ctx.expression() else None
            format_options = [opt.getText() for opt in ctx.formatOption()]
            
            node = VariableAssignNode(
                NodeType.VARIABLE_ASSIGN,
                var_name=var_name,
                expression=expression,
                format_options=format_options
            )
            if expression:
                node.children.append(expression)
            return node
        
        def visitTradingInstruction(self, ctx: MFLangParser.TradingInstructionContext) -> ASTNode:
            """访问交易指令"""
            condition = None
            if ctx.expression():
                condition = self.visit(ctx.expression())
            
            instruction_type = ctx.tradingCmd().getText()
            group = None
            if ctx.GROUP():  # GROUP是词法规则，使用大写
                group = ctx.GROUP().getText()
            
            node = TradingInstructionNode(
                NodeType.TRADING_INSTRUCTION,
                condition=condition,
                instruction_type=instruction_type,
                group=group
            )
            return node
        
        def visitTCommandStatement(self, ctx: MFLangParser.TCommandStatementContext) -> ASTNode:
            """访问T_COMMAND语句"""
            volume = int(ctx.integer().getText())
            node = ASTNode(NodeType.T_COMMAND, value=volume)
            return node
        
        def visitIfThenBlock(self, ctx: MFLangParser.IfThenBlockContext) -> ASTNode:
            """访问IF-THEN-BEGIN-END块"""
            condition = self.visit(ctx.expression())
            statements = [self.visit(stmt) for stmt in ctx.blockStatement()]
            
            node = ASTNode(NodeType.IF_THEN_BLOCK)
            node.children = [condition] + statements
            return node
        
        def visitExpression(self, ctx: MFLangParser.ExpressionContext) -> ASTNode:
            """访问表达式"""
            # 处理各种表达式类型
            if ctx.OrExpression():
                return self._visitBinaryOp(ctx, '||')
            elif ctx.AndExpression():
                return self._visitBinaryOp(ctx, '&&')
            elif ctx.OrKeywordExpression():
                return self._visitBinaryOp(ctx, 'OR')
            elif ctx.AndKeywordExpression():
                return self._visitBinaryOp(ctx, 'AND')
            elif ctx.NotExpression():
                return self._visitUnaryOp(ctx, '!')
            elif ctx.NotKeywordExpression():
                return self._visitUnaryOp(ctx, 'NOT')
            elif ctx.ComparisonExpression():
                op = ctx.getChild(1).getText()
                return self._visitBinaryOp(ctx, op)
            elif ctx.AdditiveExpression():
                op = ctx.getChild(1).getText()
                return self._visitBinaryOp(ctx, op)
            elif ctx.MultiplicativeExpression():
                op = ctx.getChild(1).getText()
                return self._visitBinaryOp(ctx, op)
            elif ctx.UnaryExpression():
                op = ctx.getChild(0).getText()
                return self._visitUnaryOp(ctx, op)
            elif ctx.PrimaryExpr():
                return self.visit(ctx.primaryExpression())
            else:
                return ASTNode(NodeType.EXPRESSION, value="UNKNOWN")
        
        def _visitBinaryOp(self, ctx, op: str) -> ASTNode:
            """访问二元运算符"""
            left = self.visit(ctx.expression(0))
            right = self.visit(ctx.expression(1))
            node = BinaryOpNode(NodeType.BINARY_OP, operator=op, left=left, right=right)
            if left:
                node.children.append(left)
            if right:
                node.children.append(right)
            return node
        
        def _visitUnaryOp(self, ctx, op: str) -> ASTNode:
            """访问一元运算符"""
            operand = self.visit(ctx.expression(0))
            node = UnaryOpNode(NodeType.UNARY_OP, operator=op, operand=operand)
            if operand:
                node.children.append(operand)
            return node
        
        def visitPrimaryExpression(self, ctx: MFLangParser.PrimaryExpressionContext) -> ASTNode:
            """访问基本表达式"""
            if ctx.LiteralExpr():
                return self.visit(ctx.literal())
            elif ctx.IdentifierExpr():
                return ASTNode(NodeType.IDENTIFIER, value=ctx.identifier().getText())
            elif ctx.KlineDataExpr():
                return ASTNode(NodeType.IDENTIFIER, value=ctx.klineData().getText())
            elif ctx.FunctionCallExpr():
                return self.visit(ctx.functionCall())
            elif ctx.CrossPeriodRefExpr():
                return self.visit(ctx.crossPeriodRef())
            elif ctx.ParenExpr():
                return self.visit(ctx.expression())
            else:
                return ASTNode(NodeType.EXPRESSION, value="UNKNOWN")
        
        def visitFunctionCall(self, ctx: MFLangParser.FunctionCallContext) -> ASTNode:
            """访问函数调用"""
            # 根据函数类型调用相应的访问方法
            if ctx.refFunction():
                return self._visitFunction(ctx.refFunction(), 'REF', 2)
            elif ctx.barslastFunction():
                return self._visitFunction(ctx.barslastFunction(), 'BARSLAST', 1)
            elif ctx.sumbarsFunction():
                return self._visitFunction(ctx.sumbarsFunction(), 'SUMBARS', 2)
            elif ctx.hhvFunction():
                return self._visitFunction(ctx.hhvFunction(), 'HHV', 2)
            elif ctx.llvFunction():
                return self._visitFunction(ctx.llvFunction(), 'LLV', 2)
            elif ctx.hhvbarsFunction():
                return self._visitFunction(ctx.hhvbarsFunction(), 'HHVBARS', 2)
            elif ctx.llvbarsFunction():
                return self._visitFunction(ctx.llvbarsFunction(), 'LLVBARS', 2)
            elif ctx.countFunction():
                return self._visitFunction(ctx.countFunction(), 'COUNT', 2)
            elif ctx.maxFunction():
                return self._visitFunction(ctx.maxFunction(), 'MAX', -1)  # 可变参数
            elif ctx.max1Function():
                return self._visitFunction(ctx.max1Function(), 'MAX1', -1)
            elif ctx.minFunction():
                return self._visitFunction(ctx.minFunction(), 'MIN', -1)  # 可变参数
            elif ctx.min1Function():
                return self._visitFunction(ctx.min1Function(), 'MIN1', -1)
            elif ctx.ifFunction():
                return self._visitFunction(ctx.ifFunction(), 'IF', 3)
            elif ctx.absFunction():
                return self._visitFunction(ctx.absFunction(), 'ABS', 1)
            elif ctx.emaFunction():
                return self._visitFunction(ctx.emaFunction(), 'EMA', 2)
            elif ctx.maFunction():
                return self._visitFunction(ctx.maFunction(), 'MA', 2)
            elif ctx.stdFunction():
                return self._visitFunction(ctx.stdFunction(), 'STD', 2)
            elif ctx.modFunction():
                return self._visitFunction(ctx.modFunction(), 'MOD', 2)
            elif ctx.hvFunction():
                return self._visitFunction(ctx.hvFunction(), 'HV', 2)
            elif ctx.lvFunction():
                return self._visitFunction(ctx.lvFunction(), 'LV', 2)
            elif ctx.timeFunction():
                return self._visitFunction(ctx.timeFunction(), 'TIME', 0)
            elif ctx.betweenFunction():
                return self._visitFunction(ctx.betweenFunction(), 'BETWEEN', 3)
            else:
                # 处理其他函数
                return ASTNode(NodeType.FUNCTION_CALL, value="UNKNOWN")
        
        def _visitFunction(self, func_ctx, func_name: str, arg_count: int) -> ASTNode:
            """访问函数（通用方法）"""
            args: List[ASTNode] = []
            expressions: List = []

            # 兼容只定义了 expression()（无索引参数）与带索引版本的上下文
            expr_attr = getattr(func_ctx, "expression", None)
            if expr_attr:
                try:
                    expr_result = expr_attr()
                except TypeError:
                    expr_result = None
                if isinstance(expr_result, list):
                    expressions = expr_result
                elif expr_result is not None:
                    expressions = [expr_result]

            if arg_count == -1:
                # 可变参数函数
                for expr_ctx in expressions:
                    args.append(self.visit(expr_ctx))
            else:
                # 固定参数函数
                for i in range(arg_count):
                    if i < len(expressions):
                        args.append(self.visit(expressions[i]))
            
            node = FunctionCallNode(
                NodeType.FUNCTION_CALL,
                function_name=func_name,
                arguments=args
            )
            for arg in args:
                node.children.append(arg)
            return node
        
        def visitCrossPeriodRef(self, ctx: MFLangParser.CrossPeriodRefContext) -> ASTNode:
            """访问跨周期引用"""
            var_name = ctx.identifier(0).getText()
            field_name = ctx.identifier(1).getText()
            
            return CrossPeriodRefNode(
                NodeType.CROSS_PERIOD_REF,
                var_name=var_name,
                field_name=field_name
            )
        
        def visitLiteral(self, ctx: MFLangParser.LiteralContext) -> ASTNode:
            """访问字面量"""
            if ctx.integer():
                value = int(ctx.integer().getText())
            elif ctx.float_():  # ANTLR生成的Python代码中，float会变成float_
                value = float(ctx.float_().getText())
            elif ctx.booleanLiteral():
                text = ctx.booleanLiteral().getText()
                value = text in ['1', 'true', 'TRUE']
            elif ctx.stringLiteral():
                text = ctx.stringLiteral().getText()
                # 去掉首尾引号，并简单处理转义
                value = bytes(text[1:-1], 'utf-8').decode('unicode_escape')
            else:
                value = None
            
            return ASTNode(NodeType.LITERAL, value=value)
        
        def visitEmptyStatement(self, ctx: MFLangParser.EmptyStatementContext) -> ASTNode:
            """访问空语句"""
            return None  # 空语句不生成节点

