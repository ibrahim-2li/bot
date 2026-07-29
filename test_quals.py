import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

with open(r"C:\0MONTAR\qualifications_page.txt", "r", encoding="utf-8") as f:
    body_text = f.read()

import importlib.util
spec = importlib.util.spec_from_file_location("m", r"C:\0MONTAR\qualifications_monitor.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

quals = mod.parse_qualifications_from_text(body_text)

print(f"Total: {len(quals)} qualifications\n")
for i, q in enumerate(quals):
    print(f"{i+1}. [{q['type']}] {q['name'][:65]}")
    print(f"   Agency: {q['agency'][:60]}")
    print(f"   Ref: {q['reference']} | Deadline: {q['submission_deadline']}")
    print()
