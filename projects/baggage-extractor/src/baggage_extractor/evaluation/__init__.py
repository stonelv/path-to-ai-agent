"""Deterministic evaluation for baggage extraction results."""

from baggage_extractor.evaluation.loader import (
    EvaluationDataError,
    load_cases,
    load_predictions,
)
from baggage_extractor.evaluation.models import (
    CaseScore,
    DatasetSplit,
    DatasetUsage,
    EvaluationCase,
    EvaluationReport,
    PredictionRecord,
    PredictionStatus,
)
from baggage_extractor.evaluation.scorer import (
    EvaluationScoringError,
    evaluate_predictions,
    score_case,
)

__all__ = [
    "CaseScore",
    "DatasetSplit",
    "DatasetUsage",
    "EvaluationCase",
    "EvaluationDataError",
    "EvaluationReport",
    "EvaluationScoringError",
    "PredictionRecord",
    "PredictionStatus",
    "evaluate_predictions",
    "load_cases",
    "load_predictions",
    "score_case",
]
