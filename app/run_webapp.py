import logging
import os

import uvicorn

from app.logging import get_logger

logger = get_logger(__name__)


def run() -> None:
    logger.info("Запуск Web App сервера...")
    try:
        # Railway назначает порт через переменную PORT
        port = int(os.environ.get("PORT", 8000))
        logger.info(f"Listening on port {port}")
        uvicorn.run(
            "app.webapp.app:app",
            host="0.0.0.0",
            port=port,
            reload=False,
            log_level="info",
            access_log=True,
        )
    except Exception as e:
        logger.error(f"Критическая ошибка Web App: {e}", exc_info=True)
        raise
    finally:
        logger.info("Web App сервер остановлен")


if __name__ == "__main__":
    run()

