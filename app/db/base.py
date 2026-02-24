from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine, async_scoped_session
from sqlalchemy.orm import DeclarativeBase, scoped_session
from sqlalchemy.pool import NullPool

from app.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()

# Определяем тип БД и настраиваем пул соединений
is_postgresql = settings.db_url.startswith("postgresql+")
is_sqlite = settings.db_url.startswith("sqlite+")

if is_postgresql:
    # PostgreSQL: используем connection pool с оптимизацией для Render
    engine = create_async_engine(
        settings.db_url,
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
        settings.db_url,
        echo=False,
        future=True,
        poolclass=NullPool,
    )
else:
    # Другие БД: default settings
    engine = create_async_engine(settings.db_url, echo=False, future=True)

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

