"""Domain events for lexigram-ai-safety governance submodule.

Emitted when governance policy decisions are made. Consumed by audit,
compliance, and cost management systems.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from lexigram.contracts.domain.events import DomainEvent

__all__ = [
    "PolicyEvaluatedEvent",
]


@dataclass(frozen=True, init=False)
class PolicyEvaluatedEvent(DomainEvent):
    """Emitted when a governance policy evaluation completes.

    Consumed by: audit, compliance, cost management.
    """

    policy_id: str
    decision: str
    occurred_at: datetime = field(
        default_factory=lambda: datetime.now(UTC), kw_only=True
    )
