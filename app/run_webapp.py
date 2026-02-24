import asyncio
import logging
import os

import uvicorn

from app.logging import get_logger

logger = get_logger(__name__)


def init_database_sync() -> None:
    """Синхронно создать таблицы БД."""
    import asyncio
    from app.db.base import engine, Base
    from app.db import models  # noqa: F401
    
    async def _create_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    asyncio.run(_create_tables())
    logger.info("Database tables created!")


def run() -> None:
    logger.info("Запуск Web App сервера...")
    
    # Создаём БД ПЕРЕД запуском uvicorn
    logger.info("Initializing database...")
    try:
        init_database_sync()
        logger.info("Database initialized!")
    except Exception as e:
        logger.error(f"Database init error: {e}")
    
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"Listening on port {port}")
    
    uvicorn.run(
        "app.webapp.app:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info",
        access_log=True,
    )
    logger.info("Server running...")


if __name__ == "__main__":
    run()

