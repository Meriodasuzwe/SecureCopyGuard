# core/vision_protector.py

import cv2
import time
import os
from pathlib import Path
from ultralytics import YOLO
from PyQt5.QtCore import QThread, pyqtSignal


class VisionProtector(QThread):
    """
    ИИ-поток детекции смартфонов через YOLOv8.
    Общается с UI исключительно через Qt-сигналы — никаких прямых вызовов UI из потока.
    """

    # Сигналы: поток → UI/Dashboard
    phone_detected = pyqtSignal(str, str)  # (сообщение, путь_к_фото)
    status_changed = pyqtSignal(bool)      # True = запущен, False = остановлен
    camera_error   = pyqtSignal(str)       # ошибка открытия камеры

    # COCO dataset: class 67 = "cell phone"
    PHONE_CLASS_ID = 67
    CONFIDENCE_THRESHOLD = 0.50
    ALERT_COOLDOWN_SEC   = 7     # не спамим чаще раза в 7 сек
    FPS_LIMIT_MS         = 100   # ~10 FPS — щадим GPU/CPU

    def __init__(self, model_path: str = "yolov8n.pt", parent=None):
        super().__init__(parent)
        self._running = False
        self._model_path = model_path
        self._model = None
        self._last_alert_time = 0.0

        # Папка для хранения кадров-доказательств
        self._evidence_dir = Path("_INTRUDERS")
        self._evidence_dir.mkdir(exist_ok=True)

    # ------------------------------------------------------------------
    # Публичный интерфейс
    # ------------------------------------------------------------------

    def stop(self):
        """Мягкая остановка: выставляем флаг, ждём завершения потока."""
        self._running = False
        self.wait(3000)  # даём 3 сек на завершение, потом Qt сам прибьёт

    # ------------------------------------------------------------------
    # Основной цикл (выполняется в отдельном потоке)
    # ------------------------------------------------------------------

    def run(self):
        # Загружаем модель один раз
        try:
            self._model = YOLO(self._model_path)
        except Exception as exc:
            self.camera_error.emit(f"Не удалось загрузить модель YOLO: {exc}")
            return

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            self.camera_error.emit("Камера недоступна. Проверьте подключение.")
            return

        self._running = True
        self.status_changed.emit(True)
        print("[VISION] ИИ-детекция запущена.")

        try:
            while self._running:
                ret, frame = cap.read()
                if not ret:
                    # Одиночный сбой чтения — пробуем снова
                    self.msleep(200)
                    continue

                self._process_frame(frame)
                self.msleep(self.FPS_LIMIT_MS)

        finally:
            # Гарантированное освобождение камеры при любом выходе
            cap.release()
            self._running = False
            self.status_changed.emit(False)
            print("[VISION] ИИ-детекция остановлена.")

    # ------------------------------------------------------------------
    # Вспомогательные методы
    # ------------------------------------------------------------------

    def _process_frame(self, frame):
        """Прогоняем кадр через YOLO, реагируем на телефон."""
        results = self._model.predict(
            frame,
            classes=[self.PHONE_CLASS_ID],
            conf=self.CONFIDENCE_THRESHOLD,
            verbose=False
        )

        if not results or len(results[0].boxes) == 0:
            return  # телефона нет — идём дальше

        now = time.time()
        if now - self._last_alert_time < self.ALERT_COOLDOWN_SEC:
            return  # кулдаун ещё не истёк

        self._last_alert_time = now

        # Сохраняем кадр с bounding box как доказательство
        photo_path = self._save_evidence(results[0].plot(), now)

        msg = (
            "⚠️ ОБНАРУЖЕН СМАРТФОН: возможная попытка фотофиксации экрана!\n"
            f"Кадр сохранён: {photo_path}"
        )
        print(f"[VISION ALERT] {msg}")

        # Уведомляем UI через сигнал — UI сам решит что делать (мигать, сирена, Telegram)
        self.phone_detected.emit(msg, str(photo_path))

    def _save_evidence(self, annotated_frame, timestamp: float) -> Path:
        """Сохраняет аннотированный кадр и возвращает путь к файлу."""
        filename = self._evidence_dir / f"phone_{int(timestamp)}.jpg"
        cv2.imwrite(str(filename), annotated_frame)
        return filename