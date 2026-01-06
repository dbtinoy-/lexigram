"""Tests for AdminSecurityHeaders and SecurityHeadersMiddleware."""

from __future__ import annotations

from unittest.mock import AsyncMock, call

import pytest

from lexigram.admin.middleware.security_headers import (
    AdminSecurityHeaders,
    SecurityHeadersMiddleware,
)
from lexigram.contracts.security import SecurityHeadersProtocol


# ============================================================================
# AdminSecurityHeaders unit tests
# ============================================================================


class TestAdminSecurityHeaders:
    def test_implements_protocol(self) -> None:
        assert isinstance(AdminSecurityHeaders(), SecurityHeadersProtocol)

    def test_apply_adds_mandatory_headers(self) -> None:
        service = AdminSecurityHeaders()
        headers = service.apply({})

        assert "Strict-Transport-Security" in headers
        assert "X-Frame-Options" in headers
        assert "X-Content-Type-Options" in headers
        assert "Referrer-Policy" in headers
        assert "Permissions-Policy" in headers
        assert "Content-Security-Policy" in headers

    def test_x_frame_options_is_deny(self) -> None:
        service = AdminSecurityHeaders()
        headers = service.apply({})
        assert headers["X-Frame-Options"] == "DENY"

    def test_x_content_type_options_is_nosniff(self) -> None:
        service = AdminSecurityHeaders()
        headers = service.apply({})
        assert headers["X-Content-Type-Options"] == "nosniff"

    def test_hsts_includes_subdomains(self) -> None:
        service = AdminSecurityHeaders()
        headers = service.apply({})
        assert "includeSubDomains" in headers["Strict-Transport-Security"]

    def test_hsts_custom_max_age(self) -> None:
        service = AdminSecurityHeaders(hsts_max_age=3600)
        headers = service.apply({})
        assert "max-age=3600" in headers["Strict-Transport-Security"]

    def test_csp_allows_unsafe_inline_for_htmx(self) -> None:
        service = AdminSecurityHeaders()
        headers = service.apply({})
        csp = headers["Content-Security-Policy"]
        assert "'unsafe-inline'" in csp

    def test_custom_csp_is_used(self) -> None:
        custom_csp = "default-src 'none';"
        service = AdminSecurityHeaders(csp=custom_csp)
        headers = service.apply({})
        assert headers["Content-Security-Policy"] == custom_csp

    def test_apply_does_not_overwrite_existing_header(self) -> None:
        """Route-level overrides must be preserved."""
        service = AdminSecurityHeaders()
        existing = {"X-Frame-Options": "SAMEORIGIN"}
        headers = service.apply(existing)
        assert headers["X-Frame-Options"] == "SAMEORIGIN"

    def test_apply_returns_same_dict(self) -> None:
        service = AdminSecurityHeaders()
        headers: dict[str, str] = {}
        returned = service.apply(headers)
        assert returned is headers

    def test_apply_to_non_empty_headers_merges_correctly(self) -> None:
        service = AdminSecurityHeaders()
        existing = {"content-type": "text/html"}
        headers = service.apply(existing)
        assert "content-type" in headers
        assert "X-Frame-Options" in headers


# ============================================================================
# SecurityHeadersMiddleware unit tests
# ============================================================================


class TestSecurityHeadersMiddleware:
    def _make_app(
        self,
        status: int = 200,
        raw_headers: list[tuple[bytes, bytes]] | None = None,
    ) -> AsyncMock:
        headers = raw_headers or []

        async def app(scope: dict, receive, send) -> None:
            await send(
                {
                    "type": "http.response.start",
                    "status": status,
                    "headers": headers,
                }
            )
            await send({"type": "http.response.body", "body": b""})

        return app  # type: ignore[return-value]

    @pytest.mark.asyncio
    async def test_security_headers_injected_on_http_response(self) -> None:
        app = self._make_app()
        send_mock = AsyncMock()
        middleware = SecurityHeadersMiddleware(app)

        await middleware(
            {"type": "http", "path": "/admin/"},
            AsyncMock(),
            send_mock,
        )

        start_call = send_mock.call_args_list[0][0][0]
        assert start_call["type"] == "http.response.start"
        injected = {k.decode(): v.decode() for k, v in start_call["headers"]}
        assert "X-Frame-Options" in injected
        assert "Content-Security-Policy" in injected

    @pytest.mark.asyncio
    async def test_non_http_scope_bypasses_middleware(self) -> None:
        app = AsyncMock()
        send_mock = AsyncMock()
        middleware = SecurityHeadersMiddleware(app)

        await middleware({"type": "websocket"}, AsyncMock(), send_mock)

        app.assert_called_once()
        send_mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_existing_headers_preserved(self) -> None:
        existing_headers = [(b"content-type", b"text/html; charset=utf-8")]
        app = self._make_app(raw_headers=existing_headers)
        send_mock = AsyncMock()
        middleware = SecurityHeadersMiddleware(app)

        await middleware({"type": "http"}, AsyncMock(), send_mock)

        start_call = send_mock.call_args_list[0][0][0]
        injected = {k.decode(): v.decode() for k, v in start_call["headers"]}
        assert injected.get("content-type") == "text/html; charset=utf-8"

    @pytest.mark.asyncio
    async def test_existing_security_header_not_overwritten(self) -> None:
        existing_headers = [(b"X-Frame-Options", b"SAMEORIGIN")]
        app = self._make_app(raw_headers=existing_headers)
        send_mock = AsyncMock()
        middleware = SecurityHeadersMiddleware(app)

        await middleware({"type": "http"}, AsyncMock(), send_mock)

        start_call = send_mock.call_args_list[0][0][0]
        injected = {k.decode(): v.decode() for k, v in start_call["headers"]}
        assert injected["X-Frame-Options"] == "SAMEORIGIN"

    @pytest.mark.asyncio
    async def test_body_message_passed_through_unchanged(self) -> None:
        app = self._make_app()
        send_mock = AsyncMock()
        middleware = SecurityHeadersMiddleware(app)

        await middleware({"type": "http"}, AsyncMock(), send_mock)

        body_call = send_mock.call_args_list[1][0][0]
        assert body_call["type"] == "http.response.body"
        assert body_call["body"] == b""

    @pytest.mark.asyncio
    async def test_custom_headers_service_used(self) -> None:
        """Injecting a custom SecurityHeadersProtocol impl is respected."""

        class AllowAllHeaders:
            def apply(self, headers: dict[str, str]) -> dict[str, str]:
                headers["X-Custom"] = "yes"
                return headers

        app = self._make_app()
        send_mock = AsyncMock()
        middleware = SecurityHeadersMiddleware(app, headers_service=AllowAllHeaders())

        await middleware({"type": "http"}, AsyncMock(), send_mock)

        start_call = send_mock.call_args_list[0][0][0]
        injected = {k.decode(): v.decode() for k, v in start_call["headers"]}
        assert injected.get("X-Custom") == "yes"
