from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import Settings
from app.db import crud

router = Router(name="booking_actions")


def register_booking_actions(session_factory: async_sessionmaker, settings: Settings) -> Router:
    @router.callback_query(F.data.startswith("booking_confirm_"))
    async def on_confirm_booking(callback: CallbackQuery) -> None:
        if not callback.from_user:
            await callback.answer("Ошибка", show_alert=True)
            return

        try:
            booking_id = int(callback.data.split("_")[-1])
        except (ValueError, IndexError):
            await callback.answer("Неверный ID брони", show_alert=True)
            return

        async with session_factory() as session:
            booking = await crud.confirm_booking_visit(session, booking_id)

        if not booking:
            await callback.answer("Бронь не найдена", show_alert=True)
            return

        # Уведомляем пользователя
        try:
            await callback.bot.send_message(
                booking.client.telegram_id,
                f"✅ <b>Бронь подтверждена!</b>\n\n"
                f"📅 Дата: {booking.booking_at:%d.%m.%Y %H:%M}\n"
                f"🪑 Столик: {booking.table_no}\n"
                f"👥 Гостей: {booking.guests}\n\n"
                f"Ждем вас в Filin Lounge! 🎉"
            )
        except Exception:
            pass

        # Обновляем сообщение в чате работников
        try:
            await callback.message.edit_text(
                f"🟢 <b>Бронь #{booking.id} подтверждена</b>\n\n"
                f"👤 Клиент: {booking.client.full_name or '—'}\n"
                f"📅 Дата: {booking.booking_at:%d.%m.%Y %H:%M}\n"
                f"🪑 Стол: {booking.table_no}, гостей: {booking.guests}\n\n"
                f"Статус: <b>ПОДТВЕРЖДЕНА</b> ✅",
                reply_markup=None,
            )
        except Exception:
            pass

        await callback.answer("Бронь подтверждена!")

    @router.callback_query(F.data.startswith("booking_cancel_"))
    async def on_cancel_booking(callback: CallbackQuery) -> None:
        if not callback.from_user:
            await callback.answer("Ошибка", show_alert=True)
            return

        try:
            booking_id = int(callback.data.split("_")[-1])
        except (ValueError, IndexError):
            await callback.answer("Неверный ID брони", show_alert=True)
            return

        async with session_factory() as session:
            booking = await crud.cancel_booking(session, booking_id)

        if not booking:
            await callback.answer("Бронь не найдена", show_alert=True)
            return

        # Уведомляем пользователя
        try:
            await callback.bot.send_message(
                booking.client.telegram_id,
                f"🔴 <b>Бронь отменена!</b>\n\n"
                f"❌ Бронь #{booking.id} отменена\n"
                f"📅 Дата: {booking.booking_at:%d.%m.%Y %H:%M}\n"
                f"🪑 Столик: {booking.table_no}\n\n"
                f"По вопросам: {settings.default_contacts}"
            )
        except Exception:
            pass

        # Обновляем сообщение в чате работников
        try:
            await callback.message.edit_text(
                f"🔴 <b>Бронь #{booking.id} отменена</b>\n\n"
                f"👤 Клиент: {booking.client.full_name or '—'}\n"
                f"📅 Дата: {booking.booking_at:%d.%m.%Y %H:%M}\n"
                f"🪑 Стол: {booking.table_no}, гостей: {booking.guests}\n\n"
                f"Статус: <b>ОТМЕНЕНА</b> ❌",
                reply_markup=None,
            )
        except Exception:
            pass

        await callback.answer("Бронь отменена!")

    @router.callback_query(F.data.startswith("booking_close_"))
    async def on_close_booking(callback: CallbackQuery) -> None:
        if not callback.from_user:
            await callback.answer("Ошибка", show_alert=True)
            return

        try:
            booking_id = int(callback.data.split("_")[-1])
        except (ValueError, IndexError):
            await callback.answer("Неверный ID брони", show_alert=True)
            return

        async with session_factory() as session:
            booking = await crud.close_booking(session, booking_id)

        if not booking:
            await callback.answer("Бронь не найдена", show_alert=True)
            return

        # Уведомляем пользователя
        try:
            await callback.bot.send_message(
                booking.client.telegram_id,
                f"🟢 <b>Бронь выполнена!</b>\n\n"
                f"✅ Бронь #{booking.id} закрыта\n"
                f"📅 Дата: {booking.booking_at:%d.%m.%Y %H:%M}\n"
                f"🪑 Столик: {booking.table_no}\n\n"
                f"Спасибо за визит! Ждем вас снова! 💚"
            )
        except Exception:
            pass

        # Обновляем сообщение в чате работников
        try:
            await callback.message.edit_text(
                f"🟢 <b>Бронь #{booking.id} выполнена</b>\n\n"
                f"👤 Клиент: {booking.client.full_name or '—'}\n"
                f"📅 Дата: {booking.booking_at:%d.%m.%Y %H:%M}\n"
                f"🪑 Стол: {booking.table_no}, гостей: {booking.guests}\n\n"
                f"Статус: <b>ВЫПОЛНЕНА</b> ✅\n"
                f"Визитов у клиента: <b>{booking.client.visits}</b>",
                reply_markup=None,
            )
        except Exception:
            pass

        await callback.answer("Бронь закрыта!")

    @router.callback_query(F.data.startswith("confirm_attend_"))
    async def on_confirm_attend(callback: CallbackQuery) -> None:
        """Гость подтверждает, что придёт (из напоминания за 24 часа)."""
        if not callback.from_user:
            await callback.answer("Ошибка", show_alert=True)
            return

        try:
            booking_id = int(callback.data.split("_")[-1])
        except (ValueError, IndexError):
            await callback.answer("Неверный ID брони", show_alert=True)
            return

        async with session_factory() as session:
            booking = await crud.get_booking_by_id(session, booking_id)

        if not booking:
            await callback.answer("Бронь не найдена", show_alert=True)
            return

        # Проверяем, что это тот же пользователь
        if booking.client.telegram_id != callback.from_user.id:
            await callback.answer("Это не ваша бронь!", show_alert=True)
            return

        # Подтверждаем бронь
        booking.status = "confirmed"
        await session.commit()

        # Обновляем сообщение
        try:
            await callback.message.edit_text(
                f"✅ <b>Вы подтвердили бронь #{booking.id}</b>\n\n"
                f"📅 Дата: {booking.booking_at:%d.%m.%Y %H:%M}\n"
                f"🪑 Стол: {booking.table_no}\n"
                f"👥 Гостей: {booking.guests}\n\n"
                f"Ждём вас завтра! 🦉",
                reply_markup=None,
            )
        except Exception:
            pass

        await callback.answer("Бронь подтверждена! Ждём вас!")

    return router
