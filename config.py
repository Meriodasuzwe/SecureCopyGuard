import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

# ОПРЕДЕЛЯЕМ ПУТИ (современный подход через Path)
# BASE_DIR указывает на корень проекта
BASE_DIR = Path(__file__).resolve().parent

INTRUDER_FOLDER = BASE_DIR / os.getenv("INTRUDER_FOLDER", "_INTRUDERS")
QUARANTINE_FOLDER = BASE_DIR / os.getenv("QUARANTINE_FOLDER", "_QUARANTINE")
DB_PATH = BASE_DIR / "dlp_logs.db"

# Автоматически создаем системные папки, если их нет
INTRUDER_FOLDER.mkdir(parents=True, exist_ok=True)
QUARANTINE_FOLDER.mkdir(parents=True, exist_ok=True)

# СЕКРЕТЫ И НАСТРОЙКИ
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
ADMIN_PIN = os.getenv("ADMIN_PIN", "1234")

# Общие настройки (можно расширять)
SUPPORTED_EXTENSIONS = ['.docx', '.doc', '.xlsx', '.pdf', '.jpg', '.png', '.jpeg', '.txt']