"""Shared value types for the builder."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class DiagnosticSeverity(StrEnum):
    """Severity of a node-scoped diagnostic."""

    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """A validation diagnostic scoped to a canvas node.

    Attributes:
        node_id: Owning canvas node id, or None for graph-level issues.
        severity: Error or warning.
        code: Stable machine-readable code.
        message: Human-readable description.
    """

    node_id: str | None
    severity: DiagnosticSeverity
    code: str
    message: str
