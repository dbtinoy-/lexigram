"""R7 regression tests: content-negotiated 403/404/405/500 responses.

Browser navigations must always see the styled error page; API callers keep
JSON; HTMX callers keep fragment/HX-header semantics. Covers:

- ``AdminErrorMiddleware`` upgrading bare router responses (Starlette's
  plain-text 404/405) to the styled page for HTML navigations only.
- ``AdminAuthorizationMiddleware._forbidden`` returning the styled page,
  an HX-Trigger toast, or JSON depending on the caller.
"""

from __future__ import annotations

import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from lexigram.admin.middleware._negotiation import (
    NEGOTIABLE_STATUS_CODES,
    error_page_meta,
    prefers_html,
    styled_error_response,
)
from lexigram.admin.middleware.error import AdminErrorMiddleware

BROWSER_ACCEPT = (
    "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
)


def _app() -> Starlette:
    async def ok(request):
        return PlainTextResponse("ok")

    async def json_error(request):
        return JSONResponse({"error": "forbidden"}, status_code=403)

    app = Starlette(
        routes=[
            Route("/admin/ok", ok),
            Route("/admin/json-403", json_error),
        ],
    )
    app.add_middleware(
        AdminErrorMiddleware,
        debug=False,
        admin_prefix="/admin",
    )
    return app


@pytest.fixture
def client() -> TestClient:
    return TestClient(_app(), raise_server_exceptions=False)


class TestErrorMiddlewareNegotiation:
    def test_browser_404_gets_styled_page(self, client):
        resp = client.get("/admin/nope", headers={"Accept": BROWSER_ACCEPT})
        assert resp.status_code == 404
        assert resp.headers["content-type"].startswith("text/html")
        assert "Page Not Found" in resp.text
        assert "Not Found" != resp.text.strip()  # no bare plain-text body

    def test_browser_405_gets_styled_page(self, client):
        resp = client.post("/admin/ok", headers={"Accept": BROWSER_ACCEPT})
        assert resp.status_code == 405
        assert resp.headers["content-type"].startswith("text/html")
        assert "Method Not Allowed" in resp.text

    def test_json_caller_keeps_plain_404(self, client):
        resp = client.get("/admin/nope", headers={"Accept": "application/json"})
        assert resp.status_code == 404
        assert not resp.headers["content-type"].startswith("text/html")

    def test_default_accept_keeps_plain_404(self, client):
        # curl-style Accept: */* is not a browser navigation
        resp = client.get("/admin/nope", headers={"Accept": "*/*"})
        assert resp.status_code == 404
        assert not resp.headers["content-type"].startswith("text/html")

    def test_htmx_fragment_swap_is_not_upgraded(self, client):
        # Fragment swaps carry an HX-Target other than "body"; they must not
        # receive a full styled page. (Boosted navigations without a target
        # behave like browser navigations and DO get the page.)
        resp = client.get(
            "/admin/nope",
            headers={
                "Accept": BROWSER_ACCEPT,
                "HX-Request": "true",
                "HX-Target": "main-content",
            },
        )
        assert not resp.headers["content-type"].startswith("text/html")

    def test_inner_json_403_upgraded_for_browser(self, client):
        resp = client.get("/admin/json-403", headers={"Accept": BROWSER_ACCEPT})
        assert resp.status_code == 403
        assert resp.headers["content-type"].startswith("text/html")
        assert "Access Denied" in resp.text

    def test_inner_json_403_kept_for_api(self, client):
        resp = client.get(
            "/admin/json-403", headers={"Accept": "application/json"}
        )
        assert resp.status_code == 403
        assert resp.json() == {"error": "forbidden"}

    def test_success_responses_untouched(self, client):
        resp = client.get("/admin/ok", headers={"Accept": BROWSER_ACCEPT})
        assert resp.status_code == 200
        assert resp.text == "ok"


class TestAuthorizationForbiddenNegotiation:
    def _middleware(self):
        from lexigram.admin.middleware.authorization import (
            AdminAuthorizationMiddleware,
        )

        # dispatch is never called in these tests; app/authorizer are inert.
        return AdminAuthorizationMiddleware.__new__(AdminAuthorizationMiddleware)

    def _request(self, headers: dict[str, str]):
        from starlette.requests import Request

        raw = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/admin/products",
            "query_string": b"",
            "headers": raw,
        }
        return Request(scope)

    def test_browser_navigation_gets_styled_403(self):
        mw = self._middleware()
        mw._admin_prefix = "/admin"
        resp = mw._forbidden(self._request({"Accept": BROWSER_ACCEPT}))
        assert resp.status_code == 403
        assert resp.headers["content-type"].startswith("text/html")
        assert b"Access Denied" in resp.body

    def test_htmx_gets_toast_trigger(self):
        mw = self._middleware()
        mw._admin_prefix = "/admin"
        resp = mw._forbidden(
            self._request({"Accept": BROWSER_ACCEPT, "HX-Request": "true"})
        )
        assert resp.status_code == 403
        assert "HX-Trigger" in resp.headers
        assert "showMessage" in resp.headers["HX-Trigger"]

    def test_api_caller_gets_json(self):
        mw = self._middleware()
        mw._admin_prefix = "/admin"
        resp = mw._forbidden(self._request({"Accept": "application/json"}))
        assert resp.status_code == 403
        assert resp.headers["content-type"].startswith("application/json")


class TestNegotiationHelpers:
    def test_negotiable_status_codes(self):
        assert NEGOTIABLE_STATUS_CODES == frozenset({403, 404, 405, 500})

    def test_error_page_meta_known_and_fallback(self):
        assert error_page_meta(404)[0] == "Page Not Found"
        assert error_page_meta(418)[0] == "Error"

    def test_styled_error_response_uses_prefix(self):
        resp = styled_error_response(404, "/panel")
        assert b'href="/panel/"' in resp.body or b"/panel/" in resp.body

    def test_prefers_html_rules(self):
        class _Req:
            def __init__(self, accept):
                self.headers = {"accept": accept}

        assert prefers_html(_Req(BROWSER_ACCEPT)) is True
        assert prefers_html(_Req("application/json")) is False
        assert prefers_html(_Req("text/html, application/json")) is False
        assert prefers_html(_Req("*/*")) is False
