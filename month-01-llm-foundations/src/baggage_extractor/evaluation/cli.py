import argparse
import asyncio
import sys
from collections.abc import Sequence
from pathlib import Path
from time import perf_counter
from typing import TextIO

from pydantic import ValidationError

from baggage_extractor import __version__
from baggage_extractor.config import Settings, get_settings
from baggage_extractor.errors import ExtractionError
from baggage_extractor.evaluation.loader import (
    EvaluationDataError,
    load_cases,
    load_predictions,
    require_writable_output,
    write_jsonl,
    write_report,
)
from baggage_extractor.evaluation.models import (
    EvaluationCase,
    PredictionRecord,
    PredictionStatus,
)
from baggage_extractor.evaluation.scorer import (
    EvaluationScoringError,
    evaluate_predictions,
)
from baggage_extractor.extractor import BaggageExtractor
from baggage_extractor.models import DOMAIN_SCHEMA_VERSION
from baggage_extractor.prompts import PROMPT_VERSION
from baggage_extractor.providers import ModelProviderError, OpenAICompatibleProvider

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_HOLDOUT_DATASET = PROJECT_ROOT / "evals" / "datasets" / "v1" / "holdout.jsonl"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Score saved predictions or explicitly run a real-model evaluation."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    score_parser = subparsers.add_parser(
        "score",
        help="Score saved predictions without model or network access.",
    )
    score_parser.add_argument("--dataset", type=Path, default=DEFAULT_HOLDOUT_DATASET)
    score_parser.add_argument("--predictions", type=Path, required=True)
    score_parser.add_argument("--output", type=Path)
    score_parser.add_argument("--model")
    score_parser.add_argument("--prompt-version")
    score_parser.add_argument("--domain-schema-version")
    score_parser.add_argument("--package-version")
    score_parser.add_argument("--model-max-retries", type=int)
    score_parser.add_argument("--overwrite", action="store_true")

    run_parser = subparsers.add_parser(
        "run",
        help="Call the configured real model, save predictions, then score them.",
    )
    run_parser.add_argument("--dataset", type=Path, default=DEFAULT_HOLDOUT_DATASET)
    run_parser.add_argument("--predictions-output", type=Path, required=True)
    run_parser.add_argument("--report-output", type=Path, required=True)
    run_parser.add_argument(
        "--confirm-max-requests",
        type=int,
        required=True,
        help="Must equal cases multiplied by maximum attempts per case.",
    )
    run_parser.add_argument("--overwrite", action="store_true")
    return parser


def _print_configuration_error(error: ValidationError) -> None:
    fields = sorted({str(detail["loc"][0]) for detail in error.errors()})
    print(f"Invalid model configuration: {', '.join(fields)}.", file=sys.stderr)


def _require_distinct_paths(named_paths: dict[str, Path]) -> None:
    resolved: dict[Path, str] = {}
    for label, path in named_paths.items():
        normalized = path.resolve()
        if normalized in resolved:
            raise EvaluationDataError(
                f"{label} path must differ from {resolved[normalized]} path: {path}"
            )
        resolved[normalized] = label


async def _run_cases(
    cases: Sequence[EvaluationCase],
    extractor: BaggageExtractor,
    *,
    progress: TextIO | None = None,
) -> list[PredictionRecord]:
    predictions: list[PredictionRecord] = []
    for index, case in enumerate(cases, start=1):
        if progress is not None:
            print(f"[{index}/{len(cases)}] {case.id}: running", file=progress, flush=True)
        started = perf_counter()
        try:
            actual = await extractor.extract(case.policy_text)
        except (ExtractionError, ModelProviderError) as error:
            predictions.append(
                PredictionRecord(
                    case_id=case.id,
                    status=PredictionStatus.FAILURE,
                    error_type=type(error).__name__,
                    error_message=str(error),
                    latency_seconds=perf_counter() - started,
                )
            )
            if progress is not None:
                print(
                    f"[{index}/{len(cases)}] {case.id}: {type(error).__name__}",
                    file=progress,
                    flush=True,
                )
        else:
            predictions.append(
                PredictionRecord(
                    case_id=case.id,
                    status=PredictionStatus.SUCCESS,
                    actual=actual,
                    latency_seconds=perf_counter() - started,
                )
            )
            if progress is not None:
                print(f"[{index}/{len(cases)}] {case.id}: success", file=progress, flush=True)
    return predictions


async def _run_real_evaluation(
    cases: Sequence[EvaluationCase],
    settings: Settings,
) -> list[PredictionRecord]:
    async with OpenAICompatibleProvider(settings) as provider:
        return await _run_cases(cases, BaggageExtractor(provider), progress=sys.stderr)


def _score_command(args: argparse.Namespace) -> int:
    if args.output is not None:
        _require_distinct_paths(
            {
                "dataset": args.dataset,
                "predictions": args.predictions,
                "report output": args.output,
            }
        )
    cases = load_cases(args.dataset)
    predictions = load_predictions(args.predictions)
    report = evaluate_predictions(
        cases,
        predictions,
        model=args.model,
        prompt_version=args.prompt_version,
        domain_schema_version=args.domain_schema_version,
        package_version=args.package_version,
        model_max_retries=args.model_max_retries,
    )
    if args.output is not None:
        write_report(args.output, report, overwrite=args.overwrite)
    print(report.model_dump_json(indent=2))
    return 0


def _run_command(args: argparse.Namespace) -> int:
    _require_distinct_paths(
        {
            "dataset": args.dataset,
            "predictions output": args.predictions_output,
            "report output": args.report_output,
        }
    )
    cases = load_cases(args.dataset)
    require_writable_output(args.predictions_output, overwrite=args.overwrite)
    require_writable_output(args.report_output, overwrite=args.overwrite)
    try:
        settings = get_settings()
    except ValidationError as error:
        _print_configuration_error(error)
        return 2

    max_requests = len(cases) * (settings.model_max_retries + 1)
    if args.confirm_max_requests != max_requests:
        print(
            f"Request confirmation mismatch: expected --confirm-max-requests {max_requests} "
            f"for {len(cases)} cases and {settings.model_max_retries + 1} attempts per case.",
            file=sys.stderr,
        )
        return 2

    predictions = asyncio.run(_run_real_evaluation(cases, settings))
    report = evaluate_predictions(
        cases,
        predictions,
        model=settings.model_name,
        prompt_version=PROMPT_VERSION,
        domain_schema_version=DOMAIN_SCHEMA_VERSION,
        package_version=__version__,
        model_max_retries=settings.model_max_retries,
    )
    write_jsonl(args.predictions_output, predictions, overwrite=args.overwrite)
    write_report(args.report_output, report, overwrite=args.overwrite)
    print(report.model_dump_json(indent=2))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "score":
            return _score_command(args)
        return _run_command(args)
    except (EvaluationDataError, EvaluationScoringError) as error:
        print(f"Evaluation data error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
