# SecureCopyGuard — DLP System v2.0

**Система защиты от утечки данных (Data Loss Prevention)**  
Дипломный проект | Специальность: Кибербезопасность

---

## Быстрый старт (установка на новом ПК)

### Требования
- Windows 10/11 (64-bit)
- Python 3.11 или 3.12 ([скачать](https://python.org)) — при установке отметить **"Add to PATH"**
- Веб-камера (для AI Vision и Webcam Trap)
- Telegram-бот (инструкция ниже)

### Установка

```
1. Скачать/скопировать папку проекта
2. Двойной клик на install.bat
3. Заполнить .env файл (токен Telegram)
4. Двойной клик на run.bat
```

### Настройка Telegram-бота

1. Написать [@BotFather](https://t.me/BotFather) → `/newbot` → получить токен
2. Написать своему боту любое сообщение
3. Открыть `https://api.telegram.org/bot<TOKEN>/getUpdates` — найти `"chat":{"id":...}`
4. Вставить в `.env`:
```
TELEGRAM_BOT_TOKEN=1234567890:ABCdef...
TELEGRAM_CHAT_ID=123456789
```

---

## Архитектура системы

```
┌─────────────────────────────────────────────────────┐
│                   SecureCopyGuard                   │
├──────────────┬──────────────┬───────────────────────┤
│   core/      │   ui/        │   db/                 │
│              │              │                       │
│ file_watcher │ DashboardPage│ SQLite (WAL-режим)    │
│ clipboard_   │ PoliciesPage │ Таблицы:              │
│  guard       │ LogsPage     │  - incidents          │
│ usb_monitor  │ SettingsPage │  - policies           │
│ vision_      │              │  - users/devices      │
│  protector   │ pdf_report   │                       │
│ spy_module   │              │                       │
│ autostart    │              │                       │
│ telegram_    │              │                       │
│  alerts      │              │                       │
└──────────────┴──────────────┴───────────────────────┘
         ↓ Qt Signals (межпоточное общение)
┌─────────────────────────────────────────────────────┐
│              Telegram Bot Admin                     │
│  Команды: Активировать / Деактивировать / Статус    │
│  Алерты: фото нарушителя + описание инцидента       │
└─────────────────────────────────────────────────────┘
```

## Модули защиты

| Модуль | Описание | Уровень угрозы |
|--------|----------|----------------|
| File Watcher | Мониторинг удаления/копирования файлов | High |
| Clipboard Guard | Перехват конф. данных в буфере обмена | High |
| USB Guard | Детекция подключения внешних носителей | High |
| AI Vision | YOLOv8 детекция смартфонов у экрана | Critical |
| Webcam Trap | Снимок нарушителя при инциденте | — |
| File Locker | Блокировка файлов на запись/удаление | — |

## Структура проекта

```
dlp_project/
├── main.py               # Точка входа
├── config.py             # Конфигурация путей
├── install.bat           # Установщик зависимостей
├── run.bat               # Запуск приложения
├── requirements.txt      # Зависимости Python
├── .env                  # Токены (не коммитить!)
├── .gitignore
├── core/
│   ├── file_watcher.py   # Watchdog мониторинг ФС
│   ├── clipboard_guard.py
│   ├── usb_monitor.py    # Win32 WM_DEVICECHANGE
│   ├── vision_protector.py  # YOLOv8 детекция
│   ├── spy_module.py     # Камера + сирена
│   ├── file_locker.py    # os.chmod блокировка
│   ├── autostart.py      # Реестр Windows
│   ├── telegram_bot.py   # Бот-администратор
│   └── telegram_alerts.py
├── db/
│   └── database.py       # SQLite singleton
├── ui/
│   ├── main_window.py
│   ├── pages.py
│   ├── widgets.py
│   ├── theme.py
│   └── pdf_report.py
└── _INTRUDERS/           # Кадры-доказательства (gitignore)
```
