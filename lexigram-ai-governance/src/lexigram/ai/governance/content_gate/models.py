"""Content policy gate domain models.

Frozen value objects for :class:`PolicyRequest` and :class:`PolicyDecision`,
plus the :class:`PolicyOutcome` enum.  These cross package boundaries and
therefore use ``@dataclass(frozen=True)``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class PolicyOutcome(StrEnum):
    """Result of a content policy gate evaluation.

    * ``ALLOW``    — request is permitted.
    * ``DENY``     — request is blocked; the caller must not proceed.
    * ``THROTTLE`` — allow now but record; future requests may be denied.
    """

    ALLOW = "allow"
    DENY = "deny"
    THROTTLE = "throttle"


@dataclass(frozen=True)
class PolicyRequest:
    """Context passed to a :class:`~protocol.ContentPolicyGateProtocol`.

    Attributes:
        principal_id: Identifies the caller (user-id, session token, etc.).
            ``None`` for fully anonymous requests.
        content_type: Application-defined label for what is being submitted
            (e.g. ``"image"``, ``"text"``, ``"document"``).
        content_metadata: Free-form key/value pairs describing the content
            (e.g. ``{"species": "cat", "mime_type": "image/jpeg"}``).
        history_summary: Aggregated counters from prior requests by this
            principal (e.g. ``{"non_pet_images": 3}``).  ``None`` when no
            history is available.
    """

    principal_id: str | None
    content_type: str
    content_metadata: dict[str, str] = field(default_factory=dict)
    history_summary: dict[str, int] | None = None


@dataclass(frozen=True)
class PolicyDecision:
    """Result produced by a :class:`~protocol.ContentPolicyGateProtocol`.

    Decisions are *values*, not exceptions — even a ``DENY`` is returned
    normally.  The caller decides what to do.

    Attributes:
        outcome: One of ``ALLOW``, ``DENY``, or ``THROTTLE``.
        reason: Human-readable explanation (shown in logs / returned to the
            app; may be empty for ``ALLOW``).
        metadata: Additional context produced by the gate
            (e.g. ``{"threshold": "5", "current_count": "6"}``).
    """

    outcome: PolicyOutcome
    reason: str
    metadata: dict[str, str] = field(default_factory=dict)


__all__ = [
    "PolicyDecision",
    "PolicyOutcome",
    "PolicyRequest",
]
