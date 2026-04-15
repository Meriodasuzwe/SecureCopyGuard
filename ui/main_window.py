# ui/main_window.py

from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QStackedWidget, QDialog, QLabel, QLineEdit, QFrame
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon, QFont
from ui.pages import DashboardPage, PoliciesPage, LogsPage, SettingsPage
from ui.theme import *
from config import verify_pin, get_config_value

# ── Диалог ввода PIN-кода ──────────────────────────────────────────
class UnlockDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Блокировка DLP")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        base_layout = QVBoxLayout(self)
        base_layout.setContentsMargins(0, 0, 0, 0)

        self.container = QFrame()
        self.container.setObjectName("MainContainer")
        self.container.setMinimumWidth(420)
        self.container.setStyleSheet(f"""
            QFrame#MainContainer {{
                background-color: {BG_SURFACE};
                border: 2px solid {BORDER_COLOR};
                border-radius: 10px;
            }}
        """)
        base_layout.addWidget(self.container)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        lbl = QLabel("🛡️ Введите Master-PIN для выхода:")
        lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 16px; font-weight: bold; border: none; background: transparent;")
        lbl.setWordWrap(True)
        layout.addWidget(lbl)

        self.pin_input = QLineEdit()
        self.pin_input.setEchoMode(QLineEdit.Password)
        self.pin_input.setPlaceholderText("PIN-код")
        self.pin_input.setMinimumHeight(50)
        self.pin_input.setStyleSheet(
            f"QLineEdit {{ padding: 0 15px; background: {BG_BASE}; color: {TEXT_PRIMARY}; "
            f"border-radius: 6px; border: 1px solid {BORDER_COLOR}; font-size: 18px; letter-spacing: 5px; }}"
            f"QLineEdit:focus {{ border: 1px solid {ACCENT_BLUE}; }}"
        )
        layout.addWidget(self.pin_input)

        self.err_lbl = QLabel("")
        self.err_lbl.setStyleSheet(f"color: {STATUS_DANGER}; font-size: 14px; border: none; background: transparent;")
        self.err_lbl.setMinimumHeight(20)
        layout.addWidget(self.err_lbl)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(15)

        btn_cancel = QPushButton("Отмена")
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setMinimumHeight(45)
        btn_cancel.setStyleSheet(
            f"QPushButton {{ background: {BG_BASE}; color: {TEXT_PRIMARY}; border: 1px solid {BORDER_COLOR}; "
            f"border-radius: 6px; font-weight: bold; font-size: 14px; }}"
            f"QPushButton:hover {{ background: #334155; }}"
        )
        btn_cancel.clicked.connect(self.reject)

        btn_ok = QPushButton("Подтвердить")
        btn_ok.setCursor(Qt.PointingHandCursor)
        btn_ok.setMinimumHeight(45)
        btn_ok.setStyleSheet(
            f"QPushButton {{ background: {STATUS_DANGER}; color: white; border: none; "
            f"border-radius: 6px; font-weight: bold; font-size: 14px; }}"
            f"QPushButton:hover {{ background: #DC2626; }}"
        )
        btn_ok.clicked.connect(self.check)

        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)
        self.adjustSize()

    def check(self):
        entered = self.pin_input.text().strip()
        if verify_pin(entered):
            self.accept()
        else:
            self.err_lbl.setText("❌ Неверный PIN-код!")
            self.pin_input.clear()


