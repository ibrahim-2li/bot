"""
مراقب إعلانات قوائم الموردين - Etimad Supplier Announcements Monitor
يراقب إعلانات الموردين الجديدة ويرسل إشعار تليجرام
"""

import io
import os
import sys
import json
import re
import time
import requests
from pathlib import Path
from datetime import datetime

_LOG_DIR = Path(__file__).parent

# حماية من انقطاع الكونسول
try:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
    sys.stderr = open(os.devnull, "w", encoding="utf-8")
except:
    pass

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
except ImportError:
    exit(1)

try:
    from webdriver_manager.chrome import ChromeDriverManager
    USE_WEBDRIVER_MANAGER = True
except ImportError:
    USE_WEBDRIVER_MANAGER = False

# ============================================================
# الإعدادات
# ============================================================

TELEGRAM_BOT_TOKEN = "8688443116:AAE6SZ9ZIJncJiCCqDWRHBxW6Ti1sYnV1Ug"
TELEGRAM_CHAT_ID = "1795773958"

SUPPLIERS_URL = "https://tenders.etimad.sa/AnnouncementSuppliersTemplate/AllSupplierAnnouncementSupplierTemplates?PageNumber=1"

CHECK_INTERVAL = 10800  # 3 ساعات

SEEN_FILE = Path(__file__).parent / "seen_suppliers.json"
LOG_FILE = Path(__file__).parent / "suppliers_log.txt"

# ============================================================


def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except:
        pass
    try:
        print(line)
    except:
        pass


def load_seen():
    if SEEN_FILE.exists():
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(seen, f, ensure_ascii=False, indent=2)


def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    try:
        resp = requests.post(url, json=payload, timeout=15)
        if resp.status_code == 200:
            log("  -> تم إرسال الإشعار")
        else:
            log(f"  -> فشل الإشعار: {resp.status_code}")
    except Exception as e:
        log(f"  -> خطأ إرسال: {e}")


import tempfile
import shutil

def create_driver():
    options = Options()
    # استخدام الوضع الخفي الحديث والمستقر
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-extensions")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=ar")
    options.add_argument("--remote-debugging-pipe")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    )

    # إنشاء مجلد بيانات مؤقت ومستقل لكل جلسة لتفادي أخطاء الملفات المقفولة
    temp_dir = tempfile.mkdtemp(prefix="chrome_user_data_")
    options.add_argument(f"--user-data-dir={temp_dir}")

    # في Selenium 4 الحديث، Selenium Manager مدمج تلقائياً
    try:
        driver = webdriver.Chrome(options=options)
    except Exception:
        if USE_WEBDRIVER_MANAGER:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
        else:
            raise

    # حفظ المسار المؤقت على الـ driver لحذفه عند الإغلاق
    driver._temp_dir = temp_dir
    return driver



def parse_suppliers_from_text(page_text):
    lines = [l.strip() for l in page_text.split("\n") if l.strip()]
    announcements = []
    i = 0

    while i < len(lines):
        # البحث عن "الجهة الحكومية" كبداية إعلان
        if lines[i] != "الجهة الحكومية":
            i += 1
            continue

        # السطر قبله هو اسم الإعلان
        name = lines[i - 1] if i > 0 else ""
        if name in ("اعلانات قوائم الموردين", "searchبحث", "layers", "جميع اعلانات قوائم الموردين"):
            i += 1
            continue

        ann = {
            "name": name,
            "agency": "",
            "reference": "",
            "tender_type": "",
            "list_status": "",
            "list_type": "",
            "activity": "",
            "publish_date": "",
        }

        i += 1  # تجاوز "الجهة الحكومية"

        # قراءة الحقول المتتابعة
        block_end = min(i + 20, len(lines))
        while i < block_end:
            line = lines[i]

            if line == "الجهة الحكومية" and ann.get("reference"):
                break

            if not ann["agency"] and line != "الرقم المرجعي للقائمة" and not line.startswith("نوع"):
                if line != "التفاصيل" and line != name:
                    ann["agency"] = line
            elif line == "الرقم المرجعي للقائمة" and i + 1 < block_end:
                i += 1
                ann["reference"] = lines[i]
            elif line == "نوع المنافسة" and i + 1 < block_end:
                i += 1
                ann["tender_type"] = lines[i]
            elif line == "حالة القائمة" and i + 1 < block_end:
                i += 1
                ann["list_status"] = lines[i]
            elif line == "نوع القائمة" and i + 1 < block_end:
                i += 1
                ann["list_type"] = lines[i]
            elif line == "النشاط الرئيسي" and i + 1 < block_end:
                i += 1
                ann["activity"] = lines[i]
            elif line == "تاريخ النشر" and i + 1 < block_end:
                i += 1
                ann["publish_date"] = lines[i]
            elif line == "التفاصيل":
                i += 1
                break

            i += 1

        if ann["reference"]:
            ann["id"] = ann["reference"]
        elif ann["name"]:
            ann["id"] = ann["name"][:50]
        else:
            continue

        announcements.append(ann)

    return announcements


