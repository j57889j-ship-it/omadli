from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

router = Router(name='common')


@router.message(F.text == '/cancel')
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer('❌ Joriy amal bekor qilindi.')
