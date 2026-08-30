"""Tests for AdminAuthorizationMiddleware (AUTH-09, AUTH-18)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from lexigram.admin.middleware.authorization import (
    AdminAuthorizationMiddleware,
)


class DenyAll:
    """Authorizer that denies every request."""

    async def authorize_request(self, user: object, request: Request) -> bool:
        return False


class AllowAdmin:
    """Authorizer that allows users with the 'admin' role."""

    async def authorize_request(self, user: object, request: Request) -> bool:
        return "admin" in getattr(user, "roles", [])


class _ResourcePermissions:
    def __init__(self, **overrides: bool) -> None:
        self.values = {
            "can_view": True,
            "can_create": True,
            "can_update": True,
            "can_delete": True,
        }
        self.values.update(overrides)

    async def can_view(self, user: object, resource: str) -> bool:
        return self.values["can_view"]

    async def can_create(self, user: object, resource: str) -> bool:
        return self.values["can_create"]

    async def can_update(self, user: object, resource: str) -> bool:
        return self.values["can_update"]

    async def can_delete(self, user: object, resource: str) -> bool:
        return self.values["can_delete"]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_request(
    path: str = "/admin/users",
    user: object = None,
    hx_request: str | None = None,
) -> Request:
    """Build a minimal Starlette Request with state.user."""
    headers = [(b"host", b"localhost")]
    if hx_request is not None:
        headers.append((b"hx-request", hx_request.encode()))
    scope: dict = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": headers,
        "state": {},
        "query_string": b"",
        "scheme": "http",
        "server": ("localhost", 80),
    }
    req = Request(scope)  # type: ignore[arg-type]
    req.state.user = user
    return req


async def _ok_call_next(request: Request) -> PlainTextResponse:
    return PlainTextResponse("OK")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_anonymous_request_redirects_to_login() -> None:
    """Anonymous (no user) request gets 302 redirect to login."""
    mw = AdminAuthorizationMiddleware(app=None, authorizer=DenyAll())
    request = _make_request()
    resp = mw._unauthenticated(request)
    assert resp.status_code == 302
    assert "/admin/login" in resp.headers.get("location", "")


@pytest.mark.asyncio
async def test_logged_in_non_admin_denied() -> None:
    """Non-admin user is denied by AllowAdmin authorizer."""
    mw = AdminAuthorizationMiddleware(app=None, authorizer=AllowAdmin())
    viewer = MagicMock()
    viewer.user_id = "v1"
    viewer.roles = ["viewer"]
    request = _make_request(user=viewer)
    allowed = await mw._authorizer.authorize_request(viewer, request)
    assert allowed is False
    resp = mw._forbidden(request)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_passes_through() -> None:
    """Admin user passes through to call_next."""
    mw = AdminAuthorizationMiddleware(app=None, authorizer=AllowAdmin())
    admin = MagicMock()
    admin.roles = ["admin"]
    request = _make_request(user=admin)

    resp = await mw.dispatch(request, _ok_call_next)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_resource_capability_denies_create_route() -> None:
    """A request-level allow does not bypass resource CRUD permissions."""
    mw = AdminAuthorizationMiddleware(
        app=None,
        authorizer=AllowAdmin(),
        permission_authorizer=_ResourcePermissions(can_create=False),
    )
    admin = MagicMock()
    admin.roles = ["admin"]
    request = _make_request(path="/admin/users/create", user=admin)

    resp = await mw.dispatch(request, _ok_call_next)

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_resource_capabilities_are_attached_for_rendering() -> None:
    """Allowed resource capabilities are made available to UI renderers."""
    mw = AdminAuthorizationMiddleware(
        app=None,
        authorizer=AllowAdmin(),
        permission_authorizer=_ResourcePermissions(can_delete=False),
    )
    admin = MagicMock()
    admin.roles = ["admin"]
    request = _make_request(path="/admin/users", user=admin)

    async def inspect_request(current_request: Request) -> PlainTextResponse:
        assert current_request.state.permissions == {
            "can_view": True,
            "can_create": True,
            "can_update": True,
            "can_delete": False,
        }
        return PlainTextResponse("OK")

    resp = await mw.dispatch(request, inspect_request)

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_non_resource_routes_use_request_authorization_only() -> None:
    """Search and contributor routes are not mistaken for resources."""
    mw = AdminAuthorizationMiddleware(
        app=None,
        authorizer=AllowAdmin(),
        permission_authorizer=_ResourcePermissions(can_view=False),
        resource_names={"users"},
    )
    admin = MagicMock()
    admin.roles = ["admin"]
    request = _make_request(path="/admin/search", user=admin)

    async def inspect_request(current_request: Request) -> PlainTextResponse:
        assert not hasattr(current_request.state, "permissions")
        return PlainTextResponse("OK")

    resp = await mw.dispatch(request, inspect_request)

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_public_path_skips_authorization() -> None:
    """Login, static, and health paths bypass authorizer."""
    mw = AdminAuthorizationMiddleware(app=None, authorizer=DenyAll())

    for path in ("/admin/login", "/admin/static/css/app.css", "/admin/health"):
        request = _make_request(path=path)
        resp = await mw.dispatch(request, _ok_call_next)
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_public_paths_follow_configured_prefix() -> None:
    """Custom mount prefixes skip the same public paths."""
    mw = AdminAuthorizationMiddleware(
        app=None, authorizer=DenyAll(), admin_prefix="/console"
    )

    for path in (
        "/console/login",
        "/console/static/css/app.css",
        "/console/health",
        "/console/password-reset",
    ):
        request = _make_request(path=path)
        resp = await mw.dispatch(request, _ok_call_next)
        assert resp.status_code == 200

    # The default-prefix public paths no longer bypass under /console.
    request = _make_request(path="/admin/login")
    resp = await mw.dispatch(request, _ok_call_next)
    assert resp.status_code == 302


@pytest.mark.asyncio
async def test_public_path_matching_does_not_allow_prefix_collisions() -> None:
    """A resource named login-evil must not inherit the public login bypass."""
    mw = AdminAuthorizationMiddleware(app=None, authorizer=DenyAll())
    request = _make_request(path="/admin/login-evil")

    resp = await mw.dispatch(request, _ok_call_next)

    assert resp.status_code == 302


@pytest.mark.asyncio
async def test_login_redirect_uses_configured_prefix() -> None:
    """Redirects point at the configured mount's login page."""
    mw = AdminAuthorizationMiddleware(
        app=None, authorizer=DenyAll(), admin_prefix="/console"
    )
    request = _make_request(path="/console/users")
    resp = mw._unauthenticated(request)
    assert resp.status_code == 302
    assert resp.headers.get("location", "").startswith("/console/login?next=")


