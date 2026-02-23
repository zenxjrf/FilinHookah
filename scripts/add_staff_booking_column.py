import asyncio
from app.db.base import engine
from sqlalchemy import text

async def main():
    async with engine.begin() as conn:
        # Проверяем, существует ли колонка
        result = await conn.execute(text(
            "PRAGMA table_info(bookings)"
        ))
        columns = [row[1] for row in result.fetchall()]
        
        if "is_staff_booking" not in columns:
            await conn.execute(text(
                "ALTER TABLE bookings ADD COLUMN is_staff_booking BOOLEAN DEFAULT 0"
            ))
            print("Column is_staff_booking added")
        else:
            print("Column is_staff_booking already exists")

asyncio.run(main())
