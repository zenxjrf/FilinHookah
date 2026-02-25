from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()

# Определяем тип БД и настраиваем пул соединений
# Render выдаёт URL с 'postgres://', конвертируем для asyncpg
db_url = settings.db_url
if db_url.startswith("postgres://"):
    # Конвертируем формат Render в формат asyncpg
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif db_url.startswith("postgresql://"):
    # Стандартный PostgreSQL URL
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

is_postgresql = db_url.startswith("postgresql+asyncpg+")
is_sqlite = db_url.startswith("sqlite+")

if is_postgresql:
    # PostgreSQL: используем connection pool с оптимизацией для Render
    engine = create_async_engine(
        db_url,
        echo=False,
        future=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_recycle=settings.db_pool_recycle,
        pool_pre_ping=True,  # Проверка соединения перед использованием
    )
elif is_sqlite:
    # SQLite: NullPool для избежания проблем с блокировками
    engine = create_async_engine(
        db_url,
        echo=False,
        future=True,
        poolclass=NullPool,
    )
else:
    # Другие БД: default settings
    engine = create_async_engine(db_url, echo=False, future=True)

session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncSession:
    async with session_factory() as session:
        yield session


async def init_db() -> None:
    from app.db import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose_engine() -> None:
    """Закрыть все соединения с БД (важно для PostgreSQL)."""
    await engine.dispose()

