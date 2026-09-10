import json

from pydantic import ValidationError

from baggage_extractor.errors import (
    InvalidExtractionInputError,
    StructuredOutputParseError,
    StructuredOutputValidationError,
)
from baggage_extractor.models import ExtractionResult
from baggage_extractor.prompts import PROMPT_VERSION, build_extraction_messages
from baggage_extractor.providers import ModelProvider, ModelRequest, StructuredOutputSpec

MAX_POLICY_TEXT_LENGTH = 20_000
STRUCTURED_OUTPUT_NAME = "baggage_extraction"
STRUCTURED_OUTPUT_DESCRIPTION = f"Airline baggage extraction using {PROMPT_VERSION}."


class BaggageExtractor:
    def __init__(self, provider: ModelProvider) -> None:
        self._provider = provider

    async def extract(self, policy_text: str) -> ExtractionResult:
        self._validate_input(policy_text)
        request = ModelRequest(
            messages=build_extraction_messages(policy_text),
            temperature=0,
            structured_output=StructuredOutputSpec(
                name=STRUCTURED_OUTPUT_NAME,
                description=STRUCTURED_OUTPUT_DESCRIPTION,
                json_schema=ExtractionResult.model_json_schema(),
            ),
        )
        response = await self._provider.generate(request)

        try:
            data = json.loads(response.content)
        except json.JSONDecodeError as error:
            raise StructuredOutputParseError(
                "Model structured output was not valid JSON."
            ) from error

        try:
            return ExtractionResult.model_validate(data)
        except ValidationError as error:
            raise StructuredOutputValidationError(
                "Model structured output did not match the baggage domain schema."
            ) from error

    @staticmethod
    def _validate_input(policy_text: str) -> None:
        if not policy_text.strip():
            raise InvalidExtractionInputError("Policy text must not be blank.")
        if len(policy_text) > MAX_POLICY_TEXT_LENGTH:
            raise InvalidExtractionInputError(
                f"Policy text exceeds the maximum length of {MAX_POLICY_TEXT_LENGTH} characters."
            )
