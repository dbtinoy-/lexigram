"""Conflict signalling for optimistic concurrency on settings writes.

Comparing a submitted revision token in the controller and then issuing an
unconditional write leaves a time-of-check/time-of-use window: two sessions
can both read the same revision, both pass the comparison, and both write,
with the later write silently discarding the earlier one.

Closing that window requires the check to be re-evaluated inside the same
transaction as the write. :class:`SettingsConflictError` is the signal a
store raises when that in-transaction re-check fails, so the surrounding
transaction rolls back and the caller can re-render the conflict UI.
"""

from __future__ import annotations

__all__ = ["SettingsConflictError"]


class SettingsConflictError(RuntimeError):
    """Raised when settings changed between rendering a form and saving it.

    Attributes:
        namespace: The configuration namespace that failed to save, when known.
    """

    def __init__(
        self,
        message: str = "Settings changed since the form was rendered.",
        *,
        namespace: str | None = None,
    ) -> None:
        super().__init__(message)
        self.namespace = namespace
