from __future__ import annotations

from datetime import datetime
from pathlib import Path

print(">>> BUILD 999 LOADED <<<", flush=True)

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from app.config import get_settings
from app.db import crud
from app.db.base import get_session
from app.db.models import Booking, BookingStatus

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Filin WebApp v2")

# CORS для Telegram WebApp
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

settings = get_settings()


# ==================== PYDANTIC MODEELS ====================

class CreateBookingRequest(BaseModel):
    telegram_id: int = Field(ge=1)
    full_name: str | None = None
    username: str | None = None
    phone: str = Field(..., pattern=r"^\+7\d{10}$")
    date_time: datetime
    table_no: int = Field(ge=1, le=30)
    guests: int = Field(ge=1, le=20)
    comment: str | None = None


class CreateReviewRequest(BaseModel):
    telegram_id: int = Field(ge=1)
    rating: int = Field(ge=1, le=5)
    text: str = Field(min_length=3, max_length=2000)


class CancelBookingRequest(BaseModel):
    telegram_id: int = Field(ge=1)


class BookTableRequest(BaseModel):
    table_no: int = Field(ge=1, le=8)
    datetime: str
    guests: int = Field(default=2, ge=1, le=20)


class OccupyTableRequest(BaseModel):
    table_no: int = Field(ge=1, le=8)


class FreeTableRequest(BaseModel):
    close_all: bool = False


class BlockTableRequest(BaseModel):
    table_no: int = Field(ge=1, le=8)
    datetime: str


class UpdateBookingStatusRequest(BaseModel):
    status: str = Field(..., pattern=r"^(pending|confirmed|completed|canceled)$")


class CreateEventRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    datetime: datetime
    description: str | None = None


