"""Tests for inbox notification contracts used by admin."""

from __future__ import annotations

from datetime import UTC, datetime

from lexigram.contracts.notification.inbox import InboxMessage


class TestInboxMessage:
    """Tests for InboxMessage contract model."""

    def test_create_sets_fields(self) -> None:
        """InboxMessage.create populates user_id, title, and body."""
        m = InboxMessage.create(user_id="u1", title="Hello", body="World")
        assert m.user_id == "u1"
        assert m.title == "Hello"
        assert m.body == "World"

    def test_create_generates_unique_ids(self) -> None:
        """Each InboxMessage.create call produces a distinct id."""
        m1 = InboxMessage.create(user_id="u1", title="T", body="B")
        m2 = InboxMessage.create(user_id="u1", title="T", body="B")
        assert m1.id != m2.id

    def test_not_read_by_default(self) -> None:
        """Messages are unread at creation time."""
        m = InboxMessage.create(user_id="u1", title="T", body="B")
        assert not m.read

    def test_metadata_defaults_to_empty(self) -> None:
        """Metadata is an empty dict when not supplied."""
        m = InboxMessage.create(user_id="u1", title="T", body="B")
        assert m.metadata == {}

    def test_metadata_roundtrips(self) -> None:
        """Arbitrary key-value pairs supplied as metadata are preserved."""
        m = InboxMessage.create(
            user_id="u1",
            title="T",
            body="B",
            metadata={"level": "error", "action_url": "/admin/users/1"},
        )
        assert m.metadata["level"] == "error"
        assert m.metadata["action_url"] == "/admin/users/1"

    def test_created_at_is_utc(self) -> None:
        """created_at is timezone-aware and in UTC."""
        m = InboxMessage.create(user_id="u1", title="T", body="B")
        assert m.created_at.tzinfo is not None
        assert m.created_at <= datetime.now(UTC)
