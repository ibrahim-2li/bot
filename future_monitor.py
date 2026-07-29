"""
مراقب مشاريع المنافسات المستقبلية - Etimad Future Projects Monitor
يراقب المشاريع الجديدة عبر تتبع آخر صفحة وأعلى رقم مشروع
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

FUTURE_URL = "https://tenders.etimad.sa/Preplanning/PrePlaningForVisitor"
CHECK_INTERVAL = 10800  # 3 ساعات

SEEN_FILE = Path(__file__).parent / "seen_future.json"
LOG_FILE = Path(__file__).parent / "future_log.txt"
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
    return {"project_ids": [], "last_page": 0}


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


def create_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=ar")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    )
    if USE_WEBDRIVER_MANAGER:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    else:
        driver = webdriver.Chrome(options=options)
    return driver


def parse_project_row(row_text):
    """يستخرج بيانات مشروع من سطر الجدول"""
    # النمط: رقم_المشروع اسم_المشروع الجهة الربع السنة مكان طبيعة وصف حالة أيام شهور سنين
    match = re.match(r"^(\d+)\s+(.+)$", row_text.strip())
    if not match:
        return None

    project_id = match.group(1)
    rest = match.group(2)

    # استخراج الحقول من باقي النص
    project = {
        "id": project_id,
        "raw": rest,
        "name": "",
        "agency": "",
        "quarter": "",
        "year": "",
        "status": "",
    }

    # البحث عن السنة (4 أرقام بين 2020-2030)
    year_match = re.search(r"\b(20[2-3]\d)\b", rest)
    if year_match:
        project["year"] = year_match.group(1)

    # البحث عن الربع
    quarter_match = re.search(r"(الربع\s+\w+)", rest)
    if quarter_match:
        project["quarter"] = quarter_match.group(1)

    # البحث عن الحالة
    if "معتمد" in rest:
        project["status"] = "معتمد"

    # استخراج الاسم والجهة
    # الاسم يأتي قبل الجهة، والجهة قبل الربع
    if quarter_match:
        before_quarter = rest[:quarter_match.start()].strip()
        # محاولة تقسيم الاسم والجهة
        # الجهة عادة تحتوي على كلمات مثل: جامعة، وزارة، هيئة، أمانة، بلدية
        agency_patterns = [
            r"(جامعة\s+.+?)(?=\s+الربع)",
            r"(وزارة\s+.+?)(?=\s+الربع)",
            r"(هيئة\s+.+?)(?=\s+الربع)",
            r"(أمانة\s+.+?)(?=\s+الربع)",
            r"(بلدية\s+.+?)(?=\s+الربع)",
            r"(مستشفى\s+.+?)(?=\s+الربع)",
        ]
        for pat in agency_patterns:
            ag_match = re.search(pat, rest)
            if ag_match:
                project["agency"] = ag_match.group(1).strip()
                # الاسم هو ما قبل الجهة
                agency_start = rest.index(project["agency"])
                project["name"] = rest[:agency_start].strip()
                break

        if not project["name"]:
            project["name"] = before_quarter[:80]

    if not project["name"]:
        project["name"] = rest[:80]

    return project


def extract_last_page_projects(driver):
    """يفتح الصفحة ويضغط »» للذهاب لآخر صفحة ويستخرج المشاريع"""
    driver.get(FUTURE_URL)
    time.sleep(10)

    # الضغط على »» للذهاب لآخر صفحة
    driver.execute_script("""
        var allElements = document.querySelectorAll('button, li, a, span');
        for (var i = 0; i < allElements.length; i++) {
            if (allElements[i].textContent.trim() === '»»' && allElements[i].tagName === 'BUTTON') {
                allElements[i].click();
                break;
            }
        }
    """)
    time.sleep(8)

    body_text = driver.find_element(By.TAG_NAME, "body").text
    lines = [l.strip() for l in body_text.split("\n") if l.strip()]

    # استخراج رقم آخر صفحة
    last_page = 0
    for line in lines:
        if line.isdigit():
            num = int(line)
            if num > 100:
                last_page = max(last_page, num)

    # استخراج المشاريع من الجدول
    projects = []
    in_table = False
    for line in lines:
        if "# إسم المشروع" in line or "# اسم المشروع" in line:
            in_table = True
            continue
        if line == "««":
            break
        if in_table:
            project = parse_project_row(line)
            if project:
                projects.append(project)

    return projects, last_page


def format_notification(project):
    msg = "<b>اشعار مشروع منافسة مستقبلية جديد</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━\n\n"

    msg += f"<b>{project['name'][:100]}</b>\n\n"

    msg += f"رقم المشروع: <code>{project['id']}</code>\n"
    if project.get("agency"):
        msg += f"الجهة: {project['agency']}\n"
    if project.get("quarter"):
        msg += f"الربع: {project['quarter']}\n"
    if project.get("year"):
        msg += f"السنة: {project['year']}\n"
    if project.get("status"):
        msg += f"الحالة: {project['status']}\n"

    msg += f"\n<a href='{FUTURE_URL}'>فتح صفحة المشاريع المستقبلية</a>"
    return msg


def check_for_new():
    log("جاري الفحص...")

    seen = load_seen()
    known_ids = set(seen.get("project_ids", []))
    driver = None

    try:
        driver = create_driver()
        projects, last_page = extract_last_page_projects(driver)

        if not projects:
            log("لم يتم العثور على مشاريع!")
            return

        log(f"آخر صفحة: {last_page} | مشاريع في الصفحة: {len(projects)}")

        try:
            from db_config import save_future_project
            for project in projects:
                save_future_project(project)
        except Exception as dbe:
            log(f"خطأ حفظ قاعدة البيانات: {dbe}")

        new_count = 0
        for project in projects:
            pid = project["id"]
            if pid not in known_ids:
                new_count += 1
                known_ids.add(pid)
                msg = format_notification(project)
                send_telegram_message(msg)
                log(f"  جديد: #{pid} - {project['name'][:60]}")

        if new_count == 0:
            log("لا جديد")
        else:
            log(f"{new_count} مشروع جديد!")

        seen["project_ids"] = list(known_ids)
        seen["last_page"] = last_page
        seen["last_check"] = datetime.now().isoformat()
        save_seen(seen)

    except Exception as e:
        log(f"خطأ: {e}")
    finally:
        if driver:
            driver.quit()


def main():
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        log("يجب إعداد تليجرام أولاً!")
        return

    log("فحص المشاريع المستقبلية...")
    check_for_new()
    log("انتهى الفحص")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"توقف غير متوقع: {e}")
        import traceback
        with open(_LOG_DIR / "future_crash.log", "a", encoding="utf-8") as f:
            traceback.print_exc(file=f)
