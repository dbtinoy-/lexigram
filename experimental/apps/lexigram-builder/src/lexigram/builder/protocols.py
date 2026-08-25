"""Package-local seams for process execution (scoped by import-linter)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

__all__ = ["RunOutcome", "ServerSpawner", "SpawnedServer", "SubprocessRunner"]


@dataclass(frozen=True, slots=True)
class RunOutcome:
    """Result of one subprocess invocation."""

    command: tuple[str, ...]
    returncode: int
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        """True when the process exited zero without timeout."""
        return self.returncode == 0 and not self.timed_out

    def tail(self, limit: int = 2000) -> str:
        """Trailing slice of stderr for error reporting."""
        return (self.stderr or "")[-limit:]


@runtime_checkable
class SubprocessRunner(Protocol):
    """Runs a command to completion, capturing output."""

    async def run(
        self,
        command: list[str],
        *,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> RunOutcome: ...


@runtime_checkable
class SpawnedServer(Protocol):
    """A spawned preview server process."""

    @property
    def pid(self) -> int: ...

    def terminate(self) -> None: ...

    def is_running(self) -> bool: ...


@runtime_checkable
class ServerSpawner(Protocol):
    """Starts a long-running preview server."""

    async def start(
        self,
        command: list[str],
        *,
        cwd: Path,
    ) -> SpawnedServer: ...
