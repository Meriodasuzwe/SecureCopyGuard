# ui/pages.py

import os
from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QFileDialog, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QLineEdit, QGroupBox, QApplication
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor

from ui.widgets import MetricCard, PolicyCard
from ui.theme import *
from db.database import Database

from core.file_locker   import FileLocker
from core.file_watcher  import FolderWatcher
from core.clipboard_guard import ClipboardGuard
from core.usb_monitor   import USBMonitor
from core.vision_protector import VisionProtector
from core.telegram_alerts  import send_telegram_alert


# ══════════════════════════════════════════════════════════════════════
#  DASHBOARD
# ══════════════════════════════════════════════════════════════════════

class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()
        self.target_folder = None
        self.is_armed      = False
        self.db            = Database()

        # Воркеры
        self.watcher       = FolderWatcher()
        self.clip_guard    = ClipboardGuard()
        self.usb_monitor   = USBMonitor()
        self.vision_thread = VisionProtector()

        self.setup_ui()
        self._connect_worker_signals()  # ← подключаем сигналы воркеров к слотам UI

        # Авто-обновление счётчика каждые 5 сек
        self.stats_timer = QTimer(self)
        self.stats_timer.timeout.connect(self.update_stats)
        self.stats_timer.start(5000)

        # Таймер мигания — используется при обнаружении телефона
        self._flash_timer  = QTimer(self)
        self._flash_count  = 0
        self._flash_timer.timeout.connect(self._do_flash)

    # ──────────────────────────────────────────────────────────────────
    #  UI
    # ──────────────────────────────────────────────────────────────────

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)

        # Заголовок
        header = QHBoxLayout()
        title  = QLabel("ОБЗОР СИСТЕМЫ")
        title.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 22px; font-weight: 600; letter-spacing: 1px;"
        )
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        # Метрики
        metrics = QHBoxLayout()
        metrics.setSpacing(20)
        self.card_folder  = MetricCard("Целевая директория", "Не задана",  ACCENT_BLUE)
        self.card_threats = MetricCard("Заблокировано угроз", "0",         STATUS_OK)
        self.card_status  = MetricCard("Статус ядра",         "ОЖИДАНИЕ",  TEXT_MUTED)
        metrics.addWidget(self.card_folder,  2)
        metrics.addWidget(self.card_threats, 1)
        metrics.addWidget(self.card_status,  1)
        layout.addLayout(metrics)

        # Панель управления
        panel = QFrame()
        panel.setStyleSheet(
            f"QFrame {{ background-color: {BG_SURFACE}; "
            f"border: 1px solid {BORDER_COLOR}; border-radius: 8px; }}"
        )
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 50, 0, 50)
        panel_layout.setAlignment(Qt.AlignCenter)

        self.led = QLabel()
        self.led.setFixedSize(24, 24)
        self.led.setStyleSheet(f"background-color: {TEXT_MUTED}; border-radius: 12px;")

        self.status_lbl = QLabel("СИСТЕМА ДЕАКТИВИРОВАНА")
        self.status_lbl.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 14px; font-weight: bold; "
            f"letter-spacing: 2px; margin-top: 15px;"
        )
        self.status_lbl.setAlignment(Qt.AlignCenter)

        led_row = QHBoxLayout()
        led_row.setAlignment(Qt.AlignCenter)
        led_row.addWidget(self.led)
        panel_layout.addLayout(led_row)
        panel_layout.addWidget(self.status_lbl)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(20)
        btn_row.setContentsMargins(0, 30, 0, 0)

        self.btn_select = QPushButton("ВЫБРАТЬ ДИРЕКТОРИЮ")
        self.btn_select.setFixedSize(220, 45)
        self.btn_select.setCursor(Qt.PointingHandCursor)
        self.btn_select.setStyleSheet(
            f"QPushButton {{ background-color: transparent; border: 1px solid {BORDER_COLOR}; "
            f"color: {TEXT_PRIMARY}; border-radius: 4px; font-weight: bold; font-size: 12px; "
            f"letter-spacing: 1px; }}"
            f"QPushButton:hover {{ border: 1px solid {ACCENT_BLUE}; color: {ACCENT_BLUE}; }}"
        )

        self.btn_arm = QPushButton("АКТИВИРОВАТЬ ЗАЩИТУ")
        self.btn_arm.setFixedSize(220, 45)
        self.btn_arm.setCheckable(True)
        self.btn_arm.setCursor(Qt.PointingHandCursor)
        self.btn_arm.setStyleSheet(
            f"QPushButton {{ background-color: {ACCENT_BLUE}; color: white; border: none; "
            f"border-radius: 4px; font-weight: bold; font-size: 12px; letter-spacing: 1px; }}"
            f"QPushButton:hover {{ background-color: #2563EB; }}"
            f"QPushButton:checked {{ background-color: {STATUS_DANGER}; }}"
        )

        btn_row.addStretch()
        btn_row.addWidget(self.btn_select)
        btn_row.addWidget(self.btn_arm)
        btn_row.addStretch()
        panel_layout.addLayout(btn_row)

        layout.addWidget(panel)
        layout.addStretch()

        # Подключение кнопок
        self.btn_select.clicked.connect(self.choose_directory)
        self.btn_arm.clicked.connect(self.toggle_protection)

    # ──────────────────────────────────────────────────────────────────
    #  Подключение сигналов воркеров → слоты UI
    #  ВСЁ межпоточное общение идёт ТОЛЬКО через сигналы Qt.
    # ──────────────────────────────────────────────────────────────────

    def _connect_worker_signals(self):
        # VisionProtector
        self.vision_thread.phone_detected.connect(self._on_phone_detected)
        self.vision_thread.camera_error.connect(
            lambda msg: self._log_and_notify("AI Vision", msg, level="High")
        )
        self.vision_thread.status_changed.connect(
            lambda active: print(f"[VISION] {'запущен' if active else 'остановлен'}")
        )

        # ClipboardGuard
        self.clip_guard.violation_detected.connect(
            lambda msg, _: self._log_and_notify("Clipboard Guard", msg, level="High")
        )

        # USBMonitor
        self.usb_monitor.device_connected.connect(self._on_usb_connected)
        self.usb_monitor.device_disconnected.connect(
            lambda drive: self._log_and_notify(
                "USB Guard", f"USB-устройство отключено: {drive or 'неизвестный диск'}", level="Low"
            )
        )

        # FolderWatcher — сигнал (policy_id, message)
        self.watcher.incident_detected.connect(self._on_file_incident)

    # ──────────────────────────────────────────────────────────────────
    #  Слоты (вызываются из основного потока UI через очередь сигналов)
    # ──────────────────────────────────────────────────────────────────

    def _on_file_incident(self, policy_id: int, message: str):
        """Реакция на событие файловой системы: лог + Telegram если критично."""
        level_map = {1: "Critical", 2: "High", 3: "Low"}
        level = level_map.get(policy_id, "Medium")
        self._log_and_notify("File Watcher", message, level=level)
        if policy_id in (1, 2):                     # только критичные — в Telegram
            send_telegram_alert(message)

    def _on_phone_detected(self, message: str, photo_path: str):
        """Реакция на телефон: лог + мигание + Telegram."""
        self._log_and_notify("AI Vision", message, level="Critical")
        self._start_flash()                              # мигание экрана
        send_telegram_alert(message, photo_path)        # Telegram с фото

    def _on_usb_connected(self, drive: str):
        msg = f"⚠️ USB-носитель подключён: {drive or 'неизвестный диск'}"
        self._log_and_notify("USB Guard", msg, level="High")
        send_telegram_alert(msg)

    def _log_and_notify(self, module: str, description: str, level: str = "Medium"):
        """Единая точка записи инцидента в БД и обновления UI."""
        level_map = {"Low": 1, "Medium": 2, "High": 3, "Critical": 3}
        self.db.log_incident(level_map.get(level, 2), f"[{module}] {description}")
        self.update_stats()

    # ──────────────────────────────────────────────────────────────────
    #  Мигание экрана (тревога при детекции телефона)
    # ──────────────────────────────────────────────────────────────────

    def _start_flash(self):
        """Запускает 6 миганий (3 цикла красный/нормальный)."""
        self._flash_count = 6
        self._flash_timer.start(200)  # 200 мс между сменами

    def _do_flash(self):
        if self._flash_count <= 0:
            self._flash_timer.stop()
            self.setStyleSheet("")  # сбрасываем стиль
            return
        if self._flash_count % 2 == 0:
            self.setStyleSheet("background-color: #7F1D1D;")  # тёмно-красный
        else:
            self.setStyleSheet("")
        self._flash_count -= 1

    # ──────────────────────────────────────────────────────────────────
    #  Управление защитой
    # ──────────────────────────────────────────────────────────────────

    def choose_directory(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите целевую директорию")
        if folder:
            self.target_folder = folder
            name = os.path.basename(folder) or folder
            self.card_folder.lbl_value.setText(f"/{name}")

    def toggle_protection(self):
        if not self.target_folder:
            self.btn_arm.setChecked(False)
            QMessageBox.warning(self, "Ошибка", "Сначала выберите директорию для защиты.")
            return

        self.is_armed = self.btn_arm.isChecked()
        policies      = self._read_policies()

        if self.is_armed:
            self._arm(policies)
        else:
            self._disarm()

        self.update_stats()

    def _read_policies(self) -> dict:
        """Читаем состояние переключателей политик из PoliciesPage."""
        p = self.window().page_policies
        return {
            "file_lock": p.policy_file_lock.is_active(),
            "clipboard": p.policy_clipboard.is_active(),
            "webcam":    p.policy_webcam.is_active(),
            "usb":       p.policy_usb.is_active(),
            "ai_vision": p.policy_ai_vision.is_active(),
            "siren":     p.policy_siren.is_active(),
        }

    def _arm(self, policies: dict):
        if policies["file_lock"]:
            FileLocker.lock_directory(self.target_folder)
        
        self.watcher.start(self.target_folder, use_camera=policies["webcam"])
        
        if policies["clipboard"]:
            self.clip_guard.start()
        
        if policies["usb"]:
            # Пересоздаём поток (QThread нельзя перезапустить)
            self.usb_monitor = USBMonitor()
            self.usb_monitor.device_connected.connect(self._on_usb_connected)
            self.usb_monitor.device_disconnected.connect(
                lambda d: self._log_and_notify("USB Guard", f"USB отключён: {d}", "Low")
            )
            self.usb_monitor.start()
        
        if policies["ai_vision"]:
            self.vision_thread = VisionProtector()
            self.vision_thread.phone_detected.connect(self._on_phone_detected)
            self.vision_thread.camera_error.connect(
                lambda m: self._log_and_notify("AI Vision", m, "High")
            )
            self.vision_thread.start()

        self.db.log_incident(3, "ЗАЩИТА АКТИВИРОВАНА")
        self._set_ui_armed(True)

    def _disarm(self):
        FileLocker.unlock_directory(self.target_folder)
        self.watcher.stop()
        self.clip_guard.stop()
        self.usb_monitor.stop()
        self.vision_thread.stop()

        self.db.log_incident(3, "ЗАЩИТА ДЕАКТИВИРОВАНА")
        self._set_ui_armed(False)

    def _set_ui_armed(self, armed: bool):
        if armed:
            self.led.setStyleSheet(
                f"background-color: {STATUS_OK}; border-radius: 12px; border: 2px solid #065F46;"
            )
            self.status_lbl.setText("СИСТЕМА АКТИВНА")
            self.status_lbl.setStyleSheet(
                f"color: {STATUS_OK}; font-size: 14px; font-weight: bold; letter-spacing: 2px; margin-top: 15px;"
            )
            self.btn_arm.setText("ДЕАКТИВИРОВАТЬ")
            self.btn_select.setEnabled(False)
            self.card_status.lbl_value.setText("АКТИВНО")
            self.card_status.lbl_value.setStyleSheet(
                f"color: {STATUS_OK}; font-size: 28px; font-weight: bold; border: none;"
            )
        else:
            self.led.setStyleSheet(f"background-color: {TEXT_MUTED}; border-radius: 12px; border: none;")
            self.status_lbl.setText("СИСТЕМА ДЕАКТИВИРОВАНА")
            self.status_lbl.setStyleSheet(
                f"color: {TEXT_MUTED}; font-size: 14px; font-weight: bold; letter-spacing: 2px; margin-top: 15px;"
            )
            self.btn_arm.setText("АКТИВИРОВАТЬ ЗАЩИТУ")
            self.btn_select.setEnabled(True)
            self.card_status.lbl_value.setText("ОЖИДАНИЕ")
            self.card_status.lbl_value.setStyleSheet(
                f"color: {TEXT_MUTED}; font-size: 28px; font-weight: bold; border: none;"
            )

    def update_stats(self):
        count = self.db.get_incident_count()
        self.card_threats.lbl_value.setText(str(count))
        if count > 0:
            self.card_threats.lbl_value.setStyleSheet(
                f"color: {STATUS_DANGER}; font-size: 28px; font-weight: bold; border: none;"
            )

    # Удалённое управление через Telegram-бота
    def remote_arm(self):
        if not self.btn_arm.isChecked():
            self.btn_arm.setChecked(True)
            self.toggle_protection()

    def remote_disarm(self):
        if self.btn_arm.isChecked():
            self.btn_arm.setChecked(False)
            self.toggle_protection()


# ══════════════════════════════════════════════════════════════════════
#  ПОЛИТИКИ
# ══════════════════════════════════════════════════════════════════════

class PoliciesPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(15)

        title = QLabel("ПОЛИТИКИ БЕЗОПАСНОСТИ")
        title.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 22px; font-weight: 600; letter-spacing: 1px;"
        )
        layout.addWidget(title)

        self.policy_file_lock = PolicyCard(
            "Блокировка файловой системы (Anti-Delete)",
            "Жёсткая блокировка файлов через os.chmod — запрет удаления и изменения."
        )
        self.policy_clipboard = PolicyCard(
            "Контроль буфера обмена (DLP)",
            "Перехват и блокировка копирования конфиденциальных данных (карты, пароли, email)."
        )
        self.policy_webcam = PolicyCard(
            "Фото-фиксация нарушителя (Webcam Trap)",
            "Снимок с веб-камеры при срабатывании любого из модулей защиты."
        )
        self.policy_usb = PolicyCard(
            "Контроль внешних носителей (USB Guard)",
            "Мгновенное уведомление при подключении USB-флешек и дисков."
        )
        self.policy_ai_vision = PolicyCard(
            "AI Vision: Детекция гаджетов (YOLOv8)",
            "Нейросеть детектирует смартфоны рядом с экраном — мигание + Telegram-алерт с фото.",
            default_state=False
        )
        self.policy_siren = PolicyCard(
            "Аудио-оповещение (Siren Alarm)",
            "Звуковой сигнал тревоги при обнаружении инцидента.",
            default_state=False
        )

        for card in [
            self.policy_file_lock, self.policy_clipboard,
            self.policy_webcam,    self.policy_usb,
            self.policy_ai_vision, self.policy_siren
        ]:
            layout.addWidget(card)

        layout.addStretch()


