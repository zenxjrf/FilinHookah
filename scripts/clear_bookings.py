import asyncio
from app.db.base import engine
from sqlalchemy import text

async def main():
    async with engine.begin() as conn:
        result = await conn.execute(text('DELETE FROM bookings'))
        print(f"Deleted {result.rowcount} bookings")

asyncio.run(main())
