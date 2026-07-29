import traceback, sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

try:
    from etimad_monitor import main
    main()
except Exception as e:
    with open(BASE_DIR / "crash.log", "a", encoding="utf-8") as f:
        f.write(f"CRASH: {e}\n")
        traceback.print_exc(file=f)
