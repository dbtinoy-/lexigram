from __future__ import annotations

import subprocess
import sys

from scripts.core import command_runner
from scripts.core.command_runner import run_command


def test_run_command_captures_success_output_and_cwd(tmp_path):
    result = run_command(
        [
            sys.executable,
            "-c",
            "import os; print(os.getcwd())",
        ],
        cwd=tmp_path,
    )

    assert result.command == (
        sys.executable,
        "-c",
        "import os; print(os.getcwd())",
    )
    assert result.cwd == tmp_path
    assert result.exit_code == 0
    assert result.stdout.strip() == str(tmp_path)
    assert result.stderr == ""
    assert result.timed_out is False
    assert result.duration_ms >= 0


def test_run_command_captures_failure_output(tmp_path):
    result = run_command(
        [
            sys.executable,
            "-c",
            "import sys; print('boom', file=sys.stderr); sys.exit(2)",
        ],
        cwd=tmp_path,
    )

    assert result.exit_code == 2
    assert "boom" in result.stderr
    assert result.stdout == ""
    assert result.timed_out is False


def test_run_command_captures_timeout_evidence(monkeypatch):
    timeout = subprocess.TimeoutExpired(
        cmd=("demo",),
        timeout=1.5,
        output=b"timed-out stdout",
        stderr=b"timed-out stderr",
    )

    def fake_run(*_args, **_kwargs):
        raise timeout

    monkeypatch.setattr(command_runner.subprocess, "run", fake_run)
    ticks = iter([20.0, 20.125])
    monkeypatch.setattr(command_runner, "perf_counter", lambda: next(ticks))

    result = run_command(["demo"], timeout=1.5)

    assert result.timed_out is True
    assert result.exit_code is None
    assert result.timeout_seconds == 1.5
    assert result.stdout == "timed-out stdout"
    assert result.stderr == "timed-out stderr"
    assert result.duration_ms == 125


def test_run_command_duration_uses_elapsed_time(monkeypatch, tmp_path):
    ticks = iter([10.0, 10.375])
    monkeypatch.setattr(command_runner, "perf_counter", lambda: next(ticks))

    result = run_command([sys.executable, "-c", "print('ok')"])

    assert result.exit_code == 0
    assert result.duration_ms == 375
    assert result.cwd is None
