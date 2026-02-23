import asyncio
import os

from aiogram import Bot
from app.config import get_settings
from app.run_bot import run_polling, set_webhook, remove_webhook


async def run_webhook() -> None:
    """Настройка webhook для Railway."""
    settings = get_settings()
    bot = Bot(token=settings.bot_token)
    
    webapp_url = os.getenv("WEBAPP_URL", "http://localhost:8000")
    webhook_url = f"{webapp_url}/api/telegram/webhook"
    
    try:
        # Удаляем старый webhook
        await remove_webhook(bot)
        # Устанавливаем новый webhook
        await set_webhook(bot, webhook_url)
        print(f✓ Webhook установлен: {webhook_url}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    # Проверяем, запущены ли через Railway (есть PORT)
    if os.getenv("PORT"):
        # Railway - используем webhook
        asyncio.run(run_webhook())
    else:
        # Локальный запуск - polling
        asyncio.run(run_polling())
