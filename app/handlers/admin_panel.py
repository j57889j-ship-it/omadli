from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select

from app.db.models import AnswerLog, Book, Question, QuestionReport, User
from app.db.session import SessionLocal
from app.filters import AdminCallbackFilter, AdminFilter
from app.keyboards.inline import kb
from app.keyboards.reply import admin_main, user_main
from app.services.admin import audit
from app.services.formatting import e, panel
from app.services.referrals import top_referrals
from app.services.settings import get_bool, get_int, get_setting, set_setting
from app.services.users import top_users
from app.states import AdminSettingState

router = Router(name='admin_panel')
router.message.filter(AdminFilter())
router.callback_query.filter(AdminCallbackFilter())


async def dashboard_text() -> str:
    async with SessionLocal() as session:
        users = int(await session.scalar(select(func.count(User.id))) or 0)
        active = int(await session.scalar(select(func.count(User.id)).where(User.last_activity_at >= datetime.now(timezone.utc) - timedelta(days=1))) or 0)
        books = int(await session.scalar(select(func.count(Book.id)).where(Book.is_active.is_(True))) or 0)
        questions = int(await session.scalar(select(func.count(Question.id)).where(Question.is_active.is_(True))) or 0)
        attempts = int(await session.scalar(select(func.count(__import__('app.db.models', fromlist=['QuizAttempt']).QuizAttempt.id))) or 0)
        answers = int(await session.scalar(select(func.count(AnswerLog.id))) or 0)
        correct = int(await session.scalar(select(func.count(AnswerLog.id)).where(AnswerLog.is_correct.is_(True))) or 0)
        reports = int(await session.scalar(select(func.count(QuestionReport.id)).where(QuestionReport.status == 'open')) or 0)
    return panel('ADMIN DASHBOARD',
        f'👥 Foydalanuvchilar: <b>{users:,}</b>\n'
        f'🟢 24 soat faol: <b>{active:,}</b>\n\n'
        f'📚 Faol kitoblar: <b>{books:,}</b>\n'
        f'❓ Faol savollar: <b>{questions:,}</b>\n\n'
        f'🧠 Testlar: <b>{attempts:,}</b>\n'
        f'📝 Javoblar: <b>{answers:,}</b>\n'
        f'✅ To‘g‘ri: <b>{correct:,}</b>\n'
        f'⚠️ Ochiq reportlar: <b>{reports:,}</b>'
    )


