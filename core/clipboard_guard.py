# core/clipboard_guard.py

import time
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication

class ClipboardGuard(QThread):
    """
    Жёсткий мониторинг буфера обмена.
    Блокирует копирование любых файлов из защищенной папки и копирование любого текста.
    """
    violation_detected = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._watched_folder = None
        self._last_alert_time = 0

    def set_watched_folder(self, folder):
        self._watched_folder = folder.replace("\\", "/") if folder else None

    def stop(self):
        self._running = False
        self.wait(2000)

    def run(self):
        self._running = True
        clipboard = QApplication.clipboard()
        
        # ── ФИКС БАГА ──────────────────────────────────────────────────
        # Сразу читаем то, что УЖЕ есть в буфере обмена до запуска защиты.
        # Теперь программа не будет выдавать ложную тревогу при старте.
        last_seen_text = clipboard.text().strip()
        # ───────────────────────────────────────────────────────────────
        
        print("[CLIPBOARD] Жёсткая блокировка буфера запущена.")

        while self._running:
            try:
                mime_data = clipboard.mimeData()
                if mime_data is None:
                    self.msleep(500)
                    continue

                # 1. БЛОКИРОВКА ФАЙЛОВ
                if mime_data.hasUrls():
                    urls = mime_data.urls()
                    blocked = False
                    for url in urls:
                        file_path = url.toLocalFile().replace("\\", "/")
                        if self._watched_folder and file_path.startswith(self._watched_folder):
                            blocked = True
                            break
                    
                    if blocked:
                        clipboard.setText("")  # setText("") работает в винде надежнее, чем clear()
                        self._trigger_alert("Попытка скопировать файл из защищенной директории", "Файл заблокирован")
                        self.msleep(500)
                        continue

                # 2. БЛОКИРОВКА ТЕКСТА
                if mime_data.hasText():
                    text = mime_data.text().strip()
                    # Защита от спама: ругаемся ТОЛЬКО если текст есть и он отличается от прошлого
                    if text and text != last_seen_text:
                        last_seen_text = text
                        clipboard.setText("")
                        self._trigger_alert("Копирование текста запрещено политикой DLP", "***")

            except Exception as e:
                pass
                
            self.msleep(500)

        print("[CLIPBOARD] Мониторинг буфера обмена остановлен.")

    def _trigger_alert(self, msg, snippet):
        now = time.time()
        # Анти-спам таймер: не чаще 1 алерта в 2 секунды
        if now - self._last_alert_time > 2:
            self._last_alert_time = now
            print(f"[CLIPBOARD ALERT] {msg}")
            self.violation_detected.emit(msg, snippet)