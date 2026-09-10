from copy import deepcopy

import pytest
from pydantic import ValidationError

from baggage_extractor.evaluation.models import (
    EvaluationCase,
    PredictionRecord,
    PredictionStatus,
)


def case_data() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "dataset_version": "baggage-eval-v1",
        "id": "zh-simple-001",
        "split": "dev",
        "policy_text": "示例航空经济舱可免费托运1件23kg行李。",
        "expected": {
            "airline_code": None,
            "airline_name": "示例航空",
            "free_baggage_rules": [
                {
                    "cabin_class": "经济舱",
                    "fare_codes": [],
                    "checked_baggage": "每件不超过23kg",
                    "pieces": 1,
                    "size_limit": {
                        "length": None,
                        "width": None,
                        "height": None,
                        "note": "",
                    },
                    "special_notes": "",
                }
            ],
            "baggage_rules": [],
        },
        "tags": ["zh", "simple", "checked-baggage"],
        "source": {"type": "synthetic", "note": "课程自编"},
    }


def test_evaluation_case_validates_versioned_contract() -> None:
    case = EvaluationCase.model_validate(case_data())

    assert case.id == "zh-simple-001"
    assert case.expected.free_baggage_rules[0].pieces == 1
    assert case.source.type == "synthetic"


def test_evaluation_case_rejects_duplicate_tags() -> None:
    data = case_data()
    data["tags"] = ["zh", "zh"]

    with pytest.raises(ValidationError, match="tags must be unique"):
        EvaluationCase.model_validate(data)


def test_evaluation_case_rejects_ambiguous_expected_rule_identity() -> None:
    data = case_data()
    expected = data["expected"]
    expected["free_baggage_rules"].append(deepcopy(expected["free_baggage_rules"][0]))

    with pytest.raises(ValidationError, match="ambiguous rule identities"):
        EvaluationCase.model_validate(data)


def test_evaluation_case_rejects_duplicate_expected_fare_codes() -> None:
    data = case_data()
    data["expected"]["free_baggage_rules"][0]["fare_codes"] = ["Y", "Y"]

    with pytest.raises(ValidationError, match="duplicate fare codes"):
        EvaluationCase.model_validate(data)


@pytest.mark.parametrize(
    "data",
    [
        {"case_id": "case-001", "status": "success"},
        {
            "case_id": "case-001",
            "status": "failure",
            "actual": case_data()["expected"],
            "error_type": "Timeout",
        },
        {"case_id": "case-001", "status": "failure"},
    ],
)
def test_prediction_record_rejects_inconsistent_outcomes(data: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        PredictionRecord.model_validate(data)


def test_prediction_record_accepts_failure_without_message() -> None:
    prediction = PredictionRecord(
        case_id="case-001",
        status=PredictionStatus.FAILURE,
        error_type="ProviderTimeoutError",
    )

    assert prediction.actual is None
    assert prediction.error_message is None
