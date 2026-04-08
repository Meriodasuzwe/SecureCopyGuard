# core/first_run.py
"""
Проверяет, нужен ли мастер первого запуска, и запускает его.
Вызывается из main.py ДО создания основного интерфейса MainWindow.
"""

import sys
from config import load_config

def check_and_run_wizard() -> bool:
    """
    Если config.json отсутствует или first_run==True — запускает SetupWizard.
    Возвращает True  — можно запускать основную программу.
    Возвращает False — юзер закрыл окно настройки, значит выходим.
    """
    cfg = load_config()

    if not cfg.get("first_run", True):
        return True   # Уже настроено, пропускаем мастера

    # Импортируем здесь, чтобы не было конфликтов до старта приложения
    from ui.setup_wizard import SetupWizard

    wizard = SetupWizard()
    wizard.exec_()   # Блокирует выполнение кода, пока окно не закроют

    # Проверяем, завершил ли юзер настройку (сохранился ли first_run = False)
    final_cfg = load_config()
    return not final_cfg.get("first_run", True)