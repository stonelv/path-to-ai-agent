from baggage_extractor.providers import (
    ChatMessage,
    ChatRole,
    ModelProvider,
    ModelRequest,
    ModelResponse,
)


class StubProvider:
    async def generate(self, request: ModelRequest) -> ModelResponse:
        return ModelResponse(
            content=request.messages[-1].content,
            model="stub-model",
            request_id="stub-request-id",
        )


async def invoke_provider(provider: ModelProvider, request: ModelRequest) -> ModelResponse:
    return await provider.generate(request)


async def test_provider_protocol_accepts_structural_implementation() -> None:
    request = ModelRequest(
        messages=(
            ChatMessage(
                role=ChatRole.USER,
                content="北京至东京经济舱可免费托运一件23公斤行李。",
            ),
        ),
        temperature=0.0,
        max_output_tokens=200,
    )

    response = await invoke_provider(StubProvider(), request)

    assert response.content == request.messages[0].content
    assert response.model == "stub-model"
    assert response.request_id == "stub-request-id"
