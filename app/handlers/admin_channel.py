from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from app.db.models import RequiredChannel
from app.db.session import SessionLocal
from app.filters import AdminCallbackFilter, AdminFilter
from app.keyboards.inline import kb
from app.keyboards.reply import admin_main
from app.services.admin import audit
from app.services.reactions import react_to_message
from app.services.settings import get_bool, get_setting, set_setting
from app.states import AdminChannelPostState, AdminChannelState, AdminReactionState

router = Router(name='admin_channel')
router.message.filter(AdminFilter())
router.callback_query.filter(AdminCallbackFilter())


@router.callback_query(F.data == 'admin:channels')
async def channels(call: CallbackQuery) -> None:
    await call.answer()
    async with SessionLocal() as session:
        rows = list((await session.scalars(select(RequiredChannel).order_by(RequiredChannel.id))).all())
    text = '<b>📡 MAJBURIY KANALLAR</b>\n\n' + ('\n'.join(f'#{c.id} · {c.title} · {"🟢" if c.is_active else "🔴"}' for c in rows) or 'Kanal yo‘q')
    await call.message.answer(text, reply_markup=kb([
        [('➕ Kanal qo‘shish', 'admin:channel_add')],
        *[[(f'✏️ {c.title}', f'admin:channel_toggle:{c.id}')] for c in rows],
    ]))


