"""Unit tests for FeedbackProcessorRegistry edge cases."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from lexigram.ai.feedback.processors.processor_registry import (
    FeedbackProcessorRegistry,
)
from lexigram.ai.feedback.services.collector import FeedbackCollector
from lexigram.ai.feedback.types import FeedbackType


class TestProcessorRegistryEdgeCases:
    """Edge case tests for FeedbackProcessorRegistry."""

    def test_unknown_feedback_type_returns_none(self) -> None:
        """Unknown feedback type returns None from get."""
        registry = FeedbackProcessorRegistry()
        processor = registry._processors.get("unknown_type")
        assert processor is None

    def test_processor_registration_conflict(self) -> None:
        """Duplicate registration overwrites existing processor without raising."""
        registry = FeedbackProcessorRegistry()
        processor1 = MagicMock()
        processor2 = MagicMock()
        
        registry.register("custom_type", processor1)
        assert registry._processors["custom_type"] is processor1
        
        registry.register("custom_type", processor2)
        assert registry._processors["custom_type"] is processor2

    @pytest.mark.asyncio
    async def test_processor_not_found_raises(self) -> None:
        """Processing unknown feedback type raises ValueError."""
        registry = FeedbackProcessorRegistry()
        collector = FeedbackCollector()
        
        with pytest.raises(ValueError, match="No processor for feedback type"):
            await registry.process(
                FeedbackType.RATING,
                5,
                {},
                collector,
            )

    @pytest.mark.asyncio
    async def test_empty_registry_process_raises(self) -> None:
        """Empty registry raises when processing any type."""
        registry = FeedbackProcessorRegistry()
        collector = FeedbackCollector()
        
        with pytest.raises(ValueError, match="No processor for feedback type"):
            await registry.process("any_type", "value", {}, collector)

    @pytest.mark.asyncio
    async def test_process_with_non_enum_type(self) -> None:
        """Registry handles string feedback types not in FeedbackType enum."""
        from unittest.mock import AsyncMock
        
        registry = FeedbackProcessorRegistry()
        custom_processor = AsyncMock()
        custom_processor.process = AsyncMock(return_value="custom-id")
        
        registry.register("custom_feedback", custom_processor)
        
        result = await registry.process(
            "custom_feedback",
            "value",
            {"ctx": "test"},
            collector=FeedbackCollector(),
        )
        
        assert result == "custom-id"
        custom_processor.process.assert_called_once()
