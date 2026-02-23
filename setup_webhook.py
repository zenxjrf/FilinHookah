# Webhook setup script for Railway
import asyncio
import os
import time

from aiogram import Bot
from app.config import get_settings
from app.run_bot import set_webhook, remove_webhook


async def main():
    print("[WEBHOOK] Starting setup...", flush=True)
    settings = get_settings()
    
    if not settings.bot_token:
        print("[WEBHOOK] ERROR: BOT_TOKEN not set", flush=True)
        return
    
    # Ждём пока Web App будет готов (Railway уже запустил его)
    print("[WEBHOOK] Waiting for Web App to be ready...", flush=True)
    await asyncio.sleep(3)
    
    bot = Bot(token=settings.bot_token)
    
    # Render автоматически задаёт RENDER_EXTERNAL_URL
    webapp_url = os.getenv("RENDER_EXTERNAL_URL")
    
    # Если нет - пробуем RAILWAY_PUBLIC_DOMAIN
    if not webapp_url:
        webapp_url = os.getenv("RAILWAY_PUBLIC_DOMAIN")
    
    # Если нет - пробуем WEBAPP_URL
    if not webapp_url:
        webapp_url = os.getenv("WEBAPP_URL")
    
    # Если совсем ничего - localhost
    if not webapp_url:
        webapp_url = "http://localhost:8000"
    
    # Очищаем от пробелов и переносов
    webapp_url = webapp_url.strip()
    
    # Добавляем https если нет протокола
    if not webapp_url.startswith("http"):
        webapp_url = f"https://{webapp_url}"
    
    webhook_url = f"{webapp_url}/api/telegram/webhook"
    
    print(f"[WEBHOOK] URL: {webhook_url}", flush=True)
    
    try:
        await remove_webhook(bot)
        print("[WEBHOOK] Removed old webhook", flush=True)
        
        result = await bot.set_webhook(
            url=webhook_url,
            allowed_updates=["message", "callback_query", "pre_checkout_query"],
        )
        print(f"[WEBHOOK] Telegram response: {result}", flush=True)
        
        if result:
            print("[WEBHOOK] SUCCESS", flush=True)
        else:
            print("[WEBHOOK] FAILED - Telegram returned False", flush=True)
        
        # Проверяем что webhook установлен
        await asyncio.sleep(2)
        info = await bot.get_webhook_info()
        print(f"[WEBHOOK] Current webhook URL: {info.url}", flush=True)
        if info.url == webhook_url:
            print(f"[WEBHOOK] Verified: {info.url}", flush=True)
        else:
            print(f"[WEBHOOK] WARNING: URL mismatch! Expected {webhook_url}, got {info.url}", flush=True)
    except Exception as e:
        print(f"[WEBHOOK] ERROR: {e}", flush=True)
        import traceback
        traceback.print_exc()
    finally:
        await bot.session.close()


if __name__ == "__main__":
    if os.getenv("PORT"):
        asyncio.run(main())
    print("[WEBHOOK] Done", flush=True)
