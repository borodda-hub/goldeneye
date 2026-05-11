from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://ngti:ngti@localhost:5432/ngti"
    redis_url: str = "redis://localhost:6379/0"
    debug: bool = False

    llm_mode: Literal["fake", "real"] = "fake"
    llm_model_fast: str = "claude-haiku-4-5-20251001"
    llm_model_smart: str = "claude-sonnet-4-6"
    adapter_market: str = "mock"
    adapter_energy: str = "mock"
    adapter_weather: str = "mock"
    adapter_positioning: str = "mock"
    adapter_news: str = "mock"
    anthropic_api_key: str = ""
    redis_ttl_market_summary: int = 1800   # 30 min
    redis_ttl_scenario: int = 86400         # 24h


settings = Settings()
