from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import desc, func, select

from app.db.models import AnswerLog, User
from app.db.session import SessionLocal


def now() -> datetime:
    return datetime.now(timezone.utc)


async def get_or_create_user(tg_user) -> tuple[User, bool]:
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.telegram_id == tg_user.id))
        created = False
        if not user:
            user = User(telegram_id=tg_user.id, username=tg_user.username, full_name=tg_user.full_name or 'Foydalanuvchi')
            session.add(user)
            created = True
        else:
            user.username = tg_user.username
            user.full_name = tg_user.full_name or user.full_name
            user.last_activity_at = now()
        await session.commit()
        await session.refresh(user)
        return user, created


async def get_user(telegram_id: int) -> User | None:
    async with SessionLocal() as session:
        return await session.scalar(select(User).where(User.telegram_id == telegram_id))


async def top_users(limit: int = 10) -> list[User]:
    async with SessionLocal() as session:
        return list((await session.scalars(select(User).where(User.is_blocked.is_(False), User.rank_points > 0).order_by(desc(User.rank_points), desc(User.points), desc(User.correct_answers), User.id).limit(limit))).all())


async def user_rank(telegram_id: int) -> int | None:
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if not user:
            return None
        if user.rank_points <= 0:
            return None
        better = await session.scalar(
            select(func.count(User.id)).where(
                User.is_blocked.is_(False),
                User.rank_points > 0,
                (User.rank_points > user.rank_points) | ((User.rank_points == user.rank_points) & (User.correct_answers > user.correct_answers)),
            )
        )
        return int(better or 0) + 1


async def question_stats(telegram_id: int) -> tuple[int, int, int]:
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if not user:
            return (0, 0, 0)
        return user.questions_answered, user.correct_answers, user.points


async def update_streak(user: User) -> int:
    current = now()
    async with SessionLocal() as session:
        db_user = await session.scalar(select(User).where(User.telegram_id == user.telegram_id))
        if not db_user:
            return 0
        if not db_user.last_answer_at:
            db_user.streak_days = 1
        else:
            delta = current.date() - db_user.last_answer_at.date()
            if delta.days == 0:
                pass
            elif delta.days == 1:
                db_user.streak_days += 1
            else:
                db_user.streak_days = 1
        db_user.last_answer_at = current
        await session.commit()
        return db_user.streak_days


async def adjust_points(telegram_id: int, delta: int) -> User | None:
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if not user:
            return None
        user.points = max(0, user.points + delta)
        user.rank_points = max(0, user.rank_points + delta)
        await session.commit()
        return user


async def reset_user_stats(telegram_id: int) -> bool:
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if not user:
            return False
        user.points = 0
        user.rank_points = 0
        user.questions_answered = 0
        user.correct_answers = 0
        user.streak_days = 0
        user.last_answer_at = None
        await session.execute(AnswerLog.__table__.delete().where(AnswerLog.user_id == user.id))
        await session.commit()
        return True


async def active_user_ids() -> list[int]:
    async with SessionLocal() as session:
        return list((await session.scalars(select(User.telegram_id).where(User.is_blocked.is_(False)))).all())
