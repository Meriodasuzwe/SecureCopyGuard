# core/file_locker.py

import os
import stat
from pathlib import Path
from config import BASE_DIR


class FileLocker:

    @staticmethod
    def lock_directory(directory_path: str):
        """
        Переводит все файлы директории в режим "только чтение".
        Пропускает файлы самого dlp_project чтобы не заблокировать себя.
        """
        path = Path(directory_path).resolve()
        if not path.exists():
            return

        for file_path in path.rglob("*"):
            if not file_path.is_file():
                continue
            # Защита: не трогаем файлы самого проекта
            if FileLocker._is_own_file(file_path):
                continue
            try:
                os.chmod(file_path, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
            except Exception:
                pass   # системные/скрытые файлы — пропускаем молча

    @staticmethod
    def unlock_directory(directory_path: str):
        """
        Возвращает файлам полные права на чтение и запись.
        """
        path = Path(directory_path).resolve()
        if not path.exists():
            return

        for file_path in path.rglob("*"):
            if not file_path.is_file():
                continue
            try:
                os.chmod(
                    file_path,
                    stat.S_IREAD | stat.S_IWRITE |
                    stat.S_IRGRP | stat.S_IWGRP |
                    stat.S_IROTH
                )
            except Exception:
                pass

    @staticmethod
    def _is_own_file(file_path: Path) -> bool:
        """Проверяет принадлежит ли файл директории самого проекта."""
        try:
            return file_path.is_relative_to(BASE_DIR)
        except AttributeError:
            # Python < 3.9
            return str(BASE_DIR) in str(file_path)