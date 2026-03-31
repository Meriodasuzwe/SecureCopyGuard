@echo off
chcp 65001 >nul
title SecureCopyGuard DLP

:: Переходим в папку скрипта — важно для относительных путей
cd /d "%~dp0"

:: Быстрая проверка что зависимости есть
python -c "import PyQt5, cv2, ultralytics" >nul 2>&1
if errorlevel 1 (
    echo  [!] Зависимости не установлены. Запустите install.bat
    pause
    exit /b 1
)

:: Запуск
python main.py
if errorlevel 1 (
    echo.
    echo  [ОШИБКА] Программа завершилась с ошибкой.
    echo  Проверьте вывод выше.
    pause
)
