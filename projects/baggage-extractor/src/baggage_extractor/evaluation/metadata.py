from dataclasses import dataclass

from baggage_extractor.evaluation.models import (
    UNVERIFIED_DATASET_LIMITATION,
    DatasetSplit,
    DatasetUsage,
)


@dataclass(frozen=True, slots=True)
class DatasetMetadata:
    usage: DatasetUsage
    limitations: tuple[str, ...]


SMALL_SYNTHETIC_DATASET_LIMITATION = (
    "This small synthetic teaching dataset is not statistically representative."
)

# Explicit declarations, not an inference from file names or split labels.
DATASET_METADATA = {
    ("baggage-eval-v1", DatasetSplit.DEV): DatasetMetadata(
        usage=DatasetUsage.DEVELOPMENT,
        limitations=(
            "Development cases are available for prompt tuning, not independent validation.",
            SMALL_SYNTHETIC_DATASET_LIMITATION,
        ),
    ),
    ("baggage-eval-v1", DatasetSplit.HOLDOUT): DatasetMetadata(
        usage=DatasetUsage.REGRESSION,
        limitations=(
            "Prompt v2 was tuned using failures from this original holdout; "
            "use it for teaching and regression, not independent validation.",
            SMALL_SYNTHETIC_DATASET_LIMITATION,
        ),
    ),
}


def get_dataset_metadata(dataset_version: str, split: DatasetSplit) -> DatasetMetadata:
    return DATASET_METADATA.get(
        (dataset_version, split),
        DatasetMetadata(
            usage=DatasetUsage.UNVERIFIED,
            limitations=(UNVERIFIED_DATASET_LIMITATION,),
        ),
    )
