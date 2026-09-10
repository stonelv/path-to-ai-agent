import json

import pytest
from pydantic import ValidationError

from baggage_extractor.models import (
    CarryOnBaggageRule,
    ExtractionResult,
    FreeBaggageRule,
    SizeLimit,
)


def make_size_limit(**overrides: object) -> SizeLimit:
    values: dict[str, object] = {
        "length": 55,
        "width": 40,
        "height": 20,
        "note": "三边尺寸限制",
    }
    values.update(overrides)
    return SizeLimit.model_validate(values)


def make_rule(
    rule_type: type[FreeBaggageRule] | type[CarryOnBaggageRule],
    **overrides: object,
) -> FreeBaggageRule | CarryOnBaggageRule:
    values: dict[str, object] = {
        "cabin_class": "经济舱",
        "fare_codes": ["Y", "B", "M"],
        "checked_baggage": "每件不超过23公斤",
        "pieces": 1,
        "size_limit": make_size_limit(),
        "special_notes": "超过限制需支付逾重行李费",
    }
    values.update(overrides)
    return rule_type.model_validate(values)


def make_result(**overrides: object) -> ExtractionResult:
    values: dict[str, object] = {
        "airline_code": "CA",
        "airline_name": "中国国际航空",
        "free_baggage_rules": [make_rule(FreeBaggageRule)],
        "baggage_rules": [
            make_rule(
                CarryOnBaggageRule,
                checked_baggage="每件不超过5公斤",
                pieces=1,
                special_notes="",
            )
        ],
    }
    values.update(overrides)
    return ExtractionResult.model_validate(values)


def assert_error_at(
    error: ValidationError,
    location: tuple[str | int, ...],
    error_type: str,
) -> None:
    assert any(
        detail["loc"] == location and detail["type"] == error_type
        for detail in error.errors()
    )


def test_accepts_final_baggage_data_format() -> None:
    result = make_result()

    assert result.airline_code == "CA"
    assert result.airline_name == "中国国际航空"
    assert result.free_baggage_rules[0].fare_codes == ["Y", "B", "M"]
    assert result.free_baggage_rules[0].checked_baggage == "每件不超过23公斤"
    assert result.baggage_rules[0].checked_baggage == "每件不超过5公斤"
    assert result.baggage_rules[0].size_limit.height == 20
    assert result.baggage_rules[0].special_notes == ""


def test_accepts_eastern_airlines_expected_example() -> None:
    payload = {
        "airline_code": "MU",
        "airline_name": "中国东方航空",
        "free_baggage_rules": [
            {
                "cabin_class": "头等舱",
                "fare_codes": [],
                "checked_baggage": "40kg",
                "pieces": None,
                "size_limit": {
                    "length": 40,
                    "width": 60,
                    "height": 100,
                    "note": "每件行李尺寸不小于5×15×20cm且不超过40×60×100cm",
                },
                "special_notes": "每件重量不超过50kg",
            },
            {
                "cabin_class": "豪华公务舱、公务舱",
                "fare_codes": [],
                "checked_baggage": "30kg",
                "pieces": None,
                "size_limit": {
                    "length": 40,
                    "width": 60,
                    "height": 100,
                    "note": "每件行李尺寸不小于5×15×20cm且不超过40×60×100cm",
                },
                "special_notes": "每件重量不超过50kg",
            },
            {
                "cabin_class": "超级经济舱、经济舱",
                "fare_codes": [],
                "checked_baggage": "20kg",
                "pieces": None,
                "size_limit": {
                    "length": 40,
                    "width": 60,
                    "height": 100,
                    "note": "每件行李尺寸不小于5×15×20cm且不超过40×60×100cm",
                },
                "special_notes": "每件重量不超过50kg",
            },
        ],
        "baggage_rules": [
            {
                "cabin_class": "头等舱",
                "fare_codes": [],
                "checked_baggage": "10kg",
                "pieces": 2,
                "size_limit": {
                    "length": 55,
                    "width": 40,
                    "height": 20,
                    "note": "每件行李尺寸不超过55×40×20cm",
                },
                "special_notes": "",
            },
            {
                "cabin_class": "豪华公务舱、公务舱",
                "fare_codes": [],
                "checked_baggage": "8kg",
                "pieces": 2,
                "size_limit": {
                    "length": 55,
                    "width": 40,
                    "height": 20,
                    "note": "每件行李尺寸不超过55×40×20cm",
                },
                "special_notes": "",
            },
            {
                "cabin_class": "超级经济舱、经济舱",
                "fare_codes": [],
                "checked_baggage": "8kg",
                "pieces": 1,
                "size_limit": {
                    "length": 55,
                    "width": 40,
                    "height": 20,
                    "note": "每件行李尺寸不超过55×40×20cm",
                },
                "special_notes": "",
            },
        ],
    }

    result = ExtractionResult.model_validate(payload)

    assert result.model_dump(mode="json") == payload


