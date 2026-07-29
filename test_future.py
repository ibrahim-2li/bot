import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time

options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)
driver.get("https://tenders.etimad.sa/Preplanning/PrePlaningForVisitor")
time.sleep(10)

# Find all links and look for last-page navigation
all_links = driver.find_elements(By.TAG_NAME, "a")
for link in all_links:
    text = link.text.strip()
    href = link.get_attribute("href") or ""
    if text in ("»»", ">>", "»", "«", "««", "<<") or "last" in href.lower() or "page" in href.lower():
        tag = link.tag_name
        cls = link.get_attribute("class") or ""
        print(f"NAV: [{text}] href={href} class={cls}")

# Find page count by checking pagination area
print("\n--- All page-like elements ---")
page_items = driver.find_elements(By.CSS_SELECTOR, "[class*='pagination'] *, [class*='pager'] *, [class*='page'] a")
for p in page_items[:20]:
    print(f"  [{p.text.strip()[:20]}] tag={p.tag_name}")

# Alternative: find by XPath containing page numbers
print("\n--- XPath search ---")
elems = driver.find_elements(By.XPATH, "//a[contains(@class,'page') or contains(@ng-click,'page') or contains(@href,'page')]")
for e in elems[:10]:
    t = e.text.strip()
    print(f"  [{t}] href={e.get_attribute('href') or 'none'}")

# Get page source for pagination section
src = driver.page_source
import re
# Find last page number in source
page_matches = re.findall(r"lastPage['\"]?\s*[:=]\s*(\d+)", src)
print(f"\nlastPage matches: {page_matches}")

total_matches = re.findall(r"totalPages?['\"]?\s*[:=]\s*(\d+)", src)
print(f"totalPages matches: {total_matches}")

count_matches = re.findall(r"pageCount['\"]?\s*[:=]\s*(\d+)", src)
print(f"pageCount matches: {count_matches}")

# Find any number > 10000 in source (likely total pages)
big_nums = re.findall(r"['\"]?(\d{4,6})['\"]?", src)
big_nums = [n for n in big_nums if 10000 < int(n) < 99999]
big_unique = list(set(big_nums))[:10]
print(f"Big numbers in source: {big_unique}")

driver.quit()
