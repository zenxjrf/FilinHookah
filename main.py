import asyncio
import logging
import os
import sys

from aiogram import Bot
from app.config import get_settings
from app.run_bot import run_polling, set_webhook, remove_webhook

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)


async def run_webhook() -> None:
    """Настройка webhook для Railway."""
    logger.info("Starting webhook setup...")
    settings = get_settings()
    
    if not settings.bot_token:
        logger.critical("BOT_TOKEN not set!")
        return
    
    bot = Bot(token=settings.bot_token)
    
    webapp_url = os.getenv("WEBAPP_URL", "http://localhost:8000")
    webhook_url = f"{webapp_url}/api/telegram/webhook"
    
    logger.info(f"Webhook URL: {webhook_url}")
    
    try:
        # Удаляем старый webhook
        await remove_webhook(bot)
        # Устанавливаем новый webhook
        await set_webhook(bot, webhook_url)
        logger.info(f"Webhook set successfully: {webhook_url}")
    except Exception as e:
        logger.error(f"ERROR setting webhook: {e}", exc_info=True)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    logger.info("Script started")
    # Проверяем, запущены ли через Railway (есть PORT)
    if os.getenv("PORT"):
        # Railway - используем webhook
        logger.info("Running in Railway mode (webhook)")
        asyncio.run(run_webhook())
    else:
        # Локальный запуск - polling
        logger.info("Running in local mode (polling)")
        asyncio.run(run_polling())
