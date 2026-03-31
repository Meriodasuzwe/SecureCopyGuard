# main.py

import os
import sys

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from PyQt5.QtWidgets import QApplication
from ui.main_window import MainWindow
from core.telegram_bot import TelegramAdminBot
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


def main():
    app = QApplication(sys.argv)

    # 1. Создаём интерфейс
    window = MainWindow()
    window.show()

    # 2. Telegram-бот (если токен задан)
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        try:
            admin_bot = TelegramAdminBot()

            # Связываем сигналы бота с методами страницы
            admin_bot.arm_signal.connect(window.page_dash.remote_arm)
            admin_bot.disarm_signal.connect(window.page_dash.remote_disarm)

            # Передаём ссылку на dashboard — для реального статуса
            admin_bot.set_dashboard(window.page_dash)

            admin_bot.start()

            # Сохраняем ссылку чтобы поток не удалился сборщиком мусора
            window.tg_bot = admin_bot
            print("[SYSTEM] Связь с Telegram установлена.")
        except Exception as e:
            print(f"[SYSTEM] Ошибка запуска Telegram-админки: {e}")

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()