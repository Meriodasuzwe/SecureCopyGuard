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
from ui.pdf_report import generate_report
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtCore import QUrl
from ui.widgets import MetricCard, PolicyCard
from ui.theme import *
from db.database import Database
from config import set_config_value, verify_pin, hash_pin, get_config_value
from PyQt5.QtCore import pyqtSlot
from ui.locker import HardLockScreen
from core.file_locker   import FileLocker
from core.file_watcher  import FolderWatcher
from core.clipboard_guard import ClipboardGuard
from core.usb_monitor   import USBMonitor
from core.vision_protector import VisionProtector
from core.telegram_alerts  import send_telegram_alert
from core.autostart import enable_autostart, disable_autostart, is_enabled as autostart_is_enabled

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
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

    # ══════════════════════════════════════════════════════════════════════
#  DASHBOARD (ОБЗОР СИСТЕМЫ)
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
        title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 26px; font-weight: 800; letter-spacing: 1px;")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        # ─── НОВЫЕ СОЧНЫЕ КАРТОЧКИ (С ВЕКТОРНЫМИ ИКОНКАМИ) ───
        metrics = QHBoxLayout()
        metrics.setSpacing(20)
        
        
        self.card_folder  = MetricCard("folder", "Целевая директория", "Не задана",  ACCENT_BLUE)
        self.card_threats = MetricCard("shield", "Заблокировано", "0",        STATUS_OK)
        self.card_status  = MetricCard("pulse",  "Статус ядра",         "ОЖИДАНИЕ",  TEXT_MUTED)
        
        metrics.addWidget(self.card_folder,  2) # Эта карточка шире, чтобы влез длинный путь
        metrics.addWidget(self.card_threats, 1)
        metrics.addWidget(self.card_status,  1)
        layout.addLayout(metrics)

        # ─── ЦЕНТРАЛЬНАЯ ПАНЕЛЬ УПРАВЛЕНИЯ (С градиентом) ───
        panel = QFrame()
        panel.setStyleSheet(f"""
            QFrame {{ 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1E293B, stop:1 #0F172A);
                border: 1px solid #334155; 
                border-radius: 16px; 
            }}
        """)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 50, 0, 50)
        panel_layout.setAlignment(Qt.AlignCenter)

        self.led = QLabel()
        self.led.setFixedSize(28, 28)
        self.led.setStyleSheet(f"background-color: {TEXT_MUTED}; border-radius: 14px; border: 3px solid #334155;")

        self.status_lbl = QLabel("СИСТЕМА ДЕАКТИВИРОВАНА")
        self.status_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 16px; font-weight: 900; letter-spacing: 3px; margin-top: 15px; background: transparent; border: none;")
        self.status_lbl.setAlignment(Qt.AlignCenter)

        led_row = QHBoxLayout()
        led_row.setAlignment(Qt.AlignCenter)
        led_row.addWidget(self.led)
        
        # Избавляемся от фона у вложенных слоев
        panel_inner = QWidget()
        panel_inner.setStyleSheet("background: transparent; border: none;")
        inner_layout = QVBoxLayout(panel_inner)
        inner_layout.addLayout(led_row)
        inner_layout.addWidget(self.status_lbl)
        panel_layout.addWidget(panel_inner)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(20)
        btn_row.setContentsMargins(0, 30, 0, 0)

        self.btn_select = QPushButton("ВЫБРАТЬ ДИРЕКТОРИЮ")
        self.btn_select.setFixedSize(220, 50)
        self.btn_select.setCursor(Qt.PointingHandCursor)
        self.btn_select.setStyleSheet(f"""
            QPushButton {{ background-color: transparent; border: 2px solid #334155; color: {TEXT_PRIMARY}; border-radius: 8px; font-weight: bold; font-size: 12px; letter-spacing: 1px; }}
            QPushButton:hover {{ border: 2px solid {ACCENT_BLUE}; color: {ACCENT_BLUE}; background-color: rgba(59, 130, 246, 0.05); }}
        """)

        self.btn_arm = QPushButton("АКТИВИРОВАТЬ ЗАЩИТУ")
        self.btn_arm.setFixedSize(220, 50)
        self.btn_arm.setCheckable(True)
        self.btn_arm.setCursor(Qt.PointingHandCursor)
        self.btn_arm.setStyleSheet(f"""
            QPushButton {{ background-color: {ACCENT_BLUE}; color: white; border: none; border-radius: 8px; font-weight: 800; font-size: 13px; letter-spacing: 1px; }}
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
        self.vision_thread.env_warning.connect(self._on_env_warning)
        
        def _on_clipboard_violation(msg, snippet):
            self._log_and_notify("Clipboard Guard", msg, level="High")
            self._check_and_play_siren()
            from core.spy_module import SpyModule
            photo_path = SpyModule.take_photo() 
            if not photo_path: photo_path = SpyModule.take_screenshot()
            
            from core.telegram_alerts import send_telegram_alert
            send_telegram_alert(f"{msg}\n\nУтечка данных:\n{snippet}", photo_path)
            
            # 🔥 АВТОБЛОКИРОВКА ПРИ КОПИРОВАНИИ
            self.trigger_hard_lock()

        self.clip_guard.violation_detected.connect(_on_clipboard_violation)

    def _on_camera_error(self, msg):
        QMessageBox.warning(self, "Аппаратный сбой", f"Веб-камера не найдена или заблокирована.\n\nМодуль 'AI Vision' будет автоматически отключен.\nЗахват доказательств переведен в режим скриншотов.")
        self._log_and_notify("Система", "AI Vision отключен (нет камеры)", level="Low")
        if hasattr(self.window(), 'page_policies'):
            self.window().page_policies.policy_ai_vision.toggle.setChecked(False)
            self.window().page_policies.save_all_policies()
        self.vision_thread.stop()
    
    def _on_env_warning(self, msg: str):
        self._log_and_notify("AI Vision", msg, level="High")
        
        if self.is_armed:
            self.status_lbl.setText(msg)
            self.status_lbl.setStyleSheet("color: #F59E0B; font-size: 13px; font-weight: bold; letter-spacing: 1px; margin-top: 15px;")
            
            from core.telegram_alerts import send_telegram_alert
            send_telegram_alert(f"⚠️ ПОДОЗРЕНИЕ НА ВМЕШАТЕЛЬСТВО В РАБОТУ КАМЕРЫ, СРОЧНО ПРИМИТЕ МЕРЫ:\n{msg}")

            # 🔥 АВТОБЛОКИРОВКА ПРИ САБОТАЖЕ КАМЕРЫ
            self.trigger_hard_lock()

            from PyQt5.QtCore import QTimer
            QTimer.singleShot(5000, lambda: self._set_ui_armed(True) if self.is_armed else None)

    def _on_file_incident(self, policy_id: int, message: str):
        level_map = {1: "Critical", 2: "High", 3: "Low"}
        level = level_map.get(policy_id, "Medium")
        self._log_and_notify("File Watcher", message, level=level)
        if policy_id in (1, 2):
            self._check_and_play_siren()
            from core.spy_module import SpyModule
            photo_path = SpyModule.take_photo() or SpyModule.take_screenshot()
            
            from core.telegram_alerts import send_telegram_alert
            send_telegram_alert(message, photo_path)

    def _on_phone_detected(self, message: str, photo_path: str):
        self._log_and_notify("AI Vision", message, level="Critical")
        self._start_flash()
        self._check_and_play_siren()
        
        from core.telegram_alerts import send_telegram_alert
        send_telegram_alert(message, photo_path)

    def _on_usb_connected(self, drive: str):
        msg = f"⚠️ USB-носитель подключён: {drive or 'неизвестный диск'}"
        self._log_and_notify("USB Guard", msg, level="High")
        self._check_and_play_siren()
        
        from core.telegram_alerts import send_telegram_alert
        send_telegram_alert(msg)
        
        
        self.trigger_hard_lock()

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
            # Если у тебя PinDialog в другом файле, убедись что он импортирован!
            from ui.pages import PinDialog # <-- Зависит от того, где у тебя PinDialog
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
            self.vision_thread.env_warning.connect(self._on_env_warning) 
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
            self.led.setStyleSheet(f"background-color: {STATUS_OK}; border-radius: 14px; border: 3px solid #065F46;")
            self.status_lbl.setText("СИСТЕМА АКТИВНА")
            self.status_lbl.setStyleSheet(f"color: {STATUS_OK}; font-size: 16px; font-weight: 900; letter-spacing: 3px; margin-top: 15px; background: transparent; border: none;")
            self.btn_arm.setText("ДЕАКТИВИРОВАТЬ")
            self.btn_select.setEnabled(False)
            self.card_status.lbl_value.setText("АКТИВНО")
            self.card_status.lbl_value.setStyleSheet(f"color: {STATUS_OK}; font-size: 26px; font-weight: 900; border: none; background: transparent;")
        else:
            self.led.setStyleSheet(f"background-color: {TEXT_MUTED}; border-radius: 14px; border: 3px solid #334155;")
            self.status_lbl.setText("СИСТЕМА ДЕАКТИВИРОВАНА")
            self.status_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 16px; font-weight: 900; letter-spacing: 3px; margin-top: 15px; background: transparent; border: none;")
            self.btn_arm.setText("АКТИВИРОВАТЬ ЗАЩИТУ")
            self.btn_select.setEnabled(True)
            self.card_status.lbl_value.setText("ОЖИДАНИЕ")
            self.card_status.lbl_value.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 26px; font-weight: 900; border: none; background: transparent;")

    def update_stats(self):
        count = self.db.get_incident_count()
        self.card_threats.lbl_value.setText(str(count))
        if count > 0:
            self.card_threats.lbl_value.setStyleSheet(f"color: {STATUS_DANGER}; font-size: 26px; font-weight: 900; border: none; background: transparent;")

    def remote_arm(self):
        if not self.btn_arm.isChecked():
            self.btn_arm.setChecked(True)
            self.toggle_protection()

    def remote_disarm(self):
        if self.btn_arm.isChecked():
            self.btn_arm.setChecked(False)
            self.toggle_protection()
    
    @pyqtSlot()
    def trigger_hard_lock(self):
        """Вызывается через QMetaObject из потока Telegram бота или автоматически при критической угрозе"""
        set_config_value("hard_lock", True)
        
        # Запускаем локер, только если он еще не открыт
        if not hasattr(self, 'locker_window') or not self.locker_window.isVisible():
            from ui.locker import HardLockScreen
            self.locker_window = HardLockScreen()
            self.locker_window.show()
    
    def _check_and_play_siren(self):
        if self._read_policies().get("siren"):
            from core.spy_module import SpyModule
            SpyModule.play_siren()

    def _connect_worker_signals(self):
        self.vision_thread.phone_detected.connect(self._on_phone_detected)
        self.vision_thread.camera_error.connect(self._on_camera_error)
        self.vision_thread.env_warning.connect(self._on_env_warning)
        
        def _on_clipboard_violation(msg, snippet):
            self._log_and_notify("Clipboard Guard", msg, level="High")
            self._check_and_play_siren()
            from core.spy_module import SpyModule
            photo_path = SpyModule.take_photo() 
            if not photo_path: photo_path = SpyModule.take_screenshot()
            send_telegram_alert(f"{msg}\n\nУтечка данных:\n{snippet}", photo_path)

            self.trigger_hard_lock()

        self.clip_guard.violation_detected.connect(_on_clipboard_violation)

    def _on_camera_error(self, msg):
        QMessageBox.warning(self, "Аппаратный сбой", f"Веб-камера не найдена или заблокирована.\n\nМодуль 'AI Vision' будет автоматически отключен.\nЗахват доказательств переведен в режим скриншотов.")
        self._log_and_notify("Система", "AI Vision отключен (нет камеры)", level="Low")
        if hasattr(self.window(), 'page_policies'):
            self.window().page_policies.policy_ai_vision.toggle.setChecked(False)
            self.window().page_policies.save_all_policies()
        self.vision_thread.stop()
    
    
    def _on_env_warning(self, msg: str):
        # Пишем в лог как Low угрозу (чтобы безопасник видел, что юзер пытался закрыть камеру рукой)
        self._log_and_notify("AI Vision", msg, level="Low")
        
        # Если система в боевом режиме, выводим алерт прямо на экран в статус!
        if self.is_armed:
            self.status_lbl.setText(msg)
            self.status_lbl.setStyleSheet("color: #F59E0B; font-size: 13px; font-weight: bold; letter-spacing: 1px; margin-top: 15px;")
            
            from core.telegram_alerts import send_telegram_alert
            send_telegram_alert(f"⚠️ ПОДОЗРЕНИЕ НА ВМЕШАТЕЛЬСТВО В РАБОТУ КАМЕРЫ,СРОЧНО ПРИМИТЕ МЕРЫ\n{msg}")

            self.trigger_hard_lock()
            # Через 5 секунд возвращаем нормальный зеленый статус "СИСТЕМА АКТИВНА"
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(5000, lambda: self._set_ui_armed(True) if self.is_armed else None)

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

        self.trigger_hard_lock()

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
            # Нужно для оповещения о саботаже
            self.vision_thread.env_warning.connect(self._on_env_warning) 
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
    
    @pyqtSlot()
    def trigger_hard_lock(self):
        """Вызывается через QMetaObject из потока Telegram бота"""
        set_config_value("hard_lock", True)
        
        # Запускаем локер, только если он еще не открыт
        if not hasattr(self, 'locker_window') or not self.locker_window.isVisible():
            self.locker_window = HardLockScreen()
            self.locker_window.show()
    
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
        layout.setSpacing(12)

        title = QLabel("ПОЛИТИКИ БЕЗОПАСНОСТИ")
        title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 22px; font-weight: 600; letter-spacing: 1px;")
        layout.addWidget(title)

        s_file  = get_config_value("pol_file",   True)
        s_clip  = get_config_value("pol_clip",   True)
        s_webc  = get_config_value("pol_webcam", True)
        s_usb   = get_config_value("pol_usb",    True)
        s_ai    = get_config_value("pol_ai",     False)
        s_siren = get_config_value("pol_siren",  False)

        self.policy_file_lock = PolicyCard("Anti-Delete (Блокировка ФС)",    "Жёсткий запрет удаления и изменения файлов ОС.",                    default_state=s_file)
        self.policy_clipboard = PolicyCard("Контроль буфера обмена",         "Блокировка копирования конфиденциальных данных.",                    default_state=s_clip)
        self.policy_webcam    = PolicyCard("Webcam Trap",                    "Тайная фото-фиксация нарушителя при любом инциденте.",              default_state=s_webc)
        self.policy_usb       = PolicyCard("USB Guard",                      "Блокировка и уведомление о подключении флешек.",                    default_state=s_usb)
        self.policy_ai_vision = PolicyCard("AI Vision (YOLOv8)",             "Нейросеть детектирует смартфоны, наведенные на экран.",             default_state=s_ai)
        self.policy_siren     = PolicyCard("Siren Alarm",                    "Громкий звуковой сигнал тревоги при утечке.",                       default_state=s_siren)

        for card in [
            self.policy_file_lock,
            self.policy_clipboard,
            self.policy_webcam,
            self.policy_usb,
            self.policy_ai_vision,
            self.policy_siren,
        ]:
            layout.addWidget(card)

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
        set_config_value("pol_file",   p["file_lock"])
        set_config_value("pol_clip",   p["clipboard"])
        set_config_value("pol_webcam", p["webcam"])
        set_config_value("pol_usb",    p["usb"])
        set_config_value("pol_ai",     p["ai_vision"])
        set_config_value("pol_siren",  p["siren"])

    def set_locked(self, is_locked: bool):
        for card in [
            self.policy_file_lock, self.policy_clipboard,
            self.policy_webcam,    self.policy_usb,
            self.policy_ai_vision, self.policy_siren,
        ]:
            card.setEnabled(not is_locked)
            effect = QGraphicsOpacityEffect()
            effect.setOpacity(0.4 if is_locked else 1.0)
            card.setGraphicsEffect(effect)


# ══════════════════════════════════════════════════════════════════════
#  ЖУРНАЛ ИНЦИДЕНТОВ С АНАЛИТИКОЙ
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

        # ─── ШАПКА ───
        header = QHBoxLayout()
        title  = QLabel("ЖУРНАЛ ИНЦИДЕНТОВ И АНАЛИТИКА")
        title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 22px; font-weight: 600; letter-spacing: 1px;")
        
        btn_refresh = QPushButton("🔄 ОБНОВИТЬ ДАННЫЕ")
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

        # ─── БЛОК АНАЛИТИКИ (ГРАФИКИ) ───
        self.charts_frame = QFrame()
        self.charts_frame.setFixedHeight(260) # Фиксированная высота для графиков
        self.charts_frame.setStyleSheet(f"background-color: {BG_SURFACE}; border: 1px solid {BORDER_COLOR}; border-radius: 8px;")
        charts_layout = QHBoxLayout(self.charts_frame)
        charts_layout.setContentsMargins(10, 10, 10, 10)
        
        # Инициализируем холст Matplotlib
        self.fig = Figure(figsize=(8, 3), dpi=100)
        self.fig.patch.set_facecolor('#1E293B') # Цвет фона BG_SURFACE
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setStyleSheet("background-color: transparent; border: none;")
        charts_layout.addWidget(self.canvas)
        
        layout.addWidget(self.charts_frame)

        # ─── ТАБЛИЦА ЛОГОВ ───
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
            QTableWidget::item {{ border-bottom: 1px solid #334155; padding: 5px; }}
            QTableWidget::item:selected {{ background-color: #334155; }}
        """)
        layout.addWidget(self.table)

    def refresh_all(self):
        self.load_logs()
        if hasattr(self.window(), 'page_dash'):
            self.window().page_dash.update_stats()

    def load_logs(self):
        self.table.setRowCount(0)
        # Берем больше логов для красивой статистики
        logs = self.db.get_recent_logs(200) 
        
        level_colors = {"High": STATUS_DANGER, "Critical": STATUS_DANGER, "Medium": "#F59E0B", "Low": TEXT_MUTED}
        
        # Словари для сбора статистики под графики
        stats_levels = {"High": 0, "Medium": 0, "Low": 0}
        stats_modules = {}

        for row_idx, log in enumerate(logs):
            # Если база возвращает: timestamp, module, level, details
            timestamp, module_name, threat_level, details = log
            
            # --- Заполняем таблицу ---
            # Ограничиваем количество строк в таблице, чтобы не лагало (например, 50)
            if row_idx < 50:
                self.table.insertRow(row_idx)
                color = level_colors.get(str(threat_level), TEXT_PRIMARY)
                item_level = QTableWidgetItem(str(threat_level))
                item_level.setForeground(QColor(color))

                self.table.setItem(row_idx, 0, QTableWidgetItem(str(timestamp)[:19]))
                self.table.setItem(row_idx, 1, item_level)
                self.table.setItem(row_idx, 2, QTableWidgetItem(str(module_name)))
                self.table.setItem(row_idx, 3, QTableWidgetItem(str(details)))

            # --- Собираем статистику ---
            t_level = str(threat_level)
            if t_level in ["Critical", "High"]: stats_levels["High"] += 1
            elif t_level == "Medium": stats_levels["Medium"] += 1
            else: stats_levels["Low"] += 1

            m_name = str(module_name)
            stats_modules[m_name] = stats_modules.get(m_name, 0) + 1

        # Обновляем графики собранными данными
        self.update_charts(stats_levels, stats_modules)

    def update_charts(self, levels: dict, modules: dict):
        self.fig.clear()
        
        # Если логов нет, просто ничего не рисуем
        if sum(levels.values()) == 0:
            self.canvas.draw()
            return

        # Настраиваем шрифты на белый цвет
        import matplotlib as mpl
        mpl.rcParams['text.color'] = '#F8FAFC'
        mpl.rcParams['axes.labelcolor'] = '#F8FAFC'
        mpl.rcParams['xtick.color'] = '#94A3B8'
        mpl.rcParams['ytick.color'] = '#94A3B8'

        # Делим холст на 2 части: слева кольцо угроз, справа столбцы модулей
        ax1 = self.fig.add_subplot(121)
        ax2 = self.fig.add_subplot(122)

        # ─── ГРАФИК 1: Кольцевая диаграмма угроз ───
        labels_pie = []
        sizes_pie = []
        colors_pie = []
        
        color_map = {"High": "#EF4444", "Medium": "#F59E0B", "Low": "#64748B"}
        for k, v in levels.items():
            if v > 0:
                labels_pie.append(f"{k} ({v})")
                sizes_pie.append(v)
                colors_pie.append(color_map[k])

        wedges, texts = ax1.pie(
            sizes_pie, 
            labels=labels_pie, 
            colors=colors_pie,
            startangle=90, 
            wedgeprops=dict(width=0.4, edgecolor='#1E293B', linewidth=2) # Делаем "бублик" с отступами
        )
        ax1.set_title("Уровни Угроз", fontsize=12, fontweight='bold', pad=10)

        # ─── ГРАФИК 2: Активность модулей защиты ───
        ax2.set_facecolor('#1E293B')
        
        # Сортируем модули по количеству сработок
        sorted_modules = sorted(modules.items(), key=lambda x: x[1])
        m_names = [x[0] for x in sorted_modules]
        m_counts = [x[1] for x in sorted_modules]

        # Рисуем горизонтальные столбцы (они лучше читаются)
        bars = ax2.barh(m_names, m_counts, color='#3B82F6', height=0.5, edgecolor='none')
        
        ax2.set_title("Срабатывания Модулей", fontsize=12, fontweight='bold', pad=10)
        
        # Убираем лишние рамки у графика для красоты
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_visible(False)
        ax2.spines['left'].set_color('#334155')
        ax2.spines['bottom'].set_color('#334155')
        ax2.xaxis.set_major_locator(mpl.ticker.MaxNLocator(integer=True)) # Только целые числа на оси X

        # Плотно упаковываем графики, чтобы не было пустых дыр
        self.fig.tight_layout(pad=2.0)
        
        # Отрисовываем
        self.canvas.draw()


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
        main_layout.setSpacing(20)

        # ── Заголовок с акцентной полосой ─────────────────────────────
        header_layout = QHBoxLayout()
        header_layout.setSpacing(15)

        accent_bar = QFrame()
        accent_bar.setFixedSize(4, 36)
        accent_bar.setStyleSheet(f"background-color: {ACCENT_BLUE}; border-radius: 2px;")

        title = QLabel("ПАНЕЛЬ УПРАВЛЕНИЯ ЯДРОМ")
        title.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 22px; font-weight: 800; letter-spacing: 2px;"
        )

        header_layout.addWidget(accent_bar)
        header_layout.addWidget(title)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        # ── Сетка карточек ─────────────────────────────────────────────
        grid = QGridLayout()
        grid.setSpacing(16)
        grid.setContentsMargins(0, 0, 0, 0)

        # Карточка 1 — PIN
        pin_card = self._make_card(
            icon="🛡",
            title="УПРАВЛЕНИЕ ДОСТУПОМ",
            desc="Master-PIN, секретное слово\nдля офлайн-восстановления",
            btn_text="Настроить безопасность",
            accent="#3B82F6",
            on_click=self.open_pin_dialog,
        )
        grid.addWidget(pin_card, 0, 0)

        # Карточка 2 — Telegram
        tg_card = self._make_card(
            icon="✈",
            title="ИНТЕГРАЦИЯ TELEGRAM",
            desc="Подключение бота для алертов,\nфото-доказательств и PDF-отчётов",
            btn_text="Настроить Telegram",
            accent="#0EA5E9",
            on_click=self.open_tg_dialog,
        )
        grid.addWidget(tg_card, 0, 1)

        # Карточка 3 — Автозапуск
        auto_card = self._make_autostart_card()
        grid.addWidget(auto_card, 1, 0)

        # Карточка 4 — Инфо
        info_card = self._make_info_card()
        grid.addWidget(info_card, 1, 1)

        grid.setRowStretch(0, 1)
        grid.setRowStretch(1, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        main_layout.addLayout(grid, stretch=1)

        # ── Подвал ─────────────────────────────────────────────────────
        footer = QLabel("Licensed to Rakhat Aliev  ·  SecureCopyGuard Enterprise v3.0")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("color: #334155; font-size: 11px; font-weight: 600; letter-spacing: 1px;")
        main_layout.addWidget(footer)

    # ── Фабрика карточек ───────────────────────────────────────────────

    def _make_card(self, icon, title, desc, btn_text, accent, on_click):
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_SURFACE};
                border: 1px solid {BORDER_COLOR};
                border-radius: 16px;
            }}
            QFrame:hover {{
                border: 1px solid {accent};
            }}
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(0)

        # Иконка в цветном круге
        icon_wrap = QHBoxLayout()
        icon_lbl = QLabel(icon)
        icon_lbl.setFixedSize(52, 52)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet(f"""
            font-size: 22px;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 {accent}33, stop:1 {accent}11);
            border: 1px solid {accent}44;
            border-radius: 14px;
        """)
        icon_wrap.addWidget(icon_lbl)
        icon_wrap.addStretch()
        layout.addLayout(icon_wrap)
        layout.addSpacing(16)

        # Заголовок
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 13px; font-weight: 800; "
            f"letter-spacing: 1px; border: none; background: transparent;"
        )
        layout.addWidget(lbl_title)
        layout.addSpacing(8)

        # Описание
        lbl_desc = QLabel(desc)
        lbl_desc.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 12px; line-height: 1.5; "
            f"border: none; background: transparent;"
        )
        lbl_desc.setWordWrap(True)
        layout.addWidget(lbl_desc)

        layout.addStretch()
        layout.addSpacing(20)

        # Кнопка
        btn = QPushButton(btn_text)
        btn.setFixedHeight(40)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {accent}, stop:1 {accent}CC);
                color: white;
                font-weight: 700;
                font-size: 12px;
                letter-spacing: 0.5px;
                border: none;
                border-radius: 10px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {accent}EE, stop:1 {accent});
            }}
            QPushButton:pressed {{
                background: {accent}99;
            }}
        """)
        btn.clicked.connect(on_click)
        layout.addWidget(btn)

        return frame

    def _make_autostart_card(self):
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_SURFACE};
                border: 1px solid {BORDER_COLOR};
                border-radius: 16px;
            }}
            QFrame:hover {{
                border: 1px solid #8B5CF6;
            }}
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(0)

        # Иконка
        icon_wrap = QHBoxLayout()
        icon_lbl = QLabel("⚡")
        icon_lbl.setFixedSize(52, 52)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("""
            font-size: 22px;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #8B5CF633, stop:1 #8B5CF611);
            border: 1px solid #8B5CF644;
            border-radius: 14px;
        """)
        icon_wrap.addWidget(icon_lbl)
        icon_wrap.addStretch()
        layout.addLayout(icon_wrap)
        layout.addSpacing(16)

        lbl_title = QLabel("СИСТЕМНЫЕ ПАРАМЕТРЫ")
        lbl_title.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 13px; font-weight: 800; "
            f"letter-spacing: 1px; border: none; background: transparent;"
        )
        layout.addWidget(lbl_title)
        layout.addSpacing(8)

        lbl_desc = QLabel("Интеграция агента защиты\nс автозагрузкой ОС Windows")
        lbl_desc.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 12px; border: none; background: transparent;"
        )
        layout.addWidget(lbl_desc)
        layout.addStretch()
        layout.addSpacing(20)

        # Переключатель автозапуска
        toggle_row = QHBoxLayout()
        toggle_lbl = QLabel("Запускать вместе с Windows")
        toggle_lbl.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 13px; font-weight: 600; "
            f"border: none; background: transparent;"
        )

        self.cb_autostart = QCheckBox()
        try:
            self.cb_autostart.setChecked(autostart_is_enabled())
        except Exception:
            pass
        self.cb_autostart.setStyleSheet(f"""
            QCheckBox {{
                border: none;
                background: transparent;
            }}
            QCheckBox::indicator {{
                width: 44px;
                height: 24px;
                border-radius: 12px;
                border: 2px solid {BORDER_COLOR};
                background: {BG_BASE};
            }}
            QCheckBox::indicator:checked {{
                background: #8B5CF6;
                border-color: #8B5CF6;
            }}
        """)
        self.cb_autostart.stateChanged.connect(self._toggle_autostart)

        toggle_row.addWidget(toggle_lbl)
        toggle_row.addStretch()
        toggle_row.addWidget(self.cb_autostart)
        layout.addLayout(toggle_row)

        return frame

    def _make_info_card(self):
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_SURFACE};
                border: 1px solid {BORDER_COLOR};
                border-radius: 16px;
            }}
            QFrame:hover {{
                border: 1px solid #10B981;
            }}
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(0)

        # Иконка
        icon_wrap = QHBoxLayout()
        icon_lbl = QLabel("⚙")
        icon_lbl.setFixedSize(52, 52)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("""
            font-size: 22px;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #10B98133, stop:1 #10B98111);
            border: 1px solid #10B98144;
            border-radius: 14px;
        """)
        icon_wrap.addWidget(icon_lbl)
        icon_wrap.addStretch()
        layout.addLayout(icon_wrap)
        layout.addSpacing(16)

        lbl_title = QLabel("ТЕХНИЧЕСКАЯ ИНФОРМАЦИЯ")
        lbl_title.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 13px; font-weight: 800; "
            f"letter-spacing: 1px; border: none; background: transparent;"
        )
        layout.addWidget(lbl_title)
        layout.addSpacing(16)

        # Строки информации
        info_items = [
            ("AI Engine",       "YOLOv8 Nano",    "#3B82F6"),
            ("Storage",         "dlp_logs.db",    "#10B981"),
            ("Evidence Cache",  "_INTRUDERS/",    "#F59E0B"),
        ]

        for label, value, color in info_items:
            row = QHBoxLayout()
            row.setSpacing(8)

            dot = QLabel("●")
            dot.setFixedWidth(12)
            dot.setStyleSheet(f"color: {color}; font-size: 8px; border: none; background: transparent;")

            lbl_key = QLabel(label)
            lbl_key.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px; border: none; background: transparent;")

            lbl_val = QLabel(value)
            lbl_val.setStyleSheet(
                f"color: {TEXT_PRIMARY}; font-size: 12px; font-weight: 600; "
                f"border: none; background: transparent;"
            )

            row.addWidget(dot)
            row.addWidget(lbl_key)
            row.addStretch()
            row.addWidget(lbl_val)
            layout.addLayout(row)
            layout.addSpacing(10)

        layout.addStretch() # Пружина, чтобы кнопка ушла в самый низ

        # 🔥 НОВАЯ КНОПКА ГЕНЕРАЦИИ PDF
        btn_pdf = QPushButton("Выгрузить PDF-отчёт")
        btn_pdf.setFixedHeight(40)
        btn_pdf.setCursor(Qt.PointingHandCursor)
        btn_pdf.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid #10B981;
                color: #10B981;
                font-weight: 700;
                font-size: 12px;
                letter-spacing: 0.5px;
                border-radius: 10px;
                margin-top: 5px;
            }}
            QPushButton:hover {{
                background-color: rgba(16, 185, 129, 0.1);
            }}
            QPushButton:pressed {{
                background-color: rgba(16, 185, 129, 0.2);
            }}
        """)
        btn_pdf.clicked.connect(self.export_pdf)
        layout.addWidget(btn_pdf)

        return frame

    
    
    def export_pdf(self):
        try:
            from ui.pdf_report import generate_report
            import os
            file_path = generate_report()
            
            msg = QMessageBox(self)
            # Задаем только фон и кнопку. Текст покрасим через HTML
            msg.setStyleSheet("""
                QMessageBox { background-color: #0F172A; border: 1px solid #334155; }
                QPushButton {
                    background-color: #10B981; color: white; font-weight: 800;
                    border-radius: 6px; padding: 8px 20px; min-width: 80px; border: none;
                }
                QPushButton:hover { background-color: #059669; }
            """)

            if file_path and os.path.exists(file_path):
                msg.setWindowTitle("✅ Отчет сформирован")
                # 🔥 Обертка в span принудительно делает текст белым
                msg.setText(f'<span style="color: #F8FAFC; font-size: 13px;">PDF-отчёт успешно сгенерирован!<br><br>Сохранён в: <b>{file_path}</b></span>')
                msg.setIcon(QMessageBox.Information)
                msg.exec_()
                
                from PyQt5.QtGui import QDesktopServices
                from PyQt5.QtCore import QUrl
                QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(file_path)))
            else:
                msg.setWindowTitle("⚠️ Ошибка")
                msg.setText('<span style="color: #F8FAFC; font-size: 13px;">Не удалось создать PDF-отчёт. Проверьте права на запись.</span>')
                msg.setIcon(QMessageBox.Warning)
                msg.setStyleSheet(msg.styleSheet().replace("#10B981", "#F59E0B").replace("#059669", "#D97706")) 
                msg.exec_()
                
        except Exception as e:
            err_msg = QMessageBox(self)
            err_msg.setWindowTitle("❌ Критическая Ошибка")
            err_msg.setText(f'<span style="color: #F8FAFC; font-size: 13px;">Сбой при генерации отчета:<br>{str(e)}</span>')
            err_msg.setIcon(QMessageBox.Critical)
            err_msg.setStyleSheet("""
                QMessageBox { background-color: #0F172A; border: 1px solid #334155; }
                QPushButton { background-color: #EF4444; color: white; font-weight: 800; border-radius: 6px; padding: 8px 20px; min-width: 80px; border: none; }
                QPushButton:hover { background-color: #DC2626; }
            """)
            err_msg.exec_()

    # ── Действия ───────────────────────────────────────────────────────

    def open_pin_dialog(self):
        ConfigPinDialog(self).exec_()

    def open_tg_dialog(self):
        ConfigTelegramDialog(self).exec_()

    def _toggle_autostart(self, state):
        if state == Qt.Checked:
            enable_autostart()
            set_config_value("autostart", True)
        else:
            disable_autostart()
            set_config_value("autostart", False)


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