# core/clipboard_guard.py

import time
import ctypes
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication

class ClipboardGuard(QThread):
    """
    Жёсткий мониторинг буфера обмена.
    Блокирует копирование любых файлов из защищенной папки.
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

    def _clear_clipboard(self):
        # Жесткая очистка буфера на низком уровне Windows API
        # Это спасает от багов PyQt и ошибок "COM error 0xffffffff800401f0"
        try:
            ctypes.windll.user32.OpenClipboard(0)
            ctypes.windll.user32.EmptyClipboard()
            ctypes.windll.user32.CloseClipboard()
        except Exception:
            pass

    def run(self):
        # ─── ФИКС ОШИБКИ OLE / COM (CO_E_NOTINITIALIZED) ───
        try:
            ctypes.windll.ole32.CoInitialize(None)
        except Exception:
            pass
        
        self._running = True
        clipboard = QApplication.clipboard()
        
        # Читаем стартовые значения, чтобы не орать при запуске
        last_seen_text = clipboard.text().strip()
        last_seen_urls = []
        
        print("[CLIPBOARD] Жёсткая блокировка буфера запущена.")

        while self._running:
            try:
                mime_data = clipboard.mimeData()
                if mime_data is None:
                    self.msleep(500)
                    continue

                # 1. БЛОКИРОВКА ФАЙЛОВ
                if mime_data.hasUrls():
                    urls = [u.toLocalFile() for u in mime_data.urls()]
                    # ФИКС БЕСКОНЕЧНОГО СПАМА: реагируем, только если файлы новые
                    if urls != last_seen_urls:
                        last_seen_urls = urls
                        blocked = False
                        
                        for url in urls:
                            file_path = url.replace("\\", "/")
                            if self._watched_folder and file_path.startswith(self._watched_folder):
                                blocked = True
                                break
                        
                        if blocked:
                            self._clear_clipboard()
                            clipboard.clear() # Чистим кэш PyQt, чтобы он забыл этот файл
                            last_seen_urls = []
                            self._trigger_alert("Попытка скопировать файл из защищенной директории", "Файл заблокирован")

                # 2. БЛОКИРОВКА ТЕКСТА
                if mime_data.hasText():
                    text = mime_data.text().strip()
                    if text and text != last_seen_text:
                        last_seen_text = text
                        # Раскомментируй 3 строчки ниже, если хочешь жестко блокировать
                        # копирование ВООБЩЕ ЛЮБОГО текста на компьютере:
                        # self._clear_clipboard()
                        # clipboard.clear()
                        # self._trigger_alert("Копирование текста запрещено DLP-системой", "***")

            except Exception:
                pass
                
            self.msleep(500)

        # Подчищаем за собой при выходе
        try:
            ctypes.windll.ole32.CoUninitialize()
        except Exception:
            pass
            
        print("[CLIPBOARD] Мониторинг буфера обмена остановлен.")

    def _trigger_alert(self, msg, snippet):
        now = time.time()
        # Анти-спам таймер: не чаще 1 алерта в 2 секунды
        if now - self._last_alert_time > 2:
            self._last_alert_time = now
            print(f"[CLIPBOARD ALERT] {msg}")
            self.violation_detected.emit(msg, snippet)