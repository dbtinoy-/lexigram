"""Shared boot-failure classification for admin contributors.

Admin contributors commonly depend on optional package services.  Dependency
errors are intentionally formatted as multi-line developer messages by the
framework, so callers must not put ``str(exc)`` directly into a structured log
field.  This module keeps that policy in the contracts package so every
contributor can apply it without depending on ``lexigram-admin``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from lexigram.contracts.exceptions.container import UnresolvableDependencyError

_DEFAULT_MAX_SUMMARY_LENGTH = 240


@dataclass(frozen=True, slots=True)
class ContributorBootFailureSummary:
    """Safe classification and summary of a contributor boot failure.

    ``summary`` is a dependency name for an expected missing-dependency
    failure, or a bounded one-line exception message for an unexpected fault.
    The original exception is deliberately not retained here; genuine-fault
    callers should pass it to their logger with ``exc_info=True``.
    """

    expected: bool
    reason: str
    summary: str


def _one_line(value: Any, *, max_length: int) -> str:
    """Collapse whitespace and bound a value for one structured log field."""
    text = " ".join(str(value).split())
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    if max_length == 1:
        return "…"
    return f"{text[: max_length - 1].rstrip()}…"


def summarize_contributor_boot_failure(
    exc: BaseException,
    *,
    max_length: int = _DEFAULT_MAX_SUMMARY_LENGTH,
) -> ContributorBootFailureSummary:
    """Classify a contributor boot exception and produce a safe summary.

    ``UnresolvableDependencyError`` and its subclasses are expected when an
    optional package is installed without its backing service.  The resolver
    stores the dependency name in ``details`` when it knows it; no formatted
    exception text is used as a fallback because that text includes the
    framework error code, hint, and documentation URL on separate lines.

    All other exceptions are genuine boot faults.  Their summary is still
    normalized to one line and bounded for structured logging, while callers
    retain the original exception for a traceback.

    Args:
        exc: Exception raised while resolving or booting a contributor.
        max_length: Maximum length of the returned summary.

    Returns:
        A frozen, safe-to-log failure summary.
    """
    limit = max(1, max_length)
    if isinstance(exc, UnresolvableDependencyError):
        details = getattr(exc, "details", None)
        dependency = details.get("dependency") if isinstance(details, Mapping) else None
        missing = _one_line(dependency, max_length=limit) if dependency else ""
        return ContributorBootFailureSummary(
            expected=True,
            reason="required service not registered",
            summary=missing or "unspecified dependency",
        )

    summary = _one_line(exc, max_length=limit) or type(exc).__name__
    return ContributorBootFailureSummary(
        expected=False,
        reason="contributor boot hook failed",
        summary=summary,
    )


__all__ = [
    "ContributorBootFailureSummary",
    "summarize_contributor_boot_failure",
]
