"""Domain events for lexigram-ai-safety guard submodule.

Emitted when guard checks complete. Consumed by safety monitoring,
audit, and security review systems.
"""

from __future__ import annotations

from dataclasses import dataclass

from lexigram.contracts.domain.events import DomainEvent

__all__ = [
    "InputGuardTriggeredEvent",
    "OutputGuardTriggeredEvent",
]


@dataclass(frozen=True, init=False)
class InputGuardTriggeredEvent(DomainEvent):
    """Emitted when an input guard check is triggered (blocked or flagged).

    Consumed by: safety monitoring, audit, security review.
    """

    guard_name: str
    triggered: bool


@dataclass(frozen=True, init=False)
class OutputGuardTriggeredEvent(DomainEvent):
    """Emitted when an output guard check is triggered (blocked or flagged).

    Consumed by: safety monitoring, audit, security review.
    """

    guard_name: str
    triggered: bool
