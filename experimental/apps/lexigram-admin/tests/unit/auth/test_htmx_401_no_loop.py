"""Tests for HTMX 401 handling (AUTH-16).

Verifies that AdminErrorMiddleware returns an HX-Redirect header for
401 responses on HTMX requests, forcing a full-page navigation to the
login page instead of swapping the login page into the current
component. Requests already targeting the login page still get JSON.
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
    def test_htmx_401_returns_hx_redirect(self) -> None:
        """HTMX 401 returns HX-Redirect for a full-page login navigation."""
        mw = AdminErrorMiddleware(app=MagicMock(), debug=False)
        exc = HTTPError(status_code=401, detail="Unauthorized")

        resp = mw._make_htmx_response(_make_htmx_request(), 401, "Unauthorized", exc)

        assert resp.status_code == 200
        assert resp.headers.get("HX-Redirect") == "/admin/login?next=/admin/users"
        assert "HX-Redirect" in resp.headers

    def test_htmx_401_on_login_page_returns_json(self) -> None:
        """HTMX 401 on the login page itself returns JSON to avoid a loop."""
        mw = AdminErrorMiddleware(app=MagicMock(), debug=False)
        exc = HTTPError(status_code=401, detail="Unauthorized")

        resp = mw._make_htmx_response(_make_htmx_request("/admin/login"), 401, "Unauthorized", exc)

        assert resp.status_code == 401

        body = json_loads(resp.body)
        assert body["error"] == "session_expired"
        assert body["login_url"] == "/admin/login"

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
