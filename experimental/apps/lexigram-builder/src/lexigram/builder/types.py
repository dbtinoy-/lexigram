"""Shared value types for the builder."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class DiagnosticSeverity(StrEnum):
    """Severity of a node-scoped diagnostic.

    Only ``ERROR`` blocks generation. ``INFO`` exists so the canvas can
    explain a deliberate no-op -- "you drew modules but the structure is
    minimal, so this grouping is visual only" -- without pretending the
    user did something wrong.
    """

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """A validation diagnostic scoped to a canvas node.

    Attributes:
        node_id: Owning canvas node id, or None for graph-level issues.
        severity: Error or warning.
        code: Stable machine-readable code.
        message: Human-readable description.
        hint: How to fix it, phrased as the remedy the *framework* would
            suggest, so the canvas teaches the same options the runtime
            error teaches.
    """

    node_id: str | None
    severity: DiagnosticSeverity
    code: str
    message: str
    hint: str | None = None
