from __future__ import annotations

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand, MenuButtonWebApp, WebAppInfo

from app.bot.handlers.admin import register_admin_handlers
from app.bot.handlers.admin_dashboard import register_admin_dashboard
from app.bot.handlers.booking_actions import register_booking_actions
from app.bot.handlers.common import register_common_handlers
from app.bot.handlers.webapp import register_webapp_handlers
from app.bot.middlewares.rate_limit import RateLimitMiddleware
from app.bot.scheduler import setup_scheduler
from app.config import get_settings
from app.db.base import init_db, session_factory
from app.logging import get_logger
from app.logging_config import setup_logging

logger = get_logger(__name__)


async def set_bot_commands(bot: Bot) -> None:
    """Установка команд бота и Menu Button."""
    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="menu", description="Показать меню"),
        BotCommand(command="mybookings", description="Мои брони"),
        BotCommand(command="help", description="Помощь"),
    ]
    await bot.set_my_commands(commands)
    
    # Устанавливаем Menu Button (кнопка OPEN в списке чатов)
    webapp_url = os.getenv("WEBAPP_URL", "https://filinhookah-1.onrender.com/webapp")
    try:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="Открыть мини-приложение",
                web_app=WebAppInfo(url=webapp_url),
            )
        )
        logger.info("Menu Button установлен: %s", webapp_url)
    except Exception as e:
        logger.warning("Не удалось установить Menu Button: %s", e)


async def set_webhook(bot: Bot, webhook_url: str) -> None:
    """Установка webhook."""
    await bot.set_webhook(
        url=webhook_url,
        allowed_updates=["message", "callback_query", "pre_checkout_query"],
    )
    logger.info("Webhook set to: %s", webhook_url)
    await set_bot_commands(bot)


async def remove_webhook(bot: Bot) -> None:
    """Удаление webhook."""
    await bot.delete_webhook()
    logger.info("Webhook removed")


async def run_polling() -> None:
    """Запуск бота с обработкой ошибок."""
    settings = get_settings()
    
    if not settings.bot_token:
        logger.critical("BOT_TOKEN не настроен в .env")
        raise ValueError("BOT_TOKEN is not set in .env")
    
    setup_logging(settings.log_path)
    logger.info("Инициализация базы данных...")
    await init_db()

    logger.info("Создание бота...")
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    
    dp = Dispatcher()
    dp.message.middleware(RateLimitMiddleware())
    dp.callback_query.middleware(RateLimitMiddleware())

    logger.info("Регистрация обработчиков...")
    dp.include_router(register_common_handlers(session_factory, settings))
    dp.include_router(register_webapp_handlers(session_factory, settings))
    dp.include_router(register_booking_actions(session_factory, settings))
    dp.include_router(register_admin_dashboard(session_factory, settings))
    dp.include_router(register_admin_handlers(session_factory, settings))

    scheduler = setup_scheduler(bot, session_factory)

    bot_me = await bot.get_me()
    logger.info(f"Запуск polling для бота @{bot_me.username}...")

    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")
    except Exception as e:
        logger.critical(f"Критическая ошибка бота: {e}", exc_info=True)
        raise
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    asyncio.run(run_polling())
