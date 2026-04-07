"""Unit tests for the RBAC policy module."""

from __future__ import annotations

import pytest

from lexigram_example_platform.domain.membership import Role
from lexigram_example_platform.domain.policy import can_access


class TestOwnerAccess:
    """OWNER role has unrestricted access."""

    def test_owner_can_read_any_resource(self):
        assert can_access(Role.OWNER, "billing", "read") is True

    def test_owner_can_write_any_resource(self):
        assert can_access(Role.OWNER, "users", "write") is True

    def test_owner_can_delete_any_resource(self):
        assert can_access(Role.OWNER, "settings", "delete") is True

    def test_owner_can_access_unknown_resource(self):
        assert can_access(Role.OWNER, "anything", "any_action") is True


class TestAdminAccess:
    """ADMIN has broad but bounded access."""

    def test_admin_can_read_billing(self):
        assert can_access(Role.ADMIN, "billing", "read") is True

    def test_admin_can_manage_users(self):
        assert can_access(Role.ADMIN, "users", "write") is True
        assert can_access(Role.ADMIN, "users", "delete") is True

    def test_admin_can_write_settings(self):
        assert can_access(Role.ADMIN, "settings", "write") is True

    def test_admin_can_delete_reports(self):
        assert can_access(Role.ADMIN, "reports", "delete") is True

    def test_admin_cannot_access_unknown_resource(self):
        assert can_access(Role.ADMIN, "secrets", "read") is False


class TestMemberAccess:
    """MEMBER can read and write core content but not admin surfaces."""

    def test_member_can_read_users(self):
        assert can_access(Role.MEMBER, "users", "read") is True

    def test_member_cannot_write_users(self):
        assert can_access(Role.MEMBER, "users", "write") is False

    def test_member_can_write_reports(self):
        assert can_access(Role.MEMBER, "reports", "write") is True

    def test_member_cannot_read_billing(self):
        assert can_access(Role.MEMBER, "billing", "read") is False

    def test_member_cannot_delete_anything(self):
        assert can_access(Role.MEMBER, "reports", "delete") is False
        assert can_access(Role.MEMBER, "users", "delete") is False


class TestViewerAccess:
    """VIEWER has read-only access to non-privileged surfaces."""

    def test_viewer_can_read_reports(self):
        assert can_access(Role.VIEWER, "reports", "read") is True

    def test_viewer_cannot_write_reports(self):
        assert can_access(Role.VIEWER, "reports", "write") is False

    def test_viewer_cannot_read_billing(self):
        assert can_access(Role.VIEWER, "billing", "read") is False

    def test_viewer_cannot_write_any_resource(self):
        for resource in ["users", "settings", "features", "reports"]:
            assert can_access(Role.VIEWER, resource, "write") is False

    def test_viewer_cannot_delete_anything(self):
        for resource in ["users", "settings", "features", "reports"]:
            assert can_access(Role.VIEWER, resource, "delete") is False


class TestEdgeCases:
    """Boundary and unknown-role checks."""

    def test_can_access_returns_false_for_empty_action(self):
        assert can_access(Role.MEMBER, "reports", "") is False

    def test_can_access_returns_false_for_unknown_resource(self):
        assert can_access(Role.MEMBER, "nuclear_launch", "activate") is False

    def test_privilege_ordering_is_consistent(self):
        """Owner ≥ Admin ≥ Member ≥ Viewer for every tested permission."""
        checks = [
            ("users", "read"),
            ("settings", "read"),
            ("features", "read"),
            ("reports", "read"),
        ]
        for resource, action in checks:
            owner = can_access(Role.OWNER, resource, action)
            admin = can_access(Role.ADMIN, resource, action)
            member = can_access(Role.MEMBER, resource, action)
            viewer = can_access(Role.VIEWER, resource, action)
            # owner >= admin >= member >= viewer for read operations
            assert owner >= admin >= member >= viewer, (
                f"Privilege ordering violated for ({resource!r}, {action!r}): "
                f"owner={owner}, admin={admin}, member={member}, viewer={viewer}"
            )


__all__: list[str] = []
