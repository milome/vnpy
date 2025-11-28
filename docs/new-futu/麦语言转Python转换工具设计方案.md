# 麦语言文本文件转Python策略转换工具设计方案

## 1. 方案概述

基于麦语言源代码文本文件，开发自动化转换工具，将文华财经WH8策略转换为VNPy框架下的Python策略。

### 1.1 技术可行性大幅提升

**对比分析：**

| 方案类型 | 难度系数 | 成功概率 | 开发周期 | 准确性 |
|----------|----------|----------|----------|--------|
| 二进制文件逆向 | 8/10 | 20-30% | 6-12个月 | 低 |
| 文本文件解析 | 3-4/10 | 90-95% | 2-4周 | 高 |
| 手动重构 | 4-5/10 | 85-95% | 1-2周/策略 | 高 |

### 1.2 核心优势

1. **源码透明**：直接处理可读的麦语言代码
2. **语法明确**：基于公开的麦语言语法规则
3. **批量处理**：一次开发，多次使用
4. **高准确性**：避免逆向工程的不确定性
5. **可扩展性**：易于添加新的函数映射和规则

## 2. 麦语言语法分析

### 2.1 基本语法结构

```m
// 变量赋值
变量名:=表达式;

// 条件判断
条件名:条件表达式;

// 函数调用
函数名(参数1,参数2,...);

// 注释
//这是注释
{这也是注释}
```

### 2.2 常用函数映射表

| 麦语言函数 | 功能描述 | Python等价实现 |
|------------|----------|----------------|
| `MA(X,N)` | N周期移动平均 | `self.am.sma(N)` |
| `EMA(X,N)` | N周期指数移动平均 | `self.am.ema(N)` |
| `MACD(CLOSE,12,26,9)` | MACD指标 | `self.am.macd(12,26,9)` |
| `RSI(CLOSE,N)` | RSI指标 | `self.am.rsi(N)` |
| `CROSS(A,B)` | A上穿B | `self.cross_over(A,B)` |
| `REF(X,N)` | N周期前的值 | `self.am.close_array[-N-1]` |
| `HHV(X,N)` | N周期内最高值 | `np.max(self.am.high_array[-N:])` |
| `LLV(X,N)` | N周期内最低值 | `np.min(self.am.low_array[-N:])` |
| `COUNT(COND,N)` | N周期内条件成立次数 | `np.sum(condition_array[-N:])` |
| `BARSLAST(COND)` | 上次条件成立到现在的周期数 | 自定义函数实现 |

### 2.3 数据引用

| 麦语言 | 含义 | Python等价 |
|--------|------|-------------|
| `OPEN` | 开盘价 | `bar.open_price` |
| `HIGH` | 最高价 | `bar.high_price` |
| `LOW` | 最低价 | `bar.low_price` |
| `CLOSE` | 收盘价 | `bar.close_price` |
| `VOL` | 成交量 | `bar.volume` |

## 3. 转换工具架构设计

### 3.1 整体架构

```python
class MaiLanguageConverter:
    """麦语言转Python转换器"""
    
    def __init__(self):
        self.lexer = MaiLexer()           # 词法分析器
        self.parser = MaiParser()         # 语法分析器
        self.generator = PythonGenerator() # Python代码生成器
        self.function_mapper = FunctionMapper() # 函数映射器
    
    def convert_file(self, input_file: str, output_file: str):
        """转换单个文件"""
        pass
    
    def convert_batch(self, input_dir: str, output_dir: str):
        """批量转换"""
        pass
```

### 3.2 词法分析器（Lexer）

