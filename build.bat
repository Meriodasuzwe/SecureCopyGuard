@echo off
:: Включаем поддержку кодировки UTF-8 в консоли (чтобы не было кракозябр)
chcp 65001 >nul

title Сборка SecureCopyGuard в EXE

echo [1/2] Установка компилятора PyInstaller...
pip install pyinstaller

echo.
echo [2/2] Начинаю сборку проекта (это займет 2-3 минуты)...
echo.

:: Удаляем старые папки сборки, если они остались от прошлых попыток
if exist "build" rmdir /s /q "build"
if exist "dist\SecureCopyGuard" rmdir /s /q "dist\SecureCopyGuard"

:: Сама команда компиляции:
:: --noconfirm (перезаписывать всё без вопросов)
:: --windowed (запускать без черного окна консоли, только красивый интерфейс)
:: --name (имя финальной программы)
pyinstaller --noconfirm --windowed --name "SecureCopyGuard" main.py

echo.
echo =======================================================
echo СБОРКА УСПЕШНО ЗАВЕРШЕНА!
echo Твоя готовая программа лежит в папке: dist\SecureCopyGuard
echo =======================================================
pause