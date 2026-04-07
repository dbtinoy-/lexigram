"""Tests for AI Feedback types."""

import pytest

from lexigram.ai.feedback.types import FeedbackItem, FeedbackType


class TestFeedbackType:
    """Tests for FeedbackType enum."""

    def test_feedback_type_rating_value(self) -> None:
        """Test rating type value."""
        assert FeedbackType.RATING.value == "rating"

    def test_feedback_type_text_value(self) -> None:
        """Test text type value."""
        assert FeedbackType.TEXT.value == "text"

    def test_feedback_type_correction_value(self) -> None:
        """Test correction type value."""
        assert FeedbackType.CORRECTION.value == "correction"

    def test_feedback_type_label_value(self) -> None:
        """Test label type value."""
        assert FeedbackType.LABEL.value == "label"


class TestFeedbackItem:
    """Tests for FeedbackItem class."""

    def test_feedback_item_creation_with_rating(self) -> None:
        """Test creating feedback item with rating."""
        item = FeedbackItem(feedback_type=FeedbackType.RATING, value=4.5)
        assert item.type == FeedbackType.RATING
        assert item.value == 4.5
        assert item.context == {}
        assert item.metadata == {}

    def test_feedback_item_creation_with_text(self) -> None:
        """Test creating feedback item with text."""
        item = FeedbackItem(feedback_type=FeedbackType.TEXT, value="Great response!")
        assert item.type == FeedbackType.TEXT
        assert item.value == "Great response!"

    def test_feedback_item_creation_with_context(self) -> None:
        """Test creating feedback item with context."""
        context = {"input": "test", "output": "result"}
        item = FeedbackItem(
            feedback_type=FeedbackType.RATING, value=5.0, context=context
        )
        assert item.context == context

    def test_feedback_item_creation_with_metadata(self) -> None:
        """Test creating feedback item with metadata."""
        metadata = {"user_id": "user123", "session_id": "sess456"}
        item = FeedbackItem(
            feedback_type=FeedbackType.LABEL,
            value="helpful",
            metadata=metadata,
        )
        assert item.metadata == metadata

    def test_feedback_item_creation_with_custom_id(self) -> None:
        """Test creating feedback item with custom ID."""
        custom_id = "feedback-123"
        item = FeedbackItem(
            feedback_type=FeedbackType.TEXT,
            value="test",
            id=custom_id,
        )
        assert item.id == custom_id

    def test_feedback_item_generates_uuid(self) -> None:
        """Test that feedback item generates UUID if not provided."""
        item = FeedbackItem(feedback_type=FeedbackType.TEXT, value="test")
        # UUID format: 8-4-4-4-12 hex digits
        assert len(item.id) == 36
        assert item.id.count("-") == 4

    def test_feedback_item_has_created_at(self) -> None:
        """Test that feedback item has created_at timestamp."""
        item = FeedbackItem(feedback_type=FeedbackType.TEXT, value="test")
        assert item.created_at is not None

    def test_feedback_item_to_dict(self) -> None:
        """Test converting feedback item to dictionary."""
        item = FeedbackItem(
            feedback_type=FeedbackType.RATING,
            value=4.0,
            context={"input": "test"},
            metadata={"user": "user1"},
        )
        result = item.to_dict()
        assert isinstance(result, dict)
        assert result["type"] == "rating"
        assert result["value"] == 4.0
        assert result["context"] == {"input": "test"}
        assert result["metadata"] == {"user": "user1"}
        assert "id" in result
        assert "created_at" in result

    def test_feedback_item_repr(self) -> None:
        """Test feedback item string representation."""
        item = FeedbackItem(feedback_type=FeedbackType.RATING, value=4.5)
        repr_str = repr(item)
        assert "FeedbackItem" in repr_str
        assert "rating" in repr_str
        assert "4.5" in repr_str


class TestTypesAllExports:
    """Tests for __all__ exports."""

    def test_all_contains_expected_types(self) -> None:
        """Test that __all__ contains all expected types."""
        from lexigram.ai.feedback import types

        expected = ["FeedbackItem", "FeedbackType"]
        for item in expected:
            assert item in types.__all__
