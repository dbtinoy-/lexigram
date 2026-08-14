"""Tests for admin realtime types."""

from datetime import datetime, timezone

import pytest

from lexigram.admin.realtime.sse import AdminEvent, AdminEventType


class TestAdminEventType:
    """Tests for AdminEventType enum."""

    def test_resource_events(self) -> None:
        """Test resource event types."""
        assert AdminEventType.RESOURCE_CREATED.value == "resource.created"
        assert AdminEventType.RESOURCE_UPDATED.value == "resource.updated"
        assert AdminEventType.RESOURCE_DELETED.value == "resource.deleted"

    def test_bulk_operation_events(self) -> None:
        """Test bulk operation event types."""
        assert AdminEventType.BULK_PROGRESS.value == "bulk.progress"
        assert AdminEventType.BULK_COMPLETED.value == "bulk.completed"
        assert AdminEventType.BULK_FAILED.value == "bulk.failed"

    def test_notification_events(self) -> None:
        """Test notification event types."""
        assert AdminEventType.NOTIFICATION.value == "notification"
        assert AdminEventType.TOAST.value == "toast"

    def test_system_events(self) -> None:
        """Test system event types."""
        assert AdminEventType.HEARTBEAT.value == "heartbeat"
        assert AdminEventType.RECONNECT.value == "reconnect"

    def test_admin_event_type_members(self) -> None:
        """Test AdminEventType has expected members."""
        members = list(AdminEventType)
        assert len(members) == 10


class TestAdminEvent:
    """Tests for AdminEvent dataclass."""

    def test_admin_event_creation(self) -> None:
        """Test creating AdminEvent."""
        event = AdminEvent(
            event_type=AdminEventType.RESOURCE_CREATED,
            data={"id": "123", "name": "Test"},
        )
        assert event.event_type == AdminEventType.RESOURCE_CREATED
        assert event.data == {"id": "123", "name": "Test"}
        assert event.id is None
        assert event.resource_type is None

    def test_admin_event_with_optional(self) -> None:
        """Test AdminEvent with optional fields."""
        event = AdminEvent(
            event_type=AdminEventType.RESOURCE_UPDATED,
            data={"name": "Updated"},
            id="evt-123",
            resource_type="user",
            resource_id="user-456",
        )
        assert event.id == "evt-123"
        assert event.resource_type == "user"
        assert event.resource_id == "user-456"

    def test_admin_event_to_dict(self) -> None:
        """Test AdminEvent to_dict method."""
        event = AdminEvent(
            event_type=AdminEventType.BULK_PROGRESS,
            data={"progress": 50, "total": 100},
        )
        result = event.to_dict()
        assert "event" in result
        assert "data" in result
        assert "id" in result
