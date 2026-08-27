"""Severity level of a system event."""

from __future__ import annotations

from enum import Enum


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
