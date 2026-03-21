# main.py

import sys
from PyQt5.QtWidgets import QApplication
from ui.main_window import MainWindow
from core.telegram_bot import TelegramAdminBot
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

def main():
    app = QApplication(sys.argv)
    
    # 1. Создаем интерфейс
    window = MainWindow()
    window.show()

    # 2. Запускаем бота-админа
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        try:
            admin_bot = TelegramAdminBot()
            
            # --- СВЯЗКА: Сигналы бота -> Методы страницы ---
            admin_bot.arm_signal.connect(window.page_dash.remote_arm)
            admin_bot.disarm_signal.connect(window.page_dash.remote_disarm)
            
            admin_bot.start()
            
            # Сохраняем ссылку, чтобы поток не удалился
            window.tg_bot = admin_bot
            print("[SYSTEM] Связь с Telegram установлена.")
        except Exception as e:
            print(f"[SYSTEM] Ошибка запуска Telegram-админки: {e}")

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()