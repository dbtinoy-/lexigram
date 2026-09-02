"""R34 regressions — CSP report-only groundwork (doc 30).

Covers the strict candidate policy headers, the settings off-switch, the
violation parser (both wire formats), the deduping store, the ingest/viewer
endpoints, and the middleware bypass entries.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest

from lexigram.admin.middleware.auth_guard import _bypass_routes
from lexigram.admin.middleware.csrf import _CSRF_BYPASS_PATHS
from lexigram.admin.middleware.security_headers import (
    AdminSecurityHeaders,
    resolve_report_only_csp,
)
from lexigram.admin.services.security.csp_reports import (
    MAX_REPORT_BODY_BYTES,
    CspReportEndpoint,
    CspReportStore,
    parse_csp_reports,
)
from lexigram.admin.settings.panel.models import DEFAULT_CSP, STRICT_CSP

LEGACY_REPORT = {
    "csp-report": {
        "document-uri": "https://admin.example/admin/",
        "violated-directive": "script-src 'self'",
        "effective-directive": "script-src",
        "blocked-uri": "inline",
        "source-file": "https://admin.example/admin/",
        "line-number": 42,
    }
}

REPORT_API_BATCH = [
    {
        "type": "csp-violation",
        "body": {
            "documentURL": "https://admin.example/admin/login",
            "effectiveDirective": "style-src",
            "blockedURL": "inline",
            "sourceFile": "https://admin.example/admin/login",
            "lineNumber": 7,
        },
    },
    {"type": "deprecation", "body": {"id": "x"}},
]


def make_request(
    *,
    body: bytes = b"",
    content_type: str = "application/csp-report",
    user: Any = None,
) -> Any:
    async def _body() -> bytes:
        return body

    return SimpleNamespace(
        headers={"content-type": content_type},
        body=_body,
        state=SimpleNamespace(user=user),
    )


# ---------------------------------------------------------------------------
# Headers
# ---------------------------------------------------------------------------


class TestReportOnlyHeaders:
    def test_strict_candidate_differs_only_in_inline_eval(self):
        assert "'unsafe-inline'" not in STRICT_CSP
        assert "'unsafe-eval'" not in STRICT_CSP
        assert "'unsafe-inline'" in DEFAULT_CSP
        # Same directive skeleton, stricter sources.
        assert "object-src 'none'" in STRICT_CSP
        assert "frame-ancestors 'none'" in STRICT_CSP

    def test_default_emits_report_only_and_enforced_headers(self):
        headers = AdminSecurityHeaders(
            report_endpoint="/admin/security/csp-report"
        ).apply({})
        assert headers["Content-Security-Policy"] == DEFAULT_CSP
        report_only = headers["Content-Security-Policy-Report-Only"]
        assert report_only.startswith(STRICT_CSP.rstrip(";").rstrip())
        assert "report-uri /admin/security/csp-report" in report_only
        assert "report-to csp-endpoint" in report_only
        assert (
            headers["Reporting-Endpoints"]
            == 'csp-endpoint="/admin/security/csp-report"'
        )

    def test_without_endpoint_policy_has_no_reporting_directives(self):
        headers = AdminSecurityHeaders().apply({})
        report_only = headers["Content-Security-Policy-Report-Only"]
        assert "report-uri" not in report_only
        assert "Reporting-Endpoints" not in headers

    def test_disabled_report_only_suppresses_headers(self):
        headers = AdminSecurityHeaders(
            report_only_csp=None, report_endpoint="/admin/security/csp-report"
        ).apply({})
        assert "Content-Security-Policy-Report-Only" not in headers
        assert "Reporting-Endpoints" not in headers
        assert headers["Content-Security-Policy"] == DEFAULT_CSP

    def test_resolve_setting_values(self):
        assert resolve_report_only_csp(None) == STRICT_CSP
        assert resolve_report_only_csp("") == STRICT_CSP
        for off in ("off", "OFF", "0", "false", "disabled", "none"):
            assert resolve_report_only_csp(off) is None
        custom = "default-src 'self'; script-src 'self';"
        assert resolve_report_only_csp(custom) == custom


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


class TestParser:
    def test_legacy_format(self):
        (report,) = parse_csp_reports(
            json.dumps(LEGACY_REPORT).encode(), "application/csp-report"
        )
        assert report["directive"] == "script-src"
        assert report["blocked_uri"] == "inline"
        assert report["line"] == "42"

    def test_report_api_batch_filters_non_csp_types(self):
        (report,) = parse_csp_reports(
            json.dumps(REPORT_API_BATCH).encode(), "application/reports+json"
        )
        assert report["directive"] == "style-src"
        assert report["document_uri"].endswith("/admin/login")

    def test_malformed_inputs_yield_nothing(self):
        for body in (b"", b"not json", b"[1, 2]", b'{"csp-report": []}', b'"x"'):
            assert parse_csp_reports(body, "application/csp-report") == []


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------


class TestStore:
    def test_dedupes_by_signature_and_counts(self):
        store = CspReportStore()
        report = {"directive": "script-src", "blocked_uri": "inline", "source_file": "x"}
        _, first_new = store.add(dict(report))
        violation, second_new = store.add(dict(report))
        assert first_new is True
        assert second_new is False
        assert violation.count == 2
        assert store.total_received == 2
        assert len(store.list_violations()) == 1

    def test_caps_signatures_evicting_oldest(self):
        store = CspReportStore(max_signatures=2)
        for i in range(3):
            store.add({"directive": f"d{i}", "blocked_uri": "", "source_file": ""})
        directives = {v.directive for v in store.list_violations()}
        assert directives == {"d1", "d2"}

    def test_orders_by_count_desc(self):
        store = CspReportStore()
        store.add({"directive": "rare", "blocked_uri": "", "source_file": ""})
        for _ in range(3):
            store.add({"directive": "hot", "blocked_uri": "", "source_file": ""})
        assert [v.directive for v in store.list_violations()] == ["hot", "rare"]


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


class TestEndpoint:
    @pytest.mark.asyncio
    async def test_ingest_stores_and_204(self):
        store = CspReportStore()
        endpoint = CspReportEndpoint(store)
        resp = await endpoint.ingest(
            make_request(body=json.dumps(LEGACY_REPORT).encode())
        )
        assert resp.status_code == 204
        assert store.total_received == 1

    @pytest.mark.asyncio
    async def test_ingest_rejects_oversized_body(self):
        store = CspReportStore()
        endpoint = CspReportEndpoint(store)
        resp = await endpoint.ingest(
            make_request(body=b"x" * (MAX_REPORT_BODY_BYTES + 1))
        )
        assert resp.status_code == 413
        assert store.total_received == 0

    @pytest.mark.asyncio
    async def test_ingest_ignores_wrong_content_type(self):
        store = CspReportStore()
        endpoint = CspReportEndpoint(store)
        resp = await endpoint.ingest(
            make_request(
                body=json.dumps(LEGACY_REPORT).encode(),
                content_type="text/plain",
            )
        )
        assert resp.status_code == 204
        assert store.total_received == 0

    @pytest.mark.asyncio
    async def test_viewer_auth_matrix(self):
        store = CspReportStore()
        store.add({"directive": "script-src", "blocked_uri": "inline"})
        endpoint = CspReportEndpoint(store)

        anon = await endpoint.list_reports(make_request(user=None))
        assert anon.status_code == 401

        plain = await endpoint.list_reports(
            make_request(user=SimpleNamespace(is_superuser=False))
        )
        assert plain.status_code == 403

        root = await endpoint.list_reports(
            make_request(user=SimpleNamespace(is_superuser=True))
        )
        assert root.status_code == 200
        payload = json.loads(root.body)
        assert payload["total_received"] == 1
        assert payload["violations"][0]["directive"] == "script-src"


# ---------------------------------------------------------------------------
# Middleware bypasses
# ---------------------------------------------------------------------------


class TestBypasses:
    def test_csrf_bypass_contains_report_path(self):
        assert "/security/csp-report" in _CSRF_BYPASS_PATHS

    def test_auth_guard_bypass_contains_full_report_path(self):
        routes = _bypass_routes("/admin")
        assert "/admin/security/csp-report" in routes
        # The viewer stays guarded.
        assert "/admin/security/csp-reports" not in routes

    def test_authorization_public_paths_contain_report_path(self):
        from lexigram.admin.middleware.authorization import _public_paths

        paths = _public_paths("/admin")
        assert "/admin/security/csp-report" in paths
        assert "/admin/security/csp-reports" not in paths
