from baggage_extractor.providers import (
    ChatMessage,
    ChatRole,
    ModelProvider,
    ModelRequest,
    ModelResponse,
    StructuredOutputSpec,
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


def test_model_request_keeps_structured_output_optional() -> None:
    request = ModelRequest(messages=(ChatMessage(role=ChatRole.USER, content="policy"),))

    assert request.structured_output is None


def test_structured_output_spec_is_provider_independent() -> None:
    schema = {
        "type": "object",
        "properties": {"airline_code": {"type": ["string", "null"]}},
        "required": ["airline_code"],
        "additionalProperties": False,
    }

    spec = StructuredOutputSpec(
        name="baggage_extraction",
        description="Structured airline baggage policy extraction.",
        json_schema=schema,
    )

    assert spec.name == "baggage_extraction"
    assert spec.description == "Structured airline baggage policy extraction."
    assert spec.json_schema == schema
    assert spec.strict is True
