"""GuardProtocol result types.

Immutable value objects representing the outcome of a single guard
or an aggregate pipeline evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.contracts.ai.guards import GuardResultProtocol


class GuardAction(StrEnum):
    """Action to take on a guard result."""

    PASS = "pass"
    """Content is safe — allow through."""

    BLOCK = "block"
    """Content is unsafe — reject the request."""

    WARN = "warn"
    """Content is borderline — allow but emit a warning."""

    REDACT = "redact"
    """Content contains sensitive information — redact before allowing."""


@dataclass(frozen=True)
class GuardCheckResult:
    """Result of a single guard evaluation.

    Immutable result produced by one :class:`InputGuardProtocol` or
    :class:`OutputGuardProtocol` check.
    """

    guard_name: str
    """Identifier of the guard that produced this result."""

    passed: bool
    """Whether the guard check passed (action is PASS or WARN)."""

    action: str
    """Action to take: 'pass', 'block', 'warn', or 'redact'."""

    details: dict[str, Any] = field(default_factory=dict)
    """Additional diagnostic details from the guard evaluation."""

    redacted_content: str | None = None
    """Redacted version of the content, if action is 'redact'."""

    @classmethod
    def allow(cls, guard_name: str, **details: Any) -> GuardCheckResult:
        """Create a passing guard result.

        Args:
            guard_name: GuardProtocol identifier.
            **details: Optional extra diagnostics.

        Returns:
            GuardCheckResult with action=PASS.
        """
        return cls(
            guard_name=guard_name,
            passed=True,
            action=GuardAction.PASS,
            details=dict(details),
        )

    @classmethod
    def block(cls, guard_name: str, reason: str, **details: Any) -> GuardCheckResult:
        """Create a blocking guard result.

        Args:
            guard_name: GuardProtocol identifier.
            reason: Human-readable explanation of why the content was blocked.
            **details: Optional extra diagnostics.

        Returns:
            GuardCheckResult with action=BLOCK.
        """
        return cls(
            guard_name=guard_name,
            passed=False,
            action=GuardAction.BLOCK,
            details={"reason": reason, **details},
        )

    @classmethod
    def warn(cls, guard_name: str, reason: str, **details: Any) -> GuardCheckResult:
        """Create a warning guard result.

        Args:
            guard_name: GuardProtocol identifier.
            reason: Human-readable explanation of why a warning was emitted.
            **details: Optional extra diagnostics.

        Returns:
            GuardCheckResult with action=WARN (passed=True).
        """
        return cls(
            guard_name=guard_name,
            passed=True,
            action=GuardAction.WARN,
            details={"reason": reason, **details},
        )

    @classmethod
    def redact(
        cls,
        guard_name: str,
        redacted_content: str,
        reason: str,
        **details: Any,
    ) -> GuardCheckResult:
        """Create a redacting guard result.

        Args:
            guard_name: GuardProtocol identifier.
            redacted_content: The sanitized version of the original content.
            reason: Human-readable explanation of what was redacted.
            **details: Optional extra diagnostics.

        Returns:
            GuardCheckResult with action=REDACT (passed=True).
        """
        return cls(
            guard_name=guard_name,
            passed=True,
            action=GuardAction.REDACT,
            details={"reason": reason, **details},
            redacted_content=redacted_content,
        )


@dataclass(frozen=True)
class AggregateGuardResult:
    """Aggregate result from running multiple guards in a pipeline.

    Combines results from all guards into a single verdict.
    The aggregate action is the most severe action from any guard
    (BLOCK > REDACT > WARN > PASS).
    """

    passed: bool
    """Whether all guards passed (no BLOCK action)."""

    action: str
    """Most severe action from any guard (BLOCK > REDACT > WARN > PASS)."""

    results: list[GuardResultProtocol] = field(default_factory=list)
    """Individual results from each guard, in evaluation order."""

    final_content: str | None = None
    """Content after redaction (may differ from input if any guard redacted)."""

    @property
    def blocked(self) -> bool:
        """Whether any guard triggered a block action."""
        return self.action == GuardAction.BLOCK

    @property
    def redacted(self) -> bool:
        """Whether any guard redacted content."""
        return self.action == GuardAction.REDACT

    @property
    def warned(self) -> bool:
        """Whether any guard emitted a warning."""
        return self.action == GuardAction.WARN

    @property
    def blocking_result(self) -> GuardResultProtocol | None:
        """Return the first blocking result, or None if none blocked."""
        return next((r for r in self.results if r.action == GuardAction.BLOCK), None)

    @classmethod
    def from_results(
        cls,
        results: list[GuardResultProtocol],
        original_content: str,
    ) -> AggregateGuardResult:
        """Build an aggregate result from a list of individual results.

        The aggregate action uses the most severe outcome. If multiple
        guards redacted content, only the last redaction is applied (guards
        should be ordered most-restrictive-first in the pipeline).

        Args:
            results: Individual guard check results.
            original_content: Original input content before any redaction.

        Returns:
            Aggregated result.
        """
        _severity: dict[str, int] = {
            GuardAction.BLOCK: 3,
            GuardAction.REDACT: 2,
            GuardAction.WARN: 1,
            GuardAction.PASS: 0,
        }

        final_action = GuardAction.PASS
        final_content = original_content

        for result in results:
            if _severity.get(result.action, 0) > _severity.get(final_action, 0):
                final_action = GuardAction(result.action)
            if (
                result.action == GuardAction.REDACT
                and result.redacted_content is not None
            ):
                final_content = result.redacted_content

        passed = final_action != GuardAction.BLOCK

        return cls(
            passed=passed,
            action=final_action,
            results=results,
            final_content=final_content if final_action != GuardAction.BLOCK else None,
        )


__all__ = [
    "AggregateGuardResult",
    "GuardAction",
    "GuardCheckResult",
]
