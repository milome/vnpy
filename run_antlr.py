#!/usr/bin/env python3
"""Run ANTLR to generate parser files."""
import subprocess
import sys
from pathlib import Path

java_exe = r"D:\Program Files\Java\jdk-25\bin\java.exe"
antlr_jar = r"d:\Dev\vnpy\jars\antlr-4.13.2-complete.jar"
grammar_file = r"mflang\grammar\MFLang.g4"

# Write results to file
output_file = Path("antlr_result.txt")

cmd = [java_exe, "-jar", antlr_jar, "-Dlanguage=Python3", "-visitor", grammar_file]
lines = [f"Running: {' '.join(cmd)}"]
result = subprocess.run(cmd, capture_output=True, text=True)
lines.append(f"Return code: {result.returncode}")
lines.append(f"stdout: {result.stdout}")
lines.append(f"stderr: {result.stderr}")

output_file.write_text("\n".join(lines), encoding="utf-8")
for line in lines:
    print(line)
sys.exit(result.returncode)

