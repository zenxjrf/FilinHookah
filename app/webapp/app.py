from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Set

from fastapi import Depends, FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from app.config import get_settings
from app.db import crud
from app.db.base import get_session
from app.db.models import Booking, BookingStatus, Client, Promotion, Subscriber

print(">>> BUILD 2026-02-25 (PostgreSQL + WebSocket + Broadcast) <<<", flush=True)

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Filin WebApp v3")

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

# ==================== LOGGING ====================
logger = logging.getLogger(__name__)

# ==================== WEBSOCKET MANAGER ====================
class ConnectionManager:
    """Менеджер WebSocket соединений для админ-панели."""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """Отправить сообщение всем подключенным клиентам."""
        async with self._lock:
            connections = set(self.active_connections)
        
        if not connections:
            return
        
        message_text = json.dumps(message)
        disconnected = set()
        
        for conn in connections:
            try:
                await conn.send_text(message_text)
            except Exception:
                disconnected.add(conn)
        
        # Удаляем отключенные
        async with self._lock:
            self.active_connections -= disconnected
    
    async def send_booking_update(self, booking_id: int, action: str, status: str = None):
        """Отправить обновление о брони."""
        await self.broadcast({
            "type": "booking_update",
            "booking_id": booking_id,
            "action": action,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
        })

manager = ConnectionManager()

# ==================== CACHE ====================
class SimpleCache:
    """Простое кэширование для оптимизации."""
    
    def __init__(self, ttl_seconds: int = 60):
        self._cache: Dict[str, tuple] = {}
        self._ttl = ttl_seconds
    
    def get(self, key: str):
        if key in self._cache:
            value, timestamp = self._cache[key]
            if datetime.utcnow().timestamp() - timestamp < self._ttl:
                return value
            del self._cache[key]
        return None
    
    def set(self, key: str, value):
        self._cache[key] = (value, datetime.utcnow().timestamp())
    
    def invalidate(self, key: str):
        if key in self._cache:
            del self._cache[key]
    
    def invalidate_pattern(self, pattern: str):
        """Удалить ключи по паттерну."""
        for key in list(self._cache.keys()):
            if key.startswith(pattern):
                del self._cache[key]

cache = SimpleCache(ttl_seconds=30)

# ==================== PYDANTIC MODELS ====================

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


class UpdateBookingStatusRequest(BaseModel):
    status: str = Field(..., pattern=r"^(pending|confirmed|completed|canceled)$")


class BroadcastRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    photo_url: str | None = None


# ==================== ROUTES ====================

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": "3.0", "db": "postgresql"}


@app.api_route("/", methods=["GET", "HEAD"])
async def root() -> dict[str, str]:
    return {"status": "ok", "service": "Filin Hookah Bot v3"}


@app.get("/webapp", response_class=HTMLResponse)
async def webapp_main(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="index.html", context={})


@app.get("/index", response_class=HTMLResponse)
async def webapp_index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="index.html", context={})


@app.get("/api/availability")
async def availability(
    date_str: str = Query(alias="date"),
    table_no: int = Query(ge=1, le=30),
    session: AsyncSession = Depends(get_session),
) -> dict[str, list[str]]:
    cache_key = f"availability:{date_str}:{table_no}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
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
    
    result = {"busy_slots": busy_slots}
    cache.set(cache_key, result)
    return result


@app.get("/api/tables_status")
async def tables_status(
    date_str: str = Query(alias="date"),
    session: AsyncSession = Depends(get_session),
) -> dict[str, list[dict]]:
    cache_key = f"tables_status:{date_str}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
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

    tables = {}
    for item in items:
        if item.table_no not in tables:
            tables[item.table_no] = []
        tables[item.table_no].append({
            "time": item.booking_at.strftime("%H:%M"),
            "is_staff": item.is_staff_booking,
        })

    result = {"tables": tables}
    cache.set(cache_key, result)
    return result


