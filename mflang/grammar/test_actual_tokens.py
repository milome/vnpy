from MFLangLexer import MFLangLexer
from MFLangParser import MFLangParser
from antlr4 import InputStream, CommonTokenStream

# 测试实际的 token 识别
text = "BETWEEN(TIME, 0915, 1130) > 0"
stream = InputStream(text)
lexer = MFLangLexer(stream)
tokens = CommonTokenStream(lexer)
tokens.fill()

print("Token stream:")
for i, token in enumerate(tokens.tokens):
    if token.type != -1:  # 不是 EOF
        token_name = lexer.symbolicNames[token.type] if token.type < len(lexer.symbolicNames) else "UNKNOWN"
        print(f"  Token {i}: '{token.text}' -> Type: {token.type}, Name: {token_name}")

