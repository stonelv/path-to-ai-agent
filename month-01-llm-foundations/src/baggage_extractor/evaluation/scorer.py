from collections.abc import Sequence
from datetime import UTC, datetime

from baggage_extractor.evaluation.models import (
    CaseScore,
    EvaluationCase,
    EvaluationReport,
    FieldIssue,
    FieldMetric,
    PredictionRecord,
    PredictionStatus,
    rule_identity,
)
from baggage_extractor.models import BaggageRule, ExtractionResult

RULE_FIELDS = (
    "cabin_class",
    "fare_codes",
    "checked_baggage",
    "pieces",
    "size_limit.length",
    "size_limit.width",
    "size_limit.height",
    "size_limit.note",
    "special_notes",
)


class EvaluationScoringError(ValueError):
    """Raised when cases and predictions cannot be scored as one evaluation."""


def _field_value(rule: BaggageRule, field: str) -> object:
    if field == "fare_codes":
        return sorted(rule.fare_codes)
    if field.startswith("size_limit."):
        return getattr(rule.size_limit, field.removeprefix("size_limit."))
    return getattr(rule, field)


def _is_supported_value(value: object) -> bool:
    return value is not None and value != "" and value != []


def _count_populated_rule_values(rule: BaggageRule) -> int:
    return sum(_is_supported_value(_field_value(rule, field)) for field in RULE_FIELDS)


def _score_rule(
    expected: BaggageRule,
    actual: BaggageRule,
    *,
    path: str,
    field_counts: dict[str, list[int]],
) -> tuple[int, int, list[FieldIssue]]:
    correct = 0
    unsupported = 0
    issues: list[FieldIssue] = []
    for field in RULE_FIELDS:
        expected_value = _field_value(expected, field)
        actual_value = _field_value(actual, field)
        if expected_value == actual_value:
            correct += 1
            field_counts[f"{path.rsplit('[', 1)[0]}.{field}"][0] += 1
            continue
        if not _is_supported_value(expected_value) and _is_supported_value(actual_value):
            unsupported += 1
        issues.append(
            FieldIssue(
                path=f"{path}.{field}",
                kind="wrong_value",
                expected=expected_value,
                actual=actual_value,
            )
        )
    return correct, unsupported, issues


def _candidate_match_score(expected: BaggageRule, actual: BaggageRule) -> int:
    return sum(
        _field_value(expected, field) == _field_value(actual, field) for field in RULE_FIELDS
    )


def _score_rule_collection(
    expected_rules: Sequence[BaggageRule],
    actual_rules: Sequence[BaggageRule],
    *,
    path: str,
    field_counts: dict[str, list[int]],
) -> tuple[int, int, int, int, int, list[FieldIssue]]:
    remaining = list(enumerate(actual_rules))
    correct = 0
    matched = 0
    unsupported_values = 0
    issues: list[FieldIssue] = []

    for expected_index, expected_rule in enumerate(expected_rules):
        identity = rule_identity(expected_rule)
        candidates = [
            (position, actual_index, actual_rule)
            for position, (actual_index, actual_rule) in enumerate(remaining)
            if rule_identity(actual_rule) == identity
        ]
        if not candidates:
            issues.append(
                FieldIssue(
                    path=f"{path}[{expected_index}]",
                    kind="missing_rule",
                    expected=expected_rule.model_dump(mode="json"),
                )
            )
            continue

        position, actual_index, actual_rule = max(
            candidates,
            key=lambda candidate: (
                _candidate_match_score(expected_rule, candidate[2]),
                -candidate[1],
            ),
        )
        remaining.pop(position)
        matched += 1
        rule_correct, rule_unsupported, rule_issues = _score_rule(
            expected_rule,
            actual_rule,
            path=f"{path}[{expected_index}]",
            field_counts=field_counts,
        )
        correct += rule_correct
        unsupported_values += rule_unsupported
        issues.extend(rule_issues)

    for actual_index, actual_rule in remaining:
        unsupported_values += _count_populated_rule_values(actual_rule)
        issues.append(
            FieldIssue(
                path=f"{path}[actual:{actual_index}]",
                kind="unsupported_rule",
                actual=actual_rule.model_dump(mode="json"),
            )
        )

    return (
        correct,
        matched,
        len(expected_rules) - matched,
        len(remaining),
        unsupported_values,
        issues,
    )


