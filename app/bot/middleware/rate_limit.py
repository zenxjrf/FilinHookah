"""Rate limiting middleware for aiogram 3.x."""
from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject


class RateLimitMiddleware(BaseMiddleware):
    """Simple rate limiting middleware."""

    def __init__(self) -> None:
        self.cache: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # Get user id from message or callback query
        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else None
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id if event.from_user else None

        if user_id is None:
            return await handler(event, data)

        # Check rate limit (1 second between messages)
        now = time.time()
        if user_id in self.cache:
            if now - self.cache[user_id] < 1.0:
                return None  # Skip this update
        self.cache[user_id] = now

        return await handler(event, data)
