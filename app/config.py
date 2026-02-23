from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


def _clean_env(value: str) -> str:
    # Protect against BOM and accidental spaces/newlines in .env values.
    return value.replace("\ufeff", "").strip()


def _parse_admin_ids(raw: str) -> set[int]:
    raw = _clean_env(raw)
    if not raw:
        return set()
    return {int(item.strip()) for item in raw.split(",") if item.strip()}


@dataclass(frozen=True)
class Settings:
    bot_token: str
    db_url: str
    webapp_url: str
    admin_ids: set[int]
    workers_chat_id: int | None
    log_path: str
    default_schedule: str
    default_contacts: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    env_path = Path(".env")
    load_dotenv(dotenv_path=env_path, override=True, encoding="utf-8-sig")

    workers_chat_raw = os.getenv("WORKERS_CHAT_ID", "")
    workers_chat_id = int(workers_chat_raw) if workers_chat_raw.strip() else None

    return Settings(
        bot_token=_clean_env(os.getenv("BOT_TOKEN", "")),
        db_url=_clean_env(os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./filin.db")),
        webapp_url=_clean_env(os.getenv("WEBAPP_URL", "http://localhost:8000")),
        admin_ids=_parse_admin_ids(os.getenv("ADMIN_IDS", "")),
        workers_chat_id=workers_chat_id,
        log_path=_clean_env(os.getenv("LOG_PATH", "logs.txt")),
        default_schedule=os.getenv("DEFAULT_SCHEDULE", "Ежедневно с 14:00 до 2:00"),
        default_contacts=os.getenv(
            "DEFAULT_CONTACTS",
            "Phone: +7 (000) 000-00-00\\nAddress: Example street, 1",
        ),
    )
