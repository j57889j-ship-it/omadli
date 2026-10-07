from __future__ import annotations

from aiogram import F, Router
import asyncio
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import desc, func, select

from app.db.models import QuizAttempt, User
from app.db.session import SessionLocal
from app.filters import AdminCallbackFilter, AdminFilter
from app.keyboards.inline import kb
from app.keyboards.reply import admin_main
from app.services.admin import audit
from app.services.users import adjust_points, reset_user_stats
from app.services.referrals import top_referrals, total_confirmed_referrals
from app.services.settings import get_bool, get_int, set_setting
from app.states import AdminBroadcastState, AdminUserState

router = Router(name='admin_users')
router.message.filter(AdminFilter())
router.callback_query.filter(AdminCallbackFilter())




@router.callback_query(F.data == 'admin:referrals')
async def referral_admin(call: CallbackQuery) -> None:
    await call.answer()
    enabled = await get_bool('referral_enabled', True)
    top_enabled = await get_bool('referral_leaderboard_enabled', True)
    bonus = await get_int('referral_bonus_points', 50)
    limit = await get_int('leaderboard_limit', 10)
    total = await total_confirmed_referrals()
    rows = await top_referrals(min(5, max(3, limit)))
    top_text = '\n'.join(f'{i}. @{u.username}' if u.username else f'{i}. {u.full_name}' for i,(u,_) in enumerate(rows,1)) or 'Ma’lumot yo‘q'
    await call.message.answer(f'<b>🔗 REFERRAL MARKAZI</b>\n\nHolat: {"🟢 ON" if enabled else "🔴 OFF"}\n🎁 Bonus: <b>{bonus}</b> ⭐\n🏆 TOP referral: {"🟢 ON" if top_enabled else "🔴 OFF"}\n🔢 TOP limit: <b>{limit}</b>\n👥 Tasdiqlangan referral: <b>{total:,}</b>\n\n🔥 <b>Hozirgi TOP</b>\n{top_text}', reply_markup=kb([
        [('🔗 Referral ON/OFF', 'setting:referral_enabled')],
        [('🎁 Bonusni o‘zgartirish', 'setting:referral_bonus_points')],
        [('🔥 TOP referral ON/OFF', 'setting:referral_leaderboard_enabled')],
        [('🧹 Referral TOP reset', 'cleanup:referrals')],
    ]))


