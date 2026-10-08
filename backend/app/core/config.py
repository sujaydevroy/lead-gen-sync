"""Application settings, read from environment variables / backend/.env."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent
SCHEMA = "dcp"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    environment: Literal["development", "test", "production"] = "development"

    # Database ----------------------------------------------------------------
    database_url: str = Field(..., description="postgresql://user:password@host:5432/db (URL-encode the password)")
    # Set true when connecting through a transaction pooler (e.g. Supabase port 6543).
    db_disable_prepared_statements: bool = False
    db_pool_size: int = 5
    db_max_overflow: int = 10

    # Auth --------------------------------------------------------------------
    jwt_secret: str = Field(..., min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days_remember: int = 30
    refresh_token_hours: int = 12
    cookie_secure: bool = True
    login_max_failed_attempts: int = 5
    login_lockout_minutes: int = 15
    login_rate_limit_per_minute: int = 10
    password_reset_minutes: int = 60

    # Files -------------------------------------------------------------------
    storage_backend: Literal["local"] = "local"
    storage_local_dir: Path = BACKEND_DIR / "storage"
    max_upload_mb: int = 10
    max_sales_rows: int = 50_000
    sample_sales_file: Path = PROJECT_ROOT / "frontend" / "public" / "samples" / "sample_sales.xlsx"

    # Web ---------------------------------------------------------------------
    frontend_origin: str = "http://localhost:3000"

    @field_validator("database_url")
    @classmethod
    def _use_psycopg_driver(cls, value: str) -> str:
        """Accept plain postgresql:// URLs and select the psycopg 3 driver."""
        for prefix in ("postgresql://", "postgres://"):
            if value.startswith(prefix):
                return "postgresql+psycopg://" + value[len(prefix) :]
        return value

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
