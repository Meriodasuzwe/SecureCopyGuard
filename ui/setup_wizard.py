# ui/setup_wizard.py
"""
Мастер первого запуска SecureCopyGuard.
Запускается один раз при первом старте.
"""

import requests
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFileDialog, QCheckBox, QFrame, QStackedWidget,
    QSizePolicy, QWidget
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont

from config import save_config, load_config, hash_pin
from core.autostart import enable_autostart, disable_autostart

# ── Цветовая палитра ──────────────────────────────────────────────────
BG        = "#0F172A"
SURFACE   = "#1E293B"
BORDER    = "#334155"
ACCENT    = "#3B82F6"
TEXT      = "#F8FAFC"
MUTED     = "#94A3B8"
SUCCESS   = "#10B981"
DANGER    = "#EF4444"
ORANGE    = "#F59E0B"

# ── Утилиты ────────────────────────────────────────────────────────────
def _label(text: str, size: int = 13, color: str = TEXT, bold: bool = False) -> QLabel:
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    font = QFont("Segoe UI", size)
    font.setBold(bold)
    lbl.setFont(font)
    lbl.setStyleSheet(f"color: {color}; background: transparent;")
    return lbl

def _input(placeholder: str = "", password: bool = False) -> QLineEdit:
    w = QLineEdit()
    w.setPlaceholderText(placeholder)
    if password:
        w.setEchoMode(QLineEdit.Password)
    w.setStyleSheet(
        f"QLineEdit {{ background: {SURFACE}; color: {TEXT}; "
        f"border: 1px solid {BORDER}; border-radius: 5px; "
        f"padding: 10px 12px; font-size: 13px; }}"
        f"QLineEdit:focus {{ border: 1px solid {ACCENT}; }}"
    )
    return w

def _btn(text: str, primary: bool = True) -> QPushButton:
    bg = ACCENT if primary else SURFACE
    b = QPushButton(text)
    b.setCursor(Qt.PointingHandCursor)
    b.setFixedHeight(42)
    b.setFont(QFont("Segoe UI", 11, QFont.Bold))
    b.setStyleSheet(
        f"QPushButton {{ background: {bg}; color: {TEXT}; border: 1px solid {BORDER}; "
        f"border-radius: 5px; padding: 0 20px; }}"
        f"QPushButton:hover {{ background: {'#2563EB' if primary else '#273548'}; }}"
        f"QPushButton:disabled {{ background: {BORDER}; color: {MUTED}; }}"
    )
    return b

# ── Поток для проверки Telegram ────────────────────────────────────────
class _TelegramChecker(QThread):
    result = pyqtSignal(bool, str)

    def __init__(self, token: str, chat_id: str):
        super().__init__()
        self.token   = token.strip()
        self.chat_id = chat_id.strip()

    def run(self):
        try:
            url  = f"https://api.telegram.org/bot{self.token}/getMe"
            resp = requests.get(url, timeout=7)
            if not resp.ok:
                self.result.emit(False, "❌ Неверный токен Telegram.")
                return
            bot_name = resp.json().get("result", {}).get("username", "?")

            url2 = f"https://api.telegram.org/bot{self.token}/sendMessage"
            r2   = requests.post(url2, json={
                "chat_id": self.chat_id,
                "text": "✅ SecureCopyGuard успешно подключён к Telegram!",
            }, timeout=7)
            if not r2.ok:
                self.result.emit(False, f"❌ Ошибка отправки. Проверьте Chat ID.\n{r2.text[:120]}")
                return
            self.result.emit(True, f"✅ Бот @{bot_name} подключён!")
        except requests.Timeout:
            self.result.emit(False, "❌ Таймаут. Проверьте интернет.")
        except Exception as e:
            self.result.emit(False, f"❌ Ошибка: {e}")

