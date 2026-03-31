# core/clipboard_guard.py

import re
import time
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication


class ClipboardGuard(QThread):
    """
    Мониторинг буфера обмена.
    При обнаружении чувствительных данных — очищает буфер и сигналит UI.
    """

    violation_detected = pyqtSignal(str, str)  # (описание, перехваченный_текст_обрезанный)

    # Паттерны чувствительных данных
    PATTERNS = [
        (r"\b(?:\d[ -]?){15,16}\b",                         "Номер банковской карты"),
        (r"\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b",             "SSN / ИИН"),
        (r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", "Email-адрес"),
        (r"(?i)(пароль|password|passwd|secret|token|api[_\s]?key)\s*[=:]\s*\S+", "Учётные данные"),
        (r"(?i)confidential|strictly private|top secret",   "Конфиденциальный документ"),
        (r"\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}([A-Z0-9]?){0,16}\b", "IBAN / банковские реквизиты"),
    ]

    POLL_INTERVAL_MS = 500  # проверяем буфер каждые 500 мс

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._compiled = [(re.compile(p), label) for p, label in self.PATTERNS]

    def stop(self):
        self._running = False
        self.wait(2000)

    def run(self):
        self._running = True
        clipboard = QApplication.clipboard()
        prev_text = ""

        print("[CLIPBOARD] Мониторинг буфера обмена запущен.")

        while self._running:
            try:
                current_text = clipboard.text()
            except Exception:
                self.msleep(self.POLL_INTERVAL_MS)
                continue

            if current_text and current_text != prev_text:
                prev_text = current_text
                match_label = self._scan(current_text)

                if match_label:
                    # Немедленно стираем буфер
                    clipboard.clear()
                    prev_text = ""

                    # Обрезаем для лога — не храним полные данные
                    snippet = (current_text[:40] + "…") if len(current_text) > 40 else current_text
                    snippet = "*" * min(len(snippet), 10)  # маскируем

                    msg = f"Перехвачено: [{match_label}] — буфер очищен"
                    print(f"[CLIPBOARD ALERT] {msg}")
                    self.violation_detected.emit(msg, snippet)

            self.msleep(self.POLL_INTERVAL_MS)

        print("[CLIPBOARD] Мониторинг буфера обмена остановлен.")

    def _scan(self, text: str) -> str | None:
        """Возвращает название категории если найден чувствительный паттерн, иначе None."""
        for pattern, label in self._compiled:
            if pattern.search(text):
                return label
        return None