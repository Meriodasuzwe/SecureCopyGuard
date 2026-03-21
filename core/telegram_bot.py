# core/telegram_bot.py

import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from PyQt5.QtCore import QThread, pyqtSignal
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

class TelegramAdminBot(QThread):
    arm_signal = pyqtSignal()
    disarm_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
        self.chat_id = int(TELEGRAM_CHAT_ID)
        self.is_running = True

    def run(self):
        def get_kb():
            kb = ReplyKeyboardMarkup(resize_keyboard=True)
            kb.add(KeyboardButton("🟢 АКТИВИРОВАТЬ"), KeyboardButton("🔴 ВЫКЛЮЧИТЬ"))
            kb.add(KeyboardButton("📊 СТАТУС"))
            return kb

        @self.bot.message_handler(commands=['start'])
        def start(m):
            if m.chat.id == self.chat_id:
                self.bot.send_message(m.chat.id, "🛡️ DLP Система на связи. Управление разрешено.", reply_markup=get_kb())

        @self.bot.message_handler(func=lambda m: m.text == "🟢 АКТИВИРОВАТЬ")
        def arm(m):
            if m.chat.id == self.chat_id:
                print("[BOT] Получена команда: Активировать")
                self.arm_signal.emit()
                self.bot.reply_to(m, "✅ Защита включена дистанционно.")

        @self.bot.message_handler(func=lambda m: m.text == "🔴 ВЫКЛЮЧИТЬ")
        def disarm(m):
            if m.chat.id == self.chat_id:
                print("[BOT] Получена команда: Выключить")
                self.disarm_signal.emit()
                self.bot.reply_to(m, "⚠️ Внимание! Защита отключена дистанционно.")

        @self.bot.message_handler(func=lambda m: m.text == "📊 СТАТУС")
        def status(m):
            if m.chat.id == self.chat_id:
                self.bot.reply_to(m, "🔋 *Статус:* Ядро активно.\n🖥️ Мониторинг портов: ВКЛ.\n🛡️ Жду команд.", parse_mode="Markdown")

        while self.is_running:
            try:
                self.bot.polling(none_stop=True, timeout=5)
            except Exception as e:
                print(f"[BOT ERROR] {e}")

    def stop(self):
        self.is_running = False
        self.bot.stop_polling()