@app.post("/api/bookings")
async def create_booking(
    payload: CreateBookingRequest,
    session: AsyncSession = Depends(get_session),
) -> dict[str, int | str]:
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

    # Уведомление в чат работников
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
            await bot.send_message(settings.workers_chat_id, admin_text, reply_markup=keyboard)
        else:
            for admin_id in settings.admin_ids:
                await bot.send_message(admin_id, admin_text, reply_markup=keyboard)

        await bot.session.close()
        
        # WebSocket уведомление
        await manager.send_booking_update(booking.id, "created", booking.status)
        cache.invalidate_pattern("tables_status:")
        
    except Exception as e:
        logger.error(f"ERROR sending notification: {e}")

    return {"id": booking.id, "status": booking.status}


@app.get("/api/bootstrap")
async def bootstrap(
    telegram_id: int = Query(ge=1),
    username: str | None = Query(default=None),
    full_name: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    cache_key = f"bootstrap:{telegram_id}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
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

    default_promo = {
        "id": 0,
        "title": "☀️ Кальян до 18:00",
        "description": "1000 рублей",
        "image_url": None,
        "is_default": True
    }

    other_promos = [
        {"id": p.id, "title": p.title, "description": p.description, "image_url": p.image_url, "is_default": False}
        for p in promotions
    ]

    promo_payload = [default_promo] + other_promos
    bookings = await crud.list_user_bookings(session, client.id)

    status_map = {
        "pending": "Ожидает подтверждения",
        "confirmed": "Бронь подтверждена",
        "completed": "Выполнена",
        "canceled": "Отменена",
    }

    result = {
        "schedule": "Ежедневно с 14:00 до 2:00",
        "contacts": venue.contacts_text,
        "visits": client.visits,
        "notes": client.notes,
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
    
    cache.set(cache_key, result)
    return result


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
    telegram_id = payload.get("telegram_id")
    if not telegram_id:
        raise HTTPException(status_code=400, detail="Telegram ID required")

    try:
        booking = await crud.cancel_booking_by_client(session, booking_id, telegram_id)
        if not booking:
            raise HTTPException(status_code=404, detail="Бронь не найдена")
        
        # WebSocket уведомление
        await manager.send_booking_update(booking_id, "canceled", "canceled")
        cache.invalidate_pattern("tables_status:")
        cache.invalidate_pattern("bootstrap:")
        
        return {"status": "canceled", "message": "Бронь отменена"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== ADMIN API ====================

@app.get("/api/admin/stats")
async def admin_stats(session: AsyncSession = Depends(get_session)):
    stats = await crud.get_today_stats(session)
    return stats


@app.get("/api/admin/tables")
async def admin_tables(
    date: str = Query(...),
    session: AsyncSession = Depends(get_session),
):
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

        is_occupied = booking.status == BookingStatus.CONFIRMED.value and booking.booking_at <= now
        is_blocked = booking.is_staff_booking and booking.status == BookingStatus.CANCELED.value

        tables[booking.table_no].append({
            "id": booking.id,
            "booking_at": booking.booking_at.isoformat(),
            "status": booking.status,
            "is_occupied": is_occupied,
            "is_blocked": is_blocked
        })

    return {"tables": tables}


@app.get("/api/admin/bookings")
async def admin_bookings(
    date: str = Query(...),
    session: AsyncSession = Depends(get_session),
):
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    from_time = datetime.combine(target_date, datetime.min.time())
    to_time = datetime.combine(target_date, datetime.max.time())

    stmt = select(Booking).order_by(desc(Booking.booking_at)).where(
        and_(
            Booking.booking_at >= from_time,
            Booking.booking_at <= to_time,
        )
    )
    bookings = (await session.scalars(stmt)).all()

    return [
        {
            "id": b.id,
            "booking_at": b.booking_at.isoformat(),
            "table_no": b.table_no,
            "guests": b.guests,
            "status": b.status,
        }
        for b in bookings
    ]


@app.post("/api/admin/bookings/{booking_id}/status")
async def update_booking_status(
    booking_id: int,
    payload: dict,
    session: AsyncSession = Depends(get_session),
):
    status = payload.get("status")
    if not status:
        raise HTTPException(status_code=400, detail="Status required")

    booking = await session.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Бронь не найдена")

    old_status = booking.status
    booking.status = status
    await session.commit()
    await session.refresh(booking)

    # WebSocket уведомление об изменении
    await manager.send_booking_update(booking_id, "status_changed", status)
    cache.invalidate_pattern("tables_status:")
    cache.invalidate_pattern("admin:stats")

    return {"status": "ok", "booking_id": booking_id, "old_status": old_status, "new_status": status}


# ==================== BROADCAST API ====================

@app.get("/api/admin/broadcast/subscribers")
async def get_subscribers_count(session: AsyncSession = Depends(get_session)):
    count = await crud.get_subscribers_count(session)
    return {"subscribers_count": count}


@app.post("/api/admin/broadcast")
async def broadcast_message(
    payload: BroadcastRequest,
    session: AsyncSession = Depends(get_session),
) -> dict[str, int]:
    """Отправить рассылку всем активным подписчикам."""
    from aiogram import Bot
    
    bot = Bot(token=settings.bot_token)
    subscribers = await crud.get_active_subscribers(session)
    
    success_count = 0
    fail_count = 0
    
    for sub in subscribers:
        try:
            if payload.photo_url:
                await bot.send_photo(
                    chat_id=sub.telegram_id,
                    photo=payload.photo_url,
                    caption=payload.message,
                    parse_mode="HTML",
                )
            else:
                await bot.send_message(
                    chat_id=sub.telegram_id,
                    text=payload.message,
                    parse_mode="HTML",
                )
            await crud.update_last_mailed(session, sub.telegram_id)
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to send to {sub.telegram_id}: {e}")
            fail_count += 1
        await asyncio.sleep(0.05)  # Anti-flood
    
    await bot.session.close()
    
    return {
        "sent": success_count,
        "failed": fail_count,
        "total": len(subscribers),
    }


# ==================== WEBSOCKET ENDPOINT ====================

@app.websocket("/ws/admin")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint для админ-панели."""
    await manager.connect(websocket)
    try:
        while True:
            # Получаем данные от клиента (можно использовать для команд)
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# ==================== ADMIN HTML ====================

@app.get("/admin", response_class=HTMLResponse)
async def admin_panel():
    return templates.TemplateResponse("admin.html", {"request": {}})


# ==================== TELEGRAM WEBHOOK ====================

from app.bot.dispatcher import get_bot, get_dispatcher

_webhook_bot = get_bot()
_webhook_dp = get_dispatcher()


@app.on_event("startup")
async def on_startup():
    """Создать таблицы БД и установить webhook при старте."""
    import os
    from app.db.base import engine, Base
    from app.db import models  # noqa: F401

    logger.info("Creating database tables...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created!")
    except Exception as e:
        logger.error(f"Database error: {e}")

    # Установка webhook
    webapp_url = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("WEBAPP_URL", "https://filinhookah-1.onrender.com")
    base_url = webapp_url.replace("/webapp", "") if webapp_url.endswith("/webapp") else webapp_url
    webhook_url = f"{base_url}/api/telegram/webhook"
    webapp_full_url = webapp_url if webapp_url.endswith("/webapp") else f"{webapp_url}/webapp"

    logger.info(f"Setting webhook to: {webhook_url}")
    try:
        await _webhook_bot.set_webhook(
            url=webhook_url,
            allowed_updates=["message", "callback_query", "pre_checkout_query"],
        )
        logger.info("Webhook set successfully!")

        from aiogram.types import MenuButtonWebApp, WebAppInfo
        await _webhook_bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="Открыть мини-приложение",
                web_app=WebAppInfo(url=webapp_full_url),
            )
        )
        logger.info(f"Menu Button set to: {webapp_full_url}")
    except Exception as e:
        logger.error(f"ERROR setting webhook/Menu Button: {e}")


@app.on_event("shutdown")
async def on_shutdown():
    """Закрыть бота и соединения при остановке."""
    logger.info("Closing bot session...")
    await _webhook_bot.session.close()
    logger.info("Disposing database engine...")
    from app.db.base import dispose_engine
    await dispose_engine()
    logger.info("Shutdown complete")


@app.post("/api/telegram/webhook")
async def telegram_webhook(request: Request) -> dict:
    """Обработка обновлений от Telegram."""
    from aiogram.types import Update

    try:
        update_data = await request.json()
        update = Update.model_validate(update_data)
        
        result = await _webhook_dp.feed_update(_webhook_bot, update)
        
        return {"ok": True}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        import traceback
        traceback.print_exc()
        return {"ok": False, "error": str(e)}