class UpdateEventRequest(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    description: str | None = None


class SetDiscountRequest(BaseModel):
    discount: int = Field(ge=0, le=100000)


class CreateBookingRequest(BaseModel):
    telegram_id: int
    full_name: str | None = None
    username: str | None = None
    phone: str | None = Field(default=None, pattern=r"^\+7\d{10}$")
    date_time: datetime
    table_no: int = Field(ge=1, le=30)
    guests: int = Field(ge=1, le=20)
    comment: str | None = None


class CreateReviewRequest(BaseModel):
    telegram_id: int
    rating: int = Field(ge=1, le=5)
    text: str = Field(min_length=3, max_length=2000)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint for health check."""
    return {"status": "ok", "service": "Filin Hookah Bot"}


@app.get("/index", response_class=HTMLResponse)
async def webapp_index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={},
    )


@app.get("/api/availability")
async def availability(
    date_str: str = Query(alias="date"),
    table_no: int = Query(ge=1, le=30),
    session: AsyncSession = Depends(get_session),
) -> dict[str, list[str]]:
    try:
        day = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid date format") from exc

    from_time = datetime.combine(day, datetime.min.time())
    to_time = datetime.combine(day, datetime.max.time())
    stmt = select(Booking).where(
        and_(
            Booking.table_no == table_no,
            Booking.booking_at >= from_time,
            Booking.booking_at <= to_time,
            Booking.status.in_([BookingStatus.PENDING.value, BookingStatus.CONFIRMED.value]),
        )
    )
    items = (await session.scalars(stmt)).all()
    busy_slots = [item.booking_at.strftime("%H:%M") for item in items]
    return {"busy_slots": busy_slots}


@app.get("/api/tables_status")
async def tables_status(
    date_str: str = Query(alias="date"),
    session: AsyncSession = Depends(get_session),
) -> dict[str, list[dict]]:
    """Получить статус всех столов на дату."""
    try:
        day = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid date format") from exc

    from_time = datetime.combine(day, datetime.min.time())
    to_time = datetime.combine(day, datetime.max.time())
    
    stmt = select(Booking).where(
        and_(
            Booking.booking_at >= from_time,
            Booking.booking_at <= to_time,
            Booking.status.in_([BookingStatus.PENDING.value, BookingStatus.CONFIRMED.value]),
        )
    )
    items = (await session.scalars(stmt)).all()
    
    # Группируем по столам
    tables = {}
    for item in items:
        if item.table_no not in tables:
            tables[item.table_no] = []
        tables[item.table_no].append({
            "time": item.booking_at.strftime("%H:%M"),
            "is_staff": item.is_staff_booking,
        })
    
    return {"tables": tables}


@app.post("/api/bookings")
async def create_booking(
    payload: CreateBookingRequest,
    session: AsyncSession = Depends(get_session),
) -> dict[str, int | str]:
    import logging
    from aiogram import Bot
    
    client = await crud.get_or_create_client(
        session,
        telegram_id=payload.telegram_id,
        username=payload.username,
        full_name=payload.full_name,
        phone=payload.phone,
    )
    try:
        booking = await crud.create_booking(
            session=session,
            client_id=client.id,
            booking_at=payload.date_time,
            table_no=payload.table_no,
            guests=payload.guests,
            comment=payload.comment,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Отправляем уведомление в чат работников
    try:
        from aiogram import Bot
        bot = Bot(token=settings.bot_token)

        admin_text = (
            f"🔔 <b>Новая бронь #{booking.id}</b>\n\n"
            f"👤 Клиент: {payload.full_name or '—'} (@{payload.username or 'нет'})\n"
            f"📞 Телефон: {payload.phone or '—'}\n"
            f"🆔 Telegram ID: {payload.telegram_id}\n"
            f"💎 Визитов: {client.visits}\n"
            f"📅 Дата: {booking.booking_at:%d.%m.%Y %H:%M}\n"
            f"🪑 Стол: {booking.table_no}, гостей: {booking.guests}\n"
            f"📝 Комментарий: {payload.comment or '—'}\n\n"
            f"<b>Статус:</b> Ожидает подтверждения ⏳"
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"booking_confirm_{booking.id}"),
                    InlineKeyboardButton(text="❌ Отменить", callback_data=f"booking_cancel_{booking.id}"),
                ],
                [
                    InlineKeyboardButton(text="🟢 Закрыть", callback_data=f"booking_close_{booking.id}"),
                ],
            ]
        )

        if settings.workers_chat_id:
            await bot.send_message(
                settings.workers_chat_id,
                admin_text,
                reply_markup=keyboard,
            )
        else:
            for admin_id in settings.admin_ids:
                await bot.send_message(
                    admin_id,
                    admin_text,
                    reply_markup=keyboard,
                )

        await bot.session.close()
    except Exception as e:
        print(f"ERROR sending notification: {e}")
        # Не прерываем создание брони если уведомление не отправилось

    return {
        "id": booking.id,
        "status": booking.status,
    }


@app.get("/api/bootstrap")
async def bootstrap(
    telegram_id: int = Query(ge=1),
    username: str | None = Query(default=None),
    full_name: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    client = await crud.get_or_create_client(
        session=session,
        telegram_id=telegram_id,
        username=username,
        full_name=full_name,
    )
    venue = await crud.get_venue_settings(
        session=session,
        default_schedule="Ежедневно с 14:00 до 2:00",
        default_contacts="📞 7-950-433-34-34\n🌙 Твой идеальный вечер",
    )
    promotions = await crud.get_active_promotions(session)
    
    # Всегда показываем акцию "Кальян до 18:00" первой
    default_promo = {
        "id": 0,
        "title": "☀️ Кальян до 18:00",
        "description": "1000 рублей",
        "image_url": None,
        "is_default": True
    }
    
    # Добавляем другие акции
    other_promos = [
        {"id": p.id, "title": p.title, "description": p.description, "image_url": p.image_url, "is_default": False}
        for p in promotions
    ]
    
    promo_payload = [default_promo] + other_promos
    bookings = await crud.list_user_bookings(session, client.id)
    
    # Маппинг статусов на русские названия
    status_map = {
        "pending": "Ожидает подтверждения",
        "confirmed": "Бронь подтверждена",
        "completed": "Выполнена",
        "canceled": "Отменена",
    }

    return {
        "schedule": "Ежедневно с 14:00 до 2:00",
        "contacts": venue.contacts_text,
        "visits": client.visits,
        "notes": client.notes,  # Возвращаем notes для личной скидки
        "promotions": promo_payload,
        "bookings": [
            {
                "id": b.id,
                "booking_at": b.booking_at.isoformat(),
                "created_at": b.created_at.isoformat(),
                "table_no": b.table_no,
                "guests": b.guests,
                "status": status_map.get(b.status, b.status),
            }
            for b in bookings
        ],
        "menu": [
            {"title": "Классический кальян", "description": "1200 рублей"},
            {"title": "Напитки и пиво", "description": "С бара по 200 рублей"},
        ],
        "loyalty_rule": "При заказе 5-го кальяна - скидка 50%, при заказе 10-го - бесплатно.",
    }


@app.post("/api/reviews")
async def create_review(
    payload: CreateReviewRequest,
    session: AsyncSession = Depends(get_session),
) -> dict[str, int]:
    client = await crud.get_client_by_telegram_id(session, payload.telegram_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    review = await crud.create_review(session, client.id, payload.rating, payload.text)
    return {"id": review.id}


@app.post("/api/bookings/{booking_id}/cancel")
async def cancel_booking(
    booking_id: int,
    payload: dict,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """Отмена брони гостем."""
    telegram_id = payload.get("telegram_id")
    if not telegram_id:
        raise HTTPException(status_code=400, detail="Telegram ID required")
    
    try:
        booking = await crud.cancel_booking_by_client(session, booking_id, telegram_id)
        if not booking:
            raise HTTPException(status_code=404, detail="Бронь не найдена")
        return {"status": "canceled", "message": "Бронь отменена"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== ADMIN API ====================

@app.get("/api/admin/stats")
async def admin_stats(session: AsyncSession = Depends(get_session)):
    """Статистика для дашборда."""
    stats = await crud.get_today_stats(session)
    return stats


@app.get("/api/admin/tables")
async def admin_tables(
    date: str = Query(...),
    session: AsyncSession = Depends(get_session),
):
    """Статус всех столов на дату."""
    from datetime import datetime
    from sqlalchemy import select, and_
    from app.db.models import Booking, BookingStatus
    
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    from_time = datetime.combine(target_date, datetime.min.time())
    to_time = datetime.combine(target_date, datetime.max.time())
    
    stmt = select(Booking).where(
        and_(
            Booking.booking_at >= from_time,
            Booking.booking_at <= to_time,
        )
    )
    bookings = (await session.scalars(stmt)).all()
    
    tables = {}
    now = datetime.utcnow()
    
    for booking in bookings:
        if booking.table_no not in tables:
            tables[booking.table_no] = []
        
        # Определяем статус брони
        is_occupied = booking.status == BookingStatus.CONFIRMED.value and booking.booking_at <= now
        is_blocked = booking.is_staff_booking and booking.status == BookingStatus.CANCELED.value
        
        tables[booking.table_no].append({
            "id": booking.id,
            "booking_at": booking.booking_at.isoformat(),
            "status": booking.status,  # pending, confirmed, completed, canceled
            "is_occupied": is_occupied,
            "is_blocked": is_blocked
        })
    
    return {"tables": tables}


@app.get("/api/admin/bookings")
async def admin_bookings(
    date: str = Query(...),
    session: AsyncSession = Depends(get_session),
):
    """Список броней на дату."""
    from datetime import datetime
    from sqlalchemy import select, and_, desc
    from sqlalchemy.orm import selectinload
    from app.db.models import Booking, Client
    
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    from_time = datetime.combine(target_date, datetime.min.time())
    to_time = datetime.combine(target_date, datetime.max.time())
    
    stmt = (
        select(Booking)
        .options(selectinload(Booking.client))
        .where(
            and_(
                Booking.booking_at >= from_time,
                Booking.booking_at <= to_time,
            )
        )
        .order_by(desc(Booking.booking_at))
    )
    bookings = (await session.scalars(stmt)).all()
    
    return [
        {
            "id": b.id,
            "booking_at": b.booking_at.isoformat(),
            "table_no": b.table_no,
            "guests": b.guests,
            "status": b.status,
            "client_name": b.client.full_name if b.client else None,
        }
        for b in bookings
    ]


@app.post("/api/admin/bookings/{booking_id}/status")
async def update_booking_status(
    booking_id: int,
    payload: dict,
    session: AsyncSession = Depends(get_session),
):
    """Обновление статуса брони."""
    from app.db import crud as db_crud
    
    status = payload.get("status")
    if not status:
        raise HTTPException(status_code=400, detail="Status required")
    
    booking = await session.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Бронь не найдена")
    
    booking.status = status
    await session.commit()
    
    return {"status": "ok"}


@app.get("/api/admin/events")
async def get_events(session: AsyncSession = Depends(get_session)):
    """Получить список событий."""
    from sqlalchemy import select, desc
    from app.db.models import Promotion
    
    stmt = select(Promotion).order_by(desc(Promotion.created_at)).limit(20)
    events = (await session.scalars(stmt)).all()
    
    return [
        {
            "id": e.id,
            "title": e.title,
            "description": e.description,
            "datetime": e.created_at.isoformat(),
        }
        for e in events
    ]


@app.post("/api/admin/events")
async def create_event(
    payload: dict,
    session: AsyncSession = Depends(get_session),
):
    """Создать событие."""
    from app.db.models import Promotion
    
    event = Promotion(
        title=payload.get("title", "Событие"),
        description=payload.get("description", ""),
        is_active=True,
    )
    
    session.add(event)
    await session.commit()
    await session.refresh(event)
    
    return {"id": event.id, "status": "created"}


@app.put("/api/admin/events/{event_id}")
async def update_event(
    event_id: int,
    payload: dict,
    session: AsyncSession = Depends(get_session),
):
    """Редактировать событие."""
    from app.db.models import Promotion
    
    event = await session.get(Promotion, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Событие не найдено")
    
    event.title = payload.get("title", event.title)
    event.description = payload.get("description", event.description)
    
    await session.commit()
    
    return {"id": event.id, "status": "updated"}


@app.delete("/api/admin/events/{event_id}")
async def delete_event(
    event_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Удалить событие."""
    from app.db.models import Promotion
    
    event = await session.get(Promotion, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Событие не найдено")
    
    await session.delete(event)
    await session.commit()
    
    return {"status": "deleted"}


@app.get("/api/admin/guests")
async def get_guests(session: AsyncSession = Depends(get_session)):
    """Получить список гостей."""
    from sqlalchemy import select, desc
    from app.db.models import Client
    
    stmt = select(Client).order_by(desc(Client.visits)).limit(100)
    guests = (await session.scalars(stmt)).all()
    
    return [
        {
            "id": g.id,
            "name": g.full_name,
            "phone": g.phone_hash,
            "visits": g.visits,
        }
        for g in guests
    ]


@app.get("/api/admin/guests/{client_id}/notes")
async def update_guest_notes(
    client_id: int,
    payload: dict,
    session: AsyncSession = Depends(get_session),
):
    """Обновить заметку о госте."""
    from app.db.models import Client
    
    client = await session.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    
    client.notes = payload.get("notes", "")
    await session.commit()
    
    return {"status": "ok"}


@app.get("/admin")
async def admin_panel():
    """Админ-панель."""
    return templates.TemplateResponse("admin.html", {"request": {}})


@app.post("/api/admin/tables/block")
async def block_table(
    payload: dict,
    session: AsyncSession = Depends(get_session),
):
    """Заблокировать стол."""
    from app.db.models import Booking, Client
    
    table_no = payload.get("table_no")
    datetime_str = payload.get("datetime")
    
    if not table_no or not datetime_str:
        raise HTTPException(status_code=400, detail="table_no and datetime required")
    
    from datetime import datetime
    try:
        booking_at = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid datetime format")
    
    # Создаём технического клиента
    client = await session.scalar(
        select(Client).where(Client.telegram_id == 999999999)
    )
    if not client:
        client = Client(
            telegram_id=999999999,
            username="staff_block",
            full_name="Техническая бронь",
        )
        session.add(client)
        await session.flush()
    
    # Создаём бронь-заглушку
    booking = Booking(
        client_id=client.id,
        booking_at=booking_at,
        table_no=table_no,
        guests=0,
        comment="СТОЛ ЗАБЛОКИРОВАН ПЕРСОНАЛОМ",
        status="canceled",  # Отменённая бронь блокирует стол
        is_staff_booking=True,
    )
    
    session.add(booking)
    await session.commit()
    
    return {"status": "blocked", "table_no": table_no}


@app.post("/api/admin/tables/{table_no}/unblock")
async def unblock_table(
    table_no: int,
    session: AsyncSession = Depends(get_session),
):
    """Освободить стол (удалить блокировки)."""
    from app.db.models import Booking
    
    # Находим все блокировки этого стола
    stmt = select(Booking).where(
        and_(
            Booking.table_no == table_no,
            Booking.is_staff_booking == True,
            Booking.status == "canceled",
        )
    )
    bookings = (await session.scalars(stmt)).all()
    
    for booking in bookings:
        await session.delete(booking)
    
    await session.commit()
    
    return {"status": "unblocked", "table_no": table_no}


@app.post("/api/admin/guests/{client_id}/discount")
async def set_guest_discount(
    client_id: int,
    payload: dict,
    session: AsyncSession = Depends(get_session),
):
    """Установить личную скидку гостю (в рублях)."""
    from app.db.models import Client
    
    discount = payload.get("discount", 0)
    
    client = await session.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    
    # Сохраняем скидку в notes в формате JSON
    import json
    notes_data = {}
    if client.notes:
        try:
            notes_data = json.loads(client.notes)
        except:
            notes_data = {}
    
    notes_data["personal_discount"] = discount
    client.notes = json.dumps(notes_data, ensure_ascii=False)
    
    await session.commit()
    
    return {"status": "ok", "discount": discount}


@app.post("/api/admin/tables/book")
async def book_table(
    payload: dict,
    session: AsyncSession = Depends(get_session),
):
    """Забронировать стол (гости придут)."""
    from app.db.models import Booking, Client
    from datetime import datetime
    
    table_no = payload.get("table_no")
    datetime_str = payload.get("datetime")
    guests = payload.get("guests", 2)
    
    if not table_no or not datetime_str:
        raise HTTPException(status_code=400, detail="table_no and datetime required")
    
    try:
        booking_at = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid datetime format")
    
    # Создаём техническую бронь
    client = await session.scalar(select(Client).where(Client.telegram_id == 999999998))
    if not client:
        client = Client(
            telegram_id=999999998,
            username="staff_booking",
            full_name="Бронь персонала",
        )
        session.add(client)
        await session.flush()
    
    booking = Booking(
        client_id=client.id,
        booking_at=booking_at,
        table_no=table_no,
        guests=guests,
        comment="Бронь через админ-панель",
        status="confirmed",
        is_staff_booking=True,
    )
    
    session.add(booking)
    await session.commit()
    
    return {"status": "booked", "table_no": table_no, "booking_id": booking.id}


@app.post("/api/admin/tables/occupy")
async def occupy_table(
    payload: dict,
    session: AsyncSession = Depends(get_session),
):
    """Отметить стол как занятый (гости без брони)."""
    from app.db.models import Booking, Client, BookingStatus
    from datetime import datetime
    
    table_no = payload.get("table_no")
    
    if not table_no:
        raise HTTPException(status_code=400, detail="table_no required")
    
    # Создаём техническую бронь на текущее время
    client = await session.scalar(select(Client).where(Client.telegram_id == 999999997))
    if not client:
        client = Client(
            telegram_id=999999997,
            username="walk_in",
            full_name="Гости без брони",
        )
        session.add(client)
        await session.flush()
    
    booking = Booking(
        client_id=client.id,
        booking_at=datetime.utcnow(),
        table_no=table_no,
        guests=2,
        comment="Гости без брони (walk-in)",
        status="confirmed",
        is_staff_booking=True,
    )
    
    session.add(booking)
    await session.commit()
    
    return {"status": "occupied", "table_no": table_no}


@app.post("/api/admin/tables/{table_no}/free")
async def free_table(
    table_no: int,
    payload: dict = {},
    session: AsyncSession = Depends(get_session),
):
    """Освободить стол (гости ушли)."""
    from app.db.models import Booking
    from datetime import datetime, timedelta
    
    close_all = payload.get("close_all", False)
    
    # Находим активные брони этого стола
    now = datetime.utcnow()
    today_start = datetime.combine(now.date(), datetime.min.time())
    
    stmt = select(Booking).where(
        and_(
            Booking.table_no == table_no,
            Booking.booking_at >= today_start,
            Booking.status.in_(["pending", "confirmed"]),
        )
    )
    bookings = (await session.scalars(stmt)).all()
    
    for booking in bookings:
        if close_all:
            # Гости ушли - закрываем все брони
            booking.status = "completed"
        else:
            # Отменяем будущие брони
            if booking.booking_at > now:
                booking.status = "canceled"
            else:
                booking.status = "completed"
    
    await session.commit()

    return {"status": "freed", "table_no": table_no}


# ==================== TELEGRAM WEBHOOK ====================

# Импортируем функции для создания глобальных bot и dispatcher
from app.bot.dispatcher import get_bot, get_dispatcher

# Получаем глобальные bot и dispatcher (singleton)
_webhook_bot = get_bot()
_webhook_dp = get_dispatcher()


@app.on_event("startup")
async def on_startup():
    """Установить webhook и инициализировать БД при старте приложения."""
    import os
    from app.db.base import init_db
    
    # Инициализация БД
    print("[STARTUP] Initializing database...", flush=True)
    try:
        await init_db()
        print("[STARTUP] Database initialized!", flush=True)
    except Exception as e:
        print(f"[STARTUP] Database init error: {e}", flush=True)
    
    # Установка webhook
    webapp_url = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("WEBAPP_URL", "https://filin-hookah.onrender.com")
    webhook_url = f"{webapp_url}/api/telegram/webhook"
    
    print(f"[STARTUP] Setting webhook to: {webhook_url}", flush=True)
    try:
        await _webhook_bot.set_webhook(
            url=webhook_url,
            allowed_updates=["message", "callback_query", "pre_checkout_query"],
        )
        print(f"[STARTUP] Webhook set successfully!", flush=True)
    except Exception as e:
        print(f"[STARTUP] ERROR setting webhook: {e}", flush=True)


@app.on_event("shutdown")
async def on_shutdown():
    """Закрыть бота при остановке приложения."""
    print("[SHUTDOWN] Closing bot...", flush=True)
    await _webhook_bot.session.close()


@app.post("/api/telegram/webhook")
async def telegram_webhook(request: Request) -> dict:
    """Обработка обновлений от Telegram (webhook)."""
    from aiogram.types import Update
    
    try:
        update_data = await request.json()
        print(f"[WEBHOOK] Received update: {update_data}", flush=True)

        # Правильное создание Update для aiogram 3.x
        update = Update.model_validate(update_data)
        print(f"[WEBHOOK] Processing update {update.update_id}...", flush=True)

        result = await _webhook_dp.feed_update(_webhook_bot, update)
        print(f"[WEBHOOK] Update processed, result: {result}", flush=True)

        return {"ok": True}
    except Exception as e:
        print(f"[WEBHOOK] ERROR: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return {"ok": False, "error": str(e)}
