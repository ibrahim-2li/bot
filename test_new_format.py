import io, sys, time, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import requests

# Load page
options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)
driver.get("https://tenders.etimad.sa/Tender/AllTendersForVisitor?PageNumber=1&PageSize=6")
time.sleep(10)

# Import module
import importlib.util
spec = importlib.util.spec_from_file_location("m", r"C:\0MONTAR\etimad_monitor.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# Extract with links
tenders = mod.extract_tenders(driver)
driver.quit()

print(f"Found {len(tenders)} tenders")

# Send only first tender as test
if tenders:
    t = tenders[0]
    print(f"Testing with: {t.get('reference')} - {t.get('name')[:50]}")
    print(f"Detail URL: {t.get('detail_url', 'NOT FOUND')}")

    msg = mod.format_notification(t)
    print(f"\nMessage:\n{msg}\n")

    # Send to Telegram
    token = "8847811868:AAHrE9ziNS5lsO3aRX4_pg8P9hnVCPbzOHI"
    chat_id = "6035072930"
    resp = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"},
        timeout=10,
    )
    print(f"Telegram: {resp.status_code} - OK: {resp.json().get('ok')}")
