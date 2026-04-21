# ui/widgets.py

from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QWidget
from PyQt5.QtGui import QPainter, QPainterPath, QPen, QColor
from PyQt5.QtCore import Qt, QPropertyAnimation, pyqtProperty, QEasingCurve, QRectF
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
        painter.setRenderHint(QPainter.Antialiasing)

        pen = QPen(self.color)
        pen.setWidth(2)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)

        path = QPainterPath()

        if self.icon_type == "folder":
            path.moveTo(3, 20)
            path.lineTo(3, 6)
            path.lineTo(9, 6)
            path.lineTo(12, 9)
            path.lineTo(21, 9)
            path.lineTo(21, 20)
            path.closeSubpath()
            painter.drawPath(path)

        elif self.icon_type == "shield":
            path.moveTo(12, 3)
            path.lineTo(21, 7)
            path.lineTo(21, 13)
            path.quadTo(21, 20, 12, 22)
            path.quadTo(3, 20, 3, 13)
            path.lineTo(3, 7)
            path.closeSubpath()
            painter.drawPath(path)

        elif self.icon_type == "pulse":
            path.moveTo(2, 12)
            path.lineTo(7, 12)
            path.lineTo(10, 4)
            path.lineTo(14, 20)
            path.lineTo(17, 12)
            path.lineTo(22, 12)
            painter.drawPath(path)
        
        elif self.icon_type == "paper_plane":
            # Рисуем самолетик Telegram
            path.moveTo(2, 12)
            path.lineTo(22, 2)
            path.lineTo(15, 22)
            path.lineTo(11, 14)
            path.lineTo(2, 12)
            path.moveTo(11, 14)
            path.lineTo(22, 2)
            painter.drawPath(path)
            
        elif self.icon_type == "gear":
            # Рисуем ползунки настроек (выглядит круче, чем просто шестеренка)
            path.moveTo(4, 8)
            path.lineTo(20, 8)
            path.moveTo(14, 4)
            path.lineTo(14, 12)
            path.moveTo(4, 16)
            path.lineTo(20, 16)
            path.moveTo(10, 12)
            path.lineTo(10, 20)
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

        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        icon_container = QWidget()
        icon_container.setFixedSize(38, 38)
        icon_container.setStyleSheet(f"background-color: {glass_bg}; border-radius: 10px;")
        
        icon_layout = QVBoxLayout(icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setAlignment(Qt.AlignCenter)
        
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


class AnimatedToggle(QCheckBox):
    """Кастомный плавный переключатель в стиле iOS / Android"""
    def __init__(self, default_state=False, parent=None):
        super().__init__(parent)
        self.setFixedSize(50, 26) 
        self.setCursor(Qt.PointingHandCursor)
        
        self._position = 27 if default_state else 3
        self.setChecked(default_state)

        self.animation = QPropertyAnimation(self, b"position")
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.animation.setDuration(250) 
        
        self.stateChanged.connect(self.setup_animation)

    # 🔥 ИСПРАВЛЕНИЕ КЛИКА: Указываем PyQt, что вся площадь виджета реагирует на мышку
    def hitButton(self, pos):
        return self.rect().contains(pos)

    @pyqtProperty(float)
    def position(self):
        return self._position

    @position.setter
    def position(self, pos):
        self._position = pos
        self.update() 

    def setup_animation(self, value):
        self.animation.stop()
        if value:
            self.animation.setEndValue(27) 
        else:
            self.animation.setEndValue(3)  
        self.animation.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, self.width(), self.height()), 13, 13)
        
        if self.isChecked():
            painter.setBrush(QColor(ACCENT_BLUE)) 
        else:
            painter.setBrush(QColor("#334155"))   
            
        painter.setPen(Qt.NoPen)
        painter.drawPath(path)
        
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawEllipse(QRectF(self._position, 3, 20, 20))


class PolicyCard(QFrame):
    """Карточка политики с плавающим тумблером"""
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
                background-color: #233147;
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(25, 20, 25, 20)
        
        text_layout = QVBoxLayout()
        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 14px; font-weight: 900; border: none; background: transparent;")
        
        self.lbl_desc = QLabel(description)
        self.lbl_desc.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px; border: none; background: transparent;")
        self.lbl_desc.setWordWrap(True)
        
        text_layout.addWidget(self.lbl_title)
        text_layout.addWidget(self.lbl_desc)
        
        self.toggle = AnimatedToggle(default_state=default_state)
        
        layout.addLayout(text_layout)
        layout.addSpacing(20)
        layout.addWidget(self.toggle, alignment=Qt.AlignRight | Qt.AlignVCenter)

    def is_active(self):
        return self.toggle.isChecked()