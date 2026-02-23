import logging

import uvicorn

from app.logging import get_logger

logger = get_logger(__name__)


def run() -> None:
    logger.info("Запуск Web App сервера...")
    try:
        uvicorn.run(
            "app.webapp.app:app",
            host="0.0.0.0",
            port=8000,
            reload=False,  # Отключаем reload для продакшена
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

