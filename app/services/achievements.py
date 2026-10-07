from __future__ import annotations

from sqlalchemy import select

from app.db.models import Achievement, User, UserAchievement
from app.db.session import SessionLocal


async def refresh_achievements(telegram_id: int) -> list[Achievement]:
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if not user:
            return []
        achievements = list((await session.scalars(select(Achievement).where(Achievement.is_active.is_(True)))).all())
        earned: list[Achievement] = []
        for achievement in achievements:
            if achievement.metric == 'questions' and user.questions_answered < achievement.requirement:
                continue
            if achievement.metric == 'points' and user.points < achievement.requirement:
                continue
            if achievement.metric == 'rank':
                if user.rank_points <= 0:
                    continue
                better = await session.scalar(select(__import__('sqlalchemy').func.count(User.id)).where(User.is_blocked.is_(False), User.rank_points > user.rank_points))
                rank = int(better or 0) + 1
                if rank > achievement.requirement:
                    continue
            exists = await session.scalar(select(UserAchievement).where(UserAchievement.user_id == user.id, UserAchievement.achievement_id == achievement.id))
            if not exists:
                session.add(UserAchievement(user_id=user.id, achievement_id=achievement.id))
                earned.append(achievement)
        await session.commit()
        return earned


async def user_achievements(telegram_id: int) -> list[Achievement]:
    async with SessionLocal() as session:
        rows = await session.execute(
            select(Achievement).join(UserAchievement, UserAchievement.achievement_id == Achievement.id).join(User, UserAchievement.user_id == User.id).where(User.telegram_id == telegram_id).order_by(UserAchievement.earned_at.desc())
        )
        return list(rows.scalars().all())
