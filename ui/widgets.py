# ui/widgets.py

from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox
from PyQt5.QtCore import Qt
from ui.theme import *

class MetricCard(QFrame):
    """Строгая корпоративная карточка для отображения статистики"""
    def __init__(self, title, value, value_color=TEXT_PRIMARY):
        super().__init__()
        # Задаем стиль карточки: фон панели и тонкая рамка
        self.setStyleSheet(f"""
            MetricCard {{
                background-color: {BG_SURFACE};
                border: 1px solid {BORDER_COLOR};
                border-radius: 6px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # Заголовок (например: ЗАБЛОКИРОВАНО УГРОЗ)
        self.lbl_title = QLabel(title.upper())
        self.lbl_title.setStyleSheet(f"""
            color: {TEXT_MUTED}; 
            font-size: 10px; 
            font-weight: bold; 
            letter-spacing: 1px;
            border: none;
        """)
        
        # Значение (например: 12)
        self.lbl_value = QLabel(str(value))
        self.lbl_value.setStyleSheet(f"""
            color: {value_color}; 
            font-size: 28px; 
            font-weight: bold;
            border: none;
        """)
        
        # Включаем перенос слов на случай длинных путей директорий
        self.lbl_value.setWordWrap(True)
        
        layout.addWidget(self.lbl_title)
        layout.addWidget(self.lbl_value)
        layout.addStretch() # Прижимаем контент вверх


class PolicyCard(QFrame):
    """Карточка для включения/отключения модулей защиты"""
    def __init__(self, title, description, default_state=True):
        super().__init__()
        self.setStyleSheet(f"""
            PolicyCard {{
                background-color: {BG_SURFACE};
                border: 1px solid {BORDER_COLOR};
                border-radius: 8px;
            }}
            PolicyCard:hover {{
                border: 1px solid #475569; /* Легкая подсветка при наведении */
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(25, 20, 25, 20)
        
        # Левая часть (Текст)
        text_layout = QVBoxLayout()
        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 14px; font-weight: bold; border: none;")
        
        self.lbl_desc = QLabel(description)
        self.lbl_desc.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; border: none;")
        self.lbl_desc.setWordWrap(True)
        
        text_layout.addWidget(self.lbl_title)
        text_layout.addWidget(self.lbl_desc)
        
        # Правая часть (Кастомный Чекбокс-переключатель)
        self.toggle = QCheckBox()
        self.toggle.setChecked(default_state)
        self.toggle.setCursor(Qt.PointingHandCursor)
        self.toggle.setStyleSheet(f"""
            QCheckBox::indicator {{
                width: 40px;
                height: 20px;
                border-radius: 10px;
                border: 1px solid {BORDER_COLOR};
                background-color: {BG_BASE};
            }}
            QCheckBox::indicator:checked {{
                background-color: {ACCENT_BLUE};
                border: 1px solid {ACCENT_BLUE};
            }}
        """)
        
        layout.addLayout(text_layout)
        layout.addStretch()
        layout.addWidget(self.toggle)

    def is_active(self):
        return self.toggle.isChecked()