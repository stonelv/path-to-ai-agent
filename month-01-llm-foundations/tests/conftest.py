import os

import pytest


@pytest.fixture(autouse=True)
def isolate_settings_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in os.environ:
        if name.upper().startswith("MODEL_") or name.upper() == "LOG_LEVEL":
            monkeypatch.delenv(name)
