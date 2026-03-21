import sqlite3
import threading
from config import DB_PATH

class Database:
    _instance = None
    _lock = threading.RLock() # Блокировка для защиты от одновременной записи из разных потоков

    # Паттерн Singleton: гарантирует, что у нас только один объект БД на всю прогу
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(Database, cls).__new__(cls)
                cls._instance._init_db()
        return cls._instance

    def _get_connection(self):
        # check_same_thread=False - РАЗРЕШАЕТ запись из фоновых потоков (наших сенсоров)
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.execute('PRAGMA foreign_keys = ON;')
        conn.execute('PRAGMA journal_mode=WAL;') # Ускоряет работу БД в многопотоке
        return conn

    def _init_db(self):
        """Инициализация таблиц при первом запуске"""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Таблица пользователей
                cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                                  (id INTEGER PRIMARY KEY AUTOINCREMENT, full_name TEXT NOT NULL, department TEXT, position TEXT)''')
                # Таблица устройств
                cursor.execute('''CREATE TABLE IF NOT EXISTS devices 
                                  (id INTEGER PRIMARY KEY AUTOINCREMENT, hostname TEXT NOT NULL, ip_address TEXT, mac_address TEXT)''')
                # Таблица политик безопасности
                cursor.execute('''CREATE TABLE IF NOT EXISTS policies 
                                  (id INTEGER PRIMARY KEY AUTOINCREMENT, policy_name TEXT NOT NULL, threat_level TEXT NOT NULL, description TEXT)''')
                # Главная таблица инцидентов
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS incidents (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        user_id INTEGER,
                        device_id INTEGER,
                        policy_id INTEGER,
                        details TEXT,
                        FOREIGN KEY (user_id) REFERENCES users (id),
                        FOREIGN KEY (device_id) REFERENCES devices (id),
                        FOREIGN KEY (policy_id) REFERENCES policies (id)
                    )
                ''')

                # Заполняем базовые данные, если база пустая
                cursor.execute("SELECT COUNT(*) FROM users")
                if cursor.fetchone()[0] == 0:
                    import socket
                    hostname = socket.gethostname()
                    cursor.execute("INSERT INTO users (full_name, department, position) VALUES ('Локальный Администратор', 'ИТ-Безопасность', 'Офицер ИБ')")
                    cursor.execute("INSERT INTO devices (hostname, ip_address, mac_address) VALUES (?, '127.0.0.1', 'LOCAL')", (hostname,))
                    
                    policies = [
                        ('Критическая Угроза', 'High', 'Взлом, подмена файлов, несанкционированный USB'),
                        ('Утечка Данных (DLP)', 'Medium', 'Копирование в буфер обмена конфиденциальных данных'),
                        ('Системное Событие', 'Low', 'Включение/Отключение защиты системы')
                    ]
                    cursor.executemany("INSERT INTO policies (policy_name, threat_level, description) VALUES (?, ?, ?)", policies)
                conn.commit()

    def log_incident(self, policy_id, details, user_id=1, device_id=1):
        """Единый метод для записи любого лога (потокобезопасный)"""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO incidents (user_id, device_id, policy_id, details) VALUES (?, ?, ?, ?)",
                    (user_id, device_id, policy_id, details)
                )
                conn.commit()
                
    def get_recent_logs(self, limit=50):
        """Получить последние логи для отображения в интерфейсе"""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT i.timestamp, p.policy_name, p.threat_level, i.details 
                    FROM incidents i
                    JOIN policies p ON i.policy_id = p.id
                    ORDER BY i.timestamp DESC LIMIT ?
                """, (limit,))
                return cursor.fetchall()
    
    def get_incident_count(self):
        """Возвращает общее количество серьезных угроз (High и Medium)"""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM incidents WHERE policy_id IN (1, 2)")
                return cursor.fetchone()[0]