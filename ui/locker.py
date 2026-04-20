# ui/locker.py

import sys
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QApplication, QFrame
from PyQt5.QtCore import Qt, QTimer
from config import verify_pin, set_config_value

class HardLockScreen(QWidget):
    """
    Агрессивный локер экрана (Kiosk Mode).
    Неубиваем через Alt+F4, перекрывает Диспетчер задач.
    """
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.start_aggressive_defense()

    def setup_ui(self):
        # ─── ФЛАГИ БЕССМЕРТИЯ ───
        # Убираем рамки, делаем окно всегда поверх всех (даже Диспетчера задач)
        # И убираем иконку из панели задач (Tool)
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.Tool | 
            Qt.CustomizeWindowHint
        )
        self.showFullScreen() # На весь экран
        self.setStyleSheet("background-color: #000000;") # Глухой черный фон

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(30)

        # ─── УГРОЖАЮЩИЙ ИНТЕРФЕЙС ───
        alert_icon = QLabel("⚠️")
        alert_icon.setStyleSheet("font-size: 72px; background: transparent; border: none;")
        alert_icon.setAlignment(Qt.AlignCenter)
        
        title = QLabel("РАБОЧАЯ СТАНЦИЯ ЗАБЛОКИРОВАНА")
        title.setStyleSheet("color: #EF4444; font-size: 32px; font-weight: 900; letter-spacing: 4px; background: transparent; border: none;")
        title.setAlignment(Qt.AlignCenter)

        subtitle = QLabel("Доступ ограничен Службой Информационной Безопасности.\nВсе действия логируются и передаются администратору.")
        subtitle.setStyleSheet("color: #94A3B8; font-size: 16px; background: transparent; border: none;")
        subtitle.setAlignment(Qt.AlignCenter)

        # Поле для PIN-кода
        self.pin_input = QLineEdit()
        self.pin_input.setEchoMode(QLineEdit.Password)
        self.pin_input.setPlaceholderText("Введите Master-PIN для разблокировки")
        self.pin_input.setFixedSize(400, 60)
        self.pin_input.setAlignment(Qt.AlignCenter)
        self.pin_input.setStyleSheet("""
            QLineEdit {
                background-color: #0F172A;
                border: 2px solid #EF4444;
                border-radius: 8px;
                color: white;
                font-size: 18px;
                font-weight: bold;
                letter-spacing: 8px;
            }
            QLineEdit:focus { border: 2px solid #F87171; }
        """)

        self.err_lbl = QLabel("")
        self.err_lbl.setStyleSheet("color: #EF4444; font-size: 14px; font-weight: bold; background: transparent; border: none;")
        self.err_lbl.setAlignment(Qt.AlignCenter)

        btn_unlock = QPushButton("РАЗБЛОКИРОВАТЬ")
        btn_unlock.setFixedSize(400, 50)
        btn_unlock.setCursor(Qt.PointingHandCursor)
        btn_unlock.setStyleSheet("""
            QPushButton {
                background-color: #EF4444;
                color: white;
                font-weight: 800;
                font-size: 16px;
                letter-spacing: 2px;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover { background-color: #DC2626; }
        """)
        btn_unlock.clicked.connect(self.try_unlock)
        self.pin_input.returnPressed.connect(self.try_unlock)

        # Явно центрируем каждый элемент при добавлении в слой!
        layout.addWidget(alert_icon, alignment=Qt.AlignCenter)
        layout.addWidget(title, alignment=Qt.AlignCenter)
        layout.addWidget(subtitle, alignment=Qt.AlignCenter)
        layout.addSpacing(20)
        layout.addWidget(self.pin_input, alignment=Qt.AlignCenter)
        layout.addWidget(self.err_lbl, alignment=Qt.AlignCenter)
        layout.addWidget(btn_unlock, alignment=Qt.AlignCenter)

    def start_aggressive_defense(self):
        """Агрессивный таймер: не дает переключиться на другое окно"""
        self.defense_timer = QTimer(self)
        self.defense_timer.timeout.connect(self._steal_focus)
        self.defense_timer.start(100) # Каждые 100 миллисекунд!

    def _steal_focus(self):
        self.raise_()
        self.activateWindow()
        self.pin_input.setFocus()

    def closeEvent(self, event):
        """🛡️ Игнорируем Alt+F4 и попытки закрыть окно с крестика"""
        event.ignore()

    def try_unlock(self):
        pin = self.pin_input.text().strip()
        if verify_pin(pin):
            self.defense_timer.stop() # Отключаем защиту
            set_config_value("hard_lock", False) # Снимаем метку смерти
            self.hide() # Прячем окно
            self.deleteLater() # Убиваем объект
        else:
            self.pin_input.clear()
            self.err_lbl.setText("❌ НЕВЕРНЫЙ PIN-КОД!")