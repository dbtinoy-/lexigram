"""Tests for configured super-admin role recognition (setup-wizard account).

The setup wizard grants the first account ``AdminRbacConfig.super_admin_role``
(default ``"superadmin"``), but the permission engines only bypass for
``is_superuser`` / ``admin`` / ``superuser``.  These tests cover the fix:

- ``AdminAuthMiddleware._mark_super_admin`` flags holders of the configured
  role as ``is_superuser`` right after the user is loaded.
- ``AdminAuthorizationMiddleware`` grants full resource capabilities to
  superusers and holders of the configured role.
"""

from __future__ import annotations

import pytest
from starlette.requests import Request

from lexigram.admin.auth.user import AdminUserRecord
from lexigram.admin.middleware.auth import AdminAuthMiddleware
from lexigram.admin.middleware.authorization import AdminAuthorizationMiddleware


def _user(roles: list[str]) -> AdminUserRecord:
    return AdminUserRecord(
        user_id="u-1",
        email="root@example.com",
        name="Root",
        roles=roles,
    )


def _request(path: str = "/admin/products") -> Request:
    scope: dict = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": [(b"host", b"localhost")],
        "state": {},
        "query_string": b"",
        "scheme": "http",
        "server": ("localhost", 80),
    }
    return Request(scope)  # type: ignore[arg-type]


class _DenyAllPermissions:
    """Resource permission service that denies every capability."""

    async def can_view(self, user: object, resource: str) -> bool:
        return False

    async def can_create(self, user: object, resource: str) -> bool:
        return False

    async def can_update(self, user: object, resource: str) -> bool:
        return False

    async def can_delete(self, user: object, resource: str) -> bool:
        return False


class TestMarkSuperAdmin:
    def test_marks_configured_role_holder(self) -> None:
        mw = AdminAuthMiddleware(app=None, super_admin_role="superadmin")
        user = _user(["superadmin"])

        mw._mark_super_admin(user)

        assert getattr(user, "is_superuser", False) is True

    def test_custom_role_name_is_honored(self) -> None:
        mw = AdminAuthMiddleware(app=None, super_admin_role="root")
        user = _user(["root"])

        mw._mark_super_admin(user)

        assert getattr(user, "is_superuser", False) is True

    def test_leaves_other_roles_untouched(self) -> None:
        mw = AdminAuthMiddleware(app=None, super_admin_role="superadmin")
        user = _user(["editor"])

        mw._mark_super_admin(user)

        assert getattr(user, "is_superuser", False) is False

    def test_none_user_is_ignored(self) -> None:
        mw = AdminAuthMiddleware(app=None, super_admin_role="superadmin")
        # Must not raise.
        mw._mark_super_admin(None)

    def test_no_configured_role_is_noop(self) -> None:
        mw = AdminAuthMiddleware(app=None, super_admin_role=None)
        user = _user(["superadmin"])

        mw._mark_super_admin(user)

        assert getattr(user, "is_superuser", False) is False


class TestAuthorizationSuperAdminBypass:
    @pytest.mark.asyncio
    async def test_superuser_gets_full_capabilities(self) -> None:
        mw = AdminAuthorizationMiddleware(
            app=None,
            authorizer=None,
            permission_authorizer=_DenyAllPermissions(),
        )
        user = _user(["superadmin"])
        user.is_superuser = True  # type: ignore[attr-defined]

        caps = await mw._resource_capabilities(user, _request())

        assert caps == {
            "can_view": True,
            "can_create": True,
            "can_update": True,
            "can_delete": True,
        }

    @pytest.mark.asyncio
    async def test_configured_role_gets_full_capabilities(self) -> None:
        mw = AdminAuthorizationMiddleware(
            app=None,
            authorizer=None,
            permission_authorizer=_DenyAllPermissions(),
            super_admin_role="superadmin",
        )
        user = _user(["superadmin"])

        caps = await mw._resource_capabilities(user, _request())

        assert caps is not None
        assert all(caps.values())

    @pytest.mark.asyncio
    async def test_regular_user_still_denied(self) -> None:
        mw = AdminAuthorizationMiddleware(
            app=None,
            authorizer=None,
            permission_authorizer=_DenyAllPermissions(),
            super_admin_role="superadmin",
        )
        user = _user(["editor"])

        caps = await mw._resource_capabilities(user, _request())

        # Denied capability for the current action → None (fail closed).
        assert caps is None
