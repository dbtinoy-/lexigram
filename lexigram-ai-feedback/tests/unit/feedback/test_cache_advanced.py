"""Advanced tests for CachedFeedbackStore."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.ai.feedback.storage.cache import CachedFeedbackStore
from lexigram.ai.feedback.types import FeedbackItem, FeedbackType
from lexigram.result import Ok


class TestCachedFeedbackStoreAdvanced:
    """Advanced tests for CachedFeedbackStore."""

    @pytest.fixture
    def mock_store(self) -> MagicMock:
        store = MagicMock()
        store.save = AsyncMock(return_value=Ok("saved"))
        store.find_by_session = AsyncMock(return_value=[])
        store.find_by_type = AsyncMock(return_value=[])
        store.aggregate = AsyncMock(return_value=MagicMock())
        return store

    @pytest.fixture
    def mock_cache(self) -> MagicMock:
        cache = MagicMock()
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock()
        cache.delete = AsyncMock()
        return cache

    @pytest.fixture
    def cached_store(self, mock_store: MagicMock, mock_cache: MagicMock) -> CachedFeedbackStore:
        return CachedFeedbackStore(mock_store, mock_cache)

    @pytest.mark.asyncio
    async def test_save_delegates_and_invalidates(
        self, cached_store: CachedFeedbackStore, mock_store: MagicMock, mock_cache: MagicMock,
    ) -> None:
        feedback = FeedbackItem(
            feedback_type=FeedbackType.RATING,
            value=5.0,
            context={"session_id": "session-1"},
        )
        result = await cached_store.save(feedback)
        assert result.is_ok()
        mock_store.save.assert_called_once_with(feedback)
        mock_cache.delete.assert_any_call("feedback:session:session-1")
        mock_cache.delete.assert_any_call("feedback:type:rating")

    @pytest.mark.asyncio
    async def test_save_without_session(
        self, cached_store: CachedFeedbackStore, mock_cache: MagicMock,
    ) -> None:
        feedback = FeedbackItem(
            feedback_type=FeedbackType.TEXT,
            value="hello",
        )
        await cached_store.save(feedback)
        assert mock_cache.delete.call_count == 1

    @pytest.mark.asyncio
    async def test_find_by_session_cache_hit(
        self, mock_store: MagicMock, mock_cache: MagicMock,
    ) -> None:
        cached = [FeedbackItem(feedback_type=FeedbackType.RATING, value=1.0)]
        mock_cache.get = AsyncMock(return_value=cached)

        store = CachedFeedbackStore(mock_store, mock_cache)
        items = await store.find_by_session("session-1")
        assert len(items) == 1
        mock_store.find_by_session.assert_not_called()

    @pytest.mark.asyncio
    async def test_find_by_session_cache_miss(
        self, cached_store: CachedFeedbackStore, mock_store: MagicMock, mock_cache: MagicMock,
    ) -> None:
        items = await cached_store.find_by_session("session-1")
        mock_store.find_by_session.assert_called_once_with("session-1")
        mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_by_type_cache_hit(
        self, mock_store: MagicMock, mock_cache: MagicMock,
    ) -> None:
        cached = [FeedbackItem(feedback_type=FeedbackType.RATING, value=1.0)]
        mock_cache.get = AsyncMock(return_value=cached)

        store = CachedFeedbackStore(mock_store, mock_cache)
        items = await store.find_by_type(FeedbackType.RATING, limit=10)
        assert len(items) == 1
        mock_store.find_by_type.assert_not_called()

    @pytest.mark.asyncio
    async def test_find_by_type_cache_miss(
        self, cached_store: CachedFeedbackStore, mock_store: MagicMock, mock_cache: MagicMock,
    ) -> None:
        items = await cached_store.find_by_type(FeedbackType.RATING, limit=10)
        mock_store.find_by_type.assert_called_once_with(FeedbackType.RATING, limit=10)
        mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_aggregate_delegates_to_store(
        self, cached_store: CachedFeedbackStore, mock_store: MagicMock,
    ) -> None:
        await cached_store.aggregate(window_hours=48)
        mock_store.aggregate.assert_called_once_with(window_hours=48)
