# ui/pages.py

import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame, QFileDialog, QMessageBox,
                             QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor

from ui.widgets import MetricCard, PolicyCard
from ui.theme import *
from db.database import Database

# Ядро
from core.file_locker import FileLocker
from core.file_watcher import FolderWatcher
from core.clipboard_guard import ClipboardGuard
from core.usb_monitor import USBMonitor
from core.spy_module import SpyModule

class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()
        self.target_folder = None
        self.is_armed = False
        self.db = Database()
        self.watcher = FolderWatcher()
        self.clip_guard = ClipboardGuard()
        self.usb_monitor = USBMonitor()
        
        self.setup_ui()
        self.connect_signals()
        self.update_stats() # Считаем угрозы при запуске

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)

        header_layout = QHBoxLayout()
        title = QLabel("ОБЗОР СИСТЕМЫ")
        title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 22px; font-weight: 600; letter-spacing: 1px;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(20)
        self.card_folder = MetricCard("Целевая директория", "Не задана", ACCENT_BLUE)
        self.card_threats = MetricCard("Заблокировано угроз", "0", STATUS_OK)
        self.card_status = MetricCard("Статус ядра", "ОЖИДАНИЕ", TEXT_MUTED)
        metrics_layout.addWidget(self.card_folder, 2)
        metrics_layout.addWidget(self.card_threats, 1)
        metrics_layout.addWidget(self.card_status, 1)
        layout.addLayout(metrics_layout)

        control_panel = QFrame()
        control_panel.setStyleSheet(f"QFrame {{ background-color: {BG_SURFACE}; border: 1px solid {BORDER_COLOR}; border-radius: 8px; }}")
        control_layout = QVBoxLayout(control_panel)
        control_layout.setContentsMargins(0, 50, 0, 50)
        control_layout.setAlignment(Qt.AlignCenter)

        self.led_indicator = QLabel()
        self.led_indicator.setFixedSize(24, 24)
        self.led_indicator.setStyleSheet(f"background-color: {TEXT_MUTED}; border-radius: 12px;") 
        
        self.status_text = QLabel("СИСТЕМА ДЕАКТИВИРОВАНА")
        self.status_text.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 14px; font-weight: bold; letter-spacing: 2px; margin-top: 15px;")
        self.status_text.setAlignment(Qt.AlignCenter)

        led_layout = QHBoxLayout()
        led_layout.setAlignment(Qt.AlignCenter)
        led_layout.addWidget(self.led_indicator)
        control_layout.addLayout(led_layout)
        control_layout.addWidget(self.status_text)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(20)
        btn_layout.setContentsMargins(0, 30, 0, 0)

        self.btn_select = QPushButton("ВЫБРАТЬ ДИРЕКТОРИЮ")
        self.btn_select.setFixedSize(220, 45)
        self.btn_select.setCursor(Qt.PointingHandCursor)
        self.btn_select.setStyleSheet(f"QPushButton {{ background-color: transparent; border: 1px solid {BORDER_COLOR}; color: {TEXT_PRIMARY}; border-radius: 4px; font-weight: bold; font-size: 12px; letter-spacing: 1px; }} QPushButton:hover {{ border: 1px solid {ACCENT_BLUE}; color: {ACCENT_BLUE}; }}")

        self.btn_arm = QPushButton("АКТИВИРОВАТЬ ЗАЩИТУ")
        self.btn_arm.setFixedSize(220, 45)
        self.btn_arm.setCheckable(True)
        self.btn_arm.setCursor(Qt.PointingHandCursor)
        self.btn_arm.setStyleSheet(f"QPushButton {{ background-color: {ACCENT_BLUE}; color: white; border: none; border-radius: 4px; font-weight: bold; font-size: 12px; letter-spacing: 1px; }} QPushButton:hover {{ background-color: #2563EB; }} QPushButton:checked {{ background-color: {STATUS_DANGER}; }}")

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_select)
        btn_layout.addWidget(self.btn_arm)
        btn_layout.addStretch()

        control_layout.addLayout(btn_layout)
        layout.addWidget(control_panel)
        layout.addStretch()

    def connect_signals(self):
        self.btn_select.clicked.connect(self.choose_directory)
        self.btn_arm.clicked.connect(self.toggle_protection)

    def update_stats(self):
        """Обновляет цифру заблокированных угроз из БД"""
        count = self.db.get_incident_count()
        self.card_threats.lbl_value.setText(str(count))
        # Если угроз больше 0, красим в красный для алярма
        if count > 0:
            self.card_threats.lbl_value.setStyleSheet(f"color: {STATUS_DANGER}; font-size: 28px; font-weight: bold; border: none;")

    def choose_directory(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите целевую директорию")
        if folder:
            self.target_folder = folder
            folder_name = os.path.basename(folder) if os.path.basename(folder) else folder
            self.card_folder.lbl_value.setText(f"/{folder_name}")

    def toggle_protection(self):
        if not self.target_folder:
            self.btn_arm.setChecked(False)
            QMessageBox.warning(self, "Ошибка", "Сначала выберите директорию.")
            return

        self.is_armed = self.btn_arm.isChecked()
        main_win = self.window()
        
        # Считываем политики
        use_locking = main_win.page_policies.policy_file_lock.is_active()
        use_clipboard = main_win.page_policies.policy_clipboard.is_active()
        use_camera = main_win.page_policies.policy_webcam.is_active()
        use_usb = main_win.page_policies.policy_usb.is_active()
        use_siren = main_win.page_policies.policy_siren.is_active()

        if self.is_armed:
            if use_locking: FileLocker.lock_directory(self.target_folder)
            self.watcher.start(self.target_folder, use_camera=use_camera)
            if use_clipboard: self.clip_guard.start()
            
            # USB монитор запускаем только если галка стоит
            if use_usb:
                if not self.usb_monitor.is_alive():
                    self.usb_monitor = USBMonitor()
                    self.usb_monitor.start()
            
            self.db.log_incident(3, "ЗАЩИТА АКТИВИРОВАНА")
            self.led_indicator.setStyleSheet(f"background-color: {STATUS_OK}; border-radius: 12px; border: 2px solid #065F46;")
            self.status_text.setText("СИСТЕМА АКТИВНА")
            self.btn_arm.setText("ДЕАКТИВИРОВАТЬ")
            self.btn_select.setEnabled(False)
            self.card_status.lbl_value.setText("АКТИВНО")
            self.card_status.lbl_value.setStyleSheet(f"color: {STATUS_OK}; font-size: 28px; font-weight: bold; border: none;")
        else:
            FileLocker.unlock_directory(self.target_folder)
            self.watcher.stop()
            self.clip_guard.stop()
            self.usb_monitor.stop()
            self.db.log_incident(3, "ЗАЩИТА ДЕАКТИВИРОВАНА")
            self.led_indicator.setStyleSheet(f"background-color: {TEXT_MUTED}; border-radius: 12px; border: none;")
            self.status_text.setText("СИСТЕМА ДЕАКТИВИРОВАНА")
            self.btn_arm.setText("АКТИВИРОВАТЬ ЗАЩИТУ")
            self.btn_select.setEnabled(True)
            self.card_status.lbl_value.setText("ОЖИДАНИЕ")
            self.card_status.lbl_value.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 28px; font-weight: bold; border: none;")
        
        self.update_stats()
    
    # Методы для удаленного управления
    def remote_arm(self):
        if not self.btn_arm.isChecked():
            self.btn_arm.setChecked(True)
            self.toggle_protection()

    def remote_disarm(self):
        if self.btn_arm.isChecked():
            self.btn_arm.setChecked(False)
            self.toggle_protection()

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

        self.policy_file_lock = PolicyCard("Блокировка файловой системы (Anti-Delete)", "Жесткая блокировка файлов (os.chmod).")
        self.policy_clipboard = PolicyCard("Контроль буфера обмена (DLP)", "Перехват попыток копирования данных.")
        self.policy_webcam = PolicyCard("Фото-фиксация нарушителя (Webcam Trap)", "Снимок с веб-камеры при нарушении.")
        self.policy_usb = PolicyCard("Контроль внешних носителей (USB Guard)", "Мониторинг подключения флешек.")
        self.policy_siren = PolicyCard("Аудио-оповещение (Siren Alarm)", "Сигнал тревоги при инциденте.", default_state=False)

        layout.addWidget(self.policy_file_lock)
        layout.addWidget(self.policy_clipboard)
        layout.addWidget(self.policy_webcam)
        layout.addWidget(self.policy_usb)
        layout.addWidget(self.policy_siren)
        layout.addStretch()

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
        header_layout = QHBoxLayout()
        title = QLabel("ЖУРНАЛ ИНЦИДЕНТОВ")
        title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 22px; font-weight: 600; letter-spacing: 1px;")
        btn_refresh = QPushButton("🔄 ОБНОВИТЬ")
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.setStyleSheet(f"QPushButton {{ background-color: transparent; border: 1px solid {BORDER_COLOR}; color: {TEXT_PRIMARY}; border-radius: 4px; padding: 8px 15px; font-weight: bold; font-size: 11px; }} QPushButton:hover {{ border: 1px solid {ACCENT_BLUE}; color: {ACCENT_BLUE}; }}")
        
        # ПРИ НАЖАТИИ ОБНОВИТЬ — обновляем и таблицу, и счетчик на главном экране
        btn_refresh.clicked.connect(self.refresh_all)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(btn_refresh)
        layout.addLayout(header_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ВРЕМЯ", "УРОВЕНЬ", "МОДУЛЬ", "ОПИСАНИЕ"])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet(f"QTableWidget {{ background-color: {BG_SURFACE}; border: 1px solid {BORDER_COLOR}; border-radius: 8px; color: {TEXT_PRIMARY}; font-size: 12px; }} QHeaderView::section {{ background-color: {BG_BASE}; color: {TEXT_MUTED}; font-size: 10px; font-weight: bold; padding: 10px; border: none; border-bottom: 2px solid {BORDER_COLOR}; }}")
        layout.addWidget(self.table)

    def refresh_all(self):
        self.load_logs()
        # Достукиваемся до DashboardPage и обновляем там статы
        main_win = self.window()
        main_win.page_dash.update_stats()

    def load_logs(self):
        self.table.setRowCount(0)
        logs = self.db.get_recent_logs(50)
        for row_idx, log in enumerate(logs):
            self.table.insertRow(row_idx)
            timestamp, policy_name, threat_level, details = log
            color = TEXT_PRIMARY
            if threat_level == "High": color = STATUS_DANGER
            item_level = QTableWidgetItem(str(threat_level))
            item_level.setForeground(QColor(color))
            self.table.setItem(row_idx, 0, QTableWidgetItem(str(timestamp)))
            self.table.setItem(row_idx, 1, item_level)
            self.table.setItem(row_idx, 2, QTableWidgetItem(str(policy_name)))
            self.table.setItem(row_idx, 3, QTableWidgetItem(str(details)))