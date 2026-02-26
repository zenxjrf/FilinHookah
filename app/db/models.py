from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


# Таблицы создаются в app/webapp/app.py при старте приложения
# Не создаём автоматически при импорте (избегаем asyncio.run() в event loop)


class BookingStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELED = "canceled"


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone_hash: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    visits: Mapped[int] = mapped_column(Integer, default=0)
    consent_accepted: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)  # Заметки о клиенте
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    bookings: Mapped[list[Booking]] = relationship(back_populates="client", lazy="selectin")
    reviews: Mapped[list[Review]] = relationship(back_populates="client", lazy="selectin")


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
    status: Mapped[str] = mapped_column(String(16), default=BookingStatus.PENDING.value, index=True)
    reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False)  # За 24 часа
    reminder_1h_sent: Mapped[bool] = mapped_column(Boolean, default=False)  # За 1 час
    is_staff_booking: Mapped[bool] = mapped_column(Boolean, default=False, index=True)  # Бронь от сотрудника
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    client: Mapped[Client] = relationship(back_populates="bookings", lazy="joined")
    review: Mapped[Review | None] = relationship(back_populates="booking", lazy="joined")


class Promotion(Base):
    __tablename__ = "promotions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), index=True)
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id"), nullable=True, index=True)
    rating: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    client: Mapped[Client] = relationship(back_populates="reviews", lazy="joined")
    booking: Mapped[Booking | None] = relationship(back_populates="review", lazy="joined")


class VenueSettings(Base):
    __tablename__ = "venue_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    schedule_text: Mapped[str] = mapped_column(Text)
    contacts_text: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Subscriber(Base):
    """Подписчики на рассылку."""
    __tablename__ = "subscribers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    subscribed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_mailed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class DynamicAdmin(Base):
    """Админы, выданные через команду /add_admin (без перезапуска)."""
    __tablename__ = "dynamic_admins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
