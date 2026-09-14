from collections.abc import Iterable
from pathlib import Path

from pydantic import BaseModel, ValidationError

from baggage_extractor.evaluation.models import EvaluationCase, PredictionRecord
from baggage_extractor.json_utils import loads_strict_json


class EvaluationDataError(ValueError):
    """Raised when an evaluation dataset or prediction file is invalid."""


def _load_jsonl[RecordT: BaseModel](
    path: Path, model_type: type[RecordT]
) -> list[RecordT]:
    if not path.is_file():
        raise EvaluationDataError(f"Evaluation file does not exist: {path}")

    records: list[RecordT] = []
    try:
        with path.open(encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, start=1):
                if not line.strip():
                    continue
                try:
                    records.append(model_type.model_validate(loads_strict_json(line)))
                except (TypeError, ValueError, ValidationError) as error:
                    raise EvaluationDataError(
                        f"Invalid record in {path} at line {line_number}: {error}"
                    ) from error
    except (OSError, UnicodeError) as error:
        raise EvaluationDataError(f"Could not read evaluation file {path}: {error}") from error
    if not records:
        raise EvaluationDataError(f"Evaluation file is empty: {path}")
    return records


def _require_unique(values: Iterable[str], *, label: str, path: Path) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise EvaluationDataError(f"Duplicate {label} '{value}' in {path}.")
        seen.add(value)


def load_cases(path: Path) -> list[EvaluationCase]:
    cases = _load_jsonl(path, EvaluationCase)
    _require_unique((case.id for case in cases), label="case ID", path=path)

    versions = {case.dataset_version for case in cases}
    splits = {case.split for case in cases}
    if len(versions) != 1:
        raise EvaluationDataError(f"Cases in {path} use multiple dataset versions.")
    if len(splits) != 1:
        raise EvaluationDataError(f"Cases in {path} use multiple dataset splits.")
    return cases


def load_predictions(path: Path) -> list[PredictionRecord]:
    predictions = _load_jsonl(path, PredictionRecord)
    _require_unique(
        (prediction.case_id for prediction in predictions),
        label="prediction case ID",
        path=path,
    )
    return predictions


def write_jsonl(path: Path, records: Iterable[BaseModel], *, overwrite: bool = False) -> None:
    require_writable_output(path, overwrite=overwrite)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    try:
        with temporary_path.open("w", encoding="utf-8", newline="\n") as stream:
            for record in records:
                stream.write(record.model_dump_json())
                stream.write("\n")
        temporary_path.replace(path)
    except OSError as error:
        raise EvaluationDataError(f"Could not write evaluation file {path}: {error}") from error
    finally:
        temporary_path.unlink(missing_ok=True)


def write_report(path: Path, report: BaseModel, *, overwrite: bool = False) -> None:
    require_writable_output(path, overwrite=overwrite)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    try:
        temporary_path.write_text(
            report.model_dump_json(indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        temporary_path.replace(path)
    except OSError as error:
        raise EvaluationDataError(f"Could not write evaluation report {path}: {error}") from error
    finally:
        temporary_path.unlink(missing_ok=True)


def require_writable_output(path: Path, *, overwrite: bool = False) -> None:
    if path.exists():
        if not path.is_file():
            raise EvaluationDataError(f"Output path is not a file: {path}")
        if not overwrite:
            raise EvaluationDataError(f"Refusing to overwrite existing file: {path}")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise EvaluationDataError(
            f"Could not prepare output directory for {path}: {error}"
        ) from error
