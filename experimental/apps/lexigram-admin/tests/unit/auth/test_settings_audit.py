"""Tests for settings audit event and permission gating."""

from __future__ import annotations

from lexigram.admin.auth.types import AdminSecurityEventType


class TestSettingsAuditEvent:
    """Tests for the settings audit event type."""

    def test_settings_updated_event_type_exists(self) -> None:
        assert AdminSecurityEventType.SETTINGS_UPDATED == "settings_updated"

    def test_permission_denied_event_type_exists(self) -> None:
        assert AdminSecurityEventType.PERMISSION_DENIED == "permission_denied"