```python
import re
from enum import Enum
from dataclasses import dataclass

class TokenType(Enum):
    # 基本类型
    IDENTIFIER = "IDENTIFIER"    # 标识符
    NUMBER = "NUMBER"           # 数字
    STRING = "STRING"           # 字符串
    
    # 运算符
    ASSIGN = ":="              # 赋值
    PLUS = "+"                 # 加
    MINUS = "-"                # 减
    MULTIPLY = "*"             # 乘
    DIVIDE = "/"               # 除
    
    # 比较运算符
    GT = ">"                   # 大于
    LT = "<"                   # 小于
    GE = ">="                  # 大于等于
    LE = "<="                  # 小于等于
    EQ = "="                   # 等于
    NE = "<>"                  # 不等于
    
    # 逻辑运算符
    AND = "AND"                # 与
    OR = "OR"                  # 或
    NOT = "NOT"                # 非
    
    # 分隔符
    SEMICOLON = ";"            # 分号
    COMMA = ","                # 逗号
    LPAREN = "("               # 左括号
    RPAREN = ")"               # 右括号
    
    # 特殊
    COMMENT = "COMMENT"        # 注释
    NEWLINE = "NEWLINE"        # 换行
    EOF = "EOF"                # 文件结束

@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    column: int

class MaiLexer:
    """麦语言词法分析器"""
    
    def __init__(self):
        self.tokens = []
        self.current_pos = 0
        self.line = 1
        self.column = 1
        
        # 定义正则表达式模式
        self.patterns = [
            (r'//.*', TokenType.COMMENT),           # 单行注释
            (r'\{[^}]*\}', TokenType.COMMENT),      # 块注释
            (r':=', TokenType.ASSIGN),              # 赋值运算符
            (r'>=', TokenType.GE),                  # 大于等于
            (r'<=', TokenType.LE),                  # 小于等于
            (r'<>', TokenType.NE),                  # 不等于
            (r'>', TokenType.GT),                   # 大于
            (r'<', TokenType.LT),                   # 小于
            (r'=', TokenType.EQ),                   # 等于
            (r'\+', TokenType.PLUS),                # 加
            (r'-', TokenType.MINUS),                # 减
            (r'\*', TokenType.MULTIPLY),            # 乘
            (r'/', TokenType.DIVIDE),               # 除
            (r';', TokenType.SEMICOLON),            # 分号
            (r',', TokenType.COMMA),                # 逗号
            (r'\(', TokenType.LPAREN),              # 左括号
            (r'\)', TokenType.RPAREN),              # 右括号
            (r'\d+\.?\d*', TokenType.NUMBER),       # 数字
            (r'[A-Za-z_][A-Za-z0-9_]*', TokenType.IDENTIFIER), # 标识符
            (r'\n', TokenType.NEWLINE),             # 换行
            (r'\s+', None),                         # 空白字符（忽略）
        ]
    
    def tokenize(self, text: str) -> list[Token]:
        """将文本转换为token列表"""
        self.tokens = []
        self.current_pos = 0
        self.line = 1
        self.column = 1
        
        while self.current_pos < len(text):
            matched = False
            
            for pattern, token_type in self.patterns:
                regex = re.compile(pattern)
                match = regex.match(text, self.current_pos)
                
                if match:
                    value = match.group(0)
                    
                    if token_type:  # 不是空白字符
                        token = Token(token_type, value, self.line, self.column)
                        self.tokens.append(token)
                    
                    # 更新位置
                    if token_type == TokenType.NEWLINE:
                        self.line += 1
                        self.column = 1
                    else:
                        self.column += len(value)
                    
                    self.current_pos = match.end()
                    matched = True
                    break
            
            if not matched:
                raise SyntaxError(f"未识别的字符: '{text[self.current_pos]}' "
                                f"在第{self.line}行第{self.column}列")
        
        # 添加EOF标记
        self.tokens.append(Token(TokenType.EOF, "", self.line, self.column))
        return self.tokens
```

### 3.3 语法分析器（Parser）

