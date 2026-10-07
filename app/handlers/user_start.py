from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.keyboards.inline import kb, url_kb
from app.keyboards.reply import user_main
from app.services.channels import is_subscribed
from app.services.referrals import confirm_referral, register_pending_referral
from app.services.users import get_or_create_user

router = Router(name='user_start')


def parse_ref(text: str | None) -> int | None:
    if not text:
        return None
    token = text.split(maxsplit=1)[1] if ' ' in text else ''
    if not token.startswith('ref_'):
        return None
    try:
        return int(token[4:])
    except ValueError:
        return None


async def subscription_gate(message: Message, bot) -> bool:
    ok, missing = await is_subscribed(bot, message.from_user.id)
    if ok:
        return True
    url_rows = []
    for channel in missing:
        if channel.join_url:
            url_rows.append([(f'📢 {channel.title}', channel.join_url)])
    callback_rows = [[('✅ Obunani tekshirish', 'sub:check')]]
    await message.answer(
        '🔐 <b>Majburiy obuna</b>\n\nAvval kanalga qo‘shiling, keyin <b>✅ Obunani tekshirish</b> tugmasini bosing.',
        reply_markup=__import__('app.keyboards.inline', fromlist=['mixed_kb']).mixed_kb(callback_rows, url_rows),
    )
    return False


@router.message(CommandStart())
async def start(message: Message, bot) -> None:
    user, created = await get_or_create_user(message.from_user)
    referrer = parse_ref(message.text)
    if created and referrer:
        await register_pending_referral(user, referrer)
    if not await subscription_gate(message, bot):
        return
    if await confirm_referral(message.from_user.id):
        await message.answer('🎉 <b>Referral tasdiqlandi!</b> Siz taklif qilgan foydalanuvchi hisobingizga qo‘shildi.')
    await message.answer(
        '✨ <b>KITOBXONLAR QUIZ</b> ga xush kelibsiz!\n\n'
        '📚 Kitoblarni tanlang, 🧠 test ishlang, 🏆 TOP kitobxonlar orasiga kiring.\n\n'
        '🔥 Har bir to‘g‘ri javob sizni reytingda yuqoriga olib chiqadi!',
        reply_markup=user_main(),
    )


@router.callback_query(F.data == 'sub:check')
async def check_subscription(call: CallbackQuery, bot) -> None:
    await call.answer()
    ok, _ = await is_subscribed(bot, call.from_user.id)
    if not ok:
        await call.message.answer('❌ Hali barcha majburiy kanallarga obuna bo‘linmagan.')
        return
    await confirm_referral(call.from_user.id)
    await call.message.answer('✅ <b>Obuna tasdiqlandi!</b> Endi botdan to‘liq foydalanishingiz mumkin.', reply_markup=user_main())
