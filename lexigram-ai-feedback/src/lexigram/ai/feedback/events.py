"""Domain events for lexigram-ai-safety feedback submodule.

Emitted when feedback operations complete. Consumed by quality tracking,
model improvement, and audit systems.
"""

from __future__ import annotations

from dataclasses import dataclass

from lexigram.contracts.domain.events import DomainEvent

__all__ = [
    "FeedbackSubmittedEvent",
]


@dataclass(frozen=True, init=False)
class FeedbackSubmittedEvent(DomainEvent):
    """Emitted when user feedback is submitted and persisted.

    Consumed by: quality tracking, model improvement, audit.
    """

    feedback_id: str
    item_type: str
