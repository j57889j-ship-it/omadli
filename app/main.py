from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand, Update
from fastapi import FastAPI, Header, HTTPException, Request
from redis.asyncio import from_url

from app.config import get_settings
from app.db.seed import seed_defaults
from app.db.session import engine, init_db
from app.handlers import ALL_ROUTERS
from app.middlewares.maintenance import MaintenanceMiddleware
from app.middlewares.rate_limit import RateLimitMiddleware

settings = get_settings()
logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO), format='%(asctime)s | %(levelname)s | %(name)s | %(message)s')
logger = logging.getLogger('kitobxonlar_v29')

redis = from_url(settings.redis_url, encoding='utf-8', decode_responses=True, health_check_interval=30)
storage = RedisStorage.from_url(settings.redis_url, state_ttl=86400, data_ttl=86400)
bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML, link_preview_is_disabled=True))
dp = Dispatcher(storage=storage)

for router in ALL_ROUTERS:
    dp.include_router(router)

dp.message.outer_middleware(MaintenanceMiddleware())
dp.callback_query.outer_middleware(MaintenanceMiddleware())
dp.message.outer_middleware(RateLimitMiddleware(redis))
dp.callback_query.outer_middleware(RateLimitMiddleware(redis))

_polling_task: asyncio.Task | None = None


async def set_commands() -> None:
    await bot.set_my_commands([
        BotCommand(command='start', description='Botni boshlash'),
        BotCommand(command='admin', description='Admin markaz'),
        BotCommand(command='cancel', description='Joriy amalni bekor qilish'),
    ])


async def lifespan(app: FastAPI):
    global _polling_task
    await init_db()
    await seed_defaults()
    await set_commands()
    if settings.webhook_endpoint:
        await bot.set_webhook(
            url=settings.webhook_endpoint,
            secret_token=settings.webhook_secret,
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=False,
        )
        logger.info('Webhook configured: %s', settings.webhook_endpoint)
    else:
        await bot.delete_webhook(drop_pending_updates=False)
        _polling_task = asyncio.create_task(dp.start_polling(bot, handle_signals=False))
        logger.info('Polling enabled')
    yield
    if _polling_task:
        _polling_task.cancel()
        try:
            await _polling_task
        except asyncio.CancelledError:
            pass
    else:
        try:
            await bot.delete_webhook(drop_pending_updates=False)
        except TelegramAPIError:
            pass
    await bot.session.close()
    await storage.close()
    await redis.aclose()
    await engine.dispose()


app = FastAPI(title=settings.app_name, version='29.0.0', lifespan=lifespan)


@app.get('/')
async def root() -> dict[str, str]:
    return {'status': 'ok', 'service': settings.app_name, 'version': '29.0.0'}


@app.get('/health')
async def health() -> dict[str, str]:
    return {'status': 'healthy', 'version': '29.0.0'}


@app.post('/webhook')
async def webhook(request: Request, x_telegram_bot_api_secret_token: str | None = Header(default=None)) -> dict[str, bool]:
    if settings.webhook_endpoint and x_telegram_bot_api_secret_token != settings.webhook_secret:
        raise HTTPException(status_code=401, detail='Invalid webhook secret')
    payload = await request.json()
    update = Update.model_validate(payload, context={'bot': bot})
    await dp.feed_update(bot, update)
    return {'ok': True}
