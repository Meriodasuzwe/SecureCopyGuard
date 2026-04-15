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
      - снимка экрана (take_screenshot)
    """

    # Флаг занятости камеры (управляется из VisionProtector)
    _camera_busy = False

    @staticmethod
    def take_photo(camera_index: int = 0) -> str | None:
        # СПАСАЕТ ОТ ЗАВИСАНИЯ! Если YOLO работает, даже не трогаем вебку.
        if SpyModule._camera_busy:
            print("[SPY] Камера занята AI Vision. Пропускаем фото, делаем скриншот.")
            return None

        cam = None
        try:
            # ВАЖНО ДЛЯ WINDOWS: Добавлен cv2.CAP_DSHOW чтобы камера не висла в .exe
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
    
    @staticmethod
    def take_screenshot() -> str | None:
        """
        Делает скриншот всего рабочего стола в момент инцидента.
        Идеальное доказательство для кражи файлов или буфера обмена.
        """
        from PyQt5.QtWidgets import QApplication
        from pathlib import Path
        import time

        try:
            folder = Path(INTRUDER_FOLDER)
            folder.mkdir(exist_ok=True, parents=True)
            filepath = folder / f"screenshot_{int(time.time())}.jpg"
            
            # Захватываем главный экран системы
            screen = QApplication.primaryScreen()
            if screen is not None:
                pixmap = screen.grabWindow(0)
                pixmap.save(str(filepath), "JPG", 75) # 75 - сжатие для быстрого Telegram
                print(f"[SPY] Скриншот доказательства сохранен: {filepath}")
                return str(filepath)
            return None
        except Exception as exc:
            print(f"[SPY] Ошибка при создании скриншота: {exc}")
            return None