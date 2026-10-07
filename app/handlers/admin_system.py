from __future__ import annotations

import json
from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.types import CallbackQuery, BufferedInputFile
from sqlalchemy import delete, select

from app.db.models import Admin, AdminAuditLog, AnswerLog, QuizAttempt, User
from app.db.session import SessionLocal
from app.filters import AdminCallbackFilter, AdminFilter
from app.keyboards.inline import kb
from app.services.admin import audit
from app.services.settings import get_bool, set_setting

router = Router(name='admin_system')
router.message.filter(AdminFilter())
router.callback_query.filter(AdminCallbackFilter())


@router.callback_query(F.data == 'admin:cleanup')
async def cleanup(call: CallbackQuery) -> None:
    await call.answer()
    await call.message.answer(
        '<b>🧹 TOZALASH MARKAZI</b>\n\nFaqat kerakli resetlar qoldirildi. Har bir amal alohida tasdiqlanadi.',
        reply_markup=kb([
            [('🏆 TOP userlar', 'cleanup:leaderboard')],
            [('🔥 TOP referallar', 'cleanup:referrals')],
            [('🧠 Test natijalari', 'cleanup:tests')],
            [('⬅️ Tizim', 'admin:home')],
        ]),
    )


@router.callback_query(F.data.startswith('cleanup:'))
async def cleanup_confirm(call: CallbackQuery) -> None:
    key = call.data.split(':')[1]
    if key not in {'leaderboard', 'referrals', 'tests'}:
        await call.answer('Noma’lum amal', show_alert=True)
        return
    await call.answer()
    labels = {'leaderboard': 'TOP userlar statistikasi', 'referrals': 'TOP referral statistikasi', 'tests': 'Test natijalari'}
    await call.message.answer(
        f'⚠️ <b>{labels[key]}</b> reset qilinsinmi?\n\nBu amalni bekor qilib bo‘lmaydi.',
        reply_markup=kb([[('✅ HA', f'cleanup:yes:{key}')], [('❌ YO‘Q', 'admin:home')]]),
    )


@router.callback_query(F.data.startswith('cleanup:yes:'))
async def cleanup_yes(call: CallbackQuery) -> None:
    key = call.data.split(':')[2]
    if key not in {'leaderboard', 'referrals', 'tests'}:
        await call.answer('Noma’lum amal', show_alert=True)
        return
    async with SessionLocal() as session:
        if key == 'leaderboard':
            await session.execute(__import__('sqlalchemy').update(User).values(rank_points=0))
        elif key == 'referrals':
            await session.execute(__import__('sqlalchemy').update(User).values(referral_rank_score=0))
        elif key == 'tests':
            await session.execute(delete(AnswerLog))
            await session.execute(delete(QuizAttempt))
            await session.execute(__import__('sqlalchemy').update(User).values(points=0, rank_points=0, questions_answered=0, correct_answers=0, streak_days=0, last_answer_at=None))
        await session.commit()
    await audit(call.from_user.id, 'cleanup', key)
    await call.answer('✅ Reset bajarildi')
    await call.message.answer('✅ <b>Reset yakunlandi.</b>', reply_markup=kb([[('⬅️ Tizim', 'admin:home')]]))


@router.callback_query(F.data == 'admin:settings')
async def settings(call: CallbackQuery) -> None:
    await call.answer()
    subscription = await get_bool('required_subscription_enabled', True)
    maintenance = await get_bool('maintenance_mode', False)
    await call.message.answer(
        '<b>⚙️ UMUMIY SOZLAMALAR</b>\n\nBu yerda faqat tizimga tegishli global parametrlar turadi. Referral, reyting va reaction sozlamalari o‘z bo‘limida.',
        reply_markup=kb([
            [(f'📡 Majburiy obuna {"🟢" if subscription else "🔴"}', 'setting:required_subscription_enabled')],
            [(f'🛠 Maintenance {"🟢" if maintenance else "🔴"}', 'setting:maintenance_mode')],
            [('⬅️ Tizim', 'admin:home')],
        ]),
    )


@router.callback_query(F.data == 'admin:audit')
async def audit_log(call: CallbackQuery) -> None:
    await call.answer()
    async with SessionLocal() as session:
        rows = list((await session.scalars(select(AdminAuditLog).order_by(AdminAuditLog.id.desc()).limit(20))).all())
    text = '<b>📝 SO‘NGGI ADMIN LOG</b>\n\n' + '\n'.join(f'#{r.id} · {r.admin_telegram_id} · {r.action} · {r.details[:80]}' for r in rows)
    await call.message.answer(text or 'Log yo‘q.')


@router.callback_query(F.data == 'admin:admins')
async def admins(call: CallbackQuery) -> None:
    await call.answer()
    async with SessionLocal() as session:
        rows = list((await session.scalars(select(Admin).order_by(Admin.id))).all())
    text = '<b>🔐 ADMINLAR</b>\n\n' + ('\n'.join(f'{a.telegram_id} · {a.role} · {"🟢" if a.active else "🔴"}' for a in rows) or 'Adminlar ro‘yxati bo‘sh')
    await call.message.answer(text + '\n\nSuper Admin ID lar <code>ADMIN_IDS</code> orqali beriladi.')


@router.callback_query(F.data == 'admin:backup')
async def backup(call: CallbackQuery) -> None:
    await call.answer('Backup tayyorlanmoqda...')
    async with SessionLocal() as session:
        users = list((await session.scalars(select(User))).all())
        books = list((await session.scalars(select(__import__('app.db.models', fromlist=['Book']).Book))).all())
    payload = {
        'created_at': datetime.now(timezone.utc).isoformat(),
        'users': [{'id': u.id, 'telegram_id': u.telegram_id, 'username': u.username, 'points': u.points} for u in users],
        'books': [{'id': b.id, 'title': b.title, 'author': b.author, 'active': b.is_active} for b in books],
    }
    data = json.dumps(payload, ensure_ascii=False, indent=2).encode('utf-8')
    await call.message.answer_document(BufferedInputFile(data, filename='kitobxonlar_v29_backup.json'))


@router.callback_query(F.data == 'admin:security')
async def security(call: CallbackQuery) -> None:
    await call.answer()
    await call.message.answer('<b>🛡 XAVFSIZLIK</b>\n\n✅ Admin filter\n✅ Redis rate limit\n✅ Audit log\n✅ Referral self-invite himoyasi\n✅ TXT import validatsiyasi\n✅ Confirmation resetlari\n✅ Maintenance mode')
