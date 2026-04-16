"""Code generator contracts for Lexigram CLI extensions."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


def _json_dumps(data: dict[str, Any], sort_keys: bool = False) -> bytes:
    """Serialize dict to JSON bytes using the stdlib json module."""
    return json.dumps(data, sort_keys=sort_keys).encode("utf-8")


@dataclass(slots=True, frozen=True)
class GenerationResult:
    """Result of a generation operation."""

    files_created: list[Path] = field(default_factory=list)
    files_skipped: list[Path] = field(default_factory=list)
    files_overwritten: list[Path] = field(default_factory=list)


@runtime_checkable
class GeneratorProtocol(Protocol):
    """Protocol for code generators used by CLI extensions."""

    name: str
    description: str

    def generate(self, name: str, **kwargs: Any) -> GenerationResult:
        """Generate files for the given name.

        Args:
            name: The name to generate code for (e.g. module name, provider name).
            **kwargs: Additional generation parameters.

        Returns:
            A ``GenerationResult`` describing which files were created/skipped.
        """
        ...


__all__ = ["GenerationResult", "GeneratorProtocol"]
