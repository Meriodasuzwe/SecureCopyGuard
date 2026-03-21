# core/file_locker.py

import os
import stat
from pathlib import Path
from config import BASE_DIR # Тянем путь к корню нашего проекта

class FileLocker:
    @staticmethod
    def lock_directory(directory_path):
        """Блокирует файлы в папке (Только чтение), пропуская папку самого проекта"""
        path = Path(directory_path).resolve()
        if not path.exists():
            return
        
        for file_path in path.rglob('*'):
            if file_path.is_file():
                # --- БРОНЕЖИЛЕТ ДЛЯ НАШЕГО ПРОЕКТА ---
                try:
                    # Если файл лежит где-то внутри dlp_project - пропускаем его!
                    if file_path.is_relative_to(BASE_DIR):
                        continue
                except AttributeError:
                    # Запасной вариант для надежности
                    if str(BASE_DIR) in str(file_path):
                        continue
                
                try:
                    os.chmod(file_path, stat.S_IREAD) # Блокируем на чтение
                except Exception:
                    pass # Глушим ошибки (например, системные скрытые файлы винды)

    @staticmethod
    def unlock_directory(directory_path):
        """Разблокирует все файлы в папке (Возвращает права на запись)"""
        path = Path(directory_path).resolve()
        if not path.exists():
            return
            
        for file_path in path.rglob('*'):
            if file_path.is_file():
                try:
                    os.chmod(file_path, stat.S_IWRITE)
                except Exception:
                    pass