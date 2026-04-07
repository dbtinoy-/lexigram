from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

# Re-export shared types from contracts — the canonical definitions.
from lexigram.contracts.ai.governance import AIAuditEvent, AuditEventType  # noqa: F401

if TYPE_CHECKING:
    from datetime import datetime

# ---------------------------------------------------------------------------
# Query / aggregation models (governance-specific, not in contracts)
# ---------------------------------------------------------------------------


@dataclass
class AuditQuery:
    """Filter criteria for querying audit events.

    All fields are optional — ``None`` means *no constraint* on that axis.

    Attributes:
        start: Inclusive lower bound on timestamp.
        end: Inclusive upper bound on timestamp.
        event_types: Restrict to these event types.
        user_id: Restrict to a specific user.
        model: Restrict to a specific model.
        provider: Restrict to a specific provider.
        status: Restrict to a specific status string.
        limit: Maximum number of results to return.
        offset: Number of results to skip (for pagination).
    """

    start: datetime | None = None
    end: datetime | None = None
    event_types: list[AuditEventType] | None = None
    user_id: str | None = None
    model: str | None = None
    provider: str | None = None
    status: str | None = None
    limit: int = 1000
    offset: int = 0


@dataclass
class AuditSummary:
    """Aggregated audit statistics for a given query period.

    Attributes:
        total_events: Total number of events matching the query.
        total_spend: Sum of ``cost`` across matching events.
        total_tokens: Sum of ``tokens`` across matching events.
        denied_count: Events where status is ``"denied"``.
        by_model: Event count per model.
        by_user: Event count per user.
        by_event_type: Event count per event type.
    """

    total_events: int = 0
    total_spend: float = 0.0
    total_tokens: int = 0
    denied_count: int = 0
    by_model: dict[str, int] = field(default_factory=dict)
    by_user: dict[str, int] = field(default_factory=dict)
    by_event_type: dict[str, int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Persistence protocol
# ---------------------------------------------------------------------------
