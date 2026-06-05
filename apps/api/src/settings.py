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
    # Force TLS on the DB connection. Managed Postgres (Timescale Cloud, etc.)
    # requires it; left False for local/compose. A URL carrying
    # `sslmode=require` also turns TLS on automatically (see db/engine.py).
    database_ssl: bool = False
    redis_url: str = "redis://localhost:6379/0"
    debug: bool = False

    # Comma-separated browser origins permitted to call this API. Defaults
    # cover the local dev URLs; in prod, set CORS_ALLOWED_ORIGINS to the
    # deployed web origin (e.g. "https://app.example.com").
    cors_allowed_origins: str = (
        "http://localhost:3000,http://127.0.0.1:3000,"
        "http://localhost:3001,http://127.0.0.1:3001"
    )

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
    redis_ttl_chart_indicator: int = 300    # 5 min


settings = Settings()
