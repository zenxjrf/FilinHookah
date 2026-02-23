import asyncio
from app.db.base import engine
from sqlalchemy import text

async def main():
    async with engine.begin() as conn:
        try:
            await conn.execute(text('ALTER TABLE bookings ADD COLUMN is_staff_booking BOOLEAN DEFAULT 0'))
            print("Column is_staff_booking added to bookings")
        except Exception as e:
            print(f"Column might exist: {e}")
        
        try:
            await conn.execute(text('ALTER TABLE clients ADD COLUMN notes TEXT'))
            print("Column notes added to clients")
        except Exception as e:
            print(f"Column might exist: {e}")

asyncio.run(main())
