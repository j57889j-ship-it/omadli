from __future__ import annotations

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from sqlalchemy import select

from app.db.models import RequiredChannel
from app.db.session import SessionLocal


async def required_channels() -> list[RequiredChannel]:
    async with SessionLocal() as session:
        return list((await session.scalars(select(RequiredChannel).where(RequiredChannel.is_active.is_(True)).order_by(RequiredChannel.id))).all())


async def is_subscribed(bot: Bot, user_id: int) -> tuple[bool, list[RequiredChannel]]:
    channels = await required_channels()
    missing: list[RequiredChannel] = []
    for channel in channels:
        try:
            member = await bot.get_chat_member(channel.chat_id, user_id)
            if member.status in {ChatMemberStatus.LEFT, ChatMemberStatus.KICKED}:
                missing.append(channel)
        except Exception:
            missing.append(channel)
    return not missing, missing
