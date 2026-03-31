# core/telegram_alerts.py

import os
import time
import threading
import requests
from pathlib import Path


class TelegramAlerter:
    """
    Отправка уведомлений в Telegram.
    Работает в отдельном daemon-потоке чтобы не блокировать UI.
    Поддерживает очередь сообщений и отправку фото-доказательств.
    """

    API_BASE  = "https://api.telegram.org/bot{token}"
    TIMEOUT   = 10  # секунд на запрос
    MAX_RETRY = 3

    def __init__(self, token: str, chat_id: str):
        self.token   = token
        self.chat_id = chat_id
        self._base   = f"https://api.telegram.org/bot{token}"

        # Лёгкая блокировка чтобы не дёргать API параллельно
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Публичный интерфейс
    # ------------------------------------------------------------------

    def send_alert(self, message: str, photo_path: str | None = None):
        """
        Отправляет уведомление в отдельном потоке.
        photo_path — путь к jpg-файлу (необязательно).
        """
        t = threading.Thread(
            target=self._send_safe,
            args=(message, photo_path),
            daemon=True,
            name="TelegramSender"
        )
        t.start()

    # ------------------------------------------------------------------
    # Внутренние методы
    # ------------------------------------------------------------------

    def _send_safe(self, message: str, photo_path: str | None):
        """Отправка с повторными попытками при сбое сети."""
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
                        time.sleep(2 * attempt)  # экспоненциальный backoff

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


# ------------------------------------------------------------------
# Удобная фабрика — создаётся один раз из config
# ------------------------------------------------------------------

_instance: TelegramAlerter | None = None


def get_alerter() -> TelegramAlerter | None:
    """Возвращает синглтон-алертер, если токен настроен."""
    global _instance
    if _instance is None:
        token   = os.getenv("TELEGRAM_BOT_TOKEN", "")
        chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        if token and chat_id:
            _instance = TelegramAlerter(token, chat_id)
    return _instance


def send_telegram_alert(message: str, photo_path: str | None = None):
    """Глобальная функция для обратной совместимости с остальными модулями."""
    alerter = get_alerter()
    if alerter:
        alerter.send_alert(message, photo_path)
    else:
        print(f"[TELEGRAM] Токен не настроен, уведомление не отправлено: {message}")