import asyncio
import importlib
import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
import pytest
from fastapi import FastAPI
from pydantic import ValidationError

from baggage_extractor.api import create_app
from baggage_extractor.config import Settings
from baggage_extractor.extractor import MAX_POLICY_TEXT_LENGTH, BaggageExtractor
from baggage_extractor.providers import (
    AuthenticationError,
    InvalidRequestError,
    ModelRequest,
    ModelResponse,
    ProviderConnectionError,
    ProviderTimeoutError,
    RateLimitError,
    ServerError,
)


def valid_result() -> dict[str, object]:
    return {
        "airline_code": None,
        "airline_name": "示例航空",
        "free_baggage_rules": [
            {
                "cabin_class": "经济舱",
                "fare_codes": [],
                "checked_baggage": "23kg",
                "pieces": 1,
                "size_limit": {
                    "length": None,
                    "width": None,
                    "height": None,
                    "note": "",
                },
                "special_notes": "",
            }
        ],
        "baggage_rules": [],
    }


class StubProvider:
    def __init__(
        self,
        *,
        content: str | None = None,
        error: Exception | None = None,
    ) -> None:
        self.content = content or json.dumps(valid_result(), ensure_ascii=False)
        self.error = error
        self.calls = 0

    async def generate(self, request: ModelRequest) -> ModelResponse:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return ModelResponse(content=self.content, model="stub-model")


class BlockingProvider(StubProvider):
    def __init__(self) -> None:
        super().__init__()
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def generate(self, request: ModelRequest) -> ModelResponse:
        self.calls += 1
        self.started.set()
        await self.release.wait()
        return ModelResponse(content=self.content, model="stub-model")


@asynccontextmanager
async def api_client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest.mark.asyncio
async def test_health_and_ready_do_not_call_model() -> None:
    provider = StubProvider()
    app = create_app(extractor=BaggageExtractor(provider))

    async with api_client(app) as client:
        health = await client.get("/health")
        ready = await client.get("/ready")

    assert health.json() == {"status": "ok"}
    assert ready.json() == {"status": "ready"}
    assert provider.calls == 0


@pytest.mark.asyncio
async def test_extraction_returns_domain_result_and_request_id() -> None:
    provider = StubProvider()
    app = create_app(extractor=BaggageExtractor(provider))

    async with api_client(app) as client:
        response = await client.post(
            "/v1/extractions",
            json={"text": "经济舱可免费托运1件23kg行李。"},
            headers={"X-Request-ID": "client-request-123"},
        )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "client-request-123"
    assert response.json() == {
        "request_id": "client-request-123",
        "result": valid_result(),
    }
    assert provider.calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("text", [" ", "x" * (MAX_POLICY_TEXT_LENGTH + 1)])
async def test_extraction_rejects_invalid_text_before_model_call(text: str) -> None:
    provider = StubProvider()
    app = create_app(extractor=BaggageExtractor(provider))

    async with api_client(app) as client:
        response = await client.post("/v1/extractions", json={"text": text})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
    assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]
    assert provider.calls == 0


@pytest.mark.asyncio
async def test_invalid_client_request_id_is_replaced() -> None:
    app = create_app(extractor=BaggageExtractor(StubProvider()))

    async with api_client(app) as client:
        response = await client.get(
            "/health",
            headers={"X-Request-ID": "invalid request id"},
        )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] != "invalid request id"
    assert len(response.headers["X-Request-ID"]) == 36


@pytest.mark.asyncio
async def test_request_log_does_not_include_policy_text(
    caplog: pytest.LogCaptureFixture,
) -> None:
    policy_text = "不得记录的合成政策正文"
    app = create_app(extractor=BaggageExtractor(StubProvider()))

    with caplog.at_level(logging.INFO, logger="baggage_extractor.api.app"):
        async with api_client(app) as client:
            response = await client.post(
                "/v1/extractions",
                json={"text": policy_text},
            )

    assert response.status_code == 200
    assert policy_text not in caplog.text
    assert "path=/v1/extractions" in caplog.text
    assert response.headers["X-Request-ID"] in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "status_code", "code"),
    [
        (AuthenticationError("secret details"), 503, "model_authentication_failed"),
        (RateLimitError("secret details", retryable=True), 503, "model_rate_limited"),
        (ProviderTimeoutError("secret details", retryable=True), 504, "model_timeout"),
        (ProviderConnectionError("secret details", retryable=True), 502, "model_unavailable"),
        (ServerError("secret details", retryable=True), 502, "model_unavailable"),
        (InvalidRequestError("secret details"), 502, "model_request_rejected"),
    ],
)
async def test_provider_errors_map_to_stable_responses(
    error: Exception,
    status_code: int,
    code: str,
) -> None:
    app = create_app(extractor=BaggageExtractor(StubProvider(error=error)))

    async with api_client(app) as client:
        response = await client.post("/v1/extractions", json={"text": "合成政策"})

    assert response.status_code == status_code
    assert response.json()["error"]["code"] == code
    assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]
    assert "secret details" not in response.text


@pytest.mark.asyncio
@pytest.mark.parametrize("content", ["not json", "{}"])
async def test_invalid_model_output_returns_bad_gateway(content: str) -> None:
    app = create_app(extractor=BaggageExtractor(StubProvider(content=content)))

    async with api_client(app) as client:
        response = await client.post("/v1/extractions", json={"text": "合成政策"})

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "invalid_model_output"


@pytest.mark.asyncio
async def test_ready_reports_invalid_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api_app = importlib.import_module("baggage_extractor.api.app")
    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)  # pyright: ignore[reportCallIssue]

    def fail_settings() -> Settings:
        raise exc_info.value

    def unexpected_provider(*args: object, **kwargs: object) -> None:
        raise AssertionError("Invalid configuration must not create a real Provider.")

    monkeypatch.setattr(api_app, "get_settings", fail_settings)
    monkeypatch.setattr(api_app, "OpenAICompatibleProvider", unexpected_provider)
    app = create_app()

    async with api_client(app) as client:
        health = await client.get("/health")
        ready = await client.get("/ready")

    assert health.status_code == 200
    assert ready.status_code == 503
    assert ready.json()["error"]["code"] == "service_not_ready"


@pytest.mark.asyncio
async def test_concurrency_limit_rejects_waiting_request() -> None:
    provider = BlockingProvider()
    app = create_app(
        extractor=BaggageExtractor(provider),
        max_concurrent_requests=1,
        acquire_timeout_seconds=0.01,
    )

    async with api_client(app) as client:
        first_request = asyncio.create_task(
            client.post("/v1/extractions", json={"text": "第一条合成政策"})
        )
        await provider.started.wait()
        second_response = await client.post(
            "/v1/extractions",
            json={"text": "第二条合成政策"},
        )
        provider.release.set()
        first_response = await first_request

    assert first_response.status_code == 200
    assert second_response.status_code == 503
    assert second_response.json()["error"]["code"] == "capacity_exceeded"
    assert provider.calls == 1
