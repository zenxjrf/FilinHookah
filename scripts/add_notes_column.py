import asyncio
from app.db.base import engine
from sqlalchemy import text

async def main():
    try:
        async with engine.begin() as conn:
            await conn.execute(text('ALTER TABLE clients ADD COLUMN notes TEXT'))
        print("Column notes added")
    except Exception as e:
        print(f"Column might exist: {e}")

asyncio.run(main())
