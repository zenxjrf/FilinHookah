from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import Settings
from app.db import crud
from app.db.models import Client

# Состояние для рассылки
_broadcast_state: dict[int, bool] = {}
logger = logging.getLogger(__name__)


def create_admin_router(session_factory: async_sessionmaker, settings: Settings) -> Router:
    router = Router(name="admin")

    def is_admin(message: Message) -> bool:
        return bool(message.from_user and message.from_user.id in settings.admin_ids)

    @router.message(Command("whoami"))
    async def whoami(message: Message) -> None:
        if not message.from_user:
            return
        await message.answer(
            f"Ваш telegram_id: `{message.from_user.id}`\n"
            f"Админ: {'да' if is_admin(message) else 'нет'}",
            parse_mode="Markdown",
        )

    @router.message(Command("admin"))
    async def admin_panel(message: Message) -> None:
        if not is_admin(message):
            if message.from_user:
                await message.answer(
                    "Нет доступа.\n"
                    f"Ваш telegram_id: `{message.from_user.id}`\n"
                    "Добавьте его в ADMIN_IDS и перезапустите бота.",
                    parse_mode="Markdown",
                )
            else:
                await message.answer("Нет доступа.")
            return
        await message.answer(
            "Админ-команды:\n"
            "/bookings [YYYY-MM-DD]\n"
            "/confirm_booking [id] - подтвердить (клиент придет)\n"
            "/close_booking [id] - закрыть (клиент посидел)\n"
            "/cancel_booking [id] - отменить бронь\n"
            "/staff_booking [телефон] [дата] [время] [стол] [гостей] - бронь по телефону\n"
            "/block_table [стол] [дата] [время] [мин] - заблокировать стол\n"
            "/check_client [id] - информация о клиенте\n"
            "/add_visits [id] [кол-во] - добавить визиты\n"
            "/reset_visits [id] - сбросить визиты\n"
            "/set_schedule [текст]\n"
            "/set_contacts [текст]\n"
            "/add_promo [заголовок] | [описание] | [url]"
        )

    @router.message(F.text.regexp(r"^/admin(@\w+)?$"))
    async def admin_panel_fallback(message: Message) -> None:
        await admin_panel(message)

    @router.message(Command("bookings"))
    async def bookings(message: Message) -> None:
        if not is_admin(message):
            await message.answer("Нет доступа.")
            return
        from_date = None
        if message.text:
            parts = message.text.split(maxsplit=1)
            if len(parts) == 2:
                try:
                    from_date = datetime.strptime(parts[1], "%Y-%m-%d").date()
                except ValueError:
                    await message.answer("Дата должна быть в формате YYYY-MM-DD.")
                    return
        async with session_factory() as session:
            items = await crud.list_all_bookings(session, from_date)
        if not items:
            await message.answer("Брони не найдены.")
            return
        lines = [
            f"#{b.id} | {b.booking_at:%d.%m %H:%M} | стол {b.table_no} | гостей {b.guests} | {b.status}"
            for b in items
        ]
        await message.answer("<b>Список броней:</b>\n" + "\n".join(lines[:50]))

    @router.message(Command("confirm_booking"))
    async def confirm_booking(message: Message) -> None:
        if not is_admin(message):
            await message.answer("Нет доступа.")
            return
        if not message.text:
            await message.answer("Формат: /confirm_booking [id]")
            return
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.answer("Формат: /confirm_booking [id]")
            return
        try:
            booking_id = int(parts[1])
        except ValueError:
            await message.answer("ID брони должен быть числом.")
            return
        async with session_factory() as session:
            booking = await crud.confirm_booking_visit(session, booking_id)
        if not booking:
            await message.answer("Бронь не найдена.")
            return
        # Отправляем уведомление пользователю
        try:
            await message.bot.send_message(
                booking.client.telegram_id,
                f"✅ <b>Бронь подтверждена!</b>\n\n"
                f"📅 Дата: {booking.booking_at:%d.%m.%Y %H:%M}\n"
                f"🪑 Столик: {booking.table_no}\n"
                f"👥 Гостей: {booking.guests}\n\n"
                f"Ждем вас в Filin Lounge! 🎉"
            )
        except Exception:
            pass  # Если пользователь заблокировал бота
        await message.answer(f"✅ Бронь #{booking_id} подтверждена. Пользователь уведомлен.")

    @router.message(Command("close_booking"))
    async def close_booking(message: Message) -> None:
        if not is_admin(message):
            await message.answer("Нет доступа.")
            return
        if not message.text:
            await message.answer("Формат: /close_booking [id]")
            return
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.answer("Формат: /close_booking [id]")
            return
        try:
            booking_id = int(parts[1])
        except ValueError:
            await message.answer("ID брони должен быть числом.")
            return
        async with session_factory() as session:
            booking = await crud.close_booking(session, booking_id)
        if not booking:
            await message.answer("Бронь не найдена.")
            return
        # Отправляем уведомление пользователю
        try:
            await message.bot.send_message(
                booking.client.telegram_id,
                f"🟢 <b>Бронь выполнена!</b>\n\n"
                f"✅ Бронь #{booking.id} закрыта\n"
                f"📅 Дата: {booking.booking_at:%d.%m.%Y %H:%M}\n"
                f"🪑 Столик: {booking.table_no}\n\n"
                f"Спасибо за визит! Ждем вас снова! 💚"
            )
        except Exception:
            pass  # Если пользователь заблокировал бота
        await message.answer(f"🟢 Бронь #{booking_id} закрыта. Пользователь уведомлен.")

    @router.message(Command("cancel_booking"))
    async def cancel_booking(message: Message) -> None:
        if not is_admin(message):
            await message.answer("Нет доступа.")
            return
        if not message.text:
            await message.answer("Формат: /cancel_booking [id]")
            return
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.answer("Формат: /cancel_booking [id]")
            return
        try:
            booking_id = int(parts[1])
        except ValueError:
            await message.answer("ID брони должен быть числом.")
            return
        async with session_factory() as session:
            booking = await crud.cancel_booking(session, booking_id)
        if not booking:
            await message.answer("Бронь не найдена.")
            return
        # Отправляем уведомление пользователю
        try:
            await message.bot.send_message(
                booking.client.telegram_id,
                f"🔴 <b>Бронь отменена!</b>\n\n"
                f"❌ Бронь #{booking.id} отменена\n"
                f"📅 Дата: {booking.booking_at:%d.%m.%Y %H:%M}\n"
                f"🪑 Столик: {booking.table_no}\n\n"
                f"По вопросам: {settings.default_contacts}"
            )
        except Exception:
            pass  # Если пользователь заблокировал бота
        await message.answer(f"🔴 Бронь #{booking_id} отменена. Пользователь уведомлен.")

    @router.message(Command("add_visits"))
    async def add_visits(message: Message) -> None:
        """Добавить визиты клиенту по Telegram ID."""
        if not is_admin(message):
            await message.answer("Нет доступа.")
            return
        if not message.text:
            await message.answer("Формат: /add_visits [telegram_id] [кол-во]")
            return
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3:
            await message.answer("Формат: /add_visits [telegram_id] [кол-во]")
            return
        try:
            telegram_id = int(parts[1])
            visits_count = int(parts[2])
        except ValueError:
            await message.answer("Telegram ID и количество должны быть числами.")
            return
        
        async with session_factory() as session:
            client = await crud.get_client_by_telegram_id(session, telegram_id)
            if not client:
                await message.answer("Клиент не найден.")
                return
            client.visits += visits_count
            await session.commit()
        
        await message.answer(
            f"✅ Добавлено {visits_count} визитов пользователю {telegram_id}\n"
            f"Всего визитов: {client.visits}"
        )

    @router.message(Command("reset_visits"))
    async def reset_visits(message: Message) -> None:
        """Сбросить визиты клиенту."""
        if not is_admin(message):
            await message.answer("Нет доступа.")
            return
        if not message.text:
            await message.answer("Формат: /reset_visits [telegram_id]")
            return
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.answer("Формат: /reset_visits [telegram_id]")
            return
        try:
            telegram_id = int(parts[1])
        except ValueError:
            await message.answer("Telegram ID должен быть числом.")
            return
        
        async with session_factory() as session:
            client = await crud.get_client_by_telegram_id(session, telegram_id)
            if not client:
                await message.answer("Клиент не найден.")
                return
            client.visits = 0
            await session.commit()
        
        await message.answer(f"✅ Визиты сброшены для пользователя {telegram_id}")

    @router.message(Command("staff_booking"))
    async def staff_booking(message: Message) -> None:
        """Создать бронь сотрудником по номеру телефона."""
        if not is_admin(message):
            await message.answer("Нет доступа.")
            return
        
        # Формат: /staff_booking [телефон] [YYYY-MM-DD HH:MM] [стол] [гостей] [комментарий]
        if not message.text:
            await message.answer(
                "Формат: /staff_booking [телефон] [YYYY-MM-DD HH:MM] [стол] [гостей]\n"
                "Пример: /staff_booking +79991234567 2026-02-23 18:00 5 4"
            )
            return
        
        parts = message.text.split(maxsplit=5)
        if len(parts) < 5:
            await message.answer(
                "Формат: /staff_booking [телефон] [YYYY-MM-DD HH:MM] [стол] [гостей] [комментарий]\n"
                "Пример: /staff_booking +79991234567 2026-02-23 18:00 5 4"
            )
            return
        
        try:
            phone = parts[1]
            booking_datetime = datetime.strptime(parts[2] + " " + parts[3], "%Y-%m-%d %H:%M")
            table_no = int(parts[4])
            guests = int(parts[5]) if len(parts) > 5 else 2
            comment = parts[6] if len(parts) > 6 else "Бронь от сотрудника"
        except ValueError as e:
            await message.answer(f"Ошибка формата: {e}")
            return
        
        async with session_factory() as session:
            # Ищем клиента по номеру телефона
            client = await session.scalar(
                select(Client).where(Client.phone_hash == phone)
            )
            
            if not client:
                # Создаем нового клиента с телефоном
                client = await crud.get_or_create_client(
                    session=session,
                    telegram_id=0,  # Временный ID
                    username=None,
                    full_name=None,
                    phone=phone,
                )
            
            try:
                booking = await crud.create_booking(
                    session=session,
                    client_id=client.id,
                    booking_at=booking_datetime,
                    table_no=table_no,
                    guests=guests,
                    comment=comment,
                )
                # Помечаем как бронь от сотрудника
                booking.is_staff_booking = True
                await session.commit()
            except ValueError as e:
                await message.answer(f"Ошибка: {e}")
                return
        
        await message.answer(
            f"✅ Бронь создана!\n\n"
            f"🆔 ID: {booking.id}\n"
            f"📞 Телефон: {phone}\n"
            f"📅 Дата: {booking_datetime:%d.%m.%Y %H:%M}\n"
            f"🪑 Стол: {table_no}\n"
            f"👥 Гостей: {guests}\n"
            f"📝 Комментарий: {comment}"
        )

    @router.message(Command("block_table"))
    async def block_table(message: Message) -> None:
        """Заблокировать стол (создать бронь-заглушку)."""
        if not is_admin(message):
            await message.answer("Нет доступа.")
            return
        
        # Формат: /block_table [стол] [YYYY-MM-DD HH:MM] [длительность в минутах]
        if not message.text:
            await message.answer(
                "Формат: /block_table [стол] [YYYY-MM-DD HH:MM] [минуты]\n"
                "Пример: /block_table 5 2026-02-23 18:00 120"
            )
            return
        
        parts = message.text.split(maxsplit=3)
        if len(parts) < 4:
            await message.answer(
                "Формат: /block_table [стол] [YYYY-MM-DD HH:MM] [минуты]"
            )
            return
        
        try:
            table_no = int(parts[1])
            booking_datetime = datetime.strptime(parts[2] + " " + parts[3].split()[0], "%Y-%m-%d %H:%M")
            duration = int(parts[3].split()[1]) if len(parts[3].split()) > 1 else 120
        except ValueError as e:
            await message.answer(f"Ошибка формата: {e}")
            return
        
        async with session_factory() as session:
            # Создаем технического клиента для заглушек
            client = await crud.get_or_create_client(
                session=session,
                telegram_id=999999999,
                username="staff_block",
                full_name="Техническая бронь",
            )
            
            try:
                booking = await crud.create_booking(
                    session=session,
                    client_id=client.id,
                    booking_at=booking_datetime,
                    table_no=table_no,
                    guests=0,
                    comment="СТОЛ ЗАБЛОКИРОВАН ПЕРСОНАЛОМ",
                    duration_minutes=duration,
                )
                booking.is_staff_booking = True
                await session.commit()
            except ValueError as e:
                await message.answer(f"Ошибка: {e}")
                return
        
        await message.answer(
            f"🚫 Стол {table_no} заблокирован!\n\n"
            f"📅 Дата: {booking_datetime:%d.%m.%Y %H:%M}\n"
            f"⏱ Длительность: {duration} мин"
        )

    @router.message(Command("check_client"))
    async def check_client(message: Message) -> None:
        """Проверить информацию о клиенте."""
        if not is_admin(message):
            await message.answer("Нет доступа.")
            return
        if not message.text:
            await message.answer("Формат: /check_client [telegram_id]")
            return
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.answer("Формат: /check_client [telegram_id]")
            return
        try:
            telegram_id = int(parts[1])
        except ValueError:
            await message.answer("Telegram ID должен быть числом.")
            return
        
        async with session_factory() as session:
            client = await crud.get_client_by_telegram_id(session, telegram_id)
            if not client:
                await message.answer("Клиент не найден.")
                return
            
            bookings = await crud.list_user_bookings(session, client.id)
            active_bookings = len([b for b in bookings if b.status in ['pending', 'confirmed']])
        
        bonus_status = "🏆 БЕСПЛАТНЫЙ" if client.visits >= 10 else "🔥 50% скидка" if client.visits >= 5 else f"⏳ До бонуса: {5 - client.visits if client.visits < 5 else 10 - client.visits}"
        
        await message.answer(
            f"👤 <b>Информация о клиенте</b>\n\n"
            f"🆔 ID: {client.telegram_id}\n"
            f"👤 Имя: {client.full_name or '—'}\n"
            f"📝 Username: @{client.username or 'нет'}\n"
            f"💎 Визитов: {client.visits}\n"
            f"🎁 Статус: {bonus_status}\n"
            f"📋 Активных броней: {active_bookings}"
        )

    @router.message(Command("set_schedule"))
    async def set_schedule(message: Message) -> None:
        if not is_admin(message):
            await message.answer("Нет доступа.")
            return
        parts = message.text.split(maxsplit=1) if message.text else []
        if len(parts) < 2:
            await message.answer("Формат: /set_schedule [текст]")
            return
        async with session_factory() as session:
            await crud.update_schedule(
                session,
                parts[1],
                (settings.default_schedule, settings.default_contacts),
            )
        await message.answer("График обновлен.")

    @router.message(Command("set_contacts"))
    async def set_contacts(message: Message) -> None:
        if not is_admin(message):
            await message.answer("Нет доступа.")
            return
        parts = message.text.split(maxsplit=1) if message.text else []
        if len(parts) < 2:
            await message.answer("Формат: /set_contacts [текст]")
            return
        async with session_factory() as session:
            await crud.update_contacts(
                session,
                parts[1],
                (settings.default_schedule, settings.default_contacts),
            )
        await message.answer("Контакты обновлены.")

    @router.message(Command("add_promo"))
    async def add_promo(message: Message) -> None:
        if not is_admin(message):
            await message.answer("Нет доступа.")
            return
        if not message.text:
            await message.answer("Формат: /add_promo Заголовок | Описание | [url]")
            return
        body = message.text.replace("/add_promo", "", 1).strip()
        chunks = [part.strip() for part in body.split("|")]
        if len(chunks) < 2:
            await message.answer("Формат: /add_promo Заголовок | Описание | [url]")
            return
        title = chunks[0]
        description = chunks[1]
        image_url = chunks[2] if len(chunks) > 2 and chunks[2] else None
        async with session_factory() as session:
            promo = await crud.add_promotion(session, title, description, image_url)
        await message.answer(f"Акция #{promo.id} добавлена.")

    @router.message(Command("broadcast"))
    async def broadcast_command(message: Message) -> None:
        """Рассылка всем подписчикам."""
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
        from app.db import crud as db_crud
        
        if not is_admin(message):
            await message.answer("Нет доступа.")
            return
        
        # Получаем количество подписчиков
        async with session_factory() as session:
            count = await db_crud.get_subscribers_count(session)
        
        if count == 0:
            await message.answer("❌ Нет активных подписчиков для рассылки.")
            return
        
        await message.answer(
            f"📢 <b>Рассылка подписчикам</b>\n\n"
            f"👥 Активных подписчиков: <b>{count}</b>\n\n"
            f"Отправьте сообщение для рассылки.\n"
            f"Поддерживается текст, фото, видео.\n\n"
            f"❗ Отмена: /cancel",
            parse_mode="HTML"
        )
        
        # Устанавливаем состояние ожидания сообщения
        # (В production лучше использовать FSM)
        await message.answer(
            "💡 <b>Совет:</b> Для отправки фото сначала отправьте фото с подписью,\n"
            f"и оно будет отправлено всем {count} подписчикам.",
            parse_mode="HTML"
        )

    @router.message(Command("subscribers"))
    async def subscribers_command(message: Message) -> None:
        """Показать статистику подписчиков."""
        from app.db import crud as db_crud
        
        if not is_admin(message):
            await message.answer("Нет доступа.")
            return
        
        async with session_factory() as session:
            count = await db_crud.get_subscribers_count(session)
        
        await message.answer(
            f"📊 <b>Статистика подписчиков</b>\n\n"
            f"👥 Активных подписчиков: <b>{count}</b>"
        )

    @router.message(Command("cancel"))
    async def cancel_broadcast(message: Message) -> None:
        """Отменить режим рассылки."""
        if not is_admin(message):
            return
        _broadcast_state.pop(message.from_user.id, None)
        await message.answer("✅ Режим рассылки отменен.")

    # Обработчик сообщений для рассылки (должен быть ПОСЛЕ команд!)
    @router.message(lambda msg: True)
    async def handle_broadcast_message(message: Message) -> None:
        """Обработка сообщения для рассылки."""
        from aiogram import Bot
        from app.db import crud as db_crud

        # Проверяем что это админ
        if not is_admin(message):
            return

        # Проверяем, в режиме ли рассылки админ
        if not _broadcast_state.get(message.from_user.id):
            return

        async with session_factory() as session:
            subscribers = await db_crud.get_active_subscribers(session)

        if not subscribers:
            await message.answer("❌ Нет подписчиков для рассылки.")
            _broadcast_state.pop(message.from_user.id, None)
            return

        bot = Bot(token=settings.bot_token)
        success_count = 0
        fail_count = 0

        # Отправляем сообщение всем подписчикам
        for sub in subscribers:
            try:
                # Копируем сообщение
                await bot.copy_message(
                    chat_id=sub.telegram_id,
                    from_chat_id=message.chat.id,
                    message_id=message.message_id,
                )
                await db_crud.update_last_mailed(session, sub.telegram_id)
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to send to {sub.telegram_id}: {e}")
                fail_count += 1
            await asyncio.sleep(0.05)  # Anti-flood

        await bot.session.close()

        _broadcast_state.pop(message.from_user.id, None)

        await message.answer(
            f"✅ <b>Рассылка завершена!</b>\n\n"
            f"📤 Отправлено: <b>{success_count}</b>\n"
            f"❌ Ошибок: <b>{fail_count}</b>\n"
            f"👥 Всего подписчиков: <b>{len(subscribers)}</b>",
            parse_mode="HTML"
        )

    return router


def register_admin_handlers(session_factory: async_sessionmaker, settings: Settings) -> Router:
    """Alias for create_admin_router for backward compatibility."""
    return create_admin_router(session_factory, settings)
