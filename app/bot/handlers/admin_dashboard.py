from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import Settings
from app.db import crud
from app.db.models import BookingStatus

router = Router(name="admin_dashboard")


def register_admin_dashboard(session_factory: async_sessionmaker, settings: Settings) -> Router:
    @router.message(Command("dashboard"))
    async def dashboard(message: Message) -> None:
        """Дашборд администратора."""
        if not message.from_user or message.from_user.id not in settings.admin_ids:
            await message.answer("Нет доступа.")
            return
        
        async with session_factory() as session:
            stats = await crud.get_today_stats(session)
        
        # Формируем визуальную карту столов
        tables_visual = []
        for table_no in range(1, 9):
            if table_no in stats.get("busy_tables", []):
                tables_visual.append(f"{table_no} 🔴")
            else:
                tables_visual.append(f"{table_no} 🟢")
        
        tables_text = " | ".join(tables_visual)
        
        await message.answer(
            f"📊 <b>Дашборд за сегодня</b>\n\n"
            f"📅 Всего броней: <b>{stats['total_bookings']}</b>\n"
            f"👥 Сейчас в заведении: <b>{stats['now_in_restaurant']}</b>\n"
            f"⏳ Ожидают: <b>{stats['expecting']}</b>\n"
            f"🪑 Свободных столов: <b>{stats['free_tables']}</b>\n\n"
            f"<b>Карта столов:</b>\n{tables_text}\n\n"
            f"🟢 — свободно | 🔴 — занято",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🔄 Обновить",
                            callback_data="dashboard_refresh"
                        )
                    ]
                ]
            )
        )

    @router.callback_query(F.data == "dashboard_refresh")
    async def refresh_dashboard(callback: CallbackQuery) -> None:
        """Обновить дашборд."""
        if not callback.from_user or callback.from_user.id not in settings.admin_ids:
            await callback.answer("Нет доступа.", show_alert=True)
            return
        
        async with session_factory() as session:
            stats = await crud.get_today_stats(session)
        
        tables_visual = []
        for table_no in range(1, 9):
            if table_no in stats.get("busy_tables", []):
                tables_visual.append(f"{table_no} 🔴")
            else:
                tables_visual.append(f"{table_no} 🟢")
        
        tables_text = " | ".join(tables_visual)
        
        try:
            await callback.message.edit_text(
                f"📊 <b>Дашборд за сегодня</b>\n\n"
                f"📅 Всего броней: <b>{stats['total_bookings']}</b>\n"
                f"👥 Сейчас в заведении: <b>{stats['now_in_restaurant']}</b>\n"
                f"⏳ Ожидают: <b>{stats['expecting']}</b>\n"
                f"🪑 Свободных столов: <b>{stats['free_tables']}</b>\n\n"
                f"<b>Карта столов:</b>\n{tables_text}\n\n"
                f"🟢 — свободно | 🔴 — занято",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="🔄 Обновить",
                                callback_data="dashboard_refresh"
                            )
                        ]
                    ]
                )
            )
        except Exception:
            pass
        
        await callback.answer("Обновлено!")

    @router.message(Command("find_client"))
    async def find_client(message: Message) -> None:
        """Поиск клиента по телефону."""
        if not message.from_user or message.from_user.id not in settings.admin_ids:
            await message.answer("Нет доступа.")
            return
        
        # Получаем аргумент команды
        args = message.text.split(maxsplit=1) if message.text else []
        if len(args) < 2:
            await message.answer(
                "📍 Формат: /find_client [телефон]\n"
                "Пример: /find_client +79991234567"
            )
            return
        
        phone = args[1].strip()
        
        async with session_factory() as session:
            client = await crud.get_client_by_phone(session, phone)
            
            if not client:
                await message.answer(f"❌ Клиент с номером {phone} не найден.")
                return
            
            stats = await crud.get_client_stats(session, client.id)
        
        # Формируем ответ
        response = (
            f"👤 <b>Информация о клиенте</b>\n\n"
            f"🆔 ID: {client.telegram_id or '—'}\n"
            f"👤 Имя: {client.full_name or '—'}\n"
            f"📝 Username: @{client.username or 'нет'}\n"
            f"📞 Телефон: {phone}\n"
            f"💎 Визитов: {stats.get('visits', 0)}\n"
            f"📋 Всего броней: {stats.get('total_bookings', 0)}\n"
            f"✅ Завершено: {stats.get('completed_bookings', 0)}\n"
            f"❌ Отменено: {stats.get('canceled_bookings', 0)}\n"
        )
        
        if stats.get('favorite_table'):
            response += f"🪑 Любимый стол: {stats['favorite_table']}\n"
        
        if stats.get('last_visit'):
            response += f"🕐 Последний визит: {stats['last_visit']:%d.%m.%Y %H:%M}\n"
        
        if stats.get('notes'):
            response += f"\n📝 <b>Заметки:</b>\n{stats['notes']}"
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📝 Добавить заметку",
                        callback_data=f"client_notes_{client.id}"
                    )
                ]
            ]
        )
        
        await message.answer(response, reply_markup=keyboard)

    @router.callback_query(F.data.startswith("client_notes_"))
    async def client_notes_callback(callback: CallbackQuery) -> None:
        """Добавить заметку о клиенте."""
        if not callback.from_user or callback.from_user.id not in settings.admin_ids:
            await callback.answer("Нет доступа.", show_alert=True)
            return
        
        try:
            client_id = int(callback.data.split("_")[-1])
        except (ValueError, IndexError):
            await callback.answer("Ошибка", show_alert=True)
            return
        
        await callback.message.answer(
            "📝 Отправьте заметку о клиенте.\n"
            "Пример: 'Любит стол у окна, аллергик'"
        )
        
        # Устанавливаем состояние для заметки (нужно добавить FSM)
        await callback.answer("Теперь отправьте текст заметки следующим сообщением")

    return router
