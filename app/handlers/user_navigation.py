from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from app.keyboards.inline import back, kb
from app.keyboards.reply import user_main
from app.services.achievements import user_achievements
from app.services.referrals import referral_count, top_referrals
from app.services.settings import get_bool, get_int
from app.services.users import get_user, question_stats, top_users, user_rank
from app.services.formatting import e, pct, user_label

router = Router(name='user_navigation')


@router.message(F.text == '🏆 REYTING')
async def rating_menu(message: Message) -> None:
    await message.answer('<b>🏆 REYTING MARKAZI</b>\n\nFaqat ikki ochiq reyting: kitobxonlar va referallar.', reply_markup=kb([
        [('👑 TOP KITOBXONLAR', 'rank:users')],
        [('🔥 TOP REFERALLAR', 'rank:referrals')],
        [('👤 MENING O‘RNIM', 'rank:me')],
    ]))


@router.callback_query(F.data == 'rank:users')
async def rank_users(call: CallbackQuery) -> None:
    await call.answer()
    if not await get_bool('leaderboard_enabled', True):
        await call.message.answer('🏆 Reyting hozircha o‘chirilgan.')
        return
    limit = min(20, max(3, await get_int('leaderboard_limit', 10)))
    users = await top_users(limit)
    lines = ['👑 <b>TOP KITOBXONLAR</b>', '']
    medals = ['🥇', '🥈', '🥉']
    for idx, user in enumerate(users, start=1):
        icon = medals[idx - 1] if idx <= 3 else f'{idx}️⃣'
        lines.append(f'{icon} {user_label(user.username, user.full_name)} — <b>{user.rank_points:,}</b> 🏆')
    await call.message.answer('\n'.join(lines), reply_markup=back('rank:home'))


@router.callback_query(F.data == 'rank:referrals')
async def rank_referrals(call: CallbackQuery) -> None:
    await call.answer()
    if not await get_bool('referral_leaderboard_enabled', True):
        await call.message.answer('🔥 Referral reytingi hozircha o‘chirilgan.')
        return
    limit = min(20, max(3, await get_int('leaderboard_limit', 10)))
    rows = await top_referrals(limit)
    lines = ['🔥 <b>TOP REFERALLAR</b>', '']
    medals = ['🥇', '🥈', '🥉']
    for idx, (user, count) in enumerate(rows, start=1):
        icon = medals[idx - 1] if idx <= 3 else f'{idx}️⃣'
        lines.append(f'{icon} {user_label(user.username, user.full_name)} — <b>{count}</b> 👥')
    await call.message.answer('\n'.join(lines), reply_markup=back('rank:home'))


@router.callback_query(F.data == 'rank:me')
async def rank_me(call: CallbackQuery) -> None:
    await call.answer()
    rank = await user_rank(call.from_user.id)
    user = await get_user(call.from_user.id)
    count = await referral_count(user.id) if user else 0
    q, c, p = await question_stats(call.from_user.id)
    await call.message.answer(
        f'👤 <b>SIZNING REYTINGINGIZ</b>\n\n'
        f'🏆 Umumiy o‘rin: <b>#{rank or "—"}</b>\n'
        f'🏆 Reyting balli: <b>{user.rank_points if user else 0:,}</b>\n'
        f'⭐ Jami ball: <b>{p:,}</b>\n'
        f'🧠 Javoblar: <b>{q}</b>\n'
        f'✅ To‘g‘ri: <b>{c}</b>\n'
        f'🔥 Referallar: <b>{count}</b>',
        reply_markup=back('rank:home')
    )


@router.callback_query(F.data == 'rank:home')
async def rank_home(call: CallbackQuery) -> None:
    await call.answer()
    await call.message.edit_text('<b>🏆 REYTING</b>\n\nQaysi reytingni ko‘rmoqchisiz?', reply_markup=kb([
        [('👑 TOP KITOBXONLAR', 'rank:users')],
        [('🔥 TOP REFERALLAR', 'rank:referrals')],
        [('👤 MENING O‘RNIM', 'rank:me')],
    ]))


@router.message(F.text == '👤 PROFIL')
async def profile(message: Message) -> None:
    q, c, p = await question_stats(message.from_user.id)
    rank = await user_rank(message.from_user.id)
    user = await get_user(message.from_user.id)
    body = (
        f'⭐ <b>{p:,}</b> ball\n'
        f'🏆 Reyting balli: <b>{user.rank_points if user else 0:,}</b>\n'
        f'🧠 <b>{q}</b> ta javob\n'
        f'✅ <b>{c}</b> ta to‘g‘ri\n'
        f'🎯 Aniqlik: <b>{pct(c, q)}%</b>\n'
        f'🏆 Reyting: <b>#{rank or "—"}</b>'
    )
    await message.answer('<b>👤 PROFILIM</b>\n\n' + body, reply_markup=kb([
        [('📊 Mening statistikam', 'profile:stats'), ('🧠 Test tarixim', 'profile:history')],
        [('❌ Xato savollarim', 'profile:mistakes'), ('🔥 Streakim', 'profile:streak')],
        [('🏅 Yutuqlarim', 'profile:achievements'), ('🔗 Referral markazi', 'profile:referral')],
        [('❤️ Sevimli kitoblarim', 'profile:favorites')],
    ]))


@router.callback_query(F.data == 'profile:stats')
async def profile_stats(call: CallbackQuery) -> None:
    await call.answer()
    q, c, p = await question_stats(call.from_user.id)
    rank = await user_rank(call.from_user.id)
    await call.message.answer(f'📊 <b>STATISTIKA</b>\n\n⭐ {p:,} ball\n🧠 {q} javob\n✅ {c} to‘g‘ri\n❌ {max(0,q-c)} xato\n🎯 {pct(c,q)}% aniqlik\n🏆 #{rank or "—"}', reply_markup=back('user:home'))


