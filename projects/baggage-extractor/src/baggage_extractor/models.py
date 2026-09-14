from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

NonBlankText = Annotated[str, Field(min_length=1, pattern=r".*\S.*")]
NonNegativeInt = Annotated[int, Field(strict=True, ge=0)]
DOMAIN_SCHEMA_VERSION = "baggage-result-v1"


class SizeLimit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    length: NonNegativeInt | None
    width: NonNegativeInt | None
    height: NonNegativeInt | None
    note: str


class BaggageRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cabin_class: NonBlankText | None
    fare_codes: list[NonBlankText]
    checked_baggage: NonBlankText | None
    pieces: NonNegativeInt | None
    size_limit: SizeLimit
    special_notes: str


class FreeBaggageRule(BaggageRule):
    """A free checked-baggage allowance rule."""


class CarryOnBaggageRule(BaggageRule):
    """A carry-on baggage allowance rule."""


class ExtractionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    airline_code: NonBlankText | None
    airline_name: NonBlankText | None
    free_baggage_rules: list[FreeBaggageRule]
    baggage_rules: list[CarryOnBaggageRule]
