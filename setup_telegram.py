"""
أداة إعداد بوت تليجرام
شغّل هذا الملف لإعداد الإشعارات خطوة بخطوة
"""

import requests
import sys
import re
from pathlib import Path


def main():
    print("\n" + "=" * 50)
    print("  إعداد بوت تليجرام")
    print("=" * 50)

    token = None
    chat_id = None

    if len(sys.argv) >= 3:
        token = sys.argv[1].strip()
        chat_id = sys.argv[2].strip()

    if not token:
        print("""
 الخطوة 1: إنشاء بوت تليجرام
 ────────────────────────────
 1. افتح تليجرام وابحث عن @BotFather
 2. أرسل له: /newbot
 3. اختر اسم للبوت (مثلاً: مراقب اعتماد)
 4. اختر username (مثلاً: etimad_watcher_bot)
 5. سيعطيك توكن مثل: 123456789:ABCdefGHI...
""")
        token = input("الصق التوكن هنا: ").strip()

    if not token or ":" not in token:
        print("[X] التوكن غير صحيح!")
        sys.exit(1)

    try:
        resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
        if resp.status_code != 200:
            print("[X] التوكن غير صالح!")
            sys.exit(1)
        bot_name = resp.json()["result"]["username"]
        print(f"[OK] البوت: @{bot_name}")
    except Exception as e:
        print(f"[X] خطأ في الاتصال بالتوكن: {e}")
        sys.exit(1)

    if not chat_id:
        print("""
 الخطوة 2: الحصول على Chat ID
 ────────────────────────────
 1. افتح المحادثة مع البوت في تليجرام
 2. أرسل له: /start
 3. ارجع هنا واضغط Enter
""")

        input("اضغط Enter بعد إرسال /start للبوت... ")

        resp = requests.get(f"https://api.telegram.org/bot{token}/getUpdates", timeout=10)
        if resp.status_code == 200 and resp.json().get("result"):
            # البحث عن آخر chat id من الرسائل
            for result in reversed(resp.json()["result"]):
                if "message" in result and "chat" in result["message"]:
                    chat_id = str(result["message"]["chat"]["id"])
                    break
            if chat_id:
                print(f"[OK] Chat ID: {chat_id}")

        if not chat_id:
            print("[!] لم أجد رسائل تلقائياً")
            chat_id = input("أدخل Chat ID يدوياً: ").strip()

    if not chat_id:
        print("[X] فشل الحصول على Chat ID!")
        sys.exit(1)

    # رسالة تجريبية
    test_resp = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": "تم إعداد مراقب مناقصات اعتماد بنجاح!\nستصلك إشعارات عند نزول مناقصات جديدة."},
        timeout=10
    )
    if test_resp.status_code == 200:
        print("[OK] تم إرسال رسالة تجريبية!")
    else:
        print(f"[X] فشل إرسال الرسالة: {test_resp.text}")
        sys.exit(1)

    # تحديث جميع ملفات المراقبة
    target_files = [
        "etimad_monitor.py",
        "future_monitor.py",
        "qualifications_monitor.py",
        "suppliers_monitor.py",
        "send_test.py",
    ]
    base_dir = Path(__file__).parent

    updated_count = 0
    for filename in target_files:
        file_path = base_dir / filename
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # استبدال التوكن
                content = re.sub(r'TELEGRAM_BOT_TOKEN\s*=\s*"[^"]*"', f'TELEGRAM_BOT_TOKEN = "{token}"', content)
                content = re.sub(r'token\s*=\s*"[^"]*"', f'token = "{token}"', content)

                # استبدال Chat ID
                content = re.sub(r'TELEGRAM_CHAT_ID\s*=\s*"[^"]*"', f'TELEGRAM_CHAT_ID = "{chat_id}"', content)
                content = re.sub(r'chat_id\s*=\s*"[^"]*"', f'chat_id = "{chat_id}"', content)

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                updated_count += 1
                print(f"[OK] تم تحديث: {filename}")
            except Exception as e:
                print(f"[!] خطأ عند تحديث {filename}: {e}")

    print(f"\n[OK] تم حفظ الإعدادات في {updated_count} ملفات!")
    print("\nاختبر البوت الآن بالمرور على:")
    print(f"  {sys.executable} send_test.py")


if __name__ == "__main__":
    main()
