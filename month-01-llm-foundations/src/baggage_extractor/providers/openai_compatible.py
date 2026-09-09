import httpx
from pydantic import BaseModel

from baggage_extractor.config import Settings
from baggage_extractor.providers.base import ModelRequest, ModelResponse


class _ResponseMessage(BaseModel):
    content: str


class _ResponseChoice(BaseModel):
    message: _ResponseMessage


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

        if self._client is not None:
            response = await self._post(self._client, payload)
        else:
            async with httpx.AsyncClient(timeout=self._settings.model_timeout_seconds) as client:
                response = await self._post(client, payload)

        response.raise_for_status()
        completion = _ChatCompletionResponse.model_validate(response.json())
        if not completion.choices:
            raise ValueError("Model response did not contain any choices.")

        return ModelResponse(
            content=completion.choices[0].message.content,
            model=completion.model,
            request_id=response.headers.get("x-request-id"),
        )

    async def _post(
        self,
        client: httpx.AsyncClient,
        payload: dict[str, object],
    ) -> httpx.Response:
        return await client.post(
            f"{self._settings.model_base_url}/chat/completions",
            headers={
                "Authorization": (
                    f"Bearer {self._settings.model_api_key.get_secret_value()}"
                ),
                "Content-Type": "application/json",
            },
            json=payload,
        )
