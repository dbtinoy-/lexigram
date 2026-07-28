"""Unit tests for session events."""

from __future__ import annotations

import pytest
from datetime import datetime


class TestSessionCreatedEvent:
    """Test SessionCreatedEvent domain event."""

    def test_event_creation(self) -> None:
        """Verify SessionCreatedEvent can be created."""
        from lexigram.ai.session.events import SessionCreatedEvent

        event = SessionCreatedEvent(
            session_id="sess-123",
            user_id="user-456",
        )
        assert event.session_id == "sess-123"
        assert event.user_id == "user-456"

    def test_event_has_occurred_at(self) -> None:
        """Verify event has occurred_at timestamp."""
        from lexigram.ai.session.events import SessionCreatedEvent

        event = SessionCreatedEvent(
            session_id="sess-123",
            user_id=None,
        )
        assert event.occurred_at is not None
        assert isinstance(event.occurred_at, datetime)

    def test_event_is_domain_event(self) -> None:
        """Verify event inherits from DomainEvent."""
        from lexigram.ai.session.events import SessionCreatedEvent
        from lexigram.contracts.domain.events import DomainEvent

        assert issubclass(SessionCreatedEvent, DomainEvent)


class TestSessionClosedEvent:
    """Test SessionClosedEvent domain event."""

    def test_event_creation(self) -> None:
        """Verify SessionClosedEvent can be created."""
        from lexigram.ai.session.events import SessionClosedEvent

        event = SessionClosedEvent(
            session_id="sess-123",
            duration_seconds=3600.5,
        )
        assert event.session_id == "sess-123"
        assert event.duration_seconds == 3600.5

    def test_event_has_occurred_at(self) -> None:
        """Verify event has occurred_at timestamp."""
        from lexigram.ai.session.events import SessionClosedEvent

        event = SessionClosedEvent(
            session_id="sess-123",
            duration_seconds=0.0,
        )
        assert event.occurred_at is not None
        assert isinstance(event.occurred_at, datetime)

    def test_event_is_domain_event(self) -> None:
        """Verify event inherits from DomainEvent."""
        from lexigram.ai.session.events import SessionClosedEvent
        from lexigram.contracts.domain.events import DomainEvent

        assert issubclass(SessionClosedEvent, DomainEvent)


class TestSessionEventsExports:
    """Test that events are properly exported."""

    def test_events_exported(self) -> None:
        """Verify events are in __all__."""
        from lexigram.ai.session import events

        assert "SessionCreatedEvent" in events.__all__
        assert "SessionClosedEvent" in events.__all__