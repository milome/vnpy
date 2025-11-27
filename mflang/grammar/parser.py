#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
麦语言解析器
使用ANTLR解析麦语言代码并生成AST
"""

from typing import Optional, List, Tuple
from pathlib import Path
import logging

try:
    from antlr4 import *
    from antlr4.error.ErrorListener import ErrorListener
    from .MFLangLexer import MFLangLexer
    from .MFLangParser import MFLangParser
    from .ast_visitor import ASTVisitor
    ANTLR_AVAILABLE = True
except ImportError:
    ANTLR_AVAILABLE = False
    MFLangLexer = None
    MFLangParser = None
    ASTVisitor = None


class MFLangParserWrapper:
    """麦语言解析器包装类"""
    
    def __init__(self):
        if not ANTLR_AVAILABLE:
            raise ImportError(
                "ANTLR解析器未生成。请先运行:\n"
                "  python mflang/grammar/generate_parser.py\n"
                "或手动执行:\n"
                "  antlr4 -Dlanguage=Python3 -visitor MFLang.g4"
            )
        self.ast_visitor = ASTVisitor()
        self._logger = logging.getLogger(__name__)
        self._last_lexer_errors: List[Tuple[int, int, str]] = []
        self._last_parser_errors: List[Tuple[int, int, str]] = []

    class _CollectingErrorListener(ErrorListener):
        """收集但不直接输出的错误监听器"""
        def __init__(self):
            super().__init__()
            self.errors: List[Tuple[int, int, str]] = []

        def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
            self.errors.append((line, column, msg))
    
    def parse_file(self, file_path: str) -> Optional[object]:
        """解析文件并返回AST"""
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        input_stream = FileStream(str(file_path), encoding='utf-8')
        return self.parse_stream(input_stream)
    
    def parse_string(self, code: str) -> Optional[object]:
        """解析字符串并返回AST"""
        input_stream = InputStream(code)
        return self.parse_stream(input_stream)
    
    def parse_stream(self, input_stream) -> Optional[object]:
        """解析输入流并返回AST"""
        # 词法分析
        lexer = MFLangLexer(input_stream)
        lexer_listener = self._CollectingErrorListener()
        lexer.removeErrorListeners()
        lexer.addErrorListener(lexer_listener)
        stream = CommonTokenStream(lexer)
        
        # 语法分析（使用ANTLR生成的解析器）
        parser = MFLangParser(stream)
        parser_listener = self._CollectingErrorListener()
        parser.removeErrorListeners()
        parser.addErrorListener(parser_listener)
        tree = parser.program()
        
        # 保存上次解析的错误供调试
        self._last_lexer_errors = lexer_listener.errors
        self._last_parser_errors = parser_listener.errors

        # 检查语法错误
        if parser.getNumberOfSyntaxErrors() > 0:
            raise SyntaxError(f"语法错误: {parser.getNumberOfSyntaxErrors()} 个错误")
        
        # 如果有词法错误，记录到调试日志而非直接输出
        if self._last_lexer_errors:
            condensed = "; ".join(
                f"line {line}:{col} {msg}" for line, col, msg in self._last_lexer_errors[:5]
            )
            more = "" if len(self._last_lexer_errors) <= 5 else f" (+{len(self._last_lexer_errors)-5} more)"
            self._logger.debug("Lexer warnings: %s%s", condensed, more)

        if self._last_parser_errors:
            condensed = "; ".join(
                f"line {line}:{col} {msg}" for line, col, msg in self._last_parser_errors[:5]
            )
            more = "" if len(self._last_parser_errors) <= 5 else f" (+{len(self._last_parser_errors)-5} more)"
            self._logger.debug("Parser warnings: %s%s", condensed, more)

        # 构建AST
        ast = self.ast_visitor.visit(tree)
        return ast


def parse_mflang_file(file_path: str) -> Optional[object]:
    """解析麦语言文件的便捷函数"""
    parser = MFLangParserWrapper()
    return parser.parse_file(file_path)


def parse_mflang_string(code: str) -> Optional[object]:
    """解析麦语言字符串的便捷函数"""
    parser = MFLangParserWrapper()
    return parser.parse_string(code)

