from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class CommandEvidence:
    """Execution evidence captured from a command invocation."""

    command: tuple[str, ...]
    cwd: Path | None
    timeout_seconds: float | None
    exit_code: int | None
    stdout: str
    stderr: str
    duration_ms: int
    timed_out: bool = False
