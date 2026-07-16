"""Unit tests for size-limit enforcement at the feedback submission chokepoints."""

from __future__ import annotations

import pytest

from lexigram.ai.feedback.constants import MAX_CONTEXT_SIZE, MAX_FEEDBACK_TEXT_LENGTH
from lexigram.ai.feedback.exceptions import FeedbackTooLargeError
from lexigram.ai.feedback.processors.processor_registry import (
    FeedbackProcessorRegistry,
)
from lexigram.ai.feedback.services.collector import FeedbackCollector
from lexigram.ai.feedback.types import FeedbackType
from lexigram.serialization import dumps_str


class TestCollectorSizeLimits:
    """MAX_FEEDBACK_TEXT_LENGTH / MAX_CONTEXT_SIZE enforced at _store()."""

    @pytest.fixture
    def collector(self) -> FeedbackCollector:
        return FeedbackCollector()

    @pytest.mark.asyncio
    async def test_text_at_limit_accepted(self, collector: FeedbackCollector) -> None:
        """Text exactly at the limit passes (boundary is inclusive)."""
        await collector.collect_text(text="x" * MAX_FEEDBACK_TEXT_LENGTH)
        assert len(collector) == 1

    @pytest.mark.asyncio
    async def test_text_over_limit_rejected(self, collector: FeedbackCollector) -> None:
        """One char over the limit raises and nothing is stored."""
        with pytest.raises(FeedbackTooLargeError):
            await collector.collect_text(text="x" * (MAX_FEEDBACK_TEXT_LENGTH + 1))
        assert len(collector) == 0

    @pytest.mark.asyncio
    async def test_context_at_limit_accepted(
        self, collector: FeedbackCollector
    ) -> None:
        """Context serializing to exactly MAX_CONTEXT_SIZE chars passes."""
        base = {"key": ""}
        pad = MAX_CONTEXT_SIZE - len(dumps_str(base))
        ctx = {"key": "x" * pad}
        assert len(dumps_str(ctx)) == MAX_CONTEXT_SIZE
        await collector.collect_rating(rating=5, context=ctx)
        assert len(collector) == 1

    @pytest.mark.asyncio
    async def test_context_over_limit_rejected(
        self, collector: FeedbackCollector
    ) -> None:
        """Context serializing to MAX_CONTEXT_SIZE + 1 chars raises."""
        base = {"key": ""}
        pad = MAX_CONTEXT_SIZE - len(dumps_str(base)) + 1
        with pytest.raises(FeedbackTooLargeError):
            await collector.collect_rating(rating=5, context={"key": "x" * pad})
        assert len(collector) == 0

    @pytest.mark.asyncio
    async def test_metadata_over_limit_rejected(
        self, collector: FeedbackCollector
    ) -> None:
        """Oversized metadata raises even with a small value."""
        base = {"m": ""}
        pad = MAX_CONTEXT_SIZE - len(dumps_str(base)) + 1
        with pytest.raises(FeedbackTooLargeError):
            await collector.collect_text(text="ok", metadata={"m": "x" * pad})
        assert len(collector) == 0

    @pytest.mark.asyncio
    async def test_rating_value_not_text_length_checked(
        self, collector: FeedbackCollector
    ) -> None:
        """The text-length rule only applies to str TEXT values, not RATING floats."""
        await collector.collect_rating(
            rating=9999,
            context={"data": "x" * (MAX_FEEDBACK_TEXT_LENGTH + 100)},
        )
        assert len(collector) == 1

    @pytest.mark.asyncio
    async def test_endpoint_pipeline_rejects_oversized_text(self) -> None:
        """The middleware path (registry -> processor -> collector) is covered."""
        registry = FeedbackProcessorRegistry.with_defaults()
        collector = FeedbackCollector()
        with pytest.raises(FeedbackTooLargeError):
            await registry.process(
                FeedbackType.TEXT,
                "x" * (MAX_FEEDBACK_TEXT_LENGTH + 1),
                {"context_id": "c1"},
                collector,
            )
        assert len(collector) == 0
