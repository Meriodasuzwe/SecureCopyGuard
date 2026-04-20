# core/clipboard_guard.py

import os
import time
import ctypes
from pathlib import Path
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication

class ClipboardGuard(QThread):
    """
    Жёсткий мониторинг буфера обмена (Context-Aware).
    Блокирует копирование файлов, а также перехватывает текст, 
    скопированный ИЗ ОТКРЫТЫХ защищенных документов.
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
        try:
            ctypes.windll.user32.OpenClipboard(0)
            ctypes.windll.user32.EmptyClipboard()
            ctypes.windll.user32.CloseClipboard()
        except Exception:
            pass

    def _get_active_window_title(self):
        """ХАК: Получает заголовок окна, в котором сейчас находится пользователь"""
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        buff = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
        return buff.value

    def run(self):
        # ─── ФИКС ОШИБКИ OLE / COM ───
        try:
            ctypes.windll.ole32.CoInitialize(None)
        except Exception:
            pass
        
        self._running = True
        clipboard = QApplication.clipboard()
        
        last_seen_text = clipboard.text().strip()
        last_seen_urls = []
        
        print("[CLIPBOARD] Интеллектуальный мониторинг буфера запущен.")

        while self._running:
            try:
                mime_data = clipboard.mimeData()
                if mime_data is None:
                    self.msleep(500)
                    continue

                # 1. БЛОКИРОВКА ФИЗИЧЕСКОГО КОПИРОВАНИЯ ФАЙЛОВ
                if mime_data.hasUrls():
                    urls = [u.toLocalFile() for u in mime_data.urls()]
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
                            clipboard.clear()
                            last_seen_urls = []
                            self._trigger_alert("🚫 Попытка скопировать файл из защищенной директории", "Файл заблокирован")

                # 2. ИНТЕЛЛЕКТУАЛЬНАЯ БЛОКИРОВКА ТЕКСТА ИЗ ОТКРЫТОГО ДОКУМЕНТА
                if mime_data.hasText():
                    text = mime_data.text().strip()
                    if text and text != last_seen_text:
                        last_seen_text = text
                        
                        if self._watched_folder and os.path.exists(self._watched_folder):
                            # В момент копирования смотрим, в каком окне сидит юзер
                            active_window = self._get_active_window_title()
                            
                            try:
                                protected_files = os.listdir(self._watched_folder)
                            except Exception:
                                protected_files = []

                            is_protected_doc = False
                            doc_name = ""

                            # Ищем, есть ли имя нашего защищенного файла в заголовке окна
                            for f in protected_files:
                                # Берем имя файла без расширения (т.к. Word часто пишет просто имя)
                                stem = Path(f).stem.lower()
                                # Исключаем слишком короткие имена для защиты от ложных срабатываний
                                if len(stem) > 2 and stem in active_window.lower():
                                    is_protected_doc = True
                                    doc_name = f
                                    break

                            # Если текст скопирован из нашего документа
                            if is_protected_doc:
                                self._clear_clipboard()
                                clipboard.clear()
                                last_seen_text = "" # Сбрасываем, чтобы забыть этот текст
                                
                                # Отправляем алерт. В pages.py это триггерит сирену, фото и Telegram!
                                alert_msg = f"⚠️ КРИТИЧЕСКАЯ УТЕЧКА: Попытка скопировать текст из защищенного документа!\n📄 Документ: {doc_name}\n🖥 Окно: {active_window}"
                                snippet = text[:150] + "..." if len(text) > 150 else text
                                self._trigger_alert(alert_msg, snippet)

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