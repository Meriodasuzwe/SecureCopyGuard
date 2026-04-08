# core/process_guard.py
"""
Защита процесса SecureCopyGuard от принудительного завершения.

Уровень 1 — DACL: устанавливаем дискреционный список доступа на наш процесс,
запрещающий PROCESS_TERMINATE для обычных пользователей.
В Диспетчере задач кнопка "Завершить задачу" выдаст "Отказано в доступе".

Уровень 2 — Ошибки игнорируются gracefully: если нет прав (уже admin),
просто логируем и продолжаем без защиты.
"""

import os
import ctypes
import ctypes.wintypes as wintypes

# ── Win32 константы ────────────────────────────────────────────────────
PROCESS_ALL_ACCESS        = 0x1F0FFF
PROCESS_TERMINATE         = 0x0001
PROCESS_VM_WRITE          = 0x0020

SE_KERNEL_OBJECT          = 6
DACL_SECURITY_INFORMATION = 0x00000004

ERROR_SUCCESS             = 0

# ACE типы
ACCESS_DENIED_ACE_TYPE    = 0x01
ACCESS_ALLOWED_ACE_TYPE   = 0x00

# ── ctypes структуры ───────────────────────────────────────────────────

class SID_IDENTIFIER_AUTHORITY(ctypes.Structure):
    _fields_ = [("Value", ctypes.c_byte * 6)]


class _SECURITY_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("nLength",              wintypes.DWORD),
        ("lpSecurityDescriptor", ctypes.c_void_p),
        ("bInheritHandle",       wintypes.BOOL),
    ]


def protect_process() -> bool:
    """
    Применяет DACL к текущему процессу:
      - Запрещает PROCESS_TERMINATE всем (Everyone SID).
      - Разрешает всё остальное (доступ к памяти, приостановка и т.д.).

    Возвращает True при успехе, False если не удалось (напр., уже Admin).
    """
    try:
        _apply_dacl()
        print("[GUARD] Защита процесса активирована.")
        return True
    except Exception as e:
        print(f"[GUARD] Не удалось установить DACL: {e}")
        return False


def _apply_dacl():
    advapi32 = ctypes.windll.advapi32
    kernel32  = ctypes.windll.kernel32

    # 1. Получаем handle текущего процесса
    h_process = kernel32.GetCurrentProcess()

    # 2. Создаём SID для "Everyone" (World SID: S-1-1-0)
    SIA_WORLD = SID_IDENTIFIER_AUTHORITY()
    SIA_WORLD.Value[5] = 1   # SECURITY_WORLD_SID_AUTHORITY

    everyone_sid = ctypes.c_void_p()
    if not advapi32.AllocateAndInitializeSid(
        ctypes.byref(SIA_WORLD),
        1,              # одна sub-authority
        0,              # SECURITY_WORLD_RID
        0, 0, 0, 0, 0, 0, 0,
        ctypes.byref(everyone_sid)
    ):
        raise ctypes.WinError()

    try:
        # 3. Создаём новый пустой DACL
        acl_size = 1024   # достаточно для двух ACE
        acl_buf  = ctypes.create_string_buffer(acl_size)
        if not advapi32.InitializeAcl(acl_buf, acl_size, 2):   # ACL_REVISION=2
            raise ctypes.WinError()

        # 4. Добавляем ACE: DENY PROCESS_TERMINATE для Everyone
        if not advapi32.AddAccessDeniedAce(
            acl_buf, 2, PROCESS_TERMINATE, everyone_sid
        ):
            raise ctypes.WinError()

        # 5. Создаём Security Descriptor и вставляем DACL
        sd_buf = ctypes.create_string_buffer(256)
        if not advapi32.InitializeSecurityDescriptor(sd_buf, 1):
            raise ctypes.WinError()

        if not advapi32.SetSecurityDescriptorDacl(
            sd_buf,
            True,     # bDaclPresent
            acl_buf,
            False     # bDaclDefaulted
        ):
            raise ctypes.WinError()

        # 6. Применяем Security Descriptor к процессу
        ret = advapi32.SetKernelObjectSecurity(
            h_process,
            DACL_SECURITY_INFORMATION,
            sd_buf
        )
        if not ret:
            raise ctypes.WinError()

    finally:
        advapi32.FreeSid(everyone_sid)
