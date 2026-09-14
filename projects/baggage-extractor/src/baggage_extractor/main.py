import asyncio

from baggage_extractor.config import get_settings
from baggage_extractor.experiments import EXPERIMENT_CASES, ExperimentCase
from baggage_extractor.providers import ModelProvider, OpenAICompatibleProvider
from baggage_extractor.telemetry import TimedModelResponse, generate_with_timing


async def run_model_experiment(
    provider: ModelProvider,
    case: ExperimentCase,
) -> TimedModelResponse:
    return await generate_with_timing(provider, case.to_model_request())


async def run_experiment_suite() -> list[tuple[ExperimentCase, TimedModelResponse]]:
    provider = OpenAICompatibleProvider(get_settings())
    results = []
    for case in EXPERIMENT_CASES:
        results.append((case, await run_model_experiment(provider, case)))
    return results


def main() -> None:
    for case, result in asyncio.run(run_experiment_suite()):
        print(f"=== {case.name} ===")
        print(f"Description: {case.description}")
        print(f"Temperature: {case.temperature}")
        print(f"Max output tokens: {case.max_output_tokens}")
        print(f"Started: {result.started_at.isoformat()}")
        print(f"Finished: {result.finished_at.isoformat()}")
        print(f"Latency: {result.latency_seconds:.3f} seconds")
        print(f"Model: {result.response.model}")
        print(f"Request ID: {result.response.request_id or 'not provided'}")
        print("Response:")
        print(result.response.content)
        print()


if __name__ == "__main__":
    main()
