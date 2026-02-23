from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import Select, and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Booking, BookingStatus, Client, Promotion, Review, VenueSettings


def _is_overlap(
    start_a: datetime,
    duration_a: int,
    start_b: datetime,
    duration_b: int,
) -> bool:
    end_a = start_a + timedelta(minutes=duration_a)
    end_b = start_b + timedelta(minutes=duration_b)
    return start_a < end_b and start_b < end_a


async def get_or_create_client(
    session: AsyncSession,
    telegram_id: int,
    username: str | None,
    full_name: str | None,
    phone: str | None = None,
) -> Client:
    client = await session.scalar(select(Client).where(Client.telegram_id == telegram_id))
    if client:
        if username and client.username != username:
            client.username = username
        if full_name and client.full_name != full_name:
            client.full_name = full_name
        if phone and client.phone_hash != phone:
            client.phone_hash = phone
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


async def create_booking(
    session: AsyncSession,
    client_id: int,
    booking_at: datetime,
    table_no: int,
    guests: int,
    comment: str | None = None,
    duration_minutes: int = 120,
) -> Booking:
    from_time = booking_at - timedelta(hours=4)
    to_time = booking_at + timedelta(hours=4)
    stmt: Select[tuple[Booking]] = select(Booking).where(
        and_(
            Booking.table_no == table_no,
            Booking.booking_at >= from_time,
            Booking.booking_at <= to_time,
            Booking.status.in_(
                [
                    BookingStatus.PENDING.value,
                    BookingStatus.CONFIRMED.value,
                ]
            ),
        )
    )
    existing = (await session.scalars(stmt)).all()
    for item in existing:
        if _is_overlap(booking_at, duration_minutes, item.booking_at, item.duration_minutes):
            raise ValueError("Выбранный столик уже занят на это время")

    booking = Booking(
        client_id=client_id,
        booking_at=booking_at,
        table_no=table_no,
        guests=guests,
        comment=comment,
        duration_minutes=duration_minutes,
    )
    session.add(booking)
    await session.commit()
    await session.refresh(booking)
    return booking


async def get_booking_by_id(session: AsyncSession, booking_id: int) -> Booking | None:
    stmt = (
        select(Booking)
        .options(selectinload(Booking.client))
        .where(Booking.id == booking_id)
    )
    return await session.scalar(stmt)


async def list_user_bookings(session: AsyncSession, client_id: int) -> list[Booking]:
    """Вернуть список броней пользователя, исключая завершенные, отмененные и технические."""
    stmt = (
        select(Booking)
        .where(
            and_(
                Booking.client_id == client_id,
                Booking.status.not_in([BookingStatus.COMPLETED.value, BookingStatus.CANCELED.value]),
                Booking.is_staff_booking.is_(False),  # Не показывать технические брони
            )
        )
        .order_by(desc(Booking.booking_at))
        .limit(20)
    )
    return list((await session.scalars(stmt)).all())


async def list_all_bookings(session: AsyncSession, from_date: date | None = None) -> list[Booking]:
    stmt = select(Booking).order_by(desc(Booking.booking_at)).limit(100)
    if from_date:
        dt = datetime.combine(from_date, datetime.min.time()).replace(tzinfo=None)
        stmt = stmt.where(Booking.booking_at >= dt)
    return list((await session.scalars(stmt)).all())


async def confirm_booking_visit(session: AsyncSession, booking_id: int) -> Booking | None:
    booking = await session.get(Booking, booking_id)
    if not booking:
        return None
    booking.status = BookingStatus.CONFIRMED.value
    await session.commit()
    await session.refresh(booking)
    return booking


async def close_booking(session: AsyncSession, booking_id: int) -> Booking | None:
    """Закрыть бронь - клиент посидел и ушел."""
    booking = await session.get(Booking, booking_id)
    if not booking:
        return None
    booking.status = BookingStatus.COMPLETED.value
    client = await session.get(Client, booking.client_id)
    if client:
        client.visits += 1
    await session.commit()
    await session.refresh(booking)
    return booking


