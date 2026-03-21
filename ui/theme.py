# ui/theme.py

# Палитра корпоративного кибербеза (Slate Dark Theme)
BG_BASE = "#0F172A"       # Самый темный фон (основа)
BG_SURFACE = "#1E293B"    # Фон панелей и карточек
TEXT_PRIMARY = "#F8FAFC"  # Белый текст
TEXT_MUTED = "#94A3B8"    # Серый текст (для подписей)
ACCENT_BLUE = "#3B82F6"   # Акцентный синий (кнопки, выделение)
STATUS_OK = "#10B981"     # Строгий зеленый
STATUS_DANGER = "#EF4444" # Строгий красный
BORDER_COLOR = "#334155"  # Тонкие границы панелей

# Главный стиль приложения
MAIN_STYLESHEET = f"""
    QMainWindow {{
        background-color: {BG_BASE};
    }}
    
    /* Верхняя панель управления окном */
    #TitleBar {{
        background-color: {BG_BASE};
        border-bottom: 1px solid {BORDER_COLOR};
    }}
    #TitleLabel {{
        color: {TEXT_PRIMARY};
        font-family: 'Segoe UI', Arial, sans-serif;
        font-weight: 600;
        font-size: 13px;
        letter-spacing: 1px;
        padding-left: 15px;
    }}
    
    /* Кнопки закрытия/сворачивания */
    QPushButton#WindowBtn {{
        background-color: transparent;
        color: {TEXT_MUTED};
        font-family: 'Segoe UI';
        font-size: 12px;
        border: none;
    }}
    QPushButton#WindowBtn:hover {{
        background-color: {BG_SURFACE};
        color: {TEXT_PRIMARY};
    }}
    QPushButton#CloseBtn:hover {{
        background-color: {STATUS_DANGER};
        color: white;
    }}

    /* Боковое меню (Сайдбар) */
    #SideBar {{
        background-color: {BG_SURFACE};
        border-right: 1px solid {BORDER_COLOR};
    }}
    
    QPushButton#MenuBtn {{
        background-color: transparent;
        color: {TEXT_MUTED};
        font-family: 'Segoe UI';
        font-size: 13px;
        font-weight: 500;
        text-align: left;
        padding: 12px 20px;
        border: none;
        border-left: 3px solid transparent; /* Подготовка под активный стейт */
    }}
    QPushButton#MenuBtn:hover {{
        background-color: #273548;
        color: {TEXT_PRIMARY};
    }}
    QPushButton#MenuBtn:checked {{
        background-color: #1e293b;
        color: {ACCENT_BLUE};
        font-weight: 600;
        border-left: 3px solid {ACCENT_BLUE}; /* Синяя полоса слева */
    }}

    /* Зона контента */
    #ContentArea {{
        background-color: {BG_BASE};
    }}
"""