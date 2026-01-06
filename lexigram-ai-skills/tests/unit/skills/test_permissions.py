"""Tests for PermissionChecker."""

from __future__ import annotations

import pytest

from lexigram.ai.skills.permissions.permission_checker import PermissionChecker


class TestPermissionChecker:
    """Tests for PermissionChecker grant/revoke/check lifecycle."""

    @pytest.fixture
    def checker(self) -> PermissionChecker:
        return PermissionChecker()

    def test_empty_required_always_passes(self, checker) -> None:
        assert checker.check("user1", set()) is True

    def test_check_fails_for_unknown_user(self, checker) -> None:
        assert checker.check("unknown", {"admin"}) is False

    def test_grant_enables_check(self, checker) -> None:
        checker.grant("user1", {"files.read"})
        assert checker.check("user1", {"files.read"}) is True

    def test_check_fails_for_ungranted_permission(self, checker) -> None:
        checker.grant("user1", {"files.read"})
        assert checker.check("user1", {"db.write"}) is False

    def test_check_requires_all_permissions(self, checker) -> None:
        checker.grant("user1", {"a", "b"})
        assert checker.check("user1", {"a", "b"}) is True
        assert checker.check("user1", {"a", "b", "c"}) is False

    def test_revoke_removes_permission(self, checker) -> None:
        checker.grant("user1", {"files.read", "files.write"})
        checker.revoke("user1", {"files.write"})
        assert checker.check("user1", {"files.read"}) is True
        assert checker.check("user1", {"files.write"}) is False

    def test_set_permissions_replaces(self, checker) -> None:
        checker.grant("user1", {"old_perm"})
        checker.set_permissions("user1", {"new_perm"})
        assert checker.check("user1", {"old_perm"}) is False
        assert checker.check("user1", {"new_perm"}) is True

    def test_get_permissions_returns_set(self, checker) -> None:
        checker.grant("user1", {"a", "b"})
        perms = checker.get_permissions("user1")
        assert perms == {"a", "b"}

    def test_get_permissions_empty_for_unknown(self, checker) -> None:
        assert checker.get_permissions("nobody") == set()
