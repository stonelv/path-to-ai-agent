import argparse
import asyncio
import sys
from collections.abc import Sequence

from baggage_extractor.config import get_settings
from baggage_extractor.errors import ExtractionError
from baggage_extractor.extractor import BaggageExtractor
from baggage_extractor.providers import (
    ModelProvider,
    ModelProviderError,
    OpenAICompatibleProvider,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract structured airline baggage data from policy text."
    )
    parser.add_argument("policy_text", help="Airline baggage policy text to extract.")
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    provider: ModelProvider | None = None,
) -> int:
    args = build_parser().parse_args(argv)
    active_provider = provider or OpenAICompatibleProvider(get_settings())

    try:
        result = asyncio.run(BaggageExtractor(active_provider).extract(args.policy_text))
    except (ExtractionError, ModelProviderError) as error:
        print(f"Extraction failed: {error}", file=sys.stderr)
        return 1

    print(result.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
