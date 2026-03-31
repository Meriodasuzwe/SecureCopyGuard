# db/database.py

import sqlite3
import threading
import socket
from config import DB_PATH


class Database:
    """
    Singleton с одним постоянным соединением на весь процесс.
    RLock защищает от гонок при параллельной записи из потоков воркеров.
    WAL-режим позволяет одновременно читать и писать без блокировок.
    """

    _instance: "Database | None" = None
    _lock = threading.RLock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                inst._conn = None
                inst._init_db()
                cls._instance = inst
        return cls._instance

    # ──────────────────────────────────────────────────────────────────
    #  Инициализация
    # ──────────────────────────────────────────────────────────────────

    def _get_conn(self) -> sqlite3.Connection:
        """Возвращает единственное соединение, создаёт при первом вызове."""
        if self._conn is None:
            self._conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            self._conn.execute("PRAGMA foreign_keys = ON;")
            self._conn.execute("PRAGMA journal_mode = WAL;")
            self._conn.row_factory = sqlite3.Row  # доступ по имени колонки
        return self._conn

    def _init_db(self):
        with self._lock:
            conn = self._get_conn()
            cur  = conn.cursor()

            cur.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name  TEXT NOT NULL,
                    department TEXT,
                    position   TEXT
                );

                CREATE TABLE IF NOT EXISTS devices (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    hostname    TEXT NOT NULL,
                    ip_address  TEXT,
                    mac_address TEXT
                );

                CREATE TABLE IF NOT EXISTS policies (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    policy_name TEXT NOT NULL,
                    threat_level TEXT NOT NULL,   -- 'High' | 'Medium' | 'Low'
                    description TEXT
                );

                CREATE TABLE IF NOT EXISTS incidents (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    user_id   INTEGER REFERENCES users(id),
                    device_id INTEGER REFERENCES devices(id),
                    policy_id INTEGER REFERENCES policies(id),
                    details   TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_incidents_ts
                    ON incidents(timestamp DESC);
            """)

            # Заполняем справочники при первом запуске
            cur.execute("SELECT COUNT(*) FROM users")
            if cur.fetchone()[0] == 0:
                cur.execute(
                    "INSERT INTO users (full_name, department, position) "
                    "VALUES ('Локальный Администратор', 'ИТ-Безопасность', 'Офицер ИБ')"
                )
                cur.execute(
                    "INSERT INTO devices (hostname, ip_address, mac_address) VALUES (?, '127.0.0.1', 'LOCAL')",
                    (socket.gethostname(),)
                )
                cur.executemany(
                    "INSERT INTO policies (policy_name, threat_level, description) VALUES (?, ?, ?)",
                    [
                        # id=1 — критическая угроза
                        ("Критическая Угроза",  "High",
                         "Удаление файла, несанкционированный USB, детекция телефона"),
                        # id=2 — утечка данных
                        ("Утечка Данных (DLP)", "High",
                         "Буфер обмена: перехват конфиденциальных данных"),
                        # id=3 — системное событие
                        ("Системное Событие",   "Low",
                         "Активация/деактивация защиты, изменение файла"),
                    ]
                )

            conn.commit()

    # ──────────────────────────────────────────────────────────────────
    #  Запись
    # ──────────────────────────────────────────────────────────────────

    def log_incident(self, policy_id: int, details: str,
                     user_id: int = 1, device_id: int = 1) -> None:
        """
        Потокобезопасная запись инцидента.

        policy_id:
            1 = Критическая угроза  (High)   — удаление файла, USB, телефон
            2 = Утечка данных       (High)   — буфер обмена
            3 = Системное событие   (Low)    — вкл/выкл защиты, изменение файла
        """
        with self._lock:
            self._get_conn().execute(
                "INSERT INTO incidents (user_id, device_id, policy_id, details) "
                "VALUES (?, ?, ?, ?)",
                (user_id, device_id, policy_id, details)
            )
            self._get_conn().commit()

    # ──────────────────────────────────────────────────────────────────
    #  Чтение
    # ──────────────────────────────────────────────────────────────────

    def get_recent_logs(self, limit: int = 50) -> list[tuple]:
        """Последние N инцидентов для таблицы журнала."""
        with self._lock:
            cur = self._get_conn().execute(
                """
                SELECT i.timestamp,
                       p.policy_name,
                       p.threat_level,
                       i.details
                FROM   incidents i
                JOIN   policies  p ON i.policy_id = p.id
                ORDER  BY i.timestamp DESC
                LIMIT  ?
                """,
                (limit,)
            )
            return cur.fetchall()

    def get_incident_count(self) -> int:
        """Количество серьёзных инцидентов (policy_id 1 и 2 = High)."""
        with self._lock:
            row = self._get_conn().execute(
                "SELECT COUNT(*) FROM incidents WHERE policy_id IN (1, 2)"
            ).fetchone()
            return row[0] if row else 0

    def get_stats_by_module(self) -> list[tuple]:
        """
        Сводка по модулям — используется для отчёта.
        Возвращает [(policy_name, threat_level, count), ...]
        """
        with self._lock:
            cur = self._get_conn().execute(
                """
                SELECT p.policy_name,
                       p.threat_level,
                       COUNT(i.id) AS cnt
                FROM   incidents i
                JOIN   policies  p ON i.policy_id = p.id
                GROUP  BY p.id
                ORDER  BY cnt DESC
                """
            )
            return cur.fetchall()

    def close(self):
        """Явное закрытие — вызывать при завершении приложения."""
        with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None