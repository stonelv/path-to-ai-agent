import json
from pathlib import Path

import pytest
from test_evaluation_models import case_data

from baggage_extractor.evaluation.loader import (
    EvaluationDataError,
    load_cases,
    load_predictions,
    write_jsonl,
    write_report,
)
from baggage_extractor.evaluation.models import PredictionRecord, PredictionStatus

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def write_lines(path: Path, records: list[str]) -> None:
    path.write_text("\n".join(records) + "\n", encoding="utf-8")


def test_load_cases_validates_unique_ids_version_and_split(tmp_path: Path) -> None:
    first = case_data()
    second = case_data()
    second["id"] = "zh-simple-002"
    path = tmp_path / "dev.jsonl"
    write_lines(
        path,
        [
            json.dumps(first, ensure_ascii=False),
            json.dumps(second, ensure_ascii=False),
        ],
    )

    cases = load_cases(path)

    assert [case.id for case in cases] == ["zh-simple-001", "zh-simple-002"]


def test_load_cases_reports_line_number_for_invalid_record(tmp_path: Path) -> None:
    path = tmp_path / "dev.jsonl"
    write_lines(path, [json.dumps(case_data()), "{}"])

    with pytest.raises(EvaluationDataError, match=r"line 2"):
        load_cases(path)


def test_load_cases_rejects_duplicate_json_keys(tmp_path: Path) -> None:
    path = tmp_path / "dev.jsonl"
    path.write_text('{"id":"first","id":"second"}\n', encoding="utf-8")

    with pytest.raises(EvaluationDataError, match=r"line 1.*Duplicate JSON object key"):
        load_cases(path)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("id", "zh-simple-001", "Duplicate case ID"),
        ("dataset_version", "other-version", "multiple dataset versions"),
        ("split", "holdout", "multiple dataset splits"),
    ],
)
def test_load_cases_rejects_inconsistent_file(
    tmp_path: Path, field: str, value: str, message: str
) -> None:
    first = case_data()
    second = case_data()
    second["id"] = "zh-simple-002"
    second[field] = value
    path = tmp_path / "cases.jsonl"
    write_lines(
        path,
        [
            json.dumps(first, ensure_ascii=False),
            json.dumps(second, ensure_ascii=False),
        ],
    )

    with pytest.raises(EvaluationDataError, match=message):
        load_cases(path)


def test_load_predictions_rejects_duplicate_case_id(tmp_path: Path) -> None:
    prediction = PredictionRecord(
        case_id="case-001",
        status=PredictionStatus.FAILURE,
        error_type="Timeout",
    )
    path = tmp_path / "predictions.jsonl"
    write_jsonl(path, [prediction, prediction])

    with pytest.raises(EvaluationDataError, match="Duplicate prediction case ID"):
        load_predictions(path)


def test_load_predictions_rejects_missing_nested_schema_field(tmp_path: Path) -> None:
    prediction = {
        "case_id": "zh-simple-001",
        "status": "success",
        "actual": case_data()["expected"],
    }
    del prediction["actual"]["free_baggage_rules"][0]["size_limit"]["note"]
    path = tmp_path / "predictions.jsonl"
    write_lines(path, [json.dumps(prediction, ensure_ascii=False)])

    with pytest.raises(EvaluationDataError, match="line 1"):
        load_predictions(path)


def test_write_helpers_refuse_to_overwrite(tmp_path: Path) -> None:
    prediction = PredictionRecord(
        case_id="case-001",
        status=PredictionStatus.FAILURE,
        error_type="Timeout",
    )
    path = tmp_path / "predictions.jsonl"

    write_jsonl(path, [prediction])

    with pytest.raises(EvaluationDataError, match="Refusing to overwrite"):
        write_jsonl(path, [prediction])
    with pytest.raises(EvaluationDataError, match="Refusing to overwrite"):
        write_report(path, prediction)


def test_versioned_course_datasets_are_valid_and_cover_distinct_cases() -> None:
    dataset_root = PROJECT_ROOT / "evals" / "datasets" / "v1"

    dev_cases = load_cases(dataset_root / "dev.jsonl")
    holdout_cases = load_cases(dataset_root / "holdout.jsonl")

    assert len(dev_cases) == 6
    assert len(holdout_cases) == 6
    assert {case.id for case in dev_cases}.isdisjoint(case.id for case in holdout_cases)
    assert {case.dataset_version for case in [*dev_cases, *holdout_cases]} == {
        "baggage-eval-v1"
    }
    all_tags = {tag for case in [*dev_cases, *holdout_cases] for tag in case.tags}
    assert {
        "checked-baggage",
        "carry-on",
        "missing-information",
        "explicit-zero",
        "multiple-rules",
        "unrelated",
    } <= all_tags