async def cancel_booking(session: AsyncSession, booking_id: int) -> Booking | None:
    """Отменить бронь."""
    booking = await session.get(Booking, booking_id)
    if not booking:
        return None
    booking.status = BookingStatus.CANCELED.value
    await session.commit()
    await session.refresh(booking)
    return booking


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


async def get_bookings_for_reminder(session: AsyncSession) -> list[Booking]:
    now = datetime.utcnow()
    in_one_hour = now + timedelta(hours=1)
    stmt = select(Booking).options(selectinload(Booking.client)).where(
        and_(
            Booking.status.in_([BookingStatus.PENDING.value, BookingStatus.CONFIRMED.value]),
            Booking.reminder_sent.is_(False),
            Booking.booking_at >= now,
            Booking.booking_at <= in_one_hour,
        )
    )
    return list((await session.scalars(stmt)).all())


async def get_client_by_phone(session: AsyncSession, phone: str) -> Client | None:
    """Поиск клиента по номеру телефона."""
    return await session.scalar(select(Client).where(Client.phone_hash == phone))


async def get_client_stats(session: AsyncSession, client_id: int) -> dict:
    """Получить статистику клиента."""
    client = await session.get(Client, client_id)
    if not client:
        return {}
    
    bookings = await session.scalars(
        select(Booking).where(Booking.client_id == client_id)
    )
    bookings_list = bookings.all()
    
    return {
        "total_bookings": len(bookings_list),
        "completed_bookings": len([b for b in bookings_list if b.status == BookingStatus.COMPLETED.value]),
        "canceled_bookings": len([b for b in bookings_list if b.status == BookingStatus.CANCELED.value]),
        "last_visit": max([b.booking_at for b in bookings_list], default=None),
        "favorite_table": max(set([b.table_no for b in bookings_list]), key=[b.table_no for b in bookings_list].count, default=None),
        "visits": client.visits,
        "notes": client.notes,
    }


async def update_client_notes(session: AsyncSession, client_id: int, notes: str) -> Client | None:
    """Обновить заметки о клиенте."""
    client = await session.get(Client, client_id)
    if not client:
        return None
    client.notes = notes
    await session.commit()
    await session.refresh(client)
    return client


async def cancel_booking_by_client(session: AsyncSession, booking_id: int, telegram_id: int) -> Booking | None:
    """Отмена брони гостем (без ограничений по времени)."""
    from datetime import UTC

    stmt = select(Booking).options(selectinload(Booking.client)).where(Booking.id == booking_id)
    booking = await session.scalar(stmt)

    if not booking:
        return None

    # Проверяем, что это бронь клиента
    if booking.client.telegram_id != telegram_id:
        return None

    # Отменяем бронь (без ограничений по времени)
    booking.status = BookingStatus.CANCELED.value
    await session.commit()
    await session.refresh(booking)
    return booking


async def get_today_stats(session: AsyncSession) -> dict:
    """Получить статистику за сегодня."""
    from datetime import UTC
    now = datetime.now(tz=UTC).replace(tzinfo=None)
    today_start = datetime.combine(now.date(), datetime.min.time())
    today_end = datetime.combine(now.date(), datetime.max.time())
    
    # Все брони на сегодня
    stmt = select(Booking).where(
        and_(
            Booking.booking_at >= today_start,
            Booking.booking_at <= today_end,
        )
    )
    bookings = (await session.scalars(stmt)).all()
    
    # Сейчас в заведении (confirmed и booking_at < now)
    now_in_restaurant = len([
        b for b in bookings 
        if b.status == BookingStatus.CONFIRMED.value and b.booking_at <= now
    ])
    
    # Ожидают (pending)
    expecting = len([b for b in bookings if b.status == BookingStatus.PENDING.value])
    
    # Свободные столы (всего 8)
    busy_tables = set([b.table_no for b in bookings if b.status in [BookingStatus.CONFIRMED.value, BookingStatus.PENDING.value]])
    free_tables = 8 - len(busy_tables)
    
    return {
        "total_bookings": len(bookings),
        "now_in_restaurant": now_in_restaurant,
        "expecting": expecting,
        "free_tables": max(0, free_tables),
        "busy_tables": list(busy_tables),
    }
