import os
import requests
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def send_message(text, chat_id=None, bot_token=None):
    token = bot_token or BOT_TOKEN
    cid = chat_id or CHAT_ID
    if not token or not cid:
        print("⚠️ Telegram: не задано TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        r = requests.post(url, data={"chat_id": cid, "text": text, "parse_mode": "HTML"}, timeout=10)
        if not r.ok:
            print(f"⚠️ Telegram помилка: {r.status_code} {r.text}")
    except Exception as e:
        print(f"⚠️ Telegram exception: {e}")