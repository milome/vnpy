from MFLangLexer import MFLangLexer
from antlr4 import InputStream

# 测试 BETWEEN 和 TIME 的 token ID
test_cases = ['BETWEEN', 'TIME', 'MIN']

for text in test_cases:
    stream = InputStream(text)
    lexer = MFLangLexer(stream)
    token = lexer.nextToken()
    token_name = lexer.symbolicNames[token.type] if token.type < len(lexer.symbolicNames) else "UNKNOWN"
    print(f"'{text}' -> Token ID: {token.type}, Name: {token_name}")
    print(f"  SymbolicNames[{token.type}]: {lexer.symbolicNames[token.type] if token.type < len(lexer.symbolicNames) else 'OUT_OF_RANGE'}")
    print(f"  Token constants: TIME={MFLangLexer.TIME}, BETWEEN={MFLangLexer.BETWEEN}")

