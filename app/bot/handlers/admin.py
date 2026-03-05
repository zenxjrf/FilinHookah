from __future__ import annotations

import logging
from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.admin_ids import get_all_admin_ids
from app.config import Settings
from app.db import crud

# Состояние для рассылки
_broadcast_state: dict[int, bool] = {}
logger = logging.getLogger(__name__)


def create_admin_router(session_factory: async_sessionmaker, settings: Settings) -> Router:
    router = Router(name="admin")

    def is_admin(message: Message) -> bool:
        return bool(message.from_user and message.from_user.id in get_all_admin_ids(settings))

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
                    f"Ваш telegram_id: <code>{message.from_user.id}</code>\n"
                    "Попросите админа: /add_admin " + str(message.from_user.id),
                    parse_mode="HTML",
                )
            else:
                await message.answer("Нет доступа.")
            return
        await message.answer(
            "Админ-команды:\n"
            "/add_admin [id] — выдать админку по Telegram ID\n"
            "/remove_admin [id] — забрать админку\n"
            "/list_admins — список админов (из .env + выданные)\n"
            "/check_client [id] - информация о клиенте\n"
            "/add_visits [id] [кол-во] - добавить визиты\n"
            "/reset_visits [id] - сбросить визиты\n"
            "/set_schedule [текст]\n"
            "/set_contacts [текст]\n"
            "/add_promo [заголовок] | [описание] | [url]\n"
            "/broadcast - рассылка подписчикам\n"
            "/subscribers - статистика подписчиков"
        )

    @router.message(F.text.regexp(r"^/admin(@\w+)?$"))
    async def admin_panel_fallback(message: Message) -> None:
        await admin_panel(message)

    @router.message(Command("add_admin"))
    async def add_admin_cmd(message: Message) -> None:
        """Выдать админку по Telegram ID. Только для текущих админов."""
        if not is_admin(message):
            await message.answer("Нет доступа.")
            return
        if not message.text:
            await message.answer("Формат: /add_admin [telegram_id]\nПример: /add_admin 123456789")
            return
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.answer("Формат: /add_admin [telegram_id]")
            return
        try:
            telegram_id = int(parts[1].strip())
        except ValueError:
            await message.answer("ID должен быть числом.")
            return
        from app.admin_ids import add_dynamic_admin_id
        async with session_factory() as session:
            added = await crud.add_dynamic_admin(session, telegram_id)
        if added:
            add_dynamic_admin_id(telegram_id)
            await message.answer(f"✅ Админка выдана пользователю <code>{telegram_id}</code>.", parse_mode="HTML")
        else:
            await message.answer(f"ℹ️ Пользователь <code>{telegram_id}</code> уже является админом.", parse_mode="HTML")

    @router.message(Command("remove_admin"))
    async def remove_admin_cmd(message: Message) -> None:
        """Забрать админку (только у выданных через /add_admin)."""
        if not is_admin(message):
            await message.answer("Нет доступа.")
            return
        if not message.text:
            await message.answer("Формат: /remove_admin [telegram_id]")
            return
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.answer("Формат: /remove_admin [telegram_id]")
            return
        try:
            telegram_id = int(parts[1].strip())
        except ValueError:
            await message.answer("ID должен быть числом.")
            return
        if telegram_id in settings.admin_ids:
            await message.answer("❌ Нельзя забрать админку у ID из ADMIN_IDS (.env). Удалите его из переменных и перезапустите.")
            return
        from app.admin_ids import remove_dynamic_admin_id
        async with session_factory() as session:
            removed = await crud.remove_dynamic_admin(session, telegram_id)
        if removed:
            remove_dynamic_admin_id(telegram_id)
            await message.answer(f"✅ Админка снята с пользователя <code>{telegram_id}</code>.", parse_mode="HTML")
        else:
            await message.answer(f"ℹ️ Пользователь <code>{telegram_id}</code> не был в списке выданных админов.", parse_mode="HTML")

    @router.message(Command("list_admins"))
    async def list_admins_cmd(message: Message) -> None:
        """Показать список админов: из .env и выданные командой."""
        if not is_admin(message):
            await message.answer("Нет доступа.")
            return
        from app.admin_ids import get_all_admin_ids
        env_ids = sorted(settings.admin_ids)
        async with session_factory() as session:
            dynamic_ids = await crud.get_dynamic_admin_ids(session)
        dynamic_set = set(dynamic_ids)
        lines = ["📋 <b>Админы из .env (ADMIN_IDS):</b>"]
        if env_ids:
            lines.append(", ".join(str(i) for i in env_ids))
        else:
            lines.append("—")
        lines.append("\n📋 <b>Выданные через /add_admin:</b>")
        if dynamic_ids:
            lines.append(", ".join(str(i) for i in sorted(dynamic_ids)))
        else:
            lines.append("—")
        lines.append(f"\n<b>Всего уникальных админов:</b> {len(get_all_admin_ids(settings))}")
        await message.answer("\n".join(lines), parse_mode="HTML")

    @router.message(Command("check_client"))
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

        bonus_status = "🏆 БЕСПЛАТНЫЙ" if client.visits >= 10 else "🔥 50% скидка" if client.visits >= 5 else f"⏳ До бонуса: {5 - client.visits if client.visits < 5 else 10 - client.visits}"

        await message.answer(
            f"👤 <b>Информация о клиенте</b>\n\n"
            f"🆔 ID: {client.telegram_id}\n"
            f"👤 Имя: {client.full_name or '—'}\n"
            f"📝 Username: @{client.username or 'нет'}\n"
            f"💎 Визитов: {client.visits}\n"
            f"🎁 Статус: {bonus_status}"
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
        
        # Включаем режим рассылки: следующее сообщение от этого админа пойдёт подписчикам
        _broadcast_state[message.from_user.id] = True

        await message.answer(
            f"📢 <b>Рассылка подписчикам</b>\n\n"
            f"👥 Активных подписчиков: <b>{count}</b>\n\n"
            f"Отправьте сообщение для рассылки.\n"
            f"Поддерживается текст, фото, видео.\n\n"
            f"❗ Отмена: /cancel",
            parse_mode="HTML"
        )
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
