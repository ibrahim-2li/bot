"""
مراقب دعوات التأهيل - Etimad Qualifications Monitor
يراقب دعوات التأهيل الجديدة ويرسل إشعار تليجرام
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
except ImportError:
    exit(1)

try:
    from webdriver_manager.chrome import ChromeDriverManager
    USE_WEBDRIVER_MANAGER = True
except ImportError:
    USE_WEBDRIVER_MANAGER = False

# ============================================================
TELEGRAM_BOT_TOKEN = "8688443116:AAE6SZ9ZIJncJiCCqDWRHBxW6Ti1sYnV1Ug"
TELEGRAM_CHAT_ID = "1795773958"

QUALIFICATIONS_URL = "https://tenders.etimad.sa/Qualification/QualificationsForVisitor?PageNumber=1"
CHECK_INTERVAL = 10800  # 3 ساعات

SEEN_FILE = Path(__file__).parent / "seen_qualifications.json"
LOG_FILE = Path(__file__).parent / "qualifications_log.txt"
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


def clean_activity_value(value):
    """Remove an activity label and reject classification-table headers."""
    value = re.sub(r"^النشاط(?:\s+الأساسي)?\s*[:：-]?\s*", "", value).strip()
    value = value.strip(" :：&-—")
    # Qualification details render "النشاط & مجال التصنيف" as table headers.
    # It is not an activity value and must not be sent or saved.
    if not value or "مجال التصنيف" in value:
        return ""
    return value


def find_activity_value(lines, start_index, limit=8):
    """Find the first non-header activity value following an activity label."""
    end_index = min(start_index + limit + 1, len(lines))
    for index in range(start_index + 1, end_index):
        raw_value = lines[index]
        # We have reached another details field, so this qualification has no
        # activity value in the current page representation.
        if raw_value.startswith(("الرقم المرجعي", "تاريخ", "آخر موعد", "الجهة", "التفاصيل")):
            return ""
        value = clean_activity_value(raw_value)
        if value:
            return value
    return ""


def parse_qualifications_from_text(page_text):
    lines = [l.strip() for l in page_text.split("\n") if l.strip()]
    qualifications = []
    i = 0

    while i < len(lines):
        match = re.match(r"تاريخ النشر\s*:\s*(\d{4}-\d{2}-\d{2})", lines[i])
        if not match:
            i += 1
            continue

        qual = {
            "publish_date": match.group(1),
            "type": "",
            "name": "",
            "agency": "",
            "activity": "",
            "reference": "",
            "inquiry_deadline": "",
            "submission_deadline": "",
            "evaluation_date": "",
        }

        i += 1
        # نوع التأهيل
        if i < len(lines) and "تأهيل" in lines[i]:
            qual["type"] = lines[i]
            i += 1

        # اسم الدعوة
        if i < len(lines) and lines[i] != "التفاصيل":
            qual["name"] = lines[i]
            i += 1

        # الجهة الحكومية
        if i < len(lines) and lines[i] != "التفاصيل":
            qual["agency"] = lines[i]
            i += 1

        # باقي التفاصيل
        block_end = min(i + 12, len(lines))
        while i < block_end:
            line = lines[i]

            if re.match(r"تاريخ النشر\s*:", line):
                break

            if line.startswith("النشاط"):
                # The list page may show the value either beside the label or
                # on the next line, depending on the current Etimad layout.
                activity = clean_activity_value(line)
                if not activity and i + 1 < block_end:
                    activity = find_activity_value(lines[:block_end], i)
                qual["activity"] = activity
            elif "الرقم المرجعي" in line:
                qual["reference"] = re.sub(r".*التأهيل\s*", "", line).strip()
            elif "إستلام الإستفسارات" in line:
                qual["inquiry_deadline"] = re.sub(r".*إستفسارات\s*", "", line).strip()
            elif "تقديم وثائق التأهيل" in line:
                qual["submission_deadline"] = re.sub(r".*التأهيل\s*", "", line).strip()
            elif "تقييم وثائق" in line:
                qual["evaluation_date"] = re.sub(r".*التأهيل\s*", "", line).strip()

            i += 1

        if qual["reference"]:
            qual["id"] = qual["reference"]
        elif qual["name"]:
            qual["id"] = qual["name"][:50]
        else:
            continue

        qualifications.append(qual)

    return qualifications


def extract_activity_from_text(page_text):
    """Return the activity shown on an Etimad qualification details page."""
    lines = [line.strip() for line in page_text.split("\n") if line.strip()]
    for index, line in enumerate(lines):
        if not line.startswith("النشاط"):
            continue

        activity = clean_activity_value(line)
        if activity:
            return activity

        activity = find_activity_value(lines, index)
        if activity:
            return activity
    return ""


def enrich_activities_from_details(driver, qualifications):
    """Load each available details page and add its activity to the record."""
    for qual in qualifications:
        detail_url = qual.get("detail_url")
        if not detail_url or qual.get("activity"):
            continue
        try:
            driver.get(detail_url)
            time.sleep(2)
            qual["activity"] = extract_activity_from_text(
                driver.find_element(By.TAG_NAME, "body").text
            )
        except Exception as exc:
            # A missing/unavailable details page must not prevent the rest of
            # the qualification list from being saved or announced.
            log(f"تعذر استخراج النشاط لـ {qual.get('reference', qual.get('name', ''))}: {exc}")


def extract_qualifications(driver):
    driver.get(QUALIFICATIONS_URL)
    time.sleep(10)

    body_text = driver.find_element(By.TAG_NAME, "body").text
    qualifications = parse_qualifications_from_text(body_text)

    detail_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "التفاصيل")
    for link in detail_links:
        href = link.get_attribute("href")
        if not href or "PrequalificationVisitorDetails" not in href:
            continue
        try:
            parent = link
            for _ in range(10):
                parent = parent.find_element(By.XPATH, "..")
                card_text = parent.text
                if "الرقم المرجعي" in card_text:
                    for cline in card_text.split("\n"):
                        ref_match = re.search(r"(\d{10,15})", cline)
                        if ref_match:
                            ref = ref_match.group(1)
                            for q in qualifications:
                                if q.get("reference") == ref:
                                    q["detail_url"] = href
                            break
                    break
        except:
            continue

    enrich_activities_from_details(driver, qualifications)
    return qualifications


def format_notification(qual):
    msg = "<b>اشعار دعوة تأهيل جديدة</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━\n\n"

    msg += f"<b>{qual['name']}</b>\n\n"

    if qual.get("agency"):
        msg += f"الجهة: {qual['agency']}\n"
    if qual.get("type"):
        msg += f"النوع: {qual['type']}\n"
    if qual.get("reference"):
        msg += f"الرقم المرجعي: <code>{qual['reference']}</code>\n"
    if qual.get("activity"):
        msg += f"النشاط: {qual['activity']}\n"
    if qual.get("publish_date"):
        msg += f"تاريخ النشر: {qual['publish_date']}\n"
    if qual.get("submission_deadline"):
        msg += f"آخر موعد تقديم الوثائق: {qual['submission_deadline']}\n"
    if qual.get("evaluation_date"):
        msg += f"تاريخ التقييم: {qual['evaluation_date']}\n"

    detail_url = qual.get("detail_url", QUALIFICATIONS_URL)
    msg += f"\n<a href='{detail_url}'>فتح صفحة دعوة التأهيل</a>"
    return msg


def check_for_new():
    log("جاري الفحص...")

    seen = load_seen()
    driver = None

    try:
        driver = create_driver()
        qualifications = extract_qualifications(driver)

        if not qualifications:
            log("لم يتم العثور على دعوات تأهيل!")
            return

        log(f"عدد دعوات التأهيل: {len(qualifications)}")

        try:
            from db_config import save_qualification
            for qual in qualifications:
                save_qualification(qual)
        except Exception as dbe:
            log(f"خطأ حفظ قاعدة البيانات: {dbe}")

        new_count = 0
        for qual in qualifications:
            qid = qual["id"]
            if qid not in seen:
                new_count += 1
                seen[qid] = {
                    "name": qual["name"],
                    "reference": qual.get("reference", ""),
                    "found_at": datetime.now().isoformat()
                }
                msg = format_notification(qual)
                send_telegram_message(msg)
                log(f"  جديد: {qual.get('reference', '')} - {qual['name'][:60]}")

        if new_count == 0:
            log("لا جديد")
        else:
            log(f"{new_count} دعوة تأهيل جديدة!")

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

    log("فحص دعوات التأهيل...")
    check_for_new()
    log("انتهى الفحص")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"توقف غير متوقع: {e}")
        import traceback
        with open(_LOG_DIR / "qualifications_crash.log", "a", encoding="utf-8") as f:
            traceback.print_exc(file=f)
