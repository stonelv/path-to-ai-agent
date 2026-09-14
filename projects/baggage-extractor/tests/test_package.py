import baggage_extractor


def test_package_version() -> None:
    assert baggage_extractor.__version__ == "0.1.0"
