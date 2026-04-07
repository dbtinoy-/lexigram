"""Integration smoke tests for the combined admin auth middleware stack.

Verifies that the middleware chain (SessionMiddleware, AdminErrorMiddleware,
AdminAuthMiddleware) works correctly when wired together.

Covers:
1. Anonymous request to /admin/* → 401 (or 302 redirect to login).
2. HTMX anonymous → JSON 401 with login_url (no HX-Redirect loop).
3. Public path (/admin/login) → 200.
4. Logged-in user reaches protected route → 200.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Route

from lexigram.admin.auth.protocols import AdminSessionServiceProtocol
from lexigram.admin.middleware.auth import AdminAuthMiddleware
from lexigram.admin.middleware.error import AdminErrorMiddleware
from lexigram.contracts import AuthenticatedUserProtocol


# ---------------------------------------------------------------------------
# Fake user
# ---------------------------------------------------------------------------


class _FakeUser:
    """Minimal AuthenticatedUserProtocol implementation."""

    def __init__(self, user_id: str, roles: list[str], is_active: bool = True) -> None:
        self.user_id = user_id
        self.email = f"{user_id}@test.io"
        self.roles = roles
        self.is_active = is_active

    def has_role(self, role: str) -> bool:
        return role in self.roles

    def has_permission(self, perm: str) -> bool:
        return True

    @property
    def id(self) -> str:
        return self.user_id


class _FakeUserStore:
    """Minimal admin user store."""

    def __init__(self, user: _FakeUser | None = None) -> None:
        self._user = user

    async def get_by_id(self, user_id: str) -> _FakeUser | None:
        return self._user


# ---------------------------------------------------------------------------
# Test app builder
# ---------------------------------------------------------------------------


def _make_app(
    user_store: _FakeUserStore | None = None,
    session_service: AdminSessionServiceProtocol | None = None,
) -> Starlette:
    """Build a minimal Starlette app with the admin auth middleware stack."""

    async def protected_route(request):
        return JSONResponse(
            {"ok": True, "user_id": request.state.user.user_id}
        )

    async def login_route(request):
        request.session["session_id"] = "test-sid"
        return JSONResponse({"ok": True})

    return Starlette(
        routes=[
            Route("/admin/users", protected_route, methods=["GET"]),
            Route("/admin/login", login_route, methods=["GET"]),
        ],
        middleware=[
            Middleware(SessionMiddleware, secret_key="test-secret"),
            Middleware(
                AdminErrorMiddleware,
                debug=False,
                login_url="/admin/login",
            ),
            Middleware(
                AdminAuthMiddleware,
                user_store=user_store,
                session_service=session_service,
                require_auth=True,
                excluded_paths=[
                    "/admin/login",
                    "/admin/static",
                    "/admin/health",
                ],
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.asyncio
async def test_anonymous_request_returns_401_or_redirect() -> None:
    """Anonymous request to /admin/* returns 401 (or redirects to login)."""
    app = _make_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.get("/admin/users")
        # Either 401 (if error middleware returns 401) or 302 (redirect to login)
        assert resp.status_code in (302, 401)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_anonymous_htmx_request_returns_json_401() -> None:
    """Anonymous HTMX request returns JSON 401 with login_url."""
    app = _make_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.get(
            "/admin/users",
            headers={"HX-Request": "true"},
        )
        assert resp.status_code == 401
        body = resp.json()
        assert body["error"] == "session_expired"
        assert body["login_url"] == "/admin/login"
        assert "HX-Redirect" not in resp.headers


@pytest.mark.integration
@pytest.mark.asyncio
async def test_public_path_skips_auth() -> None:
    """Public paths bypass the auth middleware and reach the route handler."""
    app = _make_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.get("/admin/login")
        assert resp.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_logged_in_user_reaches_protected_route() -> None:
    """A logged-in user (session_id present) gets through auth middleware."""
    user = _FakeUser(user_id="u1", roles=["admin"])
    user_store = _FakeUserStore(user=user)
    session_service = MagicMock(spec=AdminSessionServiceProtocol)
    session_service.get_session = AsyncMock(
        return_value={
            "session_id": "test-sid",
            "admin_id": "u1",
            "fingerprint": {"email": "admin@test.io", "roles": ["admin"]},
        }
    )

    app = _make_app(
        user_store=user_store,
        session_service=session_service,
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        # Seed the session by hitting the login route
        login_resp = await client.get("/admin/login")
        assert login_resp.status_code == 200

        resp = await client.get("/admin/users")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["user_id"] == "u1"
