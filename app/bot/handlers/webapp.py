from __future__ import annotations

import json
import logging
from datetime import datetime

from aiogram import F, Router
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.admin_ids import get_all_admin_ids
from app.config import Settings
from app.db import crud

router = Router(name="webapp")


def register_webapp_handlers(session_factory: async_sessionmaker, settings: Settings) -> Router:
    @router.message(F.web_app_data)
    async def web_app_data(message: Message) -> None:
        logging.info(f"=== Web App Data получено от {message.from_user.id}")
        if not message.from_user or not message.web_app_data:
            logging.warning("Нет from_user или web_app_data")
            return

        try:
            payload = json.loads(message.web_app_data.data)
            logging.info(f"Payload: {payload}")
        except Exception as e:
            logging.error(f"Ошибка парсинга payload: {e}")
            await message.answer("Не удалось обработать данные из mini app.")
            return

        action = payload.get("action", "booking")
        logging.info(f"Action: {action}")

        if action == "booking_created":
            booking_id = int(payload.get("booking_id", 0))
            if not booking_id:
                await message.answer("Не получен ID брони.")
                return

            async with session_factory() as session:
                client = await crud.get_or_create_client(
                    session=session,
                    telegram_id=message.from_user.id,
                    username=message.from_user.username,
                    full_name=message.from_user.full_name,
                )
                booking = await crud.get_booking_by_id(session, booking_id)
                if not booking or booking.client_id != client.id:
                    await message.answer("Бронь не найдена.")
                    return

            await message.answer(
                f"✅ <b>Заявка на бронь создана!</b>\n\n"
                f"📅 Дата: {booking.booking_at:%d.%m.%Y %H:%M}\n"
                f"🪑 Столик: {booking.table_no}\n"
                f"👥 Гостей: {booking.guests}\n\n"
                f"Ожидайте подтверждения от администратора. ⏳"
            )

            # Формируем сообщение для чата работников с кнопками
            admin_text = (
                f"🔔 <b>Новая бронь #{booking.id}</b>\n\n"
                f"👤 Клиент: {message.from_user.full_name} (@{message.from_user.username or 'нет'})\n"
                f"🆔 Telegram ID: {message.from_user.id}\n"
                f"📅 Дата: {booking.booking_at:%d.%m.%Y %H:%M}\n"
                f"🪑 Стол: {booking.table_no}, гостей: {booking.guests}\n"
                f"📝 Комментарий: {booking.comment or '—'}\n\n"
                f"<b>Статус:</b> Ожидает подтверждения ⏳"
            )

            # Клавиатура с действиями
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="✅ Подтвердить",
                            callback_data=f"booking_confirm_{booking.id}",
                        ),
                        InlineKeyboardButton(
                            text="❌ Отменить",
                            callback_data=f"booking_cancel_{booking.id}",
                        ),
                    ],
                    [
                        InlineKeyboardButton(
                            text="🟢 Закрыть (клиент ушел)",
                            callback_data=f"booking_close_{booking.id}",
                        ),
                    ],
                ]
            )

            # Отправляем в чат работников или всем админам
            logging.info(f"Отправка уведомления в чат работников: {settings.workers_chat_id}")
            if settings.workers_chat_id:
                try:
                    await message.bot.send_message(
                        settings.workers_chat_id,
                        admin_text,
                        reply_markup=keyboard,
                    )
                    logging.info(f"Уведомление отправлено в чат {settings.workers_chat_id}")
                except Exception as e:
                    logging.error(f"Ошибка отправки в чат работников: {e}")
                    # Если не удалось отправить в чат работников, отправляем админам
                    for admin_id in get_all_admin_ids(settings):
                        await message.bot.send_message(
                            admin_id,
                            admin_text,
                            reply_markup=keyboard,
                        )
            else:
                for admin_id in get_all_admin_ids(settings):
                    await message.bot.send_message(
                        admin_id,
                        admin_text,
                        reply_markup=keyboard,
                    )
            return

        if action == "booking_canceled":
            # Уведомление об отмене брони гостем
            booking_id = int(payload.get("booking_id", 0))
            logging.info(f"Бронь отменена: {booking_id}")
            
            if not booking_id:
                return
            
            async with session_factory() as session:
                booking = await crud.get_booking_by_id(session, booking_id)
            
            if not booking:
                return
            
            admin_text = (
                f"❌ <b>Бронь #{booking.id} отменена гостем</b>\n\n"
                f"📅 Дата: {booking.booking_at:%d.%m.%Y %H:%M}\n"
                f"🪑 Стол: {booking.table_no}\n\n"
                f"Стол освобождён."
            )
            
            if settings.workers_chat_id:
                try:
                    await message.bot.send_message(settings.workers_chat_id, admin_text)
                    logging.info(f"Уведомление об отмене отправлено в чат {settings.workers_chat_id}")
                except Exception as e:
                    logging.error(f"Ошибка отправки уведомления об отмене: {e}")
            else:
                for admin_id in get_all_admin_ids(settings):
                    await message.bot.send_message(admin_id, admin_text)
            return

        if action == "review_created":
            await message.answer("Спасибо, отзыв получен.")
            return

        # Backward compatibility: old payload format (booking fields directly).
        try:
            booking_at = datetime.fromisoformat(payload["date_time"])
            table_no = int(payload["table_no"])
            guests = int(payload.get("guests", 2))
            comment = payload.get("comment")
        except Exception:
            await message.answer("Неизвестный формат данных из mini app.")
            return

        async with session_factory() as session:
            client = await crud.get_or_create_client(
                session=session,
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                full_name=message.from_user.full_name,
            )
            try:
                booking = await crud.create_booking(
                    session=session,
                    client_id=client.id,
                    booking_at=booking_at,
                    table_no=table_no,
                    guests=guests,
                    comment=comment,
                )
            except ValueError as exc:
                await message.answer(str(exc))
                return

        await message.answer(f"Бронь создана: #{booking.id}")

    return router
