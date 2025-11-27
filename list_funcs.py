import re
from pathlib import Path

text = Path("mflang/mmodels/RICE1_DAY").read_text(encoding="utf-8")
funcs = sorted(set(re.findall(r"[A-Z][A-Z0-9_]+(?=\()", text)))
for name in funcs:
    print(name)

