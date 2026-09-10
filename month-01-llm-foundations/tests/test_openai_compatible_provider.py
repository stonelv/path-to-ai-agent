import json

import httpx
import pytest
import respx

from baggage_extractor.config import Settings
from baggage_extractor.providers import (
    AuthenticationError,
    ChatMessage,
    ChatRole,
    InvalidRequestError,
    ModelRequest,
    OpenAICompatibleProvider,
    RateLimitError,
    ServerError,
)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        model_api_key="test-key",
        model_name="test-model",
        model_base_url="https://models.example.com/v1/",
        model_connect_timeout_seconds=5,
        model_read_timeout_seconds=10,
        model_max_retries=2,
        model_retry_backoff_seconds=0,
        _env_file=None,
    )


@respx.mock
async def test_generate_sends_request_and_parses_response(settings: Settings) -> None:
    route = respx.post("https://models.example.com/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            headers={"x-request-id": "request-123"},
            json={
                "model": "test-model-2026-09",
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "可免费托运一件，每件不超过23公斤。",
                        }
                    }
                ],
            },
        )
    )
    request = ModelRequest(
        messages=(
            ChatMessage(role=ChatRole.SYSTEM, content="只根据原文回答。"),
            ChatMessage(role=ChatRole.USER, content="经济舱可托运一件23公斤行李。"),
        ),
        temperature=0.2,
        max_output_tokens=200,
    )

    response = await OpenAICompatibleProvider(settings).generate(request)

    assert route.called
    sent_request = route.calls.last.request
    assert sent_request.headers["Authorization"] == "Bearer test-key"
    assert json.loads(sent_request.content) == {
        "model": "test-model",
        "messages": [
            {"role": "system", "content": "只根据原文回答。"},
            {"role": "user", "content": "经济舱可托运一件23公斤行李。"},
        ],
        "temperature": 0.2,
        "max_tokens": 200,
    }
    assert response.content == "可免费托运一件，每件不超过23公斤。"
    assert response.model == "test-model-2026-09"
    assert response.request_id == "request-123"


@respx.mock
async def test_generate_rejects_response_without_choices(settings: Settings) -> None:
    respx.post("https://models.example.com/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={"model": "test-model", "choices": []})
    )

    with pytest.raises(ValueError, match="did not contain any choices"):
        await OpenAICompatibleProvider(settings).generate(
            ModelRequest(messages=(ChatMessage(role=ChatRole.USER, content="policy"),))
        )


@respx.mock
async def test_generate_rejects_empty_content(settings: Settings) -> None:
    respx.post("https://models.example.com/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={"model": "test-model", "choices": [{"message": {"content": ""}}]},
        )
    )

    with pytest.raises(ValueError, match="empty content"):
        await OpenAICompatibleProvider(settings).generate(
            ModelRequest(messages=(ChatMessage(role=ChatRole.USER, content="policy"),))
        )


@pytest.mark.parametrize(
    ("status_code", "error_type", "expected_calls"),
    [
        (401, AuthenticationError, 1),
        (429, RateLimitError, 3),
        (500, ServerError, 3),
        (400, InvalidRequestError, 1),
    ],
)
@respx.mock
async def test_generate_classifies_http_errors(
    settings: Settings,
    status_code: int,
    error_type: type[Exception],
    expected_calls: int,
) -> None:
    route = respx.post("https://models.example.com/v1/chat/completions").mock(
        return_value=httpx.Response(status_code)
    )

    with pytest.raises(error_type):
        await OpenAICompatibleProvider(settings).generate(
            ModelRequest(messages=(ChatMessage(role=ChatRole.USER, content="policy"),))
        )

    assert route.call_count == expected_calls


@respx.mock
async def test_generate_retries_rate_limit_then_succeeds(settings: Settings) -> None:
    route = respx.post("https://models.example.com/v1/chat/completions").mock(
        side_effect=[
            httpx.Response(429),
            httpx.Response(
                200,
                json={"model": "test-model", "choices": [{"message": {"content": "success"}}]},
            ),
        ]
    )

    response = await OpenAICompatibleProvider(settings).generate(
        ModelRequest(messages=(ChatMessage(role=ChatRole.USER, content="policy"),))
    )

    assert response.content == "success"
    assert route.call_count == 2
