from __future__ import annotations

import logging
from datetime import datetime, timedelta

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db import crud
from app.db.models import Booking, BookingStatus

logger = logging.getLogger(__name__)


def setup_scheduler(bot: Bot, session_factory: async_sessionmaker) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()

    async def send_reminder(booking: Booking, hours_before: int) -> None:
        """Отправить напоминание о брони."""
        if not booking.client.telegram_id:
            return

        # Создаём клавиатуру с кнопками (только для 24-часового напоминания)
        keyboard = None
        if hours_before == 24:
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="✅ Я приду",
                            callback_data=f"confirm_attend_{booking.id}",
                        ),
                        InlineKeyboardButton(
                            text="❌ Отменить",
                            callback_data=f"cancel_booking_{booking.id}",
                        ),
                    ]
                ]
            )

        message_text = (
            f"🔔 <b>Напоминание о брони #{booking.id}</b>\n\n"
            f"📅 Дата: {booking.booking_at:%d.%m.%Y %H:%M}\n"
            f"🪑 Стол: {booking.table_no}\n"
            f"👥 Гостей: {booking.guests}\n\n"
        )

        if hours_before == 24:
            message_text += (
                f"⏰ Напоминание за 24 часа до визита.\n\n"
                f"Пожалуйста, подтвердите, что вы придёте!"
            )
        else:
            message_text += (
                f"⏰ Напоминание за 1 час до визита.\n\n"
                f"Ждём вас в Filin Lounge Bar! 🦉"
            )

        try:
            await bot.send_message(
                booking.client.telegram_id,
                message_text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
            logger.info(f"Отправлено напоминание за {hours_before}ч для брони #{booking.id}")
        except Exception as e:
            logger.error(f"Ошибка отправки напоминания #{booking.id}: {e}")

    @scheduler.scheduled_job("interval", minutes=10)
    async def reminders_24h_job() -> None:
        """Напоминание за 24 часа до брони."""
        async with session_factory() as session:
            now = datetime.utcnow()
            target_time = now + timedelta(hours=24)
            target_time_end = target_time + timedelta(minutes=30)  # Окно ±30 минут

            stmt = (
                select(Booking)
                .where(
                    and_(
                        Booking.booking_at >= target_time,
                        Booking.booking_at <= target_time_end,
                        Booking.status.in_([BookingStatus.PENDING.value, BookingStatus.CONFIRMED.value]),
                        Booking.reminder_sent.is_(False),
                    )
                )
            )
            bookings = (await session.scalars(stmt)).all()

            for booking in bookings:
                await send_reminder(booking, hours_before=24)
                booking.reminder_sent = True  # Помечаем что напоминание отправлено

            await session.commit()

        if bookings:
            logger.info(f"Отправлено {len(bookings)} напоминаний за 24 часа")

    @scheduler.scheduled_job("interval", minutes=10)
    async def reminders_1h_job() -> None:
        """Напоминание за 1 час до брони."""
        async with session_factory() as session:
            now = datetime.utcnow()
            target_time = now + timedelta(hours=1)
            target_time_end = target_time + timedelta(minutes=15)  # Окно ±15 минут

            stmt = (
                select(Booking)
                .where(
                    and_(
                        Booking.booking_at >= target_time,
                        Booking.booking_at <= target_time_end,
                        Booking.status.in_([BookingStatus.PENDING.value, BookingStatus.CONFIRMED.value]),
                        Booking.reminder_1h_sent.is_(False),  # Проверяем флаг
                    )
                )
            )
            bookings = (await session.scalars(stmt)).all()

            for booking in bookings:
                await send_reminder(booking, hours_before=1)
                booking.reminder_1h_sent = True  # Помечаем что напоминание отправлено

            await session.commit()

        if bookings:
            logger.info(f"Отправлено {len(bookings)} напоминаний за 1 час")

    scheduler.start()
    return scheduler
