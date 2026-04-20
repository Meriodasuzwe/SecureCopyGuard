# ui/widgets.py

from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QWidget
from PyQt5.QtGui import QPainter, QPainterPath, QPen, QColor
from PyQt5.QtCore import Qt
from ui.theme import *

class VectorIcon(QWidget):
    """Свой собственный отрисовщик премиальных векторных иконок через математику"""
    def __init__(self, icon_type, color_hex):
        super().__init__()
        self.icon_type = icon_type
        self.color = QColor(color_hex)
        self.setFixedSize(24, 24)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing) # Включаем сглаживание

        # Настраиваем "перо" (линию)
        pen = QPen(self.color)
        pen.setWidth(2)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)

        path = QPainterPath()

        if self.icon_type == "folder":
            # Рисуем контур папки
            path.moveTo(3, 20)
            path.lineTo(3, 6)
            path.lineTo(9, 6)
            path.lineTo(12, 9)
            path.lineTo(21, 9)
            path.lineTo(21, 20)
            path.closeSubpath()
            painter.drawPath(path)

        elif self.icon_type == "shield":
            # Рисуем строгий щит безопасности
            path.moveTo(12, 3)
            path.lineTo(21, 7)
            path.lineTo(21, 13)
            # Используем кривые Безье для закругления низа щита
            path.quadTo(21, 20, 12, 22)
            path.quadTo(3, 20, 3, 13)
            path.lineTo(3, 7)
            path.closeSubpath()
            painter.drawPath(path)

        elif self.icon_type == "pulse":
            # Рисуем пульс (активность ядра)
            path.moveTo(2, 12)
            path.lineTo(7, 12)
            path.lineTo(10, 4)
            path.lineTo(14, 20)
            path.lineTo(17, 12)
            path.lineTo(22, 12)
            painter.drawPath(path)


class MetricCard(QFrame):
    """Премиальная карточка для отображения статистики (Glassmorphism + Вектор)"""
    def __init__(self, icon_type, title, value, color):
        super().__init__()
        
        try:
            hex_color = color.lstrip('#')
            if len(hex_color) == 6:
                r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                glass_bg = f"rgba({r}, {g}, {b}, 0.15)"
            else:
                glass_bg = "rgba(255, 255, 255, 0.1)"
        except Exception:
            glass_bg = "rgba(255, 255, 255, 0.1)"

        self.setStyleSheet(f"""
            MetricCard {{
                background-color: #1E293B;
                border: 1px solid {BORDER_COLOR};
                border-radius: 16px;
            }}
            MetricCard:hover {{
                border: 1px solid {color};
                background-color: #233147;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        # ─── ШАПКА КАРТОЧКИ (Иконка + Текст) ───
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        # Контейнер для эффекта "стекла" вокруг иконки
        icon_container = QWidget()
        icon_container.setFixedSize(38, 38)
        icon_container.setStyleSheet(f"background-color: {glass_bg}; border-radius: 10px;")
        
        icon_layout = QVBoxLayout(icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setAlignment(Qt.AlignCenter)
        
        # 🔥 Вставляем нашу кастомную векторную иконку
        vector_icon = VectorIcon(icon_type, color)
        icon_layout.addWidget(vector_icon)

        title_lbl = QLabel(title.upper())
        title_lbl.setStyleSheet("""
            color: #94A3B8; 
            font-size: 11px; 
            font-weight: 800; 
            letter-spacing: 1.5px; 
            border: none; 
            background: transparent;
        """)

        header_layout.addWidget(icon_container)
        header_layout.addWidget(title_lbl)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        layout.addSpacing(4)

        # ─── ЗНАЧЕНИЕ ───
        self.lbl_value = QLabel(value)
        self.lbl_value.setStyleSheet(f"""
            color: {color}; 
            font-size: 26px; 
            font-weight: 900; 
            border: none; 
            background: transparent;
            font-family: 'Segoe UI', Arial;
        """)
        self.lbl_value.setWordWrap(True)
        
        layout.addWidget(self.lbl_value)
        layout.addStretch()


class PolicyCard(QFrame):
    """Карточка для включения/отключения модулей защиты"""
    def __init__(self, title, description, default_state=True):
        super().__init__()
        self.setStyleSheet(f"""
            PolicyCard {{
                background-color: {BG_SURFACE};
                border: 1px solid {BORDER_COLOR};
                border-radius: 16px;
            }}
            PolicyCard:hover {{
                border: 1px solid #475569;
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(25, 20, 25, 20)
        
        text_layout = QVBoxLayout()
        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 14px; font-weight: bold; border: none;")
        
        self.lbl_desc = QLabel(description)
        self.lbl_desc.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; border: none;")
        self.lbl_desc.setWordWrap(True)
        
        text_layout.addWidget(self.lbl_title)
        text_layout.addWidget(self.lbl_desc)
        
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