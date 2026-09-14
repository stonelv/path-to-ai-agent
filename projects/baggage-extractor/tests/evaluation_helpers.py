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
