# core/telegram_bot.py

import time
import os
import ctypes
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from PyQt5.QtCore import QThread, pyqtSignal, QMetaObject, Qt

from config import get_telegram_token, get_telegram_chat_id, set_config_value
from db.database import Database

class TelegramAdminBot(QThread):
    arm_signal    = pyqtSignal()
    disarm_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.token      = get_telegram_token()
        self.chat_id    = int(get_telegram_chat_id())
        self.bot        = telebot.TeleBot(self.token, threaded=False)
        self.is_running = True
        self._db        = Database()
        self._dashboard = None

    def set_dashboard(self, dashboard):
        """Вызвать из main.py: admin_bot.set_dashboard(window.page_dash)"""
        self._dashboard = dashboard

    def run(self):
        def _kb():
            kb = ReplyKeyboardMarkup(resize_keyboard=True)
            kb.add(KeyboardButton("🟢 АКТИВИРОВАТЬ"), KeyboardButton("🔴 ВЫКЛЮЧИТЬ"))
            kb.add(KeyboardButton("📊 СТАТУС"),        KeyboardButton("📋 ОТЧЁТ"))
            # 🔥 НОВЫЕ КНОПКИ: Мягкий и Жесткий лок
            kb.add(KeyboardButton("💻 СОФТ-ЛОК (Win)"), KeyboardButton("🧱 ХАРД-ЛОК (DLP)"))
            kb.add(KeyboardButton("🔌 ВЫРУБИТЬ ПК"))
            return kb

        @self.bot.message_handler(commands=["start"])
        def cmd_start(m):
            if m.chat.id != self.chat_id: return
            self.bot.send_message(m.chat.id, "🛡️ *SecureCopyGuard DLP* на связи.\nВыберите действие:", reply_markup=_kb(), parse_mode="Markdown")

        @self.bot.message_handler(func=lambda m: m.text == "🟢 АКТИВИРОВАТЬ")
        def cmd_arm(m):
            if m.chat.id != self.chat_id: return
            self.arm_signal.emit()
            self.bot.reply_to(m, "✅ Команда отправлена — защита *включается*.", parse_mode="Markdown")

        @self.bot.message_handler(func=lambda m: m.text == "🔴 ВЫКЛЮЧИТЬ")
        def cmd_disarm(m):
            if m.chat.id != self.chat_id: return
            self.disarm_signal.emit()
            self.bot.reply_to(m, "⚠️ Команда отправлена — защита *отключается*.", parse_mode="Markdown")

        @self.bot.message_handler(func=lambda m: m.text == "📊 СТАТУС")
        def cmd_status(m):
            if m.chat.id != self.chat_id: return
            armed = self._dashboard.is_armed if self._dashboard is not None else None
            status_str = "🟢 АКТИВНА" if armed is True else "🔴 ВЫКЛЮЧЕНА" if armed is False else "❓ Неизвестно"
            total = self._db.get_incident_count()
            stats = self._db.get_stats_by_module()
            stats_text = "\n".join(f"  • {row[0]}: *{row[2]}* ({row[1]})" for row in stats) or "  нет данных"
            folder = self._dashboard.target_folder if self._dashboard and self._dashboard.target_folder else "не задана"

            text = (
                f"🛡️ *SecureCopyGuard — Статус*\n━━━━━━━━━━━━━━━━━━\nСостояние: {status_str}\n"
                f"Директория: `{folder}`\n━━━━━━━━━━━━━━━━━━\nИнцидентов (High): *{total}*\n\n"
                f"Модули:\n{stats_text}\n━━━━━━━━━━━━━━━━━━\n🕐 {time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            self.bot.reply_to(m, text, parse_mode="Markdown")

        @self.bot.message_handler(func=lambda m: m.text == "📋 ОТЧЁТ")
        def cmd_report(m):
            if m.chat.id != self.chat_id: return
            try:
                from ui.pdf_report import generate_report
                path = generate_report()
                if path:
                    with open(path, "rb") as f:
                        self.bot.send_document(m.chat.id, f, caption="📄 Отчёт об инцидентах сформирован.")
                else:
                    self.bot.reply_to(m, "❌ Не удалось создать отчёт.")
            except Exception as exc:
                self.bot.reply_to(m, f"❌ Ошибка: {exc}")

        # ── СОФТ-ЛОК (Обычный Win+L) ──
        @self.bot.message_handler(func=lambda m: m.text == "💻 СОФТ-ЛОК (Win)")
        def cmd_lock_pc(m):
            if m.chat.id != self.chat_id: return
            ctypes.windll.user32.LockWorkStation()
            self.bot.reply_to(m, "🔒 *Базовая блокировка выполнена!*\nПользователь выкинут на экран ввода пароля Windows.", parse_mode="Markdown")

        # 🔥 АГРЕССИВНЫЙ ХАРД-ЛОК (Наш черный экран) ──
        @self.bot.message_handler(func=lambda m: m.text == "🧱 ХАРД-ЛОК (DLP)")
        def cmd_hard_lock(m):
            if m.chat.id != self.chat_id: return
            set_config_value("hard_lock", True)
            
            # Безопасно вызываем метод UI из фонового потока
            if self._dashboard:
                QMetaObject.invokeMethod(self._dashboard, "trigger_hard_lock", Qt.QueuedConnection)
                
            self.bot.reply_to(m, " *АГРЕССИВНАЯ БЛОКИРОВКА АКТИВИРОВАНА!*\nПК заблокирован глухим экраном. Снять можно только через Master-PIN в программе.", parse_mode="Markdown")

        @self.bot.message_handler(func=lambda m: m.text == "🔌 ВЫРУБИТЬ ПК")
        def cmd_shutdown_pc(m):
            if m.chat.id != self.chat_id: return
            os.system('shutdown /s /t 10 /c "SECURE COPY GUARD: КРИТИЧЕСКАЯ УГРОЗА УТЕЧКИ. КОМПЬЮТЕР БУДЕТ ВЫКЛЮЧЕН."')
            self.bot.reply_to(m, "☠️ *Отправлена команда на экстренное ВЫКЛЮЧЕНИЕ!*\nУ нарушителя есть 10 секунд.", parse_mode="Markdown")

        try:
            self.bot.send_message(self.chat_id, "✅ SecureCopyGuard успешно запущен и подключён к сети!", reply_markup=_kb())
        except Exception:
            pass

        while self.is_running:
            try:
                self.bot.polling(none_stop=True, interval=0, timeout=20)
            except Exception as exc:
                print(f"[BOT ERROR] {exc}")
                time.sleep(3)

    def stop(self):
        self.is_running = False
        try:
            self.bot.stop_polling()
        except Exception:
            pass
        self.wait(3000)