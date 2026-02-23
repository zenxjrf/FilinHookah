from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.bot.keyboards.main import main_menu_keyboard
from app.config import Settings
from app.db import crud

router = Router(name="common")


def register_common_handlers(session_factory: async_sessionmaker, settings: Settings) -> Router:
    async def send_callback_text(callback: CallbackQuery, text: str) -> None:
        if callback.message:
            await callback.message.answer(text)
        else:
            await callback.bot.send_message(callback.from_user.id, text)

    @router.message(Command("start"))
    async def cmd_start(message: Message) -> None:
        if not message.from_user:
            return
        async with session_factory() as session:
            await crud.get_or_create_client(
                session=session,
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                full_name=message.from_user.full_name,
            )
        await message.answer(
            "🦉 <b>Филин Lounge Bar</b>\n\n"
            "💨 Дым. Вкус. Атмосфера\n\n"
            "Открой мини-приложение — забронируй стол, узнай об акциях и получи бонусы!\n\n"
            "🎁 5-й кальян со скидкой 50%\n"
            "🏆 10-й кальян бесплатно",
            reply_markup=main_menu_keyboard(settings.webapp_url),
        )

    @router.callback_query(F.data == "promotions")
    async def promotions(callback: CallbackQuery) -> None:
        async with session_factory() as session:
            promos = await crud.get_active_promotions(session)
        if not promos:
            text = "Сейчас активных акций нет."
        else:
            lines = [f"<b>{p.title}</b>\n{p.description}" for p in promos[:5]]
            text = "\n\n".join(lines)
        await send_callback_text(callback, text)
        await callback.answer()

    @router.callback_query(F.data == "schedule")
    async def schedule(callback: CallbackQuery) -> None:
        await send_callback_text(callback, "<b>График работы</b>\nЕжедневно с 14:00 до 2:00")
        await callback.answer()

    @router.callback_query(F.data == "contacts")
    async def contacts(callback: CallbackQuery) -> None:
        # Создаем клавиатуру с кнопкой локации
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🗺️ Показать на карте",
                        url="https://2gis.ru/krasnoyarsk/search/Филин%20центр%20паровых%20коктейлей/firm/70000001042591694/92.798474%2C56.025546?m=92.798522%2C56.025568%2F17.24"
                    )
                ]
            ]
        )
        
        if callback.message:
            await callback.message.answer(
                "📍 <b>Филин Lounge Bar</b>\n\n"
                "📞 <b>Телефон:</b> <a href='tel:+79504333434'>7-950-433-34-34</a>\n\n"
                "🌙 <i>Твой идеальный вечер</i>\n\n"
                "Нажми на кнопку ниже, чтобы увидеть местоположение на карте!",
                parse_mode="HTML",
                reply_markup=keyboard
            )
        else:
            await callback.bot.send_message(
                callback.from_user.id,
                "📍 <b>Филин Lounge Bar</b>\n\n"
                "📞 <b>Телефон:</b> <a href='tel:+79504333434'>7-950-433-34-34</a>\n\n"
                "🌙 <i>Твой идеальный вечер</i>\n\n"
                "Нажми на кнопку ниже, чтобы увидеть местоположение на карте!",
                parse_mode="HTML",
                reply_markup=keyboard
            )
        await callback.answer()

    @router.callback_query(F.data == "hookah_menu")
    async def menu(callback: CallbackQuery) -> None:
        await send_callback_text(
            callback,
            "<b>Меню</b>\n"
            "Классический кальян - 1200 рублей\n"
            "Классический кальян до 18:00 - 1000 рублей\n"
            "Напитки и пиво с бара - 200 рублей",
        )
        await callback.answer()

    @router.callback_query(F.data == "booking_link_unavailable")
    async def booking_link_unavailable(callback: CallbackQuery) -> None:
        await send_callback_text(
            callback,
            "Бронирование через mini app временно недоступно.\n"
            "Для Telegram WebApp нужен HTTPS URL в WEBAPP_URL."
        )
        await callback.answer()

    @router.callback_query(F.data == "my_bookings")
    async def my_bookings(callback: CallbackQuery) -> None:
        if not callback.from_user:
            await callback.answer()
            return
        async with session_factory() as session:
            client = await crud.get_or_create_client(
                session=session,
                telegram_id=callback.from_user.id,
                username=callback.from_user.username,
                full_name=callback.from_user.full_name,
            )
            bookings = await crud.list_user_bookings(session, client.id)
        if not bookings:
            text = "У вас нет активных броней."
        else:
            rows = [
                f"#{b.id} | Стол {b.table_no} | Бронь на {b.booking_at:%d.%m %H:%M} | Создана {b.created_at:%d.%m %H:%M} | {b.status}"
                for b in bookings
            ]
            text = "<b>Ваши брони:</b>\n" + "\n".join(rows)
        await send_callback_text(callback, text)
        await callback.answer()

    @router.callback_query(F.data == "loyalty")
    async def loyalty(callback: CallbackQuery) -> None:
        if not callback.from_user:
            await callback.answer()
            return
        async with session_factory() as session:
            client = await crud.get_or_create_client(
                session=session,
                telegram_id=callback.from_user.id,
                username=callback.from_user.username,
                full_name=callback.from_user.full_name,
            )
        await send_callback_text(
            callback,
            f"Ваши визиты: <b>{client.visits}</b>\n"
            "При заказе 5-го кальяна - скидка 50%.\n"
            "При заказе 10-го кальяна - бесплатно."
        )
        await callback.answer()

    return router
