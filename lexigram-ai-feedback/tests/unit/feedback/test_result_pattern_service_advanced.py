"""Advanced tests for FeedbackSystemWithResultPattern."""

from __future__ import annotations

import pytest

from lexigram.ai.feedback.services.result_pattern_service import FeedbackSystemWithResultPattern
from lexigram.contracts.ai.exceptions import AIError


class TestFeedbackSystemWithResultPatternAdvanced:
    """Advanced tests for FeedbackSystemWithResultPattern."""

    @pytest.fixture
    def service(self) -> FeedbackSystemWithResultPattern:
        return FeedbackSystemWithResultPattern()

    @pytest.mark.asyncio
    async def test_record_feedback_valid(self, service: FeedbackSystemWithResultPattern) -> None:
        result = await service.record_feedback("interaction-1", 4.5, "Great!")
        assert result.is_ok()
        assert result.unwrap() == "feedback:interaction-1"

    @pytest.mark.asyncio
    async def test_record_feedback_empty_id(self, service: FeedbackSystemWithResultPattern) -> None:
        result = await service.record_feedback("", 4.0)
        assert result.is_err()
        assert isinstance(result.unwrap_err(), AIError)
        assert "empty" in str(result.unwrap_err()).lower()

    @pytest.mark.asyncio
    async def test_record_feedback_negative_rating(self, service: FeedbackSystemWithResultPattern) -> None:
        result = await service.record_feedback("id-1", -1.0)
        assert result.is_err()

    @pytest.mark.asyncio
    async def test_record_feedback_rating_too_high(self, service: FeedbackSystemWithResultPattern) -> None:
        result = await service.record_feedback("id-1", 6.0)
        assert result.is_err()

    @pytest.mark.asyncio
    async def test_record_feedback_boundary_zero(self, service: FeedbackSystemWithResultPattern) -> None:
        result = await service.record_feedback("id-1", 0.0)
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_record_feedback_boundary_five(self, service: FeedbackSystemWithResultPattern) -> None:
        result = await service.record_feedback("id-1", 5.0)
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_get_feedback_empty_id(self, service: FeedbackSystemWithResultPattern) -> None:
        result = await service.get_feedback("")
        assert result.is_err()

    @pytest.mark.asyncio
    async def test_get_feedback_valid(self, service: FeedbackSystemWithResultPattern) -> None:
        result = await service.get_feedback("interaction-1")
        assert result.is_ok()
        assert result.unwrap() == []
