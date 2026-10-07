from __future__ import annotations

import random

from aiogram import Bot
from aiogram.types import ReactionTypeEmoji

from app.services.settings import get_bool, get_setting


async def choose_reaction() -> str | None:
    if not await get_bool('reaction_enabled', False):
        return None
    raw = await get_setting('reaction_emojis', '🔥,❤️,👏')
    emojis = [x.strip() for x in raw.split(',') if x.strip()]
    if not emojis:
        return None
    return random.choice(emojis)


async def react_to_message(bot: Bot, chat_id: int, message_id: int) -> bool:
    emoji = await choose_reaction()
    if not emoji:
        return False
    big = await get_bool('reaction_big', False)
    try:
        await bot.set_message_reaction(chat_id=chat_id, message_id=message_id, reaction=[ReactionTypeEmoji(emoji=emoji)], is_big=big)
        return True
    except Exception:
        return False
