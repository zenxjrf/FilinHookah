"""Global dispatcher for webhook mode."""
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.bot.handlers.admin import register_admin_handlers
from app.bot.handlers.admin_dashboard import register_admin_dashboard
from app.bot.handlers.booking_actions import register_booking_actions
from app.bot.handlers.common import register_common_handlers
from app.bot.handlers.webapp import register_webapp_handlers
from app.bot.middleware.rate_limit import RateLimitMiddleware
from app.config import get_settings
from app.db.base import session_factory


def create_dispatcher() -> Dispatcher:
    """Create and configure dispatcher with all handlers."""
    settings = get_settings()
    dp = Dispatcher()
    
    # Middleware
    dp.message.middleware(RateLimitMiddleware())
    dp.callback_query.middleware(RateLimitMiddleware())
    
    # Register all handlers using include_routers
    from app.bot.handlers.admin import register_admin_handlers
    from app.bot.handlers.admin_dashboard import register_admin_dashboard
    from app.bot.handlers.booking_actions import register_booking_actions
    from app.bot.handlers.common import register_common_handlers
    from app.bot.handlers.webapp import register_webapp_handlers
    
    dp.include_routers(
        register_common_handlers(session_factory, settings),
        register_webapp_handlers(session_factory, settings),
        register_booking_actions(session_factory, settings),
        register_admin_dashboard(session_factory, settings),
        register_admin_handlers(session_factory, settings),
    )
    
    return dp


def create_bot() -> Bot:
    """Create bot instance."""
    settings = get_settings()
    return Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