@router.callback_query(F.data == 'admin:channel_add')
async def channel_add(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    await state.set_state(AdminChannelState.waiting_chat_id)
    await call.message.answer('📡 Kanal chat ID yuboring. Masalan: <code>-1001234567890</code>.')


@router.message(AdminChannelState.waiting_chat_id)
async def channel_chat_id(message: Message, state: FSMContext) -> None:
    try:
        chat_id = int(message.text.strip())
    except ValueError:
        await message.answer('❌ Chat ID son bo‘lishi kerak.')
        return
    await state.update_data(chat_id=chat_id)
    await state.set_state(AdminChannelState.waiting_title)
    await message.answer('🏷 Kanal nomini yuboring.')


@router.message(AdminChannelState.waiting_title)
async def channel_title(message: Message, state: FSMContext) -> None:
    await state.update_data(title=message.text.strip())
    await state.set_state(AdminChannelState.waiting_join_url)
    await message.answer('🔗 Kanal havolasini yuboring (masalan https://t.me/yourchannel).')


@router.message(AdminChannelState.waiting_join_url)
async def channel_join_url(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    async with SessionLocal() as session:
        existing = await session.scalar(select(RequiredChannel).where(RequiredChannel.chat_id == data['chat_id']))
        if existing:
            existing.title = data['title']
            existing.join_url = message.text.strip()
            existing.is_active = True
        else:
            session.add(RequiredChannel(chat_id=data['chat_id'], title=data['title'], join_url=message.text.strip()))
        await session.commit()
    await audit(message.from_user.id, 'required_channel_add', str(data['chat_id']))
    await state.clear()
    await message.answer('✅ Majburiy kanal saqlandi.', reply_markup=admin_main())


@router.callback_query(F.data.startswith('admin:channel_toggle:'))
async def channel_toggle(call: CallbackQuery) -> None:
    cid = int(call.data.split(':')[2])
    async with SessionLocal() as session:
        channel = await session.get(RequiredChannel, cid)
        if channel:
            channel.is_active = not channel.is_active
            await session.commit()
    await audit(call.from_user.id, 'required_channel_toggle', str(cid))
    await call.answer('✅ Holat yangilandi')


@router.callback_query(F.data == 'admin:reactions')
async def reactions(call: CallbackQuery) -> None:
    await call.answer()
    enabled = await get_bool('reaction_enabled', False)
    emojis = await get_setting('reaction_emojis', '🔥,❤️,👏')
    big = await get_bool('reaction_big', False)
    await call.message.answer(f'<b>❤️ REACTION SOZLAMALARI</b>\n\nHolat: {"🟢 ON" if enabled else "🔴 OFF"}\nReactionlar: <code>{emojis}</code>\nKatta reaction: {"🟢" if big else "🔴"}', reply_markup=kb([
        [('🟢/🔴 ON/OFF', 'admin:reaction_toggle')],
        [('✏️ Reactionlarni o‘zgartirish', 'admin:reaction_edit')],
        [('✨ Big reaction ON/OFF', 'admin:reaction_big')],
    ]))


@router.callback_query(F.data == 'admin:reaction_toggle')
async def reaction_toggle(call: CallbackQuery) -> None:
    current = await get_bool('reaction_enabled', False)
    await set_setting('reaction_enabled', '0' if current else '1')
    await audit(call.from_user.id, 'reaction_toggle', str(not current))
    await call.answer('✅ Yangilandi')


@router.callback_query(F.data == 'admin:reaction_big')
async def reaction_big(call: CallbackQuery) -> None:
    current = await get_bool('reaction_big', False)
    await set_setting('reaction_big', '0' if current else '1')
    await audit(call.from_user.id, 'reaction_big', str(not current))
    await call.answer('✅ Yangilandi')


@router.callback_query(F.data == 'admin:reaction_edit')
async def reaction_edit(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    await state.set_state(AdminReactionState.waiting_emojis)
    await call.message.answer('❤️ Emoji larni vergul bilan yuboring. Masalan: <code>🔥,❤️,👏,😍</code>')


@router.message(AdminReactionState.waiting_emojis)
async def reaction_save(message: Message, state: FSMContext) -> None:
    raw = ','.join(x.strip() for x in message.text.split(',') if x.strip())
    await set_setting('reaction_emojis', raw[:300])
    await audit(message.from_user.id, 'reaction_emojis', raw[:300])
    await state.clear()
    await message.answer('✅ Reactionlar saqlandi.', reply_markup=admin_main())


@router.callback_query(F.data == 'admin:target')
async def target(call: CallbackQuery) -> None:
    from app.config import get_settings
    await call.answer()
    current = await get_setting('target_channel_id', get_settings().target_channel_id)
    await call.message.answer(f'📢 <b>TARGET KANAL</b>\n\nHozirgi qiymat: <code>{current or "berilmagan"}</code>', reply_markup=kb([[('✏️ Target kanal ID', 'setting:target_channel_id')]]))


@router.callback_query(F.data == 'admin:channel_post')
async def channel_post_start(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    await state.set_state(AdminChannelPostState.waiting_message)
    await call.message.answer('📣 Kanalga yuboriladigan xabarni jo‘nating. Rasm/video/matn qabul qilinadi.')


@router.message(AdminChannelPostState.waiting_message)
async def channel_post_send(message: Message, state: FSMContext, bot) -> None:
    from app.config import get_settings
    raw_id = (await __import__('app.services.settings', fromlist=['get_setting']).get_setting('target_channel_id', get_settings().target_channel_id)).strip()
    if not raw_id:
        await state.clear()
        await message.answer('❌ TARGET_CHANNEL_ID sozlanmagan.', reply_markup=admin_main())
        return
    try:
        target_id = int(raw_id)
        sent = await bot.copy_message(chat_id=target_id, from_chat_id=message.chat.id, message_id=message.message_id)
        reacted = await react_to_message(bot, target_id, sent.message_id)
        await audit(message.from_user.id, 'channel_post', f'channel={target_id},message={sent.message_id},reaction={reacted}')
        await state.clear()
        await message.answer(f'✅ Kanalga yuborildi. Reaction: {"🟢" if reacted else "⚪"}', reply_markup=admin_main())
    except Exception as exc:
        await state.clear()
        await message.answer(f'❌ Yuborishda xato: <code>{str(exc)[:250]}</code>', reply_markup=admin_main())