@router.callback_query(F.data == 'profile:history')
async def profile_history(call: CallbackQuery) -> None:
    await call.answer()
    from sqlalchemy import desc, select
    from app.db.models import QuizAttempt
    from app.db.session import SessionLocal
    async with SessionLocal() as session:
        user = await session.scalar(select(__import__('app.db.models', fromlist=['User']).User).where(__import__('app.db.models', fromlist=['User']).User.telegram_id == call.from_user.id))
        attempts = list((await session.scalars(select(QuizAttempt).where(QuizAttempt.user_id == user.id).order_by(desc(QuizAttempt.id)).limit(10))).all()) if user else []
    text = '<b>🧠 SO‘NGGI TESTLAR</b>\n\n' + ('\n'.join(f'#{a.id} · {a.correct_answers}/{a.total_questions} · {a.points_earned} ⭐' for a in attempts) or 'Hali test ishlanmagan.')
    await call.message.answer(text, reply_markup=back('user:home'))


@router.callback_query(F.data == 'profile:streak')
async def profile_streak(call: CallbackQuery) -> None:
    await call.answer()
    user = await get_user(call.from_user.id)
    streak = user.streak_days if user else 0
    await call.message.answer(f'🔥 <b>STREAK</b>\n\nHozirgi ketma-ketlik: <b>{streak} kun</b>\n\nDavom eting — har kuni kamida bitta savol ishlang!', reply_markup=back('user:home'))


@router.callback_query(F.data == 'profile:achievements')
async def profile_achievements(call: CallbackQuery) -> None:
    await call.answer()
    items = await user_achievements(call.from_user.id)
    if not items:
        text = '🏅 Hali yutuqlaringiz yo‘q. Test ishlashni boshlang!'
    else:
        text = '🏅 <b>YUTUQLARIM</b>\n\n' + '\n'.join(f'{a.icon} <b>{e(a.title)}</b> — {e(a.description)}' for a in items)
    await call.message.answer(text, reply_markup=back('user:home'))


@router.callback_query(F.data == 'profile:referral')
async def profile_referral(call: CallbackQuery, bot) -> None:
    await call.answer()
    user = await get_user(call.from_user.id)
    count = await referral_count(user.id) if user else 0
    enabled = await get_bool('referral_enabled', True)
    bot_me = await bot.get_me()
    link = f'https://t.me/{bot_me.username}?start=ref_{call.from_user.id}'
    status = '🟢 ON' if enabled else '🔴 OFF'
    from sqlalchemy import func, select
    from app.db.models import User
    from app.db.session import SessionLocal
    async with SessionLocal() as session:
        current = await session.scalar(select(User).where(User.telegram_id == call.from_user.id))
        better = int(await session.scalar(select(func.count(User.id)).where(User.is_blocked.is_(False), User.referral_rank_score > (current.referral_rank_score if current else 0))) or 0) if current else 0
    referral_rank = better + 1 if current else None
    await call.message.answer(
        f'🔗 <b>REFERRAL MARKAZI</b>\n\n'
        f'Holat: {status}\n'
        f'👥 Jami tasdiqlangan: <b>{count}</b>\n'
        f'🔥 TOP referral o‘rni: <b>#{referral_rank or "—"}</b>\n'
        f'🏅 TOPda hisoblanadigan: <b>{current.referral_rank_score if current else 0}</b>\n\n'
        f'🔗 <code>{e(link)}</code>\n\n'
        f'Referral faqat majburiy kanal obunasi tasdiqlangandan keyin hisoblanadi.',
        reply_markup=back('user:home')
    )


@router.callback_query(F.data == 'user:home')
async def user_home(call: CallbackQuery) -> None:
    await call.answer()
    await call.message.answer('🏠 <b>Bosh menyu</b>', reply_markup=user_main())


@router.message(F.text == '🎁 BONUSLAR')
async def rewards(message: Message) -> None:
    await message.answer('<b>🎁 BONUSLAR</b>\n\n🎯 Kunlik bonus\n🔥 Streak bonusi\n👥 Referral bonusi\n🏅 Yutuqlar\n\nBonuslar avtomatik tarzda hisoblanadi.', reply_markup=kb([
        [('🔗 Referral markazi', 'profile:referral'), ('🏅 Yutuqlarim', 'profile:achievements')],
    ]))


@router.message(F.text == 'ℹ️ YORDAM')
async def help_menu(message: Message) -> None:
    await message.answer('<b>ℹ️ YORDAM</b>\n\n📚 Kitob tanlang → 🧠 testni boshlang → ✅ to‘g‘ri javoblar uchun ball oling → 🏆 reytingga chiqing.\n\n🔗 Referral faqat yangi foydalanuvchi majburiy kanallarga obuna bo‘lib, tekshiruvdan o‘tgach tasdiqlanadi.', reply_markup=kb([[('💬 Admin bilan bog‘lanish', 'help:contact')]]))


@router.callback_query(F.data == 'help:contact')
async def help_contact(call: CallbackQuery) -> None:
    await call.answer()
    from app.config import get_settings
    admin_ids = sorted(get_settings().parsed_admin_ids)
    if not admin_ids:
        await call.message.answer('ℹ️ Admin aloqa ID si sozlanmagan.')
        return
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    admin_id = admin_ids[0]
    await call.message.answer('💬 <b>Admin bilan bog‘lanish</b>\
\
Savolingizni yuborishdan oldin admin profilini oching:', reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='👤 Adminni ochish', url=f'tg://user?id={admin_id}')]]))
