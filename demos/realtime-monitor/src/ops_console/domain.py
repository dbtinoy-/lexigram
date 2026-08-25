"""Value types for the realtime monitor demo.

The demo broadcasts immutable :class:`SystemEvent` records over two realtime
primitives: server-sent events (SSE, one way, server to browsers) and a
WebSocket operator channel (bidirectional, for operators pushing events back
into the console).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from lexigram.primitives import clock


class Severity(str, Enum):
    """Severity level of a system event.

    Members compare equal to their string value so they serialize cleanly
    and work in ``isinstance(value, str)`` checks.
    """

    INFO = "info"
    WARN = "warn"
    CRITICAL = "critical"

    @classmethod
    def from_name(cls, name: str) -> Severity:
        """Resolve a severity from its string member value.

        Args:
            name: One of ``info | warn | critical`` (case-sensitive).

        Returns:
            The matching member; ``INFO`` for unknown names so a malformed
            external payload can never abort the broadcast path.
        """
        try:
            return cls(name)
        except ValueError:
            return cls.INFO


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
