from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env relative to this file so settings load identically regardless
# of CWD (uvicorn launched from project root vs apps/api both work).
_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE), env_file_encoding="utf-8", extra="ignore"
    )

    database_url: str = "postgresql+asyncpg://ngti:ngti@localhost:5432/ngti"
    redis_url: str = "redis://localhost:6379/0"
    debug: bool = False

    llm_mode: Literal["fake", "real"] = "fake"
    llm_model_fast: str = "claude-haiku-4-5-20251001"
    llm_model_smart: str = "claude-sonnet-4-6"
    llm_model_premium: str = "claude-opus-4-7"

    # Per-task overrides (empty = use routing default). Format: model ID string.
    llm_model_summarize_market: str = ""
    llm_model_explain_signal: str = ""
    llm_model_narrate_scenario: str = ""
    llm_model_review_journal_entry: str = ""
    llm_model_extract_event: str = ""
    adapter_market: str = "mock"
    adapter_energy: str = "mock"
    adapter_weather: str = "mock"
    adapter_positioning: str = "mock"
    adapter_news: str = "mock"
    anthropic_api_key: str = ""
    eia_api_key: str = ""
    redis_ttl_market_summary: int = 1800   # 30 min
    redis_ttl_scenario: int = 86400         # 24h


settings = Settings()