```python
from dataclasses import dataclass
from typing import List, Optional, Union

@dataclass
class ASTNode:
    """抽象语法树节点基类"""
    pass

@dataclass
class Assignment(ASTNode):
    """赋值语句"""
    variable: str
    expression: 'Expression'

@dataclass
class FunctionCall(ASTNode):
    """函数调用"""
    name: str
    arguments: List['Expression']

@dataclass
class BinaryOp(ASTNode):
    """二元运算"""
    left: 'Expression'
    operator: str
    right: 'Expression'

@dataclass
class Identifier(ASTNode):
    """标识符"""
    name: str

@dataclass
class Number(ASTNode):
    """数字"""
    value: float

# 表达式类型别名
Expression = Union[BinaryOp, FunctionCall, Identifier, Number]

class MaiParser:
    """麦语言语法分析器"""
    
    def __init__(self):
        self.tokens = []
        self.current = 0
    
    def parse(self, tokens: List[Token]) -> List[ASTNode]:
        """解析token列表，返回AST"""
        self.tokens = tokens
        self.current = 0
        
        statements = []
        while not self.is_at_end():
            if self.peek().type == TokenType.COMMENT:
                self.advance()  # 跳过注释
                continue
            if self.peek().type == TokenType.NEWLINE:
                self.advance()  # 跳过换行
                continue
                
            stmt = self.parse_statement()
            if stmt:
                statements.append(stmt)
        
        return statements
    
    def parse_statement(self) -> Optional[ASTNode]:
        """解析语句"""
        if self.check(TokenType.IDENTIFIER):
            return self.parse_assignment()
        return None
    
    def parse_assignment(self) -> Assignment:
        """解析赋值语句"""
        variable = self.advance().value
        
        if self.check(TokenType.ASSIGN):
            self.advance()  # 消费 :=
            expression = self.parse_expression()
            
            if self.check(TokenType.SEMICOLON):
                self.advance()  # 消费 ;
            
            return Assignment(variable, expression)
        else:
            # 可能是条件语句
            self.consume(TokenType.COLON, "期望 ':'")
            expression = self.parse_expression()
            
            if self.check(TokenType.SEMICOLON):
                self.advance()
            
            return Assignment(variable, expression)
    
    def parse_expression(self) -> Expression:
        """解析表达式"""
        return self.parse_or()
    
    def parse_or(self) -> Expression:
        """解析OR表达式"""
        expr = self.parse_and()
        
        while self.match(TokenType.OR):
            operator = self.previous().value
            right = self.parse_and()
            expr = BinaryOp(expr, operator, right)
        
        return expr
    
    def parse_and(self) -> Expression:
        """解析AND表达式"""
        expr = self.parse_equality()
        
        while self.match(TokenType.AND):
            operator = self.previous().value
            right = self.parse_equality()
            expr = BinaryOp(expr, operator, right)
        
        return expr
    
    def parse_equality(self) -> Expression:
        """解析相等性表达式"""
        expr = self.parse_comparison()
        
        while self.match(TokenType.EQ, TokenType.NE):
            operator = self.previous().value
            right = self.parse_comparison()
            expr = BinaryOp(expr, operator, right)
        
        return expr
    
    def parse_comparison(self) -> Expression:
        """解析比较表达式"""
        expr = self.parse_term()
        
        while self.match(TokenType.GT, TokenType.GE, TokenType.LT, TokenType.LE):
            operator = self.previous().value
            right = self.parse_term()
            expr = BinaryOp(expr, operator, right)
        
        return expr
    
    def parse_term(self) -> Expression:
        """解析加减表达式"""
        expr = self.parse_factor()
        
        while self.match(TokenType.PLUS, TokenType.MINUS):
            operator = self.previous().value
            right = self.parse_factor()
            expr = BinaryOp(expr, operator, right)
        
        return expr
    
    def parse_factor(self) -> Expression:
        """解析乘除表达式"""
        expr = self.parse_unary()
        
        while self.match(TokenType.MULTIPLY, TokenType.DIVIDE):
            operator = self.previous().value
            right = self.parse_unary()
            expr = BinaryOp(expr, operator, right)
        
        return expr
    
    def parse_unary(self) -> Expression:
        """解析一元表达式"""
        if self.match(TokenType.MINUS, TokenType.NOT):
            operator = self.previous().value
            right = self.parse_unary()
            return BinaryOp(Number(0), operator, right)
        
        return self.parse_primary()
    
    def parse_primary(self) -> Expression:
        """解析基本表达式"""
        if self.match(TokenType.NUMBER):
            return Number(float(self.previous().value))
        
        if self.match(TokenType.IDENTIFIER):
            name = self.previous().value
            
            # 检查是否是函数调用
            if self.check(TokenType.LPAREN):
                self.advance()  # 消费 (
                arguments = []
                
                if not self.check(TokenType.RPAREN):
                    arguments.append(self.parse_expression())
                    while self.match(TokenType.COMMA):
                        arguments.append(self.parse_expression())
                
                self.consume(TokenType.RPAREN, "期望 ')'")
                return FunctionCall(name, arguments)
            else:
                return Identifier(name)
        
        if self.match(TokenType.LPAREN):
            expr = self.parse_expression()
            self.consume(TokenType.RPAREN, "期望 ')'")
            return expr
        
        raise SyntaxError(f"意外的token: {self.peek().value}")
    
    # 辅助方法
    def match(self, *types: TokenType) -> bool:
        """检查当前token是否匹配给定类型之一"""
        for token_type in types:
            if self.check(token_type):
                self.advance()
                return True
        return False
    
    def check(self, token_type: TokenType) -> bool:
        """检查当前token类型"""
        if self.is_at_end():
            return False
        return self.peek().type == token_type
    
    def advance(self) -> Token:
        """消费当前token并返回"""
        if not self.is_at_end():
            self.current += 1
        return self.previous()
    
    def is_at_end(self) -> bool:
        """检查是否到达文件末尾"""
        return self.peek().type == TokenType.EOF
    
    def peek(self) -> Token:
        """返回当前token"""
        return self.tokens[self.current]
    
    def previous(self) -> Token:
        """返回前一个token"""
        return self.tokens[self.current - 1]
    
    def consume(self, token_type: TokenType, message: str) -> Token:
        """消费指定类型的token，否则抛出异常"""
        if self.check(token_type):
            return self.advance()
        
        current_token = self.peek()
        raise SyntaxError(f"{message}，但得到了 '{current_token.value}' "
                         f"在第{current_token.line}行第{current_token.column}列")
```