# ══════════════════════════════════════════════════════════════════════
#  Страницы Wizard
# ══════════════════════════════════════════════════════════════════════
class _WelcomePage(QWidget):
    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setSpacing(18)
        lay.setContentsMargins(0, 10, 0, 10)

        icon = QLabel("🛡️")
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("font-size: 64px; background: transparent;")

        lay.addStretch()
        lay.addWidget(icon)
        lay.addWidget(_label("Добро пожаловать в\nSecureCopyGuard DLP", 20, TEXT, bold=True))
        lay.addSpacing(8)
        lay.addWidget(_label(
            "Этот мастер поможет быстро настроить систему защиты данных.\n\n"
            "Вам понадобится:\n"
            "  • Telegram-бот (токен от @BotFather)\n"
            "  • Ваш Telegram Chat ID\n"
            "  • Придумать PIN-код для защиты настроек\n\n"
            "Настройка займёт ~2 минуты.", 12, MUTED
        ))
        lay.addStretch()

class _TelegramPage(QWidget):
    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        lay.setContentsMargins(0, 10, 0, 10)

        lay.addWidget(_label("📱 Настройка Telegram", 18, TEXT, bold=True))
        lay.addWidget(_label(
            "1. Напишите @BotFather → /newbot → получите токен\n"
            "2. Напишите своему боту любое сообщение\n"
            "3. Узнайте свой Chat ID через бота @userinfobot", 11, MUTED
        ))
        lay.addSpacing(6)

        lay.addWidget(_label("Bot Token:", 12))
        self.token_input = _input("1234567890:ABCdef...")
        lay.addWidget(self.token_input)

        lay.addWidget(_label("Chat ID:", 12))
        self.chat_input = _input("123456789")
        lay.addWidget(self.chat_input)

        row = QHBoxLayout()
        self.btn_check = _btn("🔍  Проверить подключение", primary=False)
        self.btn_check.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        row.addWidget(self.btn_check)
        lay.addLayout(row)

        self.status_lbl = _label("", 11, MUTED)
        self.status_lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.status_lbl)

        lay.addStretch()
        self._checker = None
        self.btn_check.clicked.connect(self._check)

    def _check(self):
        token   = self.token_input.text().strip()
        chat_id = self.chat_input.text().strip()
        if not token or not chat_id:
            self.status_lbl.setText("⚠️ Заполните оба поля.")
            self.status_lbl.setStyleSheet(f"color: {ORANGE};")
            return
        self.btn_check.setEnabled(False)
        self.status_lbl.setStyleSheet(f"color: {MUTED};")
        self.status_lbl.setText("⏳ Проверяю...")

        self._checker = _TelegramChecker(token, chat_id)
        self._checker.result.connect(self._on_result)
        self._checker.start()

    def _on_result(self, ok: bool, msg: str):
        self.btn_check.setEnabled(True)
        color = SUCCESS if ok else DANGER
        self.status_lbl.setStyleSheet(f"color: {color};")
        self.status_lbl.setText(msg)

    def get_data(self) -> tuple[str, str]:
        return self.token_input.text().strip(), self.chat_input.text().strip()

class _PinPage(QWidget):
    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        lay.setContentsMargins(0, 10, 0, 10)

        lay.addWidget(_label("🔐 Защита администратора", 18, TEXT, bold=True))
        lay.addWidget(_label(
            "PIN-код запрашивается при деактивации защиты и изменении настроек.\n"
            "Минимум 4 символа. Если оставить пустым — защита PIN-кодом будет отключена.", 12, MUTED
        ))
        lay.addSpacing(8)

        lay.addWidget(_label("Новый PIN:", 12))
        self.pin1 = _input("Введите PIN", password=True)
        lay.addWidget(self.pin1)

        lay.addWidget(_label("Повторите PIN:", 12))
        self.pin2 = _input("Подтвердите PIN", password=True)
        lay.addWidget(self.pin2)

        self.err_lbl = _label("", 11, DANGER)
        lay.addWidget(self.err_lbl)
        lay.addStretch()

    def validate(self) -> bool:
        p1, p2 = self.pin1.text().strip(), self.pin2.text().strip()
        if not p1 and not p2:
            self.err_lbl.setText("")
            return True   # разрешаем пустой PIN
        if len(p1) < 4:
            self.err_lbl.setText("❌ PIN должен быть не короче 4 символов.")
            return False
        if p1 != p2:
            self.err_lbl.setText("❌ PIN-коды не совпадают.")
            return False
        self.err_lbl.setText("")
        return True

    def get_pin(self) -> str:
        return self.pin1.text().strip()

