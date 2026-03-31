# core/spy_module.py

import time
import threading
import winsound
import cv2
from pathlib import Path
from config import INTRUDER_FOLDER


class SpyModule:
    """
    Утилитный класс для:
      - звукового оповещения (siren)
      - снимка с веб-камеры (take_photo)

    ВАЖНО: take_photo() НЕ вызывается когда работает VisionProtector —
    тот уже держит камеру и сам сохраняет кадры с bounding box.
    Используется только в FolderWatcher (удаление файла) когда AI-Vision выключен.
    """

    # Общая блокировка камеры — предотвращает одновременное открытие
    _camera_lock = threading.Lock()

    @staticmethod
    def take_photo(camera_index: int = 0) -> str | None:
        """
        Делает снимок с веб-камеры и сохраняет в INTRUDER_FOLDER.
        Возвращает путь к файлу или None при ошибке.

        Не вызывайте этот метод пока работает VisionProtector —
        они конфликтуют за одну камеру.
        """
        # Пробуем захватить блокировку без ожидания
        acquired = SpyModule._camera_lock.acquire(blocking=False)
        if not acquired:
            print("[SPY] Камера занята VisionProtector, снимок пропущен.")
            return None

        cam = None
        try:
            cam = cv2.VideoCapture(camera_index)
            if not cam.isOpened():
                print("[SPY] Камера недоступна.")
                return None

            # Прогреваем — первые кадры всегда тёмные
            for _ in range(5):
                cam.read()

            ret, frame = cam.read()
            if not ret:
                return None

            Path(INTRUDER_FOLDER).mkdir(exist_ok=True)
            filename = f"intruder_{int(time.time())}.jpg"
            filepath = Path(INTRUDER_FOLDER) / filename
            cv2.imwrite(str(filepath), frame)
            print(f"[SPY] Снимок сохранён: {filepath}")
            return str(filepath)

        except Exception as exc:
            print(f"[SPY] Ошибка при съёмке: {exc}")
            return None

        finally:
            if cam is not None:
                cam.release()
            SpyModule._camera_lock.release()

    @staticmethod
    def play_siren():
        """
        Звуковая тревога — три двойных сигнала.
        Запускается в daemon-потоке, не блокирует вызывающий код.
        """
        def _beep():
            try:
                for _ in range(3):
                    winsound.Beep(1200, 250)   # высокий
                    winsound.Beep(600,  250)   # низкий
            except Exception as exc:
                print(f"[SPY] Ошибка сирены: {exc}")

        threading.Thread(target=_beep, daemon=True, name="Siren").start()