def extract_suppliers(driver):
    driver.get(SUPPLIERS_URL)
    time.sleep(10)

    body_text = driver.find_element(By.TAG_NAME, "body").text
    announcements = parse_suppliers_from_text(body_text)

    # ربط كل إعلان برابطه المباشر
    detail_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "التفاصيل")
    for link in detail_links:
        href = link.get_attribute("href")
        if not href or "DetailsForSuppliers" not in href:
            continue
        try:
            parent = link
            for _ in range(10):
                parent = parent.find_element(By.XPATH, "..")
                card_text = parent.text
                if "الرقم المرجعي للقائمة" in card_text:
                    for cline in card_text.split("\n"):
                        cline = cline.strip()
                        if re.match(r"^\d{8,15}$", cline):
                            for a in announcements:
                                if a.get("reference") == cline:
                                    a["detail_url"] = href
                            break
                    break
        except:
            continue

    return announcements


def format_notification(ann):
    msg = "<b>اشعار إعلان قائمة موردين جديد</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━\n\n"

    msg += f"<b>{ann['name']}</b>\n\n"

    if ann.get("agency"):
        msg += f"الجهة: {ann['agency']}\n"
    if ann.get("reference"):
        msg += f"الرقم المرجعي: <code>{ann['reference']}</code>\n"
    if ann.get("tender_type"):
        msg += f"نوع المنافسة: {ann['tender_type']}\n"
    if ann.get("list_type"):
        msg += f"نوع القائمة: {ann['list_type']}\n"
    if ann.get("list_status"):
        msg += f"حالة القائمة: {ann['list_status']}\n"
    if ann.get("activity"):
        msg += f"النشاط: {ann['activity']}\n"
    if ann.get("publish_date"):
        msg += f"تاريخ النشر: {ann['publish_date']}\n"

    detail_url = ann.get("detail_url", SUPPLIERS_URL)
    msg += f"\n<a href='{detail_url}'>فتح صفحة الإعلان</a>"
    return msg


def check_for_new():
    log("جاري الفحص...")

    seen = load_seen()
    driver = None

    try:
        driver = create_driver()
        announcements = extract_suppliers(driver)

        if not announcements:
            log("لم يتم العثور على إعلانات!")
            return

        log(f"عدد الإعلانات: {len(announcements)}")

        try:
            from db_config import save_supplier
            for ann in announcements:
                save_supplier(ann)
        except Exception as dbe:
            log(f"خطأ حفظ قاعدة البيانات: {dbe}")

        new_count = 0
        for ann in announcements:
            aid = ann["id"]
            if aid not in seen:
                new_count += 1
                seen[aid] = {
                    "name": ann["name"],
                    "reference": ann.get("reference", ""),
                    "found_at": datetime.now().isoformat()
                }
                msg = format_notification(ann)
                send_telegram_message(msg)
                log(f"  جديد: {ann.get('reference', '')} - {ann['name'][:60]}")

        if new_count == 0:
            log("لا جديد")
        else:
            log(f"{new_count} إعلان جديد!")

        save_seen(seen)

    except Exception as e:
        log(f"خطأ: {e}")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
            if hasattr(driver, "_temp_dir") and driver._temp_dir and os.path.exists(driver._temp_dir):
                shutil.rmtree(driver._temp_dir, ignore_errors=True)


def main():
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        log("يجب إعداد تليجرام أولاً!")
        return

    log("فحص إعلانات الموردين...")
    check_for_new()
    log("انتهى الفحص")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"توقف غير متوقع: {e}")
        import traceback
        with open(_LOG_DIR / "suppliers_crash.log", "a", encoding="utf-8") as f:
            traceback.print_exc(file=f)
