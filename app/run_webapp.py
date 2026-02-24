import logging
import os

import uvicorn

from app.logging import get_logger

logger = get_logger(__name__)


def run() -> None:
    logger.info("Запуск Web App сервера...")
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


if __name__ == "__main__":
    run()

