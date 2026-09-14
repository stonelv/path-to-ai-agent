from baggage_extractor.providers import ModelRequest, ModelResponse
from baggage_extractor.telemetry import generate_with_timing


class StubProvider:
    async def generate(self, request: ModelRequest) -> ModelResponse:
        return ModelResponse(content="result", model="stub-model")


async def test_generate_with_timing_records_call_metadata() -> None:
    result = await generate_with_timing(StubProvider(), ModelRequest(messages=()))

    assert result.response.content == "result"
    assert result.started_at <= result.finished_at
    assert result.latency_seconds >= 0
