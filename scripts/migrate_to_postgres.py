#!/usr/bin/env python3
"""
Скрипт миграции с SQLite на PostgreSQL.
Переносит все данные из старой БД в новую.
"""

import asyncio
import sys
from pathlib import Path

from sqlalchemy import text, select, insert
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Пути к БД
SQLITE_PATH = "sqlite+aiosqlite:///./filin.db"
POSTGRES_URL = "postgresql+asyncpg://user:password@localhost:5432/filin"


async def migrate():
    print("🚀 Миграция данных с SQLite на PostgreSQL")
    print("=" * 50)
    
    # Создаем движки
    sqlite_engine = create_async_engine(SQLITE_PATH, echo=False)
    postgres_engine = create_async_engine(POSTGRES_URL, echo=False)
    
    sqlite_session = async_sessionmaker(sqlite_engine, class_=AsyncSession)
    postgres_session = async_sessionmaker(postgres_engine, class_=AsyncSession)
    
    tables = [
        ("clients", ["id", "telegram_id", "username", "full_name", "phone_hash", "visits", "consent_accepted", "notes", "created_at"]),
        ("bookings", ["id", "client_id", "booking_at", "duration_minutes", "guests", "table_no", "comment", "status", "reminder_sent", "reminder_1h_sent", "is_staff_booking", "created_at"]),
        ("promotions", ["id", "title", "description", "image_url", "is_active", "created_at"]),
        ("reviews", ["id", "client_id", "booking_id", "rating", "text", "created_at"]),
        ("venue_settings", ["id", "schedule_text", "contacts_text", "updated_at"]),
    ]
    
    async with sqlite_engine.begin() as sqlite_conn:
        for table, columns in tables:
            print(f"\n📊 Миграция таблицы: {table}")
            
            # Получаем данные из SQLite
            columns_str = ", ".join(columns)
            result = await sqlite_conn.execute(text(f"SELECT {columns_str} FROM {table}"))
            rows = result.fetchall()
            
            if not rows:
                print(f"   ⚠️ Таблица {table} пуста")
                continue
            
            print(f"   Найдено {len(rows)} записей")
            
            # Вставляем в PostgreSQL
            async with postgres_engine.begin() as postgres_conn:
                for row in rows:
                    try:
                        data = dict(zip(columns, row))
                        # Пропускаем id для autoincrement
                        if 'id' in data:
                            # Для PostgreSQL нужно явно указать id
                            await postgres_conn.execute(
                                text(f"INSERT INTO {table} ({columns_str}) VALUES ({', '.join([f':{col}' for col in columns])})"),
                                data
                            )
                        print(f"   ✅ Перенесено")
                    except Exception as e:
                        print(f"   ❌ Ошибка: {e}")
    
    await sqlite_engine.dispose()
    await postgres_engine.dispose()
    
    print("\n" + "=" * 50)
    print("✅ Миграция завершена!")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        POSTGRES_URL = sys.argv[1]
        print(f"Используем PostgreSQL: {POSTGRES_URL}")
    
    try:
        asyncio.run(migrate())
    except Exception as e:
        print(f"❌ Ошибка миграции: {e}")
        sys.exit(1)
