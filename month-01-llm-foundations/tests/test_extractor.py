import json
from copy import deepcopy

import pytest

from baggage_extractor.errors import (
    InvalidExtractionInputError,
    StructuredOutputParseError,
    StructuredOutputValidationError,
)
from baggage_extractor.extractor import MAX_POLICY_TEXT_LENGTH, BaggageExtractor
from baggage_extractor.models import CarryOnBaggageRule, ExtractionResult, FreeBaggageRule
from baggage_extractor.prompts import PROMPT_VERSION, STRUCTURED_EXTRACTION_SYSTEM_PROMPT
from baggage_extractor.providers import (
    ModelProviderError,
    ModelRequest,
    ModelResponse,
    ProviderTimeoutError,
    RateLimitError,
)


def valid_result_data() -> dict[str, object]:
    return {
        "airline_code": "CA",
        "airline_name": "中国国际航空",
        "free_baggage_rules": [
            {
                "cabin_class": "经济舱",
                "fare_codes": ["Y"],
                "checked_baggage": "23kg",
                "pieces": 1,
                "size_limit": {
                    "length": None,
                    "width": None,
                    "height": None,
                    "note": "三边之和不超过158cm",
                },
                "special_notes": "",
            }
        ],
        "baggage_rules": [
            {
                "cabin_class": "经济舱",
                "fare_codes": ["Y"],
                "checked_baggage": "5kg",
                "pieces": 1,
                "size_limit": {
                    "length": 55,
                    "width": 40,
                    "height": 20,
                    "note": "",
                },
                "special_notes": "",
            }
        ],
    }


class StubProvider:
    def __init__(
        self,
        response_data: object | None = None,
        *,
        content: str | None = None,
        error: ModelProviderError | None = None,
    ) -> None:
        self.response_data = valid_result_data() if response_data is None else response_data
        self.content = content
        self.error = error
        self.requests: list[ModelRequest] = []

    async def generate(self, request: ModelRequest) -> ModelResponse:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        content = self.content
        if content is None:
            content = json.dumps(self.response_data, ensure_ascii=False)
        return ModelResponse(content=content, model="stub-model", request_id="stub-request")


async def test_extract_returns_validated_domain_result() -> None:
    provider = StubProvider()

    result = await BaggageExtractor(provider).extract("经济舱可托运1件23kg行李。")

    assert isinstance(result, ExtractionResult)
    assert isinstance(result.free_baggage_rules[0], FreeBaggageRule)
    assert isinstance(result.baggage_rules[0], CarryOnBaggageRule)
    assert result.free_baggage_rules[0].checked_baggage == "23kg"
    assert result.baggage_rules[0].checked_baggage == "5kg"


async def test_extract_requests_versioned_strict_schema() -> None:
    provider = StubProvider()
    policy_text = "经济舱可托运1件23kg行李。"

    await BaggageExtractor(provider).extract(policy_text)

    request = provider.requests[0]
    assert request.messages[0].content == STRUCTURED_EXTRACTION_SYSTEM_PROMPT
    assert request.messages[1].content.endswith(policy_text)
    assert request.temperature == 0
    assert request.structured_output is not None
    assert PROMPT_VERSION in request.structured_output.description
    assert request.structured_output.strict is True
    assert request.structured_output.json_schema == ExtractionResult.model_json_schema()


@pytest.mark.parametrize("text", ["", " ", "\n\t"])
async def test_extract_rejects_blank_input_without_calling_provider(text: str) -> None:
    provider = StubProvider()

    with pytest.raises(InvalidExtractionInputError, match="must not be blank"):
        await BaggageExtractor(provider).extract(text)

    assert provider.requests == []


async def test_extract_rejects_oversized_input_without_calling_provider() -> None:
    provider = StubProvider()

    with pytest.raises(InvalidExtractionInputError, match="maximum length"):
        await BaggageExtractor(provider).extract("x" * (MAX_POLICY_TEXT_LENGTH + 1))

    assert provider.requests == []


async def test_extract_preserves_nulls_and_empty_rule_lists() -> None:
    provider = StubProvider(
        {
            "airline_code": None,
            "airline_name": None,
            "free_baggage_rules": [],
            "baggage_rules": [],
        }
    )

    result = await BaggageExtractor(provider).extract("这是一段与行李无关的文本。")

    assert result.airline_code is None
    assert result.airline_name is None
    assert result.free_baggage_rules == []
    assert result.baggage_rules == []


async def test_extract_preserves_empty_fare_codes() -> None:
    response_data = valid_result_data()
    free_rule = response_data["free_baggage_rules"][0]
    free_rule["fare_codes"] = []
    provider = StubProvider(response_data)

    result = await BaggageExtractor(provider).extract("经济舱可托运1件23kg行李。")

    assert result.free_baggage_rules[0].fare_codes == []


async def test_extract_rejects_invalid_json() -> None:
    provider = StubProvider(content="```json\n{}\n```")

    with pytest.raises(StructuredOutputParseError, match="valid JSON"):
        await BaggageExtractor(provider).extract("policy")


@pytest.mark.parametrize(
    "content",
    [
        '{"airline_code": "CA", "airline_code": null, "airline_name": null,'
        '"free_baggage_rules": [], "baggage_rules": []}',
        '{"airline_code": NaN, "airline_name": null,'
        '"free_baggage_rules": [], "baggage_rules": []}',
        '{"airline_code": Infinity, "airline_name": null,'
        '"free_baggage_rules": [], "baggage_rules": []}',
        '{"airline_code": -Infinity, "airline_name": null,'
        '"free_baggage_rules": [], "baggage_rules": []}',
        '{"airline_code": null, "airline_name": null, "baggage_rules": [],'
        '"free_baggage_rules": [{"cabin_class": null, "fare_codes": [],'
        '"checked_baggage": null, "pieces": 1, "pieces": 2, "special_notes": "",'
        '"size_limit": {"length": null, "width": null, "height": null, "note": ""}}]}',
    ],
)
async def test_extract_rejects_ambiguous_or_nonstandard_json(content: str) -> None:
    provider = StubProvider(content=content)

    with pytest.raises(StructuredOutputParseError, match="valid JSON"):
        await BaggageExtractor(provider).extract("policy")

    assert len(provider.requests) == 1


@pytest.mark.parametrize(
    "invalid_data",
    [
        {
            "airline_code": "CA",
            "airline_name": "中国国际航空",
            "free_baggage_rules": [],
        },
        {
            "airline_code": " ",
            "airline_name": "中国国际航空",
            "free_baggage_rules": [],
            "baggage_rules": [],
        },
    ],
)
async def test_extract_rejects_json_that_violates_domain_schema(
    invalid_data: dict[str, object],
) -> None:
    provider = StubProvider(deepcopy(invalid_data))

    with pytest.raises(StructuredOutputValidationError, match="domain schema"):
        await BaggageExtractor(provider).extract("policy")


@pytest.mark.parametrize(
    "provider_error",
    [
        RateLimitError("rate limited", retryable=True),
        ProviderTimeoutError("timed out", retryable=True),
    ],
)
async def test_extract_preserves_provider_errors(provider_error: ModelProviderError) -> None:
    provider = StubProvider(error=provider_error)

    with pytest.raises(type(provider_error), match=str(provider_error)):
        await BaggageExtractor(provider).extract("policy")
