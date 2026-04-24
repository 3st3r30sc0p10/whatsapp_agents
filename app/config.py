from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    anthropic_api_key: str
    kapso_api_key: str
    kapso_webhook_secret: str
    mem0_api_key: str
    supabase_url: str
    supabase_key: str
    app_env: Literal["development", "production"] = "development"
    log_level: str = "INFO"
    max_memory_results: int = 5
    agent_model: str = "claude-sonnet-4-6"
    admin_api_key: str | None = None
    kapso_verify_token: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