def _expected_field_total(expected: ExtractionResult) -> int:
    rule_count = len(expected.free_baggage_rules) + len(expected.baggage_rules)
    return 2 + len(RULE_FIELDS) * rule_count


def _field_counts(expected: ExtractionResult) -> dict[str, list[int]]:
    counts = {"airline_code": [0, 1], "airline_name": [0, 1]}
    for collection in ("free_baggage_rules", "baggage_rules"):
        rule_count = len(getattr(expected, collection))
        for field in RULE_FIELDS:
            counts[f"{collection}.{field}"] = [0, rule_count]
    return counts


def _build_field_metrics(counts: dict[str, list[int]]) -> dict[str, FieldMetric]:
    return {
        path: FieldMetric(
            correct=correct,
            total=total,
            accuracy=correct / total if total else 0,
        )
        for path, (correct, total) in counts.items()
        if total
    }


def score_case(case: EvaluationCase, prediction: PredictionRecord) -> CaseScore:
    if prediction.case_id != case.id:
        raise EvaluationScoringError(
            f"Prediction '{prediction.case_id}' does not belong to case '{case.id}'."
        )
    expected = case.expected
    expected_rules = len(expected.free_baggage_rules) + len(expected.baggage_rules)
    field_total = _expected_field_total(expected)
    field_counts = _field_counts(expected)
    if prediction.status is PredictionStatus.FAILURE:
        return CaseScore(
            case_id=case.id,
            prediction_status=prediction.status,
            exact_match=False,
            field_correct=0,
            field_total=field_total,
            expected_rules=expected_rules,
            matched_rules=0,
            missing_rules=expected_rules,
            unsupported_rules=0,
            unsupported_values=0,
            error_type=prediction.error_type,
            latency_seconds=prediction.latency_seconds,
            field_metrics=_build_field_metrics(field_counts),
            issues=[],
        )

    if prediction.actual is None:
        raise EvaluationScoringError("Successful prediction is missing actual output.")
    actual = prediction.actual
    field_correct = 0
    unsupported_values = 0
    issues: list[FieldIssue] = []
    for field in ("airline_code", "airline_name"):
        expected_value = getattr(expected, field)
        actual_value = getattr(actual, field)
        if expected_value == actual_value:
            field_correct += 1
            field_counts[field][0] += 1
        else:
            if not _is_supported_value(expected_value) and _is_supported_value(actual_value):
                unsupported_values += 1
            issues.append(
                FieldIssue(
                    path=field,
                    kind="wrong_value",
                    expected=expected_value,
                    actual=actual_value,
                )
            )

    matched_rules = 0
    missing_rules = 0
    unsupported_rules = 0
    for field in ("free_baggage_rules", "baggage_rules"):
        (
            collection_correct,
            collection_matched,
            collection_missing,
            collection_unsupported,
            collection_unsupported_values,
            collection_issues,
        ) = _score_rule_collection(
            getattr(expected, field),
            getattr(actual, field),
            path=field,
            field_counts=field_counts,
        )
        field_correct += collection_correct
        matched_rules += collection_matched
        missing_rules += collection_missing
        unsupported_rules += collection_unsupported
        unsupported_values += collection_unsupported_values
        issues.extend(collection_issues)

    return CaseScore(
        case_id=case.id,
        prediction_status=prediction.status,
        exact_match=not issues,
        field_correct=field_correct,
        field_total=field_total,
        expected_rules=expected_rules,
        matched_rules=matched_rules,
        missing_rules=missing_rules,
        unsupported_rules=unsupported_rules,
        unsupported_values=unsupported_values,
        latency_seconds=prediction.latency_seconds,
        field_metrics=_build_field_metrics(field_counts),
        issues=issues,
    )


