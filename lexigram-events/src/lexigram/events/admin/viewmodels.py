"""Frozen view models for lexigram-events admin widgets."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EventsThroughputViewModel:
    """View data for events throughput widget.

    Immutable data carrier for rendering the throughput metric.
    """

    events_per_second: float
    total_events: int
    window_minutes: int


@dataclass(frozen=True)
class DeadLetterCountViewModel:
    """View data for dead letter queue count widget.

    Immutable data carrier for rendering dead letter statistics.
    """

    count: int
    oldest_age_minutes: int | None


__all__ = ["DeadLetterCountViewModel", "EventsThroughputViewModel"]
