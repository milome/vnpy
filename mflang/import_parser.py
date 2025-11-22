#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跨周期引用函数 #IMPORT 解析器
"""

import re
from typing import Dict, List, Optional, Tuple
from enum import Enum


class PeriodType(Enum):
    """周期类型枚举"""
    MIN = "MIN"           # 分钟周期
    HOUR = "HOUR"        # 小时周期
    CUSHOUR = "CUSHOUR"  # 自定义小时周期
    DAY = "DAY"          # 日周期
    WEEK = "WEEK"        # 一周
    MONTH = "MONTH"      # 月周期
    QUARTER = "QUARTER"  # 一季度
    YEAR = "YEAR"        # 年周期


class ImportStatement:
    """#IMPORT 语句解析结果"""
    
    def __init__(
        self,
        period: PeriodType,
        n: int,
        formula: str,
        var_name: str,
        line_number: int = 0
    ):
        self.period = period
        self.n = n
        self.formula = formula
        self.var_name = var_name
        self.line_number = line_number
    
    def __repr__(self):
        return f"#IMPORT[{self.period.value},{self.n},{self.formula}] AS {self.var_name}"


class ImportParser:
    """#IMPORT 语句解析器"""
    
    # 支持的周期类型
    PERIOD_TYPES = {
        "MIN": PeriodType.MIN,
        "HOUR": PeriodType.HOUR,
        "CUSHOUR": PeriodType.CUSHOUR,
        "DAY": PeriodType.DAY,
        "WEEK": PeriodType.WEEK,
        "MONTH": PeriodType.MONTH,
        "QUARTER": PeriodType.QUARTER,
        "YEAR": PeriodType.YEAR,
    }
    
    # 保留的函数名（不能作为变量名）
    RESERVED_NAMES = {
        "REF", "BARSLAST", "SUMBARS", "MA", "EMA", "MACD", "HHV", "LLV",
        "SUM", "COUNT", "MAX", "MIN", "ABS", "IF", "AND", "OR", "NOT"
    }
    
    # #IMPORT 语句正则表达式（AS前后可以有空格或没有空格）
    IMPORT_PATTERN = re.compile(
        r'#IMPORT\s*\[\s*(\w+)\s*,\s*(\d+)\s*,\s*(\w+)\s*\]\s*AS\s+(\w+)',
        re.IGNORECASE
    )
    
    @classmethod
    def parse_import_statement(cls, line: str, line_number: int = 0) -> Optional[ImportStatement]:
        """
        解析 #IMPORT 语句
        
        参数:
            line: 代码行
            line_number: 行号
            
        返回:
            ImportStatement 对象，如果解析失败返回 None
        """
        line = line.strip()
        
        # 移除末尾的分号（如果存在）
        if line.endswith(';'):
            line = line[:-1]
        
        # 匹配 #IMPORT 语句
        match = cls.IMPORT_PATTERN.match(line)
        if not match:
            return None
        
        period_str = match.group(1).upper()
        n_str = match.group(2)
        formula = match.group(3)
        var_name = match.group(4)
        
        # 验证周期类型
        if period_str not in cls.PERIOD_TYPES:
            raise ValueError(f"不支持的周期类型: {period_str}")
        
        period = cls.PERIOD_TYPES[period_str]
        
        # 验证 N 参数
        try:
            n = int(n_str)
            if n < 1:
                raise ValueError(f"N 参数必须大于等于1: {n}")
        except ValueError as e:
            raise ValueError(f"无效的N参数: {n_str}") from e
        
        # 周、季周期，N写入大于1的数，按照1计算
        if period in (PeriodType.WEEK, PeriodType.QUARTER):
            n = 1
        
        # 验证变量名
        if not var_name or var_name[0].isdigit():
            raise ValueError(f"变量名不能以数字开头: {var_name}")
        
        if var_name.upper() in cls.RESERVED_NAMES:
            raise ValueError(f"变量名不能与函数名重复: {var_name}")
        
        return ImportStatement(period, n, formula, var_name, line_number)
    
    @classmethod
    def parse_code(cls, code: str) -> List[ImportStatement]:
        """
        解析代码中的所有 #IMPORT 语句
        
        参数:
            code: 代码字符串
            
        返回:
            ImportStatement 列表
        """
        import_statements = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if line.startswith('#IMPORT') or line.startswith('#import'):
                try:
                    stmt = cls.parse_import_statement(line, i)
                    if stmt:
                        import_statements.append(stmt)
                except ValueError as e:
                    raise ValueError(f"第 {i} 行解析错误: {e}")
        
        # 检查语句总数（#IMPORT、#CALL、#CALL_PLUS、#CALL_OTHER 总共不能超过6个）
        # 目前只检查 #IMPORT
        if len(import_statements) > 6:
            raise ValueError(f"#IMPORT 语句总数不能超过6个，当前有 {len(import_statements)} 个")
        
        return import_statements
    
    @classmethod
    def validate_variable_name(cls, var_name: str) -> bool:
        """
        验证变量名是否有效
        
        参数:
            var_name: 变量名
            
        返回:
            True 如果有效，False 如果无效
        """
        if not var_name:
            return False
        
        # 不能以数字开头
        if var_name[0].isdigit():
            return False
        
        # 不能与函数名重复
        if var_name.upper() in cls.RESERVED_NAMES:
            return False
        
        return True


def parse_import(code: str) -> List[ImportStatement]:
    """
    解析代码中的 #IMPORT 语句（便捷函数）
    
    参数:
        code: 代码字符串
        
    返回:
        ImportStatement 列表
    """
    return ImportParser.parse_code(code)