def evaluate_predictions(
    cases: Sequence[EvaluationCase],
    predictions: Sequence[PredictionRecord],
    *,
    model: str | None = None,
    prompt_version: str | None = None,
    domain_schema_version: str | None = None,
    package_version: str | None = None,
    model_max_retries: int | None = None,
    generated_at: datetime | None = None,
) -> EvaluationReport:
    if not cases:
        raise EvaluationScoringError("Evaluation requires at least one case.")
    case_ids = [case.id for case in cases]
    if len(set(case_ids)) != len(case_ids):
        raise EvaluationScoringError("Evaluation cases contain duplicate IDs.")
    prediction_by_id = {prediction.case_id: prediction for prediction in predictions}
    if len(prediction_by_id) != len(predictions):
        raise EvaluationScoringError("Predictions contain duplicate case IDs.")
    expected_case_ids = set(case_ids)
    extra_ids = sorted(prediction_by_id.keys() - expected_case_ids)
    if extra_ids:
        raise EvaluationScoringError(
            f"Predictions contain unknown case IDs: {', '.join(extra_ids)}"
        )

    scores: list[CaseScore] = []
    for case in cases:
        prediction = prediction_by_id.get(case.id)
        if prediction is None:
            prediction = PredictionRecord(
                case_id=case.id,
                status=PredictionStatus.FAILURE,
                error_type="MissingPrediction",
                error_message="No prediction was provided for this case.",
            )
        scores.append(score_case(case, prediction))

    dataset_versions = {case.dataset_version for case in cases}
    splits = {case.split for case in cases}
    if len(dataset_versions) != 1 or len(splits) != 1:
        raise EvaluationScoringError(
            "Evaluation cases must share one dataset version and split."
        )

    field_correct = sum(score.field_correct for score in scores)
    field_total = sum(score.field_total for score in scores)
    exact_matches = sum(score.exact_match for score in scores)
    successful_predictions = sum(
        score.prediction_status is PredictionStatus.SUCCESS for score in scores
    )
    latencies = [
        score.latency_seconds for score in scores if score.latency_seconds is not None
    ]
    aggregate_field_counts: dict[str, list[int]] = {}
    for score in scores:
        for path, metric in score.field_metrics.items():
            counts = aggregate_field_counts.setdefault(path, [0, 0])
            counts[0] += metric.correct
            counts[1] += metric.total
    expected_rules = sum(score.expected_rules for score in scores)
    matched_rules = sum(score.matched_rules for score in scores)
    return EvaluationReport(
        dataset_version=next(iter(dataset_versions)),
        split=next(iter(splits)),
        generated_at=generated_at or datetime.now(UTC),
        model=model,
        prompt_version=prompt_version,
        domain_schema_version=domain_schema_version,
        package_version=package_version,
        model_max_retries=model_max_retries,
        case_count=len(scores),
        successful_predictions=successful_predictions,
        failed_predictions=len(scores) - successful_predictions,
        prediction_success_rate=successful_predictions / len(scores),
        exact_matches=exact_matches,
        exact_match_rate=exact_matches / len(scores),
        field_correct=field_correct,
        field_total=field_total,
        field_accuracy=field_correct / field_total,
        expected_rules=expected_rules,
        matched_rules=matched_rules,
        missing_rules=sum(score.missing_rules for score in scores),
        unsupported_rules=sum(score.unsupported_rules for score in scores),
        unsupported_values=sum(score.unsupported_values for score in scores),
        rule_recall=matched_rules / expected_rules if expected_rules else None,
        latency_sample_count=len(latencies),
        average_latency_seconds=sum(latencies) / len(latencies) if latencies else None,
        field_metrics=_build_field_metrics(aggregate_field_counts),
        cases=scores,
    )
