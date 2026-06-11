"""Tests for AdminAuthGuardMiddleware session expiry handling.

Verifies that HTMX requests are answered with an HX-Redirect header so
the browser performs a full-page navigation to the login page, instead
of swapping the login page into the current component.
"""

from __future__ import annotations

import httpx
import pytest
from starlette.applications import Starlette
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from lexigram.admin.middleware.auth_guard import AdminAuthGuardMiddleware


def _make_app() -> Starlette:
    """Build an app wrapped in the auth guard with a dummy protected route."""

    async def widgets(request) -> PlainTextResponse:
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route("/admin/widgets", widgets)])
    app.add_middleware(SessionMiddleware, secret_key="test-secret")
    return AdminAuthGuardMiddleware(app)


async def _request(path: str, *, htmx: bool) -> httpx.Response:
    headers = {"HX-Request": "true"} if htmx else {}
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=_make_app()),
        base_url="http://testserver",
    ) as client:
        return await client.get(path, headers=headers)


@pytest.mark.asyncio
async def test_htmx_request_gets_hx_redirect_to_login() -> None:
    """HTMX requests without a session get HX-Redirect to the login page."""
    resp = await _request("/admin/widgets", htmx=True)

    assert resp.status_code == 200
    assert resp.headers.get("HX-Redirect") == "/admin/login?next=/admin/widgets"


@pytest.mark.asyncio
async def test_non_htmx_request_gets_redirect_to_login() -> None:
    """Plain requests without a session get a 307 redirect to the login page."""
    resp = await _request("/admin/widgets", htmx=False)

    assert resp.status_code == 307
    assert resp.headers.get("location") == "/admin/login?next=/admin/widgets"


@pytest.mark.asyncio
async def test_2fa_challenge_path_bypasses_auth_guard() -> None:
    """The 2FA challenge page must be reachable without a session.

    The harness has no /admin/login/2fa route, so a 404 (not the 307 login
    redirect) proves the guard let the request through.
    """
    resp = await _request("/admin/login/2fa", htmx=False)

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_verify_email_page_bypasses_auth_guard() -> None:
    """The email verification landing page must be reachable without a session."""
    resp = await _request("/admin/verify-email", htmx=False)

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_verify_email_token_path_bypasses_auth_guard() -> None:
    """Email verification token links must be reachable without a session."""
    resp = await _request("/admin/verify-email/some-token-123", htmx=False)

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_unknown_login_subpath_still_auth_guarded() -> None:
    """Prefix matching must not widen the bypass for arbitrary /login paths."""
    resp = await _request("/admin/login/unknown-path", htmx=False)

    assert resp.status_code == 307


class TestSuffixCollisionPathsAreGuarded:
    """Protected routes whose last segment collides with a bypass suffix.

    Regression for Round 7 finding 32: paths like ``/admin/plugins/login``
    or a resource named ``register`` used to skip the session check because
    the guard matched by suffix; membership is now exact full-path only.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "path",
        [
            "/admin/plugins/login",
            "/admin/resources/register",
            "/admin/register/records",
            "/admin/setup/anything",
            "/admin/users/health",
            "/admin/users/health/",
            "/admin/widgets/logout",
        ],
    )
    async def test_suffix_collision_requires_session(self, path: str) -> None:
        """Suffix-colliding paths are auth-guarded (307 without a session)."""
        resp = await _request(path, htmx=False)

        assert resp.status_code == 307
        assert resp.headers.get("location") == f"/admin/login?next={path}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "path",
        [
            "/admin/login",
            "/admin/login/",
            "/admin/login/2fa",
            "/admin/login/2fa/",
            "/admin/verify-email",
            "/admin/password-reset",
            "/admin/register",
            "/admin/register/",
            "/admin/setup",
        ],
    )
    async def test_exact_public_routes_still_bypass(self, path: str) -> None:
        """Exact public routes (with or without trailing slash) stay public.

        Note: ``/admin/register`` and ``/admin/setup`` are the legitimate
        public registration/setup pages — a contributor resource named
        ``register``/``setup``/``login``/``health`` collides with that
        public route by design (naming-clash residual, recorded in the
        Round 7 finding 32 plan). The harness has no route for these
        paths, so a 404 (not the 307 login redirect) proves the guard let
        the request through.
        """
        resp = await _request(path, htmx=False)

        assert resp.status_code == 404
