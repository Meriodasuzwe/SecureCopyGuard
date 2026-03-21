# core/telegram_alerts.py

import requests
import threading
import socket
import os
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

def send_telegram_alert(message, photo_path=None):
    """Отправляет текст или фото с описанием в фоновом потоке"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    def worker():
        hostname = socket.gethostname()
        header = "🚨 *DLP ALERT: " + hostname + "*\n━━━━━━━━━━━━━━━\n"
        full_text = f"{header}📌 {message}"

        try:
            if photo_path and os.path.exists(photo_path):
                # Отправка фото
                url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
                with open(photo_path, 'rb') as f:
                    r = requests.post(url, data={'chat_id': TELEGRAM_CHAT_ID, 'caption': full_text, 'parse_mode': 'Markdown'}, files={'photo': f}, timeout=15)
            else:
                # Отправка текста
                url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                r = requests.post(url, data={'chat_id': TELEGRAM_CHAT_ID, 'text': full_text, 'parse_mode': 'Markdown'}, timeout=10)
            
            # Для отладки в консоль
            if r.status_code != 200:
                print(f"[TG ERROR] {r.text}")
        except Exception as e:
            print(f"[TG ERROR] Ошибка сети: {e}")

    threading.Thread(target=worker, daemon=True).start()