@pytest.mark.asyncio
async def test_anonymous_htmx_returns_hx_redirect() -> None:
    """HTMX requests get HX-Redirect so the login page replaces the page."""
    mw = AdminAuthorizationMiddleware(app=None, authorizer=DenyAll())
    request = _make_request(hx_request="true")
    resp = mw._unauthenticated(request)
    assert resp.status_code == 200
    assert resp.headers.get("HX-Redirect", "").startswith("/admin/login?next=")


@pytest.mark.asyncio
async def test_anonymous_non_htmx_redirects_to_login() -> None:
    """Non-HTMX requests get 302 redirect to login."""
    mw = AdminAuthorizationMiddleware(app=None, authorizer=DenyAll())
    request = _make_request()
    resp = mw._unauthenticated(request)
    assert resp.status_code == 302
    assert "/admin/login" in resp.headers.get("location", "")


@pytest.mark.asyncio
async def test_logged_in_but_denied_returns_403() -> None:
    """Even an admin user is denied by DenyAll authorizer."""
    mw = AdminAuthorizationMiddleware(app=None, authorizer=DenyAll())
    admin = MagicMock()
    admin.roles = ["admin"]
    request = _make_request(user=admin)

    resp = await mw.dispatch(request, _ok_call_next)
    assert resp.status_code == 403
