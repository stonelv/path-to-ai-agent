from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_api_key: SecretStr
    model_name: str = Field(min_length=1)
    model_base_url: str = Field(min_length=1)
    model_connect_timeout_seconds: float = Field(default=10, gt=0)
    model_read_timeout_seconds: float = Field(default=30, gt=0)
    model_max_retries: int = Field(default=2, ge=0, le=5)
    model_retry_backoff_seconds: float = Field(default=0.5, ge=0, le=30)
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("model_base_url")
    @classmethod
    def normalize_model_base_url(cls, value: str) -> str:
        return value.rstrip("/")


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]