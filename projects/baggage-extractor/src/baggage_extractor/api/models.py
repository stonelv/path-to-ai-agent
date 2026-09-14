from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from baggage_extractor.extractor import MAX_POLICY_TEXT_LENGTH
from baggage_extractor.models import ExtractionResult


class ExtractionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: Annotated[str, Field(min_length=1, max_length=MAX_POLICY_TEXT_LENGTH)]

    @field_validator("text")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Text must not be blank.")
        return value


class ExtractionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str
    result: ExtractionResult


class StatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok", "ready"]


class ErrorDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    request_id: str


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error: ErrorDetail
