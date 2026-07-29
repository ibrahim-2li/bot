"""
تشغيل جميع مراقبي اعتماد (المناقصات العامة، المشاريع المستقبلية، دعوات التأهيل، الموردين)
"""
import sys
import time
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).parent
PYTHON_EXE = sys.executable

MONITORS = [
    ("etimad_monitor.py", "مراقب المناقصات العامة"),
    ("future_monitor.py", "مراقب المشاريع المستقبلية"),
    ("qualifications_monitor.py", "مراقب دعوات التأهيل"),
    ("suppliers_monitor.py", "مراقب الموردين"),
]


def run_all():
    print("=" * 60)
    print("  بدء فحص جميع أقسام منصة اعتماد")
    print("=" * 60)

    for script, name in MONITORS:
        script_path = BASE_DIR / script
        if script_path.exists():
            print(f"\n[+] تشغيل: {name} ({script})...")
            try:
                res = subprocess.run(
                    [PYTHON_EXE, str(script_path)],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                )
                if res.stdout and res.stdout.strip():
                    print(f"   {res.stdout.strip()}")
                if res.stderr and res.stderr.strip():
                    print(f"   [تنبيه] {res.stderr.strip()}")
                print(f"[OK] اكتمل فحص {name}")
            except Exception as e:
                print(f"[X] خطأ عند تشغيل {script}: {e}")

    print("\n" + "=" * 60)
    print("[OK] تم فحص وإرسال الإشعارات لجميع الأقسام بنجاح!")
    print("=" * 60)


if __name__ == "__main__":
    loop_mode = "--loop" in sys.argv
    if loop_mode:
        interval = 10800  # 3 ساعات
        print(f"سيعمل المراقب بشكل مستمر كل {interval // 3600} ساعات...")
        while True:
            try:
                run_all()
            except Exception as e:
                print(f"خطأ في الدورة: {e}")
            time.sleep(interval)
    else:
        run_all()
