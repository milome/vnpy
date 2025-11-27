grammar MFLang;

// 语法文件：麦语言 (MFLang) 语法定义
// 基于 RICE1.txt 文件分析
// 目标：解析麦语言模型文件并生成Python代码

// ============================================================================
// 词法规则 (Lexer Rules)
// ============================================================================

// 空白字符（忽略）
WS: [ \t\r\n]+ -> skip;

// 单行注释
LINE_COMMENT: '//' ~[\r\n]* -> skip;

// 多行注释
BLOCK_COMMENT: '/*' .*? '*/' -> skip;

// 关键字
VARIABLE: 'VARIABLE';
IF: 'IF';
THEN: 'THEN';
BEGIN: 'BEGIN';
END: 'END';
AND: 'AND';
OR: 'OR';
NOT: 'NOT';

// 交易指令关键字
BP: 'BP';
SP: 'SP';
BK: 'BK';
SK: 'SK';
BPK: 'BPK';
SPK: 'SPK';

// 特殊指令
T_COMMAND: 'T_COMMAND';

// 导入语句
IMPORT: '#IMPORT';

// 数据类型关键字（K线数据）
OPEN: 'OPEN' | 'O';
CLOSE: 'CLOSE' | 'C';
HIGH: 'HIGH' | 'H';
LOW: 'LOW' | 'L';
VOLUME: 'VOLUME' | 'V';
DATE: 'DATE';
MINUTE: 'MINUTE';
// 注意：HOUR和MIN在周期类型中定义，避免冲突
BARPOS: 'BARPOS';

// 函数名（常用麦语言函数）
REF: 'REF';
BARSLAST: 'BARSLAST';
SUMBARS: 'SUMBARS';
HHV: 'HHV';
LLV: 'LLV';
HHVBARS: 'HHVBARS';
LLVBARS: 'LLVBARS';
COUNT: 'COUNT';
MAX: 'MAX';
MAX1: 'MAX1';
// 注意：MIN在词法分析时会被识别为PERIOD_MIN（因为PERIOD_MIN规则在前），
// 但在函数调用上下文中，我们将其作为MIN函数处理
MIN1: 'MIN1';
ABS: 'ABS';
EMA: 'EMA';
MA: 'MA';
STD: 'STD';
SMA: 'SMA';
MOD: 'MOD';
HV: 'HV';
LV: 'LV';
TIME: 'TIME';
BETWEEN: 'BETWEEN';
DRAWLINE3: 'DRAWLINE3';
DRAWTEXT: 'DRAWTEXT';
DRAWTEXT_REL: 'DRAWTEXT_REL';
DRAWCOLORKLINE: 'DRAWCOLORKLINE';
DRAWCOLOR: 'DRAWCOLOR';
DRAWTITLE: 'DRAWTITLE';
DRAWHLINE: 'DRAWHLINE';

// 格式化选项
PRECIS0: 'PRECIS0';
PRECIS1: 'PRECIS1';
PRECIS2: 'PRECIS2';
PRECIS3: 'PRECIS3';
NODRAW: 'NODRAW';
COLORWHITE: 'COLORWHITE';
COLORRED: 'COLORRED';
COLORGREEN: 'COLORGREEN';
COLORYELLOW: 'COLORYELLOW';
COLORLIGHTRED: 'COLORLIGHTRED';
COLORLIGHTGREEN: 'COLORLIGHTGREEN';
COLORCYAN: 'COLORCYAN';
COLORBLUE: 'COLORBLUE';
COLORPURPLE: 'COLORPURPLE';
LINETHICK1: 'LINETHICK1';
LINETHICK2: 'LINETHICK2';
LINETHICK3: 'LINETHICK3';
LINETHICK5: 'LINETHICK5';
RGB: 'RGB';
DASH: 'DASH';
DASHDOT: 'DASHDOT';
DASHDOTDOT: 'DASHDOTDOT';
VOLSTICK: 'VOLSTICK';
ALIGN0: 'ALIGN0';
ALIGN1: 'ALIGN1';
ALIGN2: 'ALIGN2';
ALIGN3: 'ALIGN3';
ALIGN4: 'ALIGN4';
FONTSIZE10: 'FONTSIZE10';
FONTSIZE12: 'FONTSIZE12';
FONTSIZE14: 'FONTSIZE14';
DOTSTYLE: 'DOT';

