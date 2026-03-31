@echo off
title SecureCopyGuard - Install

echo.
echo  SecureCopyGuard DLP - Installation
echo  ====================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found!
    echo  Download Python 3.11 from https://python.org
    echo  Make sure to check "Add to PATH"
    pause
    exit /b 1
)

python --version
echo  [OK] Python found

echo.
echo  [1/3] Updating pip...
python -m pip install --upgrade pip --quiet

echo  [2/3] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo  [ERROR] Failed to install dependencies
    pause
    exit /b 1
)
echo  [OK] Dependencies installed

echo  [3/3] Creating folders...
if not exist "_INTRUDERS"  mkdir "_INTRUDERS"
if not exist "_QUARANTINE" mkdir "_QUARANTINE"
if not exist "reports"     mkdir "reports"

if not exist ".env" (
    copy .env.example .env >nul
    echo  [!] Fill in .env with your Telegram token
)

echo.
echo  Done! Edit .env then run: python main.py
echo.
pause
