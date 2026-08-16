"""Search analytics recorder implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from lexigram.logging import get_logger
from lexigram.primitives import clock as ambient_clock

logger = get_logger(__name__)


@dataclass
class SearchEvent:
    """A recorded search event."""

    query: str
    filters: dict[str, Any] | None
    result_count: int
    user_id: str | None
    session_id: str | None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class InMemorySearchAnalyticsRecorder:
    """In-memory search analytics recorder.

    Stores search events in memory for testing and development.
    Production use should implement this protocol with a persistent store.

    Example::

        recorder = InMemorySearchAnalyticsRecorder()
        await recorder.record_search("python", None, 10, user_id="user123")
        metrics = await recorder.get_search_metrics()
    """

    def __init__(self, max_events: int = 10000) -> None:
        """Initialize the analytics recorder.

        Args:
            max_events: Maximum number of events to store in memory.
        """
        self._events: list[SearchEvent] = []
        self._max_events = max_events

    async def record_search(
        self,
        query: str,
        filters: dict[str, Any] | None,
        result_count: int,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> None:
        """Record a search query for analytics.

        Args:
            query: Search query string.
            filters: Applied filters.
            result_count: Number of results returned.
            user_id: User identifier (optional).
            session_id: Session identifier (optional).
        """
        event = SearchEvent(
            query=query,
            filters=filters,
            result_count=result_count,
            user_id=user_id,
            session_id=session_id,
        )
        self._events.append(event)

        # Trim old events if we exceed max
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events :]

        logger.debug(
            "search_recorded",
            query=query,
            result_count=result_count,
            user_id=user_id,
        )

    async def get_search_metrics(
        self,
        time_range: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Get search analytics metrics.

        Args:
            time_range: Time range for metrics (optional). Format:
                {"hours": 24} or {"days": 7} or {"start": "2024-01-01", "end": "2024-01-31"}

        Returns:
            Search metrics data including query counts, popular queries, etc.
        """
        events = self._filter_by_time_range(time_range) if time_range else self._events

        if not events:
            return {
                "total_searches": 0,
                "total_results": 0,
                "average_results_per_search": 0,
                "unique_queries": 0,
                "unique_users": 0,
                "popular_queries": [],
            }

        # Calculate metrics
        total_searches = len(events)
        total_results = sum(e.result_count for e in events)
        average_results = total_results / total_searches if total_searches > 0 else 0

        # Unique counts
        unique_queries = len({e.query for e in events})
        unique_users = len({e.user_id for e in events if e.user_id})

        # Popular queries (top 10)
        query_counts: dict[str, int] = {}
        for event in events:
            query_counts[event.query] = query_counts.get(event.query, 0) + 1

        popular_queries = sorted(
            [{"query": q, "count": c} for q, c in query_counts.items()],
            key=lambda x: x["count"],  # type: ignore[arg-type,return-value]
            reverse=True,
        )[:10]

        return {
            "total_searches": total_searches,
            "total_results": total_results,
            "average_results_per_search": average_results,
            "unique_queries": unique_queries,
            "unique_users": unique_users,
            "popular_queries": popular_queries,
        }

    async def get_zero_result_queries(
        self,
        time_range: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Get queries that returned zero results.

        Args:
            time_range: Time range for metrics (optional).

        Returns:
            List of zero-result queries with counts.
        """
        events = self._filter_by_time_range(time_range) if time_range else self._events

        zero_result_events = [e for e in events if e.result_count == 0]

        # Group by query
        query_counts: dict[str, int] = {}
        for event in zero_result_events:
            query_counts[event.query] = query_counts.get(event.query, 0) + 1

        return sorted(
            [{"query": q, "count": c} for q, c in query_counts.items()],
            key=lambda x: x["count"],
            reverse=True,
        )

    def _filter_by_time_range(
        self,
        time_range: dict[str, Any],
    ) -> list[SearchEvent]:
        """Filter events by time range.

        Args:
            time_range: Time range specification.

        Returns:
            Filtered list of events.
        """
        now = ambient_clock.now()
        start_time: datetime | None = None

        if "hours" in time_range:
            start_time = now - timedelta(hours=time_range["hours"])
        elif "days" in time_range:
            start_time = now - timedelta(days=time_range["days"])
        elif "start" in time_range:
            start_time = datetime.fromisoformat(time_range["start"])

        if start_time:
            return [e for e in self._events if e.timestamp >= start_time]

        return self._events

    def clear(self) -> None:
        """Clear all recorded events."""
        self._events.clear()
        logger.info("search_analytics_cleared")


# For backwards compatibility, alias the main class
SearchAnalyticsRecorder = InMemorySearchAnalyticsRecorder


__all__ = [
    "InMemorySearchAnalyticsRecorder",
    "SearchAnalyticsRecorder",
    "SearchEvent",
]
