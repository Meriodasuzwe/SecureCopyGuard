# main.py

import os
import sys
import traceback
import tempfile

# ── 0. ПУЛЕНЕПРОБИВАЕМЫЙ ЧЕРНЫЙ ЯЩИК ──────────────────────────────
# Пишем лог в системную временную папку (C:\Users\User\AppData\Local\Temp)
# Этот путь существует ВСЕГДА и на ЛЮБОЙ винде.
crash_log_path = os.path.join(tempfile.gettempdir(), "DLP_CRASH_LOG.txt")

try:
    log_file = open(crash_log_path, "w", encoding="utf-8")
    sys.stdout = log_file
    sys.stderr = log_file
except Exception:
    pass # Если чудо-ошибка, не роняем прогу

def global_exception_handler(exc_type, exc_value, exc_traceback):
    try:
        with open(crash_log_path, "a", encoding="utf-8") as f:
            f.write("\n" + "!"*50 + "\n")
            f.write("🔥 ПРИЛОЖЕНИЕ УПАЛО С ОШИБКОЙ:\n")
            traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
            f.write("!"*50 + "\n")
    except Exception:
        pass
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

sys.excepthook = global_exception_handler
# ───────────────────────────────────────────────────────────────

import torch
import cv2

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt

from core.single_instance import ensure_single_instance, release_mutex
from core.first_run        import check_and_run_wizard
from config                import get_telegram_token, get_telegram_chat_id, get_config_value


def main():
    print("[DEBUG] Старт функции main()")
    
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    print("[DEBUG] Проверка на один экземпляр...")
    if not ensure_single_instance():
        print("[DEBUG] Ошибка: Программа уже запущена")
        sys.exit(0)

    print("[DEBUG] Проверка First Run Wizard...")
    if not check_and_run_wizard():
        print("[DEBUG] Wizard не пройден, выход.")
        release_mutex()
        sys.exit(0)

    print("[DEBUG] Импорт интерфейса и создание окна...")
    from ui.main_window import MainWindow
    from core.telegram_bot import TelegramAdminBot

    window = MainWindow()

    saved_folder = get_config_value("protected_folder", "")
    if saved_folder:
        print(f"[DEBUG] Восстановление папки: {saved_folder}")
        window.page_dash.restore_folder(saved_folder)

    print("[DEBUG] Показ главного окна...")
    window.show()

    print("[DEBUG] Запуск Telegram бота...")
    token   = get_telegram_token()
    chat_id = get_telegram_chat_id()

    if token and chat_id:
        try:
            admin_bot = TelegramAdminBot()
            admin_bot.arm_signal.connect(window.page_dash.remote_arm)
            admin_bot.disarm_signal.connect(window.page_dash.remote_disarm)
            admin_bot.set_dashboard(window.page_dash)
            admin_bot.start()
            window.tg_bot = admin_bot
            print("[DEBUG] Связь с Telegram установлена.")
        except Exception as e:
            print(f"[DEBUG] Ошибка запуска Telegram-админки: {e}")

    print("[DEBUG] Вход в главный цикл приложения app.exec_()...")
    ret = app.exec_()
    
    print("[DEBUG] Приложение закрывается штатно.")
    release_mutex()
    sys.exit(ret)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        with open(crash_log_path, "a", encoding="utf-8") as f:
            f.write(f"\nКРИТИЧЕСКИЙ СБОЙ ПРИ ЗАПУСКЕ: {e}\n")