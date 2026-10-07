from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def kb(rows: list[list[tuple[str, str]]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=text, callback_data=data) for text, data in row] for row in rows])


def url_kb(rows: list[list[tuple[str, str]]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=text, url=url) for text, url in row] for row in rows])


def mixed_kb(callback_rows: list[list[tuple[str, str]]] | None = None, url_rows: list[list[tuple[str, str]]] | None = None) -> InlineKeyboardMarkup:
    buttons = []
    for row in url_rows or []:
        buttons.append([InlineKeyboardButton(text=text, url=url) for text, url in row])
    for row in callback_rows or []:
        buttons.append([InlineKeyboardButton(text=text, callback_data=data) for text, data in row])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back(callback: str = 'user:home') -> InlineKeyboardMarkup:
    return kb([[('⬅️ Orqaga', callback)]])
