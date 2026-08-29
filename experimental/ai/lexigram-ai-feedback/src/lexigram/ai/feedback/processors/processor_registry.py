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
        *,
        owner_id: str,
    ) -> str:
        """Process feedback and return feedback ID.

        Args:
            value: Feedback value.
            context: Context dict for the feedback.
            collector: Collector to store the feedback.
            owner_id: Owner scope; the item is recorded under this owner.
        """
        ...


class RatingFeedbackProcessor:
    """Processor for rating feedback."""

    async def process(
        self,
        value: Any,
        context: dict[str, Any],
        collector: FeedbackCollector,
        *,
        owner_id: str,
    ) -> str:
        return await collector.collect_rating(
            rating=value, owner_id=owner_id, context=context
        )


class TextFeedbackProcessor:
    """Processor for text feedback."""

    async def process(
        self,
        value: Any,
        context: dict[str, Any],
        collector: FeedbackCollector,
        *,
        owner_id: str,
    ) -> str:
        return await collector.collect_text(
            text=value, owner_id=owner_id, context=context
        )


class CorrectionFeedbackProcessor:
    """Processor for correction feedback."""

    async def process(
        self,
        value: Any,
        context: dict[str, Any],
        collector: FeedbackCollector,
        *,
        owner_id: str,
    ) -> str:
        return await collector.collect_correction(
            original=value["original"],
            corrected=value["corrected"],
            owner_id=owner_id,
            context=context,
        )


class LabelFeedbackProcessor:
    """Processor for label feedback."""

    async def process(
        self,
        value: Any,
        context: dict[str, Any],
        collector: FeedbackCollector,
        *,
        owner_id: str,
    ) -> str:
        return await collector.collect_label(
            label=value["label"],
            input_data=value["input"],
            owner_id=owner_id,
            context=context,
        )


class FeedbackProcessorRegistry:
    """Central registry for feedback processors."""

    def __init__(self) -> None:
        self._processors: dict[str, FeedbackProcessor] = {}

    @classmethod
    def _default_entries(cls) -> dict[str, FeedbackProcessor]:
        """Declare the built-in feedback processors."""
        from lexigram.ai.feedback.types import FeedbackType

        return {
            FeedbackType.RATING: RatingFeedbackProcessor(),
            FeedbackType.TEXT: TextFeedbackProcessor(),
            FeedbackType.CORRECTION: CorrectionFeedbackProcessor(),
            FeedbackType.LABEL: LabelFeedbackProcessor(),
        }

    @classmethod
    def with_defaults(cls) -> FeedbackProcessorRegistry:
        """Create a registry pre-populated with the built-in feedback processors."""
        registry = cls()
        registry._processors = dict(cls._default_entries())
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
        *,
        owner_id: str,
    ) -> str:
        """Process feedback using the appropriate processor.

        Args:
            fb_type: Feedback type key.
            value: Feedback value.
            context: Context dict for the feedback.
            collector: Collector to store the feedback.
            owner_id: Owner scope; the item is recorded under this owner.
        """
        processor = self._processors.get(fb_type)
        if not processor:
            raise ValueError(f"No processor for feedback type: {fb_type}")
        return await processor.process(value, context, collector, owner_id=owner_id)
