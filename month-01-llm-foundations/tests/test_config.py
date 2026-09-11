import pytest
from pydantic import ValidationError

from baggage_extractor.config import Settings, StructuredOutputMode


def test_settings_read_environment_variables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MODEL_API_KEY", "test-key")
    monkeypatch.setenv("MODEL_NAME", "test-model")
    monkeypatch.setenv("MODEL_BASE_URL", "https://example.com/v1/")
    monkeypatch.setenv("MODEL_STRUCTURED_OUTPUT_MODE", "json_object")
    monkeypatch.setenv("MODEL_CONNECT_TIMEOUT_SECONDS", "5")
    monkeypatch.setenv("MODEL_READ_TIMEOUT_SECONDS", "15")

    settings = Settings(_env_file=None)  # pyright: ignore[reportCallIssue]

    assert settings.model_api_key.get_secret_value() == "test-key"
    assert settings.model_name == "test-model"
    assert settings.model_base_url == "https://example.com/v1"
    assert settings.model_structured_output_mode is StructuredOutputMode.JSON_OBJECT
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


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("model_api_key", ""),
        ("model_api_key", " \t"),
        ("model_name", " \t"),
        ("model_base_url", "/"),
        ("model_base_url", "models.example.com/v1"),
        ("model_base_url", "ftp://models.example.com"),
        ("model_base_url", "https://models.example.com/v1?version=1"),
        ("model_base_url", "https://models.example.com/v1#fragment"),
        ("model_base_url", "https://user:password@models.example.com/v1"),
        ("model_connect_timeout_seconds", float("inf")),
        ("model_read_timeout_seconds", float("nan")),
        ("model_read_timeout_seconds", float("inf")),
        ("model_structured_output_mode", "unsupported"),
    ],
)
def test_settings_reject_invalid_connection_configuration(field: str, value: object) -> None:
    values = {
        "model_api_key": "test-key",
        "model_name": "test-model",
        "model_base_url": "https://models.example.com/v1",
        field: value,
    }

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None, **values)

    assert any(error["loc"] == (field,) for error in exc_info.value.errors())


def test_settings_allow_local_http_endpoint() -> None:
    settings = Settings(
        model_api_key="test-key",
        model_name="test-model",
        model_base_url="http://localhost:8000/v1/",
        _env_file=None,
    )

    assert settings.model_base_url == "http://localhost:8000/v1"


def test_settings_validation_message_does_not_include_input_values() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            model_api_key="test-key",
            model_name="test-model",
            model_base_url="https://models.example.com/v1?key=test-secret",
            _env_file=None,
        )

    assert "model_base_url" in str(exc_info.value)
    assert "test-secret" not in str(exc_info.value)