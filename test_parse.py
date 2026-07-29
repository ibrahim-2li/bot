import sys, json, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

with open(r"C:\0MONTAR\page_text.txt", "r", encoding="utf-8") as f:
    body_text = f.read()

import importlib.util
spec = importlib.util.spec_from_file_location("m", r"C:\0MONTAR\etimad_monitor.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

tenders = mod.parse_tenders_from_text(body_text)

print(f"Total: {len(tenders)} tenders")
print()
for i, t in enumerate(tenders):
    print(f"{i+1}. [{t['type']}]")
    print(f"   Name: {t['name'][:70]}")
    print(f"   Agency: {t['agency'][:70]}")
    print(f"   Ref: {t['reference']}")
    print()
