from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import Field, HttpUrl, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class StructuredOutputMode(StrEnum):
    JSON_SCHEMA = "json_schema"
    JSON_OBJECT = "json_object"


class Settings(BaseSettings):
    model_api_key: SecretStr
    model_name: str = Field(min_length=1, pattern=r".*\S.*")
    model_base_url: str = Field(min_length=1)
    model_structured_output_mode: StructuredOutputMode = StructuredOutputMode.JSON_SCHEMA
    model_connect_timeout_seconds: float = Field(default=10, gt=0, allow_inf_nan=False)
    model_read_timeout_seconds: float = Field(default=30, gt=0, allow_inf_nan=False)
    model_max_retries: int = Field(default=2, ge=0, le=5)
    model_retry_backoff_seconds: float = Field(default=0.5, ge=0, le=30)
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        hide_input_in_errors=True,
    )

    @field_validator("model_base_url")
    @classmethod
    def normalize_model_base_url(cls, value: str) -> str:
        url = HttpUrl(value)
        if url.query is not None or url.fragment is not None or url.username or url.password:
            raise ValueError("Model base URL must not contain a query, fragment or credentials.")
        return str(url).rstrip("/")

    @field_validator("model_api_key")
    @classmethod
    def validate_model_api_key(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().strip():
            raise ValueError("Model API key must not be blank.")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]