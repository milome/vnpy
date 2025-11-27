#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utility script to parse a single MFLang model file and report the result.
Usage:
    python scripts/parse_model.py path/to/model
"""

import sys
from pathlib import Path

from mflang.grammar.parser import MFLangParserWrapper


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/parse_model.py <model_path>", file=sys.stderr)
        return 1

    target = Path(sys.argv[1])
    if not target.exists():
        print(f"[X] 文件不存在: {target}")
        return 1

    parser = MFLangParserWrapper()
    try:
        ast = parser.parse_file(str(target))
        parsed = bool(ast)
    except Exception as exc:  # pragma: no cover - debug helper
        msg = str(exc)
        try:
            msg_display = msg.encode("unicode_escape").decode("ascii")
        except Exception:
            msg_display = msg
        print(f"[X] 解析失败: {type(exc).__name__}: {msg_display}")
        if parser._last_lexer_errors:
            print(f"  词法错误({len(parser._last_lexer_errors)}):")
            for line, col, msg in parser._last_lexer_errors[:10]:
                safe = msg.encode("unicode_escape").decode("ascii")
                print(f"    line {line}:{col} {safe}")
            if len(parser._last_lexer_errors) > 10:
                print("    ...")
        if parser._last_parser_errors:
            print(f"  语法错误({len(parser._last_parser_errors)}):")
            for line, col, msg in parser._last_parser_errors[:10]:
                safe = msg.encode("unicode_escape").decode("ascii")
                print(f"    line {line}:{col} {safe}")
            if len(parser._last_parser_errors) > 10:
                print("    ...")
        return 2

    print(f"[OK] 解析成功: {target} -> {parsed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


