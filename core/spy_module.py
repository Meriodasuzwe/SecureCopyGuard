# core/spy_module.py

import cv2
import time
import winsound
import threading
from pathlib import Path
from config import INTRUDER_FOLDER

class SpyModule:
    @staticmethod
    def take_photo():
        try:
            cam = cv2.VideoCapture(0)
            if not cam.isOpened(): return None
            # Пропускаем кадры для настройки экспозиции
            for _ in range(5): cam.read()
            ret, frame = cam.read()
            if ret:
                filename = f"intruder_{int(time.time())}.jpg"
                filepath = INTRUDER_FOLDER / filename
                cv2.imwrite(str(filepath), frame)
                cam.release()
                return str(filepath)
            cam.release()
        except: pass
        return None

    @staticmethod
    def play_siren():
        """Запускает звук в отдельном потоке, чтобы не вешать программу"""
        def sound_loop():
            try:
                for _ in range(3):
                    winsound.Beep(1000, 300) # Высокий писк
                    winsound.Beep(600, 300)  # Низкий писк
            except: pass
        threading.Thread(target=sound_loop, daemon=True).start()