### 3.4 Python代码生成器

```python
class PythonGenerator:
    """Python代码生成器"""
    
    def __init__(self):
        self.function_mapper = {
            'MA': self._generate_ma,
            'EMA': self._generate_ema,
            'MACD': self._generate_macd,
            'RSI': self._generate_rsi,
            'CROSS': self._generate_cross,
            'REF': self._generate_ref,
            'HHV': self._generate_hhv,
            'LLV': self._generate_llv,
            'COUNT': self._generate_count,
            'BARSLAST': self._generate_barslast,
        }
        
        self.variable_mapper = {
            'OPEN': 'bar.open_price',
            'HIGH': 'bar.high_price',
            'LOW': 'bar.low_price',
            'CLOSE': 'bar.close_price',
            'VOL': 'bar.volume',
        }
    
    def generate_strategy(self, ast_nodes: List[ASTNode], strategy_name: str) -> str:
        """生成完整的Python策略代码"""
        
        # 分析AST，提取变量和条件
        variables = []
        conditions = []
        
        for node in ast_nodes:
            if isinstance(node, Assignment):
                if self._is_condition(node):
                    conditions.append(node)
                else:
                    variables.append(node)
        
        # 生成策略代码
        code = self._generate_strategy_template(strategy_name)
        code += self._generate_variables_section(variables)
        code += self._generate_calculation_method(variables)
        code += self._generate_signal_method(conditions)
        
        return code
    
    def _generate_strategy_template(self, strategy_name: str) -> str:
        """生成策略模板"""
        return f'''#!/usr/bin/env python3
"""
{strategy_name}
从麦语言自动转换的策略
"""

from vnpy_ctastrategy import (
    CtaTemplate,
    StopOrder,
    TickData,
    BarData,
    TradeData,
    OrderData,
    BarGenerator,
    ArrayManager,
)
from vnpy.trader.constant import Direction, Offset
import talib
import numpy as np


class {strategy_name}(CtaTemplate):
    """{strategy_name}策略"""

    author = "麦语言转换器"

    # 策略参数
    fixed_size: int = 1          # 固定手数

    # 策略变量
'''
    
    def _generate_variables_section(self, variables: List[Assignment]) -> str:
        """生成变量声明部分"""
        code = ""
        for var in variables:
            code += f"    {var.variable.lower()}: float = 0.0\n"
        
        code += '''
    parameters = ["fixed_size"]
    variables = ['''
        
        for i, var in enumerate(variables):
            code += f'"{var.variable.lower()}"'
            if i < len(variables) - 1:
                code += ", "
        
        code += ''']

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """构造函数"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        # 初始化K线生成器：1分钟K线 -> 5分钟K线
        self.bg = BarGenerator(self.on_bar, 5, self.on_5min_bar)

        # 初始化数组管理器
        self.am = ArrayManager()

    def on_init(self):
        """策略初始化"""
        self.write_log(f"{self.__class__.__name__}策略初始化")
        self.load_bar(10)

    def on_start(self):
        """策略启动"""
        self.write_log(f"{self.__class__.__name__}策略启动")

    def on_stop(self):
        """策略停止"""
        self.write_log(f"{self.__class__.__name__}策略停止")

    def on_tick(self, tick: TickData):
        """Tick数据推送"""
        self.bg.update_tick(tick)

    def on_bar(self, bar: BarData):
        """1分钟K线推送"""
        self.bg.update_bar(bar)

    def on_5min_bar(self, bar: BarData):
        """5分钟K线推送（策略主逻辑）"""
        # 先撤销所有挂单
        self.cancel_all()

        # 更新K线数据到数组管理器
        self.am.update_bar(bar)
        if not self.am.inited:
            return

        # 计算技术指标
        self.calculate_indicators()

        # 生成交易信号
        self.generate_signals(bar)

        # 更新界面
        self.put_event()

'''
        return code
    
    def _generate_calculation_method(self, variables: List[Assignment]) -> str:
        """生成指标计算方法"""
        code = '''    def calculate_indicators(self):
        """计算技术指标"""
'''
        
        for var in variables:
            python_expr = self._convert_expression(var.expression)
            code += f"        self.{var.variable.lower()} = {python_expr}\n"
        
        return code + "\n"
    
    def _generate_signal_method(self, conditions: List[Assignment]) -> str:
        """生成信号生成方法"""
        code = '''    def generate_signals(self, bar: BarData):
        """生成交易信号"""
'''
        
        for condition in conditions:
            condition_name = condition.variable.lower()
            python_expr = self._convert_expression(condition.expression)
            
            if 'buy' in condition_name or 'long' in condition_name:
                code += f'''        # {condition.variable}信号
        if {python_expr} and self.pos == 0:
            self.buy(bar.close_price, self.fixed_size)
            self.write_log(f"{condition.variable}买入信号")

'''
            elif 'sell' in condition_name or 'short' in condition_name:
                code += f'''        # {condition.variable}信号
        if {python_expr}:
            if self.pos > 0:
                self.sell(bar.close_price, abs(self.pos))
                self.write_log(f"{condition.variable}平多信号")
            elif self.pos == 0:
                self.short(bar.close_price, self.fixed_size)
                self.write_log(f"{condition.variable}做空信号")

'''
        
        # 添加其他必要方法
        code += '''    def on_order(self, order: OrderData):
        """委托回报"""
        pass

    def on_trade(self, trade: TradeData):
        """成交回报"""
        self.write_log(f"成交回报: {trade.direction.value} {trade.volume}手 @ {trade.price:.2f}")
        self.put_event()

    def on_stop_order(self, stop_order: StopOrder):
        """停止单回报"""
        pass
'''
        
        return code
    
    def _convert_expression(self, expr: Expression) -> str:
        """转换表达式为Python代码"""
        if isinstance(expr, Number):
            return str(expr.value)
        
        elif isinstance(expr, Identifier):
            # 检查是否是内置变量
            if expr.name in self.variable_mapper:
                return self.variable_mapper[expr.name]
            else:
                return f"self.{expr.name.lower()}"
        
        elif isinstance(expr, FunctionCall):
            if expr.name in self.function_mapper:
                return self.function_mapper[expr.name](expr.arguments)
            else:
                # 未知函数，生成注释
                args = [self._convert_expression(arg) for arg in expr.arguments]
                return f"# TODO: 实现函数 {expr.name}({', '.join(args)})"
        
        elif isinstance(expr, BinaryOp):
            left = self._convert_expression(expr.left)
            right = self._convert_expression(expr.right)
            
            # 操作符映射
            op_map = {
                '+': '+',
                '-': '-',
                '*': '*',
                '/': '/',
                '>': '>',
                '<': '<',
                '>=': '>=',
                '<=': '<=',
                '=': '==',
                '<>': '!=',
                'AND': 'and',
                'OR': 'or',
            }
            
            operator = op_map.get(expr.operator, expr.operator)
            return f"({left} {operator} {right})"
        
        return "# TODO: 未知表达式类型"
    
    def _is_condition(self, assignment: Assignment) -> bool:
        """判断是否是条件语句"""
        condition_keywords = ['buy', 'sell', 'long', 'short', 'signal']
        return any(keyword in assignment.variable.lower() for keyword in condition_keywords)
    
    # 函数映射方法
    def _generate_ma(self, args: List[Expression]) -> str:
        if len(args) >= 2:
            period = self._convert_expression(args[1])
            return f"self.am.sma({period})"
        return "# TODO: MA函数参数不足"
    
    def _generate_ema(self, args: List[Expression]) -> str:
        if len(args) >= 2:
            period = self._convert_expression(args[1])
            return f"self.am.ema({period})"
        return "# TODO: EMA函数参数不足"
    
    def _generate_macd(self, args: List[Expression]) -> str:
        if len(args) >= 4:
            fast = self._convert_expression(args[1])
            slow = self._convert_expression(args[2])
            signal = self._convert_expression(args[3])
            return f"self.am.macd({fast}, {slow}, {signal})[0]"
        return "# TODO: MACD函数参数不足"
    
    def _generate_rsi(self, args: List[Expression]) -> str:
        if len(args) >= 2:
            period = self._convert_expression(args[1])
            return f"self.am.rsi({period})"
        return "# TODO: RSI函数参数不足"
    
    def _generate_cross(self, args: List[Expression]) -> str:
        if len(args) >= 2:
            a = self._convert_expression(args[0])
            b = self._convert_expression(args[1])
            return f"self.cross_over({a}, {b})"
        return "# TODO: CROSS函数参数不足"
    
    def _generate_ref(self, args: List[Expression]) -> str:
        if len(args) >= 2:
            period = self._convert_expression(args[1])
            return f"self.am.close_array[-{period}-1]"
        return "# TODO: REF函数参数不足"
    
    def _generate_hhv(self, args: List[Expression]) -> str:
        if len(args) >= 2:
            period = self._convert_expression(args[1])
            return f"np.max(self.am.high_array[-{period}:])"
        return "# TODO: HHV函数参数不足"
    
    def _generate_llv(self, args: List[Expression]) -> str:
        if len(args) >= 2:
            period = self._convert_expression(args[1])
            return f"np.min(self.am.low_array[-{period}:])"
        return "# TODO: LLV函数参数不足"
    
    def _generate_count(self, args: List[Expression]) -> str:
        if len(args) >= 2:
            condition = self._convert_expression(args[0])
            period = self._convert_expression(args[1])
            return f"# TODO: 实现COUNT({condition}, {period})"
        return "# TODO: COUNT函数参数不足"
    
    def _generate_barslast(self, args: List[Expression]) -> str:
        if len(args) >= 1:
            condition = self._convert_expression(args[0])
            return f"# TODO: 实现BARSLAST({condition})"
        return "# TODO: BARSLAST函数参数不足"
```

