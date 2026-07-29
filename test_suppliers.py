import io, sys, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

with open(r"C:\0MONTAR\suppliers_page.txt", "r", encoding="utf-8") as f:
    body_text = f.read()

import importlib.util
spec = importlib.util.spec_from_file_location("m", r"C:\0MONTAR\suppliers_monitor.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

announcements = mod.parse_suppliers_from_text(body_text)

print(f"Total: {len(announcements)} announcements\n")
for i, a in enumerate(announcements):
    print(f"{i+1}. {a['name'][:60]}")
    print(f"   Agency: {a['agency'][:60]}")
    print(f"   Ref: {a['reference']} | Type: {a['tender_type']} | Activity: {a['activity'][:40]}")
    print()
