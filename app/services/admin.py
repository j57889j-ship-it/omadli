from __future__ import annotations

from sqlalchemy import select

from app.config import get_settings
from app.db.models import Admin, AdminAuditLog
from app.db.session import SessionLocal


async def is_admin(telegram_id: int) -> bool:
    if telegram_id in get_settings().parsed_admin_ids:
        return True
    async with SessionLocal() as session:
        row = await session.scalar(select(Admin).where(Admin.telegram_id == telegram_id, Admin.active.is_(True)))
        return row is not None


async def is_super_admin(telegram_id: int) -> bool:
    if telegram_id in get_settings().parsed_admin_ids:
        return True
    async with SessionLocal() as session:
        row = await session.scalar(select(Admin).where(Admin.telegram_id == telegram_id, Admin.active.is_(True)))
        return bool(row and row.role == 'super_admin')


async def audit(admin_id: int, action: str, details: str = '') -> None:
    async with SessionLocal() as session:
        session.add(AdminAuditLog(admin_telegram_id=admin_id, action=action, details=details))
        await session.commit()
