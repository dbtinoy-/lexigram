"""Feedback processor registry for extensible feedback handling."""

from __future__ import annotations

from typing import Any, Protocol

from lexigram.ai.feedback.services.collector import FeedbackCollector


class FeedbackProcessor(Protocol):
    """Protocol for feedback processors."""

    async def process(
        self,
        value: Any,
        context: dict[str, Any],
        collector: FeedbackCollector,
    ) -> str:
        """Process feedback and return feedback ID."""
        ...


class RatingFeedbackProcessor:
    """Processor for rating feedback."""

    async def process(
        self,
        value: Any,
        context: dict[str, Any],
        collector: FeedbackCollector,
    ) -> str:
        return await collector.collect_rating(rating=value, context=context)


class TextFeedbackProcessor:
    """Processor for text feedback."""

    async def process(
        self,
        value: Any,
        context: dict[str, Any],
        collector: FeedbackCollector,
    ) -> str:
        return await collector.collect_text(text=value, context=context)


class CorrectionFeedbackProcessor:
    """Processor for correction feedback."""

    async def process(
        self,
        value: Any,
        context: dict[str, Any],
        collector: FeedbackCollector,
    ) -> str:
        return await collector.collect_correction(
            original=value["original"],
            corrected=value["corrected"],
            context=context,
        )


class LabelFeedbackProcessor:
    """Processor for label feedback."""

    async def process(
        self,
        value: Any,
        context: dict[str, Any],
        collector: FeedbackCollector,
    ) -> str:
        return await collector.collect_label(
            label=value["label"],
            input_data=value["input"],
            context=context,
        )


class FeedbackProcessorRegistry:
    """Central registry for feedback processors."""

    def __init__(self) -> None:
        self._processors: dict[str, FeedbackProcessor] = {}

    @classmethod
    def with_defaults(cls) -> FeedbackProcessorRegistry:
        """Create a registry pre-populated with the built-in feedback processors."""
        from lexigram.ai.feedback.types import FeedbackType

        registry = cls()
        registry._processors[FeedbackType.RATING] = RatingFeedbackProcessor()
        registry._processors[FeedbackType.TEXT] = TextFeedbackProcessor()
        registry._processors[FeedbackType.CORRECTION] = CorrectionFeedbackProcessor()
        registry._processors[FeedbackType.LABEL] = LabelFeedbackProcessor()
        return registry

    def register(self, fb_type: str, processor: FeedbackProcessor) -> None:
        """Register a new feedback processor."""
        self._processors[fb_type] = processor

    async def process(
        self,
        fb_type: str,
        value: Any,
        context: dict[str, Any],
        collector: FeedbackCollector,
    ) -> str:
        """Process feedback using the appropriate processor."""
        processor = self._processors.get(fb_type)
        if not processor:
            raise ValueError(f"No processor for feedback type: {fb_type}")
        return await processor.process(value, context, collector)
