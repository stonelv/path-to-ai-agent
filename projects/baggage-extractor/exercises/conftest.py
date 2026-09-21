from collections.abc import Awaitable, Callable

import pytest

from baggage_extractor.extractor import BaggageExtractor
from baggage_extractor.models import ExtractionResult
from baggage_extractor.providers import ModelProvider
from exercises.extract import extract

ExtractionTask = Callable[[str, ModelProvider], Awaitable[ExtractionResult]]


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--reference",
        action="store_true",
        help="Check exercise requirements against the production reference implementation.",
    )


@pytest.fixture
def extraction_task(request: pytest.FixtureRequest) -> ExtractionTask:
    if request.config.getoption("--reference"):
        async def reference(policy_text: str, provider: ModelProvider) -> ExtractionResult:
            return await BaggageExtractor(provider).extract(policy_text)

        return reference
    return extract
