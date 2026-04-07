"""Tests for feedback types."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from lexigram.ai.feedback.types import FeedbackItem, FeedbackType


class TestFeedbackType:
    """Tests for FeedbackType enum."""

    @pytest.mark.parametrize(
        "expected_value,expected_name",
        [
            ("rating", "RATING"),
            ("text", "TEXT"),
            ("correction", "CORRECTION"),
            ("label", "LABEL"),
        ],
    )
    def test_feedback_type_values(self, expected_value: str, expected_name: str) -> None:
        """Verify FeedbackType enum values match expected strings."""
        feedback_type = FeedbackType[expected_name]
        assert feedback_type.value == expected_value

    def test_feedback_type_is_str_enum(self) -> None:
        """Verify FeedbackType is a StrEnum and can be compared to strings."""
        assert FeedbackType.RATING == "rating"
        assert FeedbackType.TEXT == "text"
        assert FeedbackType.CORRECTION == "correction"
        assert FeedbackType.LABEL == "label"

    def test_feedback_type_members(self) -> None:
        """Verify all expected members exist."""
        members = list(FeedbackType)
        assert len(members) == 4
        assert FeedbackType.RATING in members
        assert FeedbackType.TEXT in members
        assert FeedbackType.CORRECTION in members
        assert FeedbackType.LABEL in members


class TestFeedbackItem:
    """Tests for FeedbackItem dataclass."""

    def test_feedback_item_creation(self) -> None:
        """Verify FeedbackItem can be created with required fields."""
        item = FeedbackItem(
            feedback_type=FeedbackType.RATING,
            value=4.5,
        )
        assert item.feedback_type == FeedbackType.RATING
        assert item.value == 4.5

    def test_feedback_item_default_context_and_metadata(self) -> None:
        """Verify default context and metadata are empty dicts."""
        item = FeedbackItem(feedback_type=FeedbackType.TEXT, value="Great response!")
        assert item.context == {}
        assert item.metadata == {}

    def test_feedback_item_custom_context_and_metadata(self) -> None:
        """Verify custom context and metadata are stored."""
        context = {"session_id": "sess-123", "model": "gpt-4"}
        metadata = {"source": "api"}
        item = FeedbackItem(
            feedback_type=FeedbackType.LABEL,
            value="helpful",
            context=context,
            metadata=metadata,
        )
        assert item.context == context
        assert item.metadata == metadata

    def test_feedback_item_default_id(self) -> None:
        """Verify default ID is a valid UUID string."""
        item = FeedbackItem(feedback_type=FeedbackType.TEXT, value="test")
        uuid_obj = UUID(item.id)
        assert str(uuid_obj) == item.id

    def test_feedback_item_default_created_at(self) -> None:
        """Verify default created_at is a datetime with UTC timezone."""
        item = FeedbackItem(feedback_type=FeedbackType.TEXT, value="test")
        assert item.created_at.tzinfo is not None
        assert item.created_at.tzinfo == UTC

    def test_feedback_item_type_property(self) -> None:
        """Verify type property returns feedback_type."""
        item = FeedbackItem(feedback_type=FeedbackType.RATING, value=5.0)
        assert item.type == item.feedback_type
        assert item.type == FeedbackType.RATING

    def test_feedback_item_to_dict(self) -> None:
        """Verify to_dict returns expected dictionary structure."""
        known_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)
        item = FeedbackItem(
            feedback_type=FeedbackType.RATING,
            value=4.0,
            context={"session_id": "abc"},
            metadata={"prompt": "test"},
            id="test-id-123",
            created_at=known_time,
        )
        result = item.to_dict()
        assert result["id"] == "test-id-123"
        assert result["type"] == "rating"
        assert result["value"] == 4.0
        assert result["context"] == {"session_id": "abc"}
        assert result["metadata"] == {"prompt": "test"}
        assert result["created_at"] == "2024-01-15T10:30:00+00:00"

    def test_feedback_item_to_dict_isoformat(self) -> None:
        """Verify to_dict produces valid ISO format timestamp."""
        item = FeedbackItem(feedback_type=FeedbackType.TEXT, value="test")
        result = item.to_dict()
        parsed = datetime.fromisoformat(result["created_at"])
        assert parsed.tzinfo is not None

    def test_feedback_item_repr(self) -> None:
        """Verify repr contains id, type, and value."""
        item = FeedbackItem(
            feedback_type=FeedbackType.CORRECTION,
            value="fixed response",
            id="repr-id-456",
        )
        repr_str = repr(item)
        assert "repr-id-456" in repr_str
        assert "correction" in repr_str
        assert "fixed response" in repr_str

    def test_feedback_item_all_types(self) -> None:
        """Verify FeedbackItem works with all FeedbackType values."""
        for fb_type in FeedbackType:
            item = FeedbackItem(feedback_type=fb_type, value="test")
            assert item.feedback_type == fb_type


class TestFeedbackSummary:
    """Tests for FeedbackSummary dataclass."""

    def test_feedback_summary_defaults(self) -> None:
        """Verify default values."""
        from lexigram.contracts.ai.feedback import FeedbackSummary

        summary = FeedbackSummary()
        assert summary.total_count == 0
        assert summary.average_rating is None
        assert summary.count_by_type == {}

    def test_feedback_summary_custom_values(self) -> None:
        """Verify custom values are stored."""
        from lexigram.contracts.ai.feedback import FeedbackSummary

        summary = FeedbackSummary(
            total_count=100,
            average_rating=4.2,
            count_by_type={"rating": 50, "text": 50},
        )
        assert summary.total_count == 100
        assert summary.average_rating == 4.2
        assert summary.count_by_type == {"rating": 50, "text": 50}

    def test_feedback_summary_can_be_dataclass(self) -> None:
        """Verify FeedbackSummary is a dataclass with expected fields."""
        from lexigram.contracts.ai.feedback import FeedbackSummary

        summary = FeedbackSummary(total_count=10, average_rating=3.5)
        data = asdict(summary)
        assert "total_count" in data
        assert "average_rating" in data
        assert "count_by_type" in data