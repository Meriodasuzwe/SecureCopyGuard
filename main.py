# main.py

import os
import sys

# ФИКС ОШИБКИ 1114: Грузим тяжелые C++ библиотеки нейросети и камеры 
# ДО ТОГО, как загрузится графический интерфейс PyQt5 и перехватит потоки
import torch
import cv2

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt

from core.single_instance import ensure_single_instance, release_mutex
from core.first_run        import check_and_run_wizard
from core.process_guard    import protect_process
from config                import get_telegram_token, get_telegram_chat_id, get_config_value


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    # ── 1. Один экземпляр ───────────────────────────────────────────
    if not ensure_single_instance():
        QMessageBox.warning(
            None,
            "SecureCopyGuard",
            "⚠️ SecureCopyGuard уже запущен.\n\nПроверьте системный трей.",
            QMessageBox.Ok
        )
        sys.exit(0)

    # ── 2. Мастер первого запуска ───────────────────────────────────
    if not check_and_run_wizard():
        release_mutex()
        sys.exit(0)

    # ── 3. Защита процесса от Kill ──────────────────────────────────
    protect_process()

    # ── 4. Импортируем UI ПОСЛЕ wizard (конфиг уже готов) ──────────
    from ui.main_window import MainWindow
    from core.telegram_bot import TelegramAdminBot

    window = MainWindow()

    # Восстанавливаем папку из прошлого сеанса
    saved_folder = get_config_value("protected_folder", "")
    if saved_folder:
        window.page_dash.restore_folder(saved_folder)

    window.show()

    # ── 5. Telegram-бот ─────────────────────────────────────────────
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
            print("[SYSTEM] Связь с Telegram установлена.")
        except Exception as e:
            print(f"[SYSTEM] Ошибка запуска Telegram-админки: {e}")

    ret = app.exec_()
    release_mutex()
    sys.exit(ret)


if __name__ == "__main__":
    main()