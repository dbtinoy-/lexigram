"""Search analytics module."""

from __future__ import annotations

from lexigram.search.analytics.recorder import (
    InMemorySearchAnalyticsRecorder,
    SearchAnalyticsRecorder,
    SearchEvent,
)

__all__ = [
    "InMemorySearchAnalyticsRecorder",
    "SearchAnalyticsRecorder",
    "SearchEvent",
]
