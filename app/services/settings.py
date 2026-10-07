from __future__ import annotations

from sqlalchemy import select

from app.db.models import BotSetting
from app.db.session import SessionLocal


async def get_setting(key: str, default: str = '') -> str:
    async with SessionLocal() as session:
        row = await session.scalar(select(BotSetting).where(BotSetting.key == key))
        return row.value if row else default


async def set_setting(key: str, value: str) -> None:
    async with SessionLocal() as session:
        row = await session.scalar(select(BotSetting).where(BotSetting.key == key))
        if row:
            row.value = value
        else:
            session.add(BotSetting(key=key, value=value))
        await session.commit()


async def get_bool(key: str, default: bool = False) -> bool:
    value = await get_setting(key, '1' if default else '0')
    return value.lower() in {'1', 'true', 'yes', 'on'}


async def get_int(key: str, default: int = 0) -> int:
    value = await get_setting(key, str(default))
    try:
        return int(value)
    except ValueError:
        return default
