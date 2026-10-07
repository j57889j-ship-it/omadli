from sqlalchemy import select

from app.config import get_settings
from app.db.models import Achievement, Admin, BotSetting
from app.db.session import SessionLocal

DEFAULT_SETTINGS = {
    'referral_enabled': '1',
    'referral_bonus_points': '50',
    'referral_leaderboard_enabled': '1',
    'leaderboard_enabled': '1',
    'leaderboard_limit': '10',
    'reaction_enabled': '0',
    'reaction_emojis': '🔥,❤️,👏',
    'reaction_big': '0',
    'daily_challenge_enabled': '1',
    'daily_challenge_reward': '30',
    'maintenance_mode': '0',
    'required_subscription_enabled': '1',
}

DEFAULT_ACHIEVEMENTS = [
    ('first_answer', 'Birinchi qadam', 'Birinchi savolga javob bering', '🌱', 1, 'questions'),
    ('hundred_questions', 'Kitobxon', '100 ta savolga javob bering', '📚', 100, 'questions'),
    ('five_hundred_questions', 'Bilimdon', '500 ta savolga javob bering', '🧠', 500, 'questions'),
    ('thousand_questions', 'Mutolaa ustasi', '1000 ta savolga javob bering', '🔥', 1000, 'questions'),
    ('top_ten', 'TOP-10', 'TOP 10 kitobxonlar qatoriga kiring', '🏆', 10, 'rank'),
]


async def seed_defaults() -> None:
    settings = get_settings()
    async with SessionLocal() as session:
        for key, value in DEFAULT_SETTINGS.items():
            row = await session.scalar(select(BotSetting).where(BotSetting.key == key))
            if not row:
                session.add(BotSetting(key=key, value=value))
        for code, title, description, icon, requirement, metric in DEFAULT_ACHIEVEMENTS:
            row = await session.scalar(select(Achievement).where(Achievement.code == code))
            if not row:
                session.add(Achievement(code=code, title=title, description=description, icon=icon, requirement=requirement, metric=metric))
        for admin_id in settings.parsed_admin_ids:
            row = await session.scalar(select(Admin).where(Admin.telegram_id == admin_id))
            if not row:
                session.add(Admin(telegram_id=admin_id, role='super_admin', active=True))
        await session.commit()
