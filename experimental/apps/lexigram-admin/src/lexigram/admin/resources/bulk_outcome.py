"""Per-row outcome accounting for bulk operations (roadmap R14).

Replaces the bare success counter in the wired bulk endpoint so every
selected id ends as either a success or a failure with a reason — and the
toast the user sees reflects reality ("Deleted 47 of 50 item(s) — 3
failed: …") instead of an all-or-nothing summary.
Design: docs/09-01-2026/09-bulk-ux.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = ["BulkOutcome"]

#: Max failure details embedded in a toast; the rest is "and N more".
_MAX_DETAILS = 3
#: Max id length shown in a toast (full ids go to the structured log).
_MAX_ID_CHARS = 8


@dataclass
class BulkOutcome:
    """Aggregated result of one bulk operation over a selection.

    Attributes:
        verb: Past-tense operation label ("Deleted", "Purged", "Restored").
        total: Number of selected ids the operation attempted.
        succeeded: Rows that completed successfully.
        failures: ``(item_id, reason)`` pairs for rows that did not.
    """

    verb: str
    total: int
    succeeded: int = 0
    failures: list[tuple[str, str]] = field(default_factory=list)

    # -- accounting ----------------------------------------------------------

    def record_success(self) -> None:
        """Count one successfully processed row."""
        self.succeeded += 1

    def record_failure(self, item_id: str, reason: str) -> None:
        """Count one failed row with a short user-facing reason."""
        self.failures.append((str(item_id), reason))

    @property
    def failed(self) -> int:
        """Number of rows that failed."""
        return len(self.failures)

    @property
    def all_ok(self) -> bool:
        """True when every attempted row succeeded."""
        return self.failed == 0

    # -- presentation --------------------------------------------------------

    @staticmethod
    def _short_id(item_id: str) -> str:
        # IDs come from user data and may contain non-ASCII; the message is
        # embedded in an HTTP header (latin-1), so replace anything unsafe.
        safe = str(item_id).encode("ascii", "replace").decode("ascii")
        if len(safe) <= _MAX_ID_CHARS:
            return safe
        return safe[:_MAX_ID_CHARS] + "..."

    def message(self, max_details: int = _MAX_DETAILS) -> str:
        """Build the user-facing summary message.

        All-success output is byte-identical to the pre-R14 messages
        ("Deleted 3 item(s)") so the happy path never churns. The string is
        deliberately ASCII-only: it travels in the ``HX-Trigger`` response
        header, and HTTP headers are latin-1 (non-ASCII raises at encode).
        """
        if self.all_ok:
            return f"{self.verb} {self.succeeded} item(s)"
        details = ", ".join(
            f"{self._short_id(item_id)} ({reason})"
            for item_id, reason in self.failures[:max_details]
        )
        more = self.failed - min(self.failed, max_details)
        if more > 0:
            details += f" and {more} more"
        return (
            f"{self.verb} {self.succeeded} of {self.total} item(s) - "
            f"{self.failed} failed: {details}"
        )

    def toast_type(self) -> str:
        """Toast severity: success, warning (partial) or error (none)."""
        if self.all_ok:
            return "success"
        if self.succeeded > 0:
            return "warning"
        return "error"

    def log_fields(self) -> dict[str, object]:
        """Structured-log payload with the full (untruncated) failure list."""
        return {
            "verb": self.verb,
            "total": self.total,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "failures": [
                {"id": item_id, "reason": reason}
                for item_id, reason in self.failures
            ],
        }
