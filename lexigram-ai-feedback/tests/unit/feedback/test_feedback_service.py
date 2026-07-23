"""Unit tests for FeedbackService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.ai.feedback.services.feedback_service import FeedbackService
from lexigram.contracts.ai.feedback import FeedbackItem, FeedbackSummary, FeedbackType
from lexigram.result import Err, Ok


class TestFeedbackService:
    """Tests for FeedbackService."""

    @pytest.fixture
    def mock_store(self) -> MagicMock:
        """Mock FeedbackStoreProtocol."""
        store = MagicMock()
        store.save = AsyncMock(return_value=Ok("feedback-id"))
        summary = FeedbackSummary(
            total_count=10,
            average_rating=4.2,
            count_by_type={"rating": 10},
        )
        store.aggregate = AsyncMock(return_value=summary)
        return store

    @pytest.fixture
    def service(self, mock_store: MagicMock) -> FeedbackService:
        """FeedbackService with mocked store."""
        return FeedbackService(store=mock_store)

    @pytest.fixture
    def service_no_store(self) -> FeedbackService:
        """FeedbackService with no store (degraded mode)."""
        return FeedbackService()

    # ------------------------------------------------------------------
    # submit_feedback
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_submit_feedback_stores_item(
        self, service: FeedbackService, mock_store: MagicMock
    ) -> None:
        """submit_feedback calls store.save exactly once."""
        await service.submit_feedback(trace_id="trace-123", score=0.9, owner_id="owner-1")
        mock_store.save.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_submit_feedback_stores_rating_type(
        self, service: FeedbackService, mock_store: MagicMock
    ) -> None:
        """Stored item has RATING feedback type."""
        await service.submit_feedback(trace_id="trace-abc", score=0.75, owner_id="owner-1")
        item: FeedbackItem = mock_store.save.call_args[0][0]
        assert item.feedback_type == FeedbackType.RATING

    @pytest.mark.asyncio
    async def test_submit_feedback_stores_score_as_value(
        self, service: FeedbackService, mock_store: MagicMock
    ) -> None:
        """Stored item carries the supplied score as value."""
        await service.submit_feedback(trace_id="trace-abc", score=0.5, owner_id="owner-1")
        item: FeedbackItem = mock_store.save.call_args[0][0]
        assert item.value == 0.5

    @pytest.mark.asyncio
    async def test_submit_feedback_stores_trace_id_in_context(
        self, service: FeedbackService, mock_store: MagicMock
    ) -> None:
        """Stored item carries trace_id inside context."""
        await service.submit_feedback(trace_id="trace-xyz", score=1.0, owner_id="owner-1")
        item: FeedbackItem = mock_store.save.call_args[0][0]
        assert item.context["trace_id"] == "trace-xyz"

    @pytest.mark.asyncio
    async def test_submit_feedback_with_comment(
        self, service: FeedbackService, mock_store: MagicMock
    ) -> None:
        """Comment is stored under metadata['comment']."""
        await service.submit_feedback(
            trace_id="trace-123", score=0.8, comment="Great!", owner_id="owner-1"
        )
        item: FeedbackItem = mock_store.save.call_args[0][0]
        assert item.metadata.get("comment") == "Great!"

    @pytest.mark.asyncio
    async def test_submit_feedback_merges_extra_metadata(
        self, service: FeedbackService, mock_store: MagicMock
    ) -> None:
        """Extra metadata keys are preserved alongside comment."""
        await service.submit_feedback(
            trace_id="t1",
            score=0.6,
            comment="ok",
            metadata={"session": "s1"},
            owner_id="owner-1",
        )
        item: FeedbackItem = mock_store.save.call_args[0][0]
        assert item.metadata["session"] == "s1"
        assert item.metadata["comment"] == "ok"

    @pytest.mark.asyncio
    async def test_submit_feedback_no_comment_no_metadata_key(
        self, service: FeedbackService, mock_store: MagicMock
    ) -> None:
        """When no comment supplied, 'comment' key is absent from metadata."""
        await service.submit_feedback(trace_id="t1", score=0.5, owner_id="owner-1")
        item: FeedbackItem = mock_store.save.call_args[0][0]
        assert "comment" not in item.metadata

    @pytest.mark.asyncio
    async def test_submit_feedback_store_error_does_not_raise(
        self, service: FeedbackService, mock_store: MagicMock
    ) -> None:
        """When store.save returns Err, submit_feedback completes without raising."""
        mock_store.save = AsyncMock(return_value=Err(Exception("db down")))
        # Should not raise
        await service.submit_feedback(trace_id="t1", score=0.5, owner_id="owner-1")

    @pytest.mark.asyncio
    async def test_submit_feedback_no_store_is_noop(
        self, service_no_store: FeedbackService
    ) -> None:
        """Without a store, submit_feedback completes silently."""
        await service_no_store.submit_feedback(trace_id="t1", score=0.9, owner_id="owner-1")

    # ------------------------------------------------------------------
    # get_feedback_stats
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_feedback_stats_returns_required_keys(
        self, service: FeedbackService
    ) -> None:
        """Result dict always contains total_count, average_rating, by_type."""
        stats = await service.get_feedback_stats(owner_id="owner-1")
        assert "total_count" in stats
        assert "average_rating" in stats
        assert "by_type" in stats

    @pytest.mark.asyncio
    async def test_get_feedback_stats_values_from_summary(
        self, service: FeedbackService
    ) -> None:
        """Stats values match the FeedbackSummary returned by the store."""
        stats = await service.get_feedback_stats(owner_id="owner-1")
        assert stats["total_count"] == 10
        assert stats["average_rating"] == pytest.approx(4.2)
        assert stats["by_type"] == {"rating": 10}

    @pytest.mark.asyncio
    async def test_get_feedback_stats_passes_model_key(
        self, service: FeedbackService
    ) -> None:
        """When model is supplied it appears in the result."""
        stats = await service.get_feedback_stats(model="gpt-4", owner_id="owner-1")
        assert stats["model"] == "gpt-4"

    @pytest.mark.asyncio
    async def test_get_feedback_stats_passes_provider_key(
        self, service: FeedbackService
    ) -> None:
        """When provider is supplied it appears in the result."""
        stats = await service.get_feedback_stats(provider="openai", owner_id="owner-1")
        assert stats["provider"] == "openai"

    @pytest.mark.asyncio
    async def test_get_feedback_stats_no_model_key_absent(
        self, service: FeedbackService
    ) -> None:
        """When model is not supplied, 'model' key is absent."""
        stats = await service.get_feedback_stats(owner_id="owner-1")
        assert "model" not in stats

    @pytest.mark.asyncio
    async def test_get_feedback_stats_no_store_returns_empty(
        self, service_no_store: FeedbackService
    ) -> None:
        """Without a store, stats returns zeroed-out dict."""
        stats = await service_no_store.get_feedback_stats(owner_id="owner-1")
        assert stats["total_count"] == 0
        assert stats["average_rating"] is None
        assert stats["by_type"] == {}
