from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Any, Awaitable, Callable, Deque, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject


class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, requests_per_window: int = 8, window_seconds: int = 10) -> None:
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self._events: Dict[int, Deque[float]] = defaultdict(deque)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if not user:
            return await handler(event, data)

        now = time.monotonic()
        bucket = self._events[user.id]
        while bucket and now - bucket[0] > self.window_seconds:
            bucket.popleft()

        if len(bucket) >= self.requests_per_window:
            return None

        bucket.append(now)
        return await handler(event, data)

