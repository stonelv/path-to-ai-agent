import json

import httpx
import pytest
import respx

from baggage_extractor.config import Settings
from baggage_extractor.providers import (
    ChatMessage,
    ChatRole,
    ModelRequest,
    OpenAICompatibleProvider,
)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        model_api_key="test-key",
        model_name="test-model",
        model_base_url="https://models.example.com/v1/",
        model_timeout_seconds=10,
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
    provider = OpenAICompatibleProvider(settings)
    request = ModelRequest(
        messages=(
            ChatMessage(role=ChatRole.SYSTEM, content="只根据原文回答。"),
            ChatMessage(role=ChatRole.USER, content="经济舱可托运一件23公斤行李。"),
        ),
        temperature=0.2,
        max_output_tokens=200,
    )

    response = await provider.generate(request)

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
        return_value=httpx.Response(
            200,
            json={"model": "test-model", "choices": []},
        )
    )

    with pytest.raises(ValueError, match="did not contain any choices"):
        await OpenAICompatibleProvider(settings).generate(
            ModelRequest(
                messages=(ChatMessage(role=ChatRole.USER, content="policy"),),
            )
        )


@respx.mock
async def test_generate_rejects_empty_content(settings: Settings) -> None:
    respx.post("https://models.example.com/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "model": "test-model",
                "choices": [{"message": {"content": ""}}],
            },
        )
    )

    with pytest.raises(ValueError, match="empty content"):
        await OpenAICompatibleProvider(settings).generate(
            ModelRequest(
                messages=(ChatMessage(role=ChatRole.USER, content="policy"),),
            )
        )
