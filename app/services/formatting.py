from __future__ import annotations

from html import escape


def e(value: object) -> str:
    return escape(str(value))


def bar(value: float, width: int = 10) -> str:
    value = max(0.0, min(1.0, value))
    filled = round(value * width)
    return '█' * filled + '░' * (width - filled)


def pct(part: int, total: int) -> int:
    return round((part / total) * 100) if total else 0


def user_label(username: str | None, full_name: str) -> str:
    return f'@{e(username)}' if username else e(full_name)


def panel(title: str, body: str) -> str:
    return f'<b>╭──────────────╮\n   {e(title)}\n╰──────────────╯</b>\n\n{body}'
