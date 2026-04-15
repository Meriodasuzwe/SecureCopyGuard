# core/vision_protector.py

import cv2
import time
import os
import sys
from pathlib import Path
from ultralytics import YOLO 
from PyQt5.QtCore import QThread, pyqtSignal

from core.spy_module import SpyModule # <--- Подключаем нашего шпиона


class VisionProtector(QThread):
    """
    ИИ-поток детекции смартфонов через YOLOv8.
    Общается с UI исключительно через Qt-сигналы.
    """

    phone_detected = pyqtSignal(str, str)
    status_changed = pyqtSignal(bool)
    camera_error   = pyqtSignal(str)

    PHONE_CLASS_ID = 67
    CONFIDENCE_THRESHOLD = 0.50
    ALERT_COOLDOWN_SEC   = 7
    FPS_LIMIT_MS         = 100

    def __init__(self, model_path: str = "yolov8n.pt", parent=None):
        super().__init__(parent)
        self._running = False
        self._model = None
        self._last_alert_time = 0.0
        self._evidence_dir = Path("_INTRUDERS")
        self._evidence_dir.mkdir(exist_ok=True)
        
        # МАГИЯ ДЛЯ EXE: Ищем нейросеть в правильной папке
        if getattr(sys, 'frozen', False):
            # Если мы в EXE, папка _internal находится рядом с экзешником
            base_dir = os.path.dirname(sys.executable)
            self._model_path = os.path.join(base_dir, "_internal", model_path)
            # Запасной вариант, если модель лежит прямо рядом с exe
            if not os.path.exists(self._model_path):
                self._model_path = os.path.join(base_dir, model_path)
        else:
            self._model_path = model_path

    def stop(self):
        self._running = False
        self.wait(3000)

    def run(self):
        try:
            self._model = YOLO(self._model_path)
        except Exception as exc:
            self.camera_error.emit(f"Не удалось загрузить модель YOLO: {exc}")
            return

        # ─── БЛОКИРУЕМ КАМЕРУ ДЛЯ ОСТАЛЬНЫХ МОДУЛЕЙ ───
        SpyModule._camera_busy = True

        # ИСПРАВЛЕНИЕ ДЛЯ WINDOWS: Добавлен cv2.CAP_DSHOW
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            self.camera_error.emit("Камера недоступна. Проверьте подключение.")
            SpyModule._camera_busy = False # Снимаем блокировку, если камера не открылась
            return

        self._running = True
        self.status_changed.emit(True)
        print("[VISION] ИИ-детекция запущена.")

        try:
            while self._running:
                ret, frame = cap.read()
                if not ret:
                    self.msleep(200)
                    continue

                self._process_frame(frame)
                self.msleep(self.FPS_LIMIT_MS)

        finally:
            cap.release()
            # ─── ОСВОБОЖДАЕМ КАМЕРУ ───
            SpyModule._camera_busy = False
            self._running = False
            self.status_changed.emit(False)
            print("[VISION] ИИ-детекция остановлена.")

    def _process_frame(self, frame):
        results = self._model.predict(
            frame,
            classes=[self.PHONE_CLASS_ID],
            conf=self.CONFIDENCE_THRESHOLD,
            verbose=False
        )

        if not results or len(results[0].boxes) == 0:
            return

        now = time.time()
        if now - self._last_alert_time < self.ALERT_COOLDOWN_SEC:
            return

        self._last_alert_time = now
        photo_path = self._save_evidence(results[0].plot(), now)

        msg = (
            "⚠️ ОБНАРУЖЕН СМАРТФОН: возможная попытка фотофиксации экрана!\n"
            f"Кадр сохранён: {photo_path}"
        )
        print(f"[VISION ALERT] {msg}")
        self.phone_detected.emit(msg, str(photo_path))

    def _save_evidence(self, annotated_frame, timestamp: float) -> Path:
        filename = self._evidence_dir / f"phone_{int(timestamp)}.jpg"
        cv2.imwrite(str(filename), annotated_frame)
        return filename