"""Динамические ID админов (выданные через /add_admin). Объединяются с ADMIN_IDS из .env."""
from __future__ import annotations

from app.config import Settings

# Кэш ID, выданных через /add_admin (загружается при старте, обновляется при add/remove)
_dynamic_admin_ids: set[int] = set()


def get_all_admin_ids(settings: Settings) -> set[int]:
    """Все админы: из .env + выданные командой."""
    return settings.admin_ids | _dynamic_admin_ids


def set_dynamic_admin_ids(ids: set[int]) -> None:
    """Загрузить список динамических админов (при старте приложения)."""
    global _dynamic_admin_ids
    _dynamic_admin_ids = set(ids)


def add_dynamic_admin_id(telegram_id: int) -> None:
    """Добавить ID в кэш после записи в БД."""
    _dynamic_admin_ids.add(telegram_id)


def remove_dynamic_admin_id(telegram_id: int) -> None:
    """Убрать ID из кэша после удаления из БД."""
    _dynamic_admin_ids.discard(telegram_id)
