"""Tests for Result pattern in feedback system."""

import pytest
from lexigram.contracts.ai.exceptions import AIError
from lexigram.ai.feedback.services.result_pattern_service import FeedbackSystemWithResultPattern

class TestFeedbackSystemResultPattern:
    """Test Result pattern in feedback system."""

    @pytest.fixture
    def feedback_system(self) -> FeedbackSystemWithResultPattern:
        """Create feedback system."""
        return FeedbackSystemWithResultPattern()

    @pytest.mark.asyncio
    async def test_record_feedback_returns_ok(self, feedback_system):
        """Verify record_feedback returns Ok."""
        result = await feedback_system.record_feedback("session123", 4.5, "Great response!")
        assert result.is_ok()
        feedback_id = result.unwrap()
        assert isinstance(feedback_id, str)

    @pytest.mark.asyncio
    async def test_record_feedback_returns_err_for_invalid_rating(self, feedback_system):
        """Verify record_feedback returns Err for invalid rating."""
        result = await feedback_system.record_feedback("session123", 6.0, "Great!")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), AIError)

    @pytest.mark.asyncio
    async def test_get_feedback_returns_ok(self, feedback_system):
        """Verify get_feedback returns Ok."""
        result = await feedback_system.get_feedback("session123")
        assert result.is_ok()
        feedback_list = result.unwrap()
        assert isinstance(feedback_list, list)
