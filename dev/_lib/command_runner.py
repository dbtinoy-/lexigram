from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
import subprocess
from time import perf_counter

from dev._lib.evidence import CommandEvidence


def _coerce_output(value: str | bytes | None) -> str:
    """Normalize subprocess output to a UTF-8 string."""

    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _duration_ms(started_at: float, finished_at: float) -> int:
    """Convert a perf-counter delta into whole milliseconds."""

    return max(0, int((finished_at - started_at) * 1000))


def run_command(
    command: Sequence[str],
    *,
    cwd: Path | str | None = None,
    timeout: float | None = None,
) -> CommandEvidence:
    """Run a command and capture deterministic execution evidence."""

    command_tuple = tuple(command)
    cwd_path = None if cwd is None else Path(cwd)
    started_at = perf_counter()

    try:
        completed = subprocess.run(
            command_tuple,
            cwd=str(cwd_path) if cwd_path is not None else None,
            capture_output=True,
            check=False,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        finished_at = perf_counter()
        return CommandEvidence(
            command=command_tuple,
            cwd=cwd_path,
            timeout_seconds=timeout,
            exit_code=None,
            stdout=_coerce_output(exc.stdout),
            stderr=_coerce_output(exc.stderr),
            duration_ms=_duration_ms(started_at, finished_at),
            timed_out=True,
        )

    finished_at = perf_counter()
    return CommandEvidence(
        command=command_tuple,
        cwd=cwd_path,
        timeout_seconds=timeout,
        exit_code=completed.returncode,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
        duration_ms=_duration_ms(started_at, finished_at),
    )
