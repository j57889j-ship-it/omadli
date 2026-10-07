from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message
from redis.asyncio import Redis

from app.services.admin import is_admin
from app.services.settings import get_bool


class MaintenanceMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable[[Any, dict[str, Any]], Awaitable[Any]], event: Any, data: dict[str, Any]) -> Any:
        user_id = getattr(getattr(event, 'from_user', None), 'id', None)
        if user_id and await get_bool('maintenance_mode', False) and not await is_admin(user_id):
            text = '🛠 <b>Texnik xizmat</b>\n\nBot vaqtincha yangilanmoqda. Keyinroq yana urinib ko‘ring.'
            if isinstance(event, Message):
                await event.answer(text)
            elif isinstance(event, CallbackQuery):
                await event.answer('🛠 Texnik xizmat', show_alert=True)
            return None
        return await handler(event, data)
