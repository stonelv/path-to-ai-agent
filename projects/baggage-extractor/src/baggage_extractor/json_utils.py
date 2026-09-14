import json
from typing import NoReturn


def _reject_nonstandard_constant(value: str) -> NoReturn:
    raise ValueError(f"Nonstandard JSON numeric constant: {value}")


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON object key: {key}")
        result[key] = value
    return result


def loads_strict_json(value: str) -> object:
    return json.loads(
        value,
        parse_constant=_reject_nonstandard_constant,
        object_pairs_hook=_reject_duplicate_keys,
    )
