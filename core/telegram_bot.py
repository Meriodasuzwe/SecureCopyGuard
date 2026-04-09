# core/telegram_bot.py

import time
import os
import ctypes
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from PyQt5.QtCore import QThread, pyqtSignal

from config import get_telegram_token, get_telegram_chat_id
from db.database import Database


class TelegramAdminBot(QThread):
    arm_signal    = pyqtSignal()
    disarm_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        # Берем данные через функции, чтобы они 100% обновились после Wizard'а
        self.token      = get_telegram_token()
        self.chat_id    = int(get_telegram_chat_id())
        
        # threaded=False - ОЧЕНЬ ВАЖНО для PyQt. Иначе telebot плодит свои потоки и конфликтует с UI
        self.bot        = telebot.TeleBot(self.token, threaded=False)
        self.is_running = True
        self._db        = Database()

        # Ссылка на DashboardPage — устанавливается из main.py
        self._dashboard = None

    def set_dashboard(self, dashboard):
        """Вызвать из main.py: admin_bot.set_dashboard(window.page_dash)"""
        self._dashboard = dashboard

    # ──────────────────────────────────────────────────────────────────

    def run(self):
        def _kb():
            kb = ReplyKeyboardMarkup(resize_keyboard=True)
            kb.add(KeyboardButton("🟢 АКТИВИРОВАТЬ"), KeyboardButton("🔴 ВЫКЛЮЧИТЬ"))
            kb.add(KeyboardButton("📊 СТАТУС"),        KeyboardButton("📋 ОТЧЁТ"))
            # ── ДОБАВЛЕНЫ КНОПКИ СМЕРТИ ──
            kb.add(KeyboardButton("💻 БЛОК ПК"),      KeyboardButton("🔌 ВЫРУБИТЬ ПК"))
            return kb

        # ── /start ────────────────────────────────────────────────────
        @self.bot.message_handler(commands=["start"])
        def cmd_start(m):
            if m.chat.id != self.chat_id:
                return
            self.bot.send_message(
                m.chat.id,
                "🛡️ *SecureCopyGuard DLP* на связи.\nВыберите действие:",
                reply_markup=_kb(),
                parse_mode="Markdown"
            )

        # ── Активировать ──────────────────────────────────────────────
        @self.bot.message_handler(func=lambda m: m.text == "🟢 АКТИВИРОВАТЬ")
        def cmd_arm(m):
            if m.chat.id != self.chat_id:
                return
            print("[BOT] Получена команда: Активировать")
            self.arm_signal.emit()
            self.bot.reply_to(m, "✅ Команда отправлена — защита *включается*.", parse_mode="Markdown")

        # ── Выключить ─────────────────────────────────────────────────
        @self.bot.message_handler(func=lambda m: m.text == "🔴 ВЫКЛЮЧИТЬ")
        def cmd_disarm(m):
            if m.chat.id != self.chat_id:
                return
            print("[BOT] Получена команда: Выключить")
            self.disarm_signal.emit()
            self.bot.reply_to(m, "⚠️ Команда отправлена — защита *отключается*.", parse_mode="Markdown")

        # ── Статус — реальные данные из БД ────────────────────────────
        @self.bot.message_handler(func=lambda m: m.text == "📊 СТАТУС")
        def cmd_status(m):
            if m.chat.id != self.chat_id:
                return

            armed = (
                self._dashboard.is_armed
                if self._dashboard is not None
                else None
            )
            status_str = (
                "🟢 АКТИВНА"  if armed is True  else
                "🔴 ВЫКЛЮЧЕНА" if armed is False else
                "❓ Неизвестно"
            )

            total      = self._db.get_incident_count()
            stats      = self._db.get_stats_by_module()
            stats_text = "\n".join(
                f"  • {row[0]}: *{row[2]}* ({row[1]})"
                for row in stats
            ) or "  нет данных"

            folder = (
                self._dashboard.target_folder
                if self._dashboard and self._dashboard.target_folder
                else "не задана"
            )

            text = (
                f"🛡️ *SecureCopyGuard — Статус системы*\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"Состояние защиты: {status_str}\n"
                f"Целевая директория: `{folder}`\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"Инцидентов (High): *{total}*\n\n"
                f"По модулям:\n{stats_text}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🕐 {time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            self.bot.reply_to(m, text, parse_mode="Markdown")

        # ── Отчёт ─────────────────────────────────────────────────────
        @self.bot.message_handler(func=lambda m: m.text == "📋 ОТЧЁТ")
        def cmd_report(m):
            if m.chat.id != self.chat_id:
                return
            try:
                from ui.pdf_report import generate_report
                path = generate_report()
                if path:
                    with open(path, "rb") as f:
                        self.bot.send_document(
                            m.chat.id, f,
                            caption="📄 Отчёт об инцидентах сформирован."
                        )
                else:
                    self.bot.reply_to(m, "❌ Не удалось создать отчёт. Проверьте fpdf2.")
            except Exception as exc:
                self.bot.reply_to(m, f"❌ Ошибка: {exc}")

        # ── Блокировка экрана (Lock Windows) ──────────────────────────
        @self.bot.message_handler(func=lambda m: m.text == "💻 БЛОК ПК")
        def cmd_lock_pc(m):
            if m.chat.id != self.chat_id:
                return
            
            # Вызываем системную функцию Windows для немедленной блокировки сеанса (Win + L)
            ctypes.windll.user32.LockWorkStation()
            
            self.bot.reply_to(m, "🔒 *Компьютер немедленно заблокирован!*\nПользователь выкинут на экран ввода пароля Windows.", parse_mode="Markdown")
            print("[BOT] Выполнена команда: Блокировка ПК")

        # ── Экстренное выключение (Shutdown) ──────────────────────────
        @self.bot.message_handler(func=lambda m: m.text == "🔌 ВЫРУБИТЬ ПК")
        def cmd_shutdown_pc(m):
            if m.chat.id != self.chat_id:
                return
            
            # /s - выключение, /t 10 - через 10 секунд, /c - комментарий на весь экран
            os.system('shutdown /s /t 10 /c "SECURE COPY GUARD: КРИТИЧЕСКАЯ УГРОЗА УТЕЧКИ. КОМПЬЮТЕР БУДЕТ ВЫКЛЮЧЕН."')
            
            self.bot.reply_to(m, "☠️ *Отправлена команда на экстренное ВЫКЛЮЧЕНИЕ!*\nУ нарушителя есть 10 секунд до отключения питания.", parse_mode="Markdown")
            print("[BOT] Выполнена команда: Выключение ПК")

        # ── Приветствие при запуске программы ─────────────────────────
        try:
            # Сразу присылаем клавиатуру, чтобы было удобно тыкать кнопки
            self.bot.send_message(
                self.chat_id, 
                "✅ SecureCopyGuard успешно запущен и подключён к сети!", 
                reply_markup=_kb()
            )
        except Exception as e:
            print(f"[BOT] Ошибка стартового сообщения: {e}")

        # ── Polling loop (БЕССМЕРТНЫЙ ЦИКЛ) ───────────────────────────
        while self.is_running:
            try:
                # none_stop=True — запрещаем боту сдаваться при мелких ошибках сети!
                self.bot.polling(none_stop=True, interval=0, timeout=20)
            except Exception as exc:
                print(f"[BOT ERROR] {exc}")
                time.sleep(3)   # пауза 3 секунды перед жестким переподключением

    def stop(self):
        self.is_running = False
        try:
            self.bot.stop_polling()
        except Exception:
            pass
        self.wait(3000)