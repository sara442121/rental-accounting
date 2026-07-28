import shutil
import os
from datetime import datetime
import threading
import time

DB_NAME = 'rental_accounting.db'
BACKUP_DIR = 'backups'

if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)

def create_local_backup():
    """ایجاد یک کپی پشتیبان محلی با تاریخ و زمان دقیق"""
    if os.path.exists(DB_NAME):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(BACKUP_DIR, f"backup_{timestamp}.db")
        shutil.copy2(DB_NAME, backup_path)
        print(f"پشتیبان‌گیری محلی انجام شد: {backup_path}")
        return backup_path
    return None

def auto_backup_worker(interval_hours=24):
    """تابع در پس‌زمینه برای بک‌آپ‌گیری دوره‌ای"""
    while True:
        create_local_backup()
        # خوابیدن به مدت مشخص شده
        time.sleep(interval_hours * 3600)

def start_auto_backup(interval_hours=24):
    """شروع سیستم پشتیبان‌گیری خودکار در یک ترد جداگانه"""
    t = threading.Thread(target=auto_backup_worker, args=(interval_hours,), daemon=True)
    t.start()
    print("سیستم پشتیبان‌گیری خودکار فعال شد.")

if __name__ == "__main__":
    create_local_backup()
