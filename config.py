import os
import json
import hashlib
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные из .env (для обратной совместимости)
load_dotenv()

# ── Пути ──────────────────────────────────────────────────────────────
BASE_DIR          = Path(__file__).resolve().parent
CONFIG_FILE       = BASE_DIR / "config.json"
DB_PATH           = BASE_DIR / "dlp_logs.db"
INTRUDER_FOLDER   = BASE_DIR / "_INTRUDERS"
QUARANTINE_FOLDER = BASE_DIR / "_QUARANTINE"

# Создаём системные папки при импорте
INTRUDER_FOLDER.mkdir(parents=True, exist_ok=True)
QUARANTINE_FOLDER.mkdir(parents=True, exist_ok=True)

# Расширения файлов для мониторинга
SUPPORTED_EXTENSIONS = ['.docx', '.doc', '.xlsx', '.pdf', '.jpg', '.png', '.jpeg', '.txt']

# ── Шаблон настроек по умолчанию ──────────────────────────────────────
_DEFAULT_CONFIG = {
    "first_run":        True,
    "protected_folder": "",
    "pin_hash":         "",        # sha256 от PIN
    "autostart":        False,
    "telegram_token":   "",
    "telegram_chat_id": "",
}


# ── Загрузка / сохранение config.json ─────────────────────────────────

def load_config() -> dict:
    """Читает config.json. Если файла нет — создаёт с дефолтными значениями."""
    if not CONFIG_FILE.exists():
        save_config(_DEFAULT_CONFIG.copy())
        return _DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Добавляем новые ключи если конфиг старый
        for k, v in _DEFAULT_CONFIG.items():
            data.setdefault(k, v)
        return data
    except Exception:
        return _DEFAULT_CONFIG.copy()


def save_config(cfg: dict) -> None:
    """Атомарная запись config.json."""
    try:
        tmp = CONFIG_FILE.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        tmp.replace(CONFIG_FILE)
    except Exception as e:
        print(f"[CONFIG] Ошибка сохранения: {e}")


def get_config_value(key: str, default=None):
    """Читает одно значение из config.json."""
    return load_config().get(key, default)


def set_config_value(key: str, value) -> None:
    """Устанавливает одно значение и сохраняет файл."""
    cfg = load_config()
    cfg[key] = value
    save_config(cfg)


# ── PIN-утилиты ───────────────────────────────────────────────────────

def hash_pin(pin: str) -> str:
    """Возвращает sha256-хэш PIN-кода."""
    return hashlib.sha256(pin.strip().encode()).hexdigest()


def verify_pin(pin: str) -> bool:
    """Проверяет PIN против сохранённого хэша."""
    stored = get_config_value("pin_hash", "")
    if not stored:
        return True   # PIN не задан — проверка пропускается
    return hash_pin(pin) == stored


# ── Динамические значения (читаются из config.json каждый раз) ────────

def get_telegram_token() -> str:
    cfg = load_config()
    return cfg.get("telegram_token") or os.getenv("TELEGRAM_BOT_TOKEN", "")


def get_telegram_chat_id() -> str:
    cfg = load_config()
    return cfg.get("telegram_chat_id") or os.getenv("TELEGRAM_CHAT_ID", "")


# ── Статические переменные (для обратной совместимости) ───────────────
# Telegram-токены теперь читаются через get_telegram_token()
# Но модули, которые уже импортируют TELEGRAM_BOT_TOKEN, получат
# значение из .env (как и раньше). Этого достаточно для старых модулей.
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "")
ADMIN_PIN          = os.getenv("ADMIN_PIN", "1234")