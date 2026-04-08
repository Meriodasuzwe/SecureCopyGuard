# core/autostart.py

import sys
import winreg
from pathlib import Path

_REG_KEY  = r"Software\Microsoft\Windows\CurrentVersion\Run"
_APP_NAME = "SecureCopyGuard"


def _get_launch_command() -> str:
    """
    Возвращает команду запуска приложения.
    - Если собрано PyInstaller'ом — путь к EXE.
    - Если запущено как .py — pythonw.exe + путь к main.py
      (pythonw — без консольного окна).
    """
    if getattr(sys, "frozen", False):
        # Режим PyInstaller: sys.executable == наш EXE
        return f'"{sys.executable}"'
    else:
        # Режим разработки: ищем pythonw рядом с python
        python_exe = Path(sys.executable)
        pythonw    = python_exe.parent / "pythonw.exe"
        if not pythonw.exists():
            pythonw = python_exe   # fallback — обычный python (покажет консоль)
        main_py = (Path(__file__).resolve().parent.parent / "main.py")
        return f'"{pythonw}" "{main_py}"'


def enable_autostart() -> bool:
    """
    Добавляет запись в реестр HKCU\\...\\Run.
    Возвращает True при успехе.
    """
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _REG_KEY,
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, _APP_NAME, 0, winreg.REG_SZ, _get_launch_command())
        winreg.CloseKey(key)
        print(f"[AUTOSTART] Автозапуск включён: {_get_launch_command()}")
        return True
    except Exception as e:
        print(f"[AUTOSTART] Ошибка включения автозапуска: {e}")
        return False


def disable_autostart() -> bool:
    """
    Удаляет запись из реестра.
    Возвращает True при успехе (или если записи не было).
    """
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _REG_KEY,
            0, winreg.KEY_SET_VALUE
        )
        winreg.DeleteValue(key, _APP_NAME)
        winreg.CloseKey(key)
        print("[AUTOSTART] Автозапуск отключён.")
        return True
    except FileNotFoundError:
        return True   # записи не было — всё равно успех
    except Exception as e:
        print(f"[AUTOSTART] Ошибка отключения автозапуска: {e}")
        return False


def is_enabled() -> bool:
    """Проверяет, есть ли запись автозапуска в реестре."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _REG_KEY,
            0, winreg.KEY_READ
        )
        winreg.QueryValueEx(key, _APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False
