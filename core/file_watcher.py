# core/file_watcher.py

import os
import threading
from pathlib import Path

from watchdog.observers import Observer
from watchdog.events    import FileSystemEventHandler

from PyQt5.QtCore import QObject, pyqtSignal

from db.database import Database


# Временные файлы, которые не нужно мониторить
_IGNORE_PREFIXES = ("~$", ".~", "._")
_IGNORE_SUFFIXES = (".tmp", ".swp", ".lock", ".part")


class _EventBridge(QObject):
    """
    Маленький QObject, чьи сигналы watchdog-поток эмитирует через
    Qt-очередь в основной поток. Сам watchdog — не QThread, поэтому
    нам нужен отдельный объект-мост.
    """
    incident = pyqtSignal(int, str)   # (policy_id, description)


class _DLPHandler(FileSystemEventHandler):
    """
    Обработчик событий файловой системы.
    Пишет в БД и испускает сигнал — никаких прямых вызовов Telegram/сирены.
    Telegram вызывает DashboardPage в ответ на сигнал (в главном потоке).
    """

    def __init__(self, bridge: _EventBridge):
        super().__init__()
        self._bridge     = bridge
        self._db         = Database()
        self._use_camera = False
        # Дебаунс: игнорируем повторные события на один файл за 2 сек
        self._recent: dict[str, float] = {}
        self._recent_lock = threading.Lock()

    def set_policy(self, use_camera: bool):
        self._use_camera = use_camera

    # ── Удаление файла ────────────────────────────────────────────────

    def on_deleted(self, event):
        if event.is_directory:
            return
        path = event.src_path
        if self._should_ignore(path) or self._is_debounced(path):
            return

        filename = Path(path).name
        details  = f"УДАЛЕНИЕ ФАЙЛА: {path}"

        # Пишем в БД прямо из потока watchdog — это безопасно (RLock)
        self._db.log_incident(1, details)

        # Сигналим в UI (Qt сам поставит в очередь главного потока)
        self._bridge.incident.emit(
            1,
            f"⚠️ Попытка удаления файла!\n📂 {filename}"
        )

    # ── Изменение файла ───────────────────────────────────────────────

    def on_modified(self, event):
        if event.is_directory:
            return
        path = event.src_path
        if self._should_ignore(path) or self._is_debounced(path):
            return

        filename = Path(path).name
        details  = f"Изменение файла: {path}"

        self._db.log_incident(3, details)   # policy 3 = Системное событие (Low)
        # Изменение — не критично, в UI не дёргаем (только БД)

    # ── Создание файла ────────────────────────────────────────────────

    def on_created(self, event):
        """Копирование файла в защищённую папку — подозрительно."""
        if event.is_directory:
            return
        path = event.src_path
        if self._should_ignore(path) or self._is_debounced(path):
            return

        filename = Path(path).name
        details  = f"Создание/копирование файла: {path}"

        self._db.log_incident(2, details)   # policy 2 = Утечка данных (High)
        self._bridge.incident.emit(
            2,
            f"📋 Файл скопирован в защищённую директорию!\n📂 {filename}"
        )

    # ── Вспомогательные ──────────────────────────────────────────────

    @staticmethod
    def _should_ignore(path: str) -> bool:
        name = Path(path).name
        return (
            any(name.startswith(p) for p in _IGNORE_PREFIXES) or
            any(name.endswith(s)   for s in _IGNORE_SUFFIXES)
        )

    def _is_debounced(self, path: str, window: float = 2.0) -> bool:
        """Возвращает True если это событие уже было за последние `window` сек."""
        import time
        now = time.monotonic()
        with self._recent_lock:
            last = self._recent.get(path, 0.0)
            if now - last < window:
                return True
            self._recent[path] = now
            # Чистим старые записи чтобы словарь не рос вечно
            if len(self._recent) > 500:
                cutoff = now - window * 2
                self._recent = {k: v for k, v in self._recent.items() if v > cutoff}
        return False


# ══════════════════════════════════════════════════════════════════════

class FolderWatcher(QObject):
    """
    Публичный класс-обёртка.
    Управляет Observer и пробрасывает его сигналы наружу.
    """

    # Сигнал: (policy_id, message) → DashboardPage._on_file_incident
    incident_detected = pyqtSignal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._observer: Observer | None = None
        self._bridge   = _EventBridge()
        self._handler  = _DLPHandler(self._bridge)

        # Прокидываем внутренний сигнал моста наружу
        self._bridge.incident.connect(self.incident_detected)

    def start(self, folder_path: str, use_camera: bool = False):
        self.stop()  # на случай если уже работает
        self._handler.set_policy(use_camera)
        self._observer = Observer()
        self._observer.schedule(self._handler, folder_path, recursive=True)
        self._observer.start()
        print(f"[WATCHER] Мониторинг запущен: {folder_path}")

    def stop(self):
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
            print("[WATCHER] Мониторинг остановлен.")