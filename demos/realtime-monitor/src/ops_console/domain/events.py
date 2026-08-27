"""Immutable, broadcast-ready system event."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from lexigram.primitives import clock
from ops_console.domain.severity import Severity


@dataclass(frozen=True)
class SystemEvent:
    """An immutable, broadcast-ready system event.

    Attributes:
        kind: Event type name (e.g. ``deploy``, ``heartbeat``).
        message: Human-readable summary.
        severity: Severity level.
        source: Component that produced the event.
        payload: Optional structured payload.
        occurred_at: UTC timestamp the event happened.
    """

    kind: str
    message: str
    severity: Severity = Severity.INFO
    source: str = "console"
    payload: dict[str, object] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=clock.now)

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-ready representation of the event.

        Returns:
            Flat dictionary with ISO-8601 timestamp.
        """
        return {
            "kind": self.kind,
            "message": self.message,
            "severity": self.severity.value,
            "source": self.source,
            "payload": self.payload,
            "occurred_at": self.occurred_at.isoformat(),
        }
