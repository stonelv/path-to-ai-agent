from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter

from baggage_extractor.providers import ModelProvider, ModelRequest, ModelResponse


@dataclass(frozen=True, slots=True)
class TimedModelResponse:
    response: ModelResponse
    started_at: datetime
    finished_at: datetime
    latency_seconds: float


async def generate_with_timing(
    provider: ModelProvider,
    request: ModelRequest,
) -> TimedModelResponse:
    started_at = datetime.now(UTC)
    started_counter = perf_counter()
    response = await provider.generate(request)
    latency_seconds = perf_counter() - started_counter
    finished_at = datetime.now(UTC)

    return TimedModelResponse(
        response=response,
        started_at=started_at,
        finished_at=finished_at,
        latency_seconds=latency_seconds,
    )
