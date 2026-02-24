from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


# Автоматическое создание таблиц при импорте моделей
_tables_created = False


def ensure_tables_created():
    """Создать таблицы БД если ещё не созданы."""
    global _tables_created
    if not _tables_created:
        import asyncio
        from app.db.base import engine
        
        async def _create():
            global _tables_created
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            _tables_created = True
            print("[DB] Tables created at import time!", flush=True)
        
        try:
            asyncio.run(_create())
        except Exception as e:
            print(f"[DB] Table creation error (will retry later): {e}", flush=True)


# Вызываем при импорте
ensure_tables_created()


class BookingStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELED = "canceled"


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone_hash: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    visits: Mapped[int] = mapped_column(Integer, default=0)
    consent_accepted: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)  # Заметки о клиенте
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    bookings: Mapped[list[Booking]] = relationship(back_populates="client")
    reviews: Mapped[list[Review]] = relationship(back_populates="client")


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        UniqueConstraint(
            "table_no",
            "booking_at",
            name="uq_booking_table_start",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), index=True)
    booking_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=120)
    guests: Mapped[int] = mapped_column(Integer, default=2)
    table_no: Mapped[int] = mapped_column(Integer, index=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default=BookingStatus.PENDING.value)
    reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    is_staff_booking: Mapped[bool] = mapped_column(Boolean, default=False)  # Бронь от сотрудника
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    client: Mapped[Client] = relationship(back_populates="bookings")
    review: Mapped[Review | None] = relationship(back_populates="booking")


class Promotion(Base):
    __tablename__ = "promotions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), index=True)
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id"), nullable=True)
    rating: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    client: Mapped[Client] = relationship(back_populates="reviews")
    booking: Mapped[Booking | None] = relationship(back_populates="review")


class VenueSettings(Base):
    __tablename__ = "venue_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    schedule_text: Mapped[str] = mapped_column(Text)
    contacts_text: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

