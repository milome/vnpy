#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Full test: parse RICE1.txt and generate Python strategy code."""

from pathlib import Path
from mflang.grammar.parser import MFLangParserWrapper
from mflang.grammar.code_generator import StrategyCodeGenerator

def main():
    output_lines = []
    target = Path("mflang/mmodels/RICE1.txt")
    output_lines.append(f"=== Parsing RICE1.txt ===")
    output_lines.append(f"File: {target}")
    output_lines.append(f"Exists: {target.exists()}")
    
    # Step 1: Parse
    parser = MFLangParserWrapper()
    try:
        ast = parser.parse_file(str(target))
        output_lines.append(f"Parse: SUCCESS")
        output_lines.append(f"AST children: {len(ast.children) if ast and hasattr(ast, 'children') else 'N/A'}")
    except Exception as exc:
        output_lines.append(f"Parse: FAILED - {type(exc).__name__}: {exc}")
        ast = None
    
    if not ast:
        output_lines.append("Cannot proceed without AST")
        _write_output(output_lines)
        return
    
    # Step 2: Generate code
    output_lines.append(f"\n=== Generating Strategy Code ===")
    try:
        generator = StrategyCodeGenerator(ast, "RICE1Strategy", "mflang/mmodels")
        code = generator.generate(ast)
        output_lines.append(f"Generate: SUCCESS")
        output_lines.append(f"Code length: {len(code)} chars")
        output_lines.append(f"Code lines: {code.count(chr(10)) + 1}")
        
        # Save generated code
        output_path = Path("generated_rice1_strategy.py")
        output_path.write_text(code, encoding="utf-8")
        output_lines.append(f"Saved to: {output_path}")
        
        # Show first 50 lines
        lines = code.split('\n')
        output_lines.append(f"\n=== First 50 lines of generated code ===")
        for i, line in enumerate(lines[:50], 1):
            output_lines.append(f"{i:4d} | {line}")
        if len(lines) > 50:
            output_lines.append(f"... ({len(lines) - 50} more lines)")
            
    except Exception as exc:
        import traceback
        output_lines.append(f"Generate: FAILED - {type(exc).__name__}: {exc}")
        output_lines.append(f"Traceback:\n{traceback.format_exc()}")
    
    _write_output(output_lines)

def _write_output(lines):
    # Write to file
    with open("test_full_rice1_result.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    # Also print
    for line in lines:
        print(line)

if __name__ == "__main__":
    main()