def test_serializes_exact_top_level_fields() -> None:
    payload = json.loads(make_result().model_dump_json())

    assert set(payload) == {
        "airline_code",
        "airline_name",
        "free_baggage_rules",
        "baggage_rules",
    }
    assert set(payload["free_baggage_rules"][0]) == {
        "cabin_class",
        "fare_codes",
        "checked_baggage",
        "pieces",
        "size_limit",
        "special_notes",
    }
    assert set(payload["free_baggage_rules"][0]["size_limit"]) == {
        "length",
        "width",
        "height",
        "note",
    }


def test_keeps_free_and_carry_on_rules_separate() -> None:
    result = make_result()

    assert isinstance(result.free_baggage_rules[0], FreeBaggageRule)
    assert isinstance(result.baggage_rules[0], CarryOnBaggageRule)


def test_accepts_multiple_rules_and_fare_codes() -> None:
    result = make_result(
        free_baggage_rules=[
            make_rule(FreeBaggageRule),
            make_rule(
                FreeBaggageRule,
                cabin_class="公务舱",
                fare_codes=["C", "D", "Z"],
                checked_baggage="每件不超过32公斤",
                pieces=2,
            ),
        ]
    )

    assert len(result.free_baggage_rules) == 2
    assert result.free_baggage_rules[1].fare_codes == ["C", "D", "Z"]


def test_accepts_empty_rule_lists() -> None:
    result = make_result(free_baggage_rules=[], baggage_rules=[])

    assert result.free_baggage_rules == []
    assert result.baggage_rules == []


def test_preserves_null_for_unknown_text_fields() -> None:
    result = make_result(
        airline_code=None,
        free_baggage_rules=[
            make_rule(
                FreeBaggageRule,
                cabin_class=None,
                checked_baggage=None,
                pieces=None,
                size_limit=make_size_limit(length=None, width=None, height=None, note=""),
                special_notes="",
            )
        ],
    )

    assert result.airline_code is None
    assert result.free_baggage_rules[0].pieces is None
    assert result.free_baggage_rules[0].size_limit.length is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("pieces", -1),
        ("pieces", "2"),
    ],
)
def test_rejects_invalid_piece_values(field: str, value: object) -> None:
    with pytest.raises(ValidationError) as exc_info:
        make_rule(FreeBaggageRule, **{field: value})

    expected_type = "greater_than_equal" if value == -1 else "int_type"
    assert_error_at(exc_info.value, (field,), expected_type)


@pytest.mark.parametrize("value", [-1, "55"])
def test_rejects_invalid_dimension_values(value: object) -> None:
    with pytest.raises(ValidationError) as exc_info:
        make_size_limit(length=value)

    expected_type = "greater_than_equal" if value == -1 else "int_type"
    assert_error_at(exc_info.value, ("length",), expected_type)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("airline_code", ""),
        ("airline_name", "   "),
    ],
)
def test_rejects_blank_airline_fields(field: str, value: str) -> None:
    with pytest.raises(ValidationError) as exc_info:
        make_result(**{field: value})

    expected_type = "string_too_short" if value == "" else "string_pattern_mismatch"
    assert_error_at(exc_info.value, (field,), expected_type)


def test_rejects_blank_fare_code_with_precise_location() -> None:
    with pytest.raises(ValidationError) as exc_info:
        make_rule(FreeBaggageRule, fare_codes=["Y", " "])

    assert_error_at(exc_info.value, ("fare_codes", 1), "string_pattern_mismatch")


def test_rejects_missing_required_output_key() -> None:
    payload = make_result().model_dump()
    del payload["baggage_rules"]

    with pytest.raises(ValidationError) as exc_info:
        ExtractionResult.model_validate(payload)

    assert_error_at(exc_info.value, ("baggage_rules",), "missing")


def test_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError) as exc_info:
        make_result(warnings=[])

    assert_error_at(exc_info.value, ("warnings",), "extra_forbidden")


def test_generated_json_schema_matches_final_contract() -> None:
    schema = ExtractionResult.model_json_schema()
    serialized_schema = json.dumps(schema)
    properties = schema["properties"]

    assert serialized_schema
    assert set(properties) == {
        "airline_code",
        "airline_name",
        "free_baggage_rules",
        "baggage_rules",
    }
    assert set(schema["required"]) == set(properties)
    assert properties["free_baggage_rules"]["type"] == "array"
    assert properties["baggage_rules"]["type"] == "array"
    assert properties["free_baggage_rules"]["items"]["$ref"].endswith("/FreeBaggageRule")
    assert properties["baggage_rules"]["items"]["$ref"].endswith("/CarryOnBaggageRule")
    assert set(schema["$defs"]["SizeLimit"]["required"]) == {
        "length",
        "width",
        "height",
        "note",
    }
    pieces_schema = schema["$defs"]["FreeBaggageRule"]["properties"]["pieces"]["anyOf"]
    length_schema = schema["$defs"]["SizeLimit"]["properties"]["length"]["anyOf"]
    assert {"minimum": 0, "type": "integer"} in pieces_schema
    assert {"minimum": 0, "type": "integer"} in length_schema
    assert "schema_version" not in serialized_schema
    assert "warnings" not in serialized_schema
