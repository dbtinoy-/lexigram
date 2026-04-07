"""Tests for search analytics recorder."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from lexigram.search.analytics import (
    InMemorySearchAnalyticsRecorder,
    SearchEvent,
)


class TestInMemorySearchAnalyticsRecorder:
    """Tests for InMemorySearchAnalyticsRecorder."""

    @pytest.fixture
    def recorder(self) -> InMemorySearchAnalyticsRecorder:
        """Create a recorder instance."""
        return InMemorySearchAnalyticsRecorder(max_events=100)

    @pytest.mark.asyncio
    async def test_record_search(self, recorder: InMemorySearchAnalyticsRecorder) -> None:
        """Test recording a search event."""
        await recorder.record_search(
            query="python",
            filters={"category": "tech"},
            result_count=10,
            user_id="user123",
            session_id="sess456",
        )

        metrics = await recorder.get_search_metrics()
        assert metrics["total_searches"] == 1
        assert metrics["total_results"] == 10

    @pytest.mark.asyncio
    async def test_get_search_metrics_empty(
        self, recorder: InMemorySearchAnalyticsRecorder
    ) -> None:
        """Test metrics with no events."""
        metrics = await recorder.get_search_metrics()

        assert metrics["total_searches"] == 0
        assert metrics["total_results"] == 0
        assert metrics["unique_queries"] == 0
        assert metrics["unique_users"] == 0

    @pytest.mark.asyncio
    async def test_get_search_metrics_aggregates(
        self, recorder: InMemorySearchAnalyticsRecorder
    ) -> None:
        """Test metric aggregation."""
        await recorder.record_search("python", None, 10, user_id="user1")
        await recorder.record_search("java", None, 5, user_id="user1")
        await recorder.record_search("python", None, 8, user_id="user2")

        metrics = await recorder.get_search_metrics()

        assert metrics["total_searches"] == 3
        assert metrics["total_results"] == 23
        assert metrics["average_results_per_search"] == pytest.approx(23 / 3)
        assert metrics["unique_queries"] == 2
        assert metrics["unique_users"] == 2

    @pytest.mark.asyncio
    async def test_popular_queries(self, recorder: InMemorySearchAnalyticsRecorder) -> None:
        """Test popular queries calculation."""
        await recorder.record_search("python", None, 10)
        await recorder.record_search("python", None, 5)
        await recorder.record_search("java", None, 3)
        await recorder.record_search("rust", None, 2)

        metrics = await recorder.get_search_metrics()

        assert len(metrics["popular_queries"]) == 3
        assert metrics["popular_queries"][0]["query"] == "python"
        assert metrics["popular_queries"][0]["count"] == 2

    @pytest.mark.asyncio
    async def test_get_zero_result_queries(
        self, recorder: InMemorySearchAnalyticsRecorder
    ) -> None:
        """Test zero result query tracking."""
        await recorder.record_search("nonexistent", None, 0)
        await recorder.record_search("another", None, 0)
        await recorder.record_search("found", None, 5)

        zero_results = await recorder.get_zero_result_queries()

        assert len(zero_results) == 2
        # Should be sorted by count descending
        assert zero_results[0]["query"] == "nonexistent"

    @pytest.mark.asyncio
    async def test_time_range_filter(
        self, recorder: InMemorySearchAnalyticsRecorder
    ) -> None:
        """Test time range filtering."""
        # These would normally be created at different times
        # For simplicity, we test the filter logic
        await recorder.record_search("query1", None, 10)

        # Get metrics with 1 hour time range
        metrics = await recorder.get_search_metrics(time_range={"hours": 1})
        assert metrics["total_searches"] == 1

    @pytest.mark.asyncio
    async def test_clear(self, recorder: InMemorySearchAnalyticsRecorder) -> None:
        """Test clearing events."""
        await recorder.record_search("python", None, 10)
        assert len(recorder._events) == 1

        recorder.clear()
        assert len(recorder._events) == 0

    @pytest.mark.asyncio
    async def test_max_events_trimming(
        self,
    ) -> None:
        """Test that old events are trimmed when max is exceeded."""
        recorder = InMemorySearchAnalyticsRecorder(max_events=3)

        await recorder.record_search("q1", None, 1)
        await recorder.record_search("q2", None, 2)
        await recorder.record_search("q3", None, 3)
        await recorder.record_search("q4", None, 4)

        # Should only have the last 3
        assert len(recorder._events) == 3
        queries = [e.query for e in recorder._events]
        assert "q1" not in queries


class TestSearchEvent:
    """Tests for SearchEvent dataclass."""

    def test_search_event_creation(self) -> None:
        """Test creating a search event."""
        event = SearchEvent(
            query="test query",
            filters={"status": "active"},
            result_count=5,
            user_id="user123",
            session_id="sess456",
        )

        assert event.query == "test query"
        assert event.filters == {"status": "active"}
        assert event.result_count == 5
        assert event.user_id == "user123"
        assert event.session_id == "sess456"
        assert event.timestamp is not None
