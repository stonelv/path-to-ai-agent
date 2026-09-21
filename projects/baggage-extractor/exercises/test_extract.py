import pytest

from baggage_extractor.errors import (
    InvalidExtractionInputError,
    StructuredOutputParseError,
    StructuredOutputValidationError,
)
from baggage_extractor.extractor import (
    MAX_POLICY_TEXT_LENGTH,
    STRUCTURED_OUTPUT_DESCRIPTION,
    STRUCTURED_OUTPUT_NAME,
)
from baggage_extractor.models import ExtractionResult, FreeBaggageRule, SizeLimit
from baggage_extractor.prompts import build_extraction_messages
from baggage_extractor.providers import ModelRequest, ModelResponse, ProviderTimeoutError
from exercises.conftest import ExtractionTask


class RecordingProvider:
    def __init__(self, content: str, error: ProviderTimeoutError | None = None) -> None:
        self.content = content
        self.error = error
        self.requests: list[ModelRequest] = []

    async def generate(self, request: ModelRequest) -> ModelResponse:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return ModelResponse(content=self.content, model="scripted")


@pytest.fixture
def expected() -> ExtractionResult:
    return ExtractionResult(
        airline_code=None,
        airline_name=None,
        free_baggage_rules=[
            FreeBaggageRule(
                cabin_class="Economy",
                fare_codes=[],
                checked_baggage="23kg",
                pieces=1,
                size_limit=SizeLimit(length=None, width=None, height=None, note=""),
                special_notes="",
            )
        ],
        baggage_rules=[],
    )


async def test_result_and_request_contract(
    extraction_task: ExtractionTask, expected: ExtractionResult
) -> None:
    provider = RecordingProvider(expected.model_dump_json())
    text = "Economy allows one checked bag of 23kg."

    result = await extraction_task(text, provider)

    assert result == expected
    assert len(provider.requests) == 1
    request = provider.requests[0]
    assert request.messages == build_extraction_messages(text)
    assert request.temperature == 0
    assert request.structured_output is not None
    assert request.structured_output.name == STRUCTURED_OUTPUT_NAME
    assert request.structured_output.description == STRUCTURED_OUTPUT_DESCRIPTION
    assert request.structured_output.strict is True
    assert request.structured_output.json_schema == ExtractionResult.model_json_schema()


@pytest.mark.parametrize(
    "text",
    ["", " \n", "x" * (MAX_POLICY_TEXT_LENGTH + 1)],
    ids=["empty", "whitespace", "over-limit"],
)
async def test_invalid_input_never_calls_provider(
    extraction_task: ExtractionTask, expected: ExtractionResult, text: str
) -> None:
    provider = RecordingProvider(expected.model_dump_json())

    with pytest.raises(InvalidExtractionInputError):
        await extraction_task(text, provider)

    assert provider.requests == []


async def test_exact_input_limit_is_allowed(
    extraction_task: ExtractionTask, expected: ExtractionResult
) -> None:
    provider = RecordingProvider(expected.model_dump_json())

    assert await extraction_task("x" * MAX_POLICY_TEXT_LENGTH, provider) == expected
    assert len(provider.requests) == 1


@pytest.mark.parametrize("content", ["```json\n{}\n```", '{"x": 1, "x": 2}', '{"x": NaN}'])
async def test_invalid_json_is_not_repaired_or_retried(
    extraction_task: ExtractionTask, content: str
) -> None:
    provider = RecordingProvider(content)

    with pytest.raises(StructuredOutputParseError):
        await extraction_task("policy", provider)

    assert len(provider.requests) == 1


async def test_missing_fields_are_not_success(extraction_task: ExtractionTask) -> None:
    provider = RecordingProvider('{"airline_code": null}')

    with pytest.raises(StructuredOutputValidationError):
        await extraction_task("policy", provider)

    assert len(provider.requests) == 1


async def test_provider_error_is_preserved(
    extraction_task: ExtractionTask, expected: ExtractionResult
) -> None:
    failure = ProviderTimeoutError("Simulated timeout.", retryable=True)
    provider = RecordingProvider(expected.model_dump_json(), error=failure)

    with pytest.raises(ProviderTimeoutError) as caught:
        await extraction_task("policy", provider)

    assert caught.value is failure
    assert len(provider.requests) == 1
