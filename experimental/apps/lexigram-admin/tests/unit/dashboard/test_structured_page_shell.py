"""R36 regressions — CSP report-only setting + structured-page shell (doc 32).

Covers the new ``SecuritySettings.csp_report_only`` field (default keeps
R34 behaviour, spec derivation) and the ``StructuredPageHandler`` response
ladder: full-page navigations now get the admin shell while HTMX fragment
requests keep receiving the bare fragment.
"""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.admin.dashboard.page_handlers import StructuredPageHandler
from lexigram.admin.middleware.security_headers import resolve_report_only_csp
from lexigram.admin.settings.panel.models import STRICT_CSP
from lexigram.contracts.admin.page_content import PageContent
from lexigram.contracts.admin.widget_content import TableCell, TableContent


class TestCspReportOnlySetting:
    def _nodes(self) -> dict[str, Any]:
        from lexigram.admin.settings.panel.security_spec import SecuritySpec

        return SecuritySpec.get_nodes()

    def test_spec_derives_the_field(self):
        """The panel form is model-derived; the field must be part of it."""
        nodes = self._nodes()
        assert "csp_report_only" in nodes
        # The other R34-relevant keys are still present.
        assert {"csp", "hsts_max_age", "frame_options"} <= set(nodes)

    def test_default_is_empty_meaning_strict_candidate_on(self):
        """A fresh panel save with untouched defaults must not change
        the R34 behaviour (empty -> strict candidate monitored)."""
        node = self._nodes()["csp_report_only"]
        default = getattr(node, "default", None)
        assert default == ""
        assert resolve_report_only_csp(default) == STRICT_CSP

    def test_off_value_suppresses(self):
        assert resolve_report_only_csp("off") is None

    def test_custom_policy_round_trips(self):
        custom = "default-src 'self'; script-src 'self';"
        assert resolve_report_only_csp(custom) == custom


def _page_content(title: str = "System Info") -> PageContent:
    return PageContent(
        title=title,
        body=TableContent(
            columns=("Field", "Value"),
            rows=((TableCell(text="K"), TableCell(text="V")),),
        ),
    )


class _Handler:
    async def handle(self, request: Any) -> PageContent:
        return _page_content()


def _scope(headers: list[tuple[bytes, bytes]] | None = None) -> dict[str, Any]:
    return {
        "type": "http",
        "method": "GET",
        "path": "/admin/system/info",
        "root_path": "/admin",
        "query_string": b"",
        "headers": headers or [],
        "app": None,
    }


async def _run(handler: StructuredPageHandler, scope: dict[str, Any]) -> tuple[int, bytes]:
    status: dict[str, Any] = {}
    chunks: list[bytes] = []

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b""}

    async def send(message: dict[str, Any]) -> None:
        if message["type"] == "http.response.start":
            status["code"] = message["status"]
        elif message["type"] == "http.response.body":
            chunks.append(message.get("body", b""))

    await handler(scope, receive, send)
    return status["code"], b"".join(chunks)


class TestStructuredPageShell:
    @pytest.mark.asyncio
    async def test_full_page_navigation_gets_admin_shell(self):
        code, body = await _run(StructuredPageHandler(_Handler()), _scope())
        html = body.decode()
        assert code == 200
        assert "<html" in html.lower()
        assert "System Info" in html
        # Shell chrome, not just the fragment
        assert "admin-shell" in html or "<title>" in html

    @pytest.mark.asyncio
    async def test_shell_title_comes_from_page_content(self):
        code, body = await _run(StructuredPageHandler(_Handler()), _scope())
        assert code == 200
        assert "<title>System Info" in body.decode()

    @pytest.mark.asyncio
    async def test_settings_panel_full_navigation_has_contextual_back_link(self):
        code, body = await _run(
            StructuredPageHandler(_Handler(), settings_url="/admin/settings"),
            _scope(),
        )
        html = body.decode()
        assert code == 200
        assert 'href="/admin/settings"' in html
        assert "Back to Settings" in html

    @pytest.mark.asyncio
    async def test_in_place_settings_panel_fragment_omits_redundant_back_link(self):
        scope = _scope(
            headers=[(b"hx-request", b"true"), (b"hx-target", b"settings-content")]
        )
        code, body = await _run(
            StructuredPageHandler(_Handler(), settings_url="/admin/settings"),
            scope,
        )
        html = body.decode()
        assert code == 200
        assert "<html" not in html.lower()
        assert "Back to Settings" not in html

    @pytest.mark.asyncio
    async def test_htmx_fragment_request_still_gets_bare_fragment(self):
        """wants_fragment keys off HX-Target (fragment swaps); boosted
        navigations carry no target and correctly get the full shell."""
        scope = _scope(
            headers=[(b"hx-request", b"true"), (b"hx-target", b"table-data")]
        )
        code, body = await _run(StructuredPageHandler(_Handler()), scope)
        html = body.decode()
        assert code == 200
        assert "<html" not in html.lower()
        assert "System Info" in html

    @pytest.mark.asyncio
    async def test_contract_violation_page_is_also_shell_wrapped(self):
        class _BadHandler:
            async def handle(self, request: Any) -> str:
                return "<h1>raw html</h1>"

        code, body = await _run(StructuredPageHandler(_BadHandler()), _scope())
        html = body.decode()
        assert code == 200
        assert "<html" in html.lower()
        assert "Page Contract Violation" in html
