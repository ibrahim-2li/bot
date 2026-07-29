import requests

token = "8688443116:AAE6SZ9ZIJncJiCCqDWRHBxW6Ti1sYnV1Ug"
chat_id = "1795773958"
msg = (
    "<b>مراقب مناقصات اعتماد</b>\n\n"
    "تم الإعداد بنجاح!\n"
    "ستصلك إشعارات فورية عند نزول مناقصات جديدة على منصة اعتماد.\n\n"
    "جاري تشغيل أول فحص الآن..."
)
resp = requests.post(
    f"https://api.telegram.org/bot{token}/sendMessage",
    json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"},
    timeout=10,
)
print(f"Status: {resp.status_code}")
result = resp.json()
print(f"OK: {result.get('ok')}")