# ══════════════════════════════════════════════════════════════════════
#  ЖУРНАЛ
# ══════════════════════════════════════════════════════════════════════

class LogsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.setup_ui()
        self.load_logs()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        header = QHBoxLayout()
        title  = QLabel("ЖУРНАЛ ИНЦИДЕНТОВ")
        title.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 22px; font-weight: 600; letter-spacing: 1px;"
        )
        btn_refresh = QPushButton("🔄 ОБНОВИТЬ")
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.setStyleSheet(
            f"QPushButton {{ background-color: transparent; border: 1px solid {BORDER_COLOR}; "
            f"color: {TEXT_PRIMARY}; border-radius: 4px; padding: 8px 15px; font-weight: bold; "
            f"font-size: 11px; }} QPushButton:hover {{ border: 1px solid {ACCENT_BLUE}; color: {ACCENT_BLUE}; }}"
        )
        btn_refresh.clicked.connect(self.refresh_all)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(btn_refresh)
        layout.addLayout(header)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ВРЕМЯ", "УРОВЕНЬ", "МОДУЛЬ", "ОПИСАНИЕ"])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet(
            f"QTableWidget {{ background-color: {BG_SURFACE}; border: 1px solid {BORDER_COLOR}; "
            f"border-radius: 8px; color: {TEXT_PRIMARY}; font-size: 12px; }}"
            f"QHeaderView::section {{ background-color: {BG_BASE}; color: {TEXT_MUTED}; "
            f"font-size: 10px; font-weight: bold; padding: 10px; border: none; "
            f"border-bottom: 2px solid {BORDER_COLOR}; }}"
        )
        layout.addWidget(self.table)

    def refresh_all(self):
        self.load_logs()
        self.window().page_dash.update_stats()

    def load_logs(self):
        self.table.setRowCount(0)
        logs = self.db.get_recent_logs(50)
        level_colors = {
            "High":     STATUS_DANGER,
            "Critical": STATUS_DANGER,
            "Medium":   "#F59E0B",
            "Low":      TEXT_MUTED,
        }
        for row_idx, log in enumerate(logs):
            self.table.insertRow(row_idx)
            timestamp, policy_name, threat_level, details = log
            color = level_colors.get(str(threat_level), TEXT_PRIMARY)

            item_level = QTableWidgetItem(str(threat_level))
            item_level.setForeground(QColor(color))

            self.table.setItem(row_idx, 0, QTableWidgetItem(str(timestamp)))
            self.table.setItem(row_idx, 1, item_level)
            self.table.setItem(row_idx, 2, QTableWidgetItem(str(policy_name)))
            self.table.setItem(row_idx, 3, QTableWidgetItem(str(details)))


