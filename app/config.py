from __future__ import annotations

from functools import lru_cache
from urllib.parse import urlparse

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    bot_token: str = Field(alias='BOT_TOKEN')
    admin_ids: str = Field(default='', alias='ADMIN_IDS')
    database_url: str = Field(alias='DATABASE_URL')
    redis_url: str = Field(alias='REDIS_URL')
    target_channel_id: str = Field(default='', alias='TARGET_CHANNEL_ID')
    webhook_url: str = Field(default='', alias='WEBHOOK_URL')
    webhook_secret: str = Field(default='change-me', alias='WEBHOOK_SECRET')
    app_name: str = Field(default='Kitobxonlar Quiz V29', alias='APP_NAME')
    log_level: str = Field(default='INFO', alias='LOG_LEVEL')

    @property
    def parsed_admin_ids(self) -> set[int]:
        ids: set[int] = set()
        for raw in self.admin_ids.split(','):
            raw = raw.strip()
            if raw:
                try:
                    ids.add(int(raw))
                except ValueError:
                    pass
        return ids

    @property
    def normalized_database_url(self) -> str:
        url = self.database_url.strip()
        if url.startswith('postgres://'):
            return 'postgresql+asyncpg://' + url[len('postgres://'):]
        if url.startswith('postgresql://'):
            return 'postgresql+asyncpg://' + url[len('postgresql://'):]
        if url.startswith('postgresql+asyncpg://'):
            return url
        raise ValueError('DATABASE_URL must be a PostgreSQL URL')

    @property
    def webhook_endpoint(self) -> str:
        if self.webhook_url.strip():
            return self.webhook_url.rstrip('/') + '/webhook'
        return ''

    def validate_runtime(self) -> None:
        if not self.bot_token:
            raise ValueError('BOT_TOKEN is required')
        if not self.database_url:
            raise ValueError('DATABASE_URL is required')
        if not self.redis_url:
            raise ValueError('REDIS_URL is required')
        if self.webhook_url:
            parsed = urlparse(self.webhook_url)
            if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
                raise ValueError('WEBHOOK_URL must be a full http(s) URL')


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_runtime()
    return settings
