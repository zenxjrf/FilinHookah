import asyncio
import httpx
from datetime import datetime, timedelta

async def main():
    # Создаем тестовую бронь
    async with httpx.AsyncClient() as client:
        payload = {
            "telegram_id": 1698158035,
            "full_name": "Test User",
            "username": "testuser",
            "phone": "+79991234567",
            "date_time": (datetime.now() + timedelta(days=1)).isoformat(),
            "table_no": 3,
            "guests": 4,
            "comment": "Тестовая бронь"
        }
        
        response = await client.post(
            "http://localhost:8000/api/bookings",
            json=payload
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"Booking created: ID={result['id']}, status={result['status']}")
        else:
            print(f"Error: {response.status_code} - {response.text}")

asyncio.run(main())
