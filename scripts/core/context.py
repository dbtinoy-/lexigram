from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ScriptContext:
    """Resolved workspace state for script execution."""

    root: Path
    packages: tuple[str, ...] = ()


def resolve_workspace_root(start: Path | str) -> Path:
    """Resolve the Lexigram workspace root from a starting path."""

    current = Path(start).resolve()
    if current.is_file():
        current = current.parent

    for candidate in reversed((current, *current.parents)):
        if (candidate / "pyproject.toml").is_file():
            return candidate

    raise FileNotFoundError(
        f"Could not find a workspace root containing pyproject.toml from {current}"
    )
