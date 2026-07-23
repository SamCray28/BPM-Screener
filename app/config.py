"""Central configuration. Every environment variable the platform needs
is declared here with a safe default so the app can boot without any
of them set (mock providers only) — nothing is hardcoded, and every API
key has a documented, empty-by-default env var slot per the brief's
"if an API key is required, create the configuration automatically"
instruction. No real key is ever committed; see .env.example.
"""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Core ---
    APP_ENV: str = "development"
    APP_NAME: str = "BPM Behavioral Intelligence Platform"
    APP_VERSION: str = "4.0.0"
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: str = ""

    # --- Database ---
    DATABASE_URL: str = "sqlite+aiosqlite:///./bpm_dev.db"

    # --- TradingView webhook (same contract as the bpm-python receiver) ---
    BPM_WEBHOOK_SECRET: str = ""
    ALLOWED_SCHEMA_VERSIONS: str = "1.1"
    ALLOWED_FORMULA_VERSIONS: str = "bpm-3.0.1"
    MAX_REQUEST_BYTES: int = 32768

    # --- Market data provider: Polygon.io (https://polygon.io/docs) ---
    POLYGON_API_KEY: str = ""
    POLYGON_REST_BASE_URL: str = "https://api.polygon.io"
    POLYGON_WS_URL: str = "wss://socket.polygon.io/stocks"
    MARKET_DATA_PROVIDER: str = "mock"  # "mock" | "polygon"

    # --- News provider: Polygon.io news endpoint (same vendor, separate concern) ---
    NEWS_PROVIDER: str = "mock"  # "mock" | "polygon"

    # --- Corporate events provider: Finnhub (https://finnhub.io/docs/api) ---
    FINNHUB_API_KEY: str = ""
    FINNHUB_BASE_URL: str = "https://finnhub.io/api/v1"
    CORPORATE_EVENTS_PROVIDER: str = "mock"  # "mock" | "finnhub"

    # --- SEC filings: EDGAR (free, public, no key required) ---
    SEC_EDGAR_USER_AGENT: str = "BPM Platform research@example.com"
    SEC_EDGAR_BASE_URL: str = "https://data.sec.gov"
    FILINGS_PROVIDER: str = "mock"  # "mock" | "sec_edgar"

    # --- Sentiment provider ---
    SENTIMENT_PROVIDER: str = "mock"  # "mock" | "rule_based"

    # --- Universe / scanning ---
    UNIVERSE_MAX_SHARE_PRICE: float = 50.0
    UNIVERSE_MIN_AVG_DAILY_VOLUME: float = 300_000.0
    UNIVERSE_MIN_AVG_DAILY_DOLLAR_VOLUME: float = 5_000_000.0
    UNIVERSE_MIN_RELATIVE_VOLUME: float = 1.0
    UNIVERSE_REFRESH_SECONDS: int = 60
    RANKING_REFRESH_SECONDS: int = 60

    # --- Scheduler leader election (multi-instance safety) ---
    # Only meaningful against Postgres (uses pg_try_advisory_lock); a
    # SQLite DATABASE_URL always runs as leader, since that only ever
    # happens in single-instance local dev/test.
    SCHEDULER_LEADER_ELECTION_ENABLED: bool = True
    SCHEDULER_LEADER_LOCK_KEY: int = 727271
    SCHEDULER_LEADER_RETRY_SECONDS: int = 15

    # --- HTTP client behavior (shared by every real provider) ---
    HTTP_TIMEOUT_SECONDS: float = 10.0
    HTTP_MAX_RETRIES: int = 3
    HTTP_RETRY_BACKOFF_SECONDS: float = 0.5
    HTTP_RATE_LIMIT_PER_SECOND: float = 5.0
    HTTP_CACHE_TTL_SECONDS: float = 5.0

    # --- Historical sample gating ---
    HISTORICAL_MIN_SAMPLE_SIZE: int = 20

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def allowed_schema_versions(self) -> List[str]:
        return [v.strip() for v in self.ALLOWED_SCHEMA_VERSIONS.split(",") if v.strip()]

    @property
    def allowed_formula_versions(self) -> List[str]:
        return [v.strip() for v in self.ALLOWED_FORMULA_VERSIONS.split(",") if v.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
