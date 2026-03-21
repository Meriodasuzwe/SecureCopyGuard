# ui/main_window.py

import sys
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QFrame, 
                             QButtonGroup, QStackedWidget)
from PyQt5.QtCore import Qt, QPoint
from ui.pages import DashboardPage, PoliciesPage, LogsPage
from ui.theme import MAIN_STYLESHEET

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.resize(1100, 700)
        self.setStyleSheet(MAIN_STYLESHEET)
        
        self.oldPos = self.pos()
        
        # --- ВАЖНО: Инициализируем страницы ПЕРЕД setup_ui ---
        self.page_dash = DashboardPage()
        self.page_policies = PoliciesPage()
        self.page_logs = LogsPage()
        self.page_settings = QWidget()

        self.setup_ui()

    def setup_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 1. TITLE BAR
        self.title_bar = QFrame()
        self.title_bar.setObjectName("TitleBar")
        self.title_bar.setFixedHeight(35)
        self.title_layout = QHBoxLayout(self.title_bar)
        self.title_layout.setContentsMargins(15, 0, 0, 0)

        self.title_label = QLabel("SECURE COPY GUARD :: DLP SYSTEM")
        self.title_label.setObjectName("TitleLabel")
        
        self.btn_min = QPushButton("—")
        self.btn_min.setObjectName("WindowBtn")
        self.btn_min.setFixedSize(45, 35)
        self.btn_min.clicked.connect(self.showMinimized)

        self.btn_close = QPushButton("✕")
        self.btn_close.setObjectName("CloseBtn")
        self.btn_close.setFixedSize(45, 35)
        self.btn_close.clicked.connect(self.close)

        self.title_layout.addWidget(self.title_label)
        self.title_layout.addStretch()
        self.title_layout.addWidget(self.btn_min)
        self.title_layout.addWidget(self.btn_close)

        # 2. РАБОЧАЯ ЗОНА
        self.work_area = QFrame()
        self.work_layout = QHBoxLayout(self.work_area)
        self.work_layout.setContentsMargins(0, 0, 0, 0)
        self.work_layout.setSpacing(0)

        # САЙДБАР
        self.side_bar = QFrame()
        self.side_bar.setObjectName("SideBar")
        self.side_bar.setFixedWidth(220)
        self.side_layout = QVBoxLayout(self.side_bar)
        self.side_layout.setContentsMargins(0, 20, 0, 20)
        self.side_layout.setSpacing(2)

        nav_label = QLabel("НАВИГАЦИЯ")
        nav_label.setStyleSheet("color: #64748B; font-size: 10px; font-weight: bold; padding-left: 20px; margin-bottom: 10px;")
        self.side_layout.addWidget(nav_label)

        self.btn_dash = self.create_menu_btn("DASHBOARD")
        self.btn_policies = self.create_menu_btn("ПОЛИТИКИ ЗАЩИТЫ")
        self.btn_logs = self.create_menu_btn("ЖУРНАЛ ИНЦИДЕНТОВ")
        self.btn_settings = self.create_menu_btn("НАСТРОЙКИ СИСТЕМЫ")

        self.btn_dash.setChecked(True)

        self.menu_group = QButtonGroup(self)
        self.menu_group.addButton(self.btn_dash, 0)
        self.menu_group.addButton(self.btn_policies, 1)
        self.menu_group.addButton(self.btn_logs, 2)
        self.menu_group.addButton(self.btn_settings, 3)
        self.menu_group.buttonClicked[int].connect(self.switch_page)

        self.side_layout.addWidget(self.btn_dash)
        self.side_layout.addWidget(self.btn_policies)
        self.side_layout.addWidget(self.btn_logs)
        self.side_layout.addWidget(self.btn_settings)
        self.side_layout.addStretch()

        version_label = QLabel("v. 2.0.0 Pro")
        version_label.setStyleSheet("color: #475569; font-size: 11px; padding-left: 20px;")
        self.side_layout.addWidget(version_label)

        # КОНТЕНТ
        self.pages = QStackedWidget()
        self.pages.setObjectName("ContentArea")
        self.pages.addWidget(self.page_dash)
        self.pages.addWidget(self.page_policies)
        self.pages.addWidget(self.page_logs)
        self.pages.addWidget(self.page_settings)

        self.work_layout.addWidget(self.side_bar)
        self.work_layout.addWidget(self.pages)

        self.main_layout.addWidget(self.title_bar)
        self.main_layout.addWidget(self.work_area)

    def create_menu_btn(self, text):
        btn = QPushButton(text)
        btn.setObjectName("MenuBtn")
        btn.setCheckable(True)
        btn.setCursor(Qt.PointingHandCursor)
        return btn

    def switch_page(self, index):
        self.pages.setCurrentIndex(index)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and event.pos().y() < 35:
            self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        if not self.oldPos.isNull():
            delta = QPoint(event.globalPos() - self.oldPos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.oldPos = event.globalPos()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.oldPos = QPoint()