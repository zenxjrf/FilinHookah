#!/usr/bin/env python3
"""
Настройка автоматического резервного копирования.
Запускается один раз при деплое.
"""

import platform
import subprocess
from pathlib import Path


def setup_backup_scheduler():
    """Настроить автоматический бэкап через планировщик задач."""
    
    script_path = Path(__file__).parent / "backup_db.py"
    
    if platform.system() == "Windows":
        # Для Windows - Task Scheduler
        task_name = "FilinDBBackup"
        command = f"schtasks /Create /TN {task_name} /TR \"python {script_path}\" /SC DAILY /ST 03:00 /RL HIGHEST /F"
        
        try:
            subprocess.run(command, shell=True, check=True)
            print(f"✅ Задача '{task_name}' создана")
            print("📅 Бэкап будет выполняться каждый день в 03:00")
        except subprocess.CalledProcessError as e:
            print(f"❌ Ошибка создания задачи: {e}")
            print("📝 Создайте бэкап вручную через cron или Task Scheduler")
    
    else:
        # Для Linux/Mac - cron
        cron_job = f"0 3 * * * python3 {script_path}"
        print(f"✅ Добавьте в cron следующую строку:")
        print(f"   {cron_job}")
        print("\nИли выполните: crontab -e и добавьте эту строку")


if __name__ == "__main__":
    setup_backup_scheduler()
