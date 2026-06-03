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
