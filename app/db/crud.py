from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Client, DynamicAdmin, Promotion, Review, Subscriber, VenueSettings


async def get_or_create_client(
    session: AsyncSession,
    telegram_id: int,
    username: str | None,
    full_name: str | None,
    phone: str | None = None,
) -> Client:
    client = await session.scalar(select(Client).where(Client.telegram_id == telegram_id))
    if client:
        # Обновляем данные только если они изменились
        updated = False
        if username and client.username != username:
            client.username = username
            updated = True
        if full_name and client.full_name != full_name:
            client.full_name = full_name
            updated = True
        if phone and client.phone_hash != phone:
            client.phone_hash = phone
            updated = True
        if updated:
            await session.commit()
        return client

    client = Client(
        telegram_id=telegram_id,
        username=username,
        full_name=full_name,
        phone_hash=phone,
    )
    session.add(client)
    await session.commit()
    await session.refresh(client)
    return client


async def get_client_by_telegram_id(session: AsyncSession, telegram_id: int) -> Client | None:
    return await session.scalar(select(Client).where(Client.telegram_id == telegram_id))


async def get_active_promotions(session: AsyncSession) -> list[Promotion]:
    stmt = (
        select(Promotion)
        .where(Promotion.is_active.is_(True))
        .order_by(desc(Promotion.created_at))
        .limit(10)
    )
    return list((await session.scalars(stmt)).all())


async def add_promotion(
    session: AsyncSession,
    title: str,
    description: str,
    image_url: str | None = None,
) -> Promotion:
    promo = Promotion(title=title, description=description, image_url=image_url)
    session.add(promo)
    await session.commit()
    await session.refresh(promo)
    return promo


async def get_venue_settings(
    session: AsyncSession,
    default_schedule: str,
    default_contacts: str,
) -> VenueSettings:
    settings = await session.get(VenueSettings, 1)
    if settings:
        return settings

    settings = VenueSettings(
        id=1,
        schedule_text=default_schedule,
        contacts_text=default_contacts,
    )
    session.add(settings)
    await session.commit()
    await session.refresh(settings)
    return settings


async def update_schedule(session: AsyncSession, text: str, defaults: tuple[str, str]) -> VenueSettings:
    settings = await get_venue_settings(session, defaults[0], defaults[1])
    settings.schedule_text = text
    settings.updated_at = datetime.now(tz=UTC).replace(tzinfo=None)
    await session.commit()
    await session.refresh(settings)
    return settings


async def update_contacts(session: AsyncSession, text: str, defaults: tuple[str, str]) -> VenueSettings:
    settings = await get_venue_settings(session, defaults[0], defaults[1])
    settings.contacts_text = text
    settings.updated_at = datetime.now(tz=UTC).replace(tzinfo=None)
    await session.commit()
    await session.refresh(settings)
    return settings


async def create_review(
    session: AsyncSession,
    client_id: int,
    rating: int,
    text: str,
) -> Review:
    review = Review(client_id=client_id, rating=rating, text=text)
    session.add(review)
    await session.commit()
    await session.refresh(review)
    return review


async def get_client_by_phone(session: AsyncSession, phone: str) -> Client | None:
    """Поиск клиента по номеру телефона."""
    return await session.scalar(select(Client).where(Client.phone_hash == phone))


async def update_client_notes(session: AsyncSession, client_id: int, notes: str) -> Client | None:
    """Обновить заметки о клиенте."""
    client = await session.get(Client, client_id)
    if not client:
        return None
    client.notes = notes
    await session.commit()
    await session.refresh(client)
    return client


# ==================== SUBSCRIBERS ====================

async def add_subscriber(
    session: AsyncSession,
    telegram_id: int,
    username: str | None = None,
    full_name: str | None = None,
) -> Subscriber:
    """Добавить подписчика или обновить существующего."""
    subscriber = await session.scalar(select(Subscriber).where(Subscriber.telegram_id == telegram_id))
    if subscriber:
        if not subscriber.is_active:
            subscriber.is_active = True
            await session.commit()
        return subscriber

    subscriber = Subscriber(
        telegram_id=telegram_id,
        username=username,
        full_name=full_name,
    )
    session.add(subscriber)
    await session.commit()
    await session.refresh(subscriber)
    return subscriber


async def remove_subscriber(session: AsyncSession, telegram_id: int) -> bool:
    """Отписать пользователя."""
    subscriber = await session.scalar(select(Subscriber).where(Subscriber.telegram_id == telegram_id))
    if not subscriber:
        return False
    subscriber.is_active = False
    await session.commit()
    return True


async def get_active_subscribers(session: AsyncSession) -> list[Subscriber]:
    """Получить всех активных подписчиков."""
    stmt = select(Subscriber).where(Subscriber.is_active.is_(True)).order_by(Subscriber.subscribed_at)
    return list((await session.scalars(stmt)).all())


async def get_subscribers_count(session: AsyncSession) -> int:
    """Получить количество активных подписчиков."""
    stmt = select(func.count()).where(Subscriber.is_active.is_(True))
    return (await session.execute(stmt)).scalar() or 0


async def update_last_mailed(session: AsyncSession, telegram_id: int) -> None:
    """Обновить время последней рассылки."""
    await session.execute(
        update(Subscriber)
        .where(Subscriber.telegram_id == telegram_id)
        .values(last_mailed_at=datetime.now(tz=UTC).replace(tzinfo=None))
    )
    await session.commit()


# ==================== DYNAMIC ADMINS ====================

async def add_dynamic_admin(session: AsyncSession, telegram_id: int) -> DynamicAdmin | None:
    """Добавить админа по ID. Возвращает запись или None если уже есть."""
    existing = await session.scalar(select(DynamicAdmin).where(DynamicAdmin.telegram_id == telegram_id))
    if existing:
        return None
    admin = DynamicAdmin(telegram_id=telegram_id)
    session.add(admin)
    await session.commit()
    await session.refresh(admin)
    return admin


async def remove_dynamic_admin(session: AsyncSession, telegram_id: int) -> bool:
    """Удалить админа по ID. Возвращает True если удалён."""
    admin = await session.scalar(select(DynamicAdmin).where(DynamicAdmin.telegram_id == telegram_id))
    if not admin:
        return False
    await session.delete(admin)
    await session.commit()
    return True


async def get_dynamic_admin_ids(session: AsyncSession) -> list[int]:
    """Список telegram_id выданных админов."""
    stmt = select(DynamicAdmin.telegram_id)
    return list((await session.scalars(stmt)).all())