// 运算符
PLUS: '+';
MINUS: '-';
MULT: '*';
DIV: '/';
GT: '>';
LT: '<';
EQ: '=';
NE: '<>';
GE: '>=';
LE: '<=';

// 逻辑运算符
AND_OP: '&&';
OR_OP: '||';
NOT_OP: '!';

// 分隔符
COMMA: ',';
SEMICOLON: ';';
COLON: ':';
ASSIGN: ':=';
LPAREN: '(';
RPAREN: ')';
LBRACKET: '[';
RBRACKET: ']';
AT: '@';

// 周期类型（必须在其他关键字之前，避免被IDENTIFIER匹配）
PERIOD_MIN: 'MIN';
PERIOD_HOUR: 'HOUR';
PERIOD_CUSHOUR: 'CUSHOUR';
PERIOD_DAY: 'DAY';
PERIOD_WEEK: 'WEEK';
PERIOD_MONTH: 'MONTH';
PERIOD_QUARTER: 'QUARTER';
PERIOD_YEAR: 'YEAR';

// AS关键字（用于#IMPORT）
AS: 'AS';

// 分组字符（A-I，用于交易指令）
GROUP: [A-I];

// 数字（必须在GROUP之后，避免单个数字被GROUP匹配）
INTEGER: [0-9]+;
// 浮点数必须包含整数部分，避免与跨周期引用如 HOURTREND.3KHIGH 冲突
FLOAT: [0-9]+ '.' [0-9]+;
STRING: '\'' (~['\r\n] | '\\' .)* '\'';

// 标识符（支持中文、英文、数字、下划线，可以以数字开头，用于跨周期引用如 3KHIGH）
// 注意：需要放在关键字之后，避免冲突
IDENTIFIER: [A-Za-z\u4e00-\u9fa5_0-9][A-Za-z0-9\u4e00-\u9fa5_]*;

// ============================================================================
// 语法规则 (Parser Rules)
// ============================================================================

// 程序入口：模型文件由多个语句组成
program: statement* EOF;

// 语句类型
statement
    : importStatement
    | variableDeclaration
    | variableAssignment
    | tradingInstruction
    | tCommandStatement
    | ifThenBlock
    | drawStatement
    | formatOnlyStatement
    | emptyStatement
    ;

// #IMPORT 语句
// 示例: #IMPORT [DAY,1, 米仓I号日内趋势] AS DAYTREND
importStatement: IMPORT LBRACKET periodType COMMA integer COMMA identifier RBRACKET AS identifier SEMICOLON?;

// 周期类型
periodType: PERIOD_MIN | PERIOD_HOUR | PERIOD_CUSHOUR | PERIOD_DAY 
          | PERIOD_WEEK | PERIOD_MONTH | PERIOD_QUARTER | PERIOD_YEAR;

// VARIABLE 声明
// 示例: VARIABLE: NUMOFDAY := 0;
variableDeclaration: VARIABLE COLON identifier ASSIGN expression SEMICOLON;

// 变量赋值
// 示例: NUMOFDAY: BARPOS, NODRAW;
// 示例: ISUPTREND := MAINTREND1M >= REF(MAINTREND1M,5), PRECIS0, NODRAW;
// 示例: 0.0, COLORWHITE, NODRAW; (分隔符语句，允许数字字面量作为标识符)
// 注意：分号是可选的（在IF-THEN块中可能没有分号）
variableAssignment: (identifier | literal) (COLON | ASSIGN)? expression? (COMMA formatOption)* SEMICOLON?;

// 交易指令
// 示例: BP;
// 示例: CONDITION,BP;
// 示例: CONDITION,BPK('A');
tradingInstruction: (expression COMMA)? tradingCmd (LPAREN GROUP RPAREN)? SEMICOLON?;

// 交易指令类型
tradingCmd: BP | SP | BK | SK | BPK | SPK;

// T_COMMAND 语句
// 示例: T_COMMAND(1);
tCommandStatement: T_COMMAND LPAREN integer RPAREN SEMICOLON;

// IF-THEN-BEGIN-END 语句块
// 示例:
// IF ISDOWNTREND = 1
// THEN
// BEGIN
//     CURRENTTREND := -4;
// END
ifThenBlock: IF expression THEN BEGIN blockStatement* END;

// 块内语句（可能没有分号）
blockStatement
    : ifThenBlock
    | identifier (COLON | ASSIGN) expression (COMMA formatOption)* SEMICOLON?
    | formatOnlyStatement
    | emptyStatement
    ;

// 空语句（仅分号或空行）
emptyStatement: SEMICOLON | AT;

// 表达式（按优先级从低到高）
expression
    : expression OR_OP expression          # OrExpression
    | expression AND_OP expression       # AndExpression
    | expression OR expression           # OrKeywordExpression
    | expression AND expression          # AndKeywordExpression
    | NOT_OP expression                  # NotExpression
    | NOT expression                     # NotKeywordExpression
    | expression (GT | LT | GE | LE | EQ | NE) expression  # ComparisonExpression
    | expression (PLUS | MINUS) expression                # AdditiveExpression
    | expression (MULT | DIV) expression                   # MultiplicativeExpression
    | (PLUS | MINUS) expression                             # UnaryExpression
    | primaryExpression                                    # PrimaryExpr
    ;

// 基本表达式
primaryExpression
    : literal                             # LiteralExpr
    | identifier                         # IdentifierExpr
    | klineData                          # KlineDataExpr
    | functionCall                       # FunctionCallExpr
    | crossPeriodRef                     # CrossPeriodRefExpr
    | LPAREN expression RPAREN           # ParenExpr
    ;

// 字面量
literal: integer | float | booleanLiteral | stringLiteral;

// 整数
integer: INTEGER | MINUS INTEGER;

// 浮点数
float: FLOAT | MINUS FLOAT;

// 布尔字面量
// 注意：使用 INTEGER token 而不是字面量 '1' 和 '0'，避免与 INTEGER 规则冲突
booleanLiteral: INTEGER | 'true' | 'false' | 'TRUE' | 'FALSE';

// 字符串字面量
stringLiteral: STRING;

// K线数据（特殊标识符）
// 注意：HOUR在词法分析时会被识别为PERIOD_HOUR，但在K线数据上下文中，我们将其作为HOUR使用
klineData: OPEN | CLOSE | HIGH | LOW | VOLUME | DATE | MINUTE | PERIOD_HOUR | BARPOS;

// 函数调用
functionCall
    : refFunction
    | barslastFunction
    | sumbarsFunction
    | hhvFunction
    | llvFunction
    | hhvbarsFunction
    | llvbarsFunction
    | countFunction
    | maxFunction
    | max1Function
    | minFunction
    | min1Function
    | ifFunction
    | absFunction
    | emaFunction
    | maFunction
    | smaFunction
    | stdFunction
    | modFunction
    | hvFunction
    | lvFunction
    | timeFunction
    | betweenFunction
    ;

// REF(X, N) - 引用N个周期前的值
refFunction: REF LPAREN expression COMMA expression RPAREN;

// BARSLAST(COND) - 上一次条件成立到当前的周期数
barslastFunction: BARSLAST LPAREN expression RPAREN;

// SUMBARS(X, A) - 求累加到指定值的周期数
sumbarsFunction: SUMBARS LPAREN expression COMMA expression RPAREN;

// HHV(X, N) - 求X在N个周期内的最高值
hhvFunction: HHV LPAREN expression COMMA expression RPAREN;

// LLV(X, N) - 求X在N个周期内的最低值
llvFunction: LLV LPAREN expression COMMA expression RPAREN;

// HHVBARS(X, N) - 求X在N个周期内的最高值位置
hhvbarsFunction: HHVBARS LPAREN expression COMMA expression RPAREN;

// LLVBARS(X, N) - 求X在N个周期内的最低值位置
llvbarsFunction: LLVBARS LPAREN expression COMMA expression RPAREN;

// COUNT(COND, N) - 统计N个周期内条件成立的次数
countFunction: COUNT LPAREN expression COMMA expression RPAREN;

// MAX(X1, X2, ...) - 求最大值（可变参数）
maxFunction: MAX LPAREN expression (COMMA expression)* RPAREN;

// MAX1(X1, X2, ..., X16) - 求最大值（最多16个参数）
max1Function: MAX1 LPAREN expression (COMMA expression)* RPAREN;

// MIN(X1, X2, ...) - 求最小值（可变参数）
// 注意：MIN在词法分析时会被识别为PERIOD_MIN（因为PERIOD_MIN规则在前），
// 但在函数调用上下文中，我们将其作为MIN函数处理
minFunction: PERIOD_MIN LPAREN expression (COMMA expression)* RPAREN;

// MIN1(X1, X2, ..., X16) - 求最小值（最多16个参数）
min1Function: MIN1 LPAREN expression (COMMA expression)* RPAREN;

// IF(COND, TRUE_VAL, FALSE_VAL) - 条件表达式
ifFunction: IF LPAREN expression COMMA expression COMMA expression RPAREN;

// ABS(X) - 绝对值
absFunction: ABS LPAREN expression RPAREN;

// EMA(X, N) - 指数移动平均
emaFunction: EMA LPAREN expression COMMA expression RPAREN;

// MA(X, N) - 移动平均
maFunction: MA LPAREN expression COMMA expression RPAREN;

// SMA(X, N, M) - 简单移动平均
smaFunction: SMA LPAREN expression COMMA expression COMMA expression RPAREN;

// STD(X, N) - 标准差
stdFunction: STD LPAREN expression COMMA expression RPAREN;

// MOD(X, Y) - 取模
modFunction: MOD LPAREN expression COMMA expression RPAREN;

// HV(X, N) - 最高值（简化版）
hvFunction: HV LPAREN expression COMMA expression RPAREN;

// LV(X, N) - 最低值（简化版）
lvFunction: LV LPAREN expression COMMA expression RPAREN;

// TIME - 时间函数（返回当前时间）
timeFunction: TIME (LPAREN RPAREN)?;

// BETWEEN(X, MIN, MAX) - 判断X是否在MIN和MAX之间
betweenFunction: BETWEEN LPAREN expression COMMA expression COMMA expression RPAREN;

// 跨周期引用
// 示例: HOURTREND.VARNAME
crossPeriodRef: identifier DOT identifier;

// 点号（用于跨周期引用）
DOT: '.';

// 格式化选项
formatOption
    : PRECIS0 | PRECIS1 | PRECIS2 | PRECIS3
    | NODRAW
    | COLORWHITE | COLORRED | COLORGREEN | COLORYELLOW
    | COLORLIGHTRED | COLORLIGHTGREEN | COLORCYAN | COLORBLUE | COLORPURPLE
    | LINETHICK1 | LINETHICK2 | LINETHICK3 | LINETHICK5
    | rgbFunction
    | DASH | DASHDOT | DASHDOTDOT | DOTSTYLE
    | VOLSTICK
    | ALIGN0 | ALIGN1 | ALIGN2 | ALIGN3 | ALIGN4
    | FONTSIZE10 | FONTSIZE12 | FONTSIZE14
    ;

// 标识符
identifier: IDENTIFIER;

// RGB 颜色函数
rgbFunction: RGB LPAREN expression COMMA expression COMMA expression RPAREN;

// 绘图语句（如DRAWLINE3等，这些语句通常以函数调用形式出现，但作为独立语句）
// 参数可以是表达式或格式化选项（如颜色常量）
drawStatement: drawFunction LPAREN drawArg (COMMA drawArg)* RPAREN (COMMA formatOption)* SEMICOLON?;

// 绘图函数参数：可以是表达式或格式化选项
drawArg: expression | formatOption;

drawFunction
    : DRAWLINE3
    | DRAWTEXT
    | DRAWTEXT_REL
    | DRAWCOLORKLINE
    | DRAWCOLOR
    | DRAWTITLE
    | DRAWHLINE
    ;

// 仅格式化选项组成的语句（例如 SETTLE, DOT, COLORYELLOW;）
// 这类语句以标识符开头，后跟逗号和格式化选项，用于输出变量并应用格式
// 注意：必须以 identifier COMMA formatOption 开头，避免与 variableAssignment 冲突
formatOnlyStatement
    : identifier COMMA formatOption (COMMA? formatOption)* SEMICOLON?
    ;

