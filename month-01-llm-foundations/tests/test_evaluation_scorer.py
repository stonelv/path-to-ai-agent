from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import pytest
from test_evaluation_models import case_data

from baggage_extractor.evaluation.loader import load_cases
from baggage_extractor.evaluation.models import (
    EvaluationCase,
    PredictionRecord,
    PredictionStatus,
)
from baggage_extractor.evaluation.scorer import (
    EvaluationScoringError,
    evaluate_predictions,
    score_case,
)
from baggage_extractor.models import ExtractionResult

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def make_case(**overrides: object) -> EvaluationCase:
    data = case_data()
    data.update(overrides)
    return EvaluationCase.model_validate(data)


def successful_prediction(case: EvaluationCase) -> PredictionRecord:
    return PredictionRecord(
        case_id=case.id,
        status=PredictionStatus.SUCCESS,
        actual=case.expected,
        latency_seconds=0.25,
    )


def test_score_case_accepts_rule_and_fare_code_reordering() -> None:
    data = case_data()
    first_rule = data["expected"]["free_baggage_rules"][0]
    first_rule["fare_codes"] = ["Y", "B", "M"]
    second_rule = deepcopy(first_rule)
    second_rule["cabin_class"] = "公务舱"
    second_rule["fare_codes"] = ["C", "D"]
    second_rule["checked_baggage"] = "每件不超过32kg"
    data["expected"]["free_baggage_rules"].append(second_rule)
    case = EvaluationCase.model_validate(data)
    actual = case.expected.model_copy(deep=True)
    actual.free_baggage_rules.reverse()
    actual.free_baggage_rules[1].fare_codes.reverse()

    score = score_case(
        case,
        PredictionRecord(case_id=case.id, status="success", actual=actual),
    )

    assert score.exact_match is True
    assert score.field_correct == score.field_total
    assert score.matched_rules == 2
    assert score.field_metrics["free_baggage_rules.pieces"].accuracy == 1


def test_score_case_reports_missing_unsupported_and_hallucinated_values() -> None:
    case = make_case()
    actual_data = case.expected.model_dump(mode="json")
    actual_data["airline_code"] = "EX"
    actual_data["free_baggage_rules"] = []
    actual_data["baggage_rules"] = [
        {
            "cabin_class": "经济舱",
            "fare_codes": [],
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
    ]

    score = score_case(
        case,
        PredictionRecord(
            case_id=case.id,
            status="success",
            actual=ExtractionResult.model_validate(actual_data),
        ),
    )

    assert score.exact_match is False
    assert score.missing_rules == 1
    assert score.unsupported_rules == 1
    assert score.unsupported_values == 7
    assert {issue.kind for issue in score.issues} == {
        "wrong_value",
        "missing_rule",
        "unsupported_rule",
    }


def test_score_case_counts_failed_prediction_in_denominators() -> None:
    case = make_case()
    prediction = PredictionRecord(
        case_id=case.id,
        status="failure",
        error_type="ProviderTimeoutError",
    )

    score = score_case(case, prediction)

    assert score.field_correct == 0
    assert score.field_total == 11
    assert score.missing_rules == 1
    assert score.error_type == "ProviderTimeoutError"


def test_score_case_counts_value_added_where_expected_is_unknown() -> None:
    case = make_case()
    actual = case.expected.model_copy(deep=True)
    actual.free_baggage_rules[0].size_limit.length = 55

    score = score_case(
        case,
        PredictionRecord(case_id=case.id, status="success", actual=actual),
    )

    assert score.unsupported_values == 1
    assert score.field_metrics["free_baggage_rules.size_limit.length"].accuracy == 0
    assert score.issues[0].path == "free_baggage_rules[0].size_limit.length"


def test_score_case_counts_unknown_pieces_as_wrong_value() -> None:
    data = case_data()
    data["expected"]["free_baggage_rules"][0]["pieces"] = None
    case = EvaluationCase.model_validate(data)
    actual = case.expected.model_copy(deep=True)
    actual.free_baggage_rules[0].pieces = 1

    score = score_case(
        case,
        PredictionRecord(case_id=case.id, status="success", actual=actual),
    )

    assert score.field_metrics["free_baggage_rules.pieces"].accuracy == 0
    assert score.unsupported_values == 1
    assert any(
        issue.path == "free_baggage_rules[0].pieces" and issue.kind == "wrong_value"
        for issue in score.issues
    )


def test_evaluate_predictions_keeps_missing_prediction_in_denominator() -> None:
    first = make_case()
    second = make_case(id="zh-simple-002")
    generated_at = datetime(2026, 9, 10, tzinfo=UTC)

    report = evaluate_predictions(
        [first, second],
        [successful_prediction(first)],
        model="test-model",
        prompt_version="test-prompt",
        domain_schema_version="test-schema",
        package_version="0.1.0",
        model_max_retries=2,
        generated_at=generated_at,
    )

    assert report.case_count == 2
    assert report.successful_predictions == 1
    assert report.failed_predictions == 1
    assert report.exact_match_rate == 0.5
    assert report.field_accuracy == 0.5
    assert report.prediction_success_rate == 0.5
    assert report.rule_recall == 0.5
    assert report.field_metrics["free_baggage_rules.checked_baggage"].accuracy == 0.5
    assert report.cases[1].error_type == "MissingPrediction"
    assert report.generated_at == generated_at
    assert report.domain_schema_version == "test-schema"
    assert report.model_max_retries == 2
    assert report.latency_sample_count == 1
    assert report.average_latency_seconds == 0.25


def test_evaluate_predictions_rejects_unknown_case_id() -> None:
    case = make_case()
    prediction = PredictionRecord(
        case_id="unknown-001",
        status="failure",
        error_type="Timeout",
    )

    with pytest.raises(EvaluationScoringError, match="unknown case IDs"):
        evaluate_predictions([case], [prediction])


def test_score_case_rejects_mismatched_case_id() -> None:
    case = make_case()
    prediction = PredictionRecord(
        case_id="other-001",
        status="failure",
        error_type="Timeout",
    )

    with pytest.raises(EvaluationScoringError, match="does not belong"):
        score_case(case, prediction)


@pytest.mark.parametrize("split", ["dev", "holdout"])
def test_course_gold_data_calibrates_to_full_score(split: str) -> None:
    cases = load_cases(PROJECT_ROOT / "evals" / "datasets" / "v1" / f"{split}.jsonl")
    predictions = [successful_prediction(case) for case in cases]

    report = evaluate_predictions(cases, predictions)

    assert report.exact_match_rate == 1
    assert report.field_accuracy == 1
    assert report.rule_recall == 1
    assert report.missing_rules == 0
    assert report.unsupported_rules == 0
    assert report.unsupported_values == 0
