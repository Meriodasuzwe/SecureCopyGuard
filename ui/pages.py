# ui/pages.py

import os
import random
from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGridLayout,
    QFrame, QFileDialog, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QLineEdit, QCheckBox, QGraphicsOpacityEffect, QDialog
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor

from ui.widgets import MetricCard, PolicyCard
from ui.theme import *
from db.database import Database
from config import set_config_value, verify_pin, hash_pin, get_config_value

from core.file_locker   import FileLocker
from core.file_watcher  import FolderWatcher
from core.clipboard_guard import ClipboardGuard
from core.usb_monitor   import USBMonitor
from core.vision_protector import VisionProtector
from core.telegram_alerts  import send_telegram_alert
from core.autostart import enable_autostart, disable_autostart, is_enabled as autostart_is_enabled


# ══════════════════════════════════════════════════════════════════════
#  DASHBOARD
# ══════════════════════════════════════════════════════════════════════
class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()
        self.target_folder = None
        self.is_armed      = False
        self.db            = Database()

        self.watcher       = FolderWatcher()
        self.clip_guard    = ClipboardGuard()
        self.usb_monitor   = USBMonitor()
        self.vision_thread = VisionProtector()

        self.setup_ui()
        self._connect_worker_signals()

        self.stats_timer = QTimer(self)
        self.stats_timer.timeout.connect(self.update_stats)
        self.stats_timer.start(5000)

        self._flash_timer  = QTimer(self)
        self._flash_count  = 0
        self._flash_timer.timeout.connect(self._do_flash)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)

        header = QHBoxLayout()
        title  = QLabel("ОБЗОР СИСТЕМЫ")
        title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 22px; font-weight: 600; letter-spacing: 1px;")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        metrics = QHBoxLayout()
        metrics.setSpacing(20)
        self.card_folder  = MetricCard("Целевая директория", "Не задана",  ACCENT_BLUE)
        self.card_threats = MetricCard("Заблокировано угроз", "0",         STATUS_OK)
        self.card_status  = MetricCard("Статус ядра",         "ОЖИДАНИЕ",  TEXT_MUTED)
        metrics.addWidget(self.card_folder,  2)
        metrics.addWidget(self.card_threats, 1)
        metrics.addWidget(self.card_status,  1)
        layout.addLayout(metrics)

        panel = QFrame()
        panel.setStyleSheet(f"QFrame {{ background-color: {BG_SURFACE}; border: 1px solid {BORDER_COLOR}; border-radius: 8px; }}")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 50, 0, 50)
        panel_layout.setAlignment(Qt.AlignCenter)

        self.led = QLabel()
        self.led.setFixedSize(24, 24)
        self.led.setStyleSheet(f"background-color: {TEXT_MUTED}; border-radius: 12px;")

        self.status_lbl = QLabel("СИСТЕМА ДЕАКТИВИРОВАНА")
        self.status_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 14px; font-weight: bold; letter-spacing: 2px; margin-top: 15px;")
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
        self.btn_select.setStyleSheet(f"""
            QPushButton {{ background-color: transparent; border: 1px solid {BORDER_COLOR}; color: {TEXT_PRIMARY}; border-radius: 4px; font-weight: bold; font-size: 12px; letter-spacing: 1px; }}
            QPushButton:hover {{ border: 1px solid {ACCENT_BLUE}; color: {ACCENT_BLUE}; }}
        """)

        self.btn_arm = QPushButton("АКТИВИРОВАТЬ ЗАЩИТУ")
        self.btn_arm.setFixedSize(220, 45)
        self.btn_arm.setCheckable(True)
        self.btn_arm.setCursor(Qt.PointingHandCursor)
        self.btn_arm.setStyleSheet(f"""
            QPushButton {{ background-color: {ACCENT_BLUE}; color: white; border: none; border-radius: 4px; font-weight: bold; font-size: 12px; letter-spacing: 1px; }}
            QPushButton:hover {{ background-color: #2563EB; }}
            QPushButton:checked {{ background-color: {STATUS_DANGER}; }}
        """)

        btn_row.addStretch()
        btn_row.addWidget(self.btn_select)
        btn_row.addWidget(self.btn_arm)
        btn_row.addStretch()
        panel_layout.addLayout(btn_row)

        layout.addWidget(panel)
        layout.addStretch()

        self.btn_select.clicked.connect(self.choose_directory)
        self.btn_arm.clicked.connect(self.toggle_protection)

    def _connect_worker_signals(self):
        self.vision_thread.phone_detected.connect(self._on_phone_detected)
        self.vision_thread.camera_error.connect(self._on_camera_error)
        
        def _on_clipboard_violation(msg, snippet):
            self._log_and_notify("Clipboard Guard", msg, level="High")
            self._check_and_play_siren()
            from core.spy_module import SpyModule
            photo_path = SpyModule.take_photo() 
            if not photo_path: photo_path = SpyModule.take_screenshot()
            send_telegram_alert(f"{msg}\n\nУтечка данных:\n{snippet}", photo_path)

        self.clip_guard.violation_detected.connect(_on_clipboard_violation)

    def _on_camera_error(self, msg):
        QMessageBox.warning(self, "Аппаратный сбой", f"Веб-камера не найдена или заблокирована.\n\nМодуль 'AI Vision' будет автоматически отключен.\nЗахват доказательств переведен в режим скриншотов.")
        self._log_and_notify("Система", "AI Vision отключен (нет камеры)", level="Low")
        if hasattr(self.window(), 'page_policies'):
            self.window().page_policies.policy_ai_vision.toggle.setChecked(False)
            self.window().page_policies.save_all_policies()
        self.vision_thread.stop()

    def _on_file_incident(self, policy_id: int, message: str):
        level_map = {1: "Critical", 2: "High", 3: "Low"}
        level = level_map.get(policy_id, "Medium")
        self._log_and_notify("File Watcher", message, level=level)
        if policy_id in (1, 2):
            self._check_and_play_siren()
            from core.spy_module import SpyModule
            photo_path = SpyModule.take_photo() or SpyModule.take_screenshot()
            send_telegram_alert(message, photo_path)

    def _on_phone_detected(self, message: str, photo_path: str):
        self._log_and_notify("AI Vision", message, level="Critical")
        self._start_flash()
        self._check_and_play_siren()
        send_telegram_alert(message, photo_path)

    def _on_usb_connected(self, drive: str):
        msg = f"⚠️ USB-носитель подключён: {drive or 'неизвестный диск'}"
        self._log_and_notify("USB Guard", msg, level="High")
        self._check_and_play_siren()
        send_telegram_alert(msg)

    def _log_and_notify(self, module: str, description: str, level: str = "Medium"):
        level_map = {"Critical": 1, "High": 1, "Medium": 2, "Low": 3}
        self.db.log_incident(level_map.get(level, 2), f"[{module}] {description}")
        self.update_stats()

    def _start_flash(self):
        self._flash_count = 6
        self._flash_timer.start(200)

    def _do_flash(self):
        if self._flash_count <= 0:
            self._flash_timer.stop()
            self.setStyleSheet("")
            return
        if self._flash_count % 2 == 0:
            self.setStyleSheet("background-color: #7F1D1D;")
        else:
            self.setStyleSheet("")
        self._flash_count -= 1

    def choose_directory(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите целевую директорию")
        if folder:
            self.target_folder = folder
            name = os.path.basename(folder) or folder
            self.card_folder.lbl_value.setText(f"/{name}")
            set_config_value("protected_folder", folder)
    
    def restore_folder(self, folder_path: str):
        if folder_path and os.path.exists(folder_path):
            self.target_folder = folder_path
            name = os.path.basename(folder_path) or folder_path
            self.card_folder.lbl_value.setText(f"/{name}")

    def toggle_protection(self):
        if not self.target_folder:
            self.btn_arm.setChecked(False)
            QMessageBox.warning(self, "Ошибка", "Сначала выберите директорию для защиты.")
            return

        if self.is_armed and not self.btn_arm.isChecked():
            dialog = PinDialog(self)
            if dialog.exec_() != QDialog.Accepted:
                self.btn_arm.setChecked(True) 
                return 

        self.is_armed = self.btn_arm.isChecked()
        policies      = self._read_policies()

        if self.is_armed:
            self._arm(policies)
        else:
            self._disarm()

        self.update_stats()

    def _read_policies(self) -> dict:
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
        self.window().page_policies.save_all_policies()
        if policies["file_lock"]: FileLocker.lock_directory(self.target_folder)
        self.watcher.start(self.target_folder, use_camera=policies["webcam"])
        if policies["clipboard"]:
            self.clip_guard.set_watched_folder(self.target_folder)
            self.clip_guard.start()
        if policies["usb"]:
            self.usb_monitor = USBMonitor()
            self.usb_monitor.device_connected.connect(self._on_usb_connected)
            self.usb_monitor.device_disconnected.connect(lambda d: self._log_and_notify("USB Guard", f"USB отключён: {d}", "Low"))
            self.usb_monitor.start()
        if policies["ai_vision"]:
            self.vision_thread = VisionProtector()
            self.vision_thread.phone_detected.connect(self._on_phone_detected)
            self.vision_thread.camera_error.connect(lambda m: self._log_and_notify("AI Vision", m, "High"))
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
        if hasattr(self.window(), 'page_policies'):
            self.window().page_policies.set_locked(armed)

        if armed:
            self.led.setStyleSheet(f"background-color: {STATUS_OK}; border-radius: 12px; border: 2px solid #065F46;")
            self.status_lbl.setText("СИСТЕМА АКТИВНА")
            self.status_lbl.setStyleSheet(f"color: {STATUS_OK}; font-size: 14px; font-weight: bold; letter-spacing: 2px; margin-top: 15px;")
            self.btn_arm.setText("ДЕАКТИВИРОВАТЬ")
            self.btn_select.setEnabled(False)
            self.card_status.lbl_value.setText("АКТИВНО")
            self.card_status.lbl_value.setStyleSheet(f"color: {STATUS_OK}; font-size: 28px; font-weight: bold; border: none;")
        else:
            self.led.setStyleSheet(f"background-color: {TEXT_MUTED}; border-radius: 12px; border: none;")
            self.status_lbl.setText("СИСТЕМА ДЕАКТИВИРОВАНА")
            self.status_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 14px; font-weight: bold; letter-spacing: 2px; margin-top: 15px;")
            self.btn_arm.setText("АКТИВИРОВАТЬ ЗАЩИТУ")
            self.btn_select.setEnabled(True)
            self.card_status.lbl_value.setText("ОЖИДАНИЕ")
            self.card_status.lbl_value.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 28px; font-weight: bold; border: none;")

    def update_stats(self):
        count = self.db.get_incident_count()
        self.card_threats.lbl_value.setText(str(count))
        if count > 0:
            self.card_threats.lbl_value.setStyleSheet(f"color: {STATUS_DANGER}; font-size: 28px; font-weight: bold; border: none;")

    def remote_arm(self):
        if not self.btn_arm.isChecked():
            self.btn_arm.setChecked(True)
            self.toggle_protection()

    def remote_disarm(self):
        if self.btn_arm.isChecked():
            self.btn_arm.setChecked(False)
            self.toggle_protection()
    
    def _check_and_play_siren(self):
        if self._read_policies().get("siren"):
            from core.spy_module import SpyModule
            SpyModule.play_siren()


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
        title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 22px; font-weight: 600; letter-spacing: 1px;")
        layout.addWidget(title)

        s_file = get_config_value("pol_file", True)
        s_clip = get_config_value("pol_clip", True)
        s_webc = get_config_value("pol_webcam", True)
        s_usb  = get_config_value("pol_usb", True)
        s_ai   = get_config_value("pol_ai", False)    
        s_siren= get_config_value("pol_siren", False) 

        self.policy_file_lock = PolicyCard("Anti-Delete (Блокировка ФС)", "Жёсткий запрет удаления и изменения файлов ОС.", default_state=s_file)
        self.policy_clipboard = PolicyCard("Контроль буфера обмена", "Блокировка копирования конфиденциальных данных.", default_state=s_clip)
        self.policy_webcam    = PolicyCard("Webcam Trap", "Тайная фото-фиксация нарушителя при любом инциденте.", default_state=s_webc)
        self.policy_usb       = PolicyCard("USB Guard", "Блокировка и уведомление о подключении флешек.", default_state=s_usb)
        self.policy_ai_vision = PolicyCard("AI Vision (YOLOv8)", "Нейросеть детектирует смартфоны, наведенные на экран.", default_state=s_ai)
        self.policy_siren     = PolicyCard("Siren Alarm", "Громкий звуковой сигнал тревоги при утечке.", default_state=s_siren)

        grid = QGridLayout()
        grid.setSpacing(20)
        grid.addWidget(self.policy_file_lock, 0, 0)
        grid.addWidget(self.policy_clipboard, 0, 1)
        grid.addWidget(self.policy_webcam, 1, 0)
        grid.addWidget(self.policy_usb, 1, 1)
        grid.addWidget(self.policy_ai_vision, 2, 0)
        grid.addWidget(self.policy_siren, 2, 1)

        layout.addLayout(grid)
        layout.addStretch()

    def get_policies(self):
        return {
            "file_lock": self.policy_file_lock.is_active(),
            "clipboard": self.policy_clipboard.is_active(),
            "webcam":    self.policy_webcam.is_active(),
            "usb":       self.policy_usb.is_active(),
            "ai_vision": self.policy_ai_vision.is_active(),
            "siren":     self.policy_siren.is_active(),
        }

    def save_all_policies(self):
        p = self.get_policies()
        set_config_value("pol_file", p["file_lock"])
        set_config_value("pol_clip", p["clipboard"])
        set_config_value("pol_webcam", p["webcam"])
        set_config_value("pol_usb", p["usb"])
        set_config_value("pol_ai", p["ai_vision"])
        set_config_value("pol_siren", p["siren"])

    def set_locked(self, is_locked: bool):
        for card in [self.policy_file_lock, self.policy_clipboard, self.policy_webcam, self.policy_usb, self.policy_ai_vision, self.policy_siren]:
            card.setEnabled(not is_locked) 
            effect = QGraphicsOpacityEffect()
            effect.setOpacity(0.4 if is_locked else 1.0)
            card.setGraphicsEffect(effect)


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
        title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 22px; font-weight: 600; letter-spacing: 1px;")
        
        btn_refresh = QPushButton("🔄 ОБНОВИТЬ")
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.setStyleSheet(f"""
            QPushButton {{ background-color: transparent; border: 1px solid {BORDER_COLOR}; color: {TEXT_PRIMARY}; border-radius: 4px; padding: 8px 15px; font-weight: bold; font-size: 11px; }}
            QPushButton:hover {{ border: 1px solid {ACCENT_BLUE}; color: {ACCENT_BLUE}; }}
        """)
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
        
        self.table.setStyleSheet(f"""
            QTableWidget {{ background-color: {BG_SURFACE}; border: 1px solid {BORDER_COLOR}; border-radius: 8px; color: {TEXT_PRIMARY}; font-size: 12px; }}
            QHeaderView::section {{ background-color: {BG_BASE}; color: {TEXT_MUTED}; font-size: 10px; font-weight: bold; padding: 10px; border: none; border-bottom: 2px solid {BORDER_COLOR}; }}
        """)
        layout.addWidget(self.table)

    def refresh_all(self):
        self.load_logs()
        self.window().page_dash.update_stats()

    def load_logs(self):
        self.table.setRowCount(0)
        logs = self.db.get_recent_logs(50)
        level_colors = {"High": STATUS_DANGER, "Critical": STATUS_DANGER, "Medium": "#F59E0B", "Low": TEXT_MUTED}
        
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
#  НАСТРОЙКИ (CONTROL PANEL STYLE - ИДЕАЛЬНЫЕ ПРОПОРЦИИ)
# ══════════════════════════════════════════════════════════════════════
class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(25)

        title = QLabel("ПАНЕЛЬ УПРАВЛЕНИЯ ЯДРОМ")
        title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 24px; font-weight: 800; letter-spacing: 1px;")
        main_layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(25)

        # ── 1. Карточка PIN и Секретного слова ──
        pin_frame = self._create_card("🛡️ УПРАВЛЕНИЕ ДОСТУПОМ", "Настройка Master-PIN и секретного слова для офлайн-доступа.")
        btn_change_pin = self._create_action_btn("Настроить безопасность")
        btn_change_pin.clicked.connect(self.open_pin_dialog)
        pin_frame.layout().addWidget(btn_change_pin, alignment=Qt.AlignCenter)
        pin_frame.layout().addStretch() # Пружина снизу для центрирования
        grid.addWidget(pin_frame, 0, 0)

        # ── 2. Карточка Telegram ──
        tg_frame = self._create_card("💬 ИНТЕГРАЦИЯ ОПОВЕЩЕНИЙ", "Подключение Telegram Bot для отправки отчетов и фото.")
        btn_change_tg = self._create_action_btn("Настроить Telegram")
        btn_change_tg.clicked.connect(self.open_tg_dialog)
        tg_frame.layout().addWidget(btn_change_tg, alignment=Qt.AlignCenter)
        tg_frame.layout().addStretch() # Пружина снизу для центрирования
        grid.addWidget(tg_frame, 0, 1)

        # ── 3. Карточка Автозапуска ──
        auto_frame = self._create_card("🚀 СИСТЕМНЫЕ ПАРАМЕТРЫ", "Интеграция агента защиты с автозагрузкой ОС Windows.")
        
        self.cb_autostart = QCheckBox("Запускать вместе с Windows")
        try: self.cb_autostart.setChecked(autostart_is_enabled())
        except: pass
        self.cb_autostart.setStyleSheet(f"""
            QCheckBox {{ font-size: 14px; font-weight: bold; color: {TEXT_PRIMARY}; border: none; background: transparent; margin-top: 10px; }} 
            QCheckBox::indicator {{ width: 22px; height: 22px; border: 2px solid {BORDER_COLOR}; border-radius: 6px; background: {BG_SURFACE}; }} 
            QCheckBox::indicator:checked {{ background: {ACCENT_BLUE}; border-color: {ACCENT_BLUE}; }}
        """)
        self.cb_autostart.stateChanged.connect(self._toggle_autostart)

        auto_frame.layout().addWidget(self.cb_autostart, alignment=Qt.AlignCenter)
        auto_frame.layout().addStretch() # Пружина снизу для центрирования
        grid.addWidget(auto_frame, 1, 0)

        # ── 4. Карточка Инфо ──
        info_frame = self._create_card("⚙️ ТЕХНИЧЕСКАЯ ИНФОРМАЦИЯ", "Рабочие директории и используемые нейросетевые модули.")
        lbl_style = f"font-size: 12px; color: {TEXT_MUTED}; border: none; background: transparent; line-height: 1.5;"
        info_lbl = QLabel("• AI Engine: YOLOv8 Nano\n• Storage: dlp_logs.db\n• Evidence Cache: _INTRUDERS/")
        info_lbl.setStyleSheet(lbl_style)
        info_frame.layout().addWidget(info_lbl, alignment=Qt.AlignCenter)
        info_frame.layout().addStretch() # Пружина снизу для центрирования
        grid.addWidget(info_frame, 1, 1)

        # Магия: Заставляем сетку равномерно растягиваться
        grid.setRowStretch(0, 1)
        grid.setRowStretch(1, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        main_layout.addLayout(grid)

        # Подвал
        footer = QLabel("Licensed to Rakhat Aliev | SecureCopyGuard Enterprise v3.0")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet(f"color: #475569; font-size: 11px; font-weight: bold; margin-top: 10px;")
        main_layout.addWidget(footer)

    def _create_card(self, title, desc):
        """Создает карточку с контентом, отцентрированным по вертикали и горизонтали"""
        frame = QFrame()
        frame.setStyleSheet(f"QFrame {{ background-color: {BG_SURFACE}; border: 1px solid {BORDER_COLOR}; border-radius: 12px; }}")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        layout.addStretch() # Пружина сверху для центрирования
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 16px; font-weight: 800; border: none; background: transparent;")
        lbl_title.setAlignment(Qt.AlignCenter)
        
        lbl_desc = QLabel(desc)
        lbl_desc.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px; border: none; background: transparent;")
        lbl_desc.setWordWrap(True)
        lbl_desc.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_desc)
        return frame

    def _create_action_btn(self, text):
        btn = QPushButton(text)
        btn.setFixedSize(220, 45) # Фиксируем размер кнопки для красоты
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{ background-color: transparent; border: 1px solid {ACCENT_BLUE}; color: {ACCENT_BLUE}; font-weight: bold; font-size: 13px; border-radius: 8px; margin-top: 10px; }}
            QPushButton:hover {{ background-color: rgba(14, 165, 233, 0.1); }}
        """)
        return btn

    def open_pin_dialog(self): ConfigPinDialog(self).exec_()
    def open_tg_dialog(self): ConfigTelegramDialog(self).exec_()

    def _toggle_autostart(self, state):
        if state == Qt.Checked:
            enable_autostart(); set_config_value("autostart", True)
        else:
            disable_autostart(); set_config_value("autostart", False)


# ══════════════════════════════════════════════════════════════════════
#  ПРОДВИНУТОЕ ОКНО НАСТРОЙКИ PIN И СЕКРЕТНОГО СЛОВА (ЗАЩИТА ОТ ПЕРЕЗАПИСИ)
# ══════════════════════════════════════════════════════════════════════
class ConfigPinDialog(QDialog):
    """Шикарное окно настройки доступа (с одноразовым вводом секретного слова)"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки Безопасности")
        self.setFixedSize(500, 580)
        self.setStyleSheet(f"background-color: {BG_BASE}; color: {TEXT_PRIMARY};")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)
        
        lbl = QLabel("🛡️ УПРАВЛЕНИЕ ДОСТУПОМ")
        lbl.setStyleSheet("font-size: 16px; font-weight: 900; letter-spacing: 1px;")
        layout.addWidget(lbl, alignment=Qt.AlignCenter)

        # ─── БЛОК ИНСТРУКЦИИ ───
        guide_frame = QFrame()
        guide_frame.setStyleSheet(f"background-color: {BG_SURFACE}; border: 1px solid {BORDER_COLOR}; border-radius: 8px;")
        guide_layout = QVBoxLayout(guide_frame)
        guide_layout.setContentsMargins(20, 20, 20, 20)
        guide_layout.setSpacing(10)

        guide_title = QLabel("📖 Как работает система доступа:")
        guide_title.setStyleSheet("font-weight: bold; font-size: 13px; border: none;")
        guide_layout.addWidget(guide_title)

        lbl1 = QLabel("<b>Master-PIN:</b> Ваш основной 4-значный код для отключения защиты ядра и изменения настроек.")
        lbl1.setStyleSheet("color: #94A3B8; font-size: 12px; border: none;")
        lbl1.setWordWrap(True)
        guide_layout.addWidget(lbl1)

        lbl2 = QLabel("<b>Секретное слово:</b> Используется для экстренного сброса PIN-кода, если ПК отключен от интернета.")
        lbl2.setStyleSheet("color: #94A3B8; font-size: 12px; border: none;")
        lbl2.setWordWrap(True)
        guide_layout.addWidget(lbl2)

        layout.addWidget(guide_frame)

        # ─── ВВОД ДАННЫХ ───
        input_style = f"border: 1px solid {BORDER_COLOR}; border-radius: 8px; padding: 5px 15px; font-size: 14px; background-color: {BG_SURFACE};"
        
        self.pin_old = QLineEdit()
        self.pin_old.setEchoMode(QLineEdit.Password)
        self.pin_old.setPlaceholderText("Текущий Master-PIN (если задан)")
        self.pin_old.setFixedHeight(45)
        self.pin_old.setStyleSheet(input_style)
        layout.addWidget(self.pin_old)

        pin_row = QHBoxLayout()
        self.pin_new = QLineEdit()
        self.pin_new.setEchoMode(QLineEdit.Password)
        self.pin_new.setPlaceholderText("Новый PIN")
        self.pin_new.setFixedHeight(45)
        self.pin_new.setStyleSheet(input_style)
        
        self.pin_conf = QLineEdit()
        self.pin_conf.setEchoMode(QLineEdit.Password)
        self.pin_conf.setPlaceholderText("Повторите PIN")
        self.pin_conf.setFixedHeight(45)
        self.pin_conf.setStyleSheet(input_style)
        
        pin_row.addWidget(self.pin_new)
        pin_row.addWidget(self.pin_conf)
        layout.addLayout(pin_row)

        # ─── СЕКРЕТНОЕ СЛОВО (ОДНОРАЗОВАЯ ЗАПИСЬ) ───
        self.sec_word = QLineEdit()
        self.sec_word.setFixedHeight(45)
        
        # Проверяем, задано ли уже слово
        self.is_word_locked = bool(get_config_value("sec_answer", ""))

        if self.is_word_locked:
            # 🔒 СЛОВО УЖЕ ЗАДАНО - НАМЕРТВО БЛОКИРУЕМ ПОЛЕ
            self.sec_word.setReadOnly(True)
            self.sec_word.setStyleSheet(f"border: 1px dashed {BORDER_COLOR}; border-radius: 8px; padding: 5px 15px; font-size: 13px; background-color: {BG_BASE}; color: {STATUS_OK}; font-weight: bold;")
            self.sec_word.setText("✅ Слово надежно зафиксировано в ядре")
            layout.addWidget(self.sec_word)
        else:
            # 🔓 СЛОВА НЕТ - РАЗРЕШАЕМ ВВОД
            self.sec_word.setStyleSheet(input_style)
            self.sec_word.setPlaceholderText("Секретное слово (например: Караганда)")
            layout.addWidget(self.sec_word)
            
            # Показываем алерт только если слово еще не задано
            warning_lbl = QLabel("⚠️ ВНИМАНИЕ: Слово задается ТОЛЬКО ОДИН РАЗ! Изменить его через программу будет невозможно. Обязательно запомните его.")
            warning_lbl.setStyleSheet("color: #F59E0B; font-size: 11px; font-weight: bold; margin-top: -5px;")
            warning_lbl.setWordWrap(True)
            layout.addWidget(warning_lbl)

        self.err_lbl = QLabel("")
        self.err_lbl.setStyleSheet(f"color: {STATUS_DANGER}; font-size: 12px; font-weight: bold;")
        layout.addWidget(self.err_lbl, alignment=Qt.AlignCenter)
        
        btn_save = QPushButton("СОХРАНИТЬ ДАННЫЕ")
        btn_save.setFixedHeight(45)
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setStyleSheet(f"background-color: {ACCENT_BLUE}; color: white; font-weight: 800; border-radius: 8px; border: none;")
        btn_save.clicked.connect(self.save_security)
        layout.addWidget(btn_save)

    def save_security(self):
        p_old = self.pin_old.text().strip()
        p_new = self.pin_new.text().strip()
        p_conf = self.pin_conf.text().strip()
        s_word = self.sec_word.text().strip()

        # Проверка безопасности: если ПИН уже был задан, требуем старый ПИН для изменения ПИНа
        if get_config_value("pin_hash", ""):
            if p_new and (not p_old or not verify_pin(p_old)):
                self.err_lbl.setText("❌ Ошибка: Введите верный Текущий PIN-код для внесения изменений!")
                return

        # Логика смены PIN
        if p_new or p_conf:
            if len(p_new) < 4:
                self.err_lbl.setText("❌ Ошибка: Новый PIN должен состоять минимум из 4 цифр!")
                return
            if p_new != p_conf:
                self.err_lbl.setText("❌ Ошибка: Новые пароли не совпадают!")
                return
            set_config_value("pin_hash", hash_pin(p_new))

        # Логика сохранения секретного слова (ТОЛЬКО ЕСЛИ ОНО НЕ БЫЛО ЗАБЛОКИРОВАНО)
        if not self.is_word_locked and s_word:
            set_config_value("sec_answer", s_word.lower()) # Сразу сохраняем в нижнем регистре для защиты от ошибок при вводе

        self.err_lbl.setStyleSheet(f"color: {STATUS_OK}; font-size: 12px; font-weight: bold;")
        self.err_lbl.setText("✅ Параметры безопасности успешно обновлены!")
        QTimer.singleShot(1000, self.accept)
        QTimer.singleShot(1000, self.accept)


class ConfigSecretDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Резервное слово")
        self.setFixedSize(380, 250)
        self.setStyleSheet(f"background-color: {BG_BASE}; color: {TEXT_PRIMARY};")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)
        
        lbl = QLabel("🔒 СЕКРЕТНОЕ СЛОВО")
        lbl.setStyleSheet("font-size: 16px; font-weight: 900; letter-spacing: 1px;")
        layout.addWidget(lbl, alignment=Qt.AlignCenter)

        desc = QLabel("Поможет сбросить PIN-код без интернета.")
        desc.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px;")
        layout.addWidget(desc, alignment=Qt.AlignCenter)
        
        self.word_input = QLineEdit()
        self.word_input.setPlaceholderText("Например: Караганда")
        self.word_input.setFixedHeight(45)
        self.word_input.setStyleSheet(f"border: 1px solid {BORDER_COLOR}; border-radius: 8px; padding: 5px 15px; font-size: 14px; background-color: {BG_SURFACE};")
        self.word_input.setText(get_config_value("sec_answer", ""))
        layout.addWidget(self.word_input)
        
        self.err_lbl = QLabel("")
        self.err_lbl.setStyleSheet(f"color: {STATUS_OK}; font-size: 12px; font-weight: bold;")
        layout.addWidget(self.err_lbl, alignment=Qt.AlignCenter)
        
        btn_save = QPushButton("СОХРАНИТЬ")
        btn_save.setFixedHeight(45)
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setStyleSheet(f"background-color: {ACCENT_BLUE}; color: white; font-weight: 800; border-radius: 8px; border: none;")
        btn_save.clicked.connect(self.save_word)
        layout.addWidget(btn_save)

    def save_word(self):
        set_config_value("sec_answer", self.word_input.text().strip())
        self.err_lbl.setText("✅ Успешно сохранено!")
        QTimer.singleShot(1000, self.accept)


