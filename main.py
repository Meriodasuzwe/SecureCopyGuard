# main.py

import sys
import os
import time
import subprocess
import shutil
import tempfile
import traceback
import ctypes

# ── 0. ПУЛЕНЕПРОБИВАЕМЫЙ ЧЕРНЫЙ ЯЩИК ──
crash_log_path = os.path.join(tempfile.gettempdir(), "DLP_CRASH_LOG.txt")
try:
    log_file = open(crash_log_path, "a", encoding="utf-8")
    sys.stdout = log_file
    sys.stderr = log_file
except Exception:
    pass

def global_exception_handler(exc_type, exc_value, exc_traceback):
    try:
        with open(crash_log_path, "a", encoding="utf-8") as f:
            f.write("\n" + "!"*50 + "\n")
            f.write(f"[{time.strftime('%X')}] 🔥 КРИТИЧЕСКАЯ ОШИБКА:\n")
            traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
            f.write("!"*50 + "\n")
    except Exception:
        pass
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

sys.excepthook = global_exception_handler

# ─── 100% НАДЕЖНЫЕ ПУТИ ───
WATCHDOG_LOG = os.path.join(tempfile.gettempdir(), "dlp_watchdog.log")

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ─── ЛОВУШКА СТОРОЖА (В САМОМ ВЕРХУ!) ───
if "--watchdog" in sys.argv:
    target_pid = int(sys.argv[sys.argv.index("--watchdog") + 1])
    original_dir = sys.argv[sys.argv.index("--watchdog") + 2] 

    # ─── УНИКАЛЬНЫЙ ИМЕННОЙ ФЛАГ С PID ПРОГРАММЫ ───
    FLAG_FILE = os.path.join(tempfile.gettempdir(), f"dlp_legal_exit_{target_pid}.flag")

    import json
    import urllib.request
    import urllib.parse

    with open(WATCHDOG_LOG, "w", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%X')}] СТОРОЖ ЗАПУЩЕН. PID: {target_pid}, Оригинал: {original_dir}\n")

    kernel32 = ctypes.windll.kernel32
    time.sleep(3) 
    
    while True:
        try:
            with open(WATCHDOG_LOG, "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%X')}] Тик... проверяю пульс PID {target_pid}\n")

            h_process = kernel32.OpenProcess(0x0400, False, target_pid)
            alive = False
            if h_process:
                exit_code = ctypes.c_ulong()
                kernel32.GetExitCodeProcess(h_process, ctypes.byref(exit_code))
                kernel32.CloseHandle(h_process)
                alive = (exit_code.value == 259)

            if not alive:
                with open(WATCHDOG_LOG, "a", encoding="utf-8") as f:
                    f.write(f"[{time.strftime('%X')}] ПУЛЬС ПРОПАЛ! Процесс мертв.\n")

                if os.path.exists(FLAG_FILE):
                    os.remove(FLAG_FILE)
                    with open(WATCHDOG_LOG, "a", encoding="utf-8") as f:
                        f.write(f"[{time.strftime('%X')}] Флаг легального выхода найден. Сплю.\n")
                else:
                    with open(WATCHDOG_LOG, "a", encoding="utf-8") as f:
                        f.write(f"[{time.strftime('%X')}] Флага НЕТ. Шлю Telegram алерт!\n")
                        
                    # ─── ПРЯМАЯ ОТПРАВКА БЕЗ СТОРОННИХ МОДУЛЕЙ ───
                    try:
                        config_path = os.path.join(original_dir, "config.json")
                        with open(config_path, "r", encoding="utf-8") as f_cfg:
                            cfg = json.load(f_cfg)
                        
                        token = cfg.get("telegram_token", "")
                        chat_id = cfg.get("telegram_chat_id", "")
                        
                        if token and chat_id:
                            url = f"https://api.telegram.org/bot{token}/sendMessage"
                            msg_data = urllib.parse.urlencode({
                                'chat_id': chat_id, 
                                'text': "🔴 КРИТИЧЕСКАЯ УГРОЗА: Агент SecureCopyGuard был принудительно УБИТ через Диспетчер задач! Процесс авто-восстановления запущен."
                            }).encode('utf-8')
                            
                            req = urllib.request.Request(url, data=msg_data)
                            urllib.request.urlopen(req, timeout=5)
                            
                            with open(WATCHDOG_LOG, "a", encoding="utf-8") as f:
                                f.write(f"[{time.strftime('%X')}] Алерт успешно доставлен в Telegram!\n")
                        else:
                            with open(WATCHDOG_LOG, "a", encoding="utf-8") as f:
                                f.write(f"[{time.strftime('%X')}] ОШИБКА: Нет токена в config.json\n")
                    except Exception as req_e:
                        with open(WATCHDOG_LOG, "a", encoding="utf-8") as f:
                            f.write(f"[{time.strftime('%X')}] Ошибка API Telegram: {req_e}\n")
                    
                    # ─── 🦅 АКТИВНАЯ ЗАЩИТА: РЕЖИМ ФЕНИКСА ───
                    try:
                        exe_path = os.path.join(original_dir, "SecureCopyGuard.exe")
                        if os.path.exists(exe_path):
                            subprocess.Popen([exe_path], cwd=original_dir)
                        else:
                            # Фолбэк на случай теста прямо из редактора кода
                            subprocess.Popen([sys.executable, os.path.join(original_dir, "main.py")], cwd=original_dir)
                            
                        with open(WATCHDOG_LOG, "a", encoding="utf-8") as f:
                            f.write(f"[{time.strftime('%X')}] 🦅 ФЕНИКС: Программа успешно перезапущена!\n")
                    except Exception as revive_e:
                        with open(WATCHDOG_LOG, "a", encoding="utf-8") as f:
                            f.write(f"[{time.strftime('%X')}] Ошибка возрождения: {revive_e}\n")
                    # ────────────────────────────────────────────────
                break

        except Exception as e:
            with open(WATCHDOG_LOG, "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%X')}] Ошибка: {e}\n")
                
        time.sleep(2)
        
    sys.exit(0)
# ─────────────────────────────────────────────────────────────

import torch
import cv2
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from core.single_instance import ensure_single_instance, release_mutex
from core.first_run        import check_and_run_wizard
from config                import get_telegram_token, get_telegram_chat_id, get_config_value

def main():
    # Очищаем уникальный флаг, если он вдруг застрял
    current_pid = os.getpid()
    FLAG_FILE = os.path.join(tempfile.gettempdir(), f"dlp_legal_exit_{current_pid}.flag")
    
    if os.path.exists(FLAG_FILE):
        try: os.remove(FLAG_FILE)
        except: pass
        
    ghost_name = "win_system_host.exe" 
    ghost_path = os.path.join(BASE_DIR, ghost_name)
    
    try:
        if not os.path.exists(ghost_path):
            shutil.copy2(sys.executable, ghost_path)
            if sys.platform == "win32":
                ctypes.windll.kernel32.SetFileAttributesW(ghost_path, 2)
    except Exception:
        ghost_path = sys.executable 

    CREATE_FLAGS = 0x09000208 
    
    if getattr(sys, 'frozen', False):
        subprocess.Popen([ghost_path, "--watchdog", str(os.getpid()), BASE_DIR], creationflags=CREATE_FLAGS, cwd=BASE_DIR)
    else:
        subprocess.Popen([ghost_path, os.path.abspath(__file__), "--watchdog", str(os.getpid()), BASE_DIR], creationflags=CREATE_FLAGS, cwd=BASE_DIR)

    print("[DEBUG] Старт функции main()")
    
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    if not ensure_single_instance():
        sys.exit(0)

    if not check_and_run_wizard():
        release_mutex()
        sys.exit(0)

    from ui.main_window import MainWindow
    from core.telegram_bot import TelegramAdminBot

    window = MainWindow()

    saved_folder = get_config_value("protected_folder", "")
    if saved_folder:
        window.page_dash.restore_folder(saved_folder)

    window.show()

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
        except Exception:
            pass

    ret = app.exec_()
    release_mutex()
    sys.exit(ret)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        with open(crash_log_path, "a", encoding="utf-8") as f:
            f.write(f"\nКРИТИЧЕСКИЙ СБОЙ ПРИ ЗАПУСКЕ: {e}\n")