# Webhook setup script for Railway
import asyncio
import os

from aiogram import Bot
from app.config import get_settings
from app.run_bot import set_webhook, remove_webhook


async def main():
    print("[WEBHOOK] Starting setup...", flush=True)
    settings = get_settings()
    
    if not settings.bot_token:
        print("[WEBHOOK] ERROR: BOT_TOKEN not set", flush=True)
        return
    
    bot = Bot(token=settings.bot_token)
    
    # Railway автоматически задаёт RAILWAY_PUBLIC_DOMAIN
    webapp_url = os.getenv("RAILWAY_PUBLIC_DOMAIN")
    
    # Если нет - пробуем WEBAPP_URL
    if not webapp_url:
        webapp_url = os.getenv("WEBAPP_URL")
    
    # Если совсем ничего - localhost
    if not webapp_url:
        webapp_url = "http://localhost:8000"
    
    # Добавляем https если нет протокола
    if not webapp_url.startswith("http"):
        webapp_url = f"https://{webapp_url}"
    
    webhook_url = f"{webapp_url}/api/telegram/webhook"
    
    print(f"[WEBHOOK] URL: {webhook_url}", flush=True)
    
    try:
        await remove_webhook(bot)
        await set_webhook(bot, webhook_url)
        print("[WEBHOOK] SUCCESS", flush=True)
    except Exception as e:
        print(f"[WEBHOOK] ERROR: {e}", flush=True)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    if os.getenv("PORT"):
        asyncio.run(main())
    print("[WEBHOOK] Done", flush=True)
