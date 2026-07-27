from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path


class FormatContractError(ValueError):
    """Raised when a format's contract declaration violates the closed
    vocabulary or demands a pipeline capability the renderer does not
    implement (per-file, during registry load)."""


class ContractLoadError(RuntimeError):
    """Raised when registry load runs in strict mode and any file violates
    the topic/format contract (unknown capability, unimplemented pipeline
    requirement, unresolvable default)."""

    def __init__(self, failures: Iterable[tuple[Path, Exception]]):
        self.failures = list(failures)
        detail = "\n".join(f"- {path}: {exc}" for path, exc in self.failures)
        super().__init__(f"topic/format contract violations during load:\n{detail}")
