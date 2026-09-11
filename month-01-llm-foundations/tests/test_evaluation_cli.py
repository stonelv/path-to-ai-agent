import json
from pathlib import Path

import pytest
from test_evaluation_models import case_data

from baggage_extractor.config import Settings
from baggage_extractor.evaluation.cli import main
from baggage_extractor.evaluation.loader import write_jsonl
from baggage_extractor.evaluation.models import (
    EvaluationCase,
    PredictionRecord,
    PredictionStatus,
)
from baggage_extractor.models import ExtractionResult
from baggage_extractor.providers import ModelRequest, ModelResponse, ProviderTimeoutError

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def create_dataset(path: Path) -> EvaluationCase:
    case = EvaluationCase.model_validate(case_data())
    write_jsonl(path, [case])
    return case


def test_score_command_outputs_report_without_network(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dataset = tmp_path / "dev.jsonl"
    predictions = tmp_path / "predictions.jsonl"
    report_path = tmp_path / "report.json"
    case = create_dataset(dataset)
    write_jsonl(
        predictions,
        [
            PredictionRecord(
                case_id=case.id,
                status=PredictionStatus.SUCCESS,
                actual=case.expected,
            )
        ],
    )

    exit_code = main(
        [
            "score",
            "--dataset",
            str(dataset),
            "--predictions",
            str(predictions),
            "--output",
            str(report_path),
            "--model",
            "saved-model",
        ]
    )

    assert exit_code == 0
    stdout_report = json.loads(capsys.readouterr().out)
    saved_report = json.loads(report_path.read_text(encoding="utf-8"))
    assert stdout_report == saved_report
    assert saved_report["exact_match_rate"] == 1.0
    assert saved_report["model"] == "saved-model"


def test_course_demo_metrics_match_lesson(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(
        [
            "score",
            "--dataset",
            str(PROJECT_ROOT / "evals" / "datasets" / "v1" / "dev.jsonl"),
            "--predictions",
            str(
                PROJECT_ROOT
                / "evals"
                / "examples"
                / "dev-predictions-with-errors.jsonl"
            ),
            "--model",
            "scorer-demo",
            "--prompt-version",
            "not-a-model-run",
        ]
    )

    report = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert {
        "case_count": report["case_count"],
        "successful_predictions": report["successful_predictions"],
        "failed_predictions": report["failed_predictions"],
        "exact_matches": report["exact_matches"],
        "exact_match_rate": report["exact_match_rate"],
        "missing_rules": report["missing_rules"],
        "unsupported_rules": report["unsupported_rules"],
        "unsupported_values": report["unsupported_values"],
    } == {
        "case_count": 6,
        "successful_predictions": 5,
        "failed_predictions": 1,
        "exact_matches": 3,
        "exact_match_rate": 0.5,
        "missing_rules": 3,
        "unsupported_rules": 1,
        "unsupported_values": 4,
    }


def test_score_command_reports_data_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(
        [
            "score",
            "--dataset",
            str(tmp_path / "missing.jsonl"),
            "--predictions",
            str(tmp_path / "predictions.jsonl"),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert "Evaluation data error" in captured.err


def test_score_command_never_overwrites_an_input_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dataset = tmp_path / "dev.jsonl"
    predictions = tmp_path / "predictions.jsonl"
    case = create_dataset(dataset)
    write_jsonl(
        predictions,
        [PredictionRecord(case_id=case.id, status="success", actual=case.expected)],
    )

    exit_code = main(
        [
            "score",
            "--dataset",
            str(dataset),
            "--predictions",
            str(predictions),
            "--output",
            str(dataset),
            "--overwrite",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "report output path must differ from dataset path" in captured.err
    assert len(dataset.read_text(encoding="utf-8").splitlines()) == 1


def test_run_command_requires_exact_request_confirmation_before_calling_provider(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset = tmp_path / "dev.jsonl"
    create_dataset(dataset)
    settings = Settings(
        model_api_key="test-key",
        model_name="test-model",
        model_base_url="https://models.example.com/v1",
        model_max_retries=2,
        _env_file=None,
    )
    monkeypatch.setattr("baggage_extractor.evaluation.cli.get_settings", lambda: settings)

    def unexpected_provider(settings: Settings) -> None:
        raise AssertionError("Provider must not be created before request confirmation.")

    monkeypatch.setattr(
        "baggage_extractor.evaluation.cli.OpenAICompatibleProvider",
        unexpected_provider,
    )

    exit_code = main(
        [
            "run",
            "--dataset",
            str(dataset),
            "--predictions-output",
            str(tmp_path / "predictions.jsonl"),
            "--report-output",
            str(tmp_path / "report.json"),
            "--confirm-max-requests",
            "1",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert "expected --confirm-max-requests 3" in captured.err


def test_run_command_refuses_existing_output_before_loading_configuration(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset = tmp_path / "dev.jsonl"
    output = tmp_path / "predictions.jsonl"
    create_dataset(dataset)
    output.write_text("existing", encoding="utf-8")

    def unexpected_settings() -> Settings:
        raise AssertionError("Settings must not load after output preflight fails.")

    monkeypatch.setattr("baggage_extractor.evaluation.cli.get_settings", unexpected_settings)

    exit_code = main(
        [
            "run",
            "--dataset",
            str(dataset),
            "--predictions-output",
            str(output),
            "--report-output",
            str(tmp_path / "report.json"),
            "--confirm-max-requests",
            "3",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert "Refusing to overwrite" in captured.err


def test_run_command_saves_predictions_and_versioned_report_without_real_network(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset = tmp_path / "dev.jsonl"
    predictions_path = tmp_path / "runs" / "predictions.jsonl"
    report_path = tmp_path / "runs" / "report.json"
    case = create_dataset(dataset)
    settings = Settings(
        model_api_key="test-key",
        model_name="test-model",
        model_base_url="https://models.example.com/v1",
        model_max_retries=2,
        _env_file=None,
    )

    class StubContextProvider:
        def __init__(self, active_settings: Settings) -> None:
            assert active_settings is settings

        async def __aenter__(self) -> "StubContextProvider":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def generate(self, request: ModelRequest) -> ModelResponse:
            return ModelResponse(content=case.expected.model_dump_json(), model="test-model")

    monkeypatch.setattr("baggage_extractor.evaluation.cli.get_settings", lambda: settings)
    monkeypatch.setattr(
        "baggage_extractor.evaluation.cli.OpenAICompatibleProvider",
        StubContextProvider,
    )

    exit_code = main(
        [
            "run",
            "--dataset",
            str(dataset),
            "--predictions-output",
            str(predictions_path),
            "--report-output",
            str(report_path),
            "--confirm-max-requests",
            "3",
        ]
    )

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out)["exact_match_rate"] == 1
    prediction = json.loads(predictions_path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert prediction["case_id"] == case.id
    assert prediction["latency_seconds"] >= 0
    assert report["model"] == "test-model"
    assert report["prompt_version"] == "baggage-extraction-v2"
    assert report["domain_schema_version"] == "baggage-result-v1"
    assert report["package_version"] == "0.1.0"
    assert report["model_max_retries"] == 2


async def test_run_cases_preserves_success_and_known_failure() -> None:
    from baggage_extractor.evaluation.cli import _run_cases
    from baggage_extractor.extractor import BaggageExtractor

    class StubProvider:
        def __init__(self) -> None:
            self.calls = 0

        async def generate(self, request: ModelRequest) -> ModelResponse:
            self.calls += 1
            if self.calls == 2:
                raise ProviderTimeoutError("timed out", retryable=True)
            return ModelResponse(
                content=ExtractionResult(
                    airline_code=None,
                    airline_name=None,
                    free_baggage_rules=[],
                    baggage_rules=[],
                ).model_dump_json(),
                model="stub-model",
            )

    first = EvaluationCase.model_validate(case_data())
    second_data = case_data()
    second_data["id"] = "zh-simple-002"
    second = EvaluationCase.model_validate(second_data)

    predictions = await _run_cases([first, second], BaggageExtractor(StubProvider()))

    assert predictions[0].status is PredictionStatus.SUCCESS
    assert predictions[1].status is PredictionStatus.FAILURE
    assert predictions[1].error_type == "ProviderTimeoutError"
    assert predictions[1].latency_seconds is not None
