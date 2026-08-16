"""Tests for audit events."""

from __future__ import annotations

import pytest

from lexigram.audit.events import (
    AuditEntryLoggedEvent,
    AuditPurgeCompletedEvent,
    AuditVerificationCompletedEvent,
)


class TestAuditEntryLoggedEvent:
    """Tests for AuditEntryLoggedEvent."""

    def test_event_creation(self) -> None:
        event = AuditEntryLoggedEvent(
            action="user.login",
            actor_id="user-123",
            severity="high",
        )
        assert event.action == "user.login"
        assert event.actor_id == "user-123"
        assert event.severity == "high"

    def test_event_default_severity(self) -> None:
        event = AuditEntryLoggedEvent(
            action="system.start",
            actor_id="system",
        )
        assert event.severity == "medium"

    def test_event_is_frozen(self) -> None:
        event = AuditEntryLoggedEvent(
            action="test",
            actor_id="actor",
        )
        with pytest.raises(AttributeError):
            event.action = "modified"

    def test_event_has_domain_event_base(self) -> None:
        from lexigram.contracts.domain.events import DomainEvent
        event = AuditEntryLoggedEvent(
            action="test",
            actor_id="actor",
        )
        assert isinstance(event, DomainEvent)


class TestAuditVerificationCompletedEvent:
    """Tests for AuditVerificationCompletedEvent."""

    def test_event_creation(self) -> None:
        event = AuditVerificationCompletedEvent(
            entries_checked=100,
            mismatches_found=0,
        )
        assert event.entries_checked == 100
        assert event.mismatches_found == 0

    def test_event_default_mismatches(self) -> None:
        event = AuditVerificationCompletedEvent(entries_checked=50)
        assert event.mismatches_found == 0

    def test_event_with_mismatches(self) -> None:
        event = AuditVerificationCompletedEvent(
            entries_checked=100,
            mismatches_found=5,
        )
        assert event.mismatches_found == 5

    def test_event_is_frozen(self) -> None:
        event = AuditVerificationCompletedEvent(entries_checked=100)
        with pytest.raises(AttributeError):
            event.entries_checked = 200


class TestAuditPurgeCompletedEvent:
    """Tests for AuditPurgeCompletedEvent."""

    def test_event_creation(self) -> None:
        event = AuditPurgeCompletedEvent(
            entries_purged=50,
            entries_archived=10,
        )
        assert event.entries_purged == 50
        assert event.entries_archived == 10

    def test_event_default_archived(self) -> None:
        event = AuditPurgeCompletedEvent(entries_purged=25)
        assert event.entries_archived == 0

    def test_event_is_frozen(self) -> None:
        event = AuditPurgeCompletedEvent(entries_purged=10)
        with pytest.raises(AttributeError):
            event.entries_purged = 20


class TestEventsModuleExports:
    """Tests for events module exports."""

    def test_all_exports_present(self) -> None:
        from lexigram.audit import events
        expected = [
            "AuditEntryLoggedEvent",
            "AuditPurgeCompletedEvent",
            "AuditVerificationCompletedEvent",
        ]
        for name in expected:
            assert hasattr(events, name)

    def test_all_exports_match(self) -> None:
        from lexigram.audit import events
        expected = [
            "AuditEntryLoggedEvent",
            "AuditPurgeCompletedEvent",
            "AuditVerificationCompletedEvent",
        ]
        assert events.__all__ == expected