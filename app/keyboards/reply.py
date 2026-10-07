from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def user_main() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='📚 KITOBLAR'), KeyboardButton(text='🧠 TESTLAR')],
            [KeyboardButton(text='🏆 REYTING'), KeyboardButton(text='👤 PROFIL')],
            [KeyboardButton(text='🎁 BONUSLAR'), KeyboardButton(text='ℹ️ YORDAM')],
        ], resize_keyboard=True, is_persistent=True,
    )


def admin_main() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='📊 BOSHQARUV'), KeyboardButton(text='📚 KONTENT')],
            [KeyboardButton(text='👥 FOYDALANUVCHILAR'), KeyboardButton(text='🏆 REYTINGLAR')],
            [KeyboardButton(text='🎁 BONUSLAR'), KeyboardButton(text='📢 KANAL')],
            [KeyboardButton(text='🛠 TIZIM'), KeyboardButton(text='🏠 USER MENYU')],
        ], resize_keyboard=True, is_persistent=True,
    )
