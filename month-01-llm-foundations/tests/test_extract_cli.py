import json

import pytest

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
