"""Global dispatcher for webhook mode."""
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.bot.middleware.rate_limit import RateLimitMiddleware
from app.config import get_settings
from app.db.base import session_factory

# Глобальные bot и dispatcher для webhook
_webhook_bot: Bot | None = None
_webhook_dp: Dispatcher | None = None


def get_bot() -> Bot:
    """Get or create global bot instance."""
    global _webhook_bot
    if _webhook_bot is None:
        settings = get_settings()
        _webhook_bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    return _webhook_bot


def get_dispatcher() -> Dispatcher:
    """Get or create global dispatcher with all handlers."""
    global _webhook_dp
    if _webhook_dp is None:
        settings = get_settings()
        _webhook_dp = Dispatcher()
        
        # Middleware
        _webhook_dp.message.middleware(RateLimitMiddleware())
        _webhook_dp.callback_query.middleware(RateLimitMiddleware())
        
        # Register all handlers
        from app.bot.handlers.admin import register_admin_handlers
        from app.bot.handlers.admin_dashboard import register_admin_dashboard
        from app.bot.handlers.booking_actions import register_booking_actions
        from app.bot.handlers.common import register_common_handlers
        from app.bot.handlers.webapp import register_webapp_handlers
        
        _webhook_dp.include_routers(
            register_common_handlers(session_factory, settings),
            register_webapp_handlers(session_factory, settings),
            register_booking_actions(session_factory, settings),
            register_admin_dashboard(session_factory, settings),
            register_admin_handlers(session_factory, settings),
        )
    
    return _webhook_dp


def create_bot() -> Bot:
    """Create bot instance (alias for get_bot)."""
    return get_bot()


def create_dispatcher() -> Dispatcher:
    """Create dispatcher (alias for get_dispatcher)."""
    return get_dispatcher()
