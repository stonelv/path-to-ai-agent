import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tool_agent.demo import main


@pytest.mark.parametrize(
    ("scenario", "termination", "exit_code"),
    [
        ("success", "success", 0),
        ("denied", "denied", 3),
        ("tool-error", "tool_error", 4),
        ("step-limit", "step_limit", 6),
        ("timeout", "timeout", 8),
    ],
)
def test_offline_scenarios(scenario, termination, exit_code, capsys):
    assert main(["--scenario", scenario, "--timeout", "0.01"]) == exit_code
    result = json.loads(capsys.readouterr().out)
    assert result["termination"] == termination
    assert result["mode"] == "offline_scripted_mechanism_demo_not_model_quality"
    assert result["events"][-1]["event"] == "terminated"
    if exit_code:
        assert result["answer"] is None


def test_success_output_is_deterministic(capsys):
    main([])
    first = capsys.readouterr().out
    main([])
    assert capsys.readouterr().out == first


def test_cli_process_propagates_nonzero_exit_and_json():
    root = Path(__file__).resolve().parents[1]
    env = {**os.environ, "PYTHONPATH": str(root / "src")}
    process = subprocess.run(
        [sys.executable, "-m", "tool_agent", "--scenario", "denied"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert process.returncode == 3
    assert process.stderr == ""
    assert json.loads(process.stdout)["termination"] == "denied"


def test_invalid_cli_limits_exit_two(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--timeout", "nan"])
    assert exc.value.code == 2
    assert "timeout_seconds" in capsys.readouterr().err
