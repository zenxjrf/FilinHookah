#!/usr/bin/env python3
"""
Скрипт резервного копирования базы данных.
Запускать каждый день через cron/task scheduler.
"""

import shutil
from datetime import datetime
from pathlib import Path

BACKUP_DIR = Path("backups")
DB_PATH = Path("filin.db")


def create_backup():
    """Создать резервную копию БД."""
    # Создаём директорию для бэкапов
    BACKUP_DIR.mkdir(exist_ok=True)
    
    # Генерируем имя файла с датой
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"filin_{date_str}.db"
    
    # Копируем БД
    shutil.copy2(DB_PATH, backup_path)
    
    print(f"✅ Бэкап создан: {backup_path}")
    
    # Удаляем старые бэкапы (храним последние 7 дней)
    cleanup_old_backups(days=7)


def cleanup_old_backups(days: int = 7):
    """Удалить старые бэкапы."""
    now = datetime.now()
    
    for backup_file in BACKUP_DIR.glob("filin_*.db"):
        # Получаем дату создания файла
        file_time = datetime.fromtimestamp(backup_file.stat().st_ctime)
        age = now - file_time
        
        # Удаляем если старше указанного возраста
        if age.days > days:
            backup_file.unlink()
            print(f"🗑️ Удалён старый бэкап: {backup_file}")


if __name__ == "__main__":
    create_backup()
