"""Extended tests for auth/permissions.py.

Covers Permission, PermissionSet, get_user_permissions, create_permission_context.
The require_permission / require_all_permissions / require_role decorators are
tested via mock request objects.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from lexigram.admin.auth.permissions import (
    Action,
    Permission,
    PermissionSet,
    create_permission_context,
    get_user_permissions,
    require_all_permissions,
    require_permission,
    require_role,
)


# ---------------------------------------------------------------------------
# Permission
# ---------------------------------------------------------------------------


class TestPermission:
    """Tests for Permission dataclass."""

    def test_str_representation(self) -> None:
        p = Permission(resource="users", action="list")
        assert str(p) == "users.list"

    def test_from_string_valid(self) -> None:
        p = Permission.from_string("posts.delete")
        assert p.resource == "posts"
        assert p.action == "delete"

    def test_from_string_invalid_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid permission format"):
            Permission.from_string("no-dot-here")

    def test_from_string_with_nested_action(self) -> None:
        # Only split on first dot
        p = Permission.from_string("admin.settings.read")
        assert p.resource == "admin"
        assert p.action == "settings.read"

    def test_for_resource_all_actions(self) -> None:
        perms = Permission.for_resource("users")
        assert len(perms) == len(Action.all_actions())
        resources = {p.resource for p in perms}
        assert resources == {"users"}

    def test_for_resource_specific_actions(self) -> None:
        perms = Permission.for_resource("posts", actions=[Action.LIST, Action.VIEW])
        assert len(perms) == 2
        actions = {p.action for p in perms}
        assert actions == {"list", "view"}

    def test_equality(self) -> None:
        p1 = Permission(resource="users", action="list")
        p2 = Permission(resource="users", action="list")
        assert p1 == p2

    def test_inequality(self) -> None:
        p1 = Permission(resource="users", action="list")
        p2 = Permission(resource="users", action="delete")
        assert p1 != p2


# ---------------------------------------------------------------------------
# PermissionSet
# ---------------------------------------------------------------------------


class TestPermissionSet:
    """Tests for PermissionSet."""

    def test_empty_set(self) -> None:
        ps = PermissionSet()
        assert len(ps) == 0

    def test_add_string_permission(self) -> None:
        ps = PermissionSet()
        ps.add("users.list")
        assert "users.list" in ps.permissions

    def test_add_permission_object(self) -> None:
        ps = PermissionSet()
        ps.add(Permission(resource="posts", action="create"))
        assert "posts.create" in ps.permissions

    def test_add_multiple(self) -> None:
        ps = PermissionSet()
        ps.add("users.list", "users.view", "posts.create")
        assert len(ps) == 3

    def test_add_returns_self(self) -> None:
        ps = PermissionSet()
        result = ps.add("users.list")
        assert result is ps

    def test_remove_permission(self) -> None:
        ps = PermissionSet(permissions={"users.list", "users.view"})
        ps.remove("users.list")
        assert "users.list" not in ps.permissions
        assert "users.view" in ps.permissions

    def test_remove_nonexistent_is_safe(self) -> None:
        ps = PermissionSet(permissions={"users.list"})
        ps.remove("nonexistent.perm")  # Should not raise
        assert "users.list" in ps.permissions

    def test_remove_returns_self(self) -> None:
        ps = PermissionSet(permissions={"users.list"})
        result = ps.remove("users.list")
        assert result is ps

    def test_has_exact_match(self) -> None:
        ps = PermissionSet(permissions={"users.list"})
        assert ps.has("users.list") is True
        assert ps.has("users.delete") is False

    def test_has_global_wildcard(self) -> None:
        ps = PermissionSet(permissions={"*"})
        assert ps.has("users.list") is True
        assert ps.has("anything.here") is True

    def test_has_resource_wildcard(self) -> None:
        ps = PermissionSet(permissions={"users.*"})
        assert ps.has("users.list") is True
        assert ps.has("users.delete") is True
        assert ps.has("posts.create") is False

    def test_has_permission_object(self) -> None:
        ps = PermissionSet(permissions={"users.list"})
        assert ps.has(Permission(resource="users", action="list")) is True

    def test_has_any(self) -> None:
        ps = PermissionSet(permissions={"users.list"})
        assert ps.has_any("users.list", "users.delete") is True
        assert ps.has_any("posts.create", "posts.delete") is False

    def test_has_all(self) -> None:
        ps = PermissionSet(permissions={"users.list", "users.view"})
        assert ps.has_all("users.list", "users.view") is True
        assert ps.has_all("users.list", "users.delete") is False

    def test_contains_operator(self) -> None:
        ps = PermissionSet(permissions={"users.list"})
        assert "users.list" in ps
        assert "posts.create" not in ps

    def test_iter(self) -> None:
        perms = {"users.list", "posts.create"}
        ps = PermissionSet(permissions=perms)
        assert set(ps) == perms

    def test_len(self) -> None:
        ps = PermissionSet(permissions={"a.b", "c.d", "e.f"})
        assert len(ps) == 3


# ---------------------------------------------------------------------------
# get_user_permissions
# ---------------------------------------------------------------------------


class TestGetUserPermissions:
    """Tests for get_user_permissions."""

    def test_no_permissions_no_roles(self) -> None:
        user = SimpleNamespace(permissions=[], roles=[])
        auth_svc = MagicMock()
        auth_svc.get_role_permissions.return_value = []
        ps = get_user_permissions(user, auth_svc)
        assert len(ps) == 0

    def test_direct_permissions(self) -> None:
        user = SimpleNamespace(permissions=["users.list", "posts.view"], roles=[])
        auth_svc = MagicMock()
        auth_svc.get_role_permissions.return_value = []
        ps = get_user_permissions(user, auth_svc)
        assert ps.has("users.list")
        assert ps.has("posts.view")

    def test_role_based_permissions(self) -> None:
        user = SimpleNamespace(permissions=[], roles=["admin"])
        auth_svc = MagicMock()
        auth_svc.get_role_permissions.return_value = ["users.*", "posts.*"]
        ps = get_user_permissions(user, auth_svc)
        assert ps.has("users.list")
        assert ps.has("posts.delete")

    def test_combined_permissions(self) -> None:
        user = SimpleNamespace(permissions=["settings.read"], roles=["editor"])
        auth_svc = MagicMock()
        auth_svc.get_role_permissions.return_value = ["posts.*"]
        ps = get_user_permissions(user, auth_svc)
        assert ps.has("settings.read")
        assert ps.has("posts.create")

    def test_missing_permissions_attr(self) -> None:
        user = SimpleNamespace(roles=[])
        auth_svc = MagicMock()
        auth_svc.get_role_permissions.return_value = []
        ps = get_user_permissions(user, auth_svc)
        assert len(ps) == 0


# ---------------------------------------------------------------------------
# create_permission_context
# ---------------------------------------------------------------------------


class TestCreatePermissionContext:
    """Tests for create_permission_context."""

    def test_returns_dict_with_required_keys(self) -> None:
        user = SimpleNamespace(permissions=["users.list"], roles=["admin"])
        auth_svc = MagicMock()
        auth_svc.get_role_permissions.return_value = []
        ctx = create_permission_context(user, auth_svc)
        assert "user" in ctx
        assert "can" in ctx
        assert "can_any" in ctx
        assert "can_all" in ctx
        assert "has_role" in ctx
        assert "has_any_role" in ctx
        assert "permissions" in ctx

    def test_user_in_context(self) -> None:
        user = SimpleNamespace(permissions=[], roles=[])
        auth_svc = MagicMock()
        auth_svc.get_role_permissions.return_value = []
        ctx = create_permission_context(user, auth_svc)
        assert ctx["user"] is user

    def test_can_callable(self) -> None:
        user = SimpleNamespace(permissions=["users.list"], roles=[])
        auth_svc = MagicMock()
        auth_svc.get_role_permissions.return_value = []
        ctx = create_permission_context(user, auth_svc)
        assert ctx["can"]("users.list") is True
        assert ctx["can"]("posts.delete") is False

    def test_has_role_callable(self) -> None:
        user = SimpleNamespace(permissions=[], roles=["admin", "editor"])
        auth_svc = MagicMock()
        auth_svc.get_role_permissions.return_value = []
        ctx = create_permission_context(user, auth_svc)
        assert ctx["has_role"]("admin") is True
        assert ctx["has_role"]("superuser") is False

    def test_has_any_role_callable(self) -> None:
        user = SimpleNamespace(permissions=[], roles=["editor"])
        auth_svc = MagicMock()
        auth_svc.get_role_permissions.return_value = []
        ctx = create_permission_context(user, auth_svc)
        assert ctx["has_any_role"]("admin", "editor") is True
        assert ctx["has_any_role"]("admin", "superuser") is False


# ---------------------------------------------------------------------------
# require_permission decorator
# ---------------------------------------------------------------------------


class TestRequirePermission:
    """Tests for require_permission decorator."""

    @pytest.mark.asyncio
    async def test_passes_when_permission_present(self) -> None:
        ps = PermissionSet(permissions={"users.list"})
        state = SimpleNamespace(permissions=ps, user=SimpleNamespace())
        request = SimpleNamespace(user=SimpleNamespace(), state=state)

        @require_permission("users.list")
        async def handler(req):
            return "ok"

        result = await handler(request)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_raises_when_permission_missing(self) -> None:
        from lexigram.admin.exceptions import PermissionDeniedError

        ps = PermissionSet(permissions={"posts.view"})
        state = SimpleNamespace(permissions=ps, user=SimpleNamespace())
        request = SimpleNamespace(user=SimpleNamespace(), state=state)

        @require_permission("users.list")
        async def handler(req):
            return "ok"

        with pytest.raises(PermissionDeniedError):
            await handler(request)

    @pytest.mark.asyncio
    async def test_raises_when_no_user(self) -> None:
        from lexigram.admin.exceptions import PermissionDeniedError

        state = SimpleNamespace(permissions=None, user=None)
        request = SimpleNamespace(user=None, state=state)

        @require_permission("users.list")
        async def handler(req):
            return "ok"

        with pytest.raises(PermissionDeniedError, match="Authentication required"):
            await handler(request)

    @pytest.mark.asyncio
    async def test_raises_when_permissions_not_in_state(self) -> None:
        from lexigram.admin.exceptions import PermissionDeniedError

        state = SimpleNamespace(permissions=None)
        request = SimpleNamespace(user=SimpleNamespace(), state=state)

        @require_permission("users.list")
        async def handler(req):
            return "ok"

        with pytest.raises(PermissionDeniedError):
            await handler(request)

    def test_stores_metadata(self) -> None:
        @require_permission("users.list", "posts.view")
        async def handler(req):
            return "ok"

        assert handler.__required_permissions__ == ["users.list", "posts.view"]


# ---------------------------------------------------------------------------
# require_role decorator
# ---------------------------------------------------------------------------


class TestRequireRole:
    """Tests for require_role decorator."""

    @pytest.mark.asyncio
    async def test_passes_when_role_present(self) -> None:
        user = SimpleNamespace(roles=["admin"])
        request = SimpleNamespace(user=user, state=SimpleNamespace())

        @require_role("admin")
        async def handler(req):
            return "ok"

        result = await handler(request)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_raises_when_role_missing(self) -> None:
        from lexigram.admin.exceptions import PermissionDeniedError

        user = SimpleNamespace(roles=["viewer"])
        request = SimpleNamespace(user=user, state=SimpleNamespace())

        @require_role("admin")
        async def handler(req):
            return "ok"

        with pytest.raises(PermissionDeniedError):
            await handler(request)

    @pytest.mark.asyncio
    async def test_passes_when_any_role_matches(self) -> None:
        user = SimpleNamespace(roles=["editor"])
        request = SimpleNamespace(user=user, state=SimpleNamespace())

        @require_role("admin", "editor")
        async def handler(req):
            return "ok"

        result = await handler(request)
        assert result == "ok"

    def test_stores_metadata(self) -> None:
        @require_role("admin", "superuser")
        async def handler(req):
            return "ok"

        assert handler.__required_roles__ == ["admin", "superuser"]


# ---------------------------------------------------------------------------
# require_all_permissions decorator
# ---------------------------------------------------------------------------


class TestRequireAllPermissions:
    """Tests for require_all_permissions decorator."""

    @pytest.mark.asyncio
    async def test_passes_when_all_present(self) -> None:
        ps = PermissionSet(permissions={"users.list", "users.view"})
        state = SimpleNamespace(permissions=ps)
        request = SimpleNamespace(user=SimpleNamespace(), state=state)

        @require_all_permissions("users.list", "users.view")
        async def handler(req):
            return "ok"

        result = await handler(request)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_raises_when_one_missing(self) -> None:
        from lexigram.admin.exceptions import PermissionDeniedError

        ps = PermissionSet(permissions={"users.list"})
        state = SimpleNamespace(permissions=ps)
        request = SimpleNamespace(user=SimpleNamespace(), state=state)

        @require_all_permissions("users.list", "users.delete")
        async def handler(req):
            return "ok"

        with pytest.raises(PermissionDeniedError):
            await handler(request)

    def test_stores_metadata(self) -> None:
        @require_all_permissions("users.list", "posts.view")
        async def handler(req):
            return "ok"

        assert handler.__required_permissions__ == ["users.list", "posts.view"]
        assert handler.__require_all__ is True
