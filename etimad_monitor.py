"""
مراقب مناقصات اعتماد - Etimad Tenders Monitor
يراقب المناقصات الجديدة ويرسل إشعار تليجرام عند نزول مناقصة جديدة
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
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
except ImportError:
    print("pip install selenium")
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

ETIMAD_URL = "https://tenders.etimad.sa/Tender/AllTendersForVisitor?PageNumber=1&PageSize=24"

CHECK_INTERVAL = 10800  # ثانية (10800 = 3 ساعات)

SEEN_TENDERS_FILE = Path(__file__).parent / "seen_tenders.json"
LOG_FILE = Path(__file__).parent / "monitor_log.txt"

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


def load_seen_tenders():
    if SEEN_TENDERS_FILE.exists():
        with open(SEEN_TENDERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_seen_tenders(seen):
    with open(SEEN_TENDERS_FILE, "w", encoding="utf-8") as f:
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



def parse_tenders_from_text(page_text):
    """
    يستخرج المناقصات من نص الصفحة بناءً على النمط المتكرر:
    تاريخ النشر :YYYY-MM-DD
    نوع المنافسة
    اسم المنافسة
    الجهة الحكومية
    التفاصيل
    النشاط الأساسي ...
    المدة المتبقية
    الرقم المرجعي ...
    آخر موعد لإستلام الإستفسارات ...
    آخر موعد لتقديم العروض ...
    تاريخ ووقت فتح العروض ...
    قيمة وثائق المنافسة
    السعر
    """
    lines = [l.strip() for l in page_text.split("\n") if l.strip()]
    tenders = []
    i = 0

    while i < len(lines):
        # البحث عن بداية مناقصة: "تاريخ النشر :YYYY-MM-DD"
        match = re.match(r"تاريخ النشر\s*:\s*(\d{4}-\d{2}-\d{2})", lines[i])
        if not match:
            i += 1
            continue

        tender = {
            "publish_date": match.group(1),
            "type": "",
            "name": "",
            "agency": "",
            "activity": "",
            "reference": "",
            "inquiry_deadline": "",
            "offer_deadline": "",
            "opening_date": "",
            "doc_price": "",
        }

        i += 1
        # نوع المنافسة (السطر التالي مباشرة)
        tender_types = ["منافسة", "شراء مباشر", "إتفاقية إطارية", "مسابقة"]
        if i < len(lines) and any(t in lines[i] for t in tender_types):
            tender["type"] = lines[i]
            i += 1

        # اسم المنافسة (سطر أو أكثر حتى نصل للجهة)
        name_parts = []
        while i < len(lines) and "التفاصيل" not in lines[i]:
            if lines[i].startswith("النشاط") or lines[i].startswith("الرقم المرجعي"):
                break
            name_parts.append(lines[i])
            i += 1

        if len(name_parts) >= 2:
            tender["name"] = name_parts[0]
            tender["agency"] = name_parts[1]
        elif name_parts:
            tender["name"] = name_parts[0]

        # باقي التفاصيل
        block_end = min(i + 15, len(lines))
        while i < block_end:
            line = lines[i]

            if line.startswith("النشاط الأساسي"):
                tender["activity"] = line.replace("النشاط الأساسي", "").strip()
            elif line.startswith("الرقم المرجعي"):
                tender["reference"] = line.replace("الرقم المرجعي", "").strip()
            elif "إستلام الإستفسارات" in line:
                tender["inquiry_deadline"] = re.sub(r".*إستفسارات\s*", "", line).strip()
            elif "تقديم العروض" in line and "آخر" in line:
                tender["offer_deadline"] = re.sub(r".*العروض\s*", "", line).strip()
            elif "فتح العروض" in line:
                tender["opening_date"] = re.sub(r".*العروض\s*", "", line).strip()
            elif line.startswith("قيمة وثائق"):
                if i + 1 < len(lines) and lines[i + 1].replace(",", "").isdigit():
                    tender["doc_price"] = lines[i + 1]
                    i += 1

            # وصلنا لبداية مناقصة جديدة
            if i + 1 < block_end and re.match(r"تاريخ النشر\s*:", lines[i]):
                break

            i += 1

        if tender["reference"]:
            tender["id"] = tender["reference"]
        elif tender["name"]:
            tender["id"] = tender["name"][:50]
        else:
            i += 1
            continue

        tenders.append(tender)

    return tenders


def extract_tenders(driver):
    driver.get(ETIMAD_URL)
    time.sleep(10)

    body_text = driver.find_element(By.TAG_NAME, "body").text
    tenders = parse_tenders_from_text(body_text)

    # ربط كل مناقصة برابطها المباشر
    detail_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "التفاصيل")
    for link in detail_links:
        href = link.get_attribute("href")
        if not href or "DetailsForVisitor" not in href:
            continue
        try:
            parent = link
            for _ in range(10):
                parent = parent.find_element(By.XPATH, "..")
                card_text = parent.text
                if "الرقم المرجعي" in card_text:
                    for line in card_text.split("\n"):
                        if "الرقم المرجعي" in line:
                            ref = line.replace("الرقم المرجعي", "").strip()
                            for t in tenders:
                                if t.get("reference") == ref:
                                    t["detail_url"] = href
                            break
                    break
        except:
            continue

    return tenders


def format_notification(tender):
    msg = "<b>اشعار مناقصة في مجال انشطتك</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━\n\n"

    msg += f"<b>{tender['name']}</b>\n\n"

    if tender.get("agency"):
        msg += f"الجهة: {tender['agency']}\n"
    if tender.get("type"):
        msg += f"النوع: {tender['type']}\n"
    if tender.get("reference"):
        msg += f"الرقم المرجعي: <code>{tender['reference']}</code>\n"
    if tender.get("activity"):
        msg += f"النشاط: {tender['activity']}\n"
    if tender.get("publish_date"):
        msg += f"تاريخ النشر: {tender['publish_date']}\n"
    if tender.get("offer_deadline"):
        msg += f"آخر موعد تقديم: {tender['offer_deadline']}\n"
    if tender.get("opening_date"):
        msg += f"فتح العروض: {tender['opening_date']}\n"
    if tender.get("doc_price"):
        msg += f"قيمة الوثائق: {tender['doc_price']} ريال\n"

    detail_url = tender.get("detail_url", "https://tenders.etimad.sa/Tender/AllTendersForVisitor")
    msg += f"\n<a href='{detail_url}'>فتح صفحة المنافسة</a>"
    return msg


def check_for_new_tenders():
    log("جاري الفحص...")

    seen = load_seen_tenders()
    driver = None

    try:
        driver = create_driver()
        tenders = extract_tenders(driver)

        if not tenders:
            log("لم يتم العثور على مناقصات!")
            return

        log(f"عدد المناقصات: {len(tenders)}")

        try:
            from db_config import save_etimad_tender
            for tender in tenders:
                save_etimad_tender(tender)
        except Exception as dbe:
            log(f"خطأ حفظ قاعدة البيانات: {dbe}")

        new_count = 0
        for tender in tenders:
            tid = tender["id"]
            if tid not in seen:
                new_count += 1
                seen[tid] = {
                    "name": tender["name"],
                    "reference": tender.get("reference", ""),
                    "found_at": datetime.now().isoformat()
                }
                msg = format_notification(tender)
                send_telegram_message(msg)
                log(f"  جديد: {tender.get('reference', '')} - {tender['name'][:60]}")

        if new_count == 0:
            log("لا جديد")
        else:
            log(f"{new_count} مناقصة جديدة!")

        save_seen_tenders(seen)

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

    log("فحص المناقصات...")
    check_for_new_tenders()
    log("انتهى الفحص")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"توقف غير متوقع: {e}")
        import traceback
        with open(_LOG_DIR / "crash.log", "a", encoding="utf-8") as f:
            traceback.print_exc(file=f)
