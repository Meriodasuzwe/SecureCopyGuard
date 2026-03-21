# core/usb_monitor.py

import time
import threading
import psutil
from db.database import Database
from core.spy_module import SpyModule
from core.telegram_alerts import send_telegram_alert

class USBMonitor(threading.Thread):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.daemon = True # Поток завершится автоматически при закрытии программы
        self.is_running = False
        # Сохраняем текущее состояние дисков, чтобы не спамить при запуске
        self._last_drives = self._get_removable_drives()

    def _get_removable_drives(self):
        """Сканирует систему на наличие съемных носителей (USB флешки)"""
        drives = []
        try:
            for part in psutil.disk_partitions():
                # 'removable' - стандартный признак флешки в Windows
                if 'removable' in part.opts or part.fstype == '':
                    drives.append(part.device)
        except Exception as e:
            print(f"[USB] Ошибка сканирования дисков: {e}")
        return set(drives)

    def run(self):
        """Основной цикл мониторинга"""
        self.is_running = True
        print("[USB] Мониторинг портов активирован...")
        
        while self.is_running:
            current_drives = self._get_removable_drives()
            
            # Вычисляем разницу: какие диски появились
            new_drives = current_drives - self._last_drives
            
            if new_drives:
                for drive in new_drives:
                    msg = f"ОБНАРУЖЕН СЪЕМНЫЙ НОСИТЕЛЬ: {drive}"
                    
                    # 1. Запись в локальную БД
                    self.db.log_incident(1, msg) # ID 1 - Критическая угроза
                    
                    # 2. Мгновенный алерт в Telegram
                    send_telegram_alert(msg)
                    
                    # 3. Аудио-оповещение (Сирена)
                    SpyModule.play_siren()
                    
                    print(f"[USB ALERT] {msg}")
            
            # Обновляем состояние для следующей итерации
            self._last_drives = current_drives
            
            # Спим 2 секунды, чтобы не грузить процессор
            time.sleep(2)

    def stop(self):
        """Безопасная остановка потока"""
        self.is_running = False
        print("[USB] Мониторинг остановлен.")