@router.message(F.text == '/admin')
async def admin_cmd(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(panel('ADMIN MARKAZI', 'Boshqaruv pastdagi 7 ta markazga ajratilgan. Kritik sozlamalar faqat admin tomonidan o‘zgartiriladi.'), reply_markup=admin_main())


@router.message(F.text == '🏠 USER MENYU')
async def user_mode(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer('🏠 <b>User rejimiga qaytdingiz.</b>', reply_markup=user_main())


@router.message(F.text == '📊 BOSHQARUV')
async def admin_dashboard(message: Message) -> None:
    await message.answer(await dashboard_text(), reply_markup=kb([
        [('📈 Batafsil statistika', 'admin:stats')],
        [('🟢 Faol userlar', 'admin:active'), ('📊 User statistikasi', 'admin:user_stats')],
        [('📝 Audit log', 'admin:audit')],
    ]))


@router.callback_query(F.data == 'admin:stats')
async def admin_stats(call: CallbackQuery) -> None:
    await call.answer()
    users = await top_users(5)
    refs = await top_referrals(5)
    user_lines = '\n'.join(f'{i}. {e(u.username or u.full_name)} — {u.rank_points:,} 🏆' for i, u in enumerate(users, 1)) or 'Ma’lumot yo‘q'
    ref_lines = '\n'.join(f'{i}. {e(u.username or u.full_name)} — {c} 👥' for i, (u, c) in enumerate(refs, 1)) or 'Ma’lumot yo‘q'
    await call.message.answer(panel('BATAFSIL STATISTIKA', f'<b>👑 TOP KITOBXONLAR</b>\n{user_lines}\n\n<b>🔥 TOP REFERALLAR</b>\n{ref_lines}'), reply_markup=kb([[('⬅️ Boshqaruv', 'admin:home')]]))


@router.callback_query(F.data == 'admin:active')
async def active_users(call: CallbackQuery) -> None:
    await call.answer()
    async with SessionLocal() as session:
        rows = list((await session.scalars(select(User).where(User.last_activity_at >= datetime.now(timezone.utc) - timedelta(days=1)).order_by(User.last_activity_at.desc()).limit(20))).all())
    lines = '\n'.join(f'• {e(u.username or u.full_name)} · {u.last_activity_at:%Y-%m-%d %H:%M}' for u in rows) or 'Faol user yo‘q'
    await call.message.answer(panel('24 SOAT ICHIDAGI FAOL USERLAR', lines), reply_markup=kb([[('⬅️ Boshqaruv', 'admin:home')]]))


@router.callback_query(F.data == 'admin:user_stats')
async def user_stats(call: CallbackQuery) -> None:
    await call.answer()
    async with SessionLocal() as session:
        total = int(await session.scalar(select(func.count(User.id))) or 0)
        blocked = int(await session.scalar(select(func.count(User.id)).where(User.is_blocked.is_(True))) or 0)
        avg_points = int(await session.scalar(select(func.avg(User.points))) or 0)
        avg_questions = int(await session.scalar(select(func.avg(User.questions_answered))) or 0)
    await call.message.answer(panel('USER STATISTIKASI', f'👥 Jami: <b>{total:,}</b>\n🚫 Bloklangan: <b>{blocked:,}</b>\n⭐ O‘rtacha ball: <b>{avg_points:,}</b>\n🧠 O‘rtacha javob: <b>{avg_questions:,}</b>'), reply_markup=kb([[('⬅️ Boshqaruv', 'admin:home')]]))


@router.message(F.text == '📚 KONTENT')
async def content_menu(message: Message) -> None:
    await message.answer(panel('KONTENT MARKAZI', 'Kitoblar, savollar, import, kategoriya va reportlar alohida boshqariladi.'), reply_markup=kb([
        [('📖 Kitoblar', 'admin:books')],
        [('❓ Savollar markazi', 'admin:questions')],
        [('📥 TXT import', 'admin:import')],
        [('🗂 Kategoriyalar', 'admin:categories')],
        [('📅 Daily challenge', 'admin:daily')],
        [('⚠️ Savol reportlari', 'admin:reports')],
    ]))


@router.message(F.text == '👥 FOYDALANUVCHILAR')
async def users_menu(message: Message) -> None:
    await message.answer(panel('FOYDALANUVCHILAR', 'Qidirish, individual statistika, bonus, ban va broadcast bir joyda.'), reply_markup=kb([
        [('🔎 Qidirish', 'admin:user_search')],
        [('🏆 TOP userlar', 'rank:users'), ('🔥 TOP referallar', 'rank:referrals')],
        [('🔗 Referral markazi', 'admin:referrals')],
        [('📊 User statistikasi', 'admin:user_stats')],
        [('📣 Userlarga xabar', 'admin:broadcast')],
    ]))


@router.message(F.text == '🏆 REYTINGLAR')
async def rankings_menu(message: Message) -> None:
    user_enabled = await get_bool('leaderboard_enabled', True)
    ref_enabled = await get_bool('referral_leaderboard_enabled', True)
    limit = min(20, max(3, await get_int('leaderboard_limit', 10)))
    await message.answer(panel('REYTING BOSHQARUVI', f'👑 TOP userlar: {"🟢 ON" if user_enabled else "🔴 OFF"}\n🔥 TOP referral: {"🟢 ON" if ref_enabled else "🔴 OFF"}\n🔢 Ko‘rsatish: <b>{limit}</b>'), reply_markup=kb([
        [('👑 TOP user ON/OFF', 'setting:leaderboard_enabled')],
        [('🔥 TOP referral ON/OFF', 'setting:referral_leaderboard_enabled')],
        [('🔢 TOP limit', 'setting:leaderboard_limit')],
        [('🧹 TOP userlar reset', 'cleanup:leaderboard')],
        [('🧹 TOP referallar reset', 'cleanup:referrals')],
    ]))


@router.message(F.text == '🎁 BONUSLAR')
async def rewards_admin(message: Message) -> None:
    await message.answer(panel('BONUSLAR MARKAZI', 'Reward va yutuqlar shu bo‘limda boshqariladi.'), reply_markup=kb([
        [('📅 Daily challenge', 'admin:daily')],
        [('👥 Referral bonusi', 'setting:referral_bonus_points')],
        [('🏅 Achievementlar', 'admin:achievements')],
        [('⭐ Manual bonus / ball', 'admin:user_search')],
    ]))


@router.message(F.text == '📢 KANAL')
async def channel_admin(message: Message) -> None:
    await message.answer(panel('KANAL MARKAZI', 'Majburiy obuna, target kanal, post va reaction alohida boshqariladi.'), reply_markup=kb([
        [('📡 Majburiy kanallar', 'admin:channels')],
        [('📣 Kanalga post', 'admin:channel_post')],
        [('❤️ Reaction sozlamalari', 'admin:reactions')],
        [('📅 Daily savol', 'admin:daily')],
        [('🔗 Target kanal', 'admin:target')],
    ]))


@router.message(F.text == '🛠 TIZIM')
async def system_admin(message: Message) -> None:
    await message.answer(panel('TIZIM MARKAZI', 'Texnik sozlamalar, xavfsizlik, reset va backup shu yerda.'), reply_markup=kb([
        [('⚙️ Umumiy sozlamalar', 'admin:settings')],
        [('🔐 Adminlar', 'admin:admins')],
        [('🛡 Xavfsizlik', 'admin:security')],
        [('🧹 Tozalash markazi', 'admin:cleanup')],
        [('💾 JSON backup', 'admin:backup')],
        [('📝 Audit log', 'admin:audit')],
        [('🔧 Maintenance ON/OFF', 'setting:maintenance_mode')],
    ]))


@router.callback_query(F.data == 'admin:home')
async def admin_home(call: CallbackQuery) -> None:
    await call.answer()
    await call.message.answer(panel('ADMIN MARKAZI', 'Asosiy 7 ta bo‘lim orqali boshqaring.'), reply_markup=admin_main())


@router.callback_query(F.data.startswith('setting:'))
async def toggle_setting(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    key = call.data.split(':', 1)[1]
    bool_keys = {'leaderboard_enabled', 'referral_leaderboard_enabled', 'reaction_enabled', 'maintenance_mode', 'daily_challenge_enabled', 'referral_enabled', 'required_subscription_enabled'}
    if key in bool_keys:
        current = await get_bool(key, False)
        await set_setting(key, '0' if current else '1')
        await audit(call.from_user.id, 'toggle_setting', f'{key}={not current}')
        await call.message.answer(f'✅ <b>{e(key)}</b> → {"🟢 ON" if not current else "🔴 OFF"}')
        return
    await state.set_state(AdminSettingState.waiting_value)
    await state.update_data(setting_key=key)
    current = await get_setting(key, '')
    await call.message.answer(f'⚙️ <b>{e(key)}</b>\n\nHozirgi qiymat: <code>{e(current)}</code>\n\nYangi qiymatni yuboring yoki /cancel.')


@router.message(AdminSettingState.waiting_value)
async def save_setting(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    value = (message.text or '').strip()
    await set_setting(data['setting_key'], value)
    await audit(message.from_user.id, 'set_setting', f'{data["setting_key"]}={value}')
    await state.clear()
    await message.answer('✅ Sozlama saqlandi.', reply_markup=admin_main())
