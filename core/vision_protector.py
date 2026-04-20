# core/vision_protector.py

import cv2
import time
import os
import sys
import numpy as np
from pathlib import Path
from ultralytics import YOLO 
from PyQt5.QtCore import QThread, pyqtSignal

from core.spy_module import SpyModule


class VisionProtector(QThread):
    """
    Интеллектуальный ИИ-поток защиты.
    1. Детекция смартфонов через YOLOv8.
    2. Анализ освещенности и саботажа (заклеивание камеры).
    """

    phone_detected = pyqtSignal(str, str) # Сообщение, путь к фото
    status_changed = pyqtSignal(bool)    # Активен/Неактивет
    camera_error   = pyqtSignal(str)     # Критические ошибки
    env_warning    = pyqtSignal(str)     # Предупреждения (темно, размыто)

    PHONE_CLASS_ID = 67
    CONFIDENCE_THRESHOLD = 0.45          # Оптимально для детекции
    ALERT_COOLDOWN_SEC   = 7             # Чтобы не спамить в Telegram
    FPS_LIMIT_MS         = 100           # Нагрузка на CPU

    def __init__(self, model_path: str = "yolov8n.pt", parent=None):
        super().__init__(parent)
        self._running = False
        self._model = None
        self._last_alert_time = 0.0
        self._last_env_check  = 0.0
        self._evidence_dir = Path("_INTRUDERS")
        self._evidence_dir.mkdir(exist_ok=True)
        
        # МАГИЯ ДЛЯ EXE: Ищем нейросеть в папке _internal или рядом
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
            self._model_path = os.path.join(base_dir, "_internal", model_path)
            if not os.path.exists(self._model_path):
                self._model_path = os.path.join(base_dir, model_path)
        else:
            self._model_path = model_path

    def stop(self):
        self._running = False
        self.wait(3000)

    def run(self):
        # 1. Загрузка нейросети
        try:
            self._model = YOLO(self._model_path)
        except Exception as exc:
            self.camera_error.emit(f"Ошибка загрузки нейросети: {exc}")
            return

        # 2. Блокируем камеру для шпионского модуля
        SpyModule._camera_busy = True

        # 3. Инициализация захвата (DirectShow для Windows)
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            self.camera_error.emit("Камера недоступна. Проверьте подключение или настройки приватности.")
            SpyModule._camera_busy = False
            return

        self._running = True
        self.status_changed.emit(True)
        print("[VISION] ИИ-детекция и мониторинг среды запущены.")

        try:
            while self._running:
                ret, frame = cap.read()
                if not ret:
                    self.msleep(200)
                    continue

                now = time.time()

                # ─── 👁️ АНАЛИЗ ОКРУЖАЮЩЕЙ СРЕДЫ (РАЗ В 10 СЕКУНД) ───
                if now - self._last_env_check > 3:
                    self._last_env_check = now
                    self._analyze_environment(frame)

                # ─── 📱 ДЕТЕКЦИЯ ТЕЛЕФОНА (YOLO) ───
                self._process_frame(frame)
                
                self.msleep(self.FPS_LIMIT_MS)

        finally:
            cap.release()
            SpyModule._camera_busy = False
            self._running = False
            self.status_changed.emit(False)
            print("[VISION] ИИ-детекция остановлена.")

    def _analyze_environment(self, frame):
        """Проверка на саботаж с выводом отладки в консоль"""
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            brightness = np.mean(gray)
            blur_value = cv2.Laplacian(gray, cv2.CV_64F).var()

            # 🔥 ВЫВОДИМ РЕАЛЬНЫЕ ЦИФРЫ В КОНСОЛЬ
            print(f"[DEBUG VISION] Яркость: {brightness:.1f} | Шум/Фокус (Blur): {blur_value:.1f}")

            # Пороги стали мягче!
            if brightness < 60: # Было 30. Камеры почти никогда не дают 0 из-за шума.
                self.env_warning.emit("⚠️ Слишком темно! Угроза слепой зоны AI.")
            elif brightness > 240:
                self.env_warning.emit("⚠️ Сильный засвет объектива!")
            elif blur_value < 50: # Было 15. Смягчили, чтобы лучше ловил палец на линзе.
                self.env_warning.emit("⚠️ Камера перекрыта или расфокусирована!")
                
        except Exception as e:
            print(f"[VISION] Ошибка анализа среды: {e}")

    def _process_frame(self, frame):
        """Поиск смартфона в кадре"""
        results = self._model.predict(
            frame,
            classes=[self.PHONE_CLASS_ID],
            conf=self.CONFIDENCE_THRESHOLD,
            imgsz=640, # Можно поднять до 800 для четкости
            verbose=False
        )

        if not results or len(results[0].boxes) == 0:
            return

        now = time.time()
        if now - self._last_alert_time < self.ALERT_COOLDOWN_SEC:
            return

        self._last_alert_time = now
        
        # Рисуем рамку детекции для доказательства
        annotated_frame = results[0].plot()
        photo_path = self._save_evidence(annotated_frame, now)

        msg = (
            "🚨 ТРЕВОГА: ОБНАРУЖЕН СМАРТФОН!\n"
            "Зафиксирована попытка несанкционированной съемки экрана."
        )
        print(f"[VISION ALERT] {msg}")
        self.phone_detected.emit(msg, str(photo_path))

    def _save_evidence(self, annotated_frame, timestamp: float) -> Path:
        """Сохранение кадра с обведенным телефоном"""
        filename = self._evidence_dir / f"intruder_{int(timestamp)}.jpg"
        cv2.imwrite(str(filename), annotated_frame)
        return filename