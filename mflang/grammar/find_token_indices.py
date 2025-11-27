from MFLangLexer import MFLangLexer

names = MFLangLexer.symbolicNames
print('Finding TIME and BETWEEN in array:')
for i, name in enumerate(names):
    if name in ['TIME', 'BETWEEN', 'PRECIS3', 'NODRAW', 'LV']:
        print(f'  Index {i}: {name}')

print(f'\nToken constants:')
print(f'  TIME = {MFLangLexer.TIME}')
print(f'  BETWEEN = {MFLangLexer.BETWEEN}')
print(f'  PRECIS3 = {MFLangLexer.PRECIS3}')
print(f'  NODRAW = {MFLangLexer.NODRAW}')

print(f'\nActual symbolicNames values:')
print(f'  symbolicNames[{MFLangLexer.TIME}] = {names[MFLangLexer.TIME]}')
print(f'  symbolicNames[{MFLangLexer.BETWEEN}] = {names[MFLangLexer.BETWEEN]}')

