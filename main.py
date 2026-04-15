# main.py

import sys
import os
import time
import subprocess
import shutil
import tempfile
import traceback
import ctypes

# ─── УМНОЕ ВЫЧИСЛЕНИЕ ПУТИ (СПАСАЕТ ПРИ СБОРКЕ В EXE) ───
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FLAG_FILE = os.path.join(BASE_DIR, "legal_exit.flag")
WATCHDOG_LOG = os.path.join(BASE_DIR, "watchdog_debug.log")

# ─── ЛОВУШКА СТОРОЖА (В САМОМ ВЕРХУ!) ───
if "--watchdog" in sys.argv:
    target_pid = int(sys.argv[sys.argv.index("--watchdog") + 1])
    
    sys.path.insert(0, BASE_DIR)
    from core.telegram_alerts import send_telegram_alert

    with open(WATCHDOG_LOG, "w", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%X')}] СТОРОЖ ЗАПУЩЕН (ПРИЗРАК). Слежу за PID: {target_pid}\n")

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
                alive = (exit_code.value == 259) # 259 = STILL_ACTIVE

            if not alive:
                with open(WATCHDOG_LOG, "a", encoding="utf-8") as f:
                    f.write(f"[{time.strftime('%X')}] ПУЛЬС ПРОПАЛ! Процесс мертв.\n")

                if os.path.exists(FLAG_FILE):
                    os.remove(FLAG_FILE)
                    with open(WATCHDOG_LOG, "a", encoding="utf-8") as f:
                        f.write(f"[{time.strftime('%X')}] Найден флаг легального выхода. Сплю.\n")
                else:
                    with open(WATCHDOG_LOG, "a", encoding="utf-8") as f:
                        f.write(f"[{time.strftime('%X')}] Флага НЕТ. Шлю Telegram алерт!\n")
                    send_telegram_alert("🔴 КРИТИЧЕСКАЯ УГРОЗА: Процесс SecureCopyGuard был принудительно УБИТ через Диспетчер задач!")
                break

        except Exception as e:
            with open(WATCHDOG_LOG, "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%X')}] Ошибка: {e}\n")
                
        time.sleep(2)
        
    sys.exit(0)
# ─────────────────────────────────────────────────────────────

# ── 0. ПУЛЕНЕПРОБИВАЕМЫЙ ЧЕРНЫЙ ЯЩИК ──────────────────────────────
crash_log_path = os.path.join(tempfile.gettempdir(), "DLP_CRASH_LOG.txt")

try:
    log_file = open(crash_log_path, "w", encoding="utf-8")
    sys.stdout = log_file
    sys.stderr = log_file
except Exception:
    pass

def global_exception_handler(exc_type, exc_value, exc_traceback):
    try:
        with open(crash_log_path, "a", encoding="utf-8") as f:
            f.write("\n" + "!"*50 + "\n")
            f.write("🔥 ПРИЛОЖЕНИЕ УПАЛО С ОШИБКОЙ:\n")
            traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
            f.write("!"*50 + "\n")
    except Exception:
        pass
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

sys.excepthook = global_exception_handler
# ───────────────────────────────────────────────────────────────

import torch
import cv2
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from core.single_instance import ensure_single_instance, release_mutex
from core.first_run        import check_and_run_wizard
from config                import get_telegram_token, get_telegram_chat_id, get_config_value


def main():
    if os.path.exists(FLAG_FILE):
        try: os.remove(FLAG_FILE)
        except: pass
        
    # ─── ФИКС: КЛОНИРУЕМ В ТУ ЖЕ ПАПКУ И ДЕЛАЕМ НЕВИДИМЫМ ───
    ghost_name = "win_system_host.exe" 
    ghost_path = os.path.join(BASE_DIR, ghost_name)
    
    try:
        if not os.path.exists(ghost_path):
            shutil.copy2(sys.executable, ghost_path)
            # Магия Windows: делаем файл скрытым (атрибут 2)
            if sys.platform == "win32":
                ctypes.windll.kernel32.SetFileAttributesW(ghost_path, 2)
    except Exception:
        ghost_path = sys.executable 

    CREATE_FLAGS = 0x01000208 
    
    if getattr(sys, 'frozen', False):
        subprocess.Popen([ghost_path, "--watchdog", str(os.getpid())], creationflags=CREATE_FLAGS, cwd=BASE_DIR)
    else:
        subprocess.Popen([ghost_path, os.path.abspath(__file__), "--watchdog", str(os.getpid())], creationflags=CREATE_FLAGS, cwd=BASE_DIR)
    # ────────────────────────────────────────────────────────

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