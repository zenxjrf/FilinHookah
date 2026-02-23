import asyncio
import os
import sys

from aiogram import Bot
from app.config import get_settings
from app.run_bot import run_polling, set_webhook, remove_webhook


async def run_webhook() -> None:
    """Настройка webhook для Railway."""
    print(">>> [MAIN] Starting webhook setup...", flush=True)
    settings = get_settings()
    
    if not settings.bot_token:
        print(">>> [MAIN] ERROR: BOT_TOKEN not set!", flush=True)
        return
    
    bot = Bot(token=settings.bot_token)
    
    webapp_url = os.getenv("WEBAPP_URL", "http://localhost:8000")
    webhook_url = f"{webapp_url}/api/telegram/webhook"
    
    print(f">>> [MAIN] Webhook URL: {webhook_url}", flush=True)
    
    try:
        # Удаляем старый webhook
        await remove_webhook(bot)
        # Устанавливаем новый webhook
        await set_webhook(bot, webhook_url)
        print(f">>> [MAIN] ✓ Webhook установлен: {webhook_url}", flush=True)
    except Exception as e:
        print(f">>> [MAIN] ERROR setting webhook: {e}", flush=True)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    print(">>> [MAIN] Script started", flush=True)
    # Проверяем, запущены ли через Railway (есть PORT)
    if os.getenv("PORT"):
        # Railway - используем webhook
        print(">>> [MAIN] Running in Railway mode (webhook)", flush=True)
        asyncio.run(run_webhook())
    else:
        # Локальный запуск - polling
        print(">>> [MAIN] Running in local mode (polling)", flush=True)
        asyncio.run(run_polling())
