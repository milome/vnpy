#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quick test script to parse RICE1_DAY model."""

from pathlib import Path
from mflang.grammar.parser import MFLangParserWrapper

def main():
    output_lines = []
    target = Path("mflang/mmodels/RICE1_DAY")
    output_lines.append(f"Parsing: {target}")
    output_lines.append(f"Exists: {target.exists()}")
    
    parser = MFLangParserWrapper()
    try:
        ast = parser.parse_file(str(target))
        output_lines.append(f"AST: {ast}")
        output_lines.append(f"Parsed: {bool(ast)}")
        if ast:
            output_lines.append(f"AST type: {type(ast)}")
            output_lines.append(f"Statements: {len(ast.statements) if hasattr(ast, 'statements') else 'N/A'}")
    except Exception as exc:
        output_lines.append(f"Exception: {type(exc).__name__}: {exc}")
        if parser._last_lexer_errors:
            output_lines.append(f"Lexer errors: {len(parser._last_lexer_errors)}")
        if parser._last_parser_errors:
            output_lines.append(f"Parser errors: {len(parser._last_parser_errors)}")
            for line, col, msg in parser._last_parser_errors[:10]:
                output_lines.append(f"  line {line}:{col} {msg}")
    
    # Write to file
    with open("test_parse_result.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))
    
    # Also print
    for line in output_lines:
        print(line)

if __name__ == "__main__":
    main()

