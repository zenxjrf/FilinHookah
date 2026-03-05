from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.admin_ids import get_all_admin_ids
from app.config import Settings
from app.db import crud

router = Router(name="admin_dashboard")


def register_admin_dashboard(session_factory: async_sessionmaker, settings: Settings) -> Router:
    @router.message(Command("dashboard"))
    async def dashboard(message: Message) -> None:
        """Дашборд администратора."""
        if not message.from_user or message.from_user.id not in get_all_admin_ids(settings):
            await message.answer("Нет доступа.")
            return

        await message.answer(
            "📊 <b>Дашборд администратора</b>\n\n"
            "Используйте команды:\n\n"
            "/subscribers - статистика подписчиков\n"
            "/broadcast - рассылка подписчикам\n"
            "/check_client [id] - информация о клиенте\n"
            "/add_visits [id] [кол-во] - добавить визиты\n"
            "/set_schedule [текст] - обновить график\n"
            "/set_contacts [текст] - обновить контакты\n"
            "/add_promo [заголовок] | [описание] | [url] - добавить акцию",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="📊 Подписчики",
                            callback_data="admin_subscribers"
                        ),
                    ],
                ]
            ),
            parse_mode="HTML",
        )

    @router.callback_query(F.data == "dashboard_refresh")
    async def dashboard_refresh(callback: CallbackQuery) -> None:
        """Обновить дашборд."""
        if not callback.from_user or callback.from_user.id not in get_all_admin_ids(settings):
            await callback.answer("Нет доступа.")
            return

        await callback.answer("Дашборд обновлён", show_alert=False)

    @router.callback_query(F.data == "admin_subscribers")
    async def admin_subscribers(callback: CallbackQuery) -> None:
        """Показать статистику подписчиков."""
        if not callback.from_user or callback.from_user.id not in get_all_admin_ids(settings):
            await callback.answer("Нет доступа.")
            return

        async with session_factory() as session:
            count = await crud.get_subscribers_count(session)

        await callback.message.answer(
            f"📊 <b>Статистика подписчиков</b>\n\n"
            f"👥 Активных подписчиков: <b>{count}</b>\n\n"
            f"Используйте /broadcast для рассылки.",
            parse_mode="HTML",
        )
        await callback.answer()

    return router
