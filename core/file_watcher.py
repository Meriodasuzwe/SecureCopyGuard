# core/file_watcher.py

import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from db.database import Database
from core.spy_module import SpyModule
from core.telegram_alerts import send_telegram_alert

class DLPEventHandler(FileSystemEventHandler):
    def __init__(self):
        self.db = Database()
        self.use_camera = False

    def set_policy(self, use_camera):
        self.use_camera = use_camera

    def on_deleted(self, event):
        if not event.is_directory:
            filename = os.path.basename(event.src_path)
            # Пропускаем временные файлы Word (~$)
            if filename.startswith("~$"): return

            details = f"ПОПЫТКА УДАЛЕНИЯ: {event.src_path}"
            self.db.log_incident(1, details)
            
            # РЕАКЦИЯ
            SpyModule.play_siren() # Орем
            
            photo = None
            if self.use_camera:
                photo = SpyModule.take_photo() # Фоткаем
            
            # Шлем в ТГ (с фоткой если есть)
            send_telegram_alert(f"Критический инцидент: Файл удален!\n📂 {filename}", photo_path=photo)

    def on_modified(self, event):
        if not event.is_directory:
            self.db.log_incident(3, f"Изменение файла: {event.src_path}")

class FolderWatcher:
    def __init__(self):
        self.observer = None
        self.handler = DLPEventHandler()

    def start(self, folder_path, use_camera=False):
        if self.observer is not None:
            self.stop()
        self.handler.set_policy(use_camera)
        self.observer = Observer()
        self.observer.schedule(self.handler, folder_path, recursive=True)
        self.observer.start()

    def stop(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None