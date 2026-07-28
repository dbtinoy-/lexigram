"""Frozen view models for lexigram-queue admin widgets."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QueueDepthViewModel:
    """View data for queue depth widget."""

    depth: int
    max_depth: int | None
    queue_name: str


@dataclass(frozen=True)
class ConsumerLagViewModel:
    """View data for consumer lag widget."""

    lag_messages: int
    lag_seconds: float


@dataclass(frozen=True)
class FailedMessagesViewModel:
    """View data for failed messages widget."""

    count: int
    oldest_age_minutes: int | None


__all__ = ["ConsumerLagViewModel", "FailedMessagesViewModel", "QueueDepthViewModel"]
