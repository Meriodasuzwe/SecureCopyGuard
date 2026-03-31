# ui/main_window.py

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QFrame,
                             QButtonGroup, QStackedWidget)
from PyQt5.QtCore import Qt, QPoint

from ui.pages import DashboardPage, PoliciesPage, LogsPage, SettingsPage
from ui.theme import MAIN_STYLESHEET
from db.database import Database


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.resize(1100, 700)
        self.setStyleSheet(MAIN_STYLESHEET)
        self.oldPos = self.pos()

        # Инициализируем страницы ДО setup_ui
        self.page_dash     = DashboardPage()
        self.page_policies = PoliciesPage()
        self.page_logs     = LogsPage()
        self.page_settings = SettingsPage()

        self.setup_ui()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Title bar ──────────────────────────────────────────────────
        title_bar = QFrame()
        title_bar.setObjectName("TitleBar")
        title_bar.setFixedHeight(35)
        tb_layout = QHBoxLayout(title_bar)
        tb_layout.setContentsMargins(15, 0, 0, 0)

        title_lbl = QLabel("SECURE COPY GUARD :: DLP SYSTEM")
        title_lbl.setObjectName("TitleLabel")

        btn_min = QPushButton("—")
        btn_min.setObjectName("WindowBtn")
        btn_min.setFixedSize(45, 35)
        btn_min.clicked.connect(self.showMinimized)

        btn_close = QPushButton("✕")
        btn_close.setObjectName("CloseBtn")
        btn_close.setFixedSize(45, 35)
        btn_close.clicked.connect(self.close)

        tb_layout.addWidget(title_lbl)
        tb_layout.addStretch()
        tb_layout.addWidget(btn_min)
        tb_layout.addWidget(btn_close)

        # ── Sidebar + content ──────────────────────────────────────────
        work_area   = QFrame()
        work_layout = QHBoxLayout(work_area)
        work_layout.setContentsMargins(0, 0, 0, 0)
        work_layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("SideBar")
        sidebar.setFixedWidth(220)
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(0, 20, 0, 20)
        sb_layout.setSpacing(2)

        nav_lbl = QLabel("НАВИГАЦИЯ")
        nav_lbl.setStyleSheet(
            "color: #64748B; font-size: 10px; font-weight: bold; "
            "padding-left: 20px; margin-bottom: 10px;"
        )
        sb_layout.addWidget(nav_lbl)

        self.btn_dash     = self._menu_btn("DASHBOARD")
        self.btn_policies = self._menu_btn("ПОЛИТИКИ ЗАЩИТЫ")
        self.btn_logs     = self._menu_btn("ЖУРНАЛ ИНЦИДЕНТОВ")
        self.btn_settings = self._menu_btn("НАСТРОЙКИ СИСТЕМЫ")
        self.btn_dash.setChecked(True)

        group = QButtonGroup(self)
        for idx, btn in enumerate([
            self.btn_dash, self.btn_policies,
            self.btn_logs, self.btn_settings
        ]):
            group.addButton(btn, idx)
            sb_layout.addWidget(btn)

        group.buttonClicked[int].connect(self._switch_page)
        sb_layout.addStretch()

        ver = QLabel("v2.0.0 Pro")
        ver.setStyleSheet("color: #475569; font-size: 11px; padding-left: 20px;")
        sb_layout.addWidget(ver)

        self.pages = QStackedWidget()
        self.pages.setObjectName("ContentArea")
        for page in [self.page_dash, self.page_policies,
                     self.page_logs, self.page_settings]:
            self.pages.addWidget(page)

        work_layout.addWidget(sidebar)
        work_layout.addWidget(self.pages)

        root.addWidget(title_bar)
        root.addWidget(work_area)

    def _menu_btn(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName("MenuBtn")
        btn.setCheckable(True)
        btn.setCursor(Qt.PointingHandCursor)
        return btn

    def _switch_page(self, index: int):
        self.pages.setCurrentIndex(index)

    # ── Перетаскивание окна ────────────────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and event.pos().y() < 35:
            self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        if not self.oldPos.isNull():
            delta = event.globalPos() - self.oldPos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.oldPos = event.globalPos()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.oldPos = QPoint()

    # ── Корректное завершение ──────────────────────────────────────────
    def closeEvent(self, event):
        """Останавливаем все воркеры перед закрытием окна."""
        dash = self.page_dash
        dash.watcher.stop()
        dash.clip_guard.stop()
        dash.usb_monitor.stop()
        dash.vision_thread.stop()
        dash.stats_timer.stop()
        Database().close()
        event.accept()