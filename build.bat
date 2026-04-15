@echo off
chcp 65001 >nul

title Сборка SecureCopyGuard в EXE

echo [1/2] Очистка старых файлов...
if exist "build" rmdir /s /q "build"
if exist "dist\SecureCopyGuard" rmdir /s /q "dist\SecureCopyGuard"

echo.
echo [2/2] Начинаю сборку проекта...
echo.

:: УБРАЛИ --icon="icon.ico", чтобы не было из-за нее ошибок
pyinstaller --noconfirm --windowed --add-data "yolov8n.pt;." --name "SecureCopyGuard" main.py

:: ─── УМНАЯ ПРОВЕРКА ОШИБОК ───
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo =======================================================
    echo [ОШИБКА] Сборка прервалась! Прокрути консоль вверх и посмотри, на что ругается красным цветом.
    echo =======================================================
    pause
    exit /b
)

echo.
echo =======================================================
echo СБОРКА УСПЕШНО ЗАВЕРШЕНА!
echo Твоя готовая программа лежит в папке: dist\SecureCopyGuard
echo =======================================================
pause