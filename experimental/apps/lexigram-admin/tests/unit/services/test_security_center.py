"""R35 regressions — Security Center CSP tab (doc 31).

Covers the rendering helpers (policy cards, badges, settings overrides,
violations region incl. the store-unavailable state), the controller's
CSP tab routes (superadmin gate, tab chrome, fragment polling attrs),
and the tab entry itself.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.exceptions import HTTPException
from starlette.requests import Request

from lexigram.admin.controllers.security import SecurityController
from lexigram.admin.services.security.csp_reports import CspReportStore
from lexigram.admin.services.security.pages import (
    EMPTY_STATE,
    STORE_UNAVAILABLE,
    render_csp_cards,
    render_csp_violations_region,
    resolve_csp_policies,
)
from lexigram.admin.settings.panel.models import DEFAULT_CSP, STRICT_CSP


class _Settings:
    def __init__(self, values: dict[str, Any] | None = None, boom: bool = False):
        self._values = values or {}
        self._boom = boom

    async def get(self, key: str) -> Any:
        if self._boom:
            raise RuntimeError("settings down")
        return self._values.get(key)


class _FakeUser:
    def __init__(self, user_id: str = "u-1", is_superuser: bool = False) -> None:
        self.user_id = user_id
        self.email = f"{user_id}@example.com"
        self.roles: list[str] = []
        self.is_superuser = is_superuser
        self.permissions: frozenset[str] = frozenset()


def _request(user: Any, path: str = "/admin/security/csp") -> MagicMock:
    req = MagicMock(spec=Request)
    req.__len__ = MagicMock(return_value=1)
    req.state.user = user
    req.state.container = None
    req.app.state.container = None
    req.scope = {"root_path": "/admin"}
    req.session = {}
    req.query_params = {}
    req.url.path = path
    req.headers = {}
    req.client = SimpleNamespace(host="127.0.0.1")
    return req


def _controller(**attrs: Any) -> SecurityController:
    controller = SecurityController(renderer=MagicMock())
    for key, value in attrs.items():
        setattr(controller, key, value)
    return controller


# ---------------------------------------------------------------------------
# Policy resolution + cards
# ---------------------------------------------------------------------------


class TestResolvePolicies:
    @pytest.mark.asyncio
    async def test_defaults_without_settings_store(self):
        enforced, report_only, status = await resolve_csp_policies(None)
        assert enforced == DEFAULT_CSP
        assert report_only == STRICT_CSP
        assert status == "On — strict default"

    @pytest.mark.asyncio
    async def test_overrides_from_settings(self):
        settings = _Settings(
            {
                "admin.security.csp": STRICT_CSP,
                "admin.security.csp_report_only": "off",
            }
        )
        enforced, report_only, status = await resolve_csp_policies(settings)
        assert enforced == STRICT_CSP
        assert report_only is None
        assert status == "Off"

    @pytest.mark.asyncio
    async def test_custom_report_only_policy(self):
        custom = "default-src 'self'; script-src 'self';"
        settings = _Settings({"admin.security.csp_report_only": custom})
        _, report_only, status = await resolve_csp_policies(settings)
        assert report_only == custom
        assert status == "On — custom policy"

    @pytest.mark.asyncio
    async def test_settings_failure_falls_back_to_defaults(self):
        enforced, report_only, status = await resolve_csp_policies(
            _Settings(boom=True)
        )
        assert enforced == DEFAULT_CSP
        assert report_only == STRICT_CSP
        assert status == "On — strict default"


class TestCards:
    def test_default_enforced_policy_gets_unsafe_badges(self):
        html = render_csp_cards(
            DEFAULT_CSP, STRICT_CSP, "On — strict default", "/admin/security/csp-report"
        )
        assert "contains 'unsafe-inline'" in html
        assert "contains 'unsafe-eval'" in html
        assert "Report-only candidate" in html
        assert "/admin/security/csp-report" in html

    def test_strict_enforced_policy_gets_ok_badge(self):
        html = render_csp_cards(
            STRICT_CSP, STRICT_CSP, "On — strict default", "/admin/security/csp-report"
        )
        assert "contains 'unsafe-inline'" not in html
        assert ">strict<" in html

    def test_report_only_off_state(self):
        html = render_csp_cards(
            DEFAULT_CSP, None, "Off", "/admin/security/csp-report"
        )
        assert ">Off<" in html
        assert "Report-only monitoring is disabled" in html


# ---------------------------------------------------------------------------
# Violations region
# ---------------------------------------------------------------------------


class TestViolationsRegion:
    FRAGMENT_URL = "/admin/security/csp/violations"

    def test_empty_store_polls_with_empty_state(self):
        html = render_csp_violations_region(CspReportStore(), self.FRAGMENT_URL)
        assert 'id="security-csp-violations"' in html
        assert f'hx-get="{self.FRAGMENT_URL}"' in html
        assert 'hx-trigger="every 10s"' in html
        assert 'hx-swap="outerHTML"' in html
        assert EMPTY_STATE in html
        assert "0 received · 0 distinct" in html

    def test_no_store_renders_static_note_without_polling(self):
        html = render_csp_violations_region(None, self.FRAGMENT_URL)
        assert STORE_UNAVAILABLE in html
        assert "hx-get" not in html

    def test_deduped_rows_render(self):
        store = CspReportStore()
        report = {
            "directive": "script-src",
            "blocked_uri": "inline",
            "document_uri": "/admin/",
            "source_file": "/admin/app.js",
            "line": "7",
        }
        store.add(dict(report))
        store.add(dict(report))
        html = render_csp_violations_region(store, self.FRAGMENT_URL)
        assert "2 received · 1 distinct" in html
        assert "script-src" in html
        assert "/admin/app.js:7" in html
        assert EMPTY_STATE not in html


# ---------------------------------------------------------------------------
# Controller routes
# ---------------------------------------------------------------------------


class TestCspTabRoutes:
    @pytest.mark.asyncio
    async def test_anonymous_redirected_to_login(self):
        controller = _controller()
        resp = await controller.csp_page(_request(None))
        assert resp.status_code == 302
        assert "/admin/login" in resp.headers["location"]

    @pytest.mark.asyncio
    async def test_non_superadmin_403(self):
        controller = _controller()
        with pytest.raises(HTTPException) as exc:
            await controller.csp_page(_request(_FakeUser()))
        assert exc.value.status_code == 403
        with pytest.raises(HTTPException) as exc:
            await controller.csp_violations_fragment(_request(_FakeUser()))
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_page_composes_tabs_cards_and_region(self):
        store = CspReportStore()
        controller = _controller(_csp_store=store)
        captured: dict[str, Any] = {}

        async def fake_page(request, html, title, crumb):
            captured.update(html=html, title=title, crumb=crumb)
            from starlette.responses import HTMLResponse

            return HTMLResponse(html)

        controller._page = fake_page
        resp = await controller.csp_page(_request(_FakeUser(is_superuser=True)))
        assert resp.status_code == 200
        html = captured["html"]
        assert captured["title"] == "Content Security Policy"
        assert captured["crumb"] == "CSP"
        # Tab chrome with CSP active
        assert ">CSP</a>" in html
        assert "/admin/security/csp" in html
        # Cards + region
        assert "Enforced policy" in html
        assert "Report-only candidate" in html
        assert 'id="security-csp-violations"' in html

    @pytest.mark.asyncio
    async def test_page_renders_without_store(self):
        controller = _controller()  # _csp_store stays None
        controller._page = AsyncMock(
            side_effect=lambda request, html, title, crumb: _html_response(html)
        )
        resp = await controller.csp_page(_request(_FakeUser(is_superuser=True)))
        assert resp.status_code == 200
        assert STORE_UNAVAILABLE in resp.body.decode()

    @pytest.mark.asyncio
    async def test_fragment_returns_region_only(self):
        store = CspReportStore()
        store.add({"directive": "style-src", "blocked_uri": "inline"})
        controller = _controller(_csp_store=store)
        resp = await controller.csp_violations_fragment(
            _request(_FakeUser(is_superuser=True))
        )
        html = resp.body.decode()
        assert 'id="security-csp-violations"' in html
        assert "style-src" in html
        assert "<html" not in html  # fragment, not a shell page

    def test_tabs_include_csp_entry(self):
        controller = _controller()
        html = controller._tabs(_request(_FakeUser(is_superuser=True)), "csp")
        assert "/admin/security/csp" in html
        assert ">CSP</a>" in html


def _html_response(html: str):
    from starlette.responses import HTMLResponse

    return HTMLResponse(html)