@router.callback_query(F.data == 'admin:user_search')
async def user_search(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    await state.set_state(AdminUserState.waiting_search)
    await call.message.answer('🔎 Telegram ID yoki username yuboring.')


@router.message(AdminUserState.waiting_search)
async def user_search_value(message: Message, state: FSMContext) -> None:
    value = message.text.strip().lstrip('@')
    async with SessionLocal() as session:
        if value.isdigit():
            user = await session.scalar(select(User).where(User.telegram_id == int(value)))
        else:
            user = await session.scalar(select(User).where(func.lower(User.username) == value.lower()))
    await state.clear()
    if not user:
        await message.answer('❌ Foydalanuvchi topilmadi.', reply_markup=admin_main())
        return
    await message.answer(f'👤 <b>{user.full_name}</b>\n🆔 {user.telegram_id}\n⭐ {user.points}\n👥 Referral pending/confirmed tizim bilan\n🧠 {user.questions_answered} javob\n✅ {user.correct_answers} to‘g‘ri\n🔥 {user.streak_days} kun', reply_markup=kb([
        [('⭐ +/− Ball', f'admin:user_points:{user.telegram_id}')],
        [('🧹 Statistikani reset', f'admin:user_reset:{user.telegram_id}')],
        [('🚫 Ban/Unban', f'admin:user_ban:{user.telegram_id}')],
        [('📊 Test tarixi', f'admin:user_tests:{user.telegram_id}')],
    ]))


@router.callback_query(F.data.startswith('admin:user_points:'))
async def points_start(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    await state.set_state(AdminUserState.waiting_points)
    await state.update_data(user_id=int(call.data.split(':')[2]))
    await call.message.answer('⭐ Necha ball qo‘shish/ayirish? Masalan: <code>100</code> yoki <code>-50</code>.')


@router.message(AdminUserState.waiting_points)
async def points_value(message: Message, state: FSMContext) -> None:
    try:
        delta = int(message.text.strip())
    except ValueError:
        await message.answer('❌ Butun son yuboring.')
        return
    data = await state.get_data()
    await adjust_points(data['user_id'], delta)
    await audit(message.from_user.id, 'adjust_points', f'user={data["user_id"]},delta={delta}')
    await state.clear()
    await message.answer('✅ Ball yangilandi.', reply_markup=admin_main())


@router.callback_query(F.data.startswith('admin:user_reset:'))
async def user_reset(call: CallbackQuery) -> None:
    await call.answer()
    uid = int(call.data.split(':')[2])
    await call.message.answer('⚠️ Foydalanuvchi statistikasi reset qilinsinmi?', reply_markup=kb([[('✅ Ha', f'admin:user_reset_yes:{uid}'), ('❌ Yo‘q','admin:home')]]))


@router.callback_query(F.data.startswith('admin:user_reset_yes:'))
async def user_reset_yes(call: CallbackQuery) -> None:
    uid = int(call.data.split(':')[2])
    await reset_user_stats(uid)
    await audit(call.from_user.id, 'user_reset', str(uid))
    await call.answer('✅ Reset qilindi')
    await call.message.answer('✅ Foydalanuvchi statistikasi tozalandi.')


@router.callback_query(F.data.startswith('admin:user_ban:'))
async def user_ban(call: CallbackQuery) -> None:
    uid = int(call.data.split(':')[2])
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.telegram_id == uid))
        if user:
            user.is_blocked = not user.is_blocked
            status = user.is_blocked
            await session.commit()
        else:
            status = None
    await audit(call.from_user.id, 'user_ban_toggle', f'user={uid},blocked={status}')
    await call.answer('✅ Holat yangilandi')


@router.callback_query(F.data.startswith('admin:user_tests:'))
async def user_tests(call: CallbackQuery) -> None:
    uid = int(call.data.split(':')[2])
    async with SessionLocal() as session:
        attempts = list((await session.scalars(select(QuizAttempt).join(User, QuizAttempt.user_id == User.id).where(User.telegram_id == uid).order_by(desc(QuizAttempt.id)).limit(10))).all())
    text = '<b>📊 SO‘NGGI TESTLAR</b>\n\n' + '\n'.join(f'#{a.id} · {a.correct_answers}/{a.total_questions} · {a.points_earned} ⭐ · {a.mode}' for a in attempts) if attempts else 'Ma’lumot yo‘q.'
    await call.message.answer(text)


@router.message(F.text == '📣 Userlarga xabar')
async def broadcast_menu(message: Message, state: FSMContext) -> None:
    await state.set_state(AdminBroadcastState.waiting_message)
    await message.answer('📣 Barcha faol foydalanuvchilarga yuboriladigan xabarni jo‘nating. Matn, rasm yoki video ham bo‘lishi mumkin.')


@router.callback_query(F.data == 'admin:broadcast')
async def broadcast_cb(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    await state.set_state(AdminBroadcastState.waiting_message)
    await call.message.answer('📣 Yuboriladigan xabarni jo‘nating.')


@router.message(AdminBroadcastState.waiting_message)
async def broadcast_message(message: Message, state: FSMContext, bot) -> None:
    async with SessionLocal() as session:
        ids = list((await session.scalars(select(User.telegram_id).where(User.is_blocked.is_(False)))).all())
    sent = failed = 0
    for uid in ids:
        try:
            await bot.copy_message(chat_id=uid, from_chat_id=message.chat.id, message_id=message.message_id)
            sent += 1
            await asyncio.sleep(0.04)
        except Exception:
            failed += 1
    await audit(message.from_user.id, 'broadcast', f'total={len(ids)},sent={sent},failed={failed}')
    await state.clear()
    await message.answer(f'📣 <b>Broadcast tugadi</b>\n\n✅ {sent}\n❌ {failed}', reply_markup=admin_main())
