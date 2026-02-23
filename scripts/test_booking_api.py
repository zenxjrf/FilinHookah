import asyncio
import httpx

async def test():
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://localhost:8000/api/bookings",
                json={
                    "telegram_id": 1698158035,
                    "phone": "+79991234599",
                    "date_time": "2026-02-25T23:59:00",
                    "table_no": 5,
                    "guests": 2
                }
            )
            print("Status:", response.status_code)
            print("Response:", response.json())
        except Exception as e:
            print("Error:", e)

asyncio.run(test())
