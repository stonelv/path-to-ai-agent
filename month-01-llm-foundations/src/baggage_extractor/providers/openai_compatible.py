import asyncio

import httpx
from pydantic import BaseModel

from baggage_extractor.config import Settings
from baggage_extractor.providers.base import ModelRequest, ModelResponse
from baggage_extractor.providers.errors import (
    AuthenticationError,
    InvalidRequestError,
    InvalidResponseError,
    ModelProviderError,
    ProviderConnectionError,
    ProviderTimeoutError,
    RateLimitError,
    ServerError,
)


class _ResponseMessage(BaseModel):
    content: str
    refusal: str | None = None


class _ResponseChoice(BaseModel):
    message: _ResponseMessage
    finish_reason: str | None = None


class _ChatCompletionResponse(BaseModel):
    model: str
    choices: list[_ResponseChoice]


class OpenAICompatibleProvider:
    def __init__(
        self,
        settings: Settings,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = settings
        self._client = client

    async def generate(self, request: ModelRequest) -> ModelResponse:
        payload: dict[str, object] = {
            "model": self._settings.model_name,
            "messages": [
                {"role": message.role.value, "content": message.content}
                for message in request.messages
            ],
            "temperature": request.temperature,
        }
        if request.max_output_tokens is not None:
            payload["max_tokens"] = request.max_output_tokens
        if request.structured_output is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": request.structured_output.name,
                    "description": request.structured_output.description,
                    "schema": dict(request.structured_output.json_schema),
                    "strict": request.structured_output.strict,
                },
            }

        if self._client is not None:
            return await self._generate_with_client(self._client, payload)

        timeout = httpx.Timeout(
            connect=self._settings.model_connect_timeout_seconds,
            read=self._settings.model_read_timeout_seconds,
            write=self._settings.model_read_timeout_seconds,
            pool=self._settings.model_connect_timeout_seconds,
        )
        async with httpx.AsyncClient(timeout=timeout) as client:
            return await self._generate_with_client(client, payload)

    async def _generate_with_client(
        self,
        client: httpx.AsyncClient,
        payload: dict[str, object],
    ) -> ModelResponse:
        for attempt in range(self._settings.model_max_retries + 1):
            try:
                response = await self._post(client, payload)
                return self._parse_response(response)
            except ModelProviderError as error:
                if not error.retryable or attempt >= self._settings.model_max_retries:
                    raise
                delay = self._settings.model_retry_backoff_seconds * (2**attempt)
                if delay:
                    await asyncio.sleep(delay)

        raise RuntimeError("Model request retry loop exited unexpectedly.")

    def _parse_response(self, response: httpx.Response) -> ModelResponse:
        status_code = response.status_code
        if status_code in (401, 403):
            raise AuthenticationError(f"Model authentication failed (HTTP {status_code}).")
        if status_code == 429:
            raise RateLimitError("Model provider rate limit exceeded.", retryable=True)
        if status_code >= 500:
            raise ServerError(f"Model provider server error (HTTP {status_code}).", retryable=True)
        if status_code >= 400:
            raise InvalidRequestError(f"Model request was rejected (HTTP {status_code}).")
        if not 200 <= status_code < 300:
            raise InvalidResponseError(f"Unexpected model response status (HTTP {status_code}).")

        try:
            completion = _ChatCompletionResponse.model_validate(response.json())
        except ValueError as error:
            raise InvalidResponseError("Model response had an invalid format.") from error
        if not completion.choices:
            raise InvalidResponseError("Model response did not contain any choices.")
        choice = completion.choices[0]
        if choice.message.refusal:
            raise InvalidResponseError("Model refused the request.")
        if choice.finish_reason not in (None, "stop"):
            raise InvalidResponseError("Model response did not finish normally.")
        content = choice.message.content
        if not content.strip():
            raise InvalidResponseError("Model response contained empty content.")

        return ModelResponse(
            content=content,
            model=completion.model,
            request_id=response.headers.get("x-request-id"),
        )

    async def _post(
        self,
        client: httpx.AsyncClient,
        payload: dict[str, object],
    ) -> httpx.Response:
        try:
            return await client.post(
                f"{self._settings.model_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._settings.model_api_key.get_secret_value()}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        except httpx.TimeoutException as error:
            raise ProviderTimeoutError("Model request timed out.", retryable=True) from error
        except (httpx.NetworkError, httpx.RemoteProtocolError) as error:
            raise ProviderConnectionError(
                "Model provider connection failed.", retryable=True
            ) from error
