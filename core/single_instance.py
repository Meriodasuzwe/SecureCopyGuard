# core/single_instance.py
"""
Гарантирует что в системе запущен только один экземпляр SecureCopyGuard.
Использует именованный Windows Mutex — надёжнее файлов-блокировок.
"""

import ctypes
import ctypes.wintypes as wintypes

_MUTEX_NAME  = "Global\\SecureCopyGuard_SingleInstance_Mutex"
_mutex_handle = None


def ensure_single_instance() -> bool:
    """
    Пытается создать глобальный мьютекс.

    Возвращает True  — мы первый экземпляр, продолжаем запуск.
    Возвращает False — уже запущен, нужно завершиться.
    """
    global _mutex_handle

    kernel32 = ctypes.windll.kernel32

    _mutex_handle = kernel32.CreateMutexW(
        None,       # атрибуты безопасности по умолчанию
        True,       # мы сразу берём владение
        _MUTEX_NAME
    )

    last_error = kernel32.GetLastError()

    if last_error == 183:   # ERROR_ALREADY_EXISTS
        # Мьютекс уже существует — другой экземпляр уже работает
        if _mutex_handle:
            kernel32.CloseHandle(_mutex_handle)
            _mutex_handle = None
        return False

    return True


def release_mutex():
    """Освобождает мьютекс при завершении приложения."""
    global _mutex_handle
    if _mutex_handle:
        ctypes.windll.kernel32.ReleaseMutex(_mutex_handle)
        ctypes.windll.kernel32.CloseHandle(_mutex_handle)
        _mutex_handle = None