# ── Главное окно программы ─────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SecureCopyGuard - DLP Core")
        self.setMinimumSize(1100, 700)
        self.setStyleSheet(f"background-color: {BG_BASE};")
        
        self.tg_bot = None

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Боковое меню
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(260)
        self.sidebar.setStyleSheet(f"background-color: {BG_SURFACE}; border-right: 1px solid {BORDER_COLOR};")
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 30, 0, 30)
        sidebar_layout.setSpacing(10)

        logo_lbl = QLabel("SecureCopyGuard")
        logo_lbl.setStyleSheet(f"color: {ACCENT_BLUE}; font-size: 20px; font-weight: 800; padding: 0 20px 20px 20px; border: none;")
        sidebar_layout.addWidget(logo_lbl)

        self.btn_dash     = self._create_nav_btn("Обзор системы")
        self.btn_policies = self._create_nav_btn("Политики")
        self.btn_logs     = self._create_nav_btn("Журнал событий")
        self.btn_settings = self._create_nav_btn("Настройки")

        sidebar_layout.addWidget(self.btn_dash)
        sidebar_layout.addWidget(self.btn_policies)
        sidebar_layout.addWidget(self.btn_logs)
        sidebar_layout.addWidget(self.btn_settings)
        sidebar_layout.addStretch()

        # Версия
        version_lbl = QLabel("v2.1 Enterprise")
        version_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; padding: 0 20px; border: none;")
        sidebar_layout.addWidget(version_lbl)

        main_layout.addWidget(self.sidebar)

        # Область контента
        self.stack = QStackedWidget()
        self.page_dash     = DashboardPage()
        self.page_policies = PoliciesPage()
        self.page_logs     = LogsPage()
        self.page_settings = SettingsPage()

        self.stack.addWidget(self.page_dash)
        self.stack.addWidget(self.page_policies)
        self.stack.addWidget(self.page_logs)
        self.stack.addWidget(self.page_settings)

        main_layout.addWidget(self.stack)

        # Сигналы навигации
        self.btn_dash.clicked.connect(lambda: self._switch_page(0, self.btn_dash))
        self.btn_policies.clicked.connect(lambda: self._switch_page(1, self.btn_policies))
        self.btn_logs.clicked.connect(lambda: self._switch_page(2, self.btn_logs))
        self.btn_settings.clicked.connect(lambda: self._switch_page(3, self.btn_settings))

        self._switch_page(0, self.btn_dash)

    def _create_nav_btn(self, text):
        btn = QPushButton(text)
        btn.setFixedHeight(50)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(
            f"QPushButton {{ text-align: left; padding-left: 25px; border: none; font-size: 14px; font-weight: 600; color: {TEXT_MUTED}; background: transparent; }}"
            f"QPushButton:hover {{ color: {TEXT_PRIMARY}; background-color: rgba(255,255,255,0.02); }}"
        )
        return btn

    def _switch_page(self, index, active_btn):
        self.stack.setCurrentIndex(index)
        for btn in [self.btn_dash, self.btn_policies, self.btn_logs, self.btn_settings]:
            btn.setStyleSheet(
                f"QPushButton {{ text-align: left; padding-left: 25px; border: none; font-size: 14px; font-weight: 600; color: {TEXT_MUTED}; background: transparent; }}"
                f"QPushButton:hover {{ color: {TEXT_PRIMARY}; background-color: rgba(255,255,255,0.02); }}"
            )
        active_btn.setStyleSheet(
            f"QPushButton {{ text-align: left; padding-left: 22px; border: none; border-left: 3px solid {ACCENT_BLUE}; "
            f"font-size: 14px; font-weight: 600; color: {TEXT_PRIMARY}; background-color: rgba(59, 130, 246, 0.1); }}"
        )
        if index == 2:
            self.page_logs.refresh_all()

    # ── ПЕРЕХВАТ ЗАКРЫТИЯ ОКНА (КРЕСТИК / ALT+F4) ────────────────────
    
    def closeEvent(self, event):
        from core.telegram_alerts import send_telegram_alert
        import os # ДОБАВИТЬ ИМПОРТ
        
        # Вычисляем точный путь к папке проекта
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        flag_path = os.path.join(base_dir, "legal_exit.flag")
        
        if hasattr(self, 'page_dash') and self.page_dash.is_armed:
            from ui.pages import PinDialog
            from PyQt5.QtWidgets import QDialog
            
            dialog = PinDialog(self)
            if dialog.exec_() == QDialog.Accepted:
                # ─── СОЗДАЕМ ФЛАГ ТОЧНО В КОРНЕ ПРОЕКТА ───
                open(flag_path, "w").close() 
                
                send_telegram_alert("⭕ СТАТУС: Агент SecureCopyGuard остановлен легально (Введен Master-PIN).")
                event.accept() 
            else:
                event.ignore()
        else:
            open(flag_path, "w").close() 
            send_telegram_alert("⭕ СТАТУС: Программа закрыта (защита была неактивна).")
            event.accept()