from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import desc, func, select
from sqlalchemy.orm import aliased

from app.db.models import User
from app.db.session import SessionLocal
from app.services.settings import get_bool, get_int


def now() -> datetime:
    return datetime.now(timezone.utc)


async def register_pending_referral(new_user: User, referrer_telegram_id: int | None) -> bool:
    if not referrer_telegram_id or new_user.pending_referrer_id or new_user.referral_confirmed_at:
        return False
    if referrer_telegram_id == new_user.telegram_id:
        return False
    if not await get_bool('referral_enabled', True):
        return False
    async with SessionLocal() as session:
        referrer = await session.scalar(select(User).where(User.telegram_id == referrer_telegram_id))
        user = await session.scalar(select(User).where(User.telegram_id == new_user.telegram_id))
        if not referrer or not user or referrer.id == user.id or user.pending_referrer_id or user.referral_confirmed_at:
            return False
        user.pending_referrer_id = referrer.id
        await session.commit()
        return True


async def confirm_referral(telegram_id: int) -> bool:
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if not user or not user.pending_referrer_id or user.referral_confirmed_at:
            return False
        if not await get_bool('referral_enabled', True):
            return False
        referrer = await session.get(User, user.pending_referrer_id)
        if not referrer or referrer.telegram_id == user.telegram_id:
            return False
        user.referral_confirmed_at = now()
        bonus = max(0, await get_int('referral_bonus_points', 50))
        if not user.referral_bonus_awarded:
            referrer.points += bonus
            referrer.rank_points += bonus
            referrer.referral_rank_score += 1
            user.referral_bonus_awarded = True
        await session.commit()
        return True


async def referral_count(user_id: int) -> int:
    async with SessionLocal() as session:
        count = await session.scalar(
            select(func.count(User.id)).where(User.pending_referrer_id == user_id, User.referral_confirmed_at.is_not(None))
        )
        return int(count or 0)


async def top_referrals(limit: int = 10) -> list[tuple[User, int]]:
    Referrer = aliased(User)
    async with SessionLocal() as session:
        result = await session.execute(
            select(Referrer, Referrer.referral_rank_score)
            .where(Referrer.referral_rank_score > 0, Referrer.is_blocked.is_(False))
            .order_by(desc(Referrer.referral_rank_score), desc(Referrer.points))
            .limit(limit)
        )
        return [(row[0], int(row[1])) for row in result.all()]


async def total_confirmed_referrals() -> int:
    async with SessionLocal() as session:
        return int(await session.scalar(select(func.count(User.id)).where(User.referral_confirmed_at.is_not(None))) or 0)


async def reset_referral_ranking() -> None:
    async with SessionLocal() as session:
        await session.execute(__import__('sqlalchemy').update(User).values(referral_rank_score=0))
        await session.commit()
