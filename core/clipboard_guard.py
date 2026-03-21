# core/clipboard_guard.py

import re
import time
from PyQt5.QtWidgets import QApplication
from db.database import Database
from core.spy_module import SpyModule
from core.telegram_alerts import send_telegram_alert

class ClipboardGuard:
    def __init__(self):
        self.db = Database()
        self.clipboard = QApplication.clipboard()
        self.patterns = {
            "ИИН": r'\b\d{12}\b',
            "Банковская карта": r'\b\d{16}\b'
        }
        self.is_running = False
        self.last_alert = 0 # Защита от спама (алерты не чаще чем раз в 3 сек)

    def check_clipboard(self):
        if not self.is_running: return
        if time.time() - self.last_alert < 3: return

        text = self.clipboard.text()
        if not text: return

        try:
            for name, pattern in self.patterns.items():
                if re.search(pattern, text):
                    self.clipboard.clear() # Чистим буфер
                    self.last_alert = time.time()
                    
                    details = f"УТЕЧКА ДАННЫХ: Копирование {name} ({text[:4]}...)"
                    self.db.log_incident(2, details)
                    
                    # РЕАКЦИЯ
                    SpyModule.play_siren()
                    send_telegram_alert(f"Попытка копирования конфиденциальных данных!\nТип: {name}")
                    print(f"[DLP ALERT] {details}")
                    break
        except Exception as e:
            print(f"Ошибка буфера: {e}")

    def start(self):
        self.is_running = True
        self.clipboard.dataChanged.connect(self.check_clipboard)

    def stop(self):
        self.is_running = False
        try: self.clipboard.dataChanged.disconnect(self.check_clipboard)
        except: pass