"""Tests for HTMX 401 handling — no redirect loop (AUTH-16).

Verifies that AdminErrorMiddleware returns JSON with login_url instead
of an HX-Redirect header when handling a 401 for an HTMX request.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from starlette.exceptions import HTTPException as HTTPError
from starlette.requests import Request

from lexigram.admin.middleware.error import AdminErrorMiddleware
from lexigram.serialization import loads as json_loads


def _make_htmx_request(path: str = "/admin/users") -> Request:
    """Create a Starlette Request simulating an HTMX request."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": [(b"hx-request", b"true")],
        "query_string": b"",
        "scheme": "http",
        "server": ("test", 80),
    }
    return Request(scope)


class TestAdminErrorMiddlewareHtmx401:
    def test_htmx_401_returns_json_not_hx_redirect(self) -> None:
        """HTMX 401 returns JSON with login_url, no HX-Redirect header."""
        mw = AdminErrorMiddleware(app=MagicMock(), debug=False)
        exc = HTTPError(status_code=401, detail="Unauthorized")

        resp = mw._make_htmx_response(_make_htmx_request(), 401, "Unauthorized", exc)

        assert resp.status_code == 401
        assert resp.headers.get("content-type") == "application/json"

        body = json_loads(resp.body)
        assert body["error"] == "session_expired"
        assert body["login_url"] == "/admin/login"
        assert "HX-Redirect" not in resp.headers

    def test_htmx_403_returns_htmx_fragment(self) -> None:
        """HTMX 403 returns HTMX fragment, not plain JSON."""
        mw = AdminErrorMiddleware(app=MagicMock(), debug=True)
        exc = HTTPError(status_code=403, detail="Forbidden")

        resp = mw._make_htmx_response(_make_htmx_request(), 403, "Forbidden", exc)

        # HTMX error fragment renders as HTMLResponse at 200 for swap
        assert resp.status_code == 200
        assert "Access Denied" in (
            resp.body.decode() if isinstance(resp.body, bytes) else str(resp.body)
        )