# ══════════════════════════════════════════════════════════════════════
#  НАСТРОЙКИ
# ══════════════════════════════════════════════════════════════════════

class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(25)

        title = QLabel("НАСТРОЙКИ СИСТЕМЫ")
        title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        # Безопасность
        pin_box = QGroupBox("Безопасность администратора")
        pin_box.setStyleSheet(
            f"color: {TEXT_PRIMARY}; border: 1px solid {BORDER_COLOR}; padding: 15px; font-weight: bold;"
        )
        pin_layout = QVBoxLayout()

        self.pin_input = QLineEdit()
        self.pin_input.setPlaceholderText("Введите новый Master-PIN")
        self.pin_input.setEchoMode(QLineEdit.Password)
        self.pin_input.setStyleSheet(
            "padding: 10px; background: #1E293B; color: white; border-radius: 5px; border: 1px solid #334155;"
        )

        btn_save = QPushButton("ОБНОВИТЬ КОНФИГУРАЦИЮ")
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setStyleSheet(
            f"background-color: {ACCENT_BLUE}; color: white; padding: 12px; font-weight: bold; border-radius: 4px;"
        )

        pin_layout.addWidget(QLabel("Управление доступом (PIN-код):"))
        pin_layout.addWidget(self.pin_input)
        pin_layout.addWidget(btn_save)
        pin_box.setLayout(pin_layout)
        layout.addWidget(pin_box)

        # Аппаратное обеспечение
        info_box = QGroupBox("Аппаратное ускорение")
        info_box.setStyleSheet(
            f"color: {TEXT_PRIMARY}; border: 1px solid {BORDER_COLOR}; padding: 15px; font-weight: bold;"
        )
        info_layout = QVBoxLayout()
        info_layout.addWidget(QLabel("AI Engine: YOLOv8 Nano (yolov8n.pt)"))
        info_layout.addWidget(QLabel(f"Storage: {os.getenv('DATABASE_NAME', 'dlp_logs.db')}"))
        info_layout.addWidget(QLabel("Evidence: _INTRUDERS/ (jpg кадры с камеры)"))
        info_box.setLayout(info_layout)
        layout.addWidget(info_box)

        layout.addStretch()