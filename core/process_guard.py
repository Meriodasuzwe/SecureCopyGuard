# core/process_guard.py

import os
import sys
import subprocess
import tempfile

LOCK_FILE = os.path.join(tempfile.gettempdir(), "dlp_watchdog.lock")
VBS_FILE = os.path.join(tempfile.gettempdir(), "dlp_watchdog.vbs")

def protect_process():
    """
    Создает системный VBS-скрипт (wscript.exe), который абсолютно независим 
    от дерева процессов Python. Его Диспетчер задач не убьет вместе с прогой.
    """
    # 1. Создаем файл-маркер "Я ЖИВ"
    with open(LOCK_FILE, "w") as f:
        f.write("active")

    my_pid = os.getpid()
    
    # Формируем команду для перезапуска (с учетом пробелов в путях)
    if getattr(sys, 'frozen', False):
        run_cmd = f'Chr(34) & "{sys.executable}" & Chr(34)'
    else:
        run_cmd = f'Chr(34) & "{sys.executable}" & Chr(34) & " " & Chr(34) & "{os.path.abspath(sys.argv[0])}" & Chr(34)'

    # 2. Пишем логику неубиваемого охранника на VBScript
    vbs_code = f"""
    Set objWMIService = GetObject("winmgmts:\\\\.\\root\\cimv2")
    Set objShell = CreateObject("WScript.Shell")
    Set fso = CreateObject("Scripting.FileSystemObject")

    Do
        WScript.Sleep 1000
        
        ' Если админ легально закрыл прогу (ввел PIN), она сама удалит этот файл.
        ' В таком случае охранник просто тихо умирает.
        If Not fso.FileExists("{LOCK_FILE}") Then
            WScript.Quit
        End If
        
        ' Проверяем, жив ли процесс
        Set colProcesses = objWMIService.ExecQuery("Select * From Win32_Process Where ProcessID = {my_pid}")
        If colProcesses.Count = 0 Then
            ' Процесса нет, а файл-маркер ЕСТЬ = юзер убил прогу через Диспетчер!
            ' ВОСКРЕШАЕМ:
            objShell.Run {run_cmd}, 1, False
            WScript.Quit
        End If
    Loop
    """
    
    # 3. Сохраняем VBS и запускаем через скрытый системный wscript.exe
    with open(VBS_FILE, "w", encoding="utf-8") as f:
        f.write(vbs_code)
        
    subprocess.Popen(["wscript.exe", VBS_FILE], creationflags=0x08000000)

def unprotect_process():
    """Снимает бессмертие. Вызывать ТОЛЬКО при вводе правильного PIN-кода."""
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)