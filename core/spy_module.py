# core/spy_module.py

import os
import time
import threading
from pathlib import Path
import cv2
from PIL import ImageGrab

# Пытаемся импортировать путь из конфига, если нет - используем дефолтный
try:
    from config import INTRUDER_FOLDER
except ImportError:
    INTRUDER_FOLDER = "_INTRUDERS"

class SpyModule:
    """
    Enterprise-утилита для аппаратного контроля:
      - Фото-фиксация (с защитой от зависания DirectShow)
      - Снимки экрана (потокобезопасные через PIL)
      - Звуковые сирены (асинхронные)
    """

    # Флаг занятости камеры (управляется из VisionProtector для предотвращения конфликта потоков)
    _camera_busy = False

    @staticmethod
    def take_photo(camera_index: int = 0) -> str | None:
        """Делает снимок с веб-камеры. Если камера занята AI, делает пропуск."""
        
        if SpyModule._camera_busy:
            print("[SPY] Камера занята AI Vision. Пропускаем фото, делаем скриншот.")
            return None

        cam = None
        try:
            # Сначала пробуем DirectShow (быстрый запуск для Windows .exe)
            cam = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
            
            # Если не получилось, пробуем стандартный бэкенд (для старых камер/ноутбуков)
            if not cam.isOpened():
                cam = cv2.VideoCapture(camera_index)
            
            # Если всё еще глухо - сдаемся
            if not cam.isOpened():
                print("[SPY] Камера недоступна аппаратно.")
                return None

            for _ in range(5):
                cam.read()

            ret, frame = cam.read()
            if not ret:
                return None

            Path(INTRUDER_FOLDER).mkdir(exist_ok=True, parents=True)
            filename = f"intruder_{int(time.time())}.jpg"
            filepath = Path(INTRUDER_FOLDER) / filename
            cv2.imwrite(str(filepath), frame)
            
            print(f"[SPY] Снимок нарушителя сохранён: {filepath}")
            return str(filepath)

        except Exception as exc:
            print(f"[SPY] Критическая ошибка при съёмке: {exc}")
            return None

        finally:
            if cam is not None:
                cam.release()

    @staticmethod
    def take_screenshot() -> str | None:
        """
        Делает скриншот всего рабочего стола.
        Использует PIL (ImageGrab) для 100% потокобезопасности при вызове из фоновых воркеров DLP.
        """
        try:
            folder = Path(INTRUDER_FOLDER)
            folder.mkdir(exist_ok=True, parents=True)
            
            filepath = folder / f"screenshot_{int(time.time())}.jpg"
            
            # Захватываем экран и сохраняем с оптимизацией для быстрой отправки в Telegram
            screenshot = ImageGrab.grab()
            screenshot.save(str(filepath), "JPEG", quality=75)
            
            print(f"[SPY] Скриншот доказательства сохранен: {filepath}")
            return str(filepath)
            
        except Exception as exc:
            print(f"[SPY] Ошибка при создании скриншота: {exc}")
            return None

    @staticmethod
    def play_siren():
        """Асинхронный запуск звуковой тревоги (не блокирует основной поток программы)"""
        def _beep():
            try:
                import winsound
                # Имитация полицейской сирены (3 цикла)
                for _ in range(3):
                    winsound.Beep(1200, 250)   # высокий тон
                    winsound.Beep(600,  250)   # низкий тон
            except Exception as exc:
                print(f"[SPY] Ошибка аппаратной сирены: {exc}")

        # Запускаем как daemon-поток (умрет вместе с программой, если что)
        threading.Thread(target=_beep, daemon=True, name="SirenThread").start()