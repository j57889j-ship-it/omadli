from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message
from redis.asyncio import Redis

from app.services.admin import is_admin


class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, redis: Redis, ttl: int = 1) -> None:
        self.redis = redis
        self.ttl = ttl

    async def __call__(self, handler: Callable[[Any, dict[str, Any]], Awaitable[Any]], event: Any, data: dict[str, Any]) -> Any:
        user_id = getattr(getattr(event, 'from_user', None), 'id', None)
        if user_id and await is_admin(user_id):
            return await handler(event, data)
        if user_id:
            key = f'rl:{user_id}'
            allowed = await self.redis.set(key, '1', nx=True, ex=self.ttl)
            if not allowed:
                if isinstance(event, Message):
                    await event.answer('⏳ Biroz sekinroq, iltimos.')
                elif isinstance(event, CallbackQuery):
                    await event.answer('⏳ Biroz sekinroq.', show_alert=False)
                return None
        return await handler(event, data)
