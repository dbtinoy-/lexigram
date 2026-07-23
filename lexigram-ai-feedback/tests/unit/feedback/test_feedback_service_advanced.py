"""Advanced tests for FeedbackService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.ai.feedback.services.feedback_service import FeedbackService
from lexigram.result import Err, Ok


class TestFeedbackServiceAdvanced:
    """Advanced tests for FeedbackService."""

    @pytest.fixture
    def mock_store(self) -> MagicMock:
        store = MagicMock()
        store.save = AsyncMock(return_value=Ok("saved"))
        return store

    @pytest.mark.asyncio
    async def test_submit_feedback_calls_store(self, mock_store: MagicMock) -> None:
        service = FeedbackService(store=mock_store)
        await service.submit_feedback(trace_id="trace-1", score=4.5, comment="good", owner_id="owner-1")
        mock_store.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_submit_feedback_with_comment_in_metadata(self, mock_store: MagicMock) -> None:
        service = FeedbackService(store=mock_store)
        await service.submit_feedback(trace_id="trace-1", score=3.0, comment="ok", owner_id="owner-1")
        call_kwargs = mock_store.save.call_args[0][0]
        assert call_kwargs.metadata.get("comment") == "ok"

    @pytest.mark.asyncio
    async def test_submit_feedback_store_error(self, mock_store: MagicMock) -> None:
        mock_store.save = AsyncMock(return_value=Err(ValueError("db error")))
        service = FeedbackService(store=mock_store)
        await service.submit_feedback(trace_id="trace-1", score=4.0, owner_id="owner-1")

    @pytest.mark.asyncio
    async def test_submit_feedback_no_store(self) -> None:
        service = FeedbackService()
        await service.submit_feedback(trace_id="trace-1", score=4.0, owner_id="owner-1")

    @pytest.mark.asyncio
    async def test_get_stats_no_store(self) -> None:
        service = FeedbackService()
        stats = await service.get_feedback_stats(owner_id="owner-1")
        assert stats["total_count"] == 0
        assert stats["average_rating"] is None
        assert stats["by_type"] == {}

    @pytest.mark.asyncio
    async def test_get_stats_with_store(self, mock_store: MagicMock) -> None:
        mock_store.aggregate = AsyncMock(
            return_value=MagicMock(
                total_count=10,
                average_rating=4.2,
                count_by_type={"rating": 10},
            ),
        )
        service = FeedbackService(store=mock_store)
        stats = await service.get_feedback_stats(model="gpt-4", provider="openai", owner_id="owner-1")
        assert stats["total_count"] == 10
        assert stats["average_rating"] == 4.2
        assert stats["model"] == "gpt-4"
        assert stats["provider"] == "openai"

    @pytest.mark.asyncio
    async def test_get_stats_with_store_no_model(self, mock_store: MagicMock) -> None:
        mock_store.aggregate = AsyncMock(
            return_value=MagicMock(
                total_count=5,
                average_rating=3.5,
                count_by_type={"rating": 5},
            ),
        )
        service = FeedbackService(store=mock_store)
        stats = await service.get_feedback_stats(owner_id="owner-1")
        assert "model" not in stats
        assert "provider" not in stats
