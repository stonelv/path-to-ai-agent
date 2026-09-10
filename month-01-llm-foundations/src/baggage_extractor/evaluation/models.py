from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from baggage_extractor.models import BaggageRule, ExtractionResult

EVALUATION_SCHEMA_VERSION = "1.0"
NonBlankText = Annotated[str, Field(min_length=1, pattern=r".*\S.*")]
CaseId = Annotated[str, Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]
NonNegativeCount = Annotated[int, Field(ge=0)]
Rate = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
Latency = Annotated[float, Field(ge=0, allow_inf_nan=False)]


class DatasetSplit(StrEnum):
    DEV = "dev"
    HOLDOUT = "holdout"


class PredictionStatus(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"


class EvaluationSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["synthetic"]
    note: NonBlankText | None = None


def rule_identity(rule: BaggageRule) -> tuple[str | None, tuple[str, ...]]:
    return rule.cabin_class, tuple(sorted(rule.fare_codes))


class EvaluationCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = EVALUATION_SCHEMA_VERSION
    dataset_version: NonBlankText
    id: CaseId
    split: DatasetSplit
    policy_text: NonBlankText
    expected: ExtractionResult
    tags: Annotated[list[CaseId], Field(min_length=1)]
    source: EvaluationSource

    @model_validator(mode="after")
    def validate_case(self) -> "EvaluationCase":
        if len(self.tags) != len(set(self.tags)):
            raise ValueError("Evaluation case tags must be unique.")
        for field_name in ("free_baggage_rules", "baggage_rules"):
            rules = getattr(self.expected, field_name)
            if any(len(rule.fare_codes) != len(set(rule.fare_codes)) for rule in rules):
                raise ValueError(f"Expected {field_name} contains duplicate fare codes.")
            identities = [rule_identity(rule) for rule in rules]
            if len(identities) != len(set(identities)):
                raise ValueError(f"Expected {field_name} contains ambiguous rule identities.")
        return self


class PredictionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = EVALUATION_SCHEMA_VERSION
    case_id: CaseId
    status: PredictionStatus
    actual: ExtractionResult | None = None
    error_type: NonBlankText | None = None
    error_message: NonBlankText | None = None
    latency_seconds: Latency | None = None

    @model_validator(mode="after")
    def validate_outcome(self) -> "PredictionRecord":
        if self.status is PredictionStatus.SUCCESS:
            if self.actual is None:
                raise ValueError("Successful prediction must include actual output.")
            if self.error_type is not None or self.error_message is not None:
                raise ValueError("Successful prediction must not include an error.")
        else:
            if self.actual is not None:
                raise ValueError("Failed prediction must not include actual output.")
            if self.error_type is None:
                raise ValueError("Failed prediction must include error_type.")
        return self


class FieldIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: NonBlankText
    kind: Literal["wrong_value", "missing_rule", "unsupported_rule"]
    expected: object | None = None
    actual: object | None = None


class FieldMetric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    correct: NonNegativeCount
    total: NonNegativeCount
    accuracy: Rate


class CaseScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: CaseId
    prediction_status: PredictionStatus
    exact_match: bool
    field_correct: NonNegativeCount
    field_total: NonNegativeCount
    expected_rules: NonNegativeCount
    matched_rules: NonNegativeCount
    missing_rules: NonNegativeCount
    unsupported_rules: NonNegativeCount
    unsupported_values: NonNegativeCount
    error_type: NonBlankText | None = None
    latency_seconds: Latency | None = None
    field_metrics: dict[str, FieldMetric]
    issues: list[FieldIssue]


class EvaluationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = EVALUATION_SCHEMA_VERSION
    dataset_version: NonBlankText
    split: DatasetSplit
    generated_at: datetime
    model: NonBlankText | None = None
    prompt_version: NonBlankText | None = None
    domain_schema_version: NonBlankText | None = None
    package_version: NonBlankText | None = None
    model_max_retries: NonNegativeCount | None = None
    case_count: NonNegativeCount
    successful_predictions: NonNegativeCount
    failed_predictions: NonNegativeCount
    prediction_success_rate: Rate
    exact_matches: NonNegativeCount
    exact_match_rate: Rate
    field_correct: NonNegativeCount
    field_total: NonNegativeCount
    field_accuracy: Rate
    expected_rules: NonNegativeCount
    matched_rules: NonNegativeCount
    missing_rules: NonNegativeCount
    unsupported_rules: NonNegativeCount
    unsupported_values: NonNegativeCount
    rule_recall: Rate | None
    latency_sample_count: NonNegativeCount
    average_latency_seconds: Latency | None
    field_metrics: dict[str, FieldMetric]
    cases: list[CaseScore]
