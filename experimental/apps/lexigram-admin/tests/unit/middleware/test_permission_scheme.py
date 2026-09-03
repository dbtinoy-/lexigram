"""R6 regression tests: canonical permission scheme + legacy alias bridge.

The canonical scheme is ``{resource}.view/.create/.update/.delete``;
``.read``/``.list`` (view) and ``.edit`` (update) are deprecated aliases
honoured during the migration window with a one-line deprecation warning.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from lexigram.admin.auth import permission_scheme as scheme
from lexigram.admin.middleware.authorization import AdminAuthorizationMiddleware


class _AllowAll:
    async def authorize_request(self, user: object, request: Request) -> bool:
        return True


class _PermissionSetService:
    """Permission service backed by a plain set of permission strings."""

    def __init__(self, permissions: set[str]) -> None:
        self._permissions = permissions

    def _has(self, resource: str, action: str) -> bool:
        return f"{resource}.{action}" in self._permissions

    async def can_view(self, user: object, resource: str) -> bool:
        return self._has(resource, "view")

    async def can_create(self, user: object, resource: str) -> bool:
        return self._has(resource, "create")

    async def can_update(self, user: object, resource: str) -> bool:
        return self._has(resource, "update")

    async def can_delete(self, user: object, resource: str) -> bool:
        return self._has(resource, "delete")

    async def can_execute_action(
        self, user: object, resource: str, action: str
    ) -> bool:
        return self._has(resource, action)


def _make_request(path: str, user: object) -> Request:
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
    req = Request(scope)  # type: ignore[arg-type]
    req.state.user = user
    return req


async def _ok(request: Request) -> PlainTextResponse:
    return PlainTextResponse("OK")


def _user() -> MagicMock:
    user = MagicMock()
    user.roles = ["editor"]
    return user


def _middleware(permissions: set[str]) -> AdminAuthorizationMiddleware:
    return AdminAuthorizationMiddleware(
        app=None,
        authorizer=_AllowAll(),
        permission_authorizer=_PermissionSetService(permissions),
    )


class TestPermissionScheme:
    def test_canonical_actions(self):
        assert scheme.CANONICAL_ACTIONS == ("view", "create", "update", "delete")

    def test_candidate_permissions_view(self):
        assert scheme.candidate_permissions("products", "view") == (
            "products.view",
            "products.read",
            "products.list",
        )

    def test_candidate_permissions_update(self):
        assert scheme.candidate_permissions("products", "update") == (
            "products.update",
            "products.edit",
        )

    def test_candidate_permissions_no_aliases(self):
        assert scheme.candidate_permissions("products", "delete") == (
            "products.delete",
        )
        assert scheme.candidate_permissions("products", "create") == (
            "products.create",
        )

    def test_warn_legacy_grant_dedupes(self, caplog):
        scheme._warned_legacy_grants.discard(("widgets", "read"))
        scheme.warn_legacy_grant("widgets", "read")
        assert ("widgets", "read") in scheme._warned_legacy_grants
        # Second call must be a no-op (no exception, still recorded once)
        scheme.warn_legacy_grant("widgets", "read")


class TestLegacyAliasBridge:
    @pytest.mark.asyncio
    async def test_canonical_view_grant_passes(self):
        mw = _middleware({"users.view"})
        resp = await mw.dispatch(_make_request("/admin/users", _user()), _ok)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_legacy_read_grant_still_views(self):
        """A user granted only ``users.read`` can still view (bridge)."""
        scheme._warned_legacy_grants.discard(("users", "read"))
        mw = _middleware({"users.read"})
        resp = await mw.dispatch(_make_request("/admin/users", _user()), _ok)
        assert resp.status_code == 200
        assert ("users", "read") in scheme._warned_legacy_grants

    @pytest.mark.asyncio
    async def test_legacy_edit_grant_still_updates(self):
        mw = _middleware({"users.view", "users.edit"})
        resp = await mw.dispatch(
            _make_request("/admin/users/1/edit", _user()), _ok
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_no_grant_is_denied(self):
        mw = _middleware(set())
        resp = await mw.dispatch(_make_request("/admin/users", _user()), _ok)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_has_no_alias(self):
        """No legacy alias exists for delete — canonical only."""
        mw = _middleware({"users.view", "users.remove"})
        resp = await mw.dispatch(
            _make_request("/admin/users/1/delete", _user()), _ok
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_capabilities_reflect_alias_grants(self):
        """Renderer capabilities include alias-granted actions."""
        mw = _middleware({"users.read", "users.edit"})

        async def inspect(request: Request) -> PlainTextResponse:
            assert request.state.permissions == {
                "can_view": True,
                "can_create": False,
                "can_update": True,
                "can_delete": False,
            }
            return PlainTextResponse("OK")

        resp = await mw.dispatch(_make_request("/admin/users", _user()), inspect)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_service_without_execute_action_fails_closed(self):
        """Services lacking ``can_execute_action`` keep canonical-only checks."""

        class _NoAliasService(_PermissionSetService):
            can_execute_action = None  # type: ignore[assignment]

        mw = AdminAuthorizationMiddleware(
            app=None,
            authorizer=_AllowAll(),
            permission_authorizer=_NoAliasService({"users.read"}),
        )
        resp = await mw.dispatch(_make_request("/admin/users", _user()), _ok)
        assert resp.status_code == 403