class _FolderPage(QWidget):
    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        lay.setContentsMargins(0, 10, 0, 10)

        lay.addWidget(_label("📁 Параметры запуска", 18, TEXT, bold=True))
        lay.addWidget(_label(
            "Выберите папку, которую система будет защищать по умолчанию.",
            12, MUTED
        ))
        lay.addSpacing(8)

        row = QHBoxLayout()
        self.folder_lbl = _label("Не выбрана", 12, MUTED)
        self.btn_browse  = _btn("Обзор...", primary=False)
        self.btn_browse.setFixedWidth(120)
        self.btn_browse.clicked.connect(self._browse)
        row.addWidget(self.folder_lbl, 1)
        row.addWidget(self.btn_browse)
        lay.addLayout(row)
        lay.addSpacing(20)

        self.cb_autostart = QCheckBox("  Запускать SecureCopyGuard при старте Windows")
        self.cb_autostart.setStyleSheet(
            f"QCheckBox {{ font-size: 13px; color: {TEXT}; }}"
            f"QCheckBox::indicator {{ width: 18px; height: 18px; border: 2px solid {BORDER}; "
            f"border-radius: 4px; background: {SURFACE}; }}"
            f"QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}"
        )
        lay.addWidget(self.cb_autostart)
        lay.addStretch()
        self._folder = ""

    def _browse(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите защищаемую папку")
        if folder:
            self._folder = folder
            short = folder if len(folder) < 50 else "..." + folder[-48:]
            self.folder_lbl.setText(short)
            self.folder_lbl.setStyleSheet(f"color: {TEXT}; font-size: 12px;")

    def get_data(self) -> tuple[str, bool]:
        return self._folder, self.cb_autostart.isChecked()

class _DonePage(QWidget):
    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setSpacing(16)
        lay.setContentsMargins(0, 10, 0, 10)

        lay.addStretch()
        ok = QLabel("✅")
        ok.setAlignment(Qt.AlignCenter)
        ok.setStyleSheet("font-size: 60px; background: transparent;")

        lay.addWidget(ok)
        lay.addWidget(_label("Настройка завершена!", 22, SUCCESS, bold=True))
        lay.addWidget(_label(
            "SecureCopyGuard готов к работе.\n\n"
            "Вы можете изменить настройки в панели управления.",
            13, MUTED
        ))
        lay.addStretch()

# ══════════════════════════════════════════════════════════════════════
#  Главный диалог wizard
# ══════════════════════════════════════════════════════════════════════
class SetupWizard(QDialog):
    TITLES = [
        "Добро пожаловать",
        "Telegram-уведомления",
        "PIN-защита",
        "Папка и автозапуск",
        "Всё готово!",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SecureCopyGuard — Настройка")
        self.setFixedSize(560, 500)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setStyleSheet(f"background: {BG};")

        self._step = 0
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── Заголовок ──────────────────────────────────────────────
        header = QFrame()
        header.setFixedHeight(56)
        header.setStyleSheet(f"background: {SURFACE}; border-bottom: 1px solid {BORDER};")
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(24, 0, 24, 0)

        self.step_lbl = _label("Шаг 1 из 4", 10, MUTED)
        self.title_lbl = _label("Добро пожаловать", 14, TEXT, bold=True)
        h_lay.addWidget(self.step_lbl)
        h_lay.addStretch()
        h_lay.addWidget(self.title_lbl)
        lay.addWidget(header)

        # ── Страницы ───────────────────────────────────────────────
        self.stack = QStackedWidget()
        self.pg_welcome  = _WelcomePage()
        self.pg_telegram = _TelegramPage()
        self.pg_pin      = _PinPage()
        self.pg_folder   = _FolderPage()
        self.pg_done     = _DonePage()

        for pg in [self.pg_welcome, self.pg_telegram, self.pg_pin, self.pg_folder, self.pg_done]:
            self.stack.addWidget(pg)

        content = QFrame()
        content.setStyleSheet(f"background: {BG};")
        c_lay = QVBoxLayout(content)
        c_lay.setContentsMargins(32, 24, 32, 8)
        c_lay.addWidget(self.stack)
        lay.addWidget(content, 1)

        # ── Кнопки навигации ───────────────────────────────────────
        foot = QFrame()
        foot.setFixedHeight(64)
        foot.setStyleSheet(f"background: {SURFACE}; border-top: 1px solid {BORDER};")
        f_lay = QHBoxLayout(foot)
        f_lay.setContentsMargins(24, 0, 24, 0)
        f_lay.setSpacing(12)

        self.btn_back = _btn("◀  Назад", primary=False)
        self.btn_back.setFixedWidth(130)
        self.btn_back.clicked.connect(self._go_back)
        self.btn_back.setEnabled(False)

        self.btn_next = _btn("Далее  ▶")
        self.btn_next.setFixedWidth(160)
        self.btn_next.clicked.connect(self._go_next)

        self.btn_skip = _btn("Пропустить", primary=False)
        self.btn_skip.setFixedWidth(130)
        self.btn_skip.clicked.connect(self._skip_telegram)
        self.btn_skip.setVisible(False)

        f_lay.addWidget(self.btn_back)
        f_lay.addWidget(self.btn_skip)
        f_lay.addStretch()
        f_lay.addWidget(self.btn_next)
        lay.addWidget(foot)

        self._update_ui()

    def _go_next(self):
        if self._step == 2:      # Валидация PIN
            if not self.pg_pin.validate(): return

        if self._step < 4:
            self._step += 1
            self.stack.setCurrentIndex(self._step)
            if self._step == 4:
                self._save_and_finish()
        else:
            self.accept()

        self._update_ui()

    def _go_back(self):
        if self._step > 0:
            self._step -= 1
            self.stack.setCurrentIndex(self._step)
            self._update_ui()

    def _skip_telegram(self):
        self._step = 2
        self.stack.setCurrentIndex(self._step)
        self._update_ui()

    def _update_ui(self):
        n = self._step
        total = 4
        self.step_lbl.setText(f"Шаг {min(n+1, total)} из {total}" if n < 4 else "")
        self.title_lbl.setText(self.TITLES[n])
        self.btn_back.setEnabled(n > 0 and n < 4)
        self.btn_skip.setVisible(n == 1)
        if n == 4:
            self.btn_next.setText("✅  Запустить")
            self.btn_back.setEnabled(False)
        else:
            self.btn_next.setText("Далее  ▶")

    def _save_and_finish(self):
        cfg = load_config()
        cfg["first_run"] = False

        token, chat_id = self.pg_telegram.get_data()
        if token:
            cfg["telegram_token"]   = token
            cfg["telegram_chat_id"] = chat_id

        pin = self.pg_pin.get_pin()
        if pin:
            cfg["pin_hash"] = hash_pin(pin)

        folder, autostart = self.pg_folder.get_data()
        if folder:
            cfg["protected_folder"] = folder
        cfg["autostart"] = autostart

        save_config(cfg)

        if autostart:
            try: enable_autostart()
            except: pass
        else:
            try: disable_autostart()
            except: pass

        if token:
            _patch_env_file(token, chat_id)

    def reject(self):
        pass   # Запрещаем закрытие окна по крестику/Esc

def _patch_env_file(token: str, chat_id: str):
    from pathlib import Path
    env_path = Path(__file__).resolve().parent.parent / ".env"
    try:
        lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
        lines = [l for l in lines if not l.startswith("TELEGRAM_BOT_TOKEN=") and not l.startswith("TELEGRAM_CHAT_ID=")]
        lines += [f"TELEGRAM_BOT_TOKEN={token}", f"TELEGRAM_CHAT_ID={chat_id}"]
        env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception as e:
        print(f"[WIZARD] Ошибка обновления .env: {e}")