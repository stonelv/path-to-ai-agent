import pytest
from pydantic import ValidationError

from baggage_extractor.config import Settings


def test_settings_read_environment_variables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MODEL_API_KEY", "test-key")
    monkeypatch.setenv("MODEL_NAME", "test-model")
    monkeypatch.setenv("MODEL_BASE_URL", "https://example.com/v1/")
    monkeypatch.setenv("MODEL_CONNECT_TIMEOUT_SECONDS", "5")
    monkeypatch.setenv("MODEL_READ_TIMEOUT_SECONDS", "15")

    settings = Settings(_env_file=None)  # pyright: ignore[reportCallIssue]

    assert settings.model_api_key.get_secret_value() == "test-key"
    assert settings.model_name == "test-model"
    assert settings.model_base_url == "https://example.com/v1"
    assert settings.model_connect_timeout_seconds == 5
    assert settings.model_read_timeout_seconds == 15


def test_settings_reject_non_positive_read_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MODEL_API_KEY", "test-key")
    monkeypatch.setenv("MODEL_NAME", "test-model")
    monkeypatch.setenv("MODEL_BASE_URL", "https://example.com/v1")
    monkeypatch.setenv("MODEL_READ_TIMEOUT_SECONDS", "0")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # pyright: ignore[reportCallIssue]