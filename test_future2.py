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

# Try Angular scope to get total pages
result = driver.execute_script("""
    try {
        var scope = angular.element(document.querySelector('[ng-controller]')).scope();
        return JSON.stringify({
            totalPages: scope.totalPages || scope.pageCount || 'N/A',
            currentPage: scope.currentPage || scope.pageNumber || 'N/A',
            totalItems: scope.totalItems || scope.totalCount || 'N/A'
        });
    } catch(e) {
        return 'Error: ' + e.message;
    }
""")
print(f"Angular scope: {result}")

# Try Vue/React data
result2 = driver.execute_script("""
    try {
        var el = document.querySelector('[class*=pagination], [class*=pager], nav');
        if (el && el.__vue__) return JSON.stringify(el.__vue__.$data);
        // Try finding all page links
        var links = document.querySelectorAll('a[href*=void]');
        var pages = [];
        links.forEach(function(l) { if (l.textContent.trim().match(/^\\d+$/)) pages.push(l.textContent.trim()); });
        return 'Page links: ' + pages.join(', ');
    } catch(e) {
        return 'Error: ' + e.message;
    }
""")
print(f"Vue/data: {result2}")

# Find the »» button and click to go to last page
result3 = driver.execute_script("""
    var allElements = document.querySelectorAll('a, button, span, li');
    var found = [];
    for (var i = 0; i < allElements.length; i++) {
        var text = allElements[i].textContent.trim();
        if (text === '»»' || text === '>>' || text === '»' || text === '««' || text === '«') {
            found.push({text: text, tag: allElements[i].tagName, classes: allElements[i].className});
            if (text === '»»') {
                allElements[i].click();
            }
        }
    }
    return JSON.stringify(found);
""")
print(f"Pagination elements: {result3}")

time.sleep(8)

# Get current page info after clicking last
body_text = driver.find_element(By.TAG_NAME, "body").text
lines = [l.strip() for l in body_text.split("\n") if l.strip()]

# Find page numbers (large numbers in pagination area)
for i, line in enumerate(lines):
    if line == "««":
        # Pages are near this
        start = max(0, i - 5)
        end = min(len(lines), i + 10)
        print(f"\nAround pagination:")
        for j in range(start, end):
            print(f"  {j}: {lines[j]}")
        break

# Get table rows
print("\n--- TABLE DATA ---")
in_table = False
for i, line in enumerate(lines):
    if "# إسم المشروع" in line or "# اسم المشروع" in line:
        in_table = True
        continue
    if line == "««":
        break
    if in_table:
        print(f"  {line}")

driver.quit()
