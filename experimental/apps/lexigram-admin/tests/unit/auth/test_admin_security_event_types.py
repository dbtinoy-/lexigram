"""Tests for new AdminSecurityEventType members."""

from __future__ import annotations

from lexigram.admin.auth.types import AdminSecurityEventType


class TestTenantSwitchedEventType:
    def test_tenant_switched_member_exists(self) -> None:
        assert AdminSecurityEventType.TENANT_SWITCHED == "tenant_switched"
