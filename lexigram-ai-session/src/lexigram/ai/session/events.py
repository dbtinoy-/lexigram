"""Domain events for lexigram-ai-platform session submodule.

Emitted when session lifecycle operations occur. Consumed by audit,
analytics, and session management systems.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from lexigram.contracts.domain.events import DomainEvent

__all__ = [
    "SessionClosedEvent",
    "SessionCreatedEvent",
]


@dataclass(frozen=True, init=False)
class SessionCreatedEvent(DomainEvent):
    """Emitted when a new AI session is created.

    Consumed by: audit, analytics, billing.
    """

    session_id: str = field(kw_only=True)
    user_id: str | None = field(kw_only=True)


@dataclass(frozen=True, init=False)
class SessionClosedEvent(DomainEvent):
    """Emitted when an AI session is closed or expires.

    Consumed by: audit, analytics, resource cleanup.
    """

    session_id: str = field(kw_only=True)
    duration_seconds: float = field(kw_only=True)
