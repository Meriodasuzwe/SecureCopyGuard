# core/telegram_alerts.py

import os
import time
import threading
import requests
from pathlib import Path

# ИМПОРТИРУЕМ ФУНКЦИИ ИЗ КОНФИГА!
from config import get_telegram_token, get_telegram_chat_id


class TelegramAlerter:
    """
    Отправка уведомлений в Telegram.
    Работает в отдельном daemon-потоке чтобы не блокировать UI.
    Поддерживает очередь сообщений и отправку фото-доказательств.
    """

    TIMEOUT   = 10  # секунд на запрос
    MAX_RETRY = 3

    def __init__(self, token: str, chat_id: str):
        self.token   = token
        self.chat_id = chat_id
        self._base   = f"https://api.telegram.org/bot{token}"
        self._lock = threading.Lock()

    def send_alert(self, message: str, photo_path: str | None = None):
        t = threading.Thread(
            target=self._send_safe,
            args=(message, photo_path),
            daemon=True,
            name="TelegramSender"
        )
        t.start()

    def _send_safe(self, message: str, photo_path: str | None):
        with self._lock:
            for attempt in range(1, self.MAX_RETRY + 1):
                try:
                    if photo_path and Path(photo_path).exists():
                        self._send_photo(message, photo_path)
                    else:
                        self._send_text(message)
                    return  # успех
                except requests.RequestException as exc:
                    print(f"[TELEGRAM] Попытка {attempt}/{self.MAX_RETRY} неудачна: {exc}")
                    if attempt < self.MAX_RETRY:
                        time.sleep(2 * attempt)  

    def _send_text(self, message: str):
        resp = requests.post(
            f"{self._base}/sendMessage",
            json={
                "chat_id": self.chat_id,
                "text":    f"🚨 <b>DLP ALERT</b>\n\n{message}",
                "parse_mode": "HTML",
            },
            timeout=self.TIMEOUT
        )
        resp.raise_for_status()

    def _send_photo(self, caption: str, photo_path: str):
        with open(photo_path, "rb") as photo_file:
            resp = requests.post(
                f"{self._base}/sendPhoto",
                data={
                    "chat_id": self.chat_id,
                    "caption": f"🚨 <b>DLP ALERT</b>\n\n{caption}",
                    "parse_mode": "HTML",
                },
                files={"photo": ("evidence.jpg", photo_file, "image/jpeg")},
                timeout=self.TIMEOUT
            )
        resp.raise_for_status()


def send_telegram_alert(message: str, photo_path: str | None = None):
    """Глобальная функция. Всегда берет свежий токен из конфига."""
    token   = get_telegram_token()
    chat_id = get_telegram_chat_id()
    
    if token and chat_id:
        alerter = TelegramAlerter(token, chat_id)
        alerter.send_alert(message, photo_path)
    else:
        print(f"[TELEGRAM] Токен не настроен, уведомление не отправлено: {message}")