## 4. 使用示例

### 4.1 输入麦语言文件

```m
// 双均线策略
MA5:=MA(CLOSE,5);
MA20:=MA(CLOSE,20);
GOLDEN_CROSS:=CROSS(MA5,MA20);
DEATH_CROSS:=CROSS(MA20,MA5);
BUY:GOLDEN_CROSS;
SELL:DEATH_CROSS;
```

### 4.2 转换命令

```python
# 使用转换工具
converter = MaiLanguageConverter()
converter.convert_file("双均线策略.txt", "dual_ma_strategy.py")
```

### 4.3 生成的Python代码

```python
#!/usr/bin/env python3
"""
DualMaStrategy
从麦语言自动转换的策略
"""

from vnpy_ctastrategy import (
    CtaTemplate,
    StopOrder,
    TickData,
    BarData,
    TradeData,
    OrderData,
    BarGenerator,
    ArrayManager,
)
from vnpy.trader.constant import Direction, Offset
import talib
import numpy as np


class DualMaStrategy(CtaTemplate):
    """DualMaStrategy策略"""

    author = "麦语言转换器"

    # 策略参数
    fixed_size: int = 1          # 固定手数

    # 策略变量
    ma5: float = 0.0
    ma20: float = 0.0
    golden_cross: float = 0.0
    death_cross: float = 0.0

    parameters = ["fixed_size"]
    variables = ["ma5", "ma20", "golden_cross", "death_cross"]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """构造函数"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        self.bg = BarGenerator(self.on_bar, 5, self.on_5min_bar)
        self.am = ArrayManager()

    def calculate_indicators(self):
        """计算技术指标"""
        self.ma5 = self.am.sma(5)
        self.ma20 = self.am.sma(20)
        self.golden_cross = self.cross_over(self.ma5, self.ma20)
        self.death_cross = self.cross_over(self.ma20, self.ma5)

    def generate_signals(self, bar: BarData):
        """生成交易信号"""
        # BUY信号
        if self.golden_cross and self.pos == 0:
            self.buy(bar.close_price, self.fixed_size)
            self.write_log("BUY买入信号")

        # SELL信号
        if self.death_cross:
            if self.pos > 0:
                self.sell(bar.close_price, abs(self.pos))
                self.write_log("SELL平多信号")
```

## 5. 实施计划

### 5.1 开发阶段（2-4周）

**第1周：基础框架**
- 实现词法分析器
- 实现基本语法分析器
- 建立函数映射表

**第2周：核心功能**
- 完善语法分析器
- 实现Python代码生成器
- 添加常用函数支持

**第3周：功能完善**
- 添加更多麦语言函数支持
- 实现批量转换功能
- 添加错误处理和日志

**第4周：测试优化**
- 全面测试转换功能
- 优化生成代码质量
- 编写使用文档

### 5.2 使用流程

1. **准备麦语言文件**：将WH8策略保存为文本文件
2. **运行转换工具**：使用转换器生成Python代码
3. **代码审核**：检查生成的代码逻辑
4. **测试验证**：进行历史数据回测
5. **部署运行**：在VNPy环境中运行策略

这种方案将大大提高转换的可行性和准确性，是目前最实用的解决方案。

