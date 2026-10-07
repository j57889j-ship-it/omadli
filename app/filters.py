from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from app.services.admin import is_admin


class AdminFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return bool(message.from_user and await is_admin(message.from_user.id))


class AdminCallbackFilter(BaseFilter):
    async def __call__(self, callback: CallbackQuery) -> bool:
        return bool(callback.from_user and await is_admin(callback.from_user.id))
