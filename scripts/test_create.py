import asyncio
from app.db.base import session_factory
from app.db import crud

async def test():
    async with session_factory() as session:
        client = await crud.get_or_create_client(
            session,
            telegram_id=1698158035,
            username=None,
            full_name=None,
            phone="+79991234599",
        )
        print("Client ID:", client.id)
        
        from datetime import datetime
        booking = await crud.create_booking(
            session=session,
            client_id=client.id,
            booking_at=datetime(2026, 2, 25, 22, 0),
            table_no=6,
            guests=2,
            comment="Test",
        )
        print("Booking ID:", booking.id)
        print("Booking created_at:", booking.created_at)

asyncio.run(test())
