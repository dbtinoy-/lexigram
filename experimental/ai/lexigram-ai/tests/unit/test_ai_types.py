"""Tests for AI types."""

import pytest
from datetime import datetime, UTC

from lexigram.ai.types import AIBaseEvent


class TestAIBaseEvent:
    """Tests for AIBaseEvent."""

    def test_event_creation(self) -> None:
        """Test creating an AI base event."""
        event = AIBaseEvent()
        assert event.timestamp is not None
        assert event.metadata == {}

    def test_event_with_metadata(self) -> None:
        """Test creating an event with metadata."""
        event = AIBaseEvent(metadata={"key": "value"})
        assert event.metadata["key"] == "value"

    def test_event_has_timestamp(self) -> None:
        """Test that event has a timestamp."""
        event = AIBaseEvent()
        assert isinstance(event.timestamp, datetime)

    def test_event_serialization(self) -> None:
        """Test event serialization includes timestamp."""
        event = AIBaseEvent(metadata={"test": True})
        # Should serialize without error
        data = event.model_dump()
        assert "timestamp" in data
        assert "metadata" in data

    def test_event_serialization_format(self) -> None:
        """Test event serialization converts datetime to ISO format."""
        event = AIBaseEvent()
        data = event.model_dump(mode="json")
        # Timestamp should be converted to ISO format string
        assert isinstance(data["timestamp"], str)
