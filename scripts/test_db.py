import asyncio
from app.db.base import engine
from sqlalchemy import text

async def test():
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text('SELECT 1'))
            print("DB OK:", result.scalar())
    except Exception as e:
        print("DB Error:", e)

asyncio.run(test())
