import asyncio
from app.db.base import session_factory
from app.db import crud
from sqlalchemy import select
from app.db.models import Booking

async def test():
    async with session_factory() as session:
        stmt = select(Booking).where(Booking.table_no == 2).order_by(Booking.booking_at)
        bookings = (await session.scalars(stmt)).all()
        for b in bookings:
            print(f"#{b.id}: {b.booking_at} - {b.booking_at}, status={b.status}")

asyncio.run(test())
