"""Advanced tests for FeedbackProcessorRegistry."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.ai.feedback.processors.processor_registry import (
    CorrectionFeedbackProcessor,
    FeedbackProcessorRegistry,
    LabelFeedbackProcessor,
    RatingFeedbackProcessor,
    TextFeedbackProcessor,
)
from lexigram.ai.feedback.types import FeedbackType


class TestFeedbackProcessorRegistryAdvanced:
    """Advanced tests for FeedbackProcessorRegistry."""

    @pytest.fixture
    def registry(self) -> FeedbackProcessorRegistry:
        return FeedbackProcessorRegistry()

    @pytest.fixture
    def mock_collector(self) -> MagicMock:
        collector = MagicMock()
        collector.collect_rating = AsyncMock(return_value="fb_1")
        collector.collect_text = AsyncMock(return_value="fb_2")
        collector.collect_correction = AsyncMock(return_value="fb_3")
        collector.collect_label = AsyncMock(return_value="fb_4")
        return collector

    @pytest.mark.asyncio
    async def test_with_defaults_has_all_processors(self, mock_collector: MagicMock) -> None:
        registry = FeedbackProcessorRegistry.with_defaults()
        fb_id = await registry.process(FeedbackType.RATING, 5.0, {}, mock_collector)
        assert fb_id == "fb_1"

    @pytest.mark.asyncio
    async def test_register_custom_processor(
        self, registry: FeedbackProcessorRegistry, mock_collector: MagicMock,
    ) -> None:
        custom = MagicMock()
        custom.process = AsyncMock(return_value="custom_id")
        registry.register("custom_type", custom)
        fb_id = await registry.process("custom_type", "data", {}, mock_collector)
        assert fb_id == "custom_id"

    @pytest.mark.asyncio
    async def test_process_unknown_type(self, registry: FeedbackProcessorRegistry) -> None:
        with pytest.raises(ValueError, match="No processor for feedback type"):
            await registry.process("unknown", "data", {}, MagicMock())

    @pytest.mark.asyncio
    async def test_rating_processor_delegates(
        self, mock_collector: MagicMock,
    ) -> None:
        processor = RatingFeedbackProcessor()
        await processor.process(5.0, {"source": "test"}, mock_collector)
        mock_collector.collect_rating.assert_called_once_with(rating=5.0, context={"source": "test"})

    @pytest.mark.asyncio
    async def test_text_processor_delegates(self, mock_collector: MagicMock) -> None:
        processor = TextFeedbackProcessor()
        await processor.process("nice!", {}, mock_collector)
        mock_collector.collect_text.assert_called_once_with(text="nice!", context={})

    @pytest.mark.asyncio
    async def test_correction_processor_delegates(self, mock_collector: MagicMock) -> None:
        processor = CorrectionFeedbackProcessor()
        await processor.process({"original": "bad", "corrected": "good"}, {}, mock_collector)
        mock_collector.collect_correction.assert_called_once_with(
            original="bad", corrected="good", context={},
        )

    @pytest.mark.asyncio
    async def test_label_processor_delegates(self, mock_collector: MagicMock) -> None:
        processor = LabelFeedbackProcessor()
        await processor.process({"label": "pos", "input": "text"}, {}, mock_collector)
        mock_collector.collect_label.assert_called_once_with(
            label="pos", input_data="text", context={},
        )
