"""Frozen view models for lexigram-tasks admin widgets."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TasksSummaryViewModel:
    """View data for tasks summary widget."""

    pending: int
    running: int
    completed: int
    failed: int


@dataclass(frozen=True)
class AvgDurationViewModel:
    """View data for average task duration widget."""

    avg_ms: float
    p95_ms: float
    window_minutes: int


__all__ = ["AvgDurationViewModel", "TasksSummaryViewModel"]
