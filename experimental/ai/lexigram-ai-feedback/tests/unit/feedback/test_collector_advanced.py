"""Advanced tests for FeedbackCollector."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.ai.feedback.services.collector import FeedbackCollector
from lexigram.ai.feedback.types import FeedbackType


class TestFeedbackCollectorAdvanced:
    """Advanced tests for FeedbackCollector."""

    @pytest.fixture
    def collector(self) -> FeedbackCollector:
        return FeedbackCollector()

    @pytest.mark.asyncio
    async def test_collect_rating_returns_id(
        self, collector: FeedbackCollector
    ) -> None:
        fb_id = await collector.collect_rating(
            rating=4.5, owner_id="owner-1", context={"model": "gpt-4"}
        )
        assert isinstance(fb_id, str)
        assert len(fb_id) > 0
        assert len(collector) == 1

    @pytest.mark.asyncio
    async def test_collect_text_returns_id(self, collector: FeedbackCollector) -> None:
        fb_id = await collector.collect_text(
            text="Great!", owner_id="owner-1", context={"input": "hello"}
        )
        assert isinstance(fb_id, str)
        assert len(fb_id) > 0

    @pytest.mark.asyncio
    async def test_collect_correction_returns_id(
        self, collector: FeedbackCollector
    ) -> None:
        fb_id = await collector.collect_correction(
            original="wrong",
            corrected="right",
            owner_id="owner-1",
            context={"id": "1"},
        )
        assert isinstance(fb_id, str)
        assert len(fb_id) > 0

    @pytest.mark.asyncio
    async def test_collect_label_returns_id(self, collector: FeedbackCollector) -> None:
        fb_id = await collector.collect_label(
            label="positive", input_data="good text", owner_id="owner-1"
        )
        assert isinstance(fb_id, str)
        assert len(fb_id) > 0

    def test_len_increases_with_items(self, collector: FeedbackCollector) -> None:
        assert len(collector) == 0

    @pytest.mark.asyncio
    async def test_get_feedback_with_type_filter(
        self, collector: FeedbackCollector
    ) -> None:
        await collector.collect_rating(5.0, owner_id="owner-1")
        await collector.collect_text("text", owner_id="owner-1")
        results = await collector.get_feedback(
            feedback_type=FeedbackType.RATING, owner_id="owner-1"
        )
        assert len(results) == 1
        assert results[0].feedback_type == FeedbackType.RATING

    @pytest.mark.asyncio
    async def test_get_feedback_with_limit(self, collector: FeedbackCollector) -> None:
        for i in range(5):
            await collector.collect_rating(float(i), owner_id="owner-1")
        results = await collector.get_feedback(limit=2, owner_id="owner-1")
        assert len(results) == 2

    def test_clear_resets_memory(self, collector: FeedbackCollector) -> None:
        import asyncio

        asyncio.run(collector.collect_rating(5.0, owner_id="owner-1"))
        assert len(collector) > 0
        collector.clear()
        assert len(collector) == 0

    @pytest.mark.asyncio
    async def test_get_feedback_dict(self, collector: FeedbackCollector) -> None:
        await collector.collect_rating(5.0, owner_id="owner-1")
        dicts = await collector.get_feedback_dict(owner_id="owner-1")
        assert len(dicts) == 1
        assert isinstance(dicts[0], dict)
        assert dicts[0]["type"] == "rating"

    def test_repr(self, collector: FeedbackCollector) -> None:
        assert repr(collector) == "FeedbackCollector(items=0)"

    @pytest.mark.asyncio
    async def test_get_feedback_zero_limit(self, collector: FeedbackCollector) -> None:
        result = await collector.get_feedback(limit=0, owner_id="owner-1")
        assert result == []

    @pytest.mark.asyncio
    async def test_storage_delegates_get_feedback(self) -> None:
        mock_storage = MagicMock()
        mock_storage.find_by_type = AsyncMock(return_value=[])
        mock_storage.save = AsyncMock()

        collector = FeedbackCollector(storage=mock_storage)
        await collector.collect_rating(5.0, owner_id="owner-1")
        results = await collector.get_feedback(owner_id="owner-1")
        assert results is not None


class TestFeedbackCollectorWithStorage:
    """Tests for FeedbackCollector with storage backend."""

    @pytest.fixture
    def mock_storage(self) -> MagicMock:
        storage = MagicMock()
        storage.save = AsyncMock()
        storage.find_by_type = AsyncMock(return_value=[])
        return storage

    @pytest.mark.asyncio
    async def test_save_to_storage(self, mock_storage: MagicMock) -> None:
        collector = FeedbackCollector(storage=mock_storage)
        await collector.collect_rating(5.0, owner_id="owner-1")
        mock_storage.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_feedback_from_storage(self, mock_storage: MagicMock) -> None:
        collector = FeedbackCollector(storage=mock_storage)
        results = await collector.get_feedback(owner_id="owner-1")
        mock_storage.find_by_type.assert_called()
