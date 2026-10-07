from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy import select

from app.db.models import Achievement
from app.db.session import SessionLocal
from app.filters import AdminCallbackFilter, AdminFilter
from app.keyboards.inline import kb
from app.services.admin import audit
from app.services.settings import get_bool, get_int, set_setting

router = Router(name='admin_misc')
router.message.filter(AdminFilter())
router.callback_query.filter(AdminCallbackFilter())


@router.callback_query(F.data == 'admin:daily')
async def daily(call: CallbackQuery):
    await call.answer()
    enabled = await get_bool('daily_challenge_enabled', True)
    reward = await get_int('daily_challenge_reward', 30)
    await call.message.answer(
        f'<b>📅 DAILY CHALLENGE</b>\n\nHolat: {"🟢 ON" if enabled else "🔴 OFF"}\n🎁 Mukofot: <b>{reward}</b> ⭐',
        reply_markup=kb([
            [('🟢/🔴 ON/OFF', 'setting:daily_challenge_enabled')],
            [('🎁 Mukofotni o‘zgartirish', 'setting:daily_challenge_reward')],
            [('⬅️ Kontent', 'admin:home')],
        ]),
    )


@router.callback_query(F.data == 'admin:achievements')
async def achievements(call: CallbackQuery):
    await call.answer()
    async with SessionLocal() as session:
        rows = list((await session.scalars(select(Achievement).order_by(Achievement.id))).all())
    buttons = [[(f'{a.icon} {a.title} — {"🟢" if a.is_active else "🔴"}', f'admin:achievement:{a.id}')] for a in rows]
    buttons.append([('⬅️ Bonuslar', 'admin:home')])
    await call.message.answer('<b>🏅 ACHIEVEMENTLAR</b>\n\nAvtomatik yutuqlar shu yerda ON/OFF qilinadi.', reply_markup=kb(buttons))


@router.callback_query(F.data.startswith('admin:achievement:'))
async def achievement_toggle(call: CallbackQuery):
    aid = int(call.data.split(':')[2])
    async with SessionLocal() as session:
        row = await session.get(Achievement, aid)
        if not row:
            await call.answer('Topilmadi', show_alert=True)
            return
        row.is_active = not row.is_active
        await session.commit()
        status = row.is_active
    await audit(call.from_user.id, 'achievement_toggle', f'id={aid},active={status}')
    await call.answer('✅ Holat yangilandi')
