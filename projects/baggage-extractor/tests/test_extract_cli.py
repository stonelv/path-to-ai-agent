import json

import pytest

from baggage_extractor.config import Settings
from baggage_extractor.extract_cli import main
from baggage_extractor.providers import ModelRequest, ModelResponse, RateLimitError


class StubProvider:
    def __init__(self, *, error: RateLimitError | None = None) -> None:
        self.error = error

    async def generate(self, request: ModelRequest) -> ModelResponse:
        if self.error is not None:
            raise self.error
        return ModelResponse(
            content=json.dumps(
                {
                    "airline_code": "CA",
                    "airline_name": "中国国际航空",
                    "free_baggage_rules": [],
                    "baggage_rules": [],
                },
                ensure_ascii=False,
            ),
            model="stub-model",
        )


def test_main_prints_formatted_json(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["经济舱可免费托运行李。"], provider=StubProvider())

    captured = capsys.readouterr()
    assert exit_code == 0
    assert json.loads(captured.out) == {
        "airline_code": "CA",
        "airline_name": "中国国际航空",
        "free_baggage_rules": [],
        "baggage_rules": [],
    }
    assert captured.err == ""


def test_main_reports_extraction_error_to_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main([" "], provider=StubProvider())

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert "must not be blank" in captured.err


def test_main_preserves_provider_error_without_printing_credentials(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(
        ["policy"],
        provider=StubProvider(error=RateLimitError("rate limited", retryable=True)),
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert "rate limited" in captured.err
    assert "API" not in captured.err


def test_main_reports_invalid_configuration_without_input_values(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def invalid_settings() -> Settings:
        return Settings(
            model_api_key="test-secret",
            model_name="test-model",
            model_base_url="https://models.example.com?key=test-secret",
            _env_file=None,
        )

    monkeypatch.setattr("baggage_extractor.extract_cli.get_settings", invalid_settings)
    monkeypatch.setattr(
        "baggage_extractor.extract_cli.OpenAICompatibleProvider", lambda settings: StubProvider()
    )

    assert main(["policy"]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Invalid model configuration" in captured.err
    assert "model_base_url" in captured.err
    assert "test-secret" not in captured.err


def test_main_keeps_explicit_provider_even_if_falsey(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    class FalseyProvider(StubProvider):
        def __bool__(self) -> bool:
            return False

    def unexpected_settings() -> Settings:
        raise AssertionError("An injected provider must not load settings.")

    monkeypatch.setattr("baggage_extractor.extract_cli.get_settings", unexpected_settings)

    assert main(["policy"], provider=FalseyProvider()) == 0
    assert capsys.readouterr().err == ""
