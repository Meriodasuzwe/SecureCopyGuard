@echo off
chcp 65001 >nul

title Сборка SecureCopyGuard в EXE

echo [1/2] Очистка старых файлов...
if exist "build" rmdir /s /q "build"
if exist "dist\SecureCopyGuard" rmdir /s /q "dist\SecureCopyGuard"

echo.
echo [2/2] Начинаю сборку проекта...
echo.

pyinstaller --noconfirm --windowed --add-data "yolov8n.pt;." --name "SecureCopyGuard" main.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo =======================================================
    echo [ОШИБКА] Сборка прервалась! Прокрути консоль вверх и посмотри, на что ругается красным цветом.
    echo =======================================================
    pause
    exit /b
)

:: ─── ФИКС: КОПИРУЕМ КОНФИГ И БАЗУ В ПАПКУ СО СБОРКОЙ ───
echo.
echo [3/3] Копирование конфигурации и базы данных...
if exist "config.json" copy "config.json" "dist\SecureCopyGuard\" >nul
if exist "dlp_logs.db" copy "dlp_logs.db" "dist\SecureCopyGuard\" >nul

echo.
echo =======================================================
echo СБОРКА УСПЕШНО ЗАВЕРШЕНА!
echo Твоя готовая программа лежит в папке: dist\SecureCopyGuard
echo =======================================================
pause