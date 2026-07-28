"""Domain events for lexigram-ai-platform skills submodule.

Emitted when skill operations complete. Consumed by audit, analytics,
and skill performance monitoring systems.
"""

from __future__ import annotations

from dataclasses import dataclass

from lexigram.contracts.domain.events import DomainEvent

__all__ = [
    "SkillExecutedEvent",
]


@dataclass(frozen=True, init=False)
class SkillExecutedEvent(DomainEvent):
    """Emitted when a skill execution completes (success or failure).

    Consumed by: audit, analytics, skill performance monitoring.
    """

    skill_name: str
    success: bool
