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
    """

    _camera_lock = threading.Lock()

    @staticmethod
    def take_photo(camera_index: int = 0) -> str | None:
        acquired = SpyModule._camera_lock.acquire(blocking=False)
        if not acquired:
            print("[SPY] Камера занята VisionProtector, снимок пропущен.")
            return None

        cam = None
        try:
            # ВАЖНО ДЛЯ WINDOWS: Добавлен cv2.CAP_DSHOW чтобы камера не висла в .exe
            cam = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
            
            if not cam.isOpened():
                print("[SPY] Камера недоступна.")
                return None

            # Прогреваем — первые кадры всегда тёмные
            for _ in range(5):
                cam.read()

            ret, frame = cam.read()
            if not ret:
                return None

            Path(INTRUDER_FOLDER).mkdir(exist_ok=True, parents=True)
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
        def _beep():
            try:
                for _ in range(3):
                    winsound.Beep(1200, 250)   # высокий
                    winsound.Beep(600,  250)   # низкий
            except Exception as exc:
                print(f"[SPY] Ошибка сирены: {exc}")

        threading.Thread(target=_beep, daemon=True, name="Siren").start()