class ConfigTelegramDialog(QDialog):
    """То самое идеальное окно Telegram с инструкцией и защитой"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройка Telegram")
        self.setFixedSize(500, 520) 
        self.setStyleSheet(f"background-color: {BG_BASE}; color: {TEXT_PRIMARY};")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)
        
        lbl = QLabel("💬 ИНТЕГРАЦИЯ TELEGRAM BOT")
        lbl.setStyleSheet("font-size: 16px; font-weight: 900; letter-spacing: 1px;")
        layout.addWidget(lbl, alignment=Qt.AlignCenter)

        # ─── БЛОК ИНСТРУКЦИИ ───
        guide_frame = QFrame()
        guide_frame.setStyleSheet(f"background-color: {BG_SURFACE}; border: 1px solid {BORDER_COLOR}; border-radius: 8px;")
        guide_layout = QVBoxLayout(guide_frame)
        guide_layout.setContentsMargins(20, 20, 20, 20)
        guide_layout.setSpacing(10)

        guide_title = QLabel("📖 Как получить данные для подключения:")
        guide_title.setStyleSheet("font-weight: bold; font-size: 13px; border: none;")
        guide_layout.addWidget(guide_title)

        from PyQt5.QtGui import QDesktopServices
        from PyQt5.QtCore import QUrl

        step1_layout = QHBoxLayout()
        step1_lbl = QLabel("1. Создайте бота и скопируйте Token:")
        step1_lbl.setStyleSheet("border: none; font-size: 12px; color: #94A3B8;")
        btn_botfather = QPushButton("@BotFather")
        btn_botfather.setCursor(Qt.PointingHandCursor)
        btn_botfather.setStyleSheet(f"color: {ACCENT_BLUE}; background: transparent; border: none; text-decoration: underline; font-weight: bold;")
        btn_botfather.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://t.me/BotFather")))
        step1_layout.addWidget(step1_lbl)
        step1_layout.addWidget(btn_botfather)
        step1_layout.addStretch()
        guide_layout.addLayout(step1_layout)

        step2_layout = QHBoxLayout()
        step2_lbl = QLabel("2. Узнайте свой Chat ID (отправьте /start):")
        step2_lbl.setStyleSheet("border: none; font-size: 12px; color: #94A3B8;")
        btn_getmyid = QPushButton("@getmyid_bot")
        btn_getmyid.setCursor(Qt.PointingHandCursor)
        btn_getmyid.setStyleSheet(f"color: {ACCENT_BLUE}; background: transparent; border: none; text-decoration: underline; font-weight: bold;")
        btn_getmyid.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://t.me/getmyid_bot")))
        step2_layout.addWidget(step2_lbl)
        step2_layout.addWidget(btn_getmyid)
        step2_layout.addStretch()
        guide_layout.addLayout(step2_layout)

        layout.addWidget(guide_frame)

        warning_lbl = QLabel("⚠️ ВНИМАНИЕ: Bot Token является строгой конфиденциальной информацией.\nНикогда не передавайте его третьим лицам!")
        warning_lbl.setStyleSheet("""
            color: #F59E0B; font-size: 11px; font-weight: bold; 
            background-color: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); 
            border-radius: 6px; padding: 10px;
        """)
        warning_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(warning_lbl)
        
        # ─── ВВОД ДАННЫХ И СТРОГАЯ ЗАЩИТА ───
        self.input_style = f"border: 1px solid {BORDER_COLOR}; border-radius: 8px; padding: 5px 15px; font-size: 14px; background-color: {BG_SURFACE}; color: {TEXT_PRIMARY};"
        self.disabled_style = f"border: 1px solid {BORDER_COLOR}; border-radius: 8px; padding: 5px 15px; font-size: 14px; background-color: {BG_BASE}; color: {TEXT_MUTED};"
        
        token_layout = QHBoxLayout()
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("Bot Token (HTTP API)")
        self.token_input.setEchoMode(QLineEdit.Password)
        self.token_input.setReadOnly(True)
        self.token_input.setFixedHeight(45)
        self.token_input.setStyleSheet(self.disabled_style)
        self.token_input.setText(get_config_value("telegram_token", ""))
        
        self.btn_reveal = QPushButton("🔓 Изменить")
        self.btn_reveal.setFixedHeight(45)
        self.btn_reveal.setCursor(Qt.PointingHandCursor)
        self.btn_reveal.setStyleSheet(f"background-color: transparent; color: {ACCENT_BLUE}; border: 1px solid {ACCENT_BLUE}; border-radius: 8px; padding: 0 15px; font-weight: bold;")
        self.btn_reveal.clicked.connect(self.reveal_token)

        token_layout.addWidget(self.token_input)
        token_layout.addWidget(self.btn_reveal)
        layout.addLayout(token_layout)
        
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Chat ID")
        self.chat_input.setReadOnly(True) 
        self.chat_input.setFixedHeight(45)
        self.chat_input.setStyleSheet(self.disabled_style)
        self.chat_input.setText(get_config_value("telegram_chat_id", ""))
        layout.addWidget(self.chat_input)
        
        self.err_lbl = QLabel("")
        self.err_lbl.setStyleSheet(f"color: {STATUS_DANGER}; font-size: 12px; font-weight: bold;")
        layout.addWidget(self.err_lbl, alignment=Qt.AlignCenter)
        
        self.btn_save = QPushButton("СОХРАНИТЬ ПРИВЯЗКУ")
        self.btn_save.setFixedHeight(45)
        self.btn_save.setEnabled(False) 
        self.btn_save.setStyleSheet(f"background-color: #334155; color: #94A3B8; font-weight: 800; border-radius: 8px; border: none;")
        self.btn_save.clicked.connect(self.save_tg)
        layout.addWidget(self.btn_save)

    def reveal_token(self):
        if self.token_input.echoMode() == QLineEdit.Normal:
            self.token_input.setEchoMode(QLineEdit.Password)
            self.token_input.setReadOnly(True)
            self.token_input.setStyleSheet(self.disabled_style)
            
            self.chat_input.setReadOnly(True)
            self.chat_input.setStyleSheet(self.disabled_style)
            
            self.btn_save.setEnabled(False)
            self.btn_save.setStyleSheet(f"background-color: #334155; color: #94A3B8; font-weight: 800; border-radius: 8px; border: none;")
            self.btn_save.setCursor(Qt.ArrowCursor)
            
            self.btn_reveal.setText("🔓 Изменить")
            self.btn_reveal.setStyleSheet(f"background-color: transparent; color: {ACCENT_BLUE}; border: 1px solid {ACCENT_BLUE}; border-radius: 8px; padding: 0 15px; font-weight: bold;")
            self.err_lbl.setText("")
            return

        dialog = PinDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.token_input.setEchoMode(QLineEdit.Normal)
            self.token_input.setReadOnly(False)
            self.token_input.setStyleSheet(self.input_style)
            
            self.chat_input.setReadOnly(False)
            self.chat_input.setStyleSheet(self.input_style)
            
            self.btn_save.setEnabled(True)
            self.btn_save.setCursor(Qt.PointingHandCursor)
            self.btn_save.setStyleSheet(f"background-color: {ACCENT_BLUE}; color: white; font-weight: 800; border-radius: 8px; border: none;")
            
            self.btn_reveal.setText("🔒 Заблокировать")
            self.btn_reveal.setStyleSheet(f"background-color: transparent; color: #EF4444; border: 1px solid #EF4444; border-radius: 8px; padding: 0 15px; font-weight: bold;")
            self.err_lbl.setText("")
        else:
            self.err_lbl.setStyleSheet(f"color: {STATUS_DANGER}; font-size: 12px; font-weight: bold;")
            self.err_lbl.setText("❌ Отказано: Требуется авторизация!")

    def save_tg(self):
        set_config_value("telegram_token", self.token_input.text().strip())
        set_config_value("telegram_chat_id", self.chat_input.text().strip())
        self.err_lbl.setStyleSheet(f"color: {STATUS_OK}; font-size: 12px; font-weight: bold;")
        self.err_lbl.setText("✅ Конфигурация применена!")
        QTimer.singleShot(1000, self.accept)
        
# ══════════════════════════════════════════════════════════════════════
#  PIN DIALOG (ДЛЯ ВХОДА И ЗАКРЫТИЯ С OTP/ОФЛАЙН)
# ══════════════════════════════════════════════════════════════════════
class PinDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Идентификация Администратора")
        self.setFixedSize(360, 280) 
        self.setStyleSheet(f"background-color: {BG_BASE}; color: {TEXT_PRIMARY};")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)
        
        self.lbl = QLabel("🛡️ ВВЕДИТЕ MASTER-PIN")
        self.lbl.setStyleSheet("font-size: 14px; font-weight: 900; letter-spacing: 1px;")
        layout.addWidget(self.lbl)
        
        self.pin_input = QLineEdit()
        self.pin_input.setEchoMode(QLineEdit.Password)
        self.pin_input.setFixedHeight(45)
        self.pin_input.setStyleSheet(f"border: 1px solid {BORDER_COLOR}; border-radius: 8px; padding: 5px 15px; font-size: 18px; background-color: {BG_SURFACE}; letter-spacing: 3px;")
        layout.addWidget(self.pin_input)
        
        self.error_lbl = QLabel("")
        self.error_lbl.setStyleSheet(f"color: {STATUS_DANGER}; font-size: 12px; font-weight: bold;")
        self.error_lbl.setWordWrap(True)
        layout.addWidget(self.error_lbl)
        
        btn_verify = QPushButton("АВТОРИЗОВАТЬСЯ")
        btn_verify.setFixedHeight(45)
        btn_verify.setCursor(Qt.PointingHandCursor)
        btn_verify.setStyleSheet(f"background-color: {ACCENT_BLUE}; color: white; font-weight: 800; letter-spacing: 1px; border-radius: 8px; border: none;")
        btn_verify.clicked.connect(self.check_pin)
        layout.addWidget(btn_verify)

        self.btn_forgot = QPushButton("Экстренный вход (OTP Telegram)")
        self.btn_forgot.setCursor(Qt.PointingHandCursor)
        self.btn_forgot.setStyleSheet(f"color: {TEXT_MUTED}; background: transparent; border: none; text-decoration: underline; font-size: 12px; margin-top: 5px;")
        self.btn_forgot.clicked.connect(self.request_otp)
        layout.addWidget(self.btn_forgot, alignment=Qt.AlignCenter)

        self.btn_offline = QPushButton("Нет интернета? (Секретное слово)")
        self.btn_offline.setCursor(Qt.PointingHandCursor)
        self.btn_offline.setStyleSheet(f"color: #F59E0B; background: transparent; border: none; text-decoration: underline; font-size: 12px;")
        self.btn_offline.clicked.connect(self.request_offline)
        layout.addWidget(self.btn_offline, alignment=Qt.AlignCenter)

        self.generated_otp = None
        self.recovery_mode = "pin" 

    def request_otp(self):
        from core.telegram_alerts import send_telegram_alert
        if not get_config_value("telegram_token", ""):
            self.error_lbl.setStyleSheet(f"color: {STATUS_DANGER};")
            self.error_lbl.setText("❌ Ошибка: Telegram не настроен!")
            return

        self.generated_otp = str(random.randint(100000, 999999))
        msg = f"🔑 ЗАПРОС ДОСТУПА ПО OTP\n\nЗапрошен экстренный обход защиты.\nКод (OTP): {self.generated_otp}\n\nНикому не сообщайте этот код!"
        send_telegram_alert(msg)

        self.recovery_mode = "otp"
        self.lbl.setText("📩 ВВЕДИТЕ OTP ИЗ TELEGRAM")
        self.pin_input.clear()
        self.pin_input.setPlaceholderText("6 цифр")
        self.pin_input.setEchoMode(QLineEdit.Normal)
        self.btn_forgot.hide()
        self.btn_offline.hide()
        
        self.error_lbl.setStyleSheet(f"color: {STATUS_OK};")
        self.error_lbl.setText("✅ OTP-код отправлен.")

    def request_offline(self):
        self.recovery_mode = "offline"
        self.lbl.setText("🔒 ВВЕДИТЕ СЕКРЕТНОЕ СЛОВО")
        self.pin_input.clear()
        self.pin_input.setPlaceholderText("Ваш ответ...")
        self.pin_input.setEchoMode(QLineEdit.Normal)
        self.btn_forgot.hide()
        self.btn_offline.hide()
        
        self.error_lbl.setStyleSheet("color: #F59E0B;")
        self.error_lbl.setText("⚠️ При успехе PIN сбросится на 0000")

    def check_pin(self):
        from core.telegram_alerts import send_telegram_alert
        from core.spy_module import SpyModule
        
        input_val = self.pin_input.text().strip()

        if self.recovery_mode == "otp":
            if input_val == self.generated_otp:
                send_telegram_alert("⚠️ Выполнен экстренный вход по OTP-коду.")
                self.accept()
            else:
                self.error_lbl.setStyleSheet(f"color: {STATUS_DANGER};")
                self.error_lbl.setText("❌ Неверный OTP-код!")
            return

        if self.recovery_mode == "offline":
            correct_ans = get_config_value("sec_answer", "").lower()
            if not correct_ans:
                self.error_lbl.setStyleSheet(f"color: {STATUS_DANGER};")
                self.error_lbl.setText("❌ Секретное слово не задано в config.json!")
                return
                
            if input_val.lower() == correct_ans:
                set_config_value("pin_hash", hash_pin("0000"))
                send_telegram_alert("⚠️ ВНИМАНИЕ: Защита сброшена через секретное слово! PIN установлен на 0000.")
                self.accept()
            else:
                self.error_lbl.setStyleSheet(f"color: {STATUS_DANGER};")
                self.error_lbl.setText("❌ Неверное секретное слово!")
                photo_path = SpyModule.take_photo() or SpyModule.take_screenshot()
                send_telegram_alert("🚨 Попытка подбора кодового слова!", photo_path)
            return

        stored_hash = get_config_value("pin_hash", "")
        if not stored_hash:
            self.error_lbl.setStyleSheet(f"color: {STATUS_DANGER};")
            self.error_lbl.setText("❌ ПИН-код не установлен.")
            return
            
        if verify_pin(input_val):
            self.accept()
        else:
            self.error_lbl.setStyleSheet(f"color: {STATUS_DANGER};")
            self.error_lbl.setText("❌ В ДОСТУПЕ ОТКАЗАНО")
            self.pin_input.clear()
            
            photo_path = SpyModule.take_photo() or SpyModule.take_screenshot()
            send_telegram_alert("🚨 ЗАФИКСИРОВАН ВЗЛОМ: Неверный ввод Master-PIN